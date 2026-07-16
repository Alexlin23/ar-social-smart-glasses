from pathlib import Path

import cv2

VIDEO_PATH = Path("data/input3.mp4")
MODEL_PATH = Path("models/face_detection_yunet_2023mar.onnx")


if not VIDEO_PATH.exists():
    raise FileNotFoundError(f"视频不存在：{VIDEO_PATH}")

if not MODEL_PATH.exists():
    raise FileNotFoundError(f"模型不存在：{MODEL_PATH}")


video = cv2.VideoCapture(str(VIDEO_PATH))

if not video.isOpened():
    raise RuntimeError(f"无法打开视频：{VIDEO_PATH}")


fps = video.get(cv2.CAP_PROP_FPS)
frame_delay = max(1, round(1000 / fps)) if fps > 0 else 33

detector = cv2.FaceDetectorYN.create(
    model=str(MODEL_PATH),
    config="",
    input_size=(320, 320),
    score_threshold=0.8,
    nms_threshold=0.3,
    top_k=5000,
)

print("YuNet 人脸检测已启动，点击视频窗口后按 Q 或 Esc 退出")

cv2.namedWindow("AR Face Detection Demo", cv2.WINDOW_AUTOSIZE)

MAX_DISPLAY_WIDTH = 900
MAX_DISPLAY_HEIGHT = 700
paused = False
resized_frame = None
while True:
    if not paused:
        ok, frame = video.read()

        if not ok:
            video.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        height, width = frame.shape[:2]
        detector.setInputSize((width, height))

        _, faces = detector.detect(frame)

        face_count = 0 if faces is None else len(faces)

        if faces is not None:
            for face in faces:
                x, y, w, h = face[:4].astype(int)
                confidence = float(face[-1])

                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),
                    2,
                )

                cv2.putText(
                    frame,
                    f"Face {confidence:.2f}",
                    (x, max(25, y - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                )

        cv2.putText(
            frame,
            f"Faces: {face_count}",
            (25, 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2,
        )

        scale = min(
            MAX_DISPLAY_WIDTH / width,
            MAX_DISPLAY_HEIGHT / height,
            1.0,
        )

        resized_frame = cv2.resize(
            frame,
            (
                int(width * scale),
                int(height * scale),
            ),
        )

        cv2.imshow("AR Face Detection Demo", resized_frame)

    key = cv2.waitKeyEx(30 if paused else frame_delay)

    if key == 32:  # 空格键
        paused = not paused

        if paused and resized_frame is not None:
            paused_frame = resized_frame.copy()

            cv2.putText(
                paused_frame,
                "PAUSED",
                (25, paused_frame.shape[0] - 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2,
            )

            cv2.imshow("AR Face Detection Demo", paused_frame)

        print("已暂停" if paused else "继续播放")

    if key in (ord("q"), ord("Q"), 27):
        break

video.release()
cv2.destroyAllWindows()