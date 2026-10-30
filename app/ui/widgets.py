from __future__ import annotations

import math
import random

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPolygon,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QFrame,
    QGraphicsDropShadowEffect,
    QSizePolicy,
    QWidget,
)

from app.theme import assets


def format_clock(ms: int) -> str:
    total = max(0, int(ms // 1000))
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def format_ms(ms: int) -> str:
    total = max(0, int(ms))
    minutes, rem = divmod(total, 60_000)
    seconds, millis = divmod(rem, 1000)
    return f"{minutes:02d}:{seconds:02d}.{millis // 10:02d}"


def apply_shadow(widget: QWidget, blur: int = 28, alpha: int = 46, dy: int = 8) -> None:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, dy)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)


class TextureFrame(QFrame):
    """A frame that paints a cover-cropped texture, optional tint and border."""

    def __init__(
        self,
        texture: str = "",
        base: str = "#000000",
        tint: tuple[int, int, int, int] | None = None,
        radius: int = 0,
        border: str | None = None,
        texture_opacity: float = 1.0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._texture = texture
        self._base = base
        self._tint = tint
        self._radius = radius
        self._border = border
        self._texture_opacity = texture_opacity
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def configure(
        self,
        texture: str | None = None,
        base: str | None = None,
        tint: tuple[int, int, int, int] | None = None,
        border: str | None = None,
        texture_opacity: float | None = None,
    ) -> None:
        if texture is not None:
            self._texture = texture
        if base is not None:
            self._base = base
        if tint is not None:
            self._tint = tint
        if border is not None:
            self._border = border
        if texture_opacity is not None:
            self._texture_opacity = texture_opacity
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect()
        path = QPainterPath()
        if self._radius:
            path.addRoundedRect(QRectF(rect), self._radius, self._radius)
        else:
            path.addRect(QRectF(rect))
        painter.setClipPath(path)
        painter.fillPath(path, QColor(self._base))

        if self._texture:
            pm = assets.cover_pixmap(self._texture, rect.width(), rect.height())
            if not pm.isNull():
                painter.setOpacity(self._texture_opacity)
                offset = QPoint(
                    (pm.width() - rect.width()) // 2,
                    (pm.height() - rect.height()) // 2,
                )
                painter.drawPixmap(QPoint(-offset.x(), -offset.y()), pm)
                painter.setOpacity(1.0)

        if self._tint:
            painter.fillPath(path, QColor(*self._tint))

        if self._border:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(self._border), 1))
            painter.drawPath(path)


class Ornament(QWidget):
    def __init__(
        self,
        name: str,
        height: int = 48,
        opacity: float = 1.0,
        align=Qt.AlignmentFlag.AlignCenter,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._name = name
        self._height = height
        self._opacity = opacity
        self._align = align
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(height)

    def set_height(self, height: int) -> None:
        self._height = height
        self.setFixedHeight(height)
        self.update()

    def paintEvent(self, event) -> None:
        source = assets.pixmap(self._name)
        if source.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        scaled = source.scaledToHeight(self._height, Qt.TransformationMode.SmoothTransformation)
        if scaled.width() > self.width():
            scaled = scaled.scaledToWidth(
                self.width(), Qt.TransformationMode.SmoothTransformation
            )
        painter.setOpacity(self._opacity)
        x = 0
        if self._align & Qt.AlignmentFlag.AlignHCenter:
            x = (self.width() - scaled.width()) // 2
        elif self._align & Qt.AlignmentFlag.AlignRight:
            x = self.width() - scaled.width()
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)


class Divider(QWidget):
    def __init__(self, height: int = 24, color: str = "#B9B0A2", parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(height)
        self._color = color
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_color(self, color: str) -> None:
        self._color = color
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        source = assets.pixmap("divider.png")
        if not source.isNull():
            scaled = source.scaledToWidth(
                max(1, self.width()), Qt.TransformationMode.SmoothTransformation
            )
            if scaled.height() > self.height():
                scaled = scaled.scaledToHeight(
                    self.height(), Qt.TransformationMode.SmoothTransformation
                )
            painter.setOpacity(0.85)
            painter.drawPixmap(
                (self.width() - scaled.width()) // 2,
                (self.height() - scaled.height()) // 2,
                scaled,
            )
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        mid = self.height() // 2
        painter.setPen(QPen(QColor(self._color), 1))
        painter.drawLine(10, mid, self.width() // 2 - 16, mid)
        painter.drawLine(self.width() // 2 + 16, mid, self.width() - 10, mid)
        painter.setBrush(QColor(self._color))
        painter.drawPolygon(
            QPolygon(
                [
                    QPoint(self.width() // 2, mid - 4),
                    QPoint(self.width() // 2 + 4, mid),
                    QPoint(self.width() // 2, mid + 4),
                    QPoint(self.width() // 2 - 4, mid),
                ]
            )
        )


class Avatar(QWidget):
    def __init__(self, initials: str, color: str, size: int = 36, parent=None) -> None:
        super().__init__(parent)
        self._initials = initials
        self._color = color
        self._size = size
        self.setFixedSize(size, size)

    def set_values(self, initials: str, color: str) -> None:
        self._initials = initials
        self._color = color
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self._color))
        painter.drawEllipse(0, 0, self._size - 1, self._size - 1)
        font = QFont("Segoe UI", max(8, int(self._size * 0.34)), QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor("#FBF8F2"))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._initials)


class WaveformWidget(QWidget):
    seeked = Signal(float)

    def __init__(self, seed: int = 7, parent=None) -> None:
        super().__init__(parent)
        self._accent = "#9B2226"
        self._silver = "#C9C9C9"
        self._position = 0.0
        self._bpm = self._make(seed)
        self.setMinimumHeight(48)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    @staticmethod
    def _make(seed: int) -> list[float]:
        rng = random.Random(seed)
        amps: list[float] = []
        count = 240
        for index in range(count):
            envelope = 0.3 + 0.7 * abs(math.sin(index / 21.0)) * (1 - index / (count * 1.4))
            amps.append(max(0.05, min(1.0, rng.random() * envelope + 0.08)))
        return amps

    def set_colors(self, accent: str, silver: str) -> None:
        self._accent = accent
        self._silver = silver
        self.update()

    def set_position(self, value: float) -> None:
        self._position = max(0.0, min(1.0, value))
        self.update()

    def position(self) -> float:
        return self._position

    def _seek(self, x: float) -> None:
        if self.width() <= 0:
            return
        self.set_position(x / self.width())
        self.seeked.emit(self._position)

    def mousePressEvent(self, event) -> None:
        self._seek(event.position().x())

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._seek(event.position().x())

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        width = self.width()
        height = self.height()
        mid = height / 2
        painter.setPen(QPen(QColor(255, 255, 255, 26), 1))
        painter.drawLine(0, int(mid), width, int(mid))

        count = len(self._bpm)
        played_x = self._position * width
        accent = QColor(self._accent)
        silver = QColor(self._silver)
        silver.setAlpha(120)
        bar_width = 3
        step = max(3.0, (width - 4) / count)
        for index, amp in enumerate(self._bpm):
            x = 2 + index * step
            bar_height = max(3.0, amp * (height - 14))
            color = accent if x <= played_x else silver
            painter.setPen(QPen(color, bar_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(int(x), int(mid - bar_height / 2), int(x), int(mid + bar_height / 2))

        painter.setPen(QPen(QColor(245, 241, 234, 210), 1))
        painter.drawLine(int(played_x), 4, int(played_x), height - 4)
        painter.setBrush(QColor(245, 241, 234, 230))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(played_x - 3, mid - 3, 6, 6))


class PlayButton(QAbstractButton):
    def __init__(self, size: int = 54, parent=None) -> None:
        super().__init__(parent)
        self._size = size
        self._playing = False
        self._accent = "#9B2226"
        self._foreground = "#FBF8F2"
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_playing(self, playing: bool) -> None:
        self._playing = playing
        self.update()

    def set_colors(self, accent: str, foreground: str) -> None:
        self._accent = accent
        self._foreground = foreground
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        color = QColor(self._accent)
        if self.underMouse():
            color = color.lighter(112)
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.setBrush(color)
        painter.drawEllipse(1, 1, self._size - 3, self._size - 3)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self._foreground))
        if self._playing:
            bar_w = self._size * 0.09
            bar_h = self._size * 0.30
            center = self._size / 2
            painter.drawRoundedRect(
                QRectF(center - bar_w * 1.7, center - bar_h / 2, bar_w, bar_h), 2, 2
            )
            painter.drawRoundedRect(
                QRectF(center + bar_w * 0.7, center - bar_h / 2, bar_w, bar_h), 2, 2
            )
        else:
            path = QPainterPath()
            cx = self._size * 0.53
            cy = self._size / 2
            path.moveTo(cx - self._size * 0.09, cy - self._size * 0.14)
            path.lineTo(cx + self._size * 0.16, cy)
            path.lineTo(cx - self._size * 0.09, cy + self._size * 0.14)
            path.closeSubpath()
            painter.drawPath(path)
