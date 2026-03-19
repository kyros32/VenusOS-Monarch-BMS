import QtQuick 2
import com.victron.velib 1.0
import "utils.js" as Utils

MbPage {
    id: root
    title: qsTr("Monarch BMS")

    property string svc: "com.victronenergy.battery.monarch"
    property string setSvc: "com.victronenergy.settings/Settings/VenusOsMonarchBms"

    // Settings -> Monarch only: connection config and status.
    // The battery itself appears in Devices; tap it for standard Victron battery UI
    // (Switch, State, Battery row, SOC, Parameters, Details, Alarms, Device).
    model: VisibleItemModel {
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

        MbItemValue { description: qsTr("Status"); item: VBusItem { bind: Utils.path(svc, "/Status") } }
        MbItemValue { description: qsTr("Connected"); item: VBusItem { bind: Utils.path(svc, "/Connected") } }
        MbItemValue { description: qsTr("Last Error"); item: VBusItem { bind: Utils.path(svc, "/Status/LastError") } }
        MbItemValue { description: qsTr("Connection"); item: VBusItem { bind: Utils.path(svc, "/Mgmt/Connection") } show: item.valid }
    }
}
