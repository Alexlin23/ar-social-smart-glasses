from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from face_identity_store import FaceIdentityStore, LoadedFaceFeature
from person_memory import PersonMemoryStore, PersonProfile
from simple_tracker import SimpleIoUTracker


BBox = tuple[int, int, int, int]


@dataclass(frozen=True)
class RecognizedPerson:
    track_id: int
    bbox: BBox
    person_id: str | None
    face_id: str | None
    score: float
    profile: PersonProfile | None
    aligned_face: np.ndarray
    feature: np.ndarray

    @property
    def known(self) -> bool:
        return self.person_id is not None


class FaceRecognitionPipeline:
    """负责人脸检测、识别、跟踪和人物档案关联。"""

    def __init__(
        self,
        detector_path: str | Path,
        recognizer_path: str | Path,
        known_faces_dir: str | Path = "known_faces",
        people_dir: str | Path = "people",
        cosine_threshold: float = 0.45,
    ) -> None:
        self.detector_path = Path(detector_path)
        self.recognizer_path = Path(recognizer_path)
        self.known_faces_dir = Path(known_faces_dir)
        self.people_dir = Path(people_dir)
        self.cosine_threshold = cosine_threshold

        self._validate_paths()

        self.memory_store = PersonMemoryStore(self.people_dir)
        self.face_store = FaceIdentityStore(
            people_dir=self.people_dir,
            known_faces_dir=self.known_faces_dir,
        )
        self.known_face_samples: list[LoadedFaceFeature] = []
        self.reload_indexes()

        self.detector = cv2.FaceDetectorYN.create(
            model=str(self.detector_path),
            config="",
            input_size=(320, 320),
            score_threshold=0.8,
            nms_threshold=0.3,
            top_k=5000,
        )
        self.recognizer = cv2.FaceRecognizerSF.create(
            str(self.recognizer_path),
            "",
        )
        self.tracker = SimpleIoUTracker(
            iou_threshold=0.25,
            max_missing_frames=10,
        )

    def _validate_paths(self) -> None:
        if not self.detector_path.exists():
            raise FileNotFoundError(
                f"人脸检测模型不存在：{self.detector_path}"
            )
        if not self.recognizer_path.exists():
            raise FileNotFoundError(
                f"人脸识别模型不存在：{self.recognizer_path}"
            )

        self.known_faces_dir.mkdir(parents=True, exist_ok=True)
        self.people_dir.mkdir(parents=True, exist_ok=True)

    def reload_indexes(self) -> None:
        self.memory_store.load()

        self.known_face_samples = (
            self.face_store.load_feature_index(
                self.memory_store
            )
        )

        if self.known_face_samples:
            print(
                "已加载人脸样本数量："
                f"{len(self.known_face_samples)}"
            )
        else:
            print(
                "当前没有已登记的人脸样本，"
                "所有检测到的人物将显示为 Unknown。"
            )

    @property
    def loaded_face_keys(self) -> list[str]:
        """兼容旧主程序的显示属性，内容已变为 person_id/face_id。"""
        return sorted(
            f"{sample.person_id}/{sample.face_id}"
            for sample in self.known_face_samples
        )

    @property
    def loaded_person_ids(self) -> list[str]:
        return sorted(self.memory_store.profiles_by_id.keys())

    def process_frame(
        self,
        frame: np.ndarray,
    ) -> list[RecognizedPerson]:
        height, width = frame.shape[:2]
        self.detector.setInputSize((width, height))
        _, faces = self.detector.detect(frame)

        detections: list[BBox] = []
        face_rows: list[np.ndarray] = []

        if faces is not None:
            for face in faces:
                x, y, w, h = face[:4].astype(int)
                detections.append((x, y, w, h))
                face_rows.append(face)

        visible_tracks = self.tracker.update(detections)
        results: list[RecognizedPerson] = []

        for track in visible_tracks:
            detection_index = track.detection_index
            if detection_index is None or detection_index >= len(face_rows):
                continue

            face = face_rows[detection_index]
            aligned_face = self.recognizer.alignCrop(frame, face)
            current_feature = self.recognizer.feature(aligned_face)

            (
                current_person_id,
                current_face_id,
                current_score,
            ) = self._match_feature(current_feature)

            current_identity = current_person_id or "Unknown"
            track.update_identity(current_identity, current_score)

            stable_identity = track.stable_name
            stable_score = track.stable_score
            stable_person_id = (
                stable_identity if stable_identity != "Unknown" else None
            )
            stable_face_id = (
                current_face_id
                if current_person_id == stable_person_id
                else None
            )
            profile = (
                self.memory_store.get_by_person_id(stable_person_id)
                if stable_person_id is not None
                else None
            )

            results.append(
                RecognizedPerson(
                    track_id=track.track_id,
                    bbox=track.bbox,
                    person_id=stable_person_id,
                    face_id=stable_face_id,
                    score=stable_score,
                    profile=profile,
                    aligned_face=aligned_face.copy(),
                    feature=current_feature.copy(),
                )
            )

        return results

    def _match_feature(
        self,
        current_feature: np.ndarray,
    ) -> tuple[str | None, str | None, float]:
        best_person_id: str | None = None
        best_face_id: str | None = None
        best_score = -1.0

        for sample in self.known_face_samples:
            score = float(
                self.recognizer.match(
                    current_feature,
                    sample.feature,
                    cv2.FaceRecognizerSF_FR_COSINE,
                )
            )

            if score > best_score:
                best_score = score
                best_person_id = sample.person_id
                best_face_id = sample.face_id

        if best_score < self.cosine_threshold:
            return None, None, best_score

        return best_person_id, best_face_id, best_score
