from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from face_identity_store import FaceIdentityStore, StoredFaceSample
from person_registry import PersonRegistry


@dataclass(frozen=True)
class RegistrationResult:
    person_id: str
    face_id: str
    profile_path: Path
    person_image_path: Path
    person_feature_path: Path
    cached_image_path: Path
    cached_feature_path: Path


class PersonRegistrationService:
    """创建人物，并为该人物登记第一张 face_id 样本。"""

    def __init__(
        self,
        people_dir: str | Path = "people",
        known_faces_dir: str | Path = "known_faces",
    ) -> None:
        self.people_dir = Path(people_dir)
        self.known_faces_dir = Path(known_faces_dir)
        self.registry = PersonRegistry(self.people_dir)
        self.face_store = FaceIdentityStore(
            people_dir=self.people_dir,
            known_faces_dir=self.known_faces_dir,
        )

    def register(
        self,
        display_name: str,
        aligned_face: np.ndarray,
        feature: np.ndarray,
        relationship: str = "unknown",
        social_accounts: dict[str, str] | None = None,
    ) -> RegistrationResult:
        profile_path: Path | None = None
        stored_sample: StoredFaceSample | None = None

        try:
            profile_path = self.registry.create_person(
                display_name=display_name,
                relationship=relationship,
                social_accounts=social_accounts,
            )
            person_id = profile_path.parent.name

            stored_sample = self.face_store.save_face_sample(
                person_id=person_id,
                aligned_face=aligned_face,
                feature=feature,
            )

            return RegistrationResult(
                person_id=person_id,
                face_id=stored_sample.face_id,
                profile_path=profile_path,
                person_image_path=stored_sample.person_image_path,
                person_feature_path=stored_sample.person_feature_path,
                cached_image_path=stored_sample.cached_image_path,
                cached_feature_path=stored_sample.cached_feature_path,
            )

        except Exception:
            if stored_sample is not None:
                self.face_store.delete_face_sample(stored_sample)

            if profile_path is not None and profile_path.parent.exists():
                shutil.rmtree(profile_path.parent)
            raise

    def add_face_sample(
        self,
        person_id: str,
        aligned_face: np.ndarray,
        feature: np.ndarray,
    ) -> StoredFaceSample:
        """为已有人物增加另一张 face_id 样本。"""
        return self.face_store.save_face_sample(
            person_id=person_id,
            aligned_face=aligned_face,
            feature=feature,
        )
