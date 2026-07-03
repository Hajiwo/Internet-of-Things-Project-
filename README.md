# Smart Garage

Smart Garage is a Python project scaffold for MQTT-driven garage automation, planning, and execution.

## The format of MQTT messages

From sensors:
1. Temperature:
```json 
{
    sequence: ,
    temperature: "38"
}
```

2. Light: 
```json
{
    sequence: ,
    lux: "300"
}
```

3. Parking: 
```json
{
    license: "BN9123"
    position: 0
    enter_time: TIME
}

{
    position: 0
}
```

## Design of the context:

```json
//context:

//temperature part:
temperature: int
fan: bool (on/off)

//lightening part:
lux: int
light: bool (on/off)

//parking part:
Position: list: class parkingVehicle (size = 4, index is the position number)

class paringVehicle{
    license: str, size = 7 for example
    enter_time: TIME
}

```



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
