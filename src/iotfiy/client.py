"""IOTFIY manager - Arduino IOTFIYManager API for Raspberry Pi."""

from __future__ import annotations

import json
import socket
import time
from typing import List, Optional

import paho.mqtt.client as mqtt

from .device_config import DeviceConfig
from .receive import Receive
from .ref import Ref
from .send import Send


class IOTFIYManager:
    MAX_SENDS = 10
    MAX_RECEIVES = 10

    def __init__(self):
        self._sends: List[Send] = []
        self._receives: List[Receive] = []
        self._config = DeviceConfig()
        self._lwt_enabled = False
        self._client: Optional[mqtt.Client] = None

    def config_obj(self) -> DeviceConfig:
        """Access underlying DeviceConfig (Arduino: config())."""
        return self._config

    def enable_lwt(self, enabled: bool = True) -> None:
        self._lwt_enabled = enabled
        state = "ENABLED (offline on disconnect)" if enabled else "disabled"
        print(f"MQTT LWT {state}")

    def config(
        self,
        ssid: str,
        password: str,
        mqtt_server: str,
        mqtt_client_id: str,
        device_id: str,
        mqtt_port: int = 1883,
        mqtt_username: str = "",
        mqtt_password: str = "",
    ) -> None:
        """Same signature as Arduino IOTFIY.config(...).

        On Raspberry Pi, WiFi is normally managed by the OS. ``ssid`` /
        ``password`` are kept for API compatibility; MQTT settings are required.
        """
        self._config.ssid(ssid).password(password).server(mqtt_server).port(
            mqtt_port
        ).client_id(mqtt_client_id).device_id(device_id).mqtt_username(
            mqtt_username
        ).mqtt_password(mqtt_password)

    def begin(self) -> None:
        if not self._config.is_valid():
            raise ValueError(
                "IOTFIY config incomplete - set mqtt_server, client_id, device_id"
            )

        # paho-mqtt 2.x uses CallbackAPIVersion; 1.x does not.
        try:
            self._client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION1,
                client_id=self._config.get_mqtt_client_id,
            )
        except (AttributeError, TypeError):
            self._client = mqtt.Client(client_id=self._config.get_mqtt_client_id)

        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

        if self._config.get_mqtt_username:
            self._client.username_pw_set(
                self._config.get_mqtt_username,
                self._config.get_mqtt_password,
            )

        if self._lwt_enabled:
            will_payload = json.dumps(
                {
                    "status": "offline",
                    "deviceId": self._config.get_device_id,
                }
            )
            self._client.will_set(
                self._config.get_status_topic(),
                payload=will_payload,
                qos=1,
                retain=True,
            )

        self._bind_client_to_capabilities()

    def register_all_capabilities(self) -> None:
        start = {
            "deviceId": self._config.get_device_id,
            "event": "capabilities_registration_start",
            "total_controls": len(self._receives),
            "total_sensors": len(self._sends),
        }
        self._publish(self._config.get_status_topic(), start, retain=False)

        for receive in self._receives:
            receive.register_capability()
        for send in self._sends:
            send.register_capability()

        end = {
            "deviceId": self._config.get_device_id,
            "event": "capabilities_registration_complete",
            "controls_registered": len(self._receives),
            "sensors_registered": len(self._sends),
        }
        self._publish(self._config.get_status_topic(), end, retain=False)

    def launch(self) -> None:
        for send in self._sends:
            send.publish_data()

    def publish_string_output(self, name: str, pin: str, value: str) -> bool:
        if not self.is_mqtt_connected():
            return False

        cap = {
            "deviceId": self._config.get_device_id,
            "type": "capabilities_output",
            "outputName": name,
            "output": {"type": "string", "pin": pin},
        }
        cap_topic = (
            f"devices/{self._config.get_device_id}/capabilities_output/{name}"
        )
        self._publish(cap_topic, cap, retain=True)

        data = {
            "type": "output",
            "deviceId": self._config.get_device_id,
            "data": {name: value, pin: value},
        }
        print(f"String output {pin}={value}")
        return self._publish(self._config.get_data_topic(), data, retain=False)

    def reconnect_mqtt(self) -> bool:
        if self._client is None:
            self.begin()

        assert self._client is not None
        if self._client.is_connected():
            return True

        for attempt in range(1, 6):
            print(f"MQTT connection attempt {attempt}... ", end="", flush=True)
            try:
                self._client.connect(
                    self._config.get_mqtt_server,
                    self._config.get_mqtt_port,
                    keepalive=60,
                )
                # Give the network stack a moment, then poll until connected.
                deadline = time.time() + 8
                while time.time() < deadline and not self._client.is_connected():
                    self._client.loop(timeout=0.2)

                if self._client.is_connected():
                    print("connected!")
                    if self._lwt_enabled:
                        print(f"LWT registered on {self._config.get_status_topic()}")

                    self._client.subscribe(self._config.get_commands_topic())
                    status = {
                        "status": "online",
                        "deviceId": self._config.get_device_id,
                    }
                    self._publish(
                        self._config.get_status_topic(), status, retain=True
                    )
                    self.register_all_capabilities()
                    return True

                print("failed (timeout)")
            except Exception as exc:
                print(f"failed ({exc})")

            if attempt < 5:
                time.sleep(5)

        return False

    def check_and_reconnect_wifi(self) -> bool:
        """On Pi, verify network path to the MQTT broker (OS manages Wi-Fi)."""
        host = self._config.get_mqtt_server
        port = self._config.get_mqtt_port
        if not host:
            print("WiFi/network check failed: MQTT server not configured")
            return False

        try:
            with socket.create_connection((host, port), timeout=3):
                return True
        except OSError:
            print("Network unreachable to MQTT broker. Will retry...")
            return False

    def is_mqtt_connected(self) -> bool:
        return bool(self._client and self._client.is_connected())

    def process_mqtt_messages(self) -> None:
        if self._client is not None:
            self._client.loop(timeout=0.05)

    def write(
        self,
        name: str,
        type_: str,
        pin: str,
        data_source: Ref,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> Optional[Send]:
        if len(self._sends) >= self.MAX_SENDS:
            return None
        if not isinstance(data_source, Ref):
            raise TypeError("write() expects an iotfiy.Ref for data_source")

        send = Send(
            name,
            type_,
            pin,
            data_source,
            self._client,
            self._config,
            min_value,
            max_value,
        )
        # Client may be created later in begin(); keep reference alive.
        self._sends.append(send)
        self._bind_client_to_capabilities()
        return send

    def read(
        self,
        name: str,
        type_: str,
        pin: str,
        entry_point: Ref,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> Optional[Receive]:
        if len(self._receives) >= self.MAX_RECEIVES:
            return None
        if not isinstance(entry_point, Ref):
            raise TypeError("read() expects an iotfiy.Ref for entry_point")

        receive = Receive(
            name,
            type_,
            pin,
            entry_point,
            self._client,
            self._config,
            min_value,
            max_value,
        )
        self._receives.append(receive)
        self._bind_client_to_capabilities()
        return receive

    def _bind_client_to_capabilities(self) -> None:
        if self._client is None:
            return
        for send in self._sends:
            send._client = self._client
        for receive in self._receives:
            receive._client = self._client

    def _publish(self, topic: str, payload: dict, retain: bool) -> bool:
        if not self.is_mqtt_connected():
            return False
        assert self._client is not None
        try:
            info = self._client.publish(topic, json.dumps(payload), retain=retain)
            return info.rc == 0
        except Exception as exc:
            print(f"MQTT publish error: {exc}")
            return False

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f"Unexpected MQTT disconnect (rc={rc})")

    def _on_message(self, client, userdata, msg):
        try:
            message = msg.payload.decode("utf-8", errors="replace")
        except Exception:
            return

        print(f"Message arrived [{msg.topic}] {message}")

        try:
            doc = json.loads(message)
        except json.JSONDecodeError as exc:
            print(f"JSON parse failed: {exc}")
            return

        if msg.topic != self._config.get_commands_topic():
            return

        value = None
        control_name = None
        pin_name = None

        if isinstance(doc, dict) and "data" in doc and "type" in doc:
            data = doc.get("data") or {}
            value = data.get("value")
            control_name = data.get("control")
            pin_name = data.get("pin")
        elif isinstance(doc, dict):
            value = doc.get("value")
            control_name = doc.get("control")
            pin_name = doc.get("pin")

        target: Optional[Receive] = None
        if control_name:
            for receive in self._receives:
                if receive.get_name() == control_name:
                    target = receive
                    break
        elif pin_name:
            for receive in self._receives:
                if receive.get_pin() == pin_name:
                    target = receive
                    break

        if target is not None:
            result = {}
            success = target.handle_command(value, result)
            response = {
                "status": "success" if success else "error",
                "control": target.get_name(),
                "result": result,
            }
            self._publish(
                self._config.get_command_response_topic(), response, retain=False
            )
        else:
            print("ERROR: No matching control or pin found")
            error = {
                "status": "error",
                "message": "No matching control or pin found",
            }
            if control_name:
                error["control"] = control_name
            if pin_name:
                error["pin"] = pin_name
            self._publish(
                self._config.get_command_response_topic(), error, retain=False
            )


# Global instance (Arduino: extern IOTFIYManager IOTFIY)
IOTFIY = IOTFIYManager()
