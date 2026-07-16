from pathlib import Path

import cv2
import numpy as np


VIDEO_PATH = Path("data/input.mp4")
DETECTOR_PATH = Path("models/face_detection_yunet_2023mar.onnx")
RECOGNIZER_PATH = Path("models/face_recognition_sface_2021dec.onnx")
OUTPUT_DIR = Path("known_faces")

MAX_DISPLAY_WIDTH = 900
MAX_DISPLAY_HEIGHT = 700


name = input("请输入要录入的人名：").strip()

if not name:
    raise ValueError("人名不能为空")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

video = cv2.VideoCapture(str(VIDEO_PATH))

if not video.isOpened():
    raise RuntimeError(f"无法打开视频：{VIDEO_PATH}")

detector = cv2.FaceDetectorYN.create(
    model=str(DETECTOR_PATH),
    config="",
    input_size=(320, 320),
    score_threshold=0.8,
    nms_threshold=0.3,
    top_k=5000,
)

recognizer = cv2.FaceRecognizerSF.create(
    str(RECOGNIZER_PATH),
    "",
)

fps = video.get(cv2.CAP_PROP_FPS)
frame_delay = max(1, round(1000 / fps)) if fps > 0 else 33

window_name = "Enroll Face"
cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

print("选择清晰正脸画面，按 S 保存；按 Q 或 Esc 退出")
paused = False
frame = None
selected_face = None
display_frame = None
while True:
    if not paused:
        ok, frame = video.read()

        if not ok:
            video.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        height, width = frame.shape[:2]
        detector.setInputSize((width, height))

        _, faces = detector.detect(frame)

        selected_face = None

        if faces is not None and len(faces) > 0:
            selected_face = max(
                faces,
                key=lambda face: float(face[2] * face[3]),
            )

            x, y, w, h = selected_face[:4].astype(int)

            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                3,
            )

            cv2.putText(
                frame,
                f"Selected: {name}",
                (x, max(30, y - 12)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
            )

        cv2.putText(
            frame,
            "SPACE: Pause   S: Save   Q/ESC: Exit",
            (25, 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (0, 255, 255),
            2,
        )

        scale = min(
            MAX_DISPLAY_WIDTH / width,
            MAX_DISPLAY_HEIGHT / height,
            1.0,
        )

        display_frame = cv2.resize(
            frame,
            (
                int(width * scale),
                int(height * scale),
            ),
        )

        cv2.imshow(window_name, display_frame)

    key = cv2.waitKeyEx(30 if paused else frame_delay)

    if key == 32:
        paused = not paused

        if paused and display_frame is not None:
            paused_frame = display_frame.copy()

            cv2.putText(
                paused_frame,
                "PAUSED",
                (25, paused_frame.shape[0] - 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2,
            )

            cv2.imshow(window_name, paused_frame)

        print("已暂停" if paused else "继续播放")
        continue

    if key in (ord("q"), ord("Q"), 27):
        break

    if key in (ord("s"), ord("S")):
        if frame is None or selected_face is None:
            print("当前帧没有检测到人脸，未保存")
            continue

        aligned_face = recognizer.alignCrop(frame, selected_face)
        feature = recognizer.feature(aligned_face).copy()

        image_path = OUTPUT_DIR / f"{name}.jpg"
        feature_path = OUTPUT_DIR / f"{name}.npy"

        cv2.imwrite(str(image_path), aligned_face)
        np.save(feature_path, feature)

        print(f"录入成功：{name}")
        print(f"人脸图片：{image_path}")
        print(f"特征文件：{feature_path}")
        break
video.release()
cv2.destroyAllWindows()