"""Unicode HUD rendered over BGR frames; no changes to the original renderer."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .layout import place_panel, safe_area


def resolve_font(explicit=None):
    candidates = [Path(explicit)] if explicit else [
        Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/msyh.ttc',
        Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/simhei.ttf',
        Path('/System/Library/Fonts/PingFang.ttc'),
        Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError('未找到中文字体，请用 --font 指定支持中文的 TTF/OTF/TTC 文件。')


class HudRenderer:
    def __init__(self, font=None, margin=24):
        self.font_path = resolve_font(font)
        self.margin = margin
        self.last_panels = []

    @lru_cache(maxsize=32)
    def font(self, size):
        return ImageFont.truetype(self.font_path, size)

    def fit(self, text, width, size):
        text = ' '.join(str(text).split())
        font = self.font(size)
        if font.getlength(text) <= width:
            return text
        while text and font.getlength(text + '…') > width:
            text = text[:-1]
        return text + '…' if text else ''

    @lru_cache(maxsize=128)
    def panel(self, lines, width, size, contrast, accent):
        height = 20 + len(lines) * (size + 10)
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=10,
                               fill=(8, 16, 23, 245 if contrast else 185),
                               outline=accent, width=2)
        for index, line in enumerate(lines):
            draw.text((12, 8 + index * (size + 10)), self.fit(line, width - 24, size),
                      font=self.font(size), fill=accent if index == 0 else (240, 244, 248))
        return image

    @staticmethod
    def name(person):
        return (person.profile.display_name if person.profile else person.person_id) if person.known else '未登记人物'

    @staticmethod
    def reminder(person):
        if not person.known:
            return 'R 登记当前人物'
        if person.profile:
            for heading in ('承诺与待办', '近期事件', '历史互动摘要', '兴趣与偏好', '当前状态'):
                content = person.profile.get_section(heading, '').strip()
                if content and content not in ('暂无。', '暂无', '-', '无'):
                    return content.replace('- ', '')
        return '暂无提醒'

    def render(self, frame, people, selected, state, status='', subtitle=''):
        height, width = frame.shape[:2]
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert('RGBA')
        draw = ImageDraw.Draw(image)
        size = state.font_size
        safe = safe_area(width, height, self.margin, top=size + 22, bottom=size + 26)
        self.last_panels = []
        accent = (101, 246, 196)
        if not state.hidden and not state.paused:
            obstacles = [p.bbox for p in people]
            ordered = ([selected] if selected is not None else []) + [
                p for p in sorted(people, key=lambda p: p.track_id)
                if selected is None or p.track_id != selected.track_id]
            # Bound visual load even when the detector sees a crowd.
            for person in ordered[:5]:
                focused = selected is not None and person.track_id == selected.track_id
                color = accent if focused else (189, 201, 213)
                lines = [self.name(person) or '已登记人物']
                if focused:
                    lines.append(self.reminder(person))
                    if state.expanded and person.profile:
                        lines += ['关系：' + person.profile.relationship,
                                  '兴趣：' + person.profile.get_section('兴趣与偏好', '暂无'),
                                  '近况：' + person.profile.get_section('当前状态', '暂无')]
                panel_width = min(360 if focused else 180, safe[2])
                panel = self.panel(tuple(lines), panel_width, size, state.high_contrast, color)
                rect = place_panel(panel.size, person.bbox, safe, obstacles + self.last_panels)
                # If expanded content cannot fit, keep the compact card when possible.
                if rect is None and len(lines) > 2:
                    panel = self.panel(tuple(lines[:2]), panel_width, size, state.high_contrast, color)
                    rect = place_panel(panel.size, person.bbox, safe, obstacles + self.last_panels)
                if rect is None:
                    continue
                x, y, pw, ph = rect
                image.alpha_composite(panel, (x, y))
                self.last_panels.append(rect)
                if focused:
                    # A short bracket marks the selected face; no long lines through other faces.
                    bx, by, bw, bh = person.bbox
                    bx, by = max(0, bx), max(0, by)
                    draw.line([(bx, min(height-1, by+14)), (bx, by),
                               (min(width-1, bx+14), by)], fill=color, width=3)
        draw = ImageDraw.Draw(image)
        mode = '识别已暂停' if state.paused else ('信息已隐藏' if state.hidden else '识别中')
        header = f'● {mode}  |  {status}'
        draw.rectangle((0, 0, width, size + 20), fill=(8, 16, 23, 255))
        draw.text((12, 6), self.fit(header, width - 24, size), font=self.font(size), fill=accent)
        footer = subtitle or 'N 切换  E 展开  H 隐藏  空格 暂停  R 登记  Q 退出'
        footer_size = min(size, 18)
        draw.rectangle((0, height-footer_size-20, width, height), fill=(8, 16, 23, 255))
        draw.text((12, height-footer_size-15), self.fit(footer, width-24, footer_size),
                  font=self.font(footer_size), fill=(240, 244, 248))
        return cv2.cvtColor(np.array(image.convert('RGB')), cv2.COLOR_RGB2BGR)
