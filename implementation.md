# Smart Garage Hardware Integration Implementation Plan

**Status:** Backend implementation completed; live Raspberry Pi verification pending  
**Based on:** [hardware_setting.md](hardware_setting.md)  
**Last reviewed:** 2026-07-15

## 1. Objective

Connect the production backend to the Raspberry Pi hardware contract:

```text
Raspberry Pi sensor/event
        -> MQTT client -> ContextManager -> PDDL problem
        -> Fast Downward -> Executor/Publisher
        -> Raspberry Pi actuator
```

The current `main.py` is a manual MQTT connection test. The production runtime must be restored after the interface changes below are implemented and tested.

## 2. Current Gaps

| Priority | Gap | Impact |
|---|---|---|
| P0 | `config/settings.py` defaults to `localhost`, while the Windows backend must reach `10.81.212.71`. | The backend can connect to the wrong broker. |
| P0 | `main.py` publishes a dictionary to the fan topic, but hardware expects a JSON string such as `"on"`. | The Raspberry Pi subscriber may reject the smoke-test command. |
| P0 | The production `main()` flow is commented out. | Sensor messages do not reach the planner and executor. |
| P0 | `ContextManager` never sets `vehicle_waiting_to_enter` or `vehicle_waiting_to_leave`. | Vehicle events cannot reliably trigger gate planning. |
| P1 | Fan, light, and gate state are not updated after commands are published. | Replanning can repeatedly produce the same action. |
| P1 | `MQTTClient.publish` is typed for dictionaries although actuator commands are strings. | Code and protocol disagree. |
| P1 | Incoming JSON is not validated or safely handled. | One malformed hardware message can stop callback processing. |
| P1 | An unknown vehicle-exit plate calls `exit(1)`. | One unexpected event can terminate the backend. |
| P1 | Fast Downward and the PDDL domain path are not configured in the runtime. | The production planner cannot be started from MQTT. |
| P2 | The light sensor sends raw ADC values but the backend field is named `lux`. | The provisional dark threshold may be incorrect. |
| P2 | Exit hardware is not connected and gate-close timing is undefined. | Exit commands and demonstrations need an explicit policy. |

## 3. Backend Implementation Tasks

### 3.1 Configure deployment settings

Modify `config/settings.py`:

- Set the Windows deployment broker to `10.81.212.71`, or load it from an environment variable while retaining `localhost` for local development.
- Keep port `1883`, client IDs `backend` and `raspberrypi`, and keep-alive `60`.
- Add settings for the Fast Downward executable and PDDL domain path.
- Keep every topic exactly aligned with `hardware_setting.md`.
- Document how simulation tests override the broker address.

### 3.2 Align the MQTT wrapper with the contract

Modify `mqtt/client.py`:

- Allow `publish` to accept actuator strings and sensor dictionaries.
- Serialize Python `"on"`, `"off"`, `"open"`, and `"close"` as JSON strings on the wire.
- Keep QoS 1 and check publish/subscribe results where appropriate.
- Validate that sensor and event payloads are JSON objects.
- Catch malformed JSON and log the topic/payload instead of killing the callback thread.
- Add connection, disconnection, and error logging.
- Make `disconnect()` safe if connection setup fails.

### 3.3 Correct context updates

Modify `context/manager.py`:

- Validate integer sequence numbers and filter duplicates/older values independently per topic.
- Continue updating temperature, light, and parking occupancy from the documented fields.
- On a valid vehicle-entry event, store the plate/time and set `vehicle_waiting_to_enter = True`.
- On a valid vehicle-exit event, set `vehicle_waiting_to_leave = True` and remove the vehicle when appropriate.
- Replace `exit(1)` for an unknown plate with a warning and continued operation.
- Define when waiting flags are cleared, such as after the corresponding gate command or an explicit completion event.
- Add tests for missing fields, invalid parking positions, duplicate sequence numbers, and unknown vehicles.

### 3.4 Keep planner state synchronized

Modify `planner/`, `executor/`, and the runtime integration:

- Confirm that `planner/domain.pddl` contains the eight hardware actions and matching preconditions/effects.
- Configure `AIPlanner` with the domain path and Fast Downward executable.
- After a command is successfully published, update the matching `Context` actuator state, or add hardware acknowledgements.
- Decide and document when entrance and exit gates close.
- Ensure the planner never opens the entrance gate when all parking positions are occupied.
- Keep humidity out of planning until a humidity predicate, threshold, and tests are added.

### 3.5 Make actuator publishing explicit

Modify `mqtt/publisher.py` and `models/command.py`:

- Keep `Command.payload` as a string.
- Verify that every command publishes exactly `"on"`, `"off"`, `"open"`, or `"close"`.
- Add serialization tests for every actuator topic.
- Keep the exit topic as a reserved interface until exit hardware is connected.

### 3.6 Restore the production runtime

Modify `main.py`:

1. Create the MQTT client, event dispatcher, context manager, planner, publisher, and executor.
2. Connect to the broker and subscribe to all sensor/event topics.
3. Wait for events without busy-spinning.
4. Update the context for each event.
5. Generate a PDDL problem and run the planner.
6. Publish the resulting actuator commands.
7. Log the event, updated context, plan, and command results.
8. Shut down MQTT cleanly on `Ctrl+C`.

Keep `test_connecting()` as a separate smoke-test mode, but change its fan payload from a dictionary to the contract string `"on"`. It should not invoke the AI planner.

## 4. Raspberry Pi Hardware-Client Tasks

These changes belong in the Raspberry Pi hardware program:

- Use the Raspberry Pi 5-compatible GrovePi bus setting `RPI_1`.
- Keep the corrected `digitalRead()` implementation that returns the first I2C byte.
- Run with `~/grovepi-venv` and both GrovePi and `di_i2c` paths in `PYTHONPATH`.
- Publish temperature/light data as JSON objects with independent sequence numbers.
- Publish optional parking and vehicle events using the exact topics and field names in `hardware_setting.md`.
- Decode actuator payloads as JSON strings and optionally tolerate quoted/raw strings.
- Map fan, light, and entrance commands to D3, D8, and GPIO18 respectively.
- Force the relay and LED off during shutdown.
- Update the LCD locally; no backend LCD command is required.
- Sample sensors about every two seconds and avoid high-frequency DHT11 reads.
- Use a separate 5 V supply and common ground for a loaded servo.
- Decide whether D4 is a parking simulator button or a local manual-control button.
- Calibrate raw A0 readings before finalizing the backend dark-light threshold.

## 5. Verification Plan

### Phase 1: Contract and unit tests

- Test JSON serialization for sensor objects and actuator strings.
- Test all topic constants against `hardware_setting.md`.
- Test per-topic sequence filtering.
- Test context updates for temperature, light, parking, entry, and exit messages.
- Test malformed messages and unknown vehicles do not crash the service.
- Test planner problems for high temperature, darkness, free parking, and full parking.
- Test mapping of all eight planner actions to actuator commands.

### Phase 2: Local simulation

Use the existing broker simulator, backend simulator, actuator monitor, and sensor publisher. Verify:

```text
temperature = 35                 -> fan       -> "on"
temperature = 25                 -> fan       -> "off"
dark light                       -> light     -> "on"
bright light                     -> light     -> "off"
vehicle entry + free space      -> entrance  -> "open"
vehicle entry + full garage     -> no entrance-open command
```

### Phase 3: Raspberry Pi smoke test

- Start Mosquitto on the Raspberry Pi.
- Run the backend connection test from Windows.
- Confirm that temperature and light messages appear in the backend log.
- Confirm that the Raspberry Pi receives the actuator test string every three seconds.
- Verify relay, LED, and servo actions physically.
- Stop with `Ctrl+C` and confirm that fan and LED are left off safely.

### Phase 4: End-to-end planner test

- Run the production backend with Fast Downward enabled.
- Verify the complete temperature-to-relay and light-to-LED paths.
- Publish parking and vehicle-entry events and verify the entrance-gate decision.
- Confirm that a full garage prevents the entrance-open command.
- Confirm logs show the MQTT event, context, generated plan, and actuator payload.

## 6. Acceptance Criteria

Implementation is complete when:

- the Windows backend connects to Mosquitto at `10.81.212.71:1883`;
- all hardware-facing topics and payloads match `hardware_setting.md`;
- malformed and duplicate messages do not terminate the backend;
- each valid event produces the expected context change;
- planner actions are generated only when needed and become correct actuator strings;
- the Raspberry Pi physically responds to fan, light, and entrance-gate commands;
- a full garage never opens the entrance gate;
- shutdown leaves fan and light off;
- automated tests and live acceptance cases pass.

## 7. Implementation Decisions

1. The broker address is loaded from `.env`/environment variables, with `10.81.212.71` as the deployment default.
2. Actuator state is updated optimistically after a command is accepted for publishing because the current hardware contract has no acknowledgement topic.
3. Entrance/exit waiting flags are cleared after the matching open command. A later state-change event can then plan gate closure.
4. D4 remains available for parking-position simulation until the hardware team selects a final mode.
5. The raw-ADC dark threshold remains provisionally `100.0` until hardware calibration is completed.
6. The exit-gate MQTT interface remains implemented and tested in software, but physical verification is deferred until exit hardware is connected.

## 8. Remaining External Verification

- Run the smoke test against Mosquitto on the Raspberry Pi.
- Confirm physical D3 relay, D8 LED, and GPIO18 servo behavior.
- Calibrate the A0 light reading and update `lux_dark_threshold`.
- Confirm the selected D4 mode and entrance-gate close timing during the live demonstration.
