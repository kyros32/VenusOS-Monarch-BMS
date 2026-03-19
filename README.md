# Monarch BMS DBus Service (VenusOS)

This project publishes Monarch BMS data from Modbus TCP to:

`com.victronenergy.battery.monarch`

It is structured for SetupHelper / kwindrem Package Manager style deployment:

- `setup` install/uninstall hook
- `service/run` runit service entrypoint
- `qml/PageMonarchBms.qml` settings + status page
- `version` package version
- `venusos_monarch_bms_service.py` driver daemon

## Why the old script could destabilize BMS behavior

The original `monarch_bms.py` had multiple high-risk behaviors:

- It pushed hardcoded placeholder battery values (`/Soc`, voltage, current) when live values were not decoded.
- It published partially decoded blocks as authoritative limits, with no plausibility checks.
- It had fixed IP/port/device-id in code, so field configuration changes required code edits/restarts.
- It lacked a proper package-managed service lifecycle, so startup/recovery could be inconsistent.

This rewrite is read-only on Modbus, removes fake live values, and adds bounded runtime settings.

## Install with Package Manager (SetupHelper)

In kwindrem Package Manager add:

- **Package name:** `venusos-monarch-bms`
- **GitHub user:** `<your github user>`
- **GitHub branch/tag:** `main`

Then **Download** and **Install**.

## Manual install (SSH)

```bash
rm -rf /data/venusos-monarch-bms
mkdir -p /data/venusos-monarch-bms
wget -O - https://github.com/<your user>/venusos-monarch-bms/archive/refs/heads/main.tar.gz | tar -xzf - -C /data/venusos-monarch-bms --strip-components=1
chmod +x /data/venusos-monarch-bms/setup
chmod +x /data/venusos-monarch-bms/service/run
bash -x /data/venusos-monarch-bms/setup install
```

## QML Settings Page

`qml/PageMonarchBms.qml` is included and reads/writes:

- `/Settings/IpAddress`
- `/Settings/Port`
- `/Settings/UnitId`
- `/Settings/Enabled`

And shows runtime state and key values:

- `/Status`, `/Status/LastError`, `/Connected`
- `/Status/Registers` (documents active Modbus register block)
- `/Dc/0/Voltage`, `/Dc/0/Current`, `/Soc`
- `/Info/MaxChargeCurrent`, `/Info/MaxDischargeCurrent`, `/Info/MaxChargeVoltage`

The current read target is:

- Modbus TCP endpoint from settings: `/Settings/IpAddress` + `/Settings/Port`
- Slave/device id from settings: `/Settings/UnitId`
- Register block: Input Registers `1` count `30`

## Recommended rename

To align with Venus package naming and future maintenance:

- Repository: `venusos-monarch-bms`
- Service package label: `VenusOS-Monarch-BMS`
- DBus service name: keep `com.victronenergy.battery.monarch` for continuity unless you need a clean break.
