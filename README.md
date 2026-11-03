# IOTFIY (Python)

MQTT gateway client for **Raspberry Pi 3 / 4 / 5**, matching the Arduino IOTFIY library API.

| | |
|---|---|
| **Version** | 1.0.1 |
| **PyPI** | `pip install iotfiy` |
| **Requires** | Python 3.9+, `paho-mqtt` |

---

## Features

- WiFi credentials + device id only in user code (MQTT broker / auth / LWT built in)
- Device id may be **plain** or **Base64** (decoded inside the library; used for topics and MQTT client id)
- `write()` / `read()` — type inferred from the variable; name optional (defaults to pin)
- Connection maintain, MQTT reconnect, and message processing inside `launch()`
- Up to **10** outputs and **10** controls

---

## Install

```bash
pip install iotfiy
```

Optional GPIO helpers: `pip install iotfiy[gpio]`

---

## Typical flow

```text
IOTFIY.config(ssid, password, device_id)
IOTFIY.begin()
IOTFIY.write(...)
IOTFIY.read(...)
IOTFIY.launch()

loop:
  update your variables
  IOTFIY.launch()
```

On Raspberry Pi, the OS manages Wi-Fi. `ssid` / `password` match the Arduino API.

---

## Quick start

Python has no `float*` — use a **one-element list** as the mutable variable (Arduino pointer equivalent):

```python
import time
from iotfiy import IOTFIY

WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
DEVICE_ID = "device_1"  # or Base64-encoded id

sensor = [0.0]      # -> type "float"
control = [0.0]
battery = [0]       # -> type "integer"

IOTFIY.config(WIFI_SSID, WIFI_PASSWORD, DEVICE_ID)
IOTFIY.begin()

IOTFIY.write("A0", sensor)                    # name = "A0"
IOTFIY.read("Ctrl", control, 0, 100)          # name = "Ctrl"
IOTFIY.write("battery", "V9", battery, 0, 100)

IOTFIY.launch()

while True:
    sensor[0] = (sensor[0] + 1.0) % 100.0
    IOTFIY.launch()
    time.sleep(0.05)
```

**Serial-style console**

- `WiFi: connected (MQTT host reachable)` / `not connected`
- `MQTT: connected` / `not connected`
- `Device ID decoded from Base64: ...` when applicable
- `Send data ... published: SUCCESS`

---

## Configuration

### `config(ssid, password, device_id)`

| Parameter | Meaning |
|-----------|---------|
| `ssid` / `password` | WiFi (API parity; OS usually already connected on Pi) |
| `device_id` | Topic prefix + MQTT client id (plain or Base64) |

MQTT host, port, username, and password are fixed inside the library for the IOTFIY gateway.

---

## API

Global instance: `IOTFIY`.

### `begin()`

Creates the MQTT client and applies LWT. Call after `config()`. Does not connect — call `launch()`.

### `launch()`

Call often (and once after `write` / `read` in setup):

1. Check network path to the broker  
2. Reconnect MQTT if needed (re-subscribe, re-register capabilities)  
3. Process incoming commands  
4. Print WiFi / MQTT status when it changes  
5. Publish `write()` values **only when they change** (with min/max **wrap**)

### `is_mqtt_connected()`

Optional status helper.

### `write(...)` / `read(...)`

| Form | Notes |
|------|--------|
| `(pin, var)` | Name = pin; type from `var` |
| `(pin, var, min, max)` | Same + range |
| `(name, pin, var)` | Explicit name |
| `(name, pin, var, min, max)` | Explicit name + range |
| `(name, type, pin, var)` | Explicit type override |
| `(name, type, pin, var, min, max)` | Explicit type + range |

`var` must be a **one-element list**:

| List element | Capability type |
|--------------|-----------------|
| `float` | `"float"` |
| `int` | `"integer"` |
| `bool` | `"boolean"` |
| `str` | `"string"` |

```python
IOTFIY.write("V9", battery, 0, 100)
IOTFIY.write("weather", "V7", temperature)
IOTFIY.read("V4", color)                 # color = [""]
IOTFIY.read("power", "boolean", "V1", power)  # explicit type if needed
```

### `publish_string_output(name, pin, value)`

One-shot string output without a prior `write()`.

---

## MQTT topics

Same as Arduino (`{deviceId}` = decoded device id):

| Topic | Role |
|-------|------|
| `devices/{deviceId}/data` | Outputs |
| `devices/{deviceId}/status` | Online / offline / registration |
| `devices/{deviceId}/commands` | Dashboard → device |
| `devices/{deviceId}/command-response` | Command result |
| `devices/{deviceId}/capabilities_output/{name}` | Output capability |
| `devices/{deviceId}/capabilities_control/{name}` | Control capability |

LWT is always on: retained offline will on unexpected disconnect; online published after connect.

---

## Example

[`examples/raspberry_pi_basic.py`](examples/raspberry_pi_basic.py) — GPS-style floats + keyboard buttons A/B/C.

```bash
python examples/raspberry_pi_basic.py
```

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Config error | Call `config(ssid, password, device_id)` then `begin()` |
| Network unreachable | Pi online; path to gateway; port 1883 |
| No dashboard updates | Change `var[0]`, then `launch()` |
| Commands ignored | Call `launch()` often; match name/pin |
| `TypeError` on write/read | Pass a one-element list, e.g. `sensor = [0.0]` |

---

## Layout

```text
pyproject.toml
README.md
src/iotfiy/
  __init__.py
  client.py
  device_config.py
  send.py
  receive.py
examples/
  raspberry_pi_basic.py
```

---

## Support

Maintainer: **iotfiy.solution@gmail.com**
