# VenusOS-Monarch-BMS

A Victron Venus OS plugin that bridges a **Monarch BMS** over Modbus TCP to the Victron DBus battery interface. The battery appears as a managed battery in the GX UI and supports DVCC (charge control).

---

## Overview

| Item | Value |
|------|-------|
| **DBus service** | `com.victronenergy.battery.monarch` |
| **Product ID** | `0xB090` |
| **Protocol** | Modbus TCP (read-only) |
| **Update interval** | 2 seconds |
| **Package name** | `VenusOS-Monarch-BMS` |

The service runs as a runit daemon, polls the BMS via Modbus TCP, and publishes values to DBus. Venus treats it like a CAN-bus battery. Settings (IP, port, unit ID) are stored in `com.victronenergy.settings` and survive reboots.

---

## Architecture

```
┌─────────────────┐     Modbus TCP      ┌──────────────┐     DBus      ┌─────────────────┐
│  Monarch BMS    │ ◄────────────────── │  Service     │ ────────────► │  Venus GX UI   │
│  (Modbus slave) │   read input regs   │  (Python)    │  battery.*    │  DVCC, gauges  │
└─────────────────┘                     └──────────────┘               └─────────────────┘
                                                 │
                                                 ▼
                                        ┌─────────────────┐
                                        │  Settings       │
                                        │  (IP, port, ID) │
                                        └─────────────────┘
```

- **Read-only:** No Modbus writes; only input registers are read.
- **Per-field mapping:** Each DBus path has its own Modbus register(s).
- **Plausibility checks:** Voltage, current, SOC, temperature are validated before publishing.

---

## Complete Mapping Reference

### Modbus → DBus Path Mapping

| DBus Path | Modbus Reg (1-based) | Type | Registers | Description |
|-----------|----------------------|------|-----------|-------------|
| `/Serial` | 1 | uint32 | 2 | BMS serial number |
| `/HardwareVersion` | 5 | uint32 | 2 | Hardware version |
| `/FirmwareVersion` | 7 | uint16 | 1 | Firmware version |
| `/System/NrOfCellsPerBattery` | 9 | uint16 | 1 | Number of cells |
| `/Dc/0/Voltage` | 13 | float32 | 2 | Pack voltage (V) |
| `/Dc/0/Current` | 15 | float32 | 2 | Current (A, + charge, − discharge) |
| `/Soc` | 17 | float32 | 2 | State of charge (%) |
| `/Info/MaxChargeCurrent` | 19 | float32 | 2 | Charge current limit (A) |
| `/Info/MaxDischargeCurrent` | 21 | float32 | 2 | Discharge current limit (A) |
| `/Info/MaxChargeVoltage` | 23 | float32 | 2 | Max charge voltage (V) |
| `/Info/BatteryLowVoltage` | 25 | float32 | 2 | Low voltage cutoff (V) |
| `/Info/ChargeRequest` | 27 | uint16 | 1 | Charge request (0/1) |
| `/Dc/0/Temperature` | 29 | float32 | 2 | Pack temperature (°C) |
| `/TimeToGo` | 31 | float32 | 2 | Time to empty/full (min) |
| `/Alarms/LowVoltage` | 33 | uint16 | 1 | 0=OK, 1=Warning, 2=Alarm |
| `/Alarms/HighVoltage` | 34 | uint16 | 1 | 0=OK, 1=Warning, 2=Alarm |
| `/Alarms/LowSoc` | 35 | uint16 | 1 | 0=OK, 1=Warning, 2=Alarm |
| `/Alarms/HighTemperature` | 36 | uint16 | 1 | 0=OK, 1=Warning, 2=Alarm |
| `/Alarms/LowTemperature` | 37 | uint16 | 1 | 0=OK, 1=Warning, 2=Alarm |

### Modbus Details

- **Function:** Read Input Registers (FC 0x04)
- **Byte order:** Big-endian for float32 and uint32
- **Register numbering:** 1-based (e.g. reg 1 = first input register)
- **Float32:** Two consecutive 16-bit registers, high word first

**Address adjustment:** Edit `REGISTER_MAP` in `venusos_monarch_bms_service.py` to match your Monarch BMS protocol. Registers 29–37 are placeholders; verify against your BMS documentation.

### Derived / Runtime Paths (Not from Modbus)

| DBus Path | Source |
|-----------|--------|
| `/Dc/0/Power` | Calculated: Voltage × Current |
| `/Alarms/State` | Max of all alarm levels |
| `/Alarms/Active` | Comma-separated list of active alarm names |
| `/Connected` | 1 when Modbus read succeeds |
| `/Status` | Service state: "Running", "Disabled", "Connection failed", etc. |
| `/Status/LastError` | Last error message |
| `/Status/LastUpdateTs` | Unix timestamp of last successful update |
| `/Io/AllowToCharge` | From `/Info/ChargeRequest` |
| `/Io/AllowToDischarge` | Always 1 when connected |

### Settings Paths (Persistent)

| Path | Type | Default | Description |
|------|------|---------|-------------|
| `com.victronenergy.settings/Settings/VenusOsMonarchBms/IpAddress` | string | `192.168.0.20` | BMS IP address |
| `com.victronenergy.settings/Settings/VenusOsMonarchBms/Port` | int | 502 | Modbus TCP port |
| `com.victronenergy.settings/Settings/VenusOsMonarchBms/UnitId` | int | 154 | Modbus slave/unit ID |
| `com.victronenergy.settings/Settings/VenusOsMonarchBms/Enabled` | int | 1 | 0=off, 1=on |
| `com.victronenergy.settings/Settings/VenusOsMonarchBms/DeviceInstance` | int | 41 | Venus device instance |

---

## Installation

### Prerequisites

- Victron Cerbo GX or compatible Venus device
- SetupHelper installed (Package Manager)
- Monarch BMS on the same network with Modbus TCP enabled

### Via Package Manager (kwindrem)

1. **Settings** → **Package Manager** → **Inactive packages** → **New**
2. Enter:
   - **Package name:** `VenusOS-Monarch-BMS`
   - **GitHub user:** `kyros32` (or your fork)
   - **Branch/tag:** `main`
3. **Save** → **Download** → **Install**

### Manual Install (SSH)

```bash
rm -rf /data/VenusOS-Monarch-BMS
mkdir -p /data/VenusOS-Monarch-BMS
wget -O - https://github.com/kyros32/VenusOS-Monarch-BMS/archive/refs/heads/main.tar.gz | tar -xzf - -C /data/VenusOS-Monarch-BMS --strip-components=1
chmod +x /data/VenusOS-Monarch-BMS/setup
chmod +x /data/VenusOS-Monarch-BMS/service/run
bash -x /data/VenusOS-Monarch-BMS/setup install
```

---

## Configuration

1. **Settings** → **Monarch BMS** (or via Settings menu)
2. Set **IP** to the BMS IP address
3. Set **Port** (default 502)
4. Set **Unit ID** (default 154)
5. Enable the service

---

## Repository Structure

```
VenusOS-Monarch-BMS/
├── README.md
├── setup
├── version
├── venusos_monarch_bms_service.py
├── service/
│   └── run
└── qml/
    └── PageMonarchBms.qml
```

| File | Purpose |
|------|---------|
| `setup` | SetupHelper install/uninstall script; patches QML menu |
| `venusos_monarch_bms_service.py` | Main daemon; contains `REGISTER_MAP` |
| `service/run` | Runit entrypoint |
| `qml/PageMonarchBms.qml` | Settings and status page |

---

## QML Page Layout

The Monarch BMS page shows:

- **Settings:** Enabled (toggle), IP address (MbEditBoxIp), Port and Unit ID (MbSpinBox)
- **Status:** Status, Connected, Last Error
- **Battery line:** Voltage, Current, Power, SOC, Temperature, Time to Go
- **Limits:** Max charge/discharge current, max charge voltage, low voltage, charge request
- **Device info:** Serial, HW version, FW version, cell count
- **Alarms:** Alarm state, active alarms, individual alarm flags

---

## Troubleshooting

### Service not starting

- **Check runit:** `sv status dbus-monarch-bms` (or `VenusOS-Monarch-BMS` depending on SetupHelper)
- **Logs:** `tail -f /var/log/dbus-monarch-bms/current` or `/service/dbus-monarch-bMS/log/main/current`

### Blank QML page / "MbItemEdit is not a type" / "MbItemNumeric is not a type"

- Venus (einstein) does not provide `MbItemEdit` or `MbItemNumeric`. IP uses `MbEditBoxIp`, Port and Unit ID use `MbSpinBox` (all editable).

### No data / Connection failed

- Verify BMS IP, port, and unit ID
- Check network: `ping <BMS_IP>`
- Run manually: `cd /data/VenusOS-Monarch-BMS && /usr/bin/python3 venusos_monarch_bms_service.py`

### Wrong values

- **Adjust `REGISTER_MAP`** in `venusos_monarch_bms_service.py` to match your Monarch BMS protocol. Registers 29–37 (temperature, alarms) are placeholders.

### DBus not visible

- `dbus-spy` to inspect `com.victronenergy.battery.monarch`
- Ensure service is enabled and BMS is reachable

---

## Manual Run

```bash
cd /data/VenusOS-Monarch-BMS
/usr/bin/python3 venusos_monarch_bms_service.py
```

Stop with Ctrl+C.

---

## Version History

- **v1.1.0** – Full register map (temp, alarms, TimeToGo, cells), compact QML, detailed README
