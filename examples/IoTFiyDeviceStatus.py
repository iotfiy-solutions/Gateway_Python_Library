"""
IOTFIY — Device Status
Device connects and shows online on the dashboard.
"""

import time
from iotfiy import IOTFIY

print("IOTFIY minimal online test")

IOTFIY.config("YOUR_WIFI_SSID", "YOUR_WIFI_PASSWORD", "YOUR_DEVICE_ID")
IOTFIY.begin()

while True:
    # default: publish-on-change (no interval)
    IOTFIY.launch()
    # IOTFIY.launch(5000)   # optional: send write data every 5s
    time.sleep(0.01)
