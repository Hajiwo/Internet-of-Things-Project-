# Smart Garage Backend

Smart Garage Backend is the Python backend for an IoT smart garage course project. It receives MQTT sensor messages, keeps the current garage context, uses AI planning to decide actuator actions, and publishes MQTT commands for the hardware side.

The default software-testing mode uses `RP_Simulator.py`, which replaces the
Raspberry Pi sensors, actuators, and local broker. A physical Raspberry Pi is
only required when `SMART_GARAGE_MODE=hardware` is selected.

## A. Project Abstraction

The backend is organized around one main idea:

```text
sensor message -> context update -> AI planning -> actuator command
```

The hardware side publishes sensor data such as temperature, lux, parking occupancy, vehicle entry, and vehicle exit. The backend converts those messages into a `Context`, generates a PDDL planning problem, parses the resulting plan, and sends commands to actuators.

Main responsibilities:

- MQTT layer receives sensor events and publishes actuator commands.
- Context layer stores the current garage state.
- Planner layer generates `problem.pddl`, runs or simulates planning, and returns ordered actions.
- Executor layer converts planner actions into actuator MQTT commands.
- Simulator layer tests the full flow without physical hardware.

Current planning decisions:

- High temperature turns the fan on.
- Low lux turns the light on.
- Vehicle entry opens the entrance gate when the garage is not full.
- Vehicle exit opens the exit gate.
- Normal conditions can turn off fan/light or close gates when appropriate.

Thresholds are defined in [config/settings.py](config/settings.py):

- `temperature_high_threshold = 30.0`
- `lux_dark_threshold = 100.0`

## B. How To Run Tests

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Run all tests:

```bash
python3 -m pytest -q
```

### Hardware integration runtime

The tracked `.env` defaults to software simulation. The simulator provides a
local broker at `127.0.0.1:18830`; no Mosquitto installation is required for
software-only testing.

For a software-only end-to-end run, use two terminals.

Terminal 1 — start the Raspberry Pi simulator:

```bash
python3 RP_Simulator.py
```

Terminal 2 — start the backend and dashboard:

```bash
python3 main.py
```

Open <http://localhost:8080>. The dashboard displays sensor data, Context,
parking occupancy, received events, actuator state, and output commands.

For the low-level MQTT smoke test, use:

```bash
python3 main.py --test-connection
```

`main.py` starts:

- the MQTT sensor/event subscriber;
- the MQTT actuator publisher;
- context updates and AI planning;
- the camera Enter/Exit API;
- the live hardware-debugging dashboard.

The dashboard shows temperature, light, vehicles, parking occupancy, actuator
state, received events, and published commands. Its Enter and Exit buttons
start license-plate recognition and pass the result directly to the backend
Context → Planner → Actuator flow. Enter is disabled while the garage is full;
Exit remains available.

If Fast Downward is installed, configure it with

```bash
FAST_DOWNWARD_EXECUTABLE=/path/to/fast-downward.py python3 main.py
```

When Fast Downward is unavailable, `main.py` automatically uses the equivalent
local hardware-debugging rules so hardware testing can continue.

The default `.env` uses `SMART_GARAGE_MODE=simulation`. The simulator publishes
temperature/light/parking data every two seconds and prints fan/light/gate
commands from the backend. Its interactive console can change sensor values:

```text
temperature   Set temperature
light         Set light reading
parking       Toggle parking position 0-2
hot-dark      Trigger fan and light
normal        Restore normal temperature/light
status        Show all simulated hardware state
```

For the real Raspberry Pi deployment, change `.env` to:

```dotenv
SMART_GARAGE_MODE=hardware
MQTT_BROKER_ADDR=10.81.212.71
MQTT_BROKER_PORT=1883
```

Run only AI planning tests:

```bash
python3 -m pytest \
  tests/test_ai_planner.py \
  tests/test_planner_problem_generator.py \
  tests/test_planner_parser.py \
  tests/test_executor.py \
  -q
```

Run only the full simulation pipeline test:

```bash
python3 -m pytest tests/test_simulation_pipeline.py -q
```

The simulation pipeline test verifies:

```text
sensor_msg -> backend/context/planner/executor -> actuator_msg
```

## C. Project Structure, Workflow, Input, And Output

### Project Structure

```text
.
├── main.py                         # Application entry point
├── config/
│   └── settings.py                 # MQTT topics, thresholds, runtime settings
├── context/
│   ├── context.py                  # Garage state model
│   └── manager.py                  # Updates context from MQTT events
├── RP_Simulator.py                  # Local Raspberry Pi and broker simulator
├── dashboard/
│   ├── server.py                    # Dashboard HTTP server and JSON API
│   └── static/                      # Dashboard HTML, CSS, and JavaScript
├── docs/
│   ├── description.md               # Bilingual system behavior description
│   ├── hardware_setting.md          # Hardware and MQTT handoff document
│   ├── implementation.md            # Hardware integration implementation plan
│   └── message_format.md            # Hardware-facing MQTT protocol document
├── executor/
│   └── executor.py                 # Converts planner actions to actuator commands
├── models/
│   ├── command.py                  # Command model
│   ├── event.py                    # MQTT event model
│   └── plan.py                     # Plan model
├── mqtt/
│   ├── client.py                   # Real MQTT client wrapper
│   ├── publisher.py                # Actuator command publisher
│   ├── simulation_client.py        # Local simulator client
│   └── topics.py                   # Sensor and actuator topic helpers
├── planner/
│   ├── actions.py                  # Planner action model and action names
│   ├── domain.pddl                 # Smart Garage PDDL domain
│   ├── fast_downward.py            # Fast Downward wrapper
│   ├── parser.py                   # Planner output parser
│   ├── planner.py                  # AIPlanner orchestration
│   └── problem_generator.py        # Context to PDDL problem generator
├── tests/
│   ├── broker_simulator.py         # Local JSON-lines broker simulator
│   ├── simulation_publisher.py     # Interactive sensor publisher simulator
│   ├── simulation_subscriber.py    # Backend simulator and actuator monitor
│   └── test_*.py                   # Unit and integration tests
├── simulator/
│   └── broker.py                   # Local JSON-lines broker
└── requirements.txt
```

### Backend Workflow

1. Sensor message arrives from MQTT.
2. `ContextManager` validates sequence number and updates `Context`.
3. `ProblemGenerator` converts `Context` into a PDDL problem.
4. `AIPlanner` runs the planner backend and parses planner output.
5. `Executor` maps planner actions to MQTT actuator commands.
6. `Publisher` sends actuator commands to hardware topics.

### Inputs

The backend accepts sensor/event MQTT messages on:

| Topic | Meaning |
|---|---|
| `garage/sensor/temperature` | Temperature update |
| `garage/sensor/light` | Light intensity update |
| `garage/sensor/parking` | Parking occupancy update |
| `garage/camera/vehicle_entry` | Vehicle wants to enter |
| `garage/camera/vehicle_exit` | Vehicle wants to leave |

Example input:

```json
{
  "sequence_number": 1,
  "lux": 20.0
}
```

### Outputs

The backend publishes actuator commands on:

| Topic | Payloads | Meaning |
|---|---|---|
| `garage/actuator/fan` | `"on"`, `"off"` | Control fan |
| `garage/actuator/light` | `"on"`, `"off"` | Control light |
| `garage/actuator/entrance` | `"open"`, `"close"` | Control entrance gate |
| `garage/actuator/exit` | `"open"`, `"close"` | Control exit gate |

Example output:

```text
Topic: garage/actuator/light
Payload: "on"
```

### Manual Simulator Workflow

Use four terminals from the project root.

Start the local broker simulator:

```bash
python3 tests/broker_simulator.py
```

Start the backend simulator:

```bash
python3 tests/simulation_subscriber.py backend
```

Start the actuator monitor:

```bash
python3 tests/simulation_subscriber.py actuator
```

Start the interactive sensor publisher:

```bash
python3 tests/simulation_publisher.py
```

Then choose a message to publish. For example:

- Temperature `35.0` should publish `garage/actuator/fan -> "on"`.
- Lux `20.0` should publish `garage/actuator/light -> "on"`.
- Vehicle entry should publish `garage/actuator/entrance -> "open"` if the garage is not full.

## D. MQTT Message Format

The project documentation is organized under `docs/`:

- [docs/description.md](docs/description.md): bilingual sensors, Context, and actuator behavior
- [docs/hardware_setting.md](docs/hardware_setting.md): Raspberry Pi wiring and MQTT handoff
- [docs/implementation.md](docs/implementation.md): implementation status and remaining hardware work
- [docs/message_format.md](docs/message_format.md): complete MQTT payload contract

These documents explain sensor messages, actuator commands, example payloads,
backend behavior, simulator usage, and hardware handoff details.
