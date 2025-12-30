# Cala Water Heater Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/RAR/Cala-HA.svg)](https://github.com/RAR/Cala-HA/releases)

A Home Assistant custom integration for Cala heat pump water heaters. This integration allows you to monitor and control your Cala water heater through Home Assistant.

## Features

- **Water Heater Entity**: Full control with temperature adjustment, operation modes, and boost mode
- **Sensor Entities**: Monitor temperatures (tank, ambient, inlet, outlet), energy consumption, and water usage
- **Binary Sensor Entities**: Track device connectivity and heating status

## Supported Devices

- Cala Heat Pump Water Heaters (HPWH)

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/RAR/Cala-HA`
6. Select "Integration" as the category
7. Click "Add"
8. Search for "Cala Water Heater" and install it
9. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/RAR/Cala-HA/releases)
2. Extract the `custom_components/cala` folder to your Home Assistant's `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Cala Water Heater"
4. Enter your Cala app credentials (email and password)
5. Select your home from the list
6. Click **Submit**

## Entities

### Water Heater

| Entity | Description |
|--------|-------------|
| `water_heater.cala_<device_name>` | Main water heater control entity |

**Supported Features:**
- Temperature control (95°F - 140°F / 35°C - 60°C)
- Operation modes: Performance, Eco, Vacation
- Boost mode (via `away_mode`)

### Sensors

| Entity | Description | Unit |
|--------|-------------|------|
| `sensor.cala_<name>_tank_temperature` | Current tank water temperature | °F/°C |
| `sensor.cala_<name>_ambient_temperature` | Ambient temperature around unit | °F/°C |
| `sensor.cala_<name>_inlet_temperature` | Water inlet temperature | °F/°C |
| `sensor.cala_<name>_outlet_temperature` | Water outlet temperature | °F/°C |
| `sensor.cala_<name>_energy_consumption` | Energy used | kWh |
| `sensor.cala_<name>_water_usage` | Hot water dispensed | Liters |

### Binary Sensors

| Entity | Description |
|--------|-------------|
| `binary_sensor.cala_<name>_connected` | Device connectivity status |
| `binary_sensor.cala_<name>_heating` | Whether the unit is actively heating |

## Services

The standard Home Assistant water heater services are supported:

- `water_heater.set_temperature` - Set target temperature
- `water_heater.set_operation_mode` - Set operation mode (performance, eco, vacation)
- `water_heater.turn_away_mode_on` - Enable boost mode
- `water_heater.turn_away_mode_off` - Disable boost mode

## Troubleshooting

### Cannot connect to Cala servers
- Verify your Cala app credentials are correct
- Check that the Cala mobile app is working
- Ensure your Home Assistant has internet access

### No sensor data
- Some sensors may not appear until the device has been connected and sending data for a while
- Check the Cala app to verify the device is connected and reporting data

### Debug Logging

To enable debug logging, add the following to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.cala: debug
```

## Requirements

- Home Assistant 2024.1.0 or newer
- A Cala account with at least one water heater configured
- The water heater must be connected to the internet and visible in the Cala app

## Privacy & Security

This integration communicates directly with Cala's AWS-based cloud services using the same API as the official mobile app. Your credentials are stored securely in Home Assistant and are only used to authenticate with Cala's servers.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This is an unofficial integration and is not affiliated with, endorsed by, or connected to Cala Systems in any way. Use at your own risk.
