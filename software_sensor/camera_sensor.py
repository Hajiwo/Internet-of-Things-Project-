"""Camera-based license plate recognition sensor powered by PaddleOCR."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any, ClassVar


class CameraSensorError(RuntimeError):
    """Raised when the camera sensor cannot complete recognition."""


@dataclass(slots=True)
class CameraSensor:
    """Capture a stable license plate snapshot and recognize it with PaddleOCR."""

    camera_index: int = 0
    timeout_seconds: float = 20.0
    countdown_seconds: float = 3.0
    capture_timeout_seconds: float = 2.0
    min_plate_length: int = 4
    show_preview: bool = True
    gpu: bool = False
    confidence_threshold: float = 0.35
    allowlist: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    max_frame_width: int = 960
    preview_window_name: str = "Smart Garage Camera Sensor"
    plate_pattern: str = r"[A-Z]{1,4}[0-9]{2,5}"
    strict_plate_pattern: bool = False
    paddle_language: str = "en"
    use_angle_cls: bool = True

    # Kept for compatibility with existing tests and manual tuning.
    required_ocr_confirmations: int = 2
    required_exact_repeats: int = 2
    max_observations: int = 8

    _reader: ClassVar[Any | None] = None
    _reader_config: ClassVar[tuple[str, bool, bool] | None] = None

    def read_license_plate(self) -> str:
        """Open the camera, capture one stable frame, and return the plate text."""

        cv2 = self._load_cv2()
        reader = self._load_reader()
        camera = cv2.VideoCapture(self.camera_index)
        if not camera.isOpened():
            raise CameraSensorError(f"Cannot open camera index {self.camera_index}")

        self._configure_camera(cv2, camera)

        try:
            frame = self._capture_frame_after_countdown(cv2, camera)
            plate = self.read_license_plate_from_frame(frame, cv2, reader)
            if plate:
                return plate
        finally:
            camera.release()
            if self.show_preview:
                self._close_preview(cv2)

        raise CameraSensorError("No license plate recognized from captured image")

    def read_license_plate_from_frame(
        self,
        frame: Any,
        cv2_module: Any | None = None,
        reader: Any | None = None,
    ) -> str:
        """Recognize a license plate from one captured image."""

        cv2 = cv2_module or self._load_cv2()
        reader = reader or self._load_reader()
        candidates = self._read_license_plate_candidates_from_frame(frame, cv2, reader)
        return self._best_observed_plate(candidates)

    def _capture_frame_after_countdown(self, cv2: Any, camera: Any) -> Any:
        """Show a countdown, then capture a clean frame for OCR."""

        last_frame = self._run_countdown(cv2, camera)
        captured_frame = self._capture_next_available_frame(cv2, camera)
        return captured_frame if captured_frame is not None else last_frame

    def _run_countdown(self, cv2: Any, camera: Any) -> Any:
        deadline = time.monotonic() + max(0.0, self.countdown_seconds)
        last_frame = None

        while time.monotonic() < deadline:
            success, frame = camera.read()
            if success:
                last_frame = frame
                if self.show_preview:
                    remaining = max(0.0, deadline - time.monotonic())
                    self._show_countdown_preview(cv2, frame, remaining)
                    self._raise_if_cancelled(cv2)
            else:
                time.sleep(0.02)

            if not self.show_preview:
                time.sleep(0.03)

        if last_frame is None:
            raise CameraSensorError("Cannot capture image from camera")
        return last_frame

    def _capture_next_available_frame(self, cv2: Any, camera: Any) -> Any | None:
        deadline = time.monotonic() + max(0.5, self.capture_timeout_seconds)

        while time.monotonic() < deadline:
            success, frame = camera.read()
            if success:
                if self.show_preview:
                    self._show_capture_preview(cv2, frame)
                    self._raise_if_cancelled(cv2)
                return frame
            time.sleep(0.02)

        return None

    def _read_license_plate_candidates_from_frame(
        self,
        frame: Any,
        cv2: Any,
        reader: Any,
    ) -> list[tuple[str, float]]:
        """Run PaddleOCR over several still-image variants."""

        results: list[Any] = []
        for image in self._preprocess_frames(frame, cv2):
            results.extend(self._run_ocr(reader, image))
        return self._license_plate_candidates(results)

    def _preprocess_frames(self, frame: Any, cv2: Any) -> list[Any]:
        """Return image variants that help PaddleOCR read printed plates."""

        resized = self._resize_frame(frame, cv2)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        equalized = cv2.equalizeHist(gray)
        filtered = cv2.bilateralFilter(gray, 11, 17, 17)
        _, threshold = cv2.threshold(
            filtered,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )
        adaptive = cv2.adaptiveThreshold(
            equalized,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            5,
        )
        inverted = cv2.bitwise_not(threshold)
        return [
            self._ensure_color_frame(image, cv2)
            for image in [resized, gray, equalized, threshold, adaptive, inverted]
        ]

    def _resize_frame(self, frame: Any, cv2: Any) -> Any:
        height, width = frame.shape[:2]
        if width <= self.max_frame_width:
            return frame

        scale = self.max_frame_width / width
        new_size = (self.max_frame_width, int(height * scale))
        return cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA)

    def _ensure_color_frame(self, frame: Any, cv2: Any) -> Any:
        shape = getattr(frame, "shape", ())
        if len(shape) == 2:
            gray_to_bgr = getattr(cv2, "COLOR_GRAY2BGR", None)
            if gray_to_bgr is not None:
                return cv2.cvtColor(frame, gray_to_bgr)
        return frame

    def _license_plate_candidates(self, results: list[Any]) -> list[tuple[str, float]]:
        candidates: list[tuple[str, float]] = []
        for text, confidence in self._extract_ocr_pairs(results):
            plate = self._normalize_license_plate(text)
            if plate and confidence >= self.confidence_threshold:
                candidates.append((plate, confidence))
        return candidates

    def _normalize_license_plate(self, raw_text: str) -> str:
        plate = re.sub(r"[^A-Za-z0-9]", "", raw_text).upper()
        if len(plate) < self.min_plate_length:
            return ""
        if self.strict_plate_pattern and not self._matches_plate_pattern(plate):
            return ""
        return plate

    def _best_license_plate_candidate(self, results: list[Any]) -> str:
        return self._best_observed_plate(self._license_plate_candidates(results))

    def _best_observed_plate(self, observations: list[tuple[str, float]]) -> str:
        if not observations:
            return ""

        scores = self._aggregate_observations(observations)
        return max(scores.items(), key=lambda item: item[1])[0]

    def _aggregate_observations(
        self,
        observations: list[tuple[str, float]],
    ) -> dict[str, float]:
        scores: dict[str, float] = {}
        counts: dict[str, int] = {}

        for plate, confidence in observations:
            counts[plate] = counts.get(plate, 0) + 1
            scores[plate] = scores.get(plate, 0.0) + self._plate_candidate_score(
                plate,
                confidence,
            )

        for plate, count in counts.items():
            scores[plate] += count * 2.0

        return scores

    def _plate_candidate_score(self, plate: str, confidence: float) -> float:
        return confidence * len(plate) + self._plate_shape_score(plate)

    def _plate_shape_score(self, plate: str) -> float:
        score = 0.0
        if self._matches_plate_pattern(plate):
            score += 3.0
        if re.search(r"[A-Z]", plate) and re.search(r"[0-9]", plate):
            score += 1.0
        if 5 <= len(plate) <= 8:
            score += 1.0
        return score

    def _confirmed_license_plate(self, observations: list[tuple[str, float]]) -> str:
        """Merge repeated observations while rejecting unstable OCR noise."""

        observations = self._recent_observations(observations)
        if self.required_ocr_confirmations <= 1:
            return self._best_observed_plate(observations)

        best_cluster: list[tuple[str, float]] = []
        for plate, _confidence in observations:
            cluster = [
                (other_plate, other_confidence)
                for other_plate, other_confidence in observations
                if self._plates_compatible(plate, other_plate)
            ]
            if len(cluster) > len(best_cluster):
                best_cluster = cluster
            elif len(cluster) == len(best_cluster) and self._cluster_score(
                cluster
            ) > self._cluster_score(best_cluster):
                best_cluster = cluster

        if len(best_cluster) < self.required_ocr_confirmations:
            return ""

        merged_plate = self._merge_plate_cluster(best_cluster)
        exact_repeats = self._exact_plate_count(merged_plate, best_cluster)
        if exact_repeats < self.required_exact_repeats:
            return ""

        return merged_plate

    def _recent_observations(
        self,
        observations: list[tuple[str, float]],
    ) -> list[tuple[str, float]]:
        if self.max_observations < 1:
            return observations
        return observations[-self.max_observations :]

    def _plates_compatible(self, first: str, second: str) -> bool:
        if len(first) != len(second):
            return False
        differences = sum(1 for left, right in zip(first, second) if left != right)
        return differences <= 1

    def _cluster_score(self, cluster: list[tuple[str, float]]) -> float:
        return sum(confidence for _plate, confidence in cluster)

    def _merge_plate_cluster(self, cluster: list[tuple[str, float]]) -> str:
        plate_length = len(cluster[0][0])
        merged = []

        for index in range(plate_length):
            votes: dict[str, tuple[int, float]] = {}
            for plate, confidence in cluster:
                char = plate[index]
                count, total_confidence = votes.get(char, (0, 0.0))
                votes[char] = (count + 1, total_confidence + confidence)
            merged.append(max(votes.items(), key=lambda item: item[1])[0])

        return "".join(merged)

    def _exact_plate_count(
        self,
        target_plate: str,
        observations: list[tuple[str, float]],
    ) -> int:
        return sum(1 for plate, _confidence in observations if plate == target_plate)

    def _extract_ocr_pairs(self, result: Any) -> list[tuple[str, float]]:
        pairs: list[tuple[str, float]] = []
        text, confidence = self._parse_easyocr_result(result)
        if text:
            return [(text, confidence)]

        if isinstance(result, dict):
            texts = result.get("rec_texts") or result.get("texts") or []
            scores = result.get("rec_scores") or result.get("scores") or []
            for index, text_item in enumerate(texts):
                score = scores[index] if index < len(scores) else 1.0
                try:
                    pairs.append((str(text_item), float(score)))
                except (TypeError, ValueError):
                    pairs.append((str(text_item), 1.0))
            return pairs

        if isinstance(result, (list, tuple)):
            for item in result:
                pairs.extend(self._extract_ocr_pairs(item))
        return pairs

    def _parse_easyocr_result(self, result: Any) -> tuple[str, float]:
        """Parse OCR output from either legacy EasyOCR-style or PaddleOCR-style data."""

        if isinstance(result, str):
            return result, 1.0
        if isinstance(result, dict):
            text = result.get("text")
            score = result.get("score", result.get("confidence", 1.0))
            if text is not None:
                try:
                    return str(text), float(score)
                except (TypeError, ValueError):
                    return str(text), 1.0
        if (
            isinstance(result, (list, tuple))
            and len(result) >= 3
            and isinstance(result[1], str)
        ):
            return str(result[1]), float(result[2])
        if (
            isinstance(result, (list, tuple))
            and len(result) >= 2
            and isinstance(result[1], (list, tuple))
            and len(result[1]) >= 2
            and isinstance(result[1][0], str)
        ):
            text = result[1][0]
            confidence = result[1][1]
            try:
                return str(text), float(confidence)
            except (TypeError, ValueError):
                return str(text), 1.0
        if isinstance(result, (list, tuple)) and len(result) == 2:
            text, confidence = result
            if isinstance(confidence, (int, float)):
                return str(text), float(confidence)
        if (
            isinstance(result, (list, tuple))
            and len(result) >= 1
            and isinstance(result[0], str)
        ):
            return str(result[0]), 1.0
        return "", 0.0

    def _run_ocr(self, reader: Any, image: Any) -> list[Any]:
        ocr_method = getattr(reader, "ocr", None)
        if callable(ocr_method):
            try:
                result = ocr_method(image)
            except TypeError:
                result = ocr_method(image, cls=self.use_angle_cls)
            return [] if result is None else [result]

        predict_method = getattr(reader, "predict", None)
        if callable(predict_method):
            result = predict_method(image)
            return [] if result is None else [result]

        legacy_method = getattr(reader, "readtext", None)
        if callable(legacy_method):
            result = legacy_method(
                image,
                detail=1,
                allowlist=self.allowlist,
                paragraph=False,
            )
            return [] if result is None else list(result)

        raise CameraSensorError(
            "PaddleOCR engine does not expose an OCR inference method"
        )

    def _matches_plate_pattern(self, plate: str) -> bool:
        try:
            return re.fullmatch(self.plate_pattern, plate) is not None
        except re.error as error:
            raise CameraSensorError(
                f"Invalid license plate regex pattern: {self.plate_pattern}"
            ) from error

    def _configure_camera(self, cv2: Any, camera: Any) -> None:
        buffer_size_property = getattr(cv2, "CAP_PROP_BUFFERSIZE", None)
        if buffer_size_property is not None:
            camera.set(buffer_size_property, 1)

    def _raise_if_cancelled(self, cv2: Any) -> None:
        if cv2.waitKey(1) & 0xFF == ord("q"):
            raise CameraSensorError("Camera recognition cancelled by user")
        if self._preview_window_closed(cv2):
            raise CameraSensorError("Camera recognition cancelled by user")

    def _preview_window_closed(self, cv2: Any) -> bool:
        get_window_property = getattr(cv2, "getWindowProperty", None)
        visible_property = getattr(cv2, "WND_PROP_VISIBLE", None)
        if get_window_property is None or visible_property is None:
            return False

        try:
            return get_window_property(self.preview_window_name, visible_property) < 1
        except Exception:
            return False

    def _close_preview(self, cv2: Any) -> None:
        destroy_window = getattr(cv2, "destroyWindow", None)
        try:
            if destroy_window is not None:
                destroy_window(self.preview_window_name)
            else:
                cv2.destroyAllWindows()
        finally:
            cv2.destroyAllWindows()
            for _ in range(5):
                cv2.waitKey(1)

    def _show_countdown_preview(self, cv2: Any, frame: Any, remaining: float) -> None:
        seconds = max(1, int(remaining) + 1)
        self._draw_preview_text(
            cv2,
            self._copy_frame(frame),
            f"Hold license plate steady. Capturing in {seconds}",
        )

    def _show_capture_preview(self, cv2: Any, frame: Any) -> None:
        self._draw_preview_text(
            cv2,
            self._copy_frame(frame),
            "Captured. Reading license plate...",
        )

    def _show_preview(self, cv2: Any, frame: Any, last_candidate: str) -> None:
        label = "Hold license plate steady. Press q to cancel."
        if last_candidate:
            label = f"Last OCR candidate: {last_candidate}"
        self._draw_preview_text(cv2, self._copy_frame(frame), label)

    def _copy_frame(self, frame: Any) -> Any:
        copy = getattr(frame, "copy", None)
        if copy is None:
            return frame
        return copy()

    def _draw_preview_text(self, cv2: Any, frame: Any, label: str) -> None:
        cv2.putText(
            frame,
            label,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )
        cv2.imshow(self.preview_window_name, frame)

    def _load_cv2(self) -> Any:
        try:
            import cv2
        except ImportError as error:
            raise CameraSensorError(
                "OpenCV is not installed. Run: python3 -m pip install opencv-python"
            ) from error
        return cv2

    def _load_reader(self) -> Any:
        reader_config = (self.paddle_language, self.use_angle_cls, self.gpu)
        if (
            self.__class__._reader is not None
            and self.__class__._reader_config == reader_config
        ):
            return self.__class__._reader

        try:
            from paddleocr import PaddleOCR
        except ImportError as error:
            raise CameraSensorError(
                "PaddleOCR is not installed. Run: python3 -m pip install paddleocr paddlepaddle"
            ) from error

        init_attempts = [
            {
                "lang": self.paddle_language,
                "use_doc_orientation_classify": False,
                "use_doc_unwarping": False,
                "use_textline_orientation": self.use_angle_cls,
                "device": "gpu" if self.gpu else "cpu",
            },
            {
                "lang": self.paddle_language,
                "use_angle_cls": self.use_angle_cls,
                "use_gpu": self.gpu,
                "show_log": False,
            },
            {
                "lang": self.paddle_language,
                "use_angle_cls": self.use_angle_cls,
                "device": "gpu" if self.gpu else "cpu",
                "show_log": False,
            },
            {
                "lang": self.paddle_language,
                "use_textline_orientation": self.use_angle_cls,
                "device": "gpu" if self.gpu else "cpu",
            },
            {
                "lang": self.paddle_language,
                "show_log": False,
            },
        ]

        last_error: Exception | None = None
        for kwargs in init_attempts:
            try:
                self.__class__._reader = PaddleOCR(**kwargs)
                self.__class__._reader_config = reader_config
                return self.__class__._reader
            except (TypeError, ValueError) as error:
                last_error = error

        if last_error is not None:
            raise CameraSensorError(
                "Failed to initialize PaddleOCR with the available constructor options"
            ) from last_error

        return self.__class__._reader
