"""
IOTFIY - Raspberry Pi Basic example (Pi 3 / 4 / 5)

Same flow as Arduino:
  config(ssid, password, device_id) -> begin -> write/read -> launch

Built into the library (not configured in the sketch):
  MQTT broker / auth, LWT, network + MQTT reconnect, message processing

write() / read():
  - Type is inferred from the variable (one-element list)
      [0.0] -> float, [0] -> integer, [False] -> boolean, [""] -> string
  - Name is optional (defaults to pin)

  IOTFIY.write("A0", sensor)
  IOTFIY.write("battery", "V9", battery, 0, 100)
  IOTFIY.read("Ctrl", control, 0, 100)

Python has no float* — use a one-element list as the mutable variable:
  sensor = [0.0]
  sensor[0] = 42.5

Keys (then Enter):
  a / b / c  = send ButtonA / ButtonB / ButtonC to backend
  q          = quit
"""

import select
import sys
import time

from iotfiy import IOTFIY

# WiFi + device — device_id may be plain or Base64 (decoded inside the library)
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
DEVICE_ID = "device_rpi_1"

# Outputs -> backend (mutable one-element lists = Arduino variables)
latitude = [24.8607]    # float
longitude = [67.0011]   # float
btn_a = [0]             # integer
btn_b = [0]
btn_c = [0]

# Input <- backend
dashboard_number = [0.0]

GPS_INTERVAL_S = 3.0


def send_button(label: str, target: list) -> None:
    btn_a[0] = 0
    btn_b[0] = 0
    btn_c[0] = 0
    target[0] = 1
    IOTFIY.launch()
    print(f"Sent button {label}")
    target[0] = 0


def main() -> None:
    print("IOTFIY Raspberry Pi Basic")

    IOTFIY.config(WIFI_SSID, WIFI_PASSWORD, DEVICE_ID)
    IOTFIY.begin()

    # name omitted -> pin used as name; type from list element type
    IOTFIY.write("Lat", latitude)
    IOTFIY.write("Lng", longitude)
    IOTFIY.write("BtnA", btn_a)
    IOTFIY.write("BtnB", btn_b)
    IOTFIY.write("BtnC", btn_c)
    IOTFIY.read("Display", dashboard_number)

    IOTFIY.launch()

    print("Keys: a/b/c + Enter = buttons, q = quit")
    last_gps = 0.0

    while True:
        IOTFIY.launch()

        now = time.time()
        if now - last_gps >= GPS_INTERVAL_S:
            last_gps = now
            latitude[0] = 24.0 + (int(now * 1000) % 20000) / 10000.0
            longitude[0] = 66.5 + (int(now * 700) % 20000) / 10000.0
            print(
                f"GPS lat={latitude[0]:.4f} lng={longitude[0]:.4f} "
                f"display={dashboard_number[0]}"
            )

        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline().strip().lower()
            if line == "q":
                break
            if line == "a":
                send_button("A", btn_a)
            elif line == "b":
                send_button("B", btn_b)
            elif line == "c":
                send_button("C", btn_c)

        time.sleep(0.05)


if __name__ == "__main__":
    main()
