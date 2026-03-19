import QtQuick 2.0
import com.victron.velib 1.0

MbPage {
    id: root
    title: qsTr("Monarch BMS")

    property string svc: "com.victronenergy.battery.monarch"

    // Pre-declare bindings for stability (mirrors SolarEdge example style).
    VBusItem { id: enabledItem; bind: svc + "/Settings/Enabled" }
    VBusItem { id: statusItem; bind: svc + "/Status" }
    VBusItem { id: lastErrorItem; bind: svc + "/Status/LastError" }
    VBusItem { id: connectedItem; bind: svc + "/Connected" }
    VBusItem { id: registersItem; bind: svc + "/Status/Registers" }

    VBusItem { id: ipItem; bind: svc + "/Settings/IpAddress" }
    VBusItem { id: portItem; bind: svc + "/Settings/Port" }
    VBusItem { id: unitIdItem; bind: svc + "/Settings/UnitId" }

    VBusItem { id: voltageItem; bind: svc + "/Dc/0/Voltage" }
    VBusItem { id: currentItem; bind: svc + "/Dc/0/Current" }
    VBusItem { id: powerItem; bind: svc + "/Dc/0/Power" }
    VBusItem { id: socItem; bind: svc + "/Soc" }

    VBusItem { id: alarmStateItem; bind: svc + "/Alarms/State" }
    VBusItem { id: activeAlarmsItem; bind: svc + "/Alarms/Active" }

    VBusItem { id: maxChargeCurrentItem; bind: svc + "/Info/MaxChargeCurrent" }
    VBusItem { id: maxDischargeCurrentItem; bind: svc + "/Info/MaxDischargeCurrent" }
    VBusItem { id: maxChargeVoltageItem; bind: svc + "/Info/MaxChargeVoltage" }

    model: VisibleItemModel {
        MbItemValue {
            description: qsTr("System Status")
            item: statusItem
        }

        MbItemValue {
            description: qsTr("Connected")
            item: connectedItem
        }

        MbItemValue {
            description: qsTr("Last Error")
            item: lastErrorItem
        }

        MbItemValue {
            description: qsTr("Voltage")
            item: voltageItem
        }

        MbItemValue {
            description: qsTr("Current")
            item: currentItem
        }

        MbItemValue {
            description: qsTr("Power")
            item: powerItem
        }

        MbItemValue {
            description: qsTr("State of Charge")
            item: socItem
        }

        MbItemValue {
            description: qsTr("Alarm State")
            item: alarmStateItem
        }

        MbItemValue {
            description: qsTr("Active Alarms")
            item: activeAlarmsItem
        }

        MbItemValue {
            description: qsTr("Max Charge Current")
            item: maxChargeCurrentItem
        }

        MbItemValue {
            description: qsTr("Max Discharge Current")
            item: maxDischargeCurrentItem
        }

        MbItemValue {
            description: qsTr("Max Charge Voltage")
            item: maxChargeVoltageItem
        }

        MbSwitch {
            name: qsTr("Enable Monarch BMS Service")
            bind: svc + "/Settings/Enabled"
        }

        // For now these are read-only to avoid UI widget type issues.
        // Once the page loads reliably, we can switch to editable components.
        MbItemValue {
            description: qsTr("BMS IP Address")
            item: ipItem
        }

        MbItemValue {
            description: qsTr("BMS Port")
            item: portItem
        }

        MbItemValue {
            description: qsTr("Device/Unit ID")
            item: unitIdItem
        }

        MbItemValue {
            description: qsTr("Modbus Register Block")
            item: registersItem
        }
    }
}
