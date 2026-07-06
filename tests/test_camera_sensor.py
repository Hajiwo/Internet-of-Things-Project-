from software_sensor.camera_sensor import CameraSensor


class FakeCV2:
    COLOR_BGR2GRAY = 1
    THRESH_BINARY = 2
    THRESH_OTSU = 4
    INTER_AREA = 8
    WND_PROP_VISIBLE = 16
    ADAPTIVE_THRESH_GAUSSIAN_C = 32

    def __init__(self):
        self.destroyed_windows = []
        self.destroy_all_calls = 0
        self.wait_key_calls = 0
        self.visible = 1.0

    def cvtColor(self, frame, _code):
        return frame

    def bilateralFilter(self, frame, _diameter, _sigma_color, _sigma_space):
        return frame

    def equalizeHist(self, frame):
        return frame

    def threshold(self, frame, _threshold, _max_value, _method):
        return None, frame

    def adaptiveThreshold(
        self,
        frame,
        _max_value,
        _adaptive_method,
        _threshold_type,
        _block_size,
        _constant,
    ):
        return frame

    def bitwise_not(self, frame):
        return frame

    def resize(self, frame, _size, interpolation=None):
        return frame

    def destroyWindow(self, name):
        self.destroyed_windows.append(name)

    def destroyAllWindows(self):
        self.destroy_all_calls += 1

    def waitKey(self, _delay):
        self.wait_key_calls += 1
        return -1

    def getWindowProperty(self, _name, _property):
        return self.visible


class FakeFrame:
    shape = (480, 640, 3)


class FakeReader:
    def __init__(self):
        self.calls = 0

    def readtext(self, _frame, **_kwargs):
        self.calls += 1
        if self.calls == 1:
            return [("NOISE", 0.99)]
        if self.calls == 2:
            return [("BN9123", 0.91)]
        return []


def test_normalize_license_plate_keeps_only_letters_and_numbers() -> None:
    cam = CameraSensor(show_preview=False)

    assert cam._normalize_license_plate(" BN-9123\n") == "BN9123"


def test_best_license_plate_candidate_uses_confidence_and_length() -> None:
    cam = CameraSensor(show_preview=False, confidence_threshold=0.5)
    results = [
        ([[0, 0], [1, 0], [1, 1], [0, 1]], "B", 0.99),
        ([[0, 0], [1, 0], [1, 1], [0, 1]], "BN9123", 0.92),
        ([[0, 0], [1, 0], [1, 1], [0, 1]], "LOW123", 0.2),
    ]

    assert cam._best_license_plate_candidate(results) == "BN9123"


def test_best_license_plate_candidate_ignores_low_confidence_text() -> None:
    cam = CameraSensor(show_preview=False, confidence_threshold=0.8)

    assert cam._best_license_plate_candidate([("box", "BN9123", 0.4)]) == ""


def test_parse_easyocr_detail_zero_with_confidence() -> None:
    cam = CameraSensor(show_preview=False)

    assert cam._parse_easyocr_result(("BN9123", 0.91)) == ("BN9123", 0.91)


def test_frame_recognition_uses_multiple_preprocessed_frames() -> None:
    cam = CameraSensor(show_preview=False)
    reader = FakeReader()

    plate = cam.read_license_plate_from_frame(FakeFrame(), FakeCV2(), reader)

    assert plate == "BN9123"
    assert reader.calls == 6


def test_confirmed_license_plate_merges_one_character_ocr_noise() -> None:
    cam = CameraSensor(show_preview=False, required_ocr_confirmations=2)
    observations = [
        ("BN9123", 0.62),
        ("BN9123", 0.58),
        ("BN1123", 0.91),
        ("BN7123", 0.88),
    ]

    assert cam._confirmed_license_plate(observations) == "BN9123"


def test_confirmed_license_plate_waits_for_repeated_observation() -> None:
    cam = CameraSensor(show_preview=False, required_ocr_confirmations=2)

    assert cam._confirmed_license_plate([("BN1123", 0.91)]) == ""


def test_confirmed_license_plate_rejects_unstable_confused_digits() -> None:
    cam = CameraSensor(show_preview=False, required_ocr_confirmations=2)
    observations = [
        ("BN1123", 0.91),
        ("BN7123", 0.88),
    ]

    assert cam._confirmed_license_plate(observations) == ""


def test_close_preview_flushes_opencv_window_events() -> None:
    cam = CameraSensor(show_preview=True)
    cv2 = FakeCV2()

    cam._close_preview(cv2)

    assert cv2.destroyed_windows == [cam.preview_window_name]
    assert cv2.destroy_all_calls == 1
    assert cv2.wait_key_calls == 5


def test_preview_window_closed_detects_user_closed_window() -> None:
    cam = CameraSensor(show_preview=True)
    cv2 = FakeCV2()
    cv2.visible = 0.0

    assert cam._preview_window_closed(cv2) is True
