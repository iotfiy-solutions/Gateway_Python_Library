"""
IOTFIY — Raspberry Pi Basic example (Pi 3 / 4 / 5)

Install (from Python/ folder):
  pip install -e .

Run:
  python examples/raspberry_pi_basic.py

Same flow as Arduino:
  IOTFIY.config → begin → write/read → reconnect_mqtt → loop
"""

import time

from iotfiy import IOTFIY, Ref

# Network on Pi is usually already up via the OS.
# ssid/password kept for API parity with Arduino (optional on Pi).
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

MQTT_SERVER = "YOUR_MQTT_HOST"  # e.g. "192.168.1.10" (no mqtt:// prefix)
MQTT_CLIENT_ID = "rpi_client_1"
DEVICE_ID = "device_rpi_1"
MQTT_PORT = 1883
# Optional auth:
# MQTT_USER = ""
# MQTT_PASS = ""

sensor_value = Ref(0.0)
control_value = Ref(0.0)

PUBLISH_INTERVAL_S = 3.0


def main() -> None:
    print("IOTFIY Raspberry Pi Basic")

    IOTFIY.config(
        WIFI_SSID,
        WIFI_PASSWORD,
        MQTT_SERVER,
        MQTT_CLIENT_ID,
        DEVICE_ID,
        MQTT_PORT,
        # MQTT_USER,
        # MQTT_PASS,
    )
    IOTFIY.enable_lwt(True)

    if not IOTFIY.check_and_reconnect_wifi():
        print("Network to MQTT broker failed — will retry in loop")
    else:
        print("Network OK (MQTT host reachable)")

    IOTFIY.begin()

    # Dashboard ← device (sensor / output)
    IOTFIY.write("SensorValue", "float", "A0", sensor_value)

    # Dashboard → device (control)
    IOTFIY.read("ControlValue", "float", "Ctrl", control_value, 0, 100)

    if IOTFIY.reconnect_mqtt():
        print("MQTT connected")
    else:
        print("MQTT connect failed — will retry in loop")

    last_publish = 0.0
    demo = 0.0

    while True:
        IOTFIY.check_and_reconnect_wifi()

        if not IOTFIY.is_mqtt_connected():
            IOTFIY.reconnect_mqtt()

        IOTFIY.process_mqtt_messages()

        now = time.time()
        if now - last_publish >= PUBLISH_INTERVAL_S:
            last_publish = now
            # Demo ramp 0–100 (replace with a real sensor read on Pi)
            demo = (demo + 3.0) % 100.0
            sensor_value.value = demo
            IOTFIY.launch()
            print(
                f"Published sensor_value={sensor_value.value}  "
                f"control_value={control_value.value}"
            )

        time.sleep(0.01)


if __name__ == "__main__":
    main()
