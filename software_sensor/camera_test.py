"""Simple runner for testing the camera license plate sensor."""

from __future__ import annotations

import argparse
import sys

try:
    from .camera_sensor import CameraSensor, CameraSensorError
except ImportError:
    from camera_sensor import CameraSensor, CameraSensorError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test the camera sensor once.")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--countdown", type=float, default=3.0)
    parser.add_argument("--capture-timeout", type=float, default=2.0)
    parser.add_argument("--confidence-threshold", type=float, default=0.35)
    parser.add_argument("--plate-pattern", default=r"[A-Z]{1,4}[0-9]{2,5}")
    parser.add_argument("--paddle-language", default="en")
    parser.add_argument("--gpu", action="store_true")
    parser.add_argument("--strict-plate-pattern", action="store_true")
    parser.add_argument("--no-preview", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sensor = CameraSensor(
        camera_index=args.camera_index,
        countdown_seconds=args.countdown,
        capture_timeout_seconds=args.capture_timeout,
        confidence_threshold=args.confidence_threshold,
        plate_pattern=args.plate_pattern,
        paddle_language=args.paddle_language,
        gpu=args.gpu,
        strict_plate_pattern=args.strict_plate_pattern,
        show_preview=not args.no_preview,
    )

    print("Smart Garage camera sensor test")
    print(f"Python executable: {sys.executable}")

    try:
        license_plate = sensor.read_license_plate()
    except CameraSensorError as error:
        print(f"Camera sensor failed: {error}")
        raise SystemExit(1)

    print(f"License plate: {license_plate}")


if __name__ == "__main__":
    main()
