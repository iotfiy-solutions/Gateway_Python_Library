"""
IOTFIY — Minimal Write
Device → cloud / dashboard (IOTFIY.write)
store: omit / store=False → no Influx history; store=True → Influx history
"""
import time
from iotfiy import IOTFIY

sensorValue = [59.0]

print("IOTFIY minimal write test")

IOTFIY.config("YOUR_WIFI_SSID", "YOUR_WIFI_PASSWORD", "YOUR_DEVICE_ID")
IOTFIY.begin()

# --- write options (pick one) ---
# pin only (name defaults to pin); type from variable; store default False
# IOTFIY.write("pin6", sensorValue)
# IOTFIY.write("pin6", sensorValue, store=False)
IOTFIY.write("pin6", sensorValue, store=True)

# pin + min/max (+ optional store)
# IOTFIY.write("pin6", sensorValue, 0, 100)
# IOTFIY.write("pin6", sensorValue, 0, 100, store=False)
# IOTFIY.write("pin6", sensorValue, 0, 100, store=True)

# name + pin (+ optional store / min/max)
# IOTFIY.write("temperature", "pin6", sensorValue)
# IOTFIY.write("temperature", "pin6", sensorValue, store=True)
# IOTFIY.write("temperature", "pin6", sensorValue, 0, 100)
# IOTFIY.write("temperature", "pin6", sensorValue, 0, 100, store=True)

# name + type + pin (explicit type)
# IOTFIY.write("temperature", "float", "pin6", sensorValue)
# IOTFIY.write("temperature", "float", "pin6", sensorValue, store=True)
# IOTFIY.write("temperature", "float", "pin6", sensorValue, 0, 100)
# IOTFIY.write("temperature", "float", "pin6", sensorValue, 0, 100, store=True)

while True:
    # default: publish-on-change (no interval)
    IOTFIY.launch()
    # IOTFIY.launch(10000)   # optional: send write data every 10s
    time.sleep(0.01)