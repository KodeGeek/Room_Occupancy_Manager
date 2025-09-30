# Room Occupancy Manager for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)
[![AppDaemon](https://img.shields.io/badge/AppDaemon-4.4.0%2B-green.svg)](https://appdaemon.readthedocs.io/)

A sophisticated AppDaemon app for Home Assistant that provides intelligent room occupancy management with advanced bathroom fan automation based on environmental conditions.

## 🌟 Key Features

### Smart Occupancy Management
- **Multi-Room Support** - Manage unlimited rooms with individual behaviors
- **Flexible Sensor Integration** - Motion, presence, door, and environmental sensors
- **Timer-Based Fallback** - For rooms without presence sensors
- **Occupancy State Tracking** - Intelligent room state management with safety checks

### Intelligent Bathroom Fan Control 🚿
- **Occupancy-Gated Activation** ⭐ NEW - Fan only activates when room is occupied (prevents false triggers)
- **Dual Environmental Triggers** - Humidity OR temperature detection (supports hot and cold showers)
- **Rate-of-Change Detection** - Detects rapid temperature rises (>1°F/min) to distinguish showers from HVAC cycles
- **Automatic Fan Shutoff** - Fan turns off when environmental conditions normalize
- **Baseline Drift Compensation** - Adapts to seasonal temperature and humidity changes
- **Manual Override Support** - Respects and tracks manual fan activation
- **Configurable Thresholds** - Customize humidity and temperature sensitivity

### Advanced Light Control 💡
- **Bathroom Mode** - Lights only turn OFF automatically, never ON (user controls when to turn on)
- **Normal Mode** - Full automatic on/off control
- **Night-Only Mode** - Lights activate only during nighttime hours
- **Light Override** - Input boolean to disable automatic light control

## 📋 Prerequisites

- **Home Assistant** 2024.1.0 or newer
- **AppDaemon** 4.4.0+ addon installed and configured
- **Timer Integration** - Built into Home Assistant
- **Sensors Required**:
  - Motion sensors (`binary_sensor.*`)
  - Temperature sensors (`sensor.*_temperature`) - for bathroom fan control
  - Humidity sensors (`sensor.*_humidity`) - for bathroom fan control
- **Sensors Recommended**:
  - Presence sensors (`binary_sensor.*_presence`) - for accurate occupancy
  - Door sensors (`binary_sensor.*_door`) - for occupancy detection
- **Entities Required**:
  - Light entities (`light.*` or `switch.*`)
  - Fan entities (`fan.*` or `switch.*`) - for bathroom fan control
  - Timer entities (`timer.*`) - must be created in Home Assistant

## 🚀 Installation

### Via HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Automation" tab
3. Click the three dots menu in the top right
4. Select "Custom repositories"
5. Add the repository URL: `https://github.com/yourusername/room-occupancy-manager`
6. Select category: "AppDaemon"
7. Click "Add"
8. Click "Install" on the Room Occupancy Manager card
9. Restart AppDaemon addon

### Manual Installation

1. Copy `rooms_occupancy_manager.py` to your AppDaemon apps directory:
   ```
   /config/appdaemon/apps/room_occupancy_manager/rooms_occupancy_manager.py
   ```

2. Add configuration to your `apps.yaml` (see Configuration section)

3. Restart AppDaemon addon

## ⚙️ Configuration

### Step 1: Create Required Home Assistant Entities

#### Derivative Sensors for Rate-of-Change Detection (configuration.yaml)

The app can optionally use Home Assistant's derivative sensors for enhanced rate-of-change detection:

```yaml
sensor:
  # Temperature rate sensor - detects rapid temperature changes
  - platform: derivative
    source: sensor.kids_bathroom_temperature
    name: 'Kids Bathroom Temperature Rate'
    unit_time: min
    time_window: '00:05:00'  # 5-minute statistical window

  # Humidity rate sensor - detects rapid humidity changes
  - platform: derivative
    source: sensor.kids_bathroom_humidity
    name: 'Kids Bathroom Humidity Rate'
    unit_time: min
    time_window: '00:03:00'  # 3-minute window for faster response
```

**Note**: Derivative sensors are optional but recommended for environments with significant HVAC cycling or temperature fluctuations. The app will calculate rate-of-change internally if these sensors are not configured.

#### Timer Entities (configuration.yaml)
```yaml
timer:
  kids_bathroom_occupancy:
    duration: "00:05:00"
    name: "Kids Bathroom Occupancy Timer"

  garage_occupancy:
    duration: "00:02:00"
    name: "Garage Occupancy Timer"
```

#### Optional: Light Override (configuration.yaml)
```yaml
input_boolean:
  bathroom_light_override:
    name: "Bathroom Light Override"
    icon: mdi:light-switch
```

### Step 2: Configure AppDaemon App (apps.yaml)

#### Full-Featured Bathroom Example
```yaml
room_occupancy_manager:
  module: rooms_occupancy_manager
  class: RoomOccupancyManager
  rooms:
    kids_bathroom:
      # Behavior mode: bathroom, normal, or night_only
      behavior: bathroom

      # Sensors
      motion_sensors:
        - binary_sensor.kids_bathroom_motion
      presence_sensors:  # Optional but recommended
        - binary_sensor.kids_bathroom_presence
      doors:
        - binary_sensor.kids_bathroom_door
      humidity_sensors:
        - sensor.kids_bathroom_humidity
      temperature_sensors:
        - sensor.kids_bathroom_temperature

      # Optional: Derivative rate sensors for enhanced detection
      temperature_rate_sensors:
        - sensor.kids_bathroom_temperature_rate
      humidity_rate_sensors:
        - sensor.kids_bathroom_humidity_rate

      # Controlled Entities
      lights:
        - light.kids_bathroom_light
      fans:
        - fan.kids_bathroom_fan

      # Timer for occupancy fallback
      timer_entity: timer.kids_bathroom_occupancy

      # Environmental Thresholds (adjust based on your environment)
      humidity_threshold: 10.0    # Percentage increase above baseline
      temperature_threshold: 6.0  # Degrees F increase above baseline

      # Optional: Light override
      light_override: input_boolean.bathroom_light_override
```

#### Simple Bathroom (Minimal Sensors)
```yaml
room_occupancy_manager:
  module: rooms_occupancy_manager
  class: RoomOccupancyManager
  rooms:
    guest_bathroom:
      behavior: bathroom
      motion_sensors:
        - binary_sensor.guest_bathroom_motion
      humidity_sensors:
        - sensor.guest_bathroom_humidity
      lights:
        - light.guest_bathroom_light
      fans:
        - fan.guest_bathroom_fan
      timer_entity: timer.guest_bathroom_occupancy
      humidity_threshold: 10.0
      temperature_threshold: 6.0
```

#### Regular Room with Normal Behavior
```yaml
room_occupancy_manager:
  module: rooms_occupancy_manager
  class: RoomOccupancyManager
  rooms:
    living_room:
      behavior: normal  # Full automatic light control
      motion_sensors:
        - binary_sensor.living_room_motion
      presence_sensors:
        - binary_sensor.living_room_presence
      lights:
        - light.living_room_ceiling
        - light.living_room_lamp
      timer_entity: timer.living_room_occupancy
```

#### Night-Only Mode (Garage Example)
```yaml
room_occupancy_manager:
  module: rooms_occupancy_manager
  class: RoomOccupancyManager
  rooms:
    garage:
      behavior: night_only
      motion_sensors:
        - binary_sensor.garage_motion
      doors:
        - binary_sensor.garage_door
      lights:
        - light.garage_light
      timer_entity: timer.garage_occupancy
      night_start: "21:00:00"  # 9 PM
      night_end: "07:00:00"    # 7 AM
```

#### Multi-Room Configuration
```yaml
room_occupancy_manager:
  module: rooms_occupancy_manager
  class: RoomOccupancyManager
  rooms:
    kids_bathroom:
      behavior: bathroom
      motion_sensors: [binary_sensor.kids_bathroom_motion]
      humidity_sensors: [sensor.kids_bathroom_humidity]
      temperature_sensors: [sensor.kids_bathroom_temperature]
      lights: [light.kids_bathroom_light]
      fans: [fan.kids_bathroom_fan]
      timer_entity: timer.kids_bathroom_occupancy
      humidity_threshold: 10.0
      temperature_threshold: 6.0

    master_bathroom:
      behavior: bathroom
      motion_sensors: [binary_sensor.master_bathroom_motion]
      presence_sensors: [binary_sensor.master_bathroom_presence]
      humidity_sensors: [sensor.master_bathroom_humidity]
      temperature_sensors: [sensor.master_bathroom_temperature]
      lights: [light.master_bathroom_light]
      fans: [fan.master_bathroom_fan]
      timer_entity: timer.master_bathroom_occupancy
      humidity_threshold: 12.0
      temperature_threshold: 7.0

    garage:
      behavior: night_only
      motion_sensors: [binary_sensor.garage_motion]
      lights: [light.garage_light]
      timer_entity: timer.garage_occupancy
      night_start: "21:00:00"
      night_end: "07:00:00"
```

## 📖 Configuration Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `behavior` | string | No | `normal` | Room behavior mode: `bathroom`, `normal`, or `night_only` |
| `motion_sensors` | list | Yes* | - | Motion sensor entities |
| `presence_sensors` | list | No | - | Presence sensor entities (recommended for accuracy) |
| `doors` | list | No | - | Door sensor entities |
| `humidity_sensors` | list | No | - | Humidity sensor entities (required for bathroom fan control) |
| `temperature_sensors` | list | No | - | Temperature sensor entities (required for bathroom fan control) |
| `temperature_rate_sensors` | list | No | - | Derivative temperature rate sensors (optional, for enhanced detection) |
| `humidity_rate_sensors` | list | No | - | Derivative humidity rate sensors (optional, for enhanced detection) |
| `lights` | list | Yes* | - | Light entities to control |
| `fans` | list | No | - | Fan entities to control (bathroom mode) |
| `timer_entity` | string | Yes | - | Timer entity for occupancy tracking |
| `humidity_threshold` | float | No | `10.0` | Humidity increase % to trigger fan |
| `temperature_threshold` | float | No | `6.0` | Temperature increase °F to trigger fan |
| `light_override` | string | No | - | Input boolean to disable light automation |
| `night_start` | string | No | `21:00:00` | Night mode start time (HH:MM:SS) |
| `night_end` | string | No | `07:00:00` | Night mode end time (HH:MM:SS) |

*At least one occupancy sensor (motion or presence) and one light required per room.

## 🎯 Room Behaviors

### Bathroom Mode (`behavior: bathroom`)

**Designed for privacy and user control:**

- ✅ **Lights**: Only turn OFF automatically when room is empty
- ❌ **Lights**: NEVER turn ON automatically (user controls when to turn on lights)
- ✅ **Fan**: Automatically turns ON when humidity OR temperature spikes AND room is occupied
- ✅ **Fan**: Automatically turns OFF when environmental conditions normalize
- ✅ **Manual Fan**: Respects manual fan activation, turns off when room becomes empty

**Why Bathroom Mode?**
Bathrooms require privacy. This mode ensures the automation only helps by turning things OFF, never surprising users by turning lights ON when they enter.

### Normal Mode (`behavior: normal`)

**Full automatic control:**

- ✅ Lights turn ON automatically when occupancy detected
- ✅ Lights turn OFF automatically when room is empty
- ✅ Standard room automation

### Night-Only Mode (`behavior: night_only`)

**Time-restricted automation:**

- ✅ Lights turn ON only during configured night hours
- ✅ Lights turn OFF when room is empty
- ✅ Perfect for garages, hallways, utility rooms

## 🔬 How It Works

### Environmental Fan Control Algorithm

The app uses a sophisticated algorithm to detect shower activity while avoiding false triggers:

#### 1. **Occupancy Gate** ⭐ NEW
```
Fan Activation = (Environmental Trigger) AND (Room Occupied)
```

This prevents the fan from turning on due to:
- HVAC cycling when nobody is in the bathroom
- Open windows on humid days
- Temperature fluctuations from neighboring rooms

#### 2. **Dual Trigger System**
The fan activates if EITHER condition is met:

**Humidity Trigger:**
- Current humidity > baseline + threshold (default 10%)
- Example: Baseline 50% → Triggers at 60%

**Temperature Trigger (Two Methods):**
- **Spike Detection**: Current temp > baseline + threshold (default 6°F)
- **Rate-of-Change**: Temperature rising faster than 1°F per minute

#### 3. **Baseline Tracking**
The app maintains dynamic baseline values that adapt to:
- Seasonal temperature changes
- Weather-related humidity variations
- HVAC system cycling

Baselines update gradually when no spike is detected, ensuring accurate detection year-round.

#### 4. **Automatic Shutoff**
Fan turns off when:
- **Humidity**: Drops below 40% of threshold (e.g., <4% above baseline)
- **Temperature**: Drops below 50% of threshold (e.g., <3°F above baseline)

This ensures the fan runs long enough to clear moisture but doesn't waste energy.

#### 5. **Manual Override Tracking**
- Detects when user manually turns fan on/off
- Manual fan activation: Fan stays on until room is empty
- Respects user control over environmental automation

### Occupancy Detection Logic

#### With Presence Sensors (Recommended)
1. Presence ON → Room occupied (immediate)
2. Presence OFF → Room empty (immediate response)
3. Most accurate method

#### With Motion Sensors Only
1. Motion ON → Room occupied
2. Motion OFF → Start timer
3. Timer expires → Check if motion still off
4. If motion ON when timer expires → Restart timer (prevents premature shutoff)
5. Room marked empty only when timer expires AND no motion

#### Timer Restart Prevention
**Safety Feature**: Timer will NEVER start if:
- Any motion sensor is ON
- Any presence sensor is ON
- Any door is open

This prevents lights/fans from turning off while room is actually occupied.

## 🐛 Troubleshooting

### Fan Keeps Turning On Randomly

**Cause**: Environmental thresholds too sensitive

**Solution**: Increase thresholds in `apps.yaml`:
```yaml
humidity_threshold: 15.0    # Increased from 10.0
temperature_threshold: 8.0  # Increased from 6.0
```

Start conservative and decrease if fan doesn't activate during actual showers.

### Fan Never Turns On

**Possible Causes**:
1. Room not detected as occupied
2. Thresholds too high
3. Sensors not reporting correctly

**Solutions**:
1. Check AppDaemon logs: Settings → Add-ons → AppDaemon → Logs
2. Verify occupancy sensors are working
3. Lower thresholds temporarily to test
4. Ensure humidity/temperature sensors are reporting values

### Lights Turn On in Bathroom

**Cause**: Behavior not set to bathroom mode

**Solution**: Verify in `apps.yaml`:
```yaml
kids_bathroom:
  behavior: bathroom  # Must be set!
```

### Timer Keeps Restarting

**This is normal behavior!** The timer restarts if motion is detected when it expires. This prevents lights from turning off while someone is still in the room.

If this is happening too frequently:
- Consider adding presence sensors for more accurate occupancy detection
- Increase timer duration

### Fan Doesn't Turn Off

**Possible Causes**:
1. Environmental conditions haven't normalized
2. Manual fan activation

**Solutions**:
1. Check current humidity/temperature in Home Assistant
2. Wait for conditions to normalize (fan will auto-shutoff)
3. If manually activated, fan turns off when room becomes empty

### Logs Show "Permission Denied"

**Cause**: AppDaemon doesn't have access to sensors or entities

**Solution**: Verify entity IDs exist in Home Assistant Developer Tools → States

## 📊 Monitoring and Tuning

### View Logs

AppDaemon logs show detailed operation:

Settings → Add-ons → AppDaemon → Logs

Look for messages like:
```
🚿 SHOWER DETECTED! Humidity spike in kids_bathroom: 12.3% increase - turning on fan automatically
💨 HUMIDITY NORMALIZED! Fan auto-shutoff in kids_bathroom: humidity dropped to 3.2% above baseline
```

### Tuning Thresholds

Start with default values and monitor for 1-2 weeks:

**Too Many False Triggers?**
- Increase `humidity_threshold` and `temperature_threshold`
- Try: 12-15% humidity, 7-9°F temperature

**Fan Doesn't Activate During Showers?**
- Decrease thresholds
- Try: 7-8% humidity, 4-5°F temperature

**Optimal Settings Depend On**:
- Bathroom size and ventilation
- Shower temperature preferences
- HVAC system behavior
- Sensor placement and accuracy

## 🎓 Examples

### Example 1: Kids Bathroom (Full Featured)
```yaml
kids_bathroom:
  behavior: bathroom
  motion_sensors:
    - binary_sensor.kids_bathroom_motion
  presence_sensors:
    - binary_sensor.kids_bathroom_presence
  doors:
    - binary_sensor.kids_bathroom_door
  humidity_sensors:
    - sensor.kids_bathroom_humidity
  temperature_sensors:
    - sensor.kids_bathroom_temperature
  lights:
    - light.kids_bathroom_light
  fans:
    - fan.kids_bathroom_fan
  timer_entity: timer.kids_bathroom_occupancy
  humidity_threshold: 10.0
  temperature_threshold: 6.0
  light_override: input_boolean.kids_bathroom_light_override
```

### Example 2: Guest Bathroom (Minimal)
```yaml
guest_bathroom:
  behavior: bathroom
  motion_sensors:
    - binary_sensor.guest_bathroom_motion
  humidity_sensors:
    - sensor.guest_bathroom_humidity
  lights:
    - light.guest_bathroom_vanity
  fans:
    - switch.guest_bathroom_fan
  timer_entity: timer.guest_bathroom_occupancy
  humidity_threshold: 12.0
```

### Example 3: Master Bedroom (Normal)
```yaml
master_bedroom:
  behavior: normal
  motion_sensors:
    - binary_sensor.master_bedroom_motion
  presence_sensors:
    - binary_sensor.master_bedroom_presence
  lights:
    - light.master_bedroom_ceiling
    - light.master_bedroom_bedside_lamp
  timer_entity: timer.master_bedroom_occupancy
```

### Example 4: Garage (Night-Only)
```yaml
garage:
  behavior: night_only
  motion_sensors:
    - binary_sensor.garage_motion
  doors:
    - binary_sensor.garage_door
  lights:
    - light.garage_overhead
  timer_entity: timer.garage_occupancy
  night_start: "20:00:00"
  night_end: "08:00:00"
```

## 🔐 Best Practices

1. **Start Conservative**: Use higher thresholds initially (10% humidity, 6°F temperature)
2. **Monitor Logs**: Watch for false triggers over 1-2 weeks
3. **Use Presence Sensors**: More accurate than motion sensors alone
4. **Create Proper Timers**: Define timer entities in `configuration.yaml`
5. **Test Thoroughly**: Verify each room's behavior matches expectations
6. **Bathroom Mode**: Always use `behavior: bathroom` for bathrooms to maintain privacy
7. **Light Override**: Create override input_booleans for manual control when needed

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Credits

Created for the Home Assistant community. Special thanks to all contributors and testers.

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/room-occupancy-manager/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/room-occupancy-manager/discussions)
- **Home Assistant Community**: [Community Forum Thread](https://community.home-assistant.io/)

## 📝 Changelog

### Version 2.0.0 (2025-09-30)
- ⭐ NEW: Occupancy-gated fan activation (prevents false triggers)
- ⭐ NEW: Comprehensive HACS documentation
- Enhanced rate-of-change temperature detection
- Improved manual fan override tracking
- Better baseline drift compensation
- Bug fixes and stability improvements

### Version 1.0.0
- Initial release
- Multi-room occupancy management
- Bathroom fan automation with humidity/temperature triggers
- Timer-based occupancy tracking
- Multiple room behavior modes