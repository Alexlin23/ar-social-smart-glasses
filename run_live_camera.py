"""Run the existing AR face-recognition demo with a live camera.

This is an additive entry point: it reuses the project's existing pipeline,
registration flow, HUD, and window helpers without changing those files.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2


PROJECT_DIR = Path(__file__).resolve().parent
WINDOW_NAME = "AR Social Smart Glasses - Live Camera"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the AR social smart-glasses prototype from a camera."
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Camera device index (default: 0).",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1280,
        help="Requested capture width (default: 1280).",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=720,
        help="Requested capture height (default: 720).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.45,
        help="SFace cosine-match threshold (default: 0.45).",
    )
    parser.add_argument(
        "--detector",
        type=Path,
        default=Path("models/face_detection_yunet_2023mar.onnx"),
        help="Path to the YuNet ONNX model, relative to the project directory.",
    )
    parser.add_argument(
        "--recognizer",
        type=Path,
        default=Path("models/face_recognition_sface_2021dec.onnx"),
        help="Path to the SFace ONNX model, relative to the project directory.",
    )
    return parser.parse_args()


def project_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_DIR / path


def open_camera(index: int, width: int, height: int) -> cv2.VideoCapture:
    if index < 0:
        raise ValueError("camera index must be zero or greater")
    if width <= 0 or height <= 0:
        raise ValueError("capture width and height must be greater than zero")

    backends = [cv2.CAP_DSHOW, cv2.CAP_ANY] if sys.platform == "win32" else [cv2.CAP_ANY]
    for backend in backends:
        capture = cv2.VideoCapture(index, backend)
        if capture.isOpened():
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            return capture
        capture.release()

    raise RuntimeError(
        f"Cannot open camera {index}. Close other camera apps or try --camera 1."
    )


def main() -> int:
    args = parse_args()

    # Resolve imports and runtime data from the project directory, regardless of
    # the shell's current working directory.
    sys.path.insert(0, str(PROJECT_DIR))
    from face_pipeline import FaceRecognitionPipeline
    from person_registration_service import PersonRegistrationService
    from recognize_face import (
        build_card_data,
        choose_unknown_person,
        register_unknown_person,
    )
    from person_card_ui import draw_person_overlay
    from window_ui import (
        create_adaptive_window,
        get_window_size,
        is_window_closed,
        resize_with_letterbox,
    )

    detector_path = project_path(args.detector)
    recognizer_path = project_path(args.recognizer)
    people_dir = PROJECT_DIR / "people"
    known_faces_dir = PROJECT_DIR / "known_faces"

    pipeline = FaceRecognitionPipeline(
        detector_path=detector_path,
        recognizer_path=recognizer_path,
        known_faces_dir=known_faces_dir,
        people_dir=people_dir,
        cosine_threshold=args.threshold,
    )
    registration_service = PersonRegistrationService(
        people_dir=people_dir,
        known_faces_dir=known_faces_dir,
    )
    camera = open_camera(args.camera, args.width, args.height)

    actual_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH)) or args.width
    actual_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT)) or args.height
    create_adaptive_window(WINDOW_NAME, actual_width, actual_height)

    paused = False
    render_frame = None
    visible_people = []
    previous_time = time.perf_counter()
    smoothed_fps = 0.0

    print("Live camera started: SPACE pause/resume, R register, Q/ESC exit")

    try:
        while True:
            if not paused:
                ok, frame = camera.read()
                if not ok:
                    print("Camera frame read failed; exiting.")
                    return 2

                visible_people = pipeline.process_frame(frame)
                for person in visible_people:
                    draw_person_overlay(frame, person.bbox, build_card_data(person))

                now = time.perf_counter()
                instant_fps = 1.0 / max(now - previous_time, 1e-6)
                previous_time = now
                smoothed_fps = (
                    instant_fps if smoothed_fps == 0.0 else 0.9 * smoothed_fps + 0.1 * instant_fps
                )
                cv2.putText(
                    frame,
                    f"FPS: {smoothed_fps:.1f}   SPACE: Pause   R: Register   Q/ESC: Exit",
                    (25, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 255, 255),
                    2,
                    cv2.LINE_AA,
                )
                render_frame = frame.copy()

            if render_frame is not None:
                window_width, window_height = get_window_size(
                    WINDOW_NAME, actual_width, actual_height
                )
                display_frame = resize_with_letterbox(
                    render_frame, window_width, window_height
                )
                if paused:
                    cv2.putText(
                        display_frame,
                        "PAUSED",
                        (25, display_frame.shape[0] - 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.0,
                        (0, 0, 255),
                        2,
                        cv2.LINE_AA,
                    )
                cv2.imshow(WINDOW_NAME, display_frame)

            key = cv2.waitKeyEx(30)
            if key == 32:
                paused = not paused
                continue
            if key in (ord("r"), ord("R")):
                paused = True
                selected = choose_unknown_person(visible_people)
                if selected is None:
                    print("No unknown person is available for registration.")
                    continue
                try:
                    register_unknown_person(selected, registration_service, pipeline)
                except Exception as error:
                    print(f"Registration failed: {error}")
                continue
            if key in (ord("q"), ord("Q"), 27) or is_window_closed(WINDOW_NAME):
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
