#!/usr/bin/env python3
import os
import time
import struct
import sys

# --- FIX: Add Victron library path ---
# This is the correct path we found on your system
lib_path = '/opt/victronenergy/dbus-systemcalc-py/ext/velib_python'
sys.path.insert(0, lib_path)
# -------------------------------------

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

# NOTE: You will likely need to read from *multiple* register blocks.
# This original block is just for the static info.
INFO_START_REGISTER = 1
INFO_NUM_REGISTERS = 30
# TODO: Add your register blocks for LIVE DATA (Voltage, Current, SoC, Temp)
# TODO: Add your register blocks for ALARMS
#
# EXAMPLE:
# LIVE_START_REGISTER = 100
# LIVE_NUM_REGISTERS = 20
# ----------------------------

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
        # FIX: Set register=False to fix the "OUTDATED REGISTRATION" warning
        service = VeDbusService(DBUS_SERVICE_NAME, register=False)
        return service

    def _setup_dbus_paths(self):
        """Create and initialize the dbus service with all important paths."""
        # --- Management Paths ---
        self.service.add_path("/Mgmt/ProcessName", __file__)
        self.service.add_path("/Mgmt/ProcessVersion", "2.0 - Final Refactor")
        self.service.add_path("/Mgmt/Connection", f"ModbusTCP {BMS_IP}")

        # --- Device Info ---
        self.service.add_path("/DeviceInstance", 0)
        self.service.add_path("/ProductId", 0xB004)   # generic battery
        self.service.add_path("/ProductName", "Monarch BMS")
        self.service.add_path("/CustomName", "Monarch Battery")
        self.service.add_path("/Connected", 0)
        self.service.add_path("/Serial", None)
        self.service.add_path("/FirmwareVersion", None)
        self.service.add_path("/HardwareVersion", None)
        self.service.add_path("/Model", None)

        # --- Live Data ---
        self.service.add_path("/Soc", None)
        self.service.add_path("/Dc/0/Voltage", None)
        self.service.add_path("/Dc/0/Current", None)
        self.service.add_path("/Dc/0/Power", None)
        self.service.add_path("/Dc/0/Temperature", None)
        
        # --- Settings ---
        self.service.add_path("/Settings/HasTemperature", 1) # Set to 1 since we have a temp path

        # --- DVCC / Parameter Data ---
        self.service.add_path("/Info/MaxChargeCurrent", None)      # CCL
        self.service.add_path("/Info/MaxDischargeCurrent", None)   # DCL
        self.service.add_path("/Info/MaxChargeVoltage", None)
        self.service.add_path("/Info/BatteryLowVoltage", None)
        self.service.add_path("/Info/ChargeRequest", None)

        # --- Alarms (0=OK, 1=Warning, 2=Alarm) ---
        self.service.add_path("/Alarms/LowVoltage", 0)
        self.service.add_path("/Alarms/HighVoltage", 0)
        self.service.add_path("/Alarms/LowSoc", 0)
        self.service.add_path("/Alarms/HighChargeCurrent", 0)
        self.service.add_path("/Alarms/HighDischargeCurrent", 0)
        self.service.add_path("/Alarms/CellImbalance", 0)
        self.service.add_path("/Alarms/InternalFailure", 0)
        self.service.add_path("/Alarms/HighChargeTemperature", 0)
        self.service.add_path("/Alarms/LowChargeTemperature", 0)
        self.service.add_path("/Alarms/HighTemperature", 0)
        self.service.add_path("/Alarms/LowTemperature", 0)

        # --- History ---
        self.service.add_path("/History/ChargeCycles", None)
        self.service.add_path("/History/TotalAhDrawn", None)
        
        # --- Register the service *after* all paths are added ---
        self.service.register()

    def _read_bms_data(self):
        """
        Reads and decodes Modbus registers from BMS.
        This function will likely need to make MULTIPLE read calls
        to different register blocks.
        """
        try:
            if not self.client.connect():
                print(f"❌ Failed to connect to {BMS_IP}:{PORT}", file=sys.stderr)
                return None

            # -----------------------------------------------------------------
            # TODO: USER MUST EDIT THIS SECTION
            # -----------------------------------------------------------------
            # You must read all the different Modbus registers for your BMS.
            # The example below only reads the original "Info" block.
            # You need to add more read calls for Live Data, Alarms, etc.
            # -----------------------------------------------------------------

            # --- 1. Read INFO block ---
            response = self.client.read_input_registers(
                INFO_START_REGISTER, INFO_NUM_REGISTERS, unit=UNIT_ID
            )
            if response.isError():
                print(f"Error reading INFO registers: {response}", file=sys.stderr)
                return None
            
            regs = response.registers

            # --- Helper Functions ---
            def get_word(regs, index):
                return regs[index]

            def get_lword(regs, index):
                return (regs[index] << 16) | regs[index + 1]

            def get_real(regs, index):
                raw = struct.pack('>HH', regs[index], regs[index + 1])
                return round(struct.unpack('>f', raw)[0], 2)

            # --- 2. Populate known values from INFO block ---
            decoded = {
                "/Info/SerialNumber": get_lword(regs, 1),
                "/Info/HardwareVersion": get_lword(regs, 5),
                "/Info/FirmwareVersion": get_word(regs, 7),
                "/Info/Model": get_word(regs, 11),
                "/Info/MaxChargeCurrent": get_real(regs, 19),
                "/Info/MaxDischargeCurrent": get_real(regs, 21),
                "/Info/MaxChargeVoltage": get_real(regs, 23),
                "/Info/BatteryLowVoltage": get_real(regs, 25),
                "/Info/ChargeRequest": get_word(regs, 27),
            }

            # -----------------------------------------------------------------
            # TODO: READ YOUR OTHER MODBUS BLOCKS
            # -----------------------------------------------------------------
            # EXAMPLE:
            #
            # response_live = self.client.read_input_registers(
            #     LIVE_START_REGISTER, LIVE_NUM_REGISTERS, unit=UNIT_ID
            # )
            # if response_live.isError():
            #     print(f"Error reading LIVE registers: {response_live}", file=sys.stderr)
            #     return None
            #
            # live_regs = response_live.registers
            #
            # decoded["/Dc/0/Voltage"] = get_real(live_regs, 0)
            # decoded["/Dc/0/Current"] = get_real(live_regs, 2)
            # decoded["/Soc"] = get_word(live_regs, 4)
            # decoded["/Dc/0/Temperature"] = get_real(live_regs, 5)
            # decoded["/Alarms/LowVoltage"] = get_word(live_regs, 6)
            # decoded["/Alarms/HighVoltage"] = get_word(live_regs, 7)
            # ... etc
            # -----------------------------------------------------------------
            
            # --- Using Static Placeholders until TODO is complete ---
            # --- This ensures the GUI appears correctly ---
            decoded.setdefault("/Dc/0/Voltage", 53.2)
            decoded.setdefault("/Dc/0/Current", 0.0) # Negative for discharge
            decoded.setdefault("/Soc", 75.0)
            decoded.setdefault("/Dc/0/Temperature", 21.0)
            
            # --- Alarms (0=OK, 2=Alarm) ---
            decoded.setdefault("/Alarms/LowVoltage", 0)
            decoded.setdefault("/Alarms/HighVoltage", 0)
            decoded.setdefault("/Alarms/LowSoc", 0)
            # ... add all other alarms here, defaulting to 0
            
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

            # --- Update all DBus paths from our data dict ---
            self.service["/Connected"] = 1
            for path, value in data.items():
                if path in self.service:
                    self.service[path] = value

            # Calculate and update power
            # (Ensures power is calculated from live voltage/current)
            power = round(self.service["/Dc/0/Voltage"] * self.service["/Dc/0/Current"], 2)
            self.service["/Dc/0/Power"] = power

            # You can uncomment this for testing, but it's very noisy.
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
