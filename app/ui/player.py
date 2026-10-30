from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout

from app.ui.i18n import I18n
from app.ui.widgets import PlayButton, TextureFrame, WaveformWidget, format_clock

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

    MULTIMEDIA = True
except Exception:  # noqa: BLE001 - optional on stripped builds
    MULTIMEDIA = False


class PlayerBar(TextureFrame):
    position_changed = Signal(int)

    def __init__(self, i18n: I18n, parent=None) -> None:
        super().__init__(
            texture="leather.webp",
            base="#1A0707",
            tint=(10, 4, 4, 150),
            border="#3A1010",
            parent=parent,
        )
        self.i18n = i18n
        self.setObjectName("PlayerBar")
        self.setFixedHeight(98)
        self._duration_ms = 0
        self._position_ms = 0
        self._playing = False
        self._has_media = False
        self._media = None
        self._audio = None

        row = QHBoxLayout(self)
        row.setContentsMargins(20, 12, 20, 12)
        row.setSpacing(14)

        self.play = PlayButton(54)
        self.play.clicked.connect(self.toggle)
        row.addWidget(self.play, 0, Qt.AlignmentFlag.AlignVCenter)

        center = QVBoxLayout()
        center.setSpacing(2)
        head = QHBoxLayout()
        self.title = QLabel()
        self.title.setObjectName("PlayerTitle")
        self.time_label = QLabel()
        self.time_label.setObjectName("PlayerTime")
        head.addWidget(self.title, 1)
        head.addWidget(self.time_label, 0, Qt.AlignmentFlag.AlignRight)
        center.addLayout(head)

        self.wave = WaveformWidget(seed=11)
        self.wave.seeked.connect(self._on_seek)
        center.addWidget(self.wave)
        row.addLayout(center, 1)

        self.speed = QComboBox()
        for value in ("1.0×", "1.25×", "1.5×", "2.0×"):
            self.speed.addItem(value)
        self.speed.setFixedWidth(84)
        self.speed.currentIndexChanged.connect(self._on_speed_changed)
        row.addWidget(self.speed, 0, Qt.AlignmentFlag.AlignVCenter)

        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)

        if MULTIMEDIA:
            self._media = QMediaPlayer(self)
            self._audio = QAudioOutput(self)
            self._media.setAudioOutput(self._audio)
            self._media.positionChanged.connect(self._on_media_position)
            self._media.durationChanged.connect(self._on_media_duration)
            self._media.playbackStateChanged.connect(self._on_media_state)
            self._media.errorOccurred.connect(self._on_media_error)

        self._update_labels()

    def set_palette(self, palette) -> None:
        self.wave.set_colors(palette.accent, palette.silver)
        self.play.set_colors(palette.accent, palette.accent_text)

    def set_job(self, job) -> None:
        self._duration_ms = int(job["duration_ms"] or 0)
        self._position_ms = 0
        self.title.setText(job["title"])
        self._stop_fake()
        self._has_media = False

        source = job["source_path"]
        if self._media is not None:
            if source and Path(str(source)).exists():
                self._media.setSource(QUrl.fromLocalFile(str(source)))
                self._has_media = True
            else:
                self._media.setSource(QUrl())

        self._update_labels()
        self.position_changed.emit(0)

    def clear(self) -> None:
        self._duration_ms = 0
        self._position_ms = 0
        self.title.setText("")
        self._stop_fake()
        self._has_media = False
        if self._media is not None:
            self._media.setSource(QUrl())
        self._update_labels()

    def seek_ms(self, position_ms: int) -> None:
        limit = self._duration_ms or position_ms
        self._position_ms = max(0, min(limit, int(position_ms)))
        if self._has_media and self._media is not None:
            self._media.setPosition(self._position_ms)
        self._update_labels()
        self.position_changed.emit(self._position_ms)

    def toggle(self) -> None:
        if self._has_media and self._media is not None:
            if self._media.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self._media.pause()
            else:
                if (
                    self._duration_ms
                    and self._position_ms >= self._duration_ms
                    and self._media.playbackState() == QMediaPlayer.PlaybackState.StoppedState
                ):
                    self._media.setPosition(0)
                self._media.play()
            return

        if self._playing:
            self._stop_fake()
        else:
            if self._duration_ms and self._position_ms >= self._duration_ms:
                self._position_ms = 0
            self._playing = True
            self.play.set_playing(True)
            self._timer.start()

    def _stop_fake(self) -> None:
        self._playing = False
        self._timer.stop()
        self.play.set_playing(False)

    def _on_media_state(self, state) -> None:
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.play.set_playing(playing)

    def _on_media_position(self, position_ms: int) -> None:
        self._position_ms = int(position_ms)
        self._update_labels()
        self.position_changed.emit(self._position_ms)

    def _on_media_duration(self, duration_ms: int) -> None:
        if duration_ms > 0:
            self._duration_ms = int(duration_ms)
            self._update_labels()

    def _on_media_error(self, *_args) -> None:
        self._has_media = False

    def _on_speed_changed(self, _index: int) -> None:
        if self._has_media and self._media is not None:
            self._media.setPlaybackRate(self._speed_factor())

    def _on_seek(self, ratio: float) -> None:
        if self._duration_ms:
            self.seek_ms(int(ratio * self._duration_ms))

    def _speed_factor(self) -> float:
        text = self.speed.currentText().replace("×", "").strip()
        try:
            return float(text)
        except ValueError:
            return 1.0

    def _tick(self) -> None:
        if not self._duration_ms:
            return
        self._position_ms += int(50 * self._speed_factor())
        if self._position_ms >= self._duration_ms:
            self._position_ms = self._duration_ms
            self._stop_fake()
        self._update_labels()
        self.position_changed.emit(self._position_ms)

    def _update_labels(self) -> None:
        self.time_label.setText(
            f"{format_clock(self._position_ms)} / {format_clock(self._duration_ms)}"
        )
        ratio = self._position_ms / self._duration_ms if self._duration_ms else 0.0
        self.wave.set_position(ratio)
