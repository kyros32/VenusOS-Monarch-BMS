import QtQuick 1.1
import com.victron.velib 1.0

MbPage {
    id: root
    title: "Monarch BMS"

    property string svc: "com.victronenergy.battery.monarch"

    model: VisualItemModel {
        MbItemValue {
            description: "Battery Line / Voltage"
            item: VBusItem { bind: svc + "/Dc/0/Voltage" }
        }

        MbItemValue {
            description: "Battery Line / Current"
            item: VBusItem { bind: svc + "/Dc/0/Current" }
        }

        MbItemValue {
            description: "Battery Line / Power"
            item: VBusItem { bind: svc + "/Dc/0/Power" }
        }

        MbItemValue {
            description: "Battery Line / SOC"
            item: VBusItem { bind: svc + "/Soc" }
        }

        MbItemValue {
            description: "Battery Line / State"
            item: VBusItem { bind: svc + "/Status" }
        }

        MbItemValue {
            description: "Battery Line / Alarm State"
            item: VBusItem { bind: svc + "/Alarms/State" }
        }

        MbItemValue {
            description: "Battery Line / Active Alarms"
            item: VBusItem { bind: svc + "/Alarms/Active" }
        }

        MbItemOptions {
            description: "Settings / BMS IP Address"
            bind: VBusItem { bind: svc + "/Settings/IpAddress" }
        }

        MbItemNumeric {
            description: "Settings / BMS Port"
            bind: VBusItem { bind: svc + "/Settings/Port" }
            decimals: 0
            unit: ""
            min: 1
            max: 65535
        }

        MbItemNumeric {
            description: "Settings / Device ID"
            bind: VBusItem { bind: svc + "/Settings/UnitId" }
            decimals: 0
            unit: ""
            min: 0
            max: 255
        }

        MbItemOptions {
            description: "Settings / Enabled"
            bind: VBusItem { bind: svc + "/Settings/Enabled" }
            possibleValues: [
                MbOption { description: "Off"; value: 0 },
                MbOption { description: "On"; value: 1 }
            ]
        }

        MbItemValue {
            description: "Parameters / Max Charge Current"
            item: VBusItem { bind: svc + "/Info/MaxChargeCurrent" }
        }

        MbItemValue {
            description: "Parameters / Max Discharge Current"
            item: VBusItem { bind: svc + "/Info/MaxDischargeCurrent" }
        }

        MbItemValue {
            description: "Parameters / Max Charge Voltage"
            item: VBusItem { bind: svc + "/Info/MaxChargeVoltage" }
        }

        MbItemValue {
            description: "Details / State"
            item: VBusItem { bind: svc + "/Status" }
        }

        MbItemValue {
            description: "Details / Last Error"
            item: VBusItem { bind: svc + "/Status/LastError" }
        }

        MbItemValue {
            description: "Details / Connected"
            item: VBusItem { bind: svc + "/Connected" }
        }

        MbItemValue {
            description: "Details / Registers"
            item: VBusItem { bind: svc + "/Status/Registers" }
        }
    }
}
