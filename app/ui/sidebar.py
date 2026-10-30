from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.i18n import I18n
from app.ui.widgets import Divider, TextureFrame, format_clock

NAV_ITEMS = [
    ("transcripts", "nav_transcripts"),
    ("speakers", "nav_speakers"),
    ("settings", "nav_settings"),
]


def _repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class JobCard(QFrame):
    clicked = Signal(int)

    def __init__(self, job, active: bool, i18n: I18n, parent=None) -> None:
        super().__init__(parent)
        self.job_id = int(job["id"])
        self.setObjectName("JobCard")
        self.setProperty("active", "true" if active else "false")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)

        align = (
            Qt.AlignmentFlag.AlignRight
            if i18n.rtl
            else Qt.AlignmentFlag.AlignLeft
        ) | Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignVCenter
        title = QLabel(job["title"])
        title.setObjectName("JobTitle")
        title.setAlignment(align)

        status = job["status"]
        if status in {"queued", "processing", "failed", "cancelled"}:
            meta_text = i18n.t(f"status_{status}")
        else:
            meta_text = (
                f"{job['speaker_count']} {i18n.t('total_speakers')} · "
                f"{format_clock(job['duration_ms'])}"
            )
        meta = QLabel(meta_text)
        meta.setObjectName("JobMeta")
        meta.setAlignment(align)
        layout.addWidget(title)
        layout.addWidget(meta)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.job_id)
        super().mousePressEvent(event)


class Sidebar(TextureFrame):
    job_selected = Signal(int)
    nav_changed = Signal(str)
    new_job = Signal()

    def __init__(self, i18n: I18n, parent=None) -> None:
        super().__init__(
            texture="leather.webp",
            base="#2A0A0A",
            tint=(20, 8, 8, 205),
            border="#3A0D0D",
            parent=parent,
        )
        self.i18n = i18n
        self.setObjectName("Sidebar")
        self.setFixedWidth(236)
        self._nav_buttons: dict[str, QPushButton] = {}
        self._active_nav = "transcripts"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(6)

        for key, label_key in NAV_ITEMS:
            button = QPushButton()
            button.setProperty("variant", "nav")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _=False, k=key: self._on_nav(k))
            self._nav_buttons[key] = button
            layout.addWidget(button)

        layout.addSpacing(10)
        line = Divider(height=18)
        layout.addWidget(line)
        layout.addSpacing(6)

        self.library_heading = QLabel()
        self.library_heading.setObjectName("SidebarHeading")
        layout.addWidget(self.library_heading)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.viewport().setAutoFillBackground(False)
        self._list_host = QWidget()
        self._list_host.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._list_layout = QVBoxLayout(self._list_host)
        self._list_layout.setContentsMargins(0, 4, 0, 4)
        self._list_layout.setSpacing(2)
        self._list_layout.addStretch(1)
        self.scroll.setWidget(self._list_host)
        layout.addWidget(self.scroll, 1)

        self.foot = QLabel()
        self.foot.setObjectName("SidebarFoot")
        layout.addWidget(self.foot)

        self._set_nav_active("transcripts")
        self.retranslate()

    def _on_nav(self, key: str) -> None:
        self._set_nav_active(key)
        self.nav_changed.emit(key)

    def _set_nav_active(self, key: str) -> None:
        self._active_nav = key
        for nav_key, button in self._nav_buttons.items():
            button.setProperty("active", "true" if nav_key == key else "false")
            _repolish(button)

    def retranslate(self) -> None:
        for key, label_key in NAV_ITEMS:
            self._nav_buttons[key].setText(self.i18n.t(label_key))
        self.library_heading.setText(self.i18n.t("library").upper())
        self.foot.setText("v0.1.0")

    def refresh_jobs(self, jobs, active_id: int | None) -> None:
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for job in jobs:
            card = JobCard(job, int(job["id"]) == active_id, self.i18n)
            card.clicked.connect(self.job_selected)
            self._list_layout.insertWidget(self._list_layout.count() - 1, card)

        if not jobs:
            empty = QLabel(self.i18n.t("no_transcript"))
            empty.setObjectName("JobMeta")
            self._list_layout.insertWidget(0, empty)
