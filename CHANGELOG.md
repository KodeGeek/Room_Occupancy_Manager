# Changelog - Room Occupancy Manager

## [Unreleased] - 2025-10-02

### Fixed
- **Critical: AppDaemon restart bug causing automatic fans to be misclassified as manual**
  - Added environmental condition checking during initialization to correctly determine fan trigger source
  - System now checks humidity/temperature levels at startup to distinguish between automatic and manual fan activation
  - Prevents automatic fans from running indefinitely after restart
  
- **Critical: Manual fans in empty rooms persist after restart**
  - Added occupancy check after manual fan detection during initialization
  - Manual fans in empty rooms are now immediately turned off at startup
  - Prevents fans from staying on indefinitely when room was empty before restart

- **Temperature monitoring causing extended bathroom fan runtime**
  - Removed temperature sensors from example bathroom configurations
  - Temperature takes 3-4x longer to normalize than humidity in bathrooms
  - Humidity-only monitoring provides faster, more appropriate fan shutoff after showers
  - Updated example configurations with warnings about temperature monitoring impact

### Changed
- Normalized humidity threshold from 40% to 50% for consistency with temperature normalization
- Updated `apps.yaml.example` with best practices and warnings for temperature monitoring
- Improved logging messages for restart scenarios with emoji indicators
- Adjusted humidity threshold in examples from 10% to 5% (matches production best practices)

### Added
- Environmental condition checking in `setup_fan_listeners()` for initial fan state detection
- Environmental condition checking in `fan_state_changed()` for runtime state changes after restart
- Empty room detection and immediate fan shutoff for manual fans at startup
- Comprehensive logging for restart scenarios:
  - "Fan already ON at startup - checking environmental conditions"
  - "Humidity elevated (X%) - treating as AUTOMATIC trigger"
  - "No environmental justification - treating as MANUAL activation"
  - "Room X is empty with manual fan - turning off fan"

## Technical Details

### Files Modified
- `apps/room_occupancy_manager/rooms_occupancy_manager.py`
  - Added 76 new lines (623 → 699 total lines)
  - Enhanced `setup_fan_listeners()` with environmental checking (lines 151-199)
  - Enhanced `fan_state_changed()` with restart detection (lines 374-405)
  - Fixed humidity normalization threshold (line 499: 0.4 → 0.5)

- `apps.yaml.example`
  - Commented out temperature monitoring in bathroom examples
  - Added warnings about temperature causing extended runtime
  - Adjusted humidity thresholds to recommended values
  - Updated comments with best practices

### Restart Scenarios Now Handled
1. **Room Occupied + Automatic Fan + Restart**: ✅ Maintains automatic trigger, turns off when normalized
2. **Room Empty + Automatic Fan + Restart**: ✅ Maintains automatic trigger, humidity_changed handles shutoff
3. **Room Occupied + Manual Fan + Restart**: ✅ Maintains manual trigger, turns off when room empty
4. **Room Empty + Manual Fan + Restart**: ✅ Detects manual + empty, immediately turns off fan

### Breaking Changes
None - All changes are backward compatible and improve reliability

### Migration Notes
- Existing installations will automatically benefit from restart bug fixes
- Consider removing `temperature_sensors` from bathroom configurations for faster fan shutoff
- No configuration changes required for bug fixes to take effect
