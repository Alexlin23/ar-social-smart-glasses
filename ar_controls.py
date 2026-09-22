"""Hardware-independent actions; a future glasses adapter can call apply()."""
from dataclasses import dataclass
from enum import Enum


class Action(Enum):
    NONE = 'none'
    NEXT = 'next'
    PREVIOUS = 'previous'
    EXPAND = 'expand'
    HIDE = 'hide'
    PAUSE = 'pause'
    CONTRAST = 'contrast'
    LARGER = 'larger'
    SMALLER = 'smaller'
    REGISTER = 'register'
    QUIT = 'quit'


KEYS = {9: Action.NEXT, ord('n'): Action.NEXT, ord('b'): Action.PREVIOUS,
        13: Action.EXPAND, 10: Action.EXPAND, ord('e'): Action.EXPAND,
        ord('h'): Action.HIDE, 32: Action.PAUSE, ord('c'): Action.CONTRAST,
        ord('+'): Action.LARGER, ord('='): Action.LARGER,
        ord('-'): Action.SMALLER, ord('r'): Action.REGISTER,
        ord('q'): Action.QUIT, 27: Action.QUIT}


def action_for_key(key):
    if 65 <= key <= 90:
        key += 32
    return KEYS.get(key, Action.NONE)


@dataclass
class ViewState:
    paused: bool = False
    hidden: bool = False
    expanded: bool = False
    high_contrast: bool = True
    font_size: int = 22

    def apply(self, action):
        if action == Action.HIDE:
            self.hidden = not self.hidden
        elif action == Action.PAUSE:
            self.paused = not self.paused
            self.expanded = False
        elif action == Action.EXPAND:
            self.expanded = not self.expanded
        elif action == Action.CONTRAST:
            self.high_contrast = not self.high_contrast
        elif action == Action.LARGER:
            self.font_size = min(40, self.font_size + 2)
        elif action == Action.SMALLER:
            self.font_size = max(16, self.font_size - 2)
