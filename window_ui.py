from __future__ import annotations

import ctypes

import cv2
import numpy as np


def resize_with_letterbox(
    frame: np.ndarray,
    target_width: int,
    target_height: int,
) -> np.ndarray:
    """等比例缩放画面，空余区域使用黑边填充。"""
    source_height, source_width = frame.shape[:2]
    target_width = max(1, int(target_width))
    target_height = max(1, int(target_height))

    scale = min(
        target_width / source_width,
        target_height / source_height,
    )

    resized_width = max(1, round(source_width * scale))
    resized_height = max(1, round(source_height * scale))

    interpolation = (
        cv2.INTER_AREA
        if scale < 1.0
        else cv2.INTER_LINEAR
    )

    resized = cv2.resize(
        frame,
        (resized_width, resized_height),
        interpolation=interpolation,
    )

    canvas = np.zeros(
        (target_height, target_width, 3),
        dtype=np.uint8,
    )

    offset_x = (target_width - resized_width) // 2
    offset_y = (target_height - resized_height) // 2

    canvas[
        offset_y : offset_y + resized_height,
        offset_x : offset_x + resized_width,
    ] = resized

    return canvas


def create_adaptive_window(
    window_name: str,
    video_width: int,
    video_height: int,
    screen_ratio: float = 0.85,
) -> None:
    """按视频比例创建初始窗口，之后允许手动缩放。"""
    if video_width <= 0 or video_height <= 0:
        video_width, video_height = 1280, 720

    try:
        screen_width = ctypes.windll.user32.GetSystemMetrics(0)
        screen_height = ctypes.windll.user32.GetSystemMetrics(1)
    except (AttributeError, OSError):
        screen_width, screen_height = 1920, 1080

    max_width = int(screen_width * screen_ratio)
    max_height = int(screen_height * screen_ratio)

    scale = min(
        max_width / video_width,
        max_height / video_height,
    )

    initial_width = max(320, round(video_width * scale))
    initial_height = max(240, round(video_height * scale))

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, initial_width, initial_height)


def get_window_size(
    window_name: str,
    fallback_width: int,
    fallback_height: int,
) -> tuple[int, int]:
    """读取 OpenCV 窗口当前图像区域大小。"""
    try:
        _, _, width, height = cv2.getWindowImageRect(window_name)
    except cv2.error:
        return fallback_width, fallback_height

    if width <= 1 or height <= 1:
        return fallback_width, fallback_height

    return width, height


def is_window_closed(window_name: str) -> bool:
    try:
        return (
            cv2.getWindowProperty(
                window_name,
                cv2.WND_PROP_VISIBLE,
            )
            < 1
        )
    except cv2.error:
        return True
