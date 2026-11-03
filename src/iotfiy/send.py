"""Output / sensor capability (mirrors Arduino Send)."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .device_config import DeviceConfig


def is_binding(obj: Any) -> bool:
    """Arduino float*/int*/bool*/String* equivalent: one-element list or .value object."""
    if isinstance(obj, list) and len(obj) == 1:
        return True
    if hasattr(obj, "value") and not isinstance(obj, (str, bytes, dict)):
        return True
    return False


def read_binding(obj: Any) -> Any:
    if isinstance(obj, list):
        return obj[0]
    return obj.value


def write_binding(obj: Any, value: Any) -> None:
    if isinstance(obj, list):
        obj[0] = value
    else:
        obj.value = value


def infer_type(obj: Any) -> str:
    value = read_binding(obj)
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    return "float"


class Send:
    def __init__(
        self,
        name: str,
        type_: str,
        pin: str,
        exit_point: Any,
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
        self.exit_point = exit_point
        self.has_range = min_value is not None and max_value is not None
        self.min = float(min_value) if min_value is not None else 0.0
        self.max = float(max_value) if max_value is not None else 0.0
        self.is_registered = False
        self.default_delay = 0.05
        self._has_last_published = False
        self._last_published_value: Optional[float] = None

    def get_name(self) -> str:
        return self.name

    def get_type(self) -> str:
        return self.type

    def get_pin(self) -> str:
        return self.pin

    def get_current_value(self) -> float:
        try:
            return float(read_binding(self.exit_point))
        except (TypeError, ValueError):
            return 0.0

    def set_delay(self, ms: int) -> None:
        self.default_delay = max(0, ms) / 1000.0

    def reset_publish_state(self) -> None:
        self._has_last_published = False
        self.is_registered = False

    def register_capability(self) -> bool:
        payload = {
            "deviceId": self._config.get_device_id,
            "type": "capabilities_output",
            "outputName": self.name,
            "output": {"type": self.type, "pin": self.pin},
        }
        topic = f"devices/{self._config.get_device_id}/capabilities_output/{self.name}"
        published = self._publish(topic, payload, retain=True)
        print(f"{self.name} output published: {'SUCCESS' if published else 'FAILED'}")
        if published:
            self.is_registered = True
        time.sleep(self.default_delay)
        return published

    def publish_data(self) -> bool:
        try:
            raw = read_binding(self.exit_point)
            value = float(raw) if not isinstance(raw, str) else 0.0
        except (TypeError, ValueError):
            value = 0.0

        # Wrap when min/max set (Arduino behaviour)
        if self.has_range and self.max > self.min:
            if value > self.max:
                value = self.min
                write_binding(self.exit_point, self._typed_store(value))
            elif value < self.min:
                value = self.max
                write_binding(self.exit_point, self._typed_store(value))

        if self._has_last_published and value == self._last_published_value:
            return True

        if not self.is_registered:
            self.register_capability()

        as_bool = self.type == "boolean"
        as_int = self.type == "integer"

        if as_bool:
            out: Any = 1 if value > 0.5 else 0
        elif as_int:
            out = int(value)
        else:
            out = value

        data = {self.name: out}
        if self.pin:
            data[self.pin] = out

        payload = {
            "type": "output",
            "deviceId": self._config.get_device_id,
            "data": data,
        }
        topic = self._config.get_data_topic()
        body = json.dumps(payload)
        print(f"Send data {self.name} -> {topic} ({len(body)} bytes)")

        published = self._publish(topic, payload, retain=False)
        if not published:
            time.sleep(0.02)
            published = self._publish(topic, payload, retain=False)

        print(f"Send data published: {'SUCCESS' if published else 'FAILED'}")
        if published:
            self._last_published_value = value
            self._has_last_published = True
        return published

    def _typed_store(self, value: float) -> Any:
        if self.type == "boolean":
            return value > 0.5
        if self.type == "integer":
            return int(value)
        return float(value)

    def _publish(self, topic: str, payload: dict, retain: bool) -> bool:
        if self._client is None or not self._client.is_connected():
            return False
        try:
            info = self._client.publish(topic, json.dumps(payload), retain=retain)
            try:
                self._client.loop(timeout=0.05)
            except Exception:
                pass
            return info.rc == 0
        except Exception as exc:
            print(f"Send publish error: {exc}")
            return False
