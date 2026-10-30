from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
    menu_requested = Signal(int, QPoint)

    def __init__(self, job, active: bool, i18n: I18n, parent=None) -> None:
        super().__init__(parent)
        self.job_id = int(job["id"])
        self.setObjectName("JobCard")
        self.setProperty("active", "true" if active else "false")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 8, 8)
        layout.setSpacing(3)

        align = (
            Qt.AlignmentFlag.AlignRight
            if i18n.rtl
            else Qt.AlignmentFlag.AlignLeft
        ) | Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignVCenter

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(4)
        title = QLabel(job["title"])
        title.setObjectName("JobTitle")
        title.setAlignment(align)
        title.setWordWrap(True)
        title.setToolTip(job["title"])
        top.addWidget(title, 1)

        self.menu = QPushButton("⋯")
        self.menu.setObjectName("JobMenu")
        self.menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu.setToolTip(i18n.t("job_actions"))
        self.menu.clicked.connect(self._show_menu)
        top.addWidget(self.menu, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(top)

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
        layout.addWidget(meta)

    def _show_menu(self) -> None:
        self.menu_requested.emit(
            self.job_id, self.menu.mapToGlobal(self.menu.rect().bottomLeft())
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.job_id)
        super().mousePressEvent(event)


class Sidebar(TextureFrame):
    job_selected = Signal(int)
    nav_changed = Signal(str)
    new_job = Signal()
    job_menu = Signal(int, QPoint)

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
        self.setFixedWidth(252)
        self._nav_buttons: dict[str, QPushButton] = {}
        self._active_nav = "transcripts"
        self._jobs: list = []
        self._active_id: int | None = None

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
        layout.addWidget(Divider(height=18))
        layout.addSpacing(6)

        self.library_heading = QLabel()
        self.library_heading.setObjectName("SidebarHeading")
        layout.addWidget(self.library_heading)

        self.search = QLineEdit()
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._render_jobs)
        layout.addWidget(self.search)

        self.sort = QComboBox()
        self.sort.currentIndexChanged.connect(self._render_jobs)
        layout.addWidget(self.sort)
        layout.addSpacing(4)

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

    def set_active_nav(self, key: str) -> None:
        self._set_nav_active(key)

    def retranslate(self) -> None:
        for key, label_key in NAV_ITEMS:
            self._nav_buttons[key].setText(self.i18n.t(label_key))
        self.library_heading.setText(self.i18n.t("library").upper())
        self.search.setPlaceholderText(self.i18n.t("search_transcripts"))
        sort_data = self.sort.currentData() or "newest"
        self.sort.blockSignals(True)
        self.sort.clear()
        self.sort.addItem(self.i18n.t("sort_newest"), "newest")
        self.sort.addItem(self.i18n.t("sort_oldest"), "oldest")
        self.sort.addItem(self.i18n.t("sort_title"), "title")
        self.sort.addItem(self.i18n.t("sort_duration"), "duration")
        index = self.sort.findData(sort_data)
        self.sort.setCurrentIndex(max(0, index))
        self.sort.blockSignals(False)
        self.foot.setText("v0.1.0")
        self._render_jobs()

    def refresh_jobs(self, jobs, active_id: int | None) -> None:
        self._jobs = list(jobs)
        self._active_id = active_id
        self._render_jobs()

    def _render_jobs(self) -> None:
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        query = self.search.text().strip().casefold()
        jobs = [
            job for job in self._jobs if not query or query in job["title"].casefold()
        ]
        sort_mode = self.sort.currentData() or "newest"
        if sort_mode == "oldest":
            jobs.sort(key=lambda job: job["created_at"] or "")
        elif sort_mode == "title":
            jobs.sort(key=lambda job: job["title"].casefold())
        elif sort_mode == "duration":
            jobs.sort(key=lambda job: int(job["duration_ms"] or 0), reverse=True)
        else:
            jobs.sort(key=lambda job: job["created_at"] or "", reverse=True)

        for job in jobs:
            card = JobCard(job, int(job["id"]) == self._active_id, self.i18n)
            card.clicked.connect(self.job_selected)
            card.menu_requested.connect(self.job_menu)
            self._list_layout.insertWidget(self._list_layout.count() - 1, card)

        if not jobs:
            empty = QLabel(
                self.i18n.t("no_matches") if self._jobs else self.i18n.t("no_transcript")
            )
            empty.setObjectName("JobMeta")
            empty.setWordWrap(True)
            self._list_layout.insertWidget(0, empty)
