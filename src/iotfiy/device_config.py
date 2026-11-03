"""Device / MQTT configuration (mirrors Arduino DeviceConfig)."""

from __future__ import annotations

import base64
import re


class DeviceConfig:
    def __init__(self):
        self._ssid = ""
        self._password = ""
        self._mqtt_server = ""
        self._mqtt_port = 1883
        self._mqtt_username = ""
        self._mqtt_password = ""
        self._device_id = ""

    def ssid(self, value: str):
        self._ssid = value or ""
        return self

    def password(self, value: str):
        self._password = value or ""
        return self

    def server(self, value: str):
        self._mqtt_server = value or ""
        return self

    def port(self, value: int):
        self._mqtt_port = int(value)
        return self

    def device_id(self, value: str):
        """Accept plain or Base64 device id (decoded like Arduino)."""
        resolved = resolve_device_id(value)
        self._device_id = resolved
        if value and resolved and resolved != value:
            print(f"Device ID decoded from Base64: {resolved}")
        return self

    def mqtt_username(self, value: str):
        self._mqtt_username = value or ""
        return self

    def mqtt_password(self, value: str):
        self._mqtt_password = value or ""
        return self

    @property
    def get_ssid(self) -> str:
        return self._ssid

    @property
    def get_password(self) -> str:
        return self._password

    @property
    def get_mqtt_server(self) -> str:
        return self._mqtt_server

    @property
    def get_mqtt_port(self) -> int:
        return self._mqtt_port

    @property
    def get_mqtt_client_id(self) -> str:
        # Arduino: deviceId is also the MQTT client id
        return self._device_id

    @property
    def get_device_id(self) -> str:
        return self._device_id

    @property
    def get_mqtt_username(self) -> str:
        return self._mqtt_username

    @property
    def get_mqtt_password(self) -> str:
        return self._mqtt_password

    def get_data_topic(self) -> str:
        return f"devices/{self._device_id}/data"

    def get_status_topic(self) -> str:
        return f"devices/{self._device_id}/status"

    def get_commands_topic(self) -> str:
        return f"devices/{self._device_id}/commands"

    def get_command_response_topic(self) -> str:
        return f"devices/{self._device_id}/command-response"

    def is_valid(self) -> bool:
        return bool(self._mqtt_server and self._device_id)


_B64_RE = re.compile(r"^[A-Za-z0-9+/]*=*$")


def resolve_device_id(value: str | None) -> str:
    """Mirror Arduino DeviceConfig::resolveDeviceId."""
    if value is None or value == "":
        return ""

    raw = value.strip()
    compact = "".join(ch for ch in raw if ch not in " \t\r\n")
    if not compact:
        return value

    had_padding = "=" in compact
    if not _B64_RE.fullmatch(compact):
        return value

    if len(compact) < 4:
        return value
    if not had_padding and (len(compact) % 4) != 0:
        return value
    if not had_padding and len(compact) < 8:
        return value

    padded = compact
    while len(padded) % 4 != 0:
        padded += "="

    try:
        decoded = base64.b64decode(padded, validate=False)
        text = decoded.decode("utf-8")
    except Exception:
        return value

    if not text or not all(33 <= ord(c) <= 126 for c in text):
        return value

    return text
