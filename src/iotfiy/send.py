"""Output / sensor capability (mirrors Arduino Send)."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any, Optional

from .ref import Ref

if TYPE_CHECKING:
    from .device_config import DeviceConfig


class Send:
    def __init__(
        self,
        name: str,
        type_: str,
        pin: str,
        exit_point: Ref,
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

    def get_name(self) -> str:
        return self.name

    def get_type(self) -> str:
        return self.type

    def get_pin(self) -> str:
        return self.pin

    def get_current_value(self) -> float:
        return float(self.exit_point.value)

    def set_delay(self, ms: int) -> None:
        self.default_delay = max(0, ms) / 1000.0

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
        value = float(self.exit_point.value)
        if self.has_range:
            value = max(self.min, min(self.max, value))

        if not self.is_registered:
            self.register_capability()

        data = {self.name: value}
        if self.pin:
            data[self.pin] = value

        payload = {
            "type": "output",
            "deviceId": self._config.get_device_id,
            "data": data,
        }
        published = self._publish(self._config.get_data_topic(), payload, retain=False)
        status = "OK" if published else "FAIL"
        print(
            f"[TX] pin={self.pin} name={self.name} value={value} "
            f"-> backend {status}"
        )
        return published

    def _publish(self, topic: str, payload: dict, retain: bool) -> bool:
        if self._client is None or not self._client.is_connected():
            return False
        try:
            info = self._client.publish(topic, json.dumps(payload), retain=retain)
            return info.rc == 0
        except Exception as exc:
            print(f"Send publish error: {exc}")
            return False
