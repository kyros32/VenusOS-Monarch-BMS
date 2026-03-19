import QtQuick 1.1
import com.victron.velib 1.0

MbPage {
    id: root
    title: "Monarch BMS"

    property string svc: "com.victronenergy.battery.monarch"

    model: VisualItemModel {
        MbItemOptions {
            description: "BMS IP Address"
            bind: VBusItem { bind: svc + "/Settings/IpAddress" }
        }

        MbItemNumeric {
            description: "BMS Port"
            bind: VBusItem { bind: svc + "/Settings/Port" }
            decimals: 0
            unit: ""
            min: 1
            max: 65535
        }

        MbItemNumeric {
            description: "Device ID"
            bind: VBusItem { bind: svc + "/Settings/UnitId" }
            decimals: 0
            unit: ""
            min: 0
            max: 255
        }

        MbItemOptions {
            description: "Enabled"
            bind: VBusItem { bind: svc + "/Settings/Enabled" }
            possibleValues: [
                MbOption { description: "Off"; value: 0 },
                MbOption { description: "On"; value: 1 }
            ]
        }

        MbItemValue {
            description: "State"
            item: VBusItem { bind: svc + "/Status" }
        }

        MbItemValue {
            description: "Last Error"
            item: VBusItem { bind: svc + "/Status/LastError" }
        }

        MbItemValue {
            description: "Connected"
            item: VBusItem { bind: svc + "/Connected" }
        }

        MbItemValue {
            description: "Voltage"
            item: VBusItem { bind: svc + "/Dc/0/Voltage" }
        }

        MbItemValue {
            description: "Current"
            item: VBusItem { bind: svc + "/Dc/0/Current" }
        }

        MbItemValue {
            description: "SOC"
            item: VBusItem { bind: svc + "/Soc" }
        }

        MbItemValue {
            description: "Max Charge Current"
            item: VBusItem { bind: svc + "/Info/MaxChargeCurrent" }
        }

        MbItemValue {
            description: "Max Discharge Current"
            item: VBusItem { bind: svc + "/Info/MaxDischargeCurrent" }
        }

        MbItemValue {
            description: "Max Charge Voltage"
            item: VBusItem { bind: svc + "/Info/MaxChargeVoltage" }
        }
    }
}
