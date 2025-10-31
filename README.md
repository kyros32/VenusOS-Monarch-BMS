# 🚀 Deploying Monarch BMS Modbus to DBus Bridge on Victron Venus OS

This script reads Modbus values from a Monarch BMS over TCP and publishes them to DBus as a custom battery service:

`com.victronenergy.battery.monarch`

✅ Visible in GX UI
✅ Auto-starts at boot
✅ **Survives firmware updates**
✅ No external dependencies besides normal Venus tools

## 📦 Installation (Persistent & Survives Updates)

SSH into your Victron Cerbo GX / Venus device and follow these steps:

**1. Create a persistent directory in `/data`**
The `/data` partition is the only one that survives firmware updates.

```bash
mkdir -p /data/monarch_bms
```

**2. Download the script into the new directory**

```bash
wget -O /data/monarch_bms/monarch_bms.py https://github.com/kyros32/DBus_client_monarch/monarch_bms.py
```

*(Remember to update this file with the final version containing the `sys.path` fix).*

**3. Make the script executable**

```bash
chmod +x /data/monarch_bms/monarch_bms.py
```

**4. Create/edit `/data/rc.local` to auto-start the script**
This file is also persistent and is executed at the end of every boot sequence.

```bash
nano /data/rc.local
```

**5. Add the following lines**
This will re-create the symbolic link on every boot, then run the script from the location Venus OS expects.

```bash
#!/bin/sh
# Start Monarch BMS driver

# Create symbolic link from the non-persistent location to our persistent script
# (The /opt/victronenergy/dbus-modbus-client/ directory is assumed to exist)
ln -sfn /data/monarch_bms/monarch_bms.py /opt/victronenergy/dbus-modbus-client/monarch_bms.py

# Run the script from the symlink location
/usr/bin/python3 /opt/victronenergy/dbus-modbus-client/monarch_bms.py > /dev/null 2>&1 &
exit 0
```

**6. Make `rc.local` executable**

```bash
chmod +x /data/rc.local
```

**7. Reboot the device**
The script will now start automatically after every boot.

```bash
reboot
```

-----

## 🧪 Manual Testing (Optional)

If you want to test before rebooting, you must **first run the symlink command** from `rc.local`:

```bash
ln -sfn /data/monarch_bms/monarch_bms.py /opt/victronenergy/dbus-modbus-client/monarch_bms.py
```

Now you can test by running from the **`/opt` path**:

```bash
/usr/bin/python3 /opt/victronenergy/dbus-modbus-client/monarch_bms.py
```

You should see the dbus service appear on `dbus-spy`.

-----

## ✅ Verification (After Reboot)

Check that the process is running. Note the path will be the one in `/opt`.

```bash
pgrep -f /opt/victronenergy/dbus-modbus-client/monarch_bms.py
```

Check if the dbus service is registered:

```bash
dbus-spy
```

✅ If detected → BMS data is successfully published to Venus OS

-----

## 🛑 Stopping the Service

This will stop the currently running process. It will restart automatically on the next reboot.

```bash
pkill -f /opt/victronenergy/dbus-modbus-client/monarch_bms.py
```
