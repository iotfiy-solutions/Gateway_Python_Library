"""IOTFIY manager - Arduino IOTFIYManager API for Raspberry Pi."""

from __future__ import annotations

import json
import socket
import time
from typing import Any, List, Optional, Tuple

import paho.mqtt.client as mqtt

from .device_config import DeviceConfig
from .receive import Receive
from .send import Send, infer_type, is_binding

# Fixed IOTFIY gateway MQTT settings (same as Arduino library)
_MQTT_SERVER = "gateway.iotfiysolutions.com"
_MQTT_PORT = 1883
_MQTT_USERNAME = "mqttuser"
_MQTT_PASSWORD = "Growmore12345@"

_KNOWN_TYPES = frozenset({"float", "integer", "boolean", "string"})


class IOTFIYManager:
    MAX_SENDS = 10
    MAX_RECEIVES = 10

    def __init__(self):
        self._sends: List[Send] = []
        self._receives: List[Receive] = []
        self._config = DeviceConfig()
        self._client: Optional[mqtt.Client] = None
        self._last_wifi_ok = False
        self._last_mqtt_ok = False
        self._status_initialized = False

    def config_obj(self) -> DeviceConfig:
        """Access underlying DeviceConfig (Arduino: config())."""
        return self._config

    def config(self, ssid: str, password: str, device_id: str) -> None:
        """WiFi + device id only. MQTT broker/auth/LWT are built into the library.

        ``device_id`` may be plain or Base64 (decoded internally). It is also
        used as the MQTT client id. On Raspberry Pi, OS manages Wi-Fi; ssid /
        password are kept for API compatibility with Arduino.
        """
        self._config.ssid(ssid).password(password).server(_MQTT_SERVER).port(
            _MQTT_PORT
        ).device_id(device_id).mqtt_username(_MQTT_USERNAME).mqtt_password(
            _MQTT_PASSWORD
        )

    def begin(self) -> None:
        if not self._config.is_valid():
            raise ValueError(
                "IOTFIY config incomplete - call config(ssid, password, device_id)"
            )

        client_id = self._config.get_mqtt_client_id
        try:
            self._client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION1,
                client_id=client_id,
            )
        except (AttributeError, TypeError):
            self._client = mqtt.Client(client_id=client_id)

        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

        if self._config.get_mqtt_username:
            self._client.username_pw_set(
                self._config.get_mqtt_username,
                self._config.get_mqtt_password,
            )

        # LWT always enabled (not user-configurable)
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
        """Maintain network + MQTT, process commands, publish changed write() values."""
        wifi_ok = self._check_and_reconnect_wifi()

        if wifi_ok and not self.is_mqtt_connected():
            self._reconnect_mqtt()

        if self.is_mqtt_connected():
            self._process_mqtt_messages()

        mqtt_ok = self.is_mqtt_connected()
        if (
            not self._status_initialized
            or wifi_ok != self._last_wifi_ok
            or mqtt_ok != self._last_mqtt_ok
        ):
            self._print_connection_status(wifi_ok, mqtt_ok)
            self._last_wifi_ok = wifi_ok
            self._last_mqtt_ok = mqtt_ok
            self._status_initialized = True

        if not mqtt_ok:
            return

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
        topic = self._config.get_data_topic()
        print(f"String output {pin}={value} -> {topic}")
        return self._publish(topic, data, retain=False)

    def is_mqtt_connected(self) -> bool:
        return bool(self._client and self._client.is_connected())

    def write(self, *args: Any) -> Optional[Send]:
        """Register an output. Type inferred from the variable; name optional.

        Forms (Arduino-compatible)::
            write(pin, var)
            write(pin, var, min, max)
            write(name, pin, var)
            write(name, pin, var, min, max)
            write(name, type, pin, var)
            write(name, type, pin, var, min, max)

        ``var`` must be a one-element list (mutable) e.g. ``sensor = [0.0]``.
        """
        if len(self._sends) >= self.MAX_SENDS:
            return None

        name, type_, pin, var, min_v, max_v = self._parse_capability_args(
            args, "write"
        )
        if type_ is None:
            type_ = infer_type(var)
        if not name:
            name = pin

        send = Send(
            name,
            type_,
            pin,
            var,
            self._client,
            self._config,
            min_v,
            max_v,
        )
        self._sends.append(send)
        self._bind_client_to_capabilities()
        return send

    def read(self, *args: Any) -> Optional[Receive]:
        """Register a control. Type inferred from the variable; name optional.

        Forms (Arduino-compatible)::
            read(pin, var)
            read(pin, var, min, max)
            read(name, pin, var)
            read(name, pin, var, min, max)
            read(name, type, pin, var)
            read(name, type, pin, var, min, max)

        ``var`` must be a one-element list (mutable) e.g. ``control = [0.0]``.
        """
        if len(self._receives) >= self.MAX_RECEIVES:
            return None

        name, type_, pin, var, min_v, max_v = self._parse_capability_args(
            args, "read"
        )
        if type_ is None:
            type_ = infer_type(var)
        if not name:
            name = pin

        receive = Receive(
            name,
            type_,
            pin,
            var,
            self._client,
            self._config,
            min_v,
            max_v,
        )
        self._receives.append(receive)
        self._bind_client_to_capabilities()
        return receive

    @staticmethod
    def _parse_capability_args(
        args: Tuple[Any, ...], label: str
    ) -> Tuple[Optional[str], Optional[str], str, Any, Optional[float], Optional[float]]:
        if len(args) < 2:
            raise TypeError(f"{label}() needs at least pin and variable")

        # Find binding from the end (before optional min/max numbers)
        # Patterns end with: var | var, min, max
        binding_index = None
        min_v: Optional[float] = None
        max_v: Optional[float] = None

        if len(args) >= 4 and is_binding(args[-3]):
            # ..., var, min, max
            if not isinstance(args[-2], (int, float)) or not isinstance(
                args[-1], (int, float)
            ):
                raise TypeError(f"{label}() min/max must be numbers")
            binding_index = len(args) - 3
            min_v = float(args[-2])
            max_v = float(args[-1])
        elif is_binding(args[-1]):
            binding_index = len(args) - 1
        else:
            raise TypeError(
                f"{label}() variable must be a one-element list, e.g. sensor = [0.0]"
            )

        var = args[binding_index]
        head = args[:binding_index]

        if len(head) == 1:
            # pin, var
            return None, None, str(head[0]), var, min_v, max_v
        if len(head) == 2:
            # name, pin, var
            return str(head[0]), None, str(head[1]), var, min_v, max_v
        if len(head) == 3:
            # name, type, pin, var
            name, type_, pin = str(head[0]), str(head[1]), str(head[2])
            if type_ not in _KNOWN_TYPES:
                raise TypeError(
                    f"{label}() unknown type {type_!r}; "
                    f"expected one of {sorted(_KNOWN_TYPES)}"
                )
            return name, type_, pin, var, min_v, max_v

        raise TypeError(f"{label}() invalid arguments: {args!r}")

    def _reconnect_mqtt(self) -> bool:
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
                deadline = time.time() + 8
                while time.time() < deadline and not self._client.is_connected():
                    self._client.loop(timeout=0.2)

                if self._client.is_connected():
                    print("connected!")
                    print(f"LWT registered on {self._config.get_status_topic()}")
                    print(f"Device ID: {self._config.get_device_id}")

                    for send in self._sends:
                        send.reset_publish_state()

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

    def _check_and_reconnect_wifi(self) -> bool:
        """On Pi, verify TCP path to the MQTT broker (OS manages Wi-Fi)."""
        host = self._config.get_mqtt_server
        port = self._config.get_mqtt_port
        if not host:
            print("Network check failed: MQTT server not configured")
            return False

        try:
            with socket.create_connection((host, port), timeout=3):
                return True
        except OSError:
            print("Network unreachable to MQTT broker. Will retry...")
            return False

    def _process_mqtt_messages(self) -> None:
        if self._client is not None:
            self._client.loop(timeout=0.05)

    def _print_connection_status(self, wifi_ok: bool, mqtt_ok: bool) -> None:
        if wifi_ok:
            print("WiFi: connected (MQTT host reachable)")
        else:
            print("WiFi: not connected")
        print(f"MQTT: {'connected' if mqtt_ok else 'not connected'}")

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
            try:
                self._client.loop(timeout=0.05)
            except Exception:
                pass
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
            result: dict = {}
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
