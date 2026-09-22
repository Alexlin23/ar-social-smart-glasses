"""Select a visible track, without pretending to provide gaze tracking."""
from __future__ import annotations


class FocusManager:
    def __init__(self, grace_seconds: float = 0.6):
        self.track_id = None
        self.last_seen = 0.0
        self.grace_seconds = grace_seconds

    def clear(self):
        self.track_id = None
        self.last_seen = 0.0

    def update(self, people, width: int, height: int, now: float):
        current = next((p for p in people if p.track_id == self.track_id), None)
        if current is not None:
            self.last_seen = now
            return current
        # Never render the disappeared person's card during the grace interval.
        if self.track_id is not None and now - self.last_seen < self.grace_seconds:
            return None
        self.clear()
        if people:
            current = min(people, key=lambda p: (
                ((p.bbox[0] + p.bbox[2] / 2 - width / 2) / width) ** 2
                + ((p.bbox[1] + p.bbox[3] / 2 - height / 2) / height) ** 2,
                p.track_id,
            ))
            self.track_id, self.last_seen = current.track_id, now
        return current

    def cycle(self, people, now: float, direction: int = 1):
        if not people:
            self.clear()
            return None
        ordered = sorted(people, key=lambda p: (p.bbox[0], p.track_id))
        ids = [p.track_id for p in ordered]
        index = (ids.index(self.track_id) + direction) % len(ids) if self.track_id in ids else 0
        self.track_id, self.last_seen = ids[index], now
        return ordered[index]
