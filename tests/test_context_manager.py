from context.manager import ContextManager


def test_vehicle_entry_accepts_license_alias() -> None:
    manager = ContextManager()

    manager.update_vehicle_entry({"license": "BN9123", "enter_time": "2026-07-02T15:30:20"})

    assert manager.context.current_vehicles["BN9123"] == "2026-07-02T15:30:20"


def test_vehicle_leave_accepts_license_alias() -> None:
    manager = ContextManager()
    manager.context.current_vehicles["BN9123"] = "2026-07-02T15:30:20"

    manager.update_vehicle_leave({"license": "BN9123"})

    assert "BN9123" not in manager.context.current_vehicles
