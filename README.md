# 🚀 Deploying Monarch BMS Modbus to DBus Bridge on Victron Venus OS

This script reads Modbus values from a Monarch BMS over TCP and publishes them to DBus as a custom battery service:

com.victronenergy.battery.monarch


✅ Visible in GX UI
✅ Auto-starts at boot
✅ No external dependencies besides normal Venus tools

## 📦 Install & Run

SSH into your Victron Cerbo GX / Venus device:
```bash
cd /opt/victronenergy/dbus-modbus-client
wget https://github.com/kyros32/DBus_client_monarch/monarch_bms.py
chmod +x monarch_bms.py
```

Test manual start:
```bash
/usr/bin/python3 /opt/victronenergy/dbus-modbus-client/monarch_bms.py
```

You should see dbus service appear on dbus-spy
```bash
dbus-spy
```

Stop script if needed:
```bash
pkill -f monarch_bms.py
```
## 🔁 Enable Auto-Start on Boot

Create/edit /data/rc.local:
```bash
nano  /data/rc.local
```

Add the following:
```bash
#!/bin/sh
/usr/bin/python3 /opt/victronenergy/dbus-modbus-client/monarch_bms.py > /dev/null 2>&1 &
exit 0
```

Make it executable:
```bash
chmod +x /data/rc.local
```

✅ Script will start automatically after reboot

✅ Verification

Check background process:
```bash
pgrep -f monarch_bms.py
```

Check dbus service:
```bash
dbus-spy
```

✅ If detected → BMS data is successfully published to Venus OS

🛑 Stopping the Service
```bash
pkill -f monarch_bms.py
```
## 📌 Notes

/data is persistent through firmware upgrades

Output logs are suppressed intentionally

Python script updates DBus values every 5 seconds
