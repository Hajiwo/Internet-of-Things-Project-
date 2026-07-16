# Smart Garage IoT Hardware and Backend Interface

**Audience:** Backend and AI-planner developers  
**Document status:** Current hardware-integration state  
**Last updated:** 2026-07-15  
**Hardware platform:** Raspberry Pi 5 + GrovePi+

This document defines the hardware setup and the MQTT interface between the Raspberry Pi hardware client, the backend, and the AI planner.

## 1. Integration Summary

The Raspberry Pi hardware client has passed individual and integrated tests. It can:

- publish temperature and light data to the backend through Mosquitto;
- subscribe to fan, light, and entrance-gate commands from the backend;
- control a fan through a relay, a light through an LED, and the entrance gate through a servo;
- display local temperature, humidity, light, fan, and gate status on the LCD.

Parking and vehicle-event messages are supported by the backend protocol and can be added to the hardware client. The LCD is updated locally and does not require a separate backend command. DHT11 humidity is currently displayed locally only; the backend currently uses temperature but not humidity.

## 2. Network Configuration

| Item | Value |
|---|---|
| MQTT broker | Mosquitto running on the Raspberry Pi |
| Broker address from the Raspberry Pi | `localhost:1883` |
| Broker address from the Windows backend | `10.81.212.71:1883` |
| MQTT QoS | `1` |
| Hardware client ID | `raspberrypi` |
| Backend client ID | `backend` |

The backend setting `mqtt_broker_addr` in `config/settings.py` must be changed from `localhost` to `10.81.212.71` when the backend runs on Windows and the broker runs on the Raspberry Pi.

## 3. System Data Flow

```text
A0 light sensor ─┐
D2 DHT11        ├──> Raspberry Pi hardware client
D4 button       ┘             │
                              │ MQTT sensor/event messages (JSON object, QoS 1)
                              ▼
                    Mosquitto on Raspberry Pi
                         10.81.212.71:1883
                              │
                              ▼
                    Windows backend / ContextManager
                              │
                              ▼
                           AIPlanner
                              │
                              │ MQTT actuator command (JSON string, QoS 1)
                              ▼
                    Raspberry Pi hardware subscriber
                    ├── D3 relay    -> fan
                    ├── D8 LED      -> garage light
                    ├── GPIO18 servo -> entrance gate
                    └── I2C LCD     -> local status display
```

## 4. Hardware Mapping

| Device | Interface | Purpose | Raspberry Pi operation | Status |
|---|---|---|---|---|
| Grove Light Sensor (P) v1.0 | A0 | Read light level (raw ADC 0–1023) | `grovepi.analogRead(0)` | Tested |
| DHT11 | D2 | Read temperature and humidity | `grovepi.dht(2, 0)` | Tested |
| Grove Relay | D3 | Switch fan power | `grovepi.digitalWrite(3, state)` | Tested |
| Grove Button | D4 | Manual trigger or parking simulation | `grovepi.digitalRead(4)` | Tested |
| Grove LED | D8 | Garage-light actuator | `grovepi.digitalWrite(8, state)` | Tested |
| Grove LCD RGB Backlight V4.0 | I2C | Display local status | `setText` / `setRGB` | Tested |
| 9g servo | GPIO18 / physical pin 12 | Entrance gate actuator | `gpiozero.Servo` | Tested |

### Servo wiring

- Red wire → 5 V, physical pin 2 or 4
- Brown/black wire → GND, physical pin 6
- Signal wire → GPIO18, physical pin 12

The current test is unloaded. For a loaded gate mechanism, use a separate 5 V supply and connect its ground to the Raspberry Pi ground.

## 5. Raspberry Pi Software Environment

### Required paths

- GrovePi driver: `/home/pi/GrovePi/Software/Python/grovepi.py`
- `di_i2c` dependency: `/home/pi/RFR_Tools/miscellaneous/di_i2c.py`
- Python virtual environment: `~/grovepi-venv`

Run the hardware program with the virtual-environment Python and both required paths in `PYTHONPATH`:

```bash
source ~/grovepi-venv/bin/activate
PYTHONPATH="$HOME/RFR_Tools/miscellaneous:$HOME/GrovePi/Software/Python" \
python "$HOME/grovepi_test/smart_garage_mqtt.py"
```

### Raspberry Pi 5 compatibility changes

In `grovepi.py`, use the Raspberry Pi 5 bus identifier:

```python
set_bus("RPI_1")  # The original RPI_1SW is not recognized on Raspberry Pi 5.
```

For the current hardware I2C path, the digital input value is in the first returned byte:

```python
def digitalRead(pin):
    write_i2c_block(dRead_cmd + [pin, unused, unused])
    data = read_i2c_block(no_bytes=1)
    return data[0]
```

## 6. MQTT Contract

### General rules

1. The production broker is Mosquitto on the Raspberry Pi at port `1883`.
2. Sensor and event payloads must be JSON objects.
3. Actuator payloads are JSON strings such as `"on"` or `"open"`.
4. All messages use QoS 1.
5. Each topic has an independent `sequence_number`, starting at `1` and increasing by one.
6. The backend ignores duplicate or older sequence numbers for a topic.

### 6.1 Raspberry Pi → Backend: sensor and event messages

#### Temperature

**Topic:** `garage/sensor/temperature`

```json
{
  "sequence_number": 1,
  "temperature": 25.0
}
```

The current backend goal is `fan = on` when `temperature >= 30.0`; below `30.0`, it can plan `fan = off` when the fan is on.

#### Light

**Topic:** `garage/sensor/light`

```json
{
  "sequence_number": 1,
  "lux": 350.0
}
```

The Grove sensor returns a raw ADC value from `0` to `1023`, not calibrated lux. During testing this value may be sent in the `lux` field, but `lux_dark_threshold = 100.0` must be calibrated against measurements or replaced by a hardware-side conversion formula.

#### Optional humidity field

The hardware may retain humidity locally or include it in the temperature message:

```json
{
  "sequence_number": 1,
  "temperature": 25.0,
  "humidity": 55.0
}
```

The current backend ignores `humidity`. Supporting humidity-based fan control requires new context fields, message handling, PDDL predicates, and tests.

#### Parking occupancy (optional)

**Topic:** `garage/sensor/parking`

```json
{
  "sequence_number": 1,
  "position": 0,
  "on_occupy": true
}
```

The D4 button has been used successfully to simulate parking position `0`. The final hardware program should either use D4 for this simulation or reserve it as a local manual-control button, and document the selected mode.

#### Vehicle entry event

**Topic:** `garage/camera/vehicle_entry`

```json
{
  "sequence_number": 1,
  "license_plate": "TEST001",
  "enter_time": "2026-07-15T14:30:00"
}
```

#### Vehicle exit event

**Topic:** `garage/camera/vehicle_exit`

```json
{
  "sequence_number": 1,
  "license_plate": "TEST001"
}
```

### 6.2 Backend → Raspberry Pi: actuator commands

| Topic | Payload | Hardware | Interface | Local action |
|---|---|---|---|---|
| `garage/actuator/fan` | `"on"` / `"off"` | Relay | D3 | Connect/disconnect fan power |
| `garage/actuator/light` | `"on"` / `"off"` | LED | D8 | Turn garage light on/off |
| `garage/actuator/entrance` | `"open"` / `"close"` | 9g servo | GPIO18 | Open/close entrance gate |
| `garage/actuator/exit` | `"open"` / `"close"` | Not connected | — | Reserved for future hardware |

The Raspberry Pi subscriber should accept both a JSON string and a quoted/raw string:

```python
text = message.payload.decode("utf-8").strip()
try:
    command = json.loads(text)
except json.JSONDecodeError:
    command = text.strip('"')
command = command.lower()
```

## 7. Hardware Execution Logic

- **Fan:** `"on"` sets D3 to `1`; `"off"` sets D3 to `0`. Set D3 to `0` during shutdown.
- **Light:** `"on"` sets D8 to `1`; `"off"` sets D8 to `0`. Set D8 to `0` during shutdown.
- **Entrance gate:** `"open"` moves the servo to `OPEN`; `"close"` moves it to `CLOSED`. Move for approximately 0.5 seconds, then detach.
- **LCD:** Display temperature, humidity, light, fan, and gate state locally. Suggested colors are green for an open gate, orange for an active fan, and blue for normal status.
- **Publishing interval:** Publish sensor data approximately every 2 seconds. Do not read the DHT11 at a high frequency.
- **MQTT receiving:** Run the MQTT network loop in a separate thread, for example with `loop_start`, so actuator commands can be received while sensors are sampled.

## 8. Entrance-Gate Planning Rule

Temperature and light messages alone do not open the entrance gate. The current planner requires a `vehicle_entry` event and at least one free parking position before it produces `open-entrance-gate`.

- When the garage is full, no entrance-open command should be sent.
- The planner may produce `close-entrance-gate`; the demonstration workflow must define when that command is expected.
- The backend should maintain separate sequence numbers for all topics.

## 9. Backend Integration Checklist

- [ ] Set `config/settings.py:mqtt_broker_addr` to `10.81.212.71` for a Windows backend.
- [ ] Keep the broker port at `1883` unless the Mosquitto configuration changes.
- [ ] Subscribe to temperature and light topics.
- [ ] Subscribe to parking and vehicle-event topics when those features are enabled.
- [ ] Keep actuator topics and payloads exactly as specified above, including JSON-string quoting.
- [ ] Confirm the temperature threshold (`30.0 °C`).
- [ ] Calibrate the light threshold against the raw A0 ADC values.
- [ ] Decide whether humidity remains local-only or becomes a backend input.
- [ ] Define when the entrance-gate close command is generated.
- [ ] Maintain an independent `sequence_number` for each topic.

## 10. Integration Acceptance Tests

| Test case | Raspberry Pi input | Expected backend output | Expected hardware result |
|---|---|---|---|
| High temperature | `temperature = 35` | `garage/actuator/fan -> "on"` | D3 relay closes; fan on; LCD shows `F=ON` |
| Temperature restored | `temperature = 25` | `garage/actuator/fan -> "off"` | D3 relay opens; fan off |
| Dark garage | `lux` below threshold | `garage/actuator/light -> "on"` | D8 LED on |
| Bright garage | `lux` above threshold | `garage/actuator/light -> "off"` | D8 LED off |
| Vehicle enters with free space | `vehicle_entry` | `garage/actuator/entrance -> "open"` | GPIO18 servo opens gate |
| Garage is full | All parking positions occupied + `vehicle_entry` | No entrance-open command | Servo does not move |

## 11. References

- Backend repository: <https://github.com/Hajiwo/Internet-of-Things-Project->
- MQTT contract: <https://github.com/Hajiwo/Internet-of-Things-Project-/blob/main/docs/message_format.md>

This document is based on the current backend README, `config/settings.py`, MQTT topic definitions, and the Raspberry Pi hardware test results.
