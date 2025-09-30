import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, time

class RoomOccupancyManager(hass.Hass):
    """
    Enhanced room occupancy manager with smart environmental controls.

    NEW FEATURES:
    - Rate-of-change temperature detection (prevents false triggers from HVAC cycles)
    - Automatic fan shutoff when humidity/temperature drops significantly
    - Temperature tracking for spike detection vs gradual warming
    - Smarter environmental monitoring

    Features:
    - Garage: Normal automatic light control with timer
    - Bathroom: Lights only turn OFF automatically, Fan turns ON with humidity OR temperature spike, uses timer for occupancy
    - Timer-based for both garage and bathroom until proper presence sensors available
    - FIXED: Timer NEVER starts if there is active occupancy (motion sensor ON)
    - FIXED: Timer restarts if motion sensor shows occupancy when timer expires
    """

    def initialize(self):
        """Initialize the room occupancy manager with all room configurations."""
        self.rooms = self.args.get("rooms", {})

        if not self.rooms:
            self.log("No rooms configured. Exiting initialization.", level="ERROR")
            return

        self.log(f"Initializing RoomOccupancyManager for {len(self.rooms)} rooms")

        for room_name, room_config in self.rooms.items():
            self.setup_room(room_name, room_config)

    def setup_room(self, room_name, room_config):
        """Set up listeners and initialize state for a single room."""
        try:
            # Initialize room state tracking
            room_config['occupancy_active'] = False
            room_config['last_humidity'] = None
            room_config['last_temperature'] = None
            room_config['previous_temperature'] = None  # NEW: For rate-of-change detection
            room_config['temperature_timestamps'] = []  # NEW: Track temperature change timing
            room_config['fan_active'] = False
            room_config['fan_triggered_by'] = None  # NEW: Track what triggered the fan (humidity/temperature/manual)

            # Validate configuration
            if not self.validate_room_config(room_name, room_config):
                return

            self.log(f"Setting up room: {room_name}")

            # Set up sensor listeners
            self.setup_motion_sensors(room_name, room_config)
            self.setup_door_sensors(room_name, room_config)
            self.setup_presence_sensors(room_name, room_config)
            self.setup_humidity_sensors(room_name, room_config)
            self.setup_temperature_sensors(room_name, room_config)
            self.setup_fan_listeners(room_name, room_config)  # NEW: Listen for manual fan activation
            self.setup_timer_listener(room_name, room_config)

        except Exception as e:
            self.log(f"Error setting up room {room_name}: {e}", level="ERROR")

    def validate_room_config(self, room_name, room_config):
        """Validate that room configuration has required elements."""
        if not room_config.get('lights') and not room_config.get('fans'):
            self.log(f"Room {room_name} has no lights or fans configured", level="WARNING")

        return True

    def setup_motion_sensors(self, room_name, room_config):
        """Set up motion sensor listeners for a room."""
        motion_sensors = room_config.get("motion_sensors", [])
        for sensor in motion_sensors:
            # Listen for motion ON (occupancy detected)
            self.listen_state(self.motion_detected, sensor, new="on",
                            room_name=room_name, sensor_type="motion")
            # Listen for motion OFF (potentially clear occupancy)
            self.listen_state(self.motion_cleared, sensor, new="off",
                            room_name=room_name, sensor_type="motion")
            self.log(f"Listening to motion sensor: {sensor}")

    def setup_door_sensors(self, room_name, room_config):
        """Set up door sensor listeners for a room."""
        doors = room_config.get("doors", [])
        for door in doors:
            self.listen_state(self.door_state_changed, door,
                            room_name=room_name, sensor_type="door")
            self.log(f"Listening to door sensor: {door}")

    def setup_presence_sensors(self, room_name, room_config):
        """Set up presence sensor listeners for immediate occupancy detection."""
        presence_sensors = room_config.get("presence_sensors", [])
        for sensor in presence_sensors:
            # Listen for both on and off states for immediate response
            self.listen_state(self.presence_detected, sensor, new="on",
                            room_name=room_name, sensor_type="presence")
            self.listen_state(self.presence_cleared, sensor, new="off",
                            room_name=room_name, sensor_type="presence")
            self.log(f"Listening to presence sensor: {sensor}")

    def setup_humidity_sensors(self, room_name, room_config):
        """Set up humidity sensor listeners for bathroom fan control."""
        humidity_sensors = room_config.get("humidity_sensors", [])
        for sensor in humidity_sensors:
            self.listen_state(self.humidity_changed, sensor,
                            room_name=room_name, sensor_type="humidity")
            # Initialize baseline humidity
            try:
                current_humidity = float(self.get_state(sensor))
                room_config['baseline_humidity'] = current_humidity
                room_config['last_humidity'] = current_humidity
                self.log(f"Baseline humidity for {room_name}: {current_humidity}%")
            except (ValueError, TypeError):
                self.log(f"Could not get initial humidity for {sensor}", level="WARNING")
                room_config['baseline_humidity'] = 50.0  # Default baseline
                room_config['last_humidity'] = 50.0

    def setup_temperature_sensors(self, room_name, room_config):
        """Set up temperature sensor listeners for bathroom fan control."""
        temperature_sensors = room_config.get("temperature_sensors", [])
        for sensor in temperature_sensors:
            self.listen_state(self.temperature_changed, sensor,
                            room_name=room_name, sensor_type="temperature")
            # Initialize baseline temperature
            try:
                current_temp = float(self.get_state(sensor))
                room_config['baseline_temperature'] = current_temp
                room_config['last_temperature'] = current_temp
                room_config['previous_temperature'] = current_temp
                room_config['temperature_timestamps'] = [datetime.now()]
                self.log(f"Baseline temperature for {room_name}: {current_temp}°")
            except (ValueError, TypeError):
                self.log(f"Could not get initial temperature for {sensor}", level="WARNING")
                room_config['baseline_temperature'] = 20.0  # Default baseline
                room_config['last_temperature'] = 20.0
                room_config['previous_temperature'] = 20.0
                room_config['temperature_timestamps'] = [datetime.now()]

    def setup_fan_listeners(self, room_name, room_config):
        """Set up fan state listeners to detect manual fan activation."""
        fans = room_config.get("fans", [])
        for fan in fans:
            # Listen for fan state changes to detect manual activation
            self.listen_state(self.fan_state_changed, fan,
                            room_name=room_name, fan_entity=fan)
            self.log(f"Listening to fan state changes: {fan}")

            # Initialize fan state tracking
            try:
                current_fan_state = self.get_state(fan)
                if current_fan_state == "on":
                    # Fan is already on at startup - assume manual until proven otherwise
                    room_config['fan_active'] = True
                    room_config['fan_triggered_by'] = 'manual'
                    self.log(f"Fan {fan} already ON at startup - marked as manual activation")
            except Exception as e:
                self.log(f"Could not get initial fan state for {fan}: {e}", level="WARNING")

    def setup_timer_listener(self, room_name, room_config):
        """Set up timer state listener for a room."""
        timer_entity = room_config.get("timer_entity")
        if timer_entity:
            self.listen_state(self.timer_finished, timer_entity, new="idle",
                            room_name=room_name)
            self.log(f"Listening to timer: {timer_entity}")

    def is_bathroom(self, room_name):
        """Check if this is a bathroom room."""
        room_config = self.rooms[room_name]
        behavior = room_config.get("behavior", "normal")
        return 'bathroom' in room_name.lower() or behavior == "bathroom"

    def has_presence_sensors(self, room_name):
        """Check if room has presence sensors configured."""
        room_config = self.rooms[room_name]
        return bool(room_config.get("presence_sensors", []))

    def motion_detected(self, entity, attribute, old, new, kwargs):
        """Handle motion detection in a room."""
        room_name = kwargs["room_name"]
        if self.is_bathroom(room_name):
            self.log(f"Motion detected in {room_name} (bathroom) - updating occupancy state only, no automatic lights")
        else:
            self.log(f"Motion detected in {room_name} - normal light control")
        self.handle_occupancy_detected(room_name)

    def motion_cleared(self, entity, attribute, old, new, kwargs):
        """Handle motion cleared - start timer ONLY when no other occupancy detected."""
        room_name = kwargs["room_name"]
        self.log(f"Motion cleared in {room_name} - checking if room is still occupied")

        # Check if any other sensors still show occupancy
        if not self.is_room_occupied(room_name):
            self.log(f"No other occupancy detected in {room_name} - starting timer")
            self.start_timer(room_name)
        else:
            self.log(f"Other occupancy still detected in {room_name} - not starting timer")

    def presence_detected(self, entity, attribute, old, new, kwargs):
        """Handle presence detection."""
        room_name = kwargs["room_name"]
        if self.is_bathroom(room_name):
            self.log(f"Presence detected in {room_name} (bathroom) - updating occupancy state only, no automatic lights")
        else:
            self.log(f"Presence detected in {room_name} - normal light control")
        self.handle_occupancy_detected(room_name)

    def presence_cleared(self, entity, attribute, old, new, kwargs):
        """Handle presence cleared - immediate response."""
        room_name = kwargs["room_name"]
        self.log(f"Presence cleared in {room_name} - immediate response")
        self.handle_occupancy_cleared(room_name)

    def door_state_changed(self, entity, attribute, old, new, kwargs):
        """Handle door state changes."""
        room_name = kwargs["room_name"]
        door_state = self.get_state(entity)

        if door_state == "on":  # Door opened
            if self.is_bathroom(room_name):
                self.log(f"Door opened in {room_name} (bathroom) - updating occupancy state only")
            else:
                self.log(f"Door opened in {room_name} - normal light control")
            self.handle_occupancy_detected(room_name)
        elif door_state == "off":  # Door closed
            self.log(f"Door closed in {room_name}")
            # For rooms with presence sensors, check immediately if empty
            if self.has_presence_sensors(room_name):
                if not self.is_room_occupied(room_name):
                    self.handle_occupancy_cleared(room_name)

    def humidity_changed(self, entity, attribute, old, new, kwargs):
        """Handle humidity changes for bathroom fan control with automatic shutoff."""
        room_name = kwargs["room_name"]
        room_config = self.rooms[room_name]

        try:
            current_humidity = float(new)
            baseline_humidity = room_config.get('baseline_humidity', 50.0)
            humidity_threshold = room_config.get('humidity_threshold', 5.0)

            # Calculate humidity change
            humidity_increase = current_humidity - baseline_humidity

            # CRITICAL: NEVER override manual control - respect user's explicit fan activation
            current_trigger = room_config.get('fan_triggered_by')
            if current_trigger == 'manual':
                # User manually turned on fan - don't interfere with environmental triggers
                self.log(f"Manual fan control active in {room_name} - ignoring humidity trigger")
                return

            # Check for humidity spike (shower detection) - AUTOMATICALLY TURN ON FAN
            if humidity_increase >= humidity_threshold and not room_config['fan_active'] and room_config.get('occupancy_active', False):
                self.log(f"🚿 SHOWER DETECTED! Humidity spike in {room_name}: {humidity_increase:.1f}% increase - turning on fan automatically")
                self.turn_on_fans(room_config)
                room_config['fan_active'] = True
                room_config['fan_triggered_by'] = 'humidity'

            # AUTOMATIC FAN SHUTOFF when humidity normalizes (only for automatically triggered fans)
            elif room_config['fan_active'] and room_config.get('fan_triggered_by') == 'humidity':
                # Use centralized environmental check
                if not self.should_keep_fan_on_when_empty(room_name, 'humidity'):
                    self.log(f"💨 HUMIDITY NORMALIZED! Fan auto-shutoff in {room_name}: humidity dropped to {humidity_increase:.1f}% above baseline")
                    self.turn_off_fans(room_config)
                    room_config['fan_active'] = False
                    room_config['fan_triggered_by'] = None
                elif humidity_increase < humidity_threshold * 0.7:  # 70% of threshold
                    self.log(f"Humidity decreasing in {room_name} ({humidity_increase:.1f}% above baseline) - fan will auto-shutoff when normalized")

            # Update baseline gradually when no spike
            elif humidity_increase < humidity_threshold * 0.5:
                # Slowly adjust baseline (moving average)
                room_config['baseline_humidity'] = (baseline_humidity * 0.95) + (current_humidity * 0.05)

            # Store last humidity for rate tracking
            room_config['last_humidity'] = current_humidity

        except (ValueError, TypeError) as e:
            self.log(f"Error processing humidity change: {e}", level="WARNING")

    def temperature_changed(self, entity, attribute, old, new, kwargs):
        """Handle temperature changes with RATE-OF-CHANGE detection and automatic fan shutoff."""
        room_name = kwargs["room_name"]
        room_config = self.rooms[room_name]

        try:
            current_temp = float(new)
            baseline_temp = room_config.get('baseline_temperature', 20.0)
            temp_threshold = room_config.get('temperature_threshold', 3.0)
            previous_temp = room_config.get('previous_temperature', current_temp)

            # Calculate temperature change
            temp_increase = current_temp - baseline_temp
            temp_change_rate = current_temp - previous_temp

            # CRITICAL: NEVER override manual control - respect user's explicit fan activation
            current_trigger = room_config.get('fan_triggered_by')
            if current_trigger == 'manual':
                # User manually turned on fan - don't interfere with environmental triggers
                self.log(f"Manual fan control active in {room_name} - ignoring temperature trigger")
                return

            # RATE-OF-CHANGE DETECTION
            now = datetime.now()
            room_config['temperature_timestamps'].append(now)

            # Keep only last 5 temperature readings (5 minutes max)
            if len(room_config['temperature_timestamps']) > 5:
                room_config['temperature_timestamps'] = room_config['temperature_timestamps'][-5:]

            # Calculate rate of change over time
            if len(room_config['temperature_timestamps']) >= 2:
                time_diff = (now - room_config['temperature_timestamps'][0]).total_seconds() / 60  # minutes
                if time_diff > 0:
                    temp_rate_per_min = temp_change_rate / time_diff

                    # SHOWER DETECTION: Rapid temperature rise (>1°F per minute) OR significant spike
                    rapid_rise = abs(temp_rate_per_min) > 1.0 and temp_change_rate > 0
                    significant_spike = temp_increase >= temp_threshold

                    if (rapid_rise or significant_spike) and not room_config['fan_active'] and room_config.get('occupancy_active', False):
                        if rapid_rise:
                            self.log(f"🚿 SHOWER DETECTED! Rapid temperature rise in {room_name}: {temp_rate_per_min:.1f}°F/min - turning on fan automatically")
                        else:
                            self.log(f"🚿 SHOWER DETECTED! Temperature spike in {room_name}: {temp_increase:.1f}°F increase - turning on fan automatically")

                        self.turn_on_fans(room_config)
                        room_config['fan_active'] = True
                        room_config['fan_triggered_by'] = 'temperature'

            # AUTOMATIC FAN SHUTOFF when temperature normalizes (only for automatically triggered fans)
            elif room_config['fan_active'] and room_config.get('fan_triggered_by') == 'temperature':
                # Use centralized environmental check
                if not self.should_keep_fan_on_when_empty(room_name, 'temperature'):
                    self.log(f"🌡️ TEMPERATURE NORMALIZED! Fan auto-shutoff in {room_name}: temperature dropped to {temp_increase:.1f}°F above baseline")
                    self.turn_off_fans(room_config)
                    room_config['fan_active'] = False
                    room_config['fan_triggered_by'] = None
                elif temp_increase < temp_threshold * 0.8:  # 80% of threshold
                    self.log(f"Temperature decreasing in {room_name} ({temp_increase:.1f}°F above baseline) - fan will auto-shutoff when normalized")

            # Update baseline gradually when no spike and stable temperature
            elif temp_increase < temp_threshold * 0.3 and abs(temp_change_rate) < 0.5:
                # Slowly adjust baseline (moving average) only when temperature is stable
                room_config['baseline_temperature'] = (baseline_temp * 0.98) + (current_temp * 0.02)

            # Store temperature for next rate calculation
            room_config['previous_temperature'] = current_temp
            room_config['last_temperature'] = current_temp

        except (ValueError, TypeError) as e:
            self.log(f"Error processing temperature change: {e}", level="WARNING")

    def fan_state_changed(self, entity, attribute, old, new, kwargs):
        """Handle fan state changes to detect manual activation."""
        room_name = kwargs["room_name"]
        fan_entity = kwargs["fan_entity"]
        room_config = self.rooms[room_name]

        self.log(f"Fan state change detected: {fan_entity} from {old} to {new}")

        if new == "on" and old == "off":
            # Fan turned ON - determine if manual or automatic
            if not room_config.get('fan_active', False):
                # System wasn't expecting fan to be on - this is MANUAL activation
                self.log(f"🔧 MANUAL FAN ACTIVATION detected in {room_name} - fan will stay on until room is empty")
                room_config['fan_active'] = True
                room_config['fan_triggered_by'] = 'manual'
            else:
                # System was expecting fan to be on (automatic activation already tracked)
                self.log(f"Automatic fan activation confirmed in {room_name}")

        elif new == "off" and old == "on":
            # Fan turned OFF
            if room_config.get('fan_active', False):
                if room_config.get('fan_triggered_by') == 'manual':
                    self.log(f"🔧 MANUAL FAN DEACTIVATION detected in {room_name}")
                else:
                    self.log(f"Automatic fan deactivation in {room_name}")

                # Reset fan tracking
                room_config['fan_active'] = False
                room_config['fan_triggered_by'] = None

    def timer_finished(self, entity, attribute, old, new, kwargs):
        """Handle when room timer finishes - FIXED to check occupancy properly."""
        room_name = kwargs["room_name"]
        room_config = self.rooms[room_name]

        self.log(f"Timer finished for {room_name} - checking if room is still occupied")

        # CRITICAL FIX: Check if room should still be considered occupied
        if self.is_room_occupied(room_name):
            self.log(f"TIMER RESTART: Room {room_name} still appears occupied (motion sensor ON), restarting timer")
            self.start_timer(room_name)
            return

        # Room is actually empty, turn off lights and fans
        self.log(f"Timer expired for {room_name} - room is confirmed empty, turning off lights/fans")
        self.handle_occupancy_cleared(room_name)

    def handle_occupancy_detected(self, room_name):
        """Handle when occupancy is detected in a room."""
        room_config = self.rooms[room_name]

        # Check light override
        light_override = room_config.get("light_override")
        if light_override and self.get_state(light_override) == "on":
            self.log(f"Light override active for {room_name}, skipping automatic control")
            return

        room_config['occupancy_active'] = True

        # CRITICAL: Cancel any running timer when occupancy is detected
        self.cancel_timer(room_name)

        # Different behavior for bathrooms vs other rooms
        if self.is_bathroom(room_name):
            # BATHROOM: NO AUTOMATIC LIGHT CONTROL
            self.log(f"Occupancy detected in {room_name} (bathroom) - no automatic light control")
        else:
            # NON-BATHROOM: Normal automatic light control
            room_behavior = room_config.get("behavior", "normal")

            if room_behavior == "night_only":
                if self.is_night_time():
                    self.turn_on_lights(room_config)
                    self.log(f"Turned on lights in {room_name} (night time)")
            elif room_behavior == "normal":
                self.turn_on_lights(room_config)
                self.log(f"Turned on lights in {room_name}")

        # DO NOT start timer here - timer should only start when occupancy clears!
        self.log(f"Occupancy active in {room_name} - timer will NOT start until occupancy clears")

    def handle_occupancy_cleared(self, room_name):
        """Handle when room becomes unoccupied."""
        room_config = self.rooms[room_name]

        # CRITICAL FIX: Double-check that room is actually empty BEFORE proceeding
        if self.is_room_occupied(room_name):
            self.log(f"OCCUPANCY CHECK: Room {room_name} appears to still be occupied, not clearing")
            return

        self.log(f"Room {room_name} is now EMPTY - checking lights and fans")

        # Check light override
        light_override = room_config.get("light_override")
        if light_override and self.get_state(light_override) == "on":
            self.log(f"Light override active for {room_name}, not turning off lights")
        else:
            # TURN OFF LIGHTS for ALL room types when empty
            self.log(f"Turning off ALL lights in {room_name} - room is empty")
            self.turn_off_lights(room_config)

        # ENHANCED FAN LOGIC: Different behavior for manual vs automatic fans
        if room_config.get('fan_active', False):
            fan_trigger_source = room_config.get('fan_triggered_by', 'unknown')

            if fan_trigger_source == 'manual':
                # MANUAL FAN: Turn off when room becomes empty (user wanted it on for bathroom use)
                self.log(f"🔧 MANUAL FAN - Turning off fan in {room_name} because room is now empty")
                self.turn_off_fans(room_config)
                room_config['fan_active'] = False
                room_config['fan_triggered_by'] = None
            elif fan_trigger_source in ['humidity', 'temperature']:
                # AUTOMATIC FAN: Only turn off if environmental conditions have normalized
                if self.should_keep_fan_on_when_empty(room_name, fan_trigger_source):
                    self.log(f"🌡️ AUTOMATIC FAN - Keeping fan on in {room_name} until environmental conditions normalize")
                else:
                    self.log(f"🌡️ AUTOMATIC FAN - Environmental conditions normalized, turning off fan in {room_name}")
                    self.turn_off_fans(room_config)
                    room_config['fan_active'] = False
                    room_config['fan_triggered_by'] = None
            else:
                # Unknown trigger source - default to turning off when empty
                self.log(f"⚠️ UNKNOWN FAN TRIGGER - Turning off fan in {room_name} (unknown source: {fan_trigger_source})")
                self.turn_off_fans(room_config)
                room_config['fan_active'] = False
                room_config['fan_triggered_by'] = None

        # Reset occupancy state
        room_config['occupancy_active'] = False

    def should_keep_fan_on_when_empty(self, room_name, trigger_source):
        """Check if automatic fan should stay on when room is empty due to environmental conditions."""
        room_config = self.rooms[room_name]

        if trigger_source == 'humidity':
            # Check if humidity has dropped significantly below threshold
            current_humidity = room_config.get('last_humidity', 0)
            baseline_humidity = room_config.get('baseline_humidity', 50.0)
            humidity_threshold = room_config.get('humidity_threshold', 5.0)
            humidity_increase = current_humidity - baseline_humidity

            # Keep fan on if humidity is still significantly elevated
            normalized_threshold = humidity_threshold * 0.4  # 40% of original threshold
            if humidity_increase >= normalized_threshold:
                self.log(f"Humidity still elevated: {humidity_increase:.1f}% (threshold: {normalized_threshold:.1f}%)")
                return True

        elif trigger_source == 'temperature':
            # Check if temperature has dropped significantly below threshold
            current_temp = room_config.get('last_temperature', 20.0)
            baseline_temp = room_config.get('baseline_temperature', 20.0)
            temp_threshold = room_config.get('temperature_threshold', 3.0)
            temp_increase = current_temp - baseline_temp

            # Keep fan on if temperature is still significantly elevated
            normalized_threshold = temp_threshold * 0.5  # 50% of original threshold
            if temp_increase >= normalized_threshold:
                self.log(f"Temperature still elevated: {temp_increase:.1f}°F (threshold: {normalized_threshold:.1f}°F)")
                return True

        # Environmental conditions have normalized
        return False

    def is_room_occupied(self, room_name):
        """Check if room appears to still be occupied - ENHANCED LOGGING."""
        room_config = self.rooms[room_name]

        # Check presence sensors first (most accurate)
        presence_sensors = room_config.get("presence_sensors", [])
        for sensor in presence_sensors:
            sensor_state = self.get_state(sensor)
            if sensor_state == "on":
                self.log(f"OCCUPANCY: Room {room_name} occupied - presence sensor {sensor} is {sensor_state}")
                return True

        # Check motion sensors - CRITICAL for timer restart logic
        motion_sensors = room_config.get("motion_sensors", [])
        for sensor in motion_sensors:
            sensor_state = self.get_state(sensor)
            if sensor_state == "on":
                self.log(f"OCCUPANCY: Room {room_name} occupied - motion sensor {sensor} is {sensor_state}")
                return True

        # Check if doors are open (indicating potential occupancy)
        doors = room_config.get("doors", [])
        for door in doors:
            door_state = self.get_state(door)
            if door_state == "on":  # Door open
                self.log(f"OCCUPANCY: Room {room_name} occupied - door sensor {door} is {door_state}")
                return True

        self.log(f"OCCUPANCY: Room {room_name} appears EMPTY - all sensors inactive")
        return False

    def start_timer(self, room_name):
        """Start timer ONLY if room is actually empty - CRITICAL SAFETY CHECK."""
        room_config = self.rooms[room_name]
        timer_entity = room_config.get("timer_entity")

        if timer_entity:
            # CRITICAL: Never start timer if there's active occupancy
            if self.is_room_occupied(room_name):
                self.log(f"TIMER BLOCKED: Cannot start timer for {room_name} - occupancy detected!")
                return

            current_timer_state = self.get_state(timer_entity)
            self.call_service("timer/start", entity_id=timer_entity)
            self.log(f"Timer for {room_name}: Started (was {current_timer_state}) - room confirmed empty")

    def cancel_timer(self, room_name):
        """Cancel the timer for a room if it's running."""
        room_config = self.rooms[room_name]
        timer_entity = room_config.get("timer_entity")

        if timer_entity:
            timer_state = self.get_state(timer_entity)
            if timer_state == "active":
                self.call_service("timer/cancel", entity_id=timer_entity)
                self.log(f"Cancelled timer for {room_name} - occupancy detected")

    def turn_on_lights(self, room_config):
        """Turn on all lights in a room."""
        lights = room_config.get("lights", [])
        for light in lights:
            current_state = self.get_state(light)
            if current_state == "off":
                self.turn_on(light)
                self.log(f"Turned ON light: {light} (was {current_state})")

    def turn_off_lights(self, room_config):
        """Turn off all lights in a room - ENHANCED to handle all light types."""
        lights = room_config.get("lights", [])
        for light in lights:
            current_state = self.get_state(light)
            if current_state == "on":
                self.turn_off(light)
                self.log(f"Turned OFF light: {light} (was {current_state})")
            elif current_state is None:
                self.log(f"WARNING: Light entity {light} not found or unavailable", level="WARNING")

    def turn_on_fans(self, room_config):
        """Turn on all fans in a room."""
        fans = room_config.get("fans", [])
        for fan in fans:
            current_state = self.get_state(fan)
            if current_state == "off":
                self.turn_on(fan)
                self.log(f"💨 Turned ON fan: {fan} (was {current_state})")

    def turn_off_fans(self, room_config):
        """Turn off all fans in a room."""
        fans = room_config.get("fans", [])
        for fan in fans:
            current_state = self.get_state(fan)
            if current_state == "on":
                self.turn_off(fan)
                self.log(f"🔇 Turned OFF fan: {fan} (was {current_state})")

    def is_night_time(self):
        """Check if it's currently night time."""
        try:
            current_time = datetime.now().time()
            sunrise_time = self.sunrise().time()
            sunset_time = self.sunset().time()
            return current_time >= sunset_time or current_time <= sunrise_time
        except Exception as e:
            self.log(f"Error checking night time: {e}", level="WARNING")
            return False