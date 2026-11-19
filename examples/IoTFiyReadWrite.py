"""
IOTFIY — Minimal Read + Write
Device → cloud (write) and cloud → device (read)
"""

import time
from iotfiy import IOTFIY

sensorValue = [30.0]
controlValue = [0.0]

print("IOTFIY minimal read/write test")

IOTFIY.config("YOUR_WIFI_SSID", "YOUR_WIFI_PASSWORD", "YOUR_DEVICE_ID")
IOTFIY.begin()

# --- write options (pick one) ---
# IOTFIY.write("pin6", sensorValue)
# IOTFIY.write("pin6", sensorValue, store=False)
IOTFIY.write("pin6", sensorValue, store=True)

# IOTFIY.write("pin6", sensorValue, 0, 100)
# IOTFIY.write("pin6", sensorValue, 0, 100, store=True)

# IOTFIY.write("temperature", "pin6", sensorValue)
# IOTFIY.write("temperature", "pin6", sensorValue, store=True)
# IOTFIY.write("temperature", "pin6", sensorValue, 0, 100)
# IOTFIY.write("temperature", "pin6", sensorValue, 0, 100, store=True)

# IOTFIY.write("temperature", "float", "pin6", sensorValue)
# IOTFIY.write("temperature", "float", "pin6", sensorValue, store=True)
# IOTFIY.write("temperature", "float", "pin6", sensorValue, 0, 100, store=True)

# --- read options (pick one) ---
# IOTFIY.read("V5", controlValue)
IOTFIY.read("V5", controlValue, 0, 100)

# IOTFIY.read("Display", "V5", controlValue)
# IOTFIY.read("Display", "V5", controlValue, 0, 100)

# IOTFIY.read("Display", "float", "V5", controlValue)
# IOTFIY.read("Display", "float", "V5", controlValue, 0, 100)

while True:
    # default: publish-on-change (no interval)
    IOTFIY.launch()
    # IOTFIY.launch(5000)   # optional: send write data every 5s

    print(controlValue[0])
    time.sleep(0.01)