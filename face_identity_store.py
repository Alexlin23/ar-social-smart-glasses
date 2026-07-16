from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np

from person_memory import PersonMemoryStore


@dataclass(frozen=True)
class StoredFaceSample:
    person_id: str
    face_id: str
    person_image_path: Path
    person_feature_path: Path
    cached_image_path: Path
    cached_feature_path: Path


@dataclass(frozen=True)
class LoadedFaceFeature:
    person_id: str
    face_id: str
    feature: np.ndarray
    feature_path: Path
    legacy: bool = False


class FaceIdentityStore:
    """管理 person_id 对应的多个 face_id 人脸样本。"""

    CACHE_SEPARATOR = "__"

    def __init__(
        self,
        people_dir: str | Path = "people",
        known_faces_dir: str | Path = "known_faces",
    ) -> None:
        self.people_dir = Path(people_dir)
        self.known_faces_dir = Path(known_faces_dir)
        self.people_dir.mkdir(parents=True, exist_ok=True)
        self.known_faces_dir.mkdir(parents=True, exist_ok=True)

    def save_face_sample(
        self,
        person_id: str,
        aligned_face: np.ndarray,
        feature: np.ndarray,
        face_id: str | None = None,
    ) -> StoredFaceSample:
        person_id = person_id.strip()
        if not person_id:
            raise ValueError("person_id 不能为空")

        person_dir = self.people_dir / person_id
        profile_path = person_dir / "profile.md"
        if not profile_path.exists():
            raise FileNotFoundError(f"人物档案不存在：{profile_path}")

        self._validate_array(aligned_face, "人脸图片")
        self._validate_array(feature, "人脸特征")

        face_id = (
            self._validate_face_id(face_id)
            if face_id
            else self._create_face_id(person_dir)
        )

        faces_dir = person_dir / "faces"
        faces_dir.mkdir(parents=True, exist_ok=True)

        person_image_path = faces_dir / f"{face_id}.jpg"
        person_feature_path = faces_dir / f"{face_id}.npy"

        cache_stem = f"{person_id}{self.CACHE_SEPARATOR}{face_id}"
        cached_image_path = self.known_faces_dir / f"{cache_stem}.jpg"
        cached_feature_path = self.known_faces_dir / f"{cache_stem}.npy"

        all_paths = (
            person_image_path,
            person_feature_path,
            cached_image_path,
            cached_feature_path,
        )
        if any(path.exists() for path in all_paths):
            raise FileExistsError(f"人脸样本已存在：{person_id}/{face_id}")

        try:
            self._save_image(person_image_path, aligned_face)
            np.save(person_feature_path, feature.copy())
            self._save_image(cached_image_path, aligned_face)
            np.save(cached_feature_path, feature.copy())
        except Exception:
            for path in all_paths:
                path.unlink(missing_ok=True)
            raise

        return StoredFaceSample(
            person_id=person_id,
            face_id=face_id,
            person_image_path=person_image_path,
            person_feature_path=person_feature_path,
            cached_image_path=cached_image_path,
            cached_feature_path=cached_feature_path,
        )

    def load_feature_index(
        self,
        memory_store: PersonMemoryStore,
    ) -> list[LoadedFaceFeature]:
        loaded: list[LoadedFaceFeature] = []

        for feature_path in sorted(
            self.known_faces_dir.glob("*.npy")
        ):
            stem = feature_path.stem

            # 新格式必须为：
            # <person_id>__<face_id>.npy
            if self.CACHE_SEPARATOR not in stem:
                continue

            person_id, face_id = stem.split(
                self.CACHE_SEPARATOR,
                maxsplit=1,
            )

            if not person_id or not face_id:
                continue

            profile = memory_store.get_by_person_id(
                person_id
            )

            if profile is None:
                print(
                    "跳过没有人物档案的人脸样本："
                    f"{feature_path}"
                )
                continue

            try:
                feature = np.load(feature_path)
            except Exception as error:
                print(
                    f"无法读取人脸特征 {feature_path}："
                    f"{error}"
                )
                continue

            loaded.append(
                LoadedFaceFeature(
                    person_id=person_id,
                    face_id=face_id,
                    feature=feature,
                    feature_path=feature_path,
                    legacy=False,
                )
            )

        return loaded

    def delete_face_sample(self, sample: StoredFaceSample) -> None:
        for path in (
            sample.person_image_path,
            sample.person_feature_path,
            sample.cached_image_path,
            sample.cached_feature_path,
        ):
            path.unlink(missing_ok=True)

    @staticmethod
    def _validate_array(value: np.ndarray, label: str) -> None:
        if value is None or value.size == 0:
            raise ValueError(f"{label}为空")

    @staticmethod
    def _save_image(path: Path, image: np.ndarray) -> None:
        if not cv2.imwrite(str(path), image):
            raise RuntimeError(f"无法保存图片：{path}")

    @staticmethod
    def _validate_face_id(face_id: str) -> str:
        face_id = face_id.strip()
        if not face_id:
            raise ValueError("face_id 不能为空")
        if any(char in face_id for char in r'\/:*?"<>|'):
            raise ValueError("face_id 包含非法文件名字符")
        return face_id

    @staticmethod
    def _create_face_id(person_dir: Path) -> str:
        faces_dir = person_dir / "faces"
        while True:
            face_id = f"face_{uuid4().hex[:8]}"
            if not any(
                (
                    (faces_dir / f"{face_id}.jpg").exists(),
                    (faces_dir / f"{face_id}.npy").exists(),
                )
            ):
                return face_id
