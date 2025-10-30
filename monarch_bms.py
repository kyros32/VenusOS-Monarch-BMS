#!/usr/bin/env python3
import os
import time
import struct
from gi.repository import GLib
from pymodbus.client.sync import ModbusTcpClient
from vedbus import VeDbusService
from dbus.mainloop.glib import DBusGMainLoop

# ----------------------------
# Modbus Configuration
# ----------------------------
BMS_IP = "192.168.0.20"
PORT = 502
UNIT_ID = 154
START_REGISTER = 1
NUM_REGISTERS = 30

# ----------------------------
# Service Settings
# ----------------------------
DBUS_SERVICE_NAME = "com.victronenergy.battery.monarch"
UPDATE_INTERVAL = 5  # seconds

# ----------------------------
# Modbus client setup
# ----------------------------
client = ModbusTcpClient(BMS_IP, port=PORT)

def read_bms_registers():
    """Reads and decodes Modbus registers from BMS."""
    if not client.connect():
        print(f"❌ Failed to connect to {BMS_IP}:{PORT}")
        return None

    response = client.read_input_registers(START_REGISTER, NUM_REGISTERS, unit=UNIT_ID)
    client.close()

    if response.isError():
        print("Error reading registers:", response)
        return None

    regs = response.registers

    def get_word(index):
        return regs[index]

    def get_lword(index):
        return (regs[index] << 16) | regs[index + 1]

    def get_real(index):
        raw = struct.pack('>HH', regs[index], regs[index + 1])
        return round(struct.unpack('>f', raw)[0], 2)

    decoded = {
        "/Info/SerialNumber": get_lword(1),
        "/Info/HardwareVersion": get_lword(5),
        "/Info/FirmwareVersion": get_word(7),
        "/Info/Model": get_word(11),
        "/Dc/Battery/MaxChargeCurrent": get_real(19),
        "/Dc/Battery/MaxDischargeCurrent": get_real(21),
        "/Dc/Battery/MaxChargeVoltage": get_real(23),
        "/Info/BatteryLowVoltage": get_real(25),
        "/Info/ChargeRequest": get_word(27),
    }

    return decoded


# ----------------------------
# DBus Initialization
# ----------------------------
def create_dbus_service():
    """Create and initialize the dbus service with mandatory fields."""
    DBusGMainLoop(set_as_default=True)
    service = VeDbusService(DBUS_SERVICE_NAME)

    # --- Mandatory paths for battery service ---
    service.add_path("/Mgmt/ProcessName", __file__)
    service.add_path("/Mgmt/ProcessVersion", "1.0")
    service.add_path("/Mgmt/Connection", f"ModbusTCP {BMS_IP}")

    service.add_path("/DeviceInstance", 0)
    service.add_path("/ProductId", 0xB004)   # generic battery
    service.add_path("/ProductName", "Monarch BMS")
    service.add_path("/CustomName", "Monarch Battery")
    service.add_path("/Connected", 1)
    service.add_path("/Serial", "")
    service.add_path("/FirmwareVersion", "")
    service.add_path("/HardwareVersion", "")
    service.add_path("/Model", "")
    service.add_path("/Dc/0/Voltage", 0.0)
    service.add_path("/Dc/0/Current", 0.0)
    service.add_path("/Dc/0/Power", 0.0)
    service.add_path("/Dc/0/Temperature", 25.0)
    service.add_path("/Dc/Battery/MaxChargeCurrent", 0.0)
    service.add_path("/Dc/Battery/MaxDischargeCurrent", 0.0)
    service.add_path("/Dc/Battery/MaxChargeVoltage", 0.0)
    service.add_path("/Info/BatteryLowVoltage", 0.0)
    service.add_path("/Info/ChargeRequest", 0)

    return service


# ----------------------------
# Periodic Update
# ----------------------------
def update_dbus():
    """Reads Modbus and updates dbus values."""
    data = read_bms_registers()
    if data is None:
        print("⚠️ No data retrieved")
        return True  # keep loop running

    # Update DBus paths
    service["/Serial"] = str(data["/Info/SerialNumber"])
    service["/FirmwareVersion"] = str(data["/Info/FirmwareVersion"])
    service["/HardwareVersion"] = str(data["/Info/HardwareVersion"])
    service["/Model"] = str(data["/Info/Model"])

    service["/Dc/Battery/MaxChargeCurrent"] = data["/Dc/Battery/MaxChargeCurrent"]
    service["/Dc/Battery/MaxDischargeCurrent"] = data["/Dc/Battery/MaxDischargeCurrent"]
    service["/Dc/Battery/MaxChargeVoltage"] = data["/Dc/Battery/MaxChargeVoltage"]
    service["/Info/BatteryLowVoltage"] = data["/Info/BatteryLowVoltage"]
    service["/Info/ChargeRequest"] = data["/Info/ChargeRequest"]

    # Derived example values (optional)
    service["/Dc/0/Voltage"] = data["/Dc/Battery/MaxChargeVoltage"]
    service["/Dc/0/Current"] = data["/Dc/Battery/MaxChargeCurrent"] / 2  # Example placeholder
    service["/Dc/0/Power"] = round(
        service["/Dc/0/Voltage"] * service["/Dc/0/Current"], 2
    )

    print("🔄 DBus updated:", data)
    return True


if __name__ == "__main__":
    service = create_dbus_service()
    GLib.timeout_add_seconds(UPDATE_INTERVAL, update_dbus)
    print(f"🚀 DBus service started: {DBUS_SERVICE_NAME}")
    GLib.MainLoop().run()
