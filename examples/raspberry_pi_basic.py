"""
IOTFIY - Raspberry Pi Basic example (Pi 3 / 4 / 5)

Tests the same library functions as Arduino:
  - write()  : Latitude / Longitude pins -> backend every few seconds
  - write()  : Button A/B/C pins -> backend when you press a key
  - read()   : Dashboard control -> Pi (logged on console)

Run (console = Serial Monitor):
  python examples/raspberry_pi_basic.py

Keys (then Enter):
  a / b / c  = send ButtonA / ButtonB / ButtonC to backend
  q          = quit
"""

import select
import sys
import time

from iotfiy import IOTFIY, Ref

# Network on Pi is usually already up via the OS.
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

MQTT_SERVER = "YOUR_MQTT_HOST"
MQTT_CLIENT_ID = "rpi_client_1"
DEVICE_ID = "device_rpi_1"
MQTT_PORT = 1883
MQTT_USER = "mqttuser"
MQTT_PASS = ""

# Outputs -> backend (like Arduino write pins)
latitude = Ref(24.8607)
longitude = Ref(67.0011)
btn_a = Ref(0)
btn_b = Ref(0)
btn_c = Ref(0)

# Input <- backend (like Arduino read)
dashboard_number = Ref(0.0)

GPS_INTERVAL_S = 3.0


def send_button(label: str, target: Ref) -> None:
    """Same idea as M5Stack sendButton(): one button=1, others=0, then launch()."""
    btn_a.value = 0
    btn_b.value = 0
    btn_c.value = 0
    target.value = 1
    print(f"[BTN] pressed {label} -> publishing pins BtnA/BtnB/BtnC")
    IOTFIY.launch()
    # pulse back to 0 so next press is clear
    target.value = 0


def poll_key() -> str:
    """Non-blocking single-line keyboard input (Pi terminal)."""
    if select.select([sys.stdin], [], [], 0)[0]:
        line = sys.stdin.readline()
        if not line:
            return ""
        return line.strip().lower()
    return ""


def main() -> None:
    print("========================================")
    print("IOTFIY Raspberry Pi - function check")
    print("Console logs = Serial Monitor")
    print("  [TX] = pin data sent to backend")
    print("  [RX] = pin data received from backend")
    print("  [BTN] = keyboard button -> MQTT")
    print("Keys: a / b / c + Enter | q + Enter = quit")
    print("========================================")

    IOTFIY.config(
        WIFI_SSID,
        WIFI_PASSWORD,
        MQTT_SERVER,
        MQTT_CLIENT_ID,
        DEVICE_ID,
        MQTT_PORT,
        MQTT_USER,
        MQTT_PASS,
    )
    IOTFIY.enable_lwt(True)

    if not IOTFIY.check_and_reconnect_wifi():
        print("Network to MQTT broker failed - will retry in loop")
    else:
        print("Network OK (MQTT host reachable)")

    IOTFIY.begin()

    # GPS-style pins -> dashboard
    IOTFIY.write("Latitude", "float", "Lat", latitude)
    IOTFIY.write("Longitude", "float", "Lng", longitude)

    # Button pins -> dashboard (press a/b/c)
    IOTFIY.write("ButtonA", "integer", "BtnA", btn_a)
    IOTFIY.write("ButtonB", "integer", "BtnB", btn_b)
    IOTFIY.write("ButtonC", "integer", "BtnC", btn_c)

    # Dashboard -> Pi
    IOTFIY.read("DashboardNumber", "float", "Display", dashboard_number)

    if IOTFIY.reconnect_mqtt():
        print("MQTT connected")
    else:
        print("MQTT connect failed - will retry in loop")

    last_gps = 0.0
    last_dashboard = dashboard_number.value
    step = 0

    while True:
        IOTFIY.check_and_reconnect_wifi()

        if not IOTFIY.is_mqtt_connected():
            IOTFIY.reconnect_mqtt()

        IOTFIY.process_mqtt_messages()

        # Show when dashboard control changes (extra clarity on console)
        if dashboard_number.value != last_dashboard:
            print(
                f"[RX-WATCH] pin=Display truth={dashboard_number.value} "
                f"(from backend)"
            )
            last_dashboard = dashboard_number.value

        key = poll_key()
        if key == "q":
            print("Quit")
            break
        if key == "a":
            send_button("A", btn_a)
        elif key == "b":
            send_button("B", btn_b)
        elif key == "c":
            send_button("C", btn_c)

        now = time.time()
        if now - last_gps >= GPS_INTERVAL_S:
            last_gps = now
            step += 1
            # Small moving demo coords (replace with real GPS later)
            latitude.value = 24.8607 + (step % 50) * 0.0001
            longitude.value = 67.0011 + (step % 50) * 0.0001
            print(
                f"[GPS] updating Lat={latitude.value:.6f} "
                f"Lng={longitude.value:.6f}"
            )
            IOTFIY.launch()

        time.sleep(0.05)


if __name__ == "__main__":
    main()
