"""Control capability (mirrors Arduino Receive)."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any, Optional

from .ref import Ref

if TYPE_CHECKING:
    from .device_config import DeviceConfig


class Receive:
    def __init__(
        self,
        name: str,
        type_: str,
        pin: str,
        entry_point: Ref,
        client: Any,
        config: DeviceConfig,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ):
        self._client = client
        self._config = config
        self.name = name
        self.type = type_
        self.pin = pin
        self.entry_point = entry_point
        self.has_range = min_value is not None and max_value is not None
        self.min = float(min_value) if min_value is not None else 0.0
        self.max = float(max_value) if max_value is not None else 0.0
        self.is_registered = False
        self.default_delay = 0.05

    def get_name(self) -> str:
        return self.name

    def get_type(self) -> str:
        return self.type

    def get_pin(self) -> str:
        return self.pin

    def register_capability(self) -> bool:
        control = {"type": self.type, "pin": self.pin}
        if self.type in ("float", "integer") and self.has_range:
            control["min"] = self.min
            control["max"] = self.max

        payload = {
            "deviceId": self._config.get_device_id,
            "type": "capabilities_control",
            "controlName": self.name,
            "control": control,
        }
        topic = f"devices/{self._config.get_device_id}/capabilities_control/{self.name}"
        published = self._publish(topic, payload, retain=True)
        print(f"{self.name} control published: {'SUCCESS' if published else 'FAILED'}")
        if published:
            self.is_registered = True
        time.sleep(self.default_delay)
        return published

    def handle_command(self, value: Any, result: dict) -> bool:
        if self.type == "float":
            float_value = float(value)
            if self.has_range:
                float_value = max(self.min, min(self.max, float_value))
            self.entry_point.value = float_value
            result["newState"] = float_value
            return True

        if self.type == "integer":
            int_value = int(value)
            if self.has_range:
                int_value = int(max(self.min, min(self.max, int_value)))
            self.entry_point.value = int_value
            result["newState"] = int_value
            return True

        if self.type == "boolean":
            str_value = str(value).strip().lower()
            bool_value = 1.0 if str_value in ("on", "true", "1") else 0.0
            self.entry_point.value = bool_value
            result["newState"] = str(value)
            return True

        if self.type == "string":
            str_value = str(value)
            self.entry_point.value = str_value
            print(f"String control {self.pin} = {str_value}")
            result["newState"] = str_value
            return True

        return False

    def _publish(self, topic: str, payload: dict, retain: bool) -> bool:
        if self._client is None or not self._client.is_connected():
            return False
        try:
            info = self._client.publish(topic, json.dumps(payload), retain=retain)
            return info.rc == 0
        except Exception as exc:
            print(f"Receive publish error: {exc}")
            return False
