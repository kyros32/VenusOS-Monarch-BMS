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
REGISTER_BLOCK_START = 1
REGISTER_BLOCK_COUNT = 30

LOG = logging.getLogger("venusos-monarch-bms")


def _float_be(regs, index):
    raw = struct.pack(">HH", regs[index], regs[index + 1])
    return struct.unpack(">f", raw)[0]


def _uint32_be(regs, index):
    return (regs[index] << 16) | regs[index + 1]


class VenusOsMonarchBmsService:
    def __init__(self):
        DBusGMainLoop(set_as_default=True)

        self._service = VeDbusService(SERVICE_NAME, register=False)
        self._modbus_client: Optional[ModbusTcpClient] = None
        self._last_ok_ts = 0
        self._last_error = ""

        # Persistent settings in com.victronenergy.settings
        self._settings = SettingsDevice(
            bus=None,
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
        self._service.add_path("/Mgmt/ProcessVersion", "1.1.0")
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
        self._service.add_path("/Status/Registers", f"input:{REGISTER_BLOCK_START}+{REGISTER_BLOCK_COUNT}")

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

    def _read_input(self, start, count):
        client = self._get_client()
        try:
            return client.read_input_registers(start, count, slave=int(self._settings["unit_id"]))
        except TypeError:
            return client.read_input_registers(start, count, unit=int(self._settings["unit_id"]))

    def _read_data(self) -> Optional[Dict[str, float]]:
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

        resp = self._read_input(REGISTER_BLOCK_START, REGISTER_BLOCK_COUNT)
        if resp.isError():
            self._last_error = f"Read error: {resp}"
            self._set_status(2, "Read failed", self._last_error)
            return None

        regs = resp.registers
        if len(regs) < 28:
            self._last_error = "Short register response"
            self._set_status(2, "Invalid response", self._last_error)
            return None

        data = {
            "/Serial": str(_uint32_be(regs, 1)),
            "/HardwareVersion": str(_uint32_be(regs, 5)),
            "/FirmwareVersion": str(regs[7]),
            "/Info/MaxChargeCurrent": round(_float_be(regs, 19), 2),
            "/Info/MaxDischargeCurrent": round(_float_be(regs, 21), 2),
            "/Info/MaxChargeVoltage": round(_float_be(regs, 23), 2),
            "/Info/BatteryLowVoltage": round(_float_be(regs, 25), 2),
            "/Info/ChargeRequest": int(regs[27]) if len(regs) > 27 else 0,
        }

        try:
            v = round(_float_be(regs, 13), 2)
            i = round(_float_be(regs, 15), 2)
            soc = round(_float_be(regs, 17), 2)
            if 0.0 < v < 1000.0:
                data["/Dc/0/Voltage"] = v
            if -2000.0 < i < 2000.0:
                data["/Dc/0/Current"] = i
            if 0.0 <= soc <= 100.0:
                data["/Soc"] = soc
        except Exception:
            pass

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
