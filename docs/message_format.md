# Smart Garage MQTT Message Format

This document is the hardware-facing MQTT contract for the Smart Garage backend.
It is based on the current project implementation, especially:

- [config/settings.py](../config/settings.py)
- [mqtt/topics.py](../mqtt/topics.py)
- [context/manager.py](../context/manager.py)
- [planner/problem_generator.py](../planner/problem_generator.py)
- [executor/executor.py](../executor/executor.py)
- [services/backend_service.py](../services/backend_service.py)
- [RP_Simulator.py](../RP_Simulator.py)

An external Raspberry Pi hardware client publishes sensor/event messages to the
backend and subscribes to actuator command topics. During software-only testing,
`RP_Simulator.py` provides the local broker, sensor publisher, and actuator
subscriber. The dashboard camera buttons create events directly inside the
backend; they do not publish camera input back through MQTT.

```text
sensor/event MQTT message
  -> ContextManager updates backend Context
  -> AI planner creates actuator actions
  -> Executor converts actions to MQTT commands
  -> hardware receives actuator command
```

---

## 1. General Rules

### Transport

The real backend uses MQTT through `paho-mqtt`.

Hardware MQTT settings:

| Setting | Value |
|---|---|
| Broker host | Configured by `MQTT_BROKER_ADDR` (for example `10.81.212.71`) |
| Broker port | `1883` |
| Backend client id | `backend` |
| Raspberry Pi client id | `raspberrypi` |
| QoS | `1` |

The simulator uses a local JSON-lines TCP broker on:

| Setting | Value |
|---|---|
| Host | `127.0.0.1` |
| Port | `18830` |

The default `.env` selects simulation mode:

```dotenv
SMART_GARAGE_MODE=simulation
SIMULATOR_HOST=127.0.0.1
SIMULATOR_PORT=18830
```

To connect to the physical Raspberry Pi, use:

```dotenv
SMART_GARAGE_MODE=hardware
MQTT_BROKER_ADDR=10.81.212.71
MQTT_BROKER_PORT=1883
```

### Message Encoding

Sensor/event messages sent to the backend must be JSON objects.

Example:

```json
{
  "sequence_number": 1,
  "temperature": 35.0
}
```

Actuator commands sent by the backend are string command values:

```json
"on"
```

```json
"open"
```

In real MQTT, the backend JSON-encodes the command value before publishing, so the
wire payload is a JSON string. In the simulator, the actuator monitor prints the
raw command value, for example `on` or `open`.

### Sequence Number

Every sensor/event topic has an independent sequence number. The backend processes
a message only when its sequence number is larger than the previous sequence number
seen on the same topic.

Preferred field:

```json
{
  "sequence_number": 1
}
```

Important:

- Start at `1` or higher. A missing or non-integer sequence number is rejected.
- Increase the sequence number separately for each topic.
- Re-sending the same sequence number will be treated as a duplicate and ignored.
- The camera API reserves its own sequence number before sending the event into the
  backend event-processing path.

---

## 2. Backend Input Topics

The backend subscribes to these five topics:

| Topic | Source | Purpose |
|---|---|---|
| `garage/sensor/temperature` | Temperature sensor | Update garage temperature |
| `garage/sensor/light` | Light sensor | Update garage lux level |
| `garage/sensor/parking` | Parking sensors | Update parking occupancy |
| `garage/camera/vehicle_entry` | Camera/license recognition software | Vehicle wants to enter |
| `garage/camera/vehicle_exit` | Camera/license recognition software | Vehicle wants to leave |

---

## 3. Sensor And Event Messages

### 3.1 Temperature Sensor

Topic:

```text
garage/sensor/temperature
```

Payload:

```json
{
  "sequence_number": 1,
  "temperature": 35.0
}
```

Fields:

| Field | Type | Required | Description |
|---|---:|---:|---|
| `sequence_number` | int | yes | Sequence number for this topic |
| `temperature` | number | yes | Current garage temperature |

Backend effect:

```text
context.temperature = payload["temperature"]
```

Planning rule:

| Condition | Planner action | Actuator command |
|---|---|---|
| `temperature >= 30.0` and fan is off | `turn-on-fan` | `garage/actuator/fan -> "on"` |
| `temperature < 30.0` and fan is on | `turn-off-fan` | `garage/actuator/fan -> "off"` |

Example:

```json
{
  "sequence_number": 10,
  "temperature": 35.0
}
```

Expected backend output:

```text
Topic: garage/actuator/fan
Payload: "on"
```

---

### 3.2 Light Sensor

Topic:

```text
garage/sensor/light
```

Payload:

```json
{
  "sequence_number": 1,
  "lux": 20.0
}
```

Fields:

| Field | Type | Required | Description |
|---|---:|---:|---|
| `sequence_number` | int | yes | Sequence number for this topic |
| `lux` | number | yes | Current garage light intensity |

Backend effect:

```text
context.lux = payload["lux"]
```

Planning rule:

| Condition | Planner action | Actuator command |
|---|---|---|
| `lux <= 100.0` and light is off | `turn-on-light` | `garage/actuator/light -> "on"` |
| `lux > 100.0` and light is on | `turn-off-light` | `garage/actuator/light -> "off"` |

Example:

```json
{
  "sequence_number": 8,
  "lux": 20.0
}
```

Expected backend output:

```text
Topic: garage/actuator/light
Payload: "on"
```

---

### 3.3 Parking Occupancy Sensor

Topic:

```text
garage/sensor/parking
```

Payload when a parking position becomes occupied:

```json
{
  "sequence_number": 1,
  "position": 2,
  "on_occupy": true
}
```

Payload when a parking position becomes free:

```json
{
  "sequence_number": 2,
  "position": 2,
  "on_occupy": false
}
```

Fields:

| Field | Type | Required | Description |
|---|---:|---:|---|
| `sequence_number` | int | yes | Sequence number for this topic |
| `position` | int | yes | Parking position index |
| `on_occupy` | bool | yes | `true` means occupied, `false` means free |

Current parking configuration:

```text
parking_size = 3
valid positions = 0, 1, 2
```

Backend effect:

```text
context.positions_occupied[position] = payload["on_occupy"]
```

Validation behavior:

- If `position` is outside `0 <= position < parking_size`, the backend ignores the parking update.
- `on_occupy` should be a real JSON boolean, not a string.

Planning rule:

Parking occupancy is used to decide whether the garage is full.

| Condition | Planner behavior |
|---|---|
| All parking positions are occupied | New vehicle entry will not open the entrance gate |
| At least one position is free | A vehicle entry event can open the entrance gate |

Parking messages usually do not directly create an actuator command by themselves.
They change whether later vehicle-entry events are allowed to open the entrance gate.

---

### 3.4 Vehicle Entry Event

Topic:

```text
garage/camera/vehicle_entry
```

Payload:

```json
{
  "sequence_number": 1,
  "license_plate": "BN9123",
  "enter_time": "2026-07-02T15:30:20"
}
```

Fields:

| Field | Type | Required | Description |
|---|---:|---:|---|
| `sequence_number` | int | yes | Sequence number for this topic |
| `license_plate` | string | yes | Vehicle license plate |
| `enter_time` | string | yes | Vehicle entry time; ISO format is recommended |

Compatibility:

The backend also accepts `license` instead of `license_plate`:

```json
{
  "sequence_number": 1,
  "license": "BN9123",
  "enter_time": "2026-07-02T15:30:20"
}
```

Backend effect:

```text
context.current_vehicles[license_plate] = enter_time
context.vehicle_waiting_to_enter = true
```

Planning rule:

| Condition | Planner action | Actuator command |
|---|---|---|
| Vehicle waiting to enter and garage is not full | `open-entrance-gate` | `garage/actuator/entrance -> "open"` |
| Vehicle waiting to enter but garage is full | no entrance-open action | no entrance command |

Expected backend output when space is available:

```text
Topic: garage/actuator/entrance
Payload: "open"
```

---

### 3.5 Vehicle Exit Event

Topic:

```text
garage/camera/vehicle_exit
```

Payload:

```json
{
  "sequence_number": 1,
  "license_plate": "BN9123"
}
```

Fields:

| Field | Type | Required | Description |
|---|---:|---:|---|
| `sequence_number` | int | yes | Sequence number for this topic |
| `license_plate` | string | yes | Vehicle license plate |

Compatibility:

The backend also accepts `license` instead of `license_plate`:

```json
{
  "sequence_number": 1,
  "license": "BN9123"
}
```

Backend effect:

```text
del context.current_vehicles[license_plate]
context.vehicle_waiting_to_leave = true
```

Important behavior:

If the license plate is not currently known in `context.current_vehicles`, the
backend logs a warning, still marks a vehicle as waiting to leave, and continues
running. Hardware/software should normally publish an exit event only for a known
vehicle.

Planning rule:

| Condition | Planner action | Actuator command |
|---|---|---|
| Vehicle waiting to leave | `open-exit-gate` | `garage/actuator/exit -> "open"` |

Expected backend output:

```text
Topic: garage/actuator/exit
Payload: "open"
```

---

## 4. Backend Output Topics

The backend publishes actuator commands to these four topics:

| Topic | Hardware actuator | Payload values |
|---|---|---|
| `garage/actuator/fan` | Fan | `"on"`, `"off"` |
| `garage/actuator/light` | Light | `"on"`, `"off"` |
| `garage/actuator/entrance` | Entrance gate | `"open"`, `"close"` |
| `garage/actuator/exit` | Exit gate | `"open"`, `"close"` |

### 4.1 Fan Command

Topic:

```text
garage/actuator/fan
```

Payloads:

```json
"on"
```

```json
"off"
```

Hardware behavior:

- `"on"`: turn fan on.
- `"off"`: turn fan off.

Generated from planner actions:

| Planner action | Command |
|---|---|
| `turn-on-fan` | `"on"` |
| `turn-off-fan` | `"off"` |

---

### 4.2 Light Command

Topic:

```text
garage/actuator/light
```

Payloads:

```json
"on"
```

```json
"off"
```

Hardware behavior:

- `"on"`: turn light on.
- `"off"`: turn light off.

Generated from planner actions:

| Planner action | Command |
|---|---|
| `turn-on-light` | `"on"` |
| `turn-off-light` | `"off"` |

---

### 4.3 Entrance Gate Command

Topic:

```text
garage/actuator/entrance
```

Payloads:

```json
"open"
```

```json
"close"
```

Hardware behavior:

- `"open"`: open the entrance gate.
- `"close"`: close the entrance gate.

Generated from planner actions:

| Planner action | Command |
|---|---|
| `open-entrance-gate` | `"open"` |
| `close-entrance-gate` | `"close"` |

---

### 4.4 Exit Gate Command

Topic:

```text
garage/actuator/exit
```

Payloads:

```json
"open"
```

```json
"close"
```

Hardware behavior:

- `"open"`: open the exit gate.
- `"close"`: close the exit gate.

Generated from planner actions:

| Planner action | Command |
|---|---|
| `open-exit-gate` | `"open"` |
| `close-exit-gate` | `"close"` |

---

## 5. Full Interaction Examples

### Example A: Temperature Turns Fan On

Hardware publishes:

```text
Topic: garage/sensor/temperature
```

```json
{
  "sequence_number": 1,
  "temperature": 35.0
}
```

Backend context update:

```text
context.temperature = 35.0
```

Planner action:

```text
turn-on-fan
```

Hardware receives:

```text
Topic: garage/actuator/fan
Payload: "on"
```

---

### Example B: Dark Garage Turns Light On

Hardware publishes:

```text
Topic: garage/sensor/light
```

```json
{
  "sequence_number": 1,
  "lux": 20.0
}
```

Backend context update:

```text
context.lux = 20.0
```

Planner action:

```text
turn-on-light
```

Hardware receives:

```text
Topic: garage/actuator/light
Payload: "on"
```

---

### Example C: Vehicle Entry Opens Entrance Gate

Hardware/software publishes:

```text
Topic: garage/camera/vehicle_entry
```

```json
{
  "sequence_number": 1,
  "license_plate": "BN9123",
  "enter_time": "2026-07-02T15:30:20"
}
```

Backend context update:

```text
context.current_vehicles["BN9123"] = "2026-07-02T15:30:20"
context.vehicle_waiting_to_enter = true
```

Planner action when garage is not full:

```text
open-entrance-gate
```

Hardware receives:

```text
Topic: garage/actuator/entrance
Payload: "open"
```

---

### Example D: Full Garage Blocks Entry Gate

Hardware publishes parking occupancy messages:

```json
{
  "sequence_number": 1,
  "position": 0,
  "on_occupy": true
}
```

```json
{
  "sequence_number": 2,
  "position": 1,
  "on_occupy": true
}
```

```json
{
  "sequence_number": 3,
  "position": 2,
  "on_occupy": true
}
```

Backend context:

```text
context.positions_occupied = [true, true, true]
garage-full = true
```

Then a vehicle entry event arrives:

```json
{
  "sequence_number": 1,
  "license_plate": "BN9123",
  "enter_time": "2026-07-02T15:30:20"
}
```

Planner result:

```text
No open-entrance-gate action, because the garage is full.
```

---

### Example E: Vehicle Exit Opens Exit Gate

Hardware/software publishes:

```text
Topic: garage/camera/vehicle_exit
```

```json
{
  "sequence_number": 1,
  "license_plate": "BN9123"
}
```

Backend context update:

```text
context.current_vehicles removes "BN9123"
context.vehicle_waiting_to_leave = true
```

Planner action:

```text
open-exit-gate
```

Hardware receives:

```text
Topic: garage/actuator/exit
Payload: "open"
```

---

## 6. Software-only Raspberry Pi Simulator

The supported software-only workflow uses two terminals:

Terminal 1:

```bash
python3 RP_Simulator.py
```

Terminal 2:

```bash
python3 main.py
```

`RP_Simulator.py` starts the local JSON-lines broker at `127.0.0.1:18830`,
publishes temperature/light/parking messages every two seconds, subscribes to all
actuator topics, and prints the commands received from the backend. Its console
commands can change temperature, light, and parking occupancy.

The older files under `tests/` remain useful for focused simulator tests, but they
are not required for the standard two-terminal workflow.

## 7. Dashboard Camera API

The web dashboard exposes these endpoints:

| Endpoint | Behavior |
|---|---|
| `GET /api/state` | Return Context, parking state, recent events, and actuator commands |
| `POST /api/camera/enter` | Capture a plate, create a `vehicle_entry` event directly in the backend, then plan/publish the actuator command |
| `POST /api/camera/exit` | Capture a plate, create a `vehicle_exit` event directly in the backend, then plan/publish the actuator command |

The dashboard camera API does not publish `garage/camera/vehicle_entry` or
`garage/camera/vehicle_exit` over MQTT. Those topics remain supported for an
external camera client. For the built-in API, only the final actuator command is
published over MQTT (or delivered to the simulator broker).

---

## 8. Hardware Checklist

Before integrating hardware, confirm these points:

1. Publish sensor/event payloads as JSON objects.
2. Use `sequence_number` and increase it independently for each topic.
3. Use JSON numbers for `temperature`, `lux`, and `position`.
4. Use JSON booleans for `on_occupy`: `true` or `false`.
5. Subscribe to every actuator topic controlled by the hardware.
6. Treat actuator payloads as command strings: `"on"`, `"off"`, `"open"`, `"close"`.
7. Do not publish vehicle-exit events for unknown vehicles.
8. Use parking positions `0`, `1`, and `2` unless `parking_size` is changed in settings.

---

## 9. Quick Reference

### Hardware Publishes To Backend

| Topic | Required fields |
|---|---|
| `garage/sensor/temperature` | `sequence_number`, `temperature` |
| `garage/sensor/light` | `sequence_number`, `lux` |
| `garage/sensor/parking` | `sequence_number`, `position`, `on_occupy` |
| `garage/camera/vehicle_entry` | `sequence_number`, `license_plate`, `enter_time` |
| `garage/camera/vehicle_exit` | `sequence_number`, `license_plate` |

### Backend Publishes To Hardware

| Topic | Payload values |
|---|---|
| `garage/actuator/fan` | `"on"`, `"off"` |
| `garage/actuator/light` | `"on"`, `"off"` |
| `garage/actuator/entrance` | `"open"`, `"close"` |
| `garage/actuator/exit` | `"open"`, `"close"` |
