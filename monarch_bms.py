#!/usr/bin/env python3
import os
import time
import struct
import sys  # Added for sys.stderr
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

class DbusMonarchBms:
    def __init__(self):
        self.client = ModbusTcpClient(BMS_IP, port=PORT)
        self.service = self._setup_dbus_service()
        self._setup_dbus_paths()

        # Start the main update loop
        GLib.timeout_add_seconds(UPDATE_INTERVAL, self._update)
        print(f"🚀 DBus service started: {DBUS_SERVICE_NAME}")

    def _setup_dbus_service(self):
        """Initializes and returns the DBus service."""
        DBusGMainLoop(set_as_default=True)
        service = VeDbusService(DBUS_SERVICE_NAME)
        return service

    def _setup_dbus_paths(self):
        """Create and initialize the dbus service with mandatory fields."""
        # --- Mandatory paths for battery service ---
        self.service.add_path("/Mgmt/ProcessName", __file__)
        self.service.add_path("/Mgmt/ProcessVersion", "1.2")
        self.service.add_path("/Mgmt/Connection", f"ModbusTCP {BMS_IP}")

        self.service.add_path("/DeviceInstance", 0)
        self.service.add_path("/ProductId", 0xB004)   # generic battery
        self.service.add_path("/ProductName", "Monarch BMS")
        self.service.add_path("/CustomName", "Monarch Battery")
        self.service.add_path("/Connected", 0)  # Will be set to 1 on successful read
        self.service.add_path("/Serial", "")
        self.service.add_path("/FirmwareVersion", "")
        self.service.add_path("/HardwareVersion", "")
        self.service.add_path("/Model", "")

        # --- Live Data (Required for GUI) ---
        self.service.add_path("/Soc", None) # CRITICAL: State of Charge
        self.service.add_path("/Dc/0/Voltage", None)
        self.service.add_path("/Dc/0/Current", None)
        self.service.add_path("/Dc/0/Power", None)
        self.service.add_path("/Dc/0/Temperature", None)

        # --- DVCC / Parameter Data (From original script) ---
        self.service.add_path("/Dc/Battery/MaxChargeCurrent", None)
        self.service.add_path("/Dc/Battery/MaxDischargeCurrent", None)
        self.service.add_path("/Dc/Battery/MaxChargeVoltage", None)
        self.service.add_path("/Info/BatteryLowVoltage", None)
        self.service.add_path("/Info/ChargeRequest", None)

    def _read_bms_data(self):
        """Reads and decodes Modbus registers from BMS."""
        try:
            if not self.client.connect():
                print(f"❌ Failed to connect to {BMS_IP}:{PORT}", file=sys.stderr)
                return None

            response = self.client.read_input_registers(START_REGISTER, NUM_REGISTERS, unit=UNIT_ID)

            if response.isError():
                print(f"Error reading registers: {response}", file=sys.stderr)
                return None

            regs = response.registers

            def get_word(index):
                return regs[index]

            def get_lword(index):
                return (regs[index] << 16) | regs[index + 1]

            def get_real(index):
                raw = struct.pack('>HH', regs[index], regs[index + 1])
                return round(struct.unpack('>f', raw)[0], 2)

            # --- Populate known values ---
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

            # -----------------------------------------------------------------
            # TODO: USER MUST EDIT THIS SECTION
            # -----------------------------------------------------------------
            # The values below are static placeholders. This is to make the
            # "Parameters" tab appear in the GUI.
            #
            # You MUST find the correct Modbus register addresses for your BMS
            # for live Voltage, Current, SoC, and Temperature.
            #
            # Then, replace the hard-coded values (like 53.2 or 75.0)
            # with real register-reading functions, e.g.:
            #
            # decoded["/Dc/0/Voltage"] = get_real(31)
            # decoded["/Dc/0/Current"] = get_real(33)
            # decoded["/Soc"] = get_word(35)
            # decoded["/Dc/0/Temperature"] = get_real(37)
            # -----------------------------------------------------------------
            decoded["/Dc/0/Voltage"] = 53.2
            decoded["/Dc/0/Current"] = 0.0
            decoded["/Soc"] = 75.0
            decoded["/Dc/0/Temperature"] = 20.0
            # -----------------------------------------------------------------
            # END OF TODO SECTION
            # -----------------------------------------------------------------

            return decoded

        except Exception as e:
            print(f"An exception occurred during Modbus read: {e}", file=sys.stderr)
            return None
        finally:
            if self.client.is_socket_open():
                self.client.close()

    def _update(self):
        """Periodically reads Modbus and updates dbus values."""
        try:
            data = self._read_bms_data()

            if data is None:
                print("⚠️ No data retrieved from BMS. Setting /Connected = 0", file=sys.stderr)
                self.service["/Connected"] = 0
                return True  # Keep loop running

            # --- Update all DBus paths ---
            self.service["/Connected"] = 1

            for path, value in data.items():
                if path in self.service:
                    self.service[path] = value

            # Calculate and update power
            power = round(self.service["/Dc/0/Voltage"] * self.service["/Dc/0/Current"], 2)
            self.service["/Dc/0/Power"] = power

            # You can uncomment this line for testing, but it's best to 
            # leave it commented out for normal operation to avoid spamming logs.
            # print("🔄 DBus updated successfully.")

        except Exception as e:
            print(f"Error in update loop: {e}", file=sys.stderr)

        return True  # Keep loop running

def main():
    """Main entry point for the script."""
    try:
        DbusMonarchBms()
        GLib.MainLoop().run()
    except Exception as e:
        print(f"Fatal error in main: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
