# Room Occupancy Manager

Intelligent multi-room occupancy management with advanced bathroom fan automation for Home Assistant.

## What Makes This Special?

**Occupancy-Gated Environmental Triggers** - The fan only activates when the room is actually occupied AND environmental conditions change. This breakthrough feature eliminates false triggers from HVAC cycling, open windows, or temperature fluctuations when nobody is using the bathroom.

## Key Features

🚿 **Smart Bathroom Fan Automation**
- Dual triggers: Humidity OR temperature detection
- Rate-of-change analysis distinguishes showers from HVAC cycles
- Automatic shutoff when conditions normalize
- Respects manual fan control

💡 **Flexible Light Control**
- Bathroom mode: Lights only turn OFF (never ON) for privacy
- Normal mode: Full automatic on/off control
- Night-only mode: Time-restricted automation

🏠 **Multi-Room Management**
- Single app controls unlimited rooms
- Individual behaviors per room
- Motion, presence, door sensor support
- Timer-based fallback for rooms without presence sensors

🧠 **Intelligent Environmental Monitoring**
- Baseline tracking adapts to seasonal changes
- Configurable sensitivity thresholds
- Prevents false triggers while maintaining responsiveness

## Perfect For

- Bathrooms with humidity and temperature sensors
- Rooms requiring motion-based lighting
- Night-time automation for garages and hallways
- Any space where automatic occupancy management adds value

## Requirements

- Home Assistant 2024.1.0+
- AppDaemon 4.4.0+
- Temperature and humidity sensors (for bathroom fan control)
- Motion or presence sensors
- Timer entities

Transform your Home Assistant setup with intelligent, privacy-respecting automation that just works!