from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from app.paths import ASSETS_DIR


@lru_cache(maxsize=64)
def pixmap(name: str) -> QPixmap:
    if not name:
        return QPixmap()
    path = ASSETS_DIR / name
    if not path.exists():
        return QPixmap()
    return QPixmap(str(path))


@lru_cache(maxsize=48)
def cover_pixmap(name: str, width: int, height: int) -> QPixmap:
    if width <= 0 or height <= 0:
        return QPixmap()
    source = pixmap(name)
    if source.isNull():
        return QPixmap()
    return source.scaled(
        width,
        height,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )


def assets_ready() -> bool:
    return (ASSETS_DIR / "paper.webp").exists() and (ASSETS_DIR / "divider.png").exists()
