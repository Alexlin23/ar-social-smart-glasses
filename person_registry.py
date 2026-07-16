from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

import frontmatter

from person_memory import PersonMemoryStore


class PersonRegistry:
    """负责创建基于 Markdown 的人物档案。"""

    def __init__(self, people_dir: str | Path = "people") -> None:
        self.people_dir = Path(people_dir)
        self.people_dir.mkdir(parents=True, exist_ok=True)

    def create_person(
        self,
        display_name: str,
        relationship: str = "unknown",
        social_accounts: dict[str, str] | None = None,
        *,
        face_key: str | None = None,
    ) -> Path:
        """
        创建人物档案。

        face_key 仅用于兼容旧调用方。新登记流程不再要求用户填写。
        """
        display_name = display_name.strip()
        relationship = relationship.strip() or "unknown"
        social_accounts = social_accounts or {}

        if not display_name:
            raise ValueError("人物姓名不能为空")

        if face_key:
            face_key = face_key.strip()
            self._ensure_legacy_face_key_unique(face_key)

        person_id = self._create_person_id()
        person_dir = self.people_dir / person_id
        self._create_directories(person_dir)

        now = datetime.now().astimezone().isoformat(timespec="seconds")
        metadata = {
            "schema_version": 2,
            "person_id": person_id,
            "display_name": display_name,
            "created_at": now,
            "updated_at": now,
            "relationship": relationship,
            "confidence": 1.0,
        }

        if face_key:
            metadata["legacy_face_key"] = face_key

        document = frontmatter.Post(
            self._build_profile_content(
                display_name=display_name,
                relationship=relationship,
                social_accounts=social_accounts,
            ),
            **metadata,
        )

        profile_path = person_dir / "profile.md"
        frontmatter.dump(document, profile_path)
        return profile_path

    def _create_person_id(self) -> str:
        while True:
            person_id = f"p_{uuid4().hex[:8]}"
            if not (self.people_dir / person_id).exists():
                return person_id

    def _ensure_legacy_face_key_unique(self, face_key: str) -> None:
        store = PersonMemoryStore(self.people_dir)
        store.load()
        existing = store.get_by_face_key(face_key)

        if existing is not None:
            raise ValueError(
                f"旧 face_key 已被人物 {existing.person_id} 使用：{face_key}"
            )

    @staticmethod
    def _create_directories(person_dir: Path) -> None:
        directories = [
            person_dir / "faces",
            person_dir / "conversations",
            person_dir / "events",
            person_dir / "sources" / "wechat",
            person_dir / "sources" / "douyin",
            person_dir / "sources" / "x",
            person_dir / "sources" / "other",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _build_profile_content(
        display_name: str,
        relationship: str,
        social_accounts: dict[str, str],
    ) -> str:
        accounts = "\n".join(
            f"- {platform}：{social_accounts.get(platform, '').strip() or '暂无'}"
            for platform in ("wechat", "douyin", "x")
        )

        return f"""# 人物档案：{display_name}

## 基本信息

- 姓名：{display_name}
- 与用户的关系：{relationship}
- 初次认识：
- 常见地点：

## 社交账号

{accounts}

## 兴趣与偏好

暂无。

## 当前状态

暂无。

## 近期事件

暂无。

## 历史互动摘要

暂无。

## 沟通偏好

暂无。

## 承诺与待办

暂无。

## 风险与注意事项

暂无。

## AI 交互建议

暂无。

## 信息来源

- 通过 AR 人物登记流程创建。
"""
