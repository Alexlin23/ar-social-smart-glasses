from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class PersonCardData:
    track_id: int
    name: str
    score: float
    known: bool
    person_id: str = ""
    relationship: str = "unknown"
    interests: str = "-"
    status: str = "-"


def _wrap_text(
    text: str,
    max_width: int,
    font_scale: float,
    thickness: int,
) -> list[str]:
    """按 OpenCV 实际像素宽度逐字符换行。"""
    text = str(text).strip() or "-"
    lines: list[str] = []
    current = ""

    for char in text:
        candidate = current + char
        width = cv2.getTextSize(
            candidate,
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            thickness,
        )[0][0]

        if width <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = char

    if current:
        lines.append(current)

    return lines


def _layout_card(
    raw_lines: list[str],
    max_width: int,
    max_height: int,
) -> tuple[int, int, list[str], float, int, int, int, bool]:
    """根据内容和空间计算卡片尺寸。"""
    max_width = max(120, int(max_width))
    max_height = max(70, int(max_height))

    if max_width < 240:
        font_scale = 0.42
        line_height = 18
        padding = 10
    else:
        font_scale = 0.52
        line_height = 22
        padding = 14

    thickness = 1
    preferred_width = min(380, max_width)
    inner_width = max(60, preferred_width - padding * 2)

    wrapped: list[str] = []
    for line in raw_lines:
        wrapped.extend(
            _wrap_text(
                line,
                inner_width,
                font_scale,
                thickness,
            )
        )

    max_lines = max(
        2,
        (max_height - padding * 2) // line_height,
    )

    truncated = len(wrapped) > max_lines
    visible_lines = wrapped[:max_lines]

    if truncated and visible_lines:
        last = visible_lines[-1]
        visible_lines[-1] = (
            last[:-3] + "..."
            if len(last) > 3
            else "..."
        )

    measured_width = max(
        (
            cv2.getTextSize(
                line,
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                thickness,
            )[0][0]
            for line in visible_lines
        ),
        default=100,
    )

    card_width = min(
        max_width,
        max(180, measured_width + padding * 2),
    )
    card_height = min(
        max_height,
        padding * 2 + len(visible_lines) * line_height,
    )

    return (
        card_width,
        card_height,
        visible_lines,
        font_scale,
        thickness,
        line_height,
        padding,
        truncated,
    )


def _build_raw_lines(card: PersonCardData) -> list[str]:
    if not card.known:
        return [
            f"PERSON #{card.track_id}",
            "UNKNOWN PERSON",
            f"Best match: {card.score:.2f}",
            "Registration required",
            "Press R to create profile",
        ]

    return [
        f"PERSON #{card.track_id}",
        f"ID: {card.person_id or '-'}",
        f"Name: {card.name}",
        f"Match: {card.score:.2f}",
        f"Relation: {card.relationship}",
        f"Interests: {card.interests}",
        f"Status: {card.status}",
    ]


def draw_person_overlay(
    frame: np.ndarray,
    bbox: tuple[int, int, int, int],
    card: PersonCardData,
) -> None:
    """绘制人脸框、外部连线和内容自适应人物卡片。"""
    x, y, w, h = bbox
    frame_height, frame_width = frame.shape[:2]

    color = (
        (0, 255, 0)
        if card.known
        else (0, 80, 255)
    )

    cv2.rectangle(
        frame,
        (x, y),
        (x + w, y + h),
        color,
        3,
        cv2.LINE_AA,
    )

    edge_margin = 10
    face_gap = 30
    raw_lines = _build_raw_lines(card)

    candidates = [
        (
            "right",
            frame_width - edge_margin - (x + w + face_gap),
            frame_height - edge_margin * 2,
            4,
        ),
        (
            "left",
            x - face_gap - edge_margin,
            frame_height - edge_margin * 2,
            3,
        ),
        (
            "below",
            frame_width - edge_margin * 2,
            frame_height - edge_margin - (y + h + face_gap),
            2,
        ),
        (
            "above",
            frame_width - edge_margin * 2,
            y - face_gap - edge_margin,
            1,
        ),
    ]

    evaluated = []

    for direction, max_width, max_height, preference in candidates:
        if max_width < 120 or max_height < 70:
            continue

        layout = _layout_card(
            raw_lines,
            max_width=max_width,
            max_height=max_height,
        )

        (
            card_width,
            card_height,
            display_lines,
            font_scale,
            thickness,
            line_height,
            padding,
            truncated,
        ) = layout

        score = (
            (0 if truncated else 10_000)
            + len(display_lines) * 100
            + min(card_width, 380)
            + preference
        )

        evaluated.append(
            (
                score,
                direction,
                layout,
            )
        )

    if not evaluated:
        # 极端近景：选面积最大的外部区域，仍不覆盖人脸框。
        direction, max_width, max_height, _ = max(
            candidates,
            key=lambda item: max(0, item[1]) * max(0, item[2]),
        )
        layout = _layout_card(
            raw_lines,
            max_width=max(120, max_width),
            max_height=max(70, max_height),
        )
    else:
        _, direction, layout = max(
            evaluated,
            key=lambda item: item[0],
        )

    (
        card_width,
        card_height,
        display_lines,
        font_scale,
        thickness,
        line_height,
        padding,
        _,
    ) = layout

    face_center_x = x + w // 2
    face_center_y = y + h // 2

    if direction == "right":
        card_x = x + w + face_gap
        card_y = max(
            edge_margin,
            min(
                face_center_y - card_height // 2,
                frame_height - edge_margin - card_height,
            ),
        )
        line_start = (x + w, face_center_y)
        line_end = (card_x, card_y + card_height // 2)

    elif direction == "left":
        card_x = x - face_gap - card_width
        card_y = max(
            edge_margin,
            min(
                face_center_y - card_height // 2,
                frame_height - edge_margin - card_height,
            ),
        )
        line_start = (x, face_center_y)
        line_end = (
            card_x + card_width,
            card_y + card_height // 2,
        )

    elif direction == "below":
        card_x = max(
            edge_margin,
            min(
                face_center_x - card_width // 2,
                frame_width - edge_margin - card_width,
            ),
        )
        card_y = y + h + face_gap
        line_start = (face_center_x, y + h)
        line_end = (card_x + card_width // 2, card_y)

    else:
        card_x = max(
            edge_margin,
            min(
                face_center_x - card_width // 2,
                frame_width - edge_margin - card_width,
            ),
        )
        card_y = y - face_gap - card_height
        line_start = (face_center_x, y)
        line_end = (
            card_x + card_width // 2,
            card_y + card_height,
        )

    cv2.line(
        frame,
        line_start,
        line_end,
        color,
        2,
        cv2.LINE_AA,
    )

    overlay = frame.copy()
    cv2.rectangle(
        overlay,
        (card_x, card_y),
        (card_x + card_width, card_y + card_height),
        (20, 20, 20),
        -1,
    )
    cv2.addWeighted(
        overlay,
        0.76,
        frame,
        0.24,
        0,
        frame,
    )
    cv2.rectangle(
        frame,
        (card_x, card_y),
        (card_x + card_width, card_y + card_height),
        color,
        2,
        cv2.LINE_AA,
    )

    for index, text in enumerate(display_lines):
        cv2.putText(
            frame,
            text,
            (
                card_x + padding,
                card_y + padding + line_height * (index + 1) - 4,
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            color,
            thickness,
            cv2.LINE_AA,
        )
