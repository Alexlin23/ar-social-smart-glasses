from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from face_pipeline import FaceRecognitionPipeline, RecognizedPerson
from person_card_ui import PersonCardData, draw_person_overlay
from person_registration_service import PersonRegistrationService
from window_ui import (
    create_adaptive_window,
    get_window_size,
    is_window_closed,
    resize_with_letterbox,
)


VIDEO_PATH = Path("data/input3.mp4")
DETECTOR_PATH = Path("models/face_detection_yunet_2023mar.onnx")
RECOGNIZER_PATH = Path("models/face_recognition_sface_2021dec.onnx")
KNOWN_FACES_DIR = Path("known_faces")
PEOPLE_DIR = Path("people")
COSINE_THRESHOLD = 0.45
WINDOW_NAME = "AR Face Recognition Demo"


def section_to_inline(profile, section_name: str, default: str = "-") -> str:
    return (
        profile.get_section(section_name, default)
        .replace("- ", "")
        .replace("\n", " / ")
    )


def build_card_data(person: RecognizedPerson) -> PersonCardData:
    if not person.known:
        return PersonCardData(
            track_id=person.track_id,
            name="Unknown",
            score=person.score,
            known=False,
        )

    profile = person.profile
    if profile is None:
        return PersonCardData(
            track_id=person.track_id,
            name=person.person_id or "Known",
            score=person.score,
            known=True,
            person_id=person.person_id or "",
        )

    return PersonCardData(
        track_id=person.track_id,
        name=profile.display_name,
        score=person.score,
        known=True,
        person_id=profile.person_id,
        relationship=profile.relationship,
        interests=section_to_inline(profile, "兴趣与偏好"),
        status=section_to_inline(profile, "当前状态"),
    )


def choose_unknown_person(
    people: list[RecognizedPerson],
) -> RecognizedPerson | None:
    unknown_people = sorted(
        (person for person in people if not person.known),
        key=lambda person: person.bbox[2] * person.bbox[3],
        reverse=True,
    )

    if not unknown_people:
        return None

    print()
    print("=" * 60)
    print("当前可登记的陌生人物：")
    print("输入 track_id 选择目标；直接回车默认选择面积最大的目标。")
    print("-" * 60)

    for person in unknown_people:
        x, y, w, h = person.bbox
        print(
            f"track_id={person.track_id:<3} "
            f"bbox=({x},{y},{w},{h}) "
            f"area={w * h:<6} "
            f"score={person.score:.3f}"
        )

    print("=" * 60)
    selected = input("请选择 track_id（留空默认最大人脸）：").strip()

    if not selected:
        return unknown_people[0]

    try:
        selected_track_id = int(selected)
    except ValueError:
        print("输入不是整数，已取消登记。")
        return None

    return next(
        (
            person
            for person in unknown_people
            if person.track_id == selected_track_id
        ),
        None,
    )


def register_unknown_person(
    person: RecognizedPerson,
    registration_service: PersonRegistrationService,
    pipeline: FaceRecognitionPipeline,
) -> None:
    print()
    print("=" * 60)
    print(
        f"正在登记陌生人物 PERSON #{person.track_id}"
    )
    print(f"当前最佳匹配分数：{person.score:.3f}")
    print("姓名留空可取消登记。")
    print("=" * 60)

    display_name = input("姓名：").strip()

    if not display_name:
        print("已取消人物登记。")
        return

    existing_profiles = (
        pipeline.memory_store.find_by_display_name(
            display_name
        )
    )

    # 存在同名人物时，打印档案并要求选择
    if existing_profiles:
        print()
        print(
            f"找到 {len(existing_profiles)} 个"
            f"名为「{display_name}」的人物："
        )

        for index, profile in enumerate(
            existing_profiles,
            start=1,
        ):
            print()
            print("=" * 60)
            print(f"编号：{index}")
            print(f"姓名：{profile.display_name}")
            print(f"person_id：{profile.person_id}")
            print(f"关系：{profile.relationship}")
            print(f"档案路径：{profile.profile_path}")

            created_at = profile.metadata.get(
                "created_at",
                "未知",
            )
            updated_at = profile.metadata.get(
                "updated_at",
                "未知",
            )
            confidence = profile.metadata.get(
                "confidence",
                "未知",
            )

            print(f"创建时间：{created_at}")
            print(f"更新时间：{updated_at}")
            print(f"置信度：{confidence}")

            if profile.sections:
                print("人物档案内容：")

                for section_name, content in (
                    profile.sections.items()
                ):
                    print()
                    print(f"【{section_name}】")
                    print(content or "暂无")

            print("=" * 60)

        print()
        print("请输入：")
        print("- 数字编号：添加人脸到已有的人物")
        print("- Y：新建一个同名人物")
        print("- 直接回车：取消")

        while True:
            choice = input("选择：").strip()

            if not choice:
                print("已取消人物登记。")
                return

            if choice.casefold() == "y":
                # 跳出选择流程，继续走新建人物逻辑
                break

            try:
                selected_index = int(choice) - 1
            except ValueError:
                print(
                    "输入无效，请输入数字编号、Y，"
                    "或直接回车取消。"
                )
                continue

            if not (
                0
                <= selected_index
                < len(existing_profiles)
            ):
                print(
                    f"请输入 1 到 "
                    f"{len(existing_profiles)} 之间的编号。"
                )
                continue

            selected_profile = existing_profiles[
                selected_index
            ]

            sample = (
                registration_service.add_face_sample(
                    person_id=(
                        selected_profile.person_id
                    ),
                    aligned_face=person.aligned_face,
                    feature=person.feature,
                )
            )

            pipeline.reload_indexes()

            print()
            print("人脸样本添加成功。")
            print(
                f"姓名："
                f"{selected_profile.display_name}"
            )
            print(
                f"person_id："
                f"{selected_profile.person_id}"
            )
            print(f"face_id：{sample.face_id}")
            print(
                f"样本路径："
                f"{sample.person_image_path}"
            )
            print()

            return

    # 没有同名人物，或者用户输入 Y
    print()
    print(
        f"将创建新的「{display_name}」人物档案。"
    )

    relationship = input(
        "关系（例如 friend / colleague）："
    ).strip() or "unknown"

    social_accounts = {
        "wechat": input(
            "微信（可留空）："
        ).strip(),
        "douyin": input(
            "抖音（可留空）："
        ).strip(),
        "x": input(
            "X（可留空）："
        ).strip(),
    }

    result = registration_service.register(
        display_name=display_name,
        aligned_face=person.aligned_face,
        feature=person.feature,
        relationship=relationship,
        social_accounts=social_accounts,
    )

    pipeline.reload_indexes()

    print()
    print("新人物登记成功。")
    print(f"姓名：{display_name}")
    print(f"person_id：{result.person_id}")
    print(f"face_id：{result.face_id}")
    print(f"人物档案：{result.profile_path}")
    print(f"人脸样本：{result.person_image_path}")
    print()

def main() -> None:
    if not VIDEO_PATH.exists():
        raise FileNotFoundError(f"视频不存在：{VIDEO_PATH}")

    pipeline = FaceRecognitionPipeline(
        detector_path=DETECTOR_PATH,
        recognizer_path=RECOGNIZER_PATH,
        known_faces_dir=KNOWN_FACES_DIR,
        people_dir=PEOPLE_DIR,
        cosine_threshold=COSINE_THRESHOLD,
    )
    registration_service = PersonRegistrationService(
        people_dir=PEOPLE_DIR,
        known_faces_dir=KNOWN_FACES_DIR,
    )

    print("已加载人脸样本：", ", ".join(pipeline.loaded_face_keys))
    print("已加载人物档案：", ", ".join(pipeline.loaded_person_ids))

    video = cv2.VideoCapture(str(VIDEO_PATH))
    if not video.isOpened():
        raise RuntimeError(f"无法打开视频：{VIDEO_PATH}")

    fps = video.get(cv2.CAP_PROP_FPS)
    frame_delay = max(1, round(1000 / fps)) if fps > 0 else 33
    video_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))

    create_adaptive_window(WINDOW_NAME, video_width, video_height)

    paused = False
    render_frame: np.ndarray | None = None
    visible_people: list[RecognizedPerson] = []

    print(
        "识别已启动：空格暂停/继续，"
        "R 选择并登记陌生人物，Q 或 Esc 退出"
    )

    try:
        while True:
            if not paused:
                ok, frame = video.read()
                if not ok:
                    video.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                visible_people = pipeline.process_frame(frame)

                for person in visible_people:
                    draw_person_overlay(
                        frame,
                        person.bbox,
                        build_card_data(person),
                    )

                cv2.putText(
                    frame,
                    "SPACE: Pause   R: Register   Q/ESC: Exit",
                    (25, 45),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (0, 255, 255),
                    2,
                    cv2.LINE_AA,
                )
                render_frame = frame.copy()

            if render_frame is not None:
                window_width, window_height = get_window_size(
                    WINDOW_NAME,
                    video_width,
                    video_height,
                )
                display_frame = resize_with_letterbox(
                    render_frame,
                    window_width,
                    window_height,
                )

                if paused:
                    cv2.putText(
                        display_frame,
                        "PAUSED",
                        (25, display_frame.shape[0] - 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 0, 255),
                        2,
                        cv2.LINE_AA,
                    )

                cv2.imshow(WINDOW_NAME, display_frame)

            key = cv2.waitKeyEx(30 if paused else frame_delay)

            if key == 32:
                paused = not paused
                print("已暂停" if paused else "继续播放")
                continue

            if key in (ord("r"), ord("R")):
                paused = True
                selected_person = choose_unknown_person(visible_people)

                if selected_person is None:
                    print("没有可登记的陌生人物，或目标选择已取消。")
                    continue

                try:
                    register_unknown_person(
                        person=selected_person,
                        registration_service=registration_service,
                        pipeline=pipeline,
                    )
                except Exception as error:
                    print(f"人物登记失败：{error}")
                continue

            if key in (ord("q"), ord("Q"), 27):
                break

            if is_window_closed(WINDOW_NAME):
                break

    finally:
        video.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
