# iotfiy

Python client for the IOTFIY MQTT gateway on **Raspberry Pi 3 / 4 / 5**. Register outputs (sensors, buttons, GPS-style values) and controls (dashboard → Pi), then publish and receive JSON over MQTT.

**PyPI package:** [`iotfiy`](https://pypi.org/project/iotfiy/)  
**Version:** 1.0.0  
**Requires:** Python **3.9+**

The public import surface is:

```python
from iotfiy import IOTFIY, Ref, IOTFIYManager
```

---

## Features

- MQTT connect with optional username/password (`paho-mqtt`)
- Optional Last Will (LWT) for offline status
- `write()` / `read()` / `launch()` for pin-style I/O
- Capability registration after a successful MQTT connect
- Up to **10** outputs and **10** controls
- Console logs for TX/RX (`[TX]`, `[RX]`)

On the Pi, Wi-Fi is normally handled by the OS. `ssid` / `password` in `config()` are kept for API compatibility; they are **not** used to bring Wi-Fi up. `check_and_reconnect_wifi()` only checks that the MQTT host:port is reachable over TCP.

---

## Install

### From PyPI

```bash
pip install iotfiy
# or
pip3 install iotfiy
```

### Optional GPIO extras

`pyproject.toml` defines an optional extra that installs `gpiozero`. The core library does **not** import GPIO itself; use this if your own sketch uses gpiozero:

```bash
pip install "iotfiy[gpio]"
```

### From a local clone (development)

```bash
cd /path/to/this/project   # folder that contains pyproject.toml
pip install -e .
```

### Dependency

| Package | Constraint |
|---------|------------|
| `paho-mqtt` | `>=1.6.1` (works with 1.x and 2.x clients) |

---

## Typical flow

```text
IOTFIY.config(...)
IOTFIY.enable_lwt(True)          # optional; call before begin()
IOTFIY.check_and_reconnect_wifi()
IOTFIY.begin()
IOTFIY.write(..., Ref(...))
IOTFIY.read(..., Ref(...))
IOTFIY.reconnect_mqtt()

while True:
    check_and_reconnect_wifi()
    reconnect_mqtt() if needed
    process_mqtt_messages()      # call often
    update Ref.value
    IOTFIY.launch()
```

Use a broker **hostname or IP** (for example `192.168.1.10`). Do not use an `mqtt://` URL prefix.

---

## Quick start

```python
import time
from iotfiy import IOTFIY, Ref

MQTT_SERVER = "YOUR_MQTT_HOST"
MQTT_CLIENT_ID = "rpi_client_1"
DEVICE_ID = "device_rpi_1"
MQTT_PORT = 1883
MQTT_USER = ""      # or your broker username
MQTT_PASS = ""

sensor = Ref(0.0)
control = Ref(0.0)

IOTFIY.config(
    "unused_ssid",      # not used for Wi-Fi on Pi
    "unused_password",
    MQTT_SERVER,
    MQTT_CLIENT_ID,
    DEVICE_ID,
    MQTT_PORT,
    MQTT_USER,
    MQTT_PASS,
)
IOTFIY.enable_lwt(True)
IOTFIY.check_and_reconnect_wifi()
IOTFIY.begin()

IOTFIY.write("SensorValue", "float", "A0", sensor)
IOTFIY.read("ControlValue", "float", "Ctrl", control, 0, 100)

IOTFIY.reconnect_mqtt()

last = 0.0
while True:
    IOTFIY.check_and_reconnect_wifi()
    if not IOTFIY.is_mqtt_connected():
        IOTFIY.reconnect_mqtt()
    IOTFIY.process_mqtt_messages()

    now = time.time()
    if now - last >= 3.0:
        last = now
        sensor.value = (sensor.value + 3.0) % 100.0
        IOTFIY.launch()

    time.sleep(0.05)
```

**What you should see**

- `MQTT LWT ENABLED (offline on disconnect)` if LWT is on  
- `MQTT connection attempt N... connected!`  
- Capability lines like `SensorValue output published: SUCCESS`  
- On publish: `[TX] pin=A0 name=SensorValue value=... -> backend OK`  
- Incoming commands: `Message arrived [devices/.../commands] ...` and `[RX] pin=...`

A fuller interactive demo (GPS + keyboard buttons) lives in  
[`examples/raspberry_pi_basic.py`](examples/raspberry_pi_basic.py).

---

## `Ref` — mutable values

Arduino uses `float*` / `String*`. In Python, pass an `iotfiy.Ref`:

```python
from iotfiy import Ref

sensor = Ref(0.0)
sensor.value = 12.5

text = Ref("")
text.value = "hello"
```

`write()` and `read()` both require a `Ref`. Anything else raises `TypeError`.

---

## Configuration

### `IOTFIY.config(...)`

```python
IOTFIY.config(
    ssid: str,
    password: str,
    mqtt_server: str,
    mqtt_client_id: str,
    device_id: str,
    mqtt_port: int = 1883,
    mqtt_username: str = "",
    mqtt_password: str = "",
) -> None
```

| Argument | Notes |
|----------|--------|
| `ssid` / `password` | Stored only; not used to connect Wi-Fi on Pi |
| `mqtt_server` | Required for `begin()` / network check |
| `mqtt_client_id` | Required; use a unique id per device |
| `device_id` | Required; used in all MQTT topic paths |
| `mqtt_port` | Default **1883** |
| `mqtt_username` / `mqtt_password` | Optional; empty = no MQTT auth |

### `IOTFIY.config_obj()` → `DeviceConfig`

Returns the internal config for chainable setters / inspection:

```python
IOTFIY.config_obj().server("192.168.1.10").port(1883).client_id("c1").device_id("d1")
```

Chainable methods: `ssid`, `password`, `server`, `port`, `client_id`, `device_id`, `mqtt_username`, `mqtt_password`.

Read-only properties: `get_ssid`, `get_password`, `get_mqtt_server`, `get_mqtt_port`, `get_mqtt_client_id`, `get_device_id`, `get_mqtt_username`, `get_mqtt_password`.

Topic helpers: `get_data_topic()`, `get_status_topic()`, `get_commands_topic()`, `get_command_response_topic()`.

### `is_valid()`

`DeviceConfig.is_valid()` is `True` when **mqtt_server**, **mqtt_client_id**, and **device_id** are non-empty. SSID/password are not required for validity on Pi.

`begin()` raises `ValueError` if config is not valid.

---

## API reference (`IOTFIY`)

Global instance: `IOTFIY` (`IOTFIYManager`). Limits: `MAX_SENDS = 10`, `MAX_RECEIVES = 10`.

### `enable_lwt(enabled: bool = True) -> None`

Turns LWT on or off and prints status. Call **before** `begin()` so `will_set(...)` is applied when the client is created.

### `begin() -> None`

Creates the Paho MQTT client (supports paho-mqtt 1.x and 2.x), sets username/password if configured, applies LWT if enabled, binds the client to already-registered sends/receives. Does **not** connect — call `reconnect_mqtt()`.

### `check_and_reconnect_wifi() -> bool`

Opens a TCP connection to `(mqtt_server, mqtt_port)` with a **3 s** timeout.

- Success → `True`  
- Missing host → prints an error, `False`  
- Failure → prints `Network unreachable to MQTT broker. Will retry...`, `False`

### `reconnect_mqtt() -> bool`

- Calls `begin()` if the client is missing  
- If already connected → `True`  
- Else up to **5** attempts: `connect(host, port, keepalive=60)`, then poll `loop` until connected or **8 s** timeout; **5 s** sleep between failed attempts  
- On success: subscribe to commands topic, publish retained **online** status, `register_all_capabilities()`, return `True`  
- Prints `connected!`, `failed (timeout)`, or `failed (<exception>)`

### `is_mqtt_connected() -> bool`

Whether the Paho client exists and reports connected.

### `process_mqtt_messages() -> None`

Runs `client.loop(timeout=0.05)`. Call this in your main loop.

### `write(name, type_, pin, data_source, min_value=None, max_value=None) -> Send | None`

Registers an output. `data_source` must be a `Ref`.

- Returns `None` if already at 10 sends  
- If both `min_value` and `max_value` are set, published values are clamped  

### `read(name, type_, pin, entry_point, min_value=None, max_value=None) -> Receive | None`

Registers a control. `entry_point` must be a `Ref` (use `Ref("")` for string controls).

- Returns `None` if already at 10 receives  
- For types `"float"` / `"integer"`, optional min/max are included in capability JSON  

### `launch() -> None`

Publishes all registered `write()` outputs.

### `publish_string_output(name, pin, value: str) -> bool`

One-shot string output: retained capability + data publish. Returns `False` if not connected.

### `register_all_capabilities() -> None`

Publishes registration start/complete on the status topic and registers every send/receive. Called automatically after a successful `reconnect_mqtt()`; you rarely need to call it yourself.

---

## Send / Receive objects

### `Send`

| Method | Purpose |
|--------|---------|
| `get_name()`, `get_type()`, `get_pin()` | Accessors |
| `get_current_value()` | `float(ref.value)` |
| `set_delay(ms)` | Sleep after capability register (default **50** ms → 0.05 s) |
| `register_capability()` | Retained output capability |
| `publish_data()` | Publish one value; logs `[TX] pin=... name=... value=...` |

### `Receive`

| Method | Purpose |
|--------|---------|
| `get_name()`, `get_type()`, `get_pin()` | Accessors |
| `register_capability()` | Retained control capability |
| `handle_command(value, result)` | Apply command; set `result["newState"]`; logs `[RX]` |

**Handled `type` strings**

| type | Behaviour |
|------|-----------|
| `float` | `Ref.value = float`; clamped if range set |
| `integer` | `Ref.value = int`; clamped if range set |
| `boolean` | `"on"` / `"true"` / `"1"` → `1.0`, else `0.0` |
| `string` | `Ref.value = str(value)` |

Unknown types return `False`.

---

## MQTT topics and payloads

Replace `{deviceId}` with your `device_id`.

| Topic | Role |
|-------|------|
| `devices/{deviceId}/data` | Output values |
| `devices/{deviceId}/status` | Online/offline + registration events |
| `devices/{deviceId}/commands` | Dashboard → device (subscribed on connect) |
| `devices/{deviceId}/command-response` | Handler result |
| `devices/{deviceId}/capabilities_output/{name}` | Output capability (retained) |
| `devices/{deviceId}/capabilities_control/{name}` | Control capability (retained) |

### Output data

```json
{
  "type": "output",
  "deviceId": "device_rpi_1",
  "data": {
    "Latitude": 24.8607,
    "Lat": 24.8607
  }
}
```

### Output capability

```json
{
  "deviceId": "device_rpi_1",
  "type": "capabilities_output",
  "outputName": "Latitude",
  "output": { "type": "float", "pin": "Lat" }
}
```

### Control capability

```json
{
  "deviceId": "device_rpi_1",
  "type": "capabilities_control",
  "controlName": "DashboardNumber",
  "control": { "type": "float", "pin": "Display", "min": 0, "max": 100 }
}
```

### Incoming commands

**Flat:** `{ "value": 25, "control": "DashboardNumber" }` or `"pin": "Display"`.

**Nested** (when both `"type"` and `"data"` are present): value/control/pin under `"data"`.

Match order: control **name** first, else **pin**.

### Command response

```json
{
  "status": "success",
  "control": "DashboardNumber",
  "result": { "newState": 25 }
}
```

### Status

Retained online after connect:

```json
{ "status": "online", "deviceId": "device_rpi_1" }
```

LWT (unexpected disconnect), set in `begin()` when LWT is enabled:

```json
{ "status": "offline", "deviceId": "device_rpi_1" }
```

QoS **1**, retained. Unexpected disconnect also prints `Unexpected MQTT disconnect (rc=...)`.

---

## Raspberry Pi 3 / 4 / 5

| Topic | Detail |
|-------|--------|
| OS | Raspberry Pi OS (or similar Linux) with Python 3.9+ |
| Network | Configure Wi-Fi/Ethernet in the OS before running |
| Hardware GPIO | Not required by the core package; optional `iotfiy[gpio]` installs `gpiozero` for your own code |
| Example input | [`raspberry_pi_basic.py`](examples/raspberry_pi_basic.py) uses keyboard (`a`/`b`/`c`) via `select` on stdin (Linux terminal) |

Same MQTT topic layout as the IOTFIY ESP firmware, so one backend can talk to both.

---

## Example: GPS + buttons

See [`examples/raspberry_pi_basic.py`](examples/raspberry_pi_basic.py).

```bash
pip install iotfiy
# edit MQTT_* placeholders in the example, then:
python examples/raspberry_pi_basic.py
```

| Action | Behaviour |
|--------|-----------|
| Every ~3 s | Updates `Lat` / `Lng` refs and `launch()` |
| `a` / `b` / `c` + Enter | Sets one button Ref to `1`, others `0`, `launch()`, then clears to `0` |
| Dashboard → `Display` | Updates `dashboard_number`; `[RX]` / `[RX-WATCH]` on console |
| `q` + Enter | Quit |

Fill in placeholders only — do not commit real passwords to git.

### Minimal button snippet

```python
btn_a = Ref(0)
IOTFIY.write("ButtonA", "integer", "BtnA", btn_a)
btn_a.value = 1
IOTFIY.launch()
btn_a.value = 0
```

### String control

```python
color = Ref("")
IOTFIY.read("Color", "string", "V4", color)
# after a command: color.value holds the string
```

### String output helper

```python
IOTFIY.publish_string_output("StatusText", "Msg", "ready")
```

---

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| `ModuleNotFoundError: iotfiy` | `pip install iotfiy` with the same `python`/`pip` you use to run the script |
| `ValueError: config incomplete` | Set `mqtt_server`, `mqtt_client_id`, `device_id` before `begin()` |
| `Network unreachable` / TCP fail | Ping broker; open port 1883; confirm host has no `mqtt://` prefix |
| MQTT connect timeout | Broker firewall, wrong port, slow link; library waits ~8 s per attempt |
| Auth failures | Check `mqtt_username` / `mqtt_password` |
| No TX on dashboard | Change `Ref.value`, then call `launch()`; ensure MQTT is connected |
| No RX | Call `process_mqtt_messages()` in a loop; match `read()` name/pin to the command JSON |
| `TypeError: expects an iotfiy.Ref` | Pass `Ref(...)`, not a bare `float` |
| `write`/`read` returns `None` | Already at 10 sends or 10 receives |
| Unicode errors in older terminals | Avoid non-ASCII in print strings (the shipped example uses ASCII hyphens) |

Quick broker check from the Pi:

```bash
python3 -c "import socket; s=socket.create_connection(('YOUR_HOST',1883),5); print('OPEN'); s.close()"
```

---

## Package layout

```text
pyproject.toml
README.md
src/iotfiy/
  __init__.py      # IOTFIY, Ref, IOTFIYManager, __version__
  client.py        # IOTFIYManager
  device_config.py
  ref.py
  send.py
  receive.py
examples/
  raspberry_pi_basic.py
```

---

## Support

Author contact in `pyproject.toml`: **iotfiy.solution@gmail.com**

PyPI: https://pypi.org/project/iotfiy/
