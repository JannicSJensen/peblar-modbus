# Peblar Modbus for Home Assistant

A HACS-compatible custom integration for Peblar Home and Peblar Business EV
chargers using the charger's local Modbus TCP API.

This integration uses the `peblar_modbus` domain and can coexist with Home
Assistant's built-in `peblar` integration, which uses Peblar's local REST API.
All communication stays on your local network.

## Features

- Charging state and active current limiter
- Total and session energy
- Total and per-phase power, voltage, and current
- Wi-Fi/cellular signal strength and uptime
- Active warning/error indication
- Socket lock state
- Optional charge enable, current limit, and 1/3-phase controls
- UI configuration; no YAML required

## Requirements

- Peblar firmware 1.6 or newer
- Modbus API enabled in the charger's web interface under advanced settings
- TCP port 502 reachable from Home Assistant
- Modbus API access mode set to **ReadOnly**, or **ReadWrite** if controls are
  enabled in the integration

## Installation with HACS

1. Open HACS and select **Integrations**.
2. Open the menu and choose **Custom repositories**.
3. Add this repository URL and select the **Integration** category.
4. Install **Peblar Modbus** and restart Home Assistant.
5. Go to **Settings > Devices & services > Add integration** and search for
   **Peblar Modbus**.

For manual installation, copy `custom_components/peblar_modbus` into the
`custom_components` directory in your Home Assistant configuration directory,
then restart Home Assistant.

## Configuration

Enter the charger's hostname or IP address. The defaults are TCP port `502`,
Modbus unit ID `255`, and a 10-second polling interval.

Write controls are disabled by default. Enable them only after setting the
charger's Modbus API access mode to **ReadWrite**. Setting the charge current to
`0 A` pauses charging. The charge switch remembers the last limit of at least
`6 A` and restores it when charging is resumed.

> Peblar advises against pausing more than three times in ten minutes to
> protect the charger's relays.

## Notes

- A 1-phase charger does not expose phase 2 and phase 3 registers; those
  entities are therefore not created.
- The force-single-phase control is only created when the charger reports
  independent relays and more than one connected phase.
- Register addresses and encodings follow Peblar's official
  [Modbus API documentation](https://developer.peblar.com/modbus-api) and
  [reference client](https://github.com/Peblar/py-modbus-api-client).

## License

MIT
