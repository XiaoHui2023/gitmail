from __future__ import annotations

from rich.console import Console
from rich.theme import Theme

THEME = Theme(
    {
        "banner.title": "#61afef",
        "status.on": "#98c379",
        "status.off": "#e06c75",
        "status.warn": "#e5c07b",
        "label": "#abb2bf",
        "value": "#d7dae0",
        "path": "#61afef",
        "dim": "#5c6370",
        "url": "#56b6c2",
    }
)


def make_console() -> Console:
    return Console(
        theme=THEME,
        color_system="truecolor",
        force_terminal=True,
        legacy_windows=False,
    )
