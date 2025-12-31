# Cala Water Heater Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/RAR/Cala-HA.svg)](https://github.com/RAR/Cala-HA/releases)

A Home Assistant custom integration for Cala heat pump water heaters. This integration allows you to monitor and control your Cala water heater through Home Assistant.

## Features

- **Water Heater Entity**: Full control with temperature adjustment and operation modes
- **Temperature Sensors**: Real-time monitoring of tank temperatures (top, upper, lower), ambient, inlet, outlet, and delivery temperatures
- **Compressor Sensors**: Monitor compressor frequency, delivery/suction pressures
- **Usage Sensors**: Track energy consumption, water usage, and hot water availability
- **Binary Sensors**: Device connectivity, compressor running, fan running, safety lockout status

## Supported Devices

- Cala Heat Pump Water Heaters (HPWH)

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: \`https://github.com/RAR/Cala-HA\`
6. Select "Integration" as the category
7. Click "Add"
8. Search for "Cala Water Heater" and install it
9. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/RAR/Cala-HA/releases)
2. Extract the \`custom_components/cala\` folder to your Home Assistant's \`custom_components\` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Cala Water Heater"
4. Enter your Cala app credentials (email and password)
5. Click **Submit**

## Entities

### Water Heater

| Entity | Description |
|--------|-------------|
| \`water_heater.cala_<device_name>\` | Main water heater control entity |

**Supported Features:**
- Temperature control (35°C - 60°C / 95°F - 140°F)
- Operation modes: Standard, Boost, Vacation, Eco

### Sensors

| Sensor | Description | Unit |
|--------|-------------|------|
| Top Tank Temperature | Temperature at top of tank (real-time) | °C |
| Upper Tank Temperature | Temperature in upper section | °C |
| Lower Tank Temperature | Temperature in lower section | °C |
| Ambient Temperature | Air temperature around unit | °C |
| Inlet Temperature | Cold water inlet temperature | °C |
| Outlet Temperature | Hot water outlet temperature | °C |
| Delivery Temperature | Refrigerant delivery temperature | °C |
| Target Temperature | User-set desired temperature | °C |
| Maximum Temperature Setting | User-set maximum temperature | °C |
| Energy Used | Energy consumption | kWh |
| Water Used | Total water used | L |
| Hot Water Available | Estimated hot water available | L |
| Uptime | Device uptime | seconds |
| Compressor Frequency | Current compressor speed | Hz |
| Delivery Pressure | Refrigerant high-side pressure | kPa |
| Suction Pressure | Refrigerant low-side pressure | kPa |

*Note: Temperature values are provided in Celsius and automatically converted by Home Assistant based on your display preferences.*

### Binary Sensors

| Sensor | Description |
|--------|-------------|
| Connected | Device cloud connectivity status |
| Compressor Running | Whether the compressor is currently running |
| Fan Running | Whether the fan is currently running |
| Safety Lockout | Safety lockout status (problem indicator) |

## Services

The standard Home Assistant water heater services are supported:

- \`water_heater.set_temperature\` - Set target temperature
- \`water_heater.set_operation_mode\` - Set operation mode (standard, boost, vacation, eco)

### Operation Modes

| Mode | Description |
|------|-------------|
| **standard** | Normal operation |
| **boost** | Activates boost mode for 1 hour (higher priority heating) |
| **vacation** | Activates vacation mode for 7 days (reduced heating) |
| **eco** | Eco mode (placeholder - not yet fully implemented) |

## Data Refresh

The integration polls the Cala cloud API every **60 seconds** for updated sensor data. This includes both aggregated data (energy usage, water usage) and real-time data (temperatures, compressor status).

## Troubleshooting

### Cannot connect to Cala servers
- Verify your Cala app credentials are correct
- Check that the Cala mobile app is working
- Ensure your Home Assistant has internet access

### No sensor data
- Some sensors may not appear until the device has been connected and sending data
- Check the Cala app to verify the device is connected and reporting data

### Sensors showing "Unknown"
- Some sensors (like outlet temperature) may return null from the API if not available
- Delete unavailable entities via Settings → Devices & Services → Entities

### Debug Logging

To enable debug logging, add the following to your \`configuration.yaml\`:

\`\`\`yaml
logger:
  default: info
  logs:
    custom_components.cala: debug
\`\`\`

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

## Trademark Disclaimer

All trademarks, logos, and brand names are the property of their respective owners. All company, product, and service names used in this project are for identification purposes only. Use of these names, trademarks, and brands does not imply endorsement.
