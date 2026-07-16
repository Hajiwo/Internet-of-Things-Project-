from software_sensor.camera_sensor import CameraSensor


class BrokenPreview:
    def destroyWindow(self, name: str) -> None:
        raise RuntimeError("window unavailable")

    def destroyAllWindows(self) -> None:
        raise RuntimeError("window unavailable")

    def waitKey(self, delay: int) -> int:
        raise RuntimeError("window unavailable")


def test_preview_cleanup_never_masks_camera_error() -> None:
    CameraSensor()._close_preview(BrokenPreview())
