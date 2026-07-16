import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from dashboard.server import DashboardServer
from services.camera_service import CameraRequestError


def test_dashboard_serves_page_state_and_camera_api() -> None:
    camera_calls: list[str] = []
    state = {
        "broker": {"connected": True, "address": "localhost", "port": 1883},
        "context": {},
        "parking": {"occupied": 0, "available": 3, "full": False},
        "events": [],
        "commands": [],
        "last_event": None,
        "last_command": None,
        "last_error": None,
    }

    def camera_handler(direction: str) -> dict[str, str]:
        camera_calls.append(direction)
        return {"license_plate": "BN9123"}

    server = DashboardServer(lambda: state, camera_handler, host="127.0.0.1", port=0)
    server.start()
    try:
        base_url = f"http://127.0.0.1:{server.address[1]}"
        with urlopen(base_url + "/", timeout=2) as response:
            assert b"Smart Garage" in response.read()
        with urlopen(base_url + "/api/state", timeout=2) as response:
            assert json.load(response)["parking"]["available"] == 3
        request = Request(base_url + "/api/camera/enter", method="POST")
        with urlopen(request, timeout=2) as response:
            assert json.load(response)["result"]["license_plate"] == "BN9123"
        assert camera_calls == ["enter"]
    finally:
        server.stop()


def test_dashboard_returns_camera_error_status() -> None:
    def reject(direction: str) -> dict[str, str]:
        raise CameraRequestError("Garage full", 409)

    server = DashboardServer(lambda: {}, reject, host="127.0.0.1", port=0)
    server.start()
    try:
        request = Request(
            f"http://127.0.0.1:{server.address[1]}/api/camera/enter",
            method="POST",
        )
        try:
            urlopen(request, timeout=2)
        except HTTPError as error:
            assert error.code == 409
            assert json.load(error)["error"] == "Garage full"
        else:
            raise AssertionError("Expected the camera API to return HTTP 409")
    finally:
        server.stop()
