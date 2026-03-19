#!/usr/bin/env python3
import sys
import time
import struct
import logging
from typing import Dict, Optional

# VenusOS Python helpers
VELIB_PATH = "/opt/victronenergy/dbus-systemcalc-py/ext/velib_python"
if VELIB_PATH not in sys.path:
    sys.path.insert(0, VELIB_PATH)

from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop
import dbus
from vedbus import VeDbusService
from settingsdevice import SettingsDevice

try:
    # VenusOS ships different pymodbus majors across firmware versions.
    from pymodbus.client import ModbusTcpClient
except Exception:
    from pymodbus.client.sync import ModbusTcpClient


SERVICE_NAME = "com.victronenergy.battery.monarch"
PRODUCT_NAME = "VenusOS Monarch BMS"
PRODUCT_ID = 0xB090
UPDATE_INTERVAL_SECONDS = 2
DEFAULT_DEVICE_INSTANCE = 41

# Block read: single request for registers 0..36 (1-based 1..37). Monarch BMS may close
# connection after each request; one block read avoids multiple round-trips.
REGISTER_BLOCK_START = 0  # 0-based
REGISTER_BLOCK_COUNT = 37

# Per-field Modbus register map (address=1-based Modbus register, type=uint16|uint32|float32).
# Alarm values: 0=OK, 1=Warning, 2=Alarm. Adjust addresses to match your Monarch BMS protocol.
REGISTER_MAP = {
    "/Serial": (1, "uint32"),
    "/HardwareVersion": (5, "uint32"),
    "/FirmwareVersion": (7, "uint16"),
    "/System/NrOfCellsPerBattery": (9, "uint16"),
    "/Dc/0/Voltage": (13, "float32"),
    "/Dc/0/Current": (15, "float32"),
    "/Soc": (17, "float32"),
    "/Info/MaxChargeCurrent": (19, "float32"),
    "/Info/MaxDischargeCurrent": (21, "float32"),
    "/Info/MaxChargeVoltage": (23, "float32"),
    "/Info/BatteryLowVoltage": (25, "float32"),
    "/Info/ChargeRequest": (27, "uint16"),
    "/Dc/0/Temperature": (29, "float32"),
    "/TimeToGo": (31, "float32"),
    "/Alarms/LowVoltage": (33, "uint16"),
    "/Alarms/HighVoltage": (34, "uint16"),
    "/Alarms/LowSoc": (35, "uint16"),
    "/Alarms/HighTemperature": (36, "uint16"),
    "/Alarms/LowTemperature": (37, "uint16"),
}

LOG = logging.getLogger("venusos-monarch-bms")


def _decode_regs(regs, dtype):
    if dtype == "uint16":
        return regs[0]
    if dtype == "uint32":
        return (regs[0] << 16) | regs[1]
    if dtype == "float32":
        raw = struct.pack(">HH", regs[0], regs[1])
        return struct.unpack(">f", raw)[0]
    return None


class VenusOsMonarchBmsService:
    def __init__(self):
        DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()

        self._service = VeDbusService(SERVICE_NAME, register=False)
        self._modbus_client: Optional[ModbusTcpClient] = None
        self._last_ok_ts = 0
        self._last_error = ""

        # Persistent settings in com.victronenergy.settings
        self._settings = SettingsDevice(
            bus=bus,
            supportedSettings={
                "ip_address": ["/Settings/VenusOsMonarchBms/IpAddress", "192.168.0.20", 0, 0],
                "port": ["/Settings/VenusOsMonarchBms/Port", 502, 1, 65535],
                "unit_id": ["/Settings/VenusOsMonarchBms/UnitId", 154, 0, 255],
                "device_instance": [
                    "/Settings/VenusOsMonarchBms/DeviceInstance",
                    DEFAULT_DEVICE_INSTANCE,
                    0,
                    255,
                ],
                "enabled": ["/Settings/VenusOsMonarchBms/Enabled", 1, 0, 1],
            },
            eventCallback=self._handle_setting_change,
        )

        self._setup_paths()
        self._service.register()

        GLib.timeout_add_seconds(UPDATE_INTERVAL_SECONDS, self._update)
        LOG.info("Service started: %s", SERVICE_NAME)

    def _setup_paths(self):
        self._service.add_path("/Mgmt/ProcessName", __file__)
        self._service.add_path("/Mgmt/ProcessVersion", "1.2.0")
        self._service.add_path("/Mgmt/Connection", "ModbusTCP")
        self._service.add_path("/DeviceInstance", int(self._settings["device_instance"]))
        self._service.add_path("/ProductId", PRODUCT_ID)
        self._service.add_path("/ProductName", PRODUCT_NAME)
        self._service.add_path("/CustomName", PRODUCT_NAME)
        self._service.add_path("/FirmwareVersion", None)
        self._service.add_path("/HardwareVersion", None)
        self._service.add_path("/Serial", None)
        self._service.add_path("/Connected", 0)

        # User-configurable settings for QML
        self._service.add_path(
            "/Settings/IpAddress",
            self._settings["ip_address"],
            writeable=True,
            onchangecallback=self._on_dbus_setting_changed,
        )
        self._service.add_path(
            "/Settings/Port",
            int(self._settings["port"]),
            writeable=True,
            onchangecallback=self._on_dbus_setting_changed,
        )
        self._service.add_path(
            "/Settings/UnitId",
            int(self._settings["unit_id"]),
            writeable=True,
            onchangecallback=self._on_dbus_setting_changed,
        )
        self._service.add_path(
            "/Settings/Enabled",
            int(self._settings["enabled"]),
            writeable=True,
            onchangecallback=self._on_dbus_setting_changed,
        )

        # Diagnostics/state for GUI
        self._service.add_path("/State", 0)  # 0=idle/disconnected, 1=running, 2=error
        self._service.add_path("/Status", "Starting")
        self._service.add_path("/Status/LastError", "")
        self._service.add_path("/Status/LastUpdateTs", 0)

        # Battery values
        self._service.add_path("/Soc", None)
        self._service.add_path("/Dc/0/Voltage", None)
        self._service.add_path("/Dc/0/Current", None)
        self._service.add_path("/Dc/0/Power", None)
        self._service.add_path("/Dc/0/Temperature", None)
        self._service.add_path("/Info/MaxChargeCurrent", None)
        self._service.add_path("/Info/MaxDischargeCurrent", None)
        self._service.add_path("/Info/MaxChargeVoltage", None)
        self._service.add_path("/Info/BatteryLowVoltage", None)
        self._service.add_path("/Info/ChargeRequest", 0)
        self._service.add_path("/TimeToGo", None)
        self._service.add_path("/System/NrOfCellsPerBattery", None)
        self._service.add_path("/System/NrOfModulesOnline", 1)
        self._service.add_path("/System/NrOfModulesOffline", 0)
        self._service.add_path("/System/NrOfModulesBlockingCharge", 0)
        self._service.add_path("/System/NrOfModulesBlockingDischarge", 0)
        self._service.add_path("/Io/AllowToCharge", 1)
        self._service.add_path("/Io/AllowToDischarge", 1)
        self._service.add_path("/Io/AllowToBalance", 0)

        # Alarm defaults, 0 = no alarm
        self._service.add_path("/Alarms/LowVoltage", 0)
        self._service.add_path("/Alarms/HighVoltage", 0)
        self._service.add_path("/Alarms/LowSoc", 0)
        self._service.add_path("/Alarms/HighTemperature", 0)
        self._service.add_path("/Alarms/LowTemperature", 0)
        self._service.add_path("/Alarms/State", 0)
        self._service.add_path("/Alarms/Active", "")

    def _set_status(self, state: int, msg: str, err: str = ""):
        self._service["/State"] = state
        self._service["/Status"] = msg
        self._service["/Status/LastError"] = err

    def _handle_setting_change(self, setting, old, new):
        _ = (setting, old)
        self._service["/Settings/IpAddress"] = self._settings["ip_address"]
        self._service["/Settings/Port"] = int(self._settings["port"])
        self._service["/Settings/UnitId"] = int(self._settings["unit_id"])
        self._service["/Settings/Enabled"] = int(self._settings["enabled"])
        self._service["/DeviceInstance"] = int(self._settings["device_instance"])
        self._close_client()
        LOG.info("Setting changed, forcing reconnect. New value: %s", new)

    def _on_dbus_setting_changed(self, path, value):
        if path == "/Settings/IpAddress":
            self._settings["ip_address"] = str(value)
        elif path == "/Settings/Port":
            self._settings["port"] = int(value)
        elif path == "/Settings/UnitId":
            self._settings["unit_id"] = int(value)
        elif path == "/Settings/Enabled":
            self._settings["enabled"] = 1 if int(value) else 0
        self._close_client()
        return True

    def _close_client(self):
        try:
            if self._modbus_client:
                self._modbus_client.close()
        except Exception:
            pass
        self._modbus_client = None

    def _get_client(self) -> ModbusTcpClient:
        if self._modbus_client is None:
            self._modbus_client = ModbusTcpClient(
                host=str(self._settings["ip_address"]),
                port=int(self._settings["port"]),
                timeout=1.0,
            )
        return self._modbus_client

    def _read_data(self) -> Optional[Dict]:
        if int(self._settings["enabled"]) == 0:
            self._set_status(0, "Disabled")
            return None

        client = self._get_client()
        if not client.connect():
            self._last_error = (
                f"Connect failed {self._settings['ip_address']}:{self._settings['port']}"
            )
            self._set_status(2, "Connection failed", self._last_error)
            return None

        # Single block read: avoids connection drops when BMS closes after each request
        unit_id = int(self._settings["unit_id"])
        try:
            resp = client.read_input_registers(
                REGISTER_BLOCK_START, REGISTER_BLOCK_COUNT, slave=unit_id
            )
        except TypeError:
            resp = client.read_input_registers(
                REGISTER_BLOCK_START, count=REGISTER_BLOCK_COUNT, slave=unit_id
            )

        client.close()
        self._modbus_client = None

        if resp.isError():
            self._last_error = f"Read error: {resp}"
            self._set_status(2, "Read failed", self._last_error)
            return None

        regs = resp.registers
        if len(regs) < REGISTER_BLOCK_COUNT:
            self._last_error = f"Short read: got {len(regs)}, need {REGISTER_BLOCK_COUNT}"
            self._set_status(2, "Read failed", self._last_error)
            return None

        data = {}
        for path, (addr_1based, dtype) in REGISTER_MAP.items():
            idx = addr_1based - 1
            count = 2 if dtype in ("uint32", "float32") else 1
            if idx + count > len(regs):
                continue
            val = _decode_regs(regs[idx : idx + count], dtype)
            if val is not None:
                if dtype in ("uint16", "uint32"):
                    if path in ("/Serial", "/HardwareVersion", "/FirmwareVersion"):
                        data[path] = str(val)
                    elif path.startswith("/Alarms/"):
                        data[path] = int(val) & 0xFFFF
                    else:
                        data[path] = int(val)
                else:
                    v = round(float(val), 2)
                    if path == "/Dc/0/Voltage" and not (0.0 < v < 1000.0):
                        continue
                    if path == "/Dc/0/Current" and not (-2000.0 < v < 2000.0):
                        continue
                    if path == "/Soc" and not (0.0 <= v <= 100.0):
                        continue
                    if path == "/Dc/0/Temperature" and not (-50.0 <= v <= 100.0):
                        continue
                    if path == "/TimeToGo" and v < 0:
                        continue
                    data[path] = v

        if not data:
            self._last_error = "No valid data decoded"
            self._set_status(2, "Decode failed", self._last_error)
            return None
        return data

    def _update(self):
        try:
            data = self._read_data()
            if data is None:
                self._service["/Connected"] = 0
                return True

            for path, value in data.items():
                if path in self._service:
                    self._service[path] = value

            v = self._service["/Dc/0/Voltage"]
            i = self._service["/Dc/0/Current"]
            if v is not None and i is not None:
                self._service["/Dc/0/Power"] = round(v * i, 2)

            self._service["/Connected"] = 1
            charge_request = int(self._service["/Info/ChargeRequest"] or 0)
            self._service["/Io/AllowToCharge"] = 1 if charge_request else 0
            self._service["/Io/AllowToDischarge"] = 1

            # Build alarm summary expected by UI.
            alarm_paths = [
                "/Alarms/LowVoltage",
                "/Alarms/HighVoltage",
                "/Alarms/LowSoc",
                "/Alarms/HighTemperature",
                "/Alarms/LowTemperature",
            ]
            active_alarms = []
            max_alarm_level = 0
            for ap in alarm_paths:
                level = int(self._service[ap] or 0)
                if level > 0:
                    active_alarms.append(ap.split("/")[-1])
                if level > max_alarm_level:
                    max_alarm_level = level
            self._service["/Alarms/State"] = max_alarm_level
            self._service["/Alarms/Active"] = ",".join(active_alarms)

            self._last_ok_ts = int(time.time())
            self._service["/Status/LastUpdateTs"] = self._last_ok_ts
            self._set_status(1, "Running")
        except Exception as exc:
            self._service["/Connected"] = 0
            self._last_error = str(exc)
            self._set_status(2, "Exception", self._last_error)
            LOG.exception("Update loop error")

        return True


def configure_logging():
    level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )


def main():
    configure_logging()
    VenusOsMonarchBmsService()
    GLib.MainLoop().run()


if __name__ == "__main__":
    main()
