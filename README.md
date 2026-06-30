# Smart Garage

Smart Garage is a Python project scaffold for MQTT-driven garage automation, planning, and execution.

## Structure

- `main.py`: application entry point
- `config/`: runtime settings
- `mqtt/`: MQTT client, topics, publisher, and subscriber helpers
- `context/`: garage context state and update manager
- `planner/`: planning inputs, parser, and Fast Downward integration
- `executor/`: plan execution layer
- `models/`: shared data models
- `utils/`: logging and helper utilities
- `tests/`: automated tests
- `examples/`: sample publishers and simulation scripts

## Next steps

1. Add environment values to `.env`.
2. Install dependencies from `requirements.txt`.
3. Implement the MQTT and planning integrations.
