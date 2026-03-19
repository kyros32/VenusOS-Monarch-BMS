import QtQuick 2
import com.victron.velib 1.0
import "utils.js" as Utils

MbPage {
    id: root
    title: qsTr("Monarch BMS")

    property string svc: "com.victronenergy.battery.monarch"
    property string setSvc: "com.victronenergy.settings/Settings/VenusOsMonarchBms"

    model: VisibleItemModel {
        // --- Settings (editable where supported) ---
        MbSwitch { name: qsTr("Enabled"); bind: Utils.path(setSvc, "/Enabled") }
        MbEditBoxIp {
            description: qsTr("IP address")
            show: item.valid
            item: VBusItem { bind: Utils.path(setSvc, "/IpAddress") }
        }
        MbSpinBox {
            description: qsTr("Port")
            show: item.valid
            item {
                bind: Utils.path(setSvc, "/Port")
                decimals: 0
                step: 1
            }
        }
        MbSpinBox {
            description: qsTr("Unit ID")
            show: item.valid
            item {
                bind: Utils.path(setSvc, "/UnitId")
                decimals: 0
                step: 1
            }
        }

        // --- Status ---
        MbItemValue { description: qsTr("Status"); item: VBusItem { bind: svc + "/Status" } }
        MbItemValue { description: qsTr("Connected"); item: VBusItem { bind: svc + "/Connected" } }
        MbItemValue { description: qsTr("Last Error"); item: VBusItem { bind: svc + "/Status/LastError" } }

        // --- Battery line ---
        MbItemValue { description: qsTr("Voltage (V)"); item: VBusItem { bind: svc + "/Dc/0/Voltage" } }
        MbItemValue { description: qsTr("Current (A)"); item: VBusItem { bind: svc + "/Dc/0/Current" } }
        MbItemValue { description: qsTr("Power (W)"); item: VBusItem { bind: svc + "/Dc/0/Power" } }
        MbItemValue { description: qsTr("SOC"); item: VBusItem { bind: svc + "/Soc" } }
        MbItemValue { description: qsTr("Temperature"); item: VBusItem { bind: svc + "/Dc/0/Temperature" } }
        MbItemValue { description: qsTr("Time to Go"); item: VBusItem { bind: svc + "/TimeToGo" } }

        // --- Limits ---
        MbItemValue { description: qsTr("Max Chg Curr (A)"); item: VBusItem { bind: svc + "/Info/MaxChargeCurrent" } }
        MbItemValue { description: qsTr("Max Dchg Curr (A)"); item: VBusItem { bind: svc + "/Info/MaxDischargeCurrent" } }
        MbItemValue { description: qsTr("Max Chg V"); item: VBusItem { bind: svc + "/Info/MaxChargeVoltage" } }
        MbItemValue { description: qsTr("Low V"); item: VBusItem { bind: svc + "/Info/BatteryLowVoltage" } }
        MbItemValue { description: qsTr("Chg Request"); item: VBusItem { bind: svc + "/Info/ChargeRequest" } }

        // --- Details ---
        MbItemValue { description: qsTr("Nr. of cells"); item: VBusItem { bind: svc + "/System/NrOfCellsPerBattery" } }
        MbItemValue { description: qsTr("Installed capacity (Ah)"); item: VBusItem { bind: svc + "/Info/InstalledCapacity" } }
        MbItemValue { description: qsTr("Available capacity (Ah)"); item: VBusItem { bind: svc + "/Info/AvailableCapacity" } }
        MbItemValue { description: qsTr("State of health (%)"); item: VBusItem { bind: svc + "/Soh" } }
        MbItemValue { description: qsTr("System switch"); item: VBusItem { bind: svc + "/System/Switch" } }
        MbItemValue { description: qsTr("Serial"); item: VBusItem { bind: svc + "/Serial" } }
        MbItemValue { description: qsTr("HW Ver"); item: VBusItem { bind: svc + "/HardwareVersion" } }
        MbItemValue { description: qsTr("FW Ver"); item: VBusItem { bind: svc + "/FirmwareVersion" } }

        // --- Alarms ---
        MbItemValue { description: qsTr("Alarm State"); item: VBusItem { bind: svc + "/Alarms/State" } }
        MbItemValue { description: qsTr("Active"); item: VBusItem { bind: svc + "/Alarms/Active" } }
        MbItemValue { description: qsTr("Low V Alm"); item: VBusItem { bind: svc + "/Alarms/LowVoltage" } }
        MbItemValue { description: qsTr("High V Alm"); item: VBusItem { bind: svc + "/Alarms/HighVoltage" } }
        MbItemValue { description: qsTr("Low SOC Alm"); item: VBusItem { bind: svc + "/Alarms/LowSoc" } }
        MbItemValue { description: qsTr("High T Alm"); item: VBusItem { bind: svc + "/Alarms/HighTemperature" } }
        MbItemValue { description: qsTr("Low T Alm"); item: VBusItem { bind: svc + "/Alarms/LowTemperature" } }
        MbItemValue { description: qsTr("Low Chg T Alm"); item: VBusItem { bind: svc + "/Alarms/LowChargeTemperature" } }
        MbItemValue { description: qsTr("High Chg T Alm"); item: VBusItem { bind: svc + "/Alarms/HighChargeTemperature" } }
        MbItemValue { description: qsTr("Cell Imbalance Alm"); item: VBusItem { bind: svc + "/Alarms/CellImbalance" } }
        MbItemValue { description: qsTr("Internal Failure Alm"); item: VBusItem { bind: svc + "/Alarms/InternalFailure" } }
    }
}
