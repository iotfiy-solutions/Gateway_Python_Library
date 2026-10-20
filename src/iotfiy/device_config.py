"""Device / MQTT configuration (mirrors Arduino DeviceConfig)."""


class DeviceConfig:
    def __init__(self):
        self._ssid = ""
        self._password = ""
        self._mqtt_server = ""
        self._mqtt_port = 1883
        self._mqtt_client_id = ""
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

    def client_id(self, value: str):
        self._mqtt_client_id = value or ""
        return self

    def device_id(self, value: str):
        self._device_id = value or ""
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
        return self._mqtt_client_id

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
        return bool(
            self._mqtt_server
            and self._mqtt_client_id
            and self._device_id
        )
