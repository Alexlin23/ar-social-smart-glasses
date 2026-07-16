from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field


BBox = tuple[int, int, int, int]


def bbox_iou(box_a: BBox, box_b: BBox) -> float:
    ax, ay, aw, ah = box_a
    bx, by, bw, bh = box_b

    left = max(ax, bx)
    top = max(ay, by)
    right = min(ax + aw, bx + bw)
    bottom = min(ay + ah, by + bh)

    intersection_width = max(0, right - left)
    intersection_height = max(0, bottom - top)
    intersection = intersection_width * intersection_height

    area_a = max(0, aw) * max(0, ah)
    area_b = max(0, bw) * max(0, bh)
    union = area_a + area_b - intersection

    if union <= 0:
        return 0.0

    return intersection / union


@dataclass
class Track:
    track_id: int
    bbox: BBox
    missing_frames: int = 0
    visible_frames: int = 1
    detection_index: int | None = None

    identity_history: deque[str] = field(
        default_factory=lambda: deque(maxlen=8)
    )
    score_history: deque[float] = field(
        default_factory=lambda: deque(maxlen=8)
    )

    def update_identity(self, name: str, score: float) -> None:
        self.identity_history.append(name)
        self.score_history.append(score)

    @property
    def stable_name(self) -> str:
        if not self.identity_history:
            return "Unknown"

        counts = Counter(self.identity_history)
        return counts.most_common(1)[0][0]

    @property
    def stable_score(self) -> float:
        if not self.score_history:
            return -1.0

        return sum(self.score_history) / len(self.score_history)


class SimpleIoUTracker:
    def __init__(
        self,
        iou_threshold: float = 0.25,
        max_missing_frames: int = 10,
    ) -> None:
        self.iou_threshold = iou_threshold
        self.max_missing_frames = max_missing_frames
        self.next_track_id = 1
        self.tracks: dict[int, Track] = {}

    def update(self, detections: list[BBox]) -> list[Track]:
        for track in self.tracks.values():
            track.detection_index = None

        candidates: list[tuple[float, int, int]] = []

        for track_id, track in self.tracks.items():
            for detection_index, detection in enumerate(detections):
                iou = bbox_iou(track.bbox, detection)

                if iou >= self.iou_threshold:
                    candidates.append(
                        (iou, track_id, detection_index)
                    )

        candidates.sort(reverse=True)

        matched_tracks: set[int] = set()
        matched_detections: set[int] = set()

        for _, track_id, detection_index in candidates:
            if track_id in matched_tracks:
                continue

            if detection_index in matched_detections:
                continue

            track = self.tracks[track_id]
            track.bbox = detections[detection_index]
            track.missing_frames = 0
            track.visible_frames += 1
            track.detection_index = detection_index

            matched_tracks.add(track_id)
            matched_detections.add(detection_index)

        for track_id, track in self.tracks.items():
            if track_id not in matched_tracks:
                track.missing_frames += 1

        for detection_index, detection in enumerate(detections):
            if detection_index in matched_detections:
                continue

            track = Track(
                track_id=self.next_track_id,
                bbox=detection,
                detection_index=detection_index,
            )

            self.tracks[track.track_id] = track
            self.next_track_id += 1

        expired_track_ids = [
            track_id
            for track_id, track in self.tracks.items()
            if track.missing_frames > self.max_missing_frames
        ]

        for track_id in expired_track_ids:
            del self.tracks[track_id]

        return [
            track
            for track in self.tracks.values()
            if track.detection_index is not None
        ]