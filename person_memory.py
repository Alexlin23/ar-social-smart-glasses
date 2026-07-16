from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import frontmatter


@dataclass(frozen=True)
class PersonProfile:
    """由 profile.md 加载得到的人物长期档案。"""

    person_id: str
    display_name: str
    relationship: str
    profile_path: Path
    metadata: dict[str, Any]
    sections: dict[str, str]
    legacy_face_key: str | None = None

    @property
    def face_key(self) -> str | None:
        """仅用于兼容旧档案；新档案改用 person_id + face_id。"""
        return self.legacy_face_key

    def get_section(self, section_name: str, default: str = "") -> str:
        return self.sections.get(section_name, default)


class PersonMemoryStore:
    """读取并索引 people/*/profile.md。"""

    def __init__(self, people_dir: str | Path = "people") -> None:
        self.people_dir = Path(people_dir)
        self.profiles_by_id: dict[str, PersonProfile] = {}
        self.profiles_by_legacy_face_key: dict[str, PersonProfile] = {}

    def load(self) -> None:
        self.profiles_by_id.clear()
        self.profiles_by_legacy_face_key.clear()

        if not self.people_dir.exists():
            return

        for profile_path in sorted(self.people_dir.glob("*/profile.md")):
            profile = self._load_profile(profile_path)
            self.profiles_by_id[profile.person_id] = profile

            if profile.legacy_face_key:
                self.profiles_by_legacy_face_key[
                    profile.legacy_face_key
                ] = profile

    def get_by_person_id(self, person_id: str) -> PersonProfile | None:
        return self.profiles_by_id.get(person_id)
    def find_by_display_name(
        self,
        display_name: str,
    ) -> list[PersonProfile]:
        """按姓名查找所有同名人物。"""
        normalized_name = display_name.strip().casefold()

        if not normalized_name:
            return []

        return [
            profile
            for profile in self.profiles_by_id.values()
            if profile.display_name.strip().casefold()
            == normalized_name
        ]
    def get_by_face_key(self, face_key: str) -> PersonProfile | None:
        """兼容旧 known_faces/<face_key>.npy；新代码应按 person_id 查询。"""
        return self.profiles_by_legacy_face_key.get(face_key)

    def _load_profile(self, profile_path: Path) -> PersonProfile:
        post = frontmatter.load(profile_path)
        metadata = dict(post.metadata)

        person_id = str(metadata.get("person_id") or profile_path.parent.name)
        display_name = str(metadata.get("display_name") or person_id)
        relationship = str(metadata.get("relationship") or "unknown")

        legacy_face_key_value = (
            metadata.get("face_key") or metadata.get("legacy_face_key")
        )
        legacy_face_key = (
            str(legacy_face_key_value) if legacy_face_key_value else None
        )

        return PersonProfile(
            person_id=person_id,
            display_name=display_name,
            relationship=relationship,
            profile_path=profile_path,
            metadata=metadata,
            sections=self._parse_sections(post.content),
            legacy_face_key=legacy_face_key,
        )

    @staticmethod
    def _parse_sections(content: str) -> dict[str, str]:
        sections: dict[str, list[str]] = {}
        current_heading: str | None = None

        for raw_line in content.splitlines():
            line = raw_line.rstrip()

            if line.startswith("## "):
                current_heading = line[3:].strip()
                sections[current_heading] = []
                continue

            if current_heading is not None:
                sections[current_heading].append(line)

        return {
            heading: "\n".join(lines).strip()
            for heading, lines in sections.items()
        }
