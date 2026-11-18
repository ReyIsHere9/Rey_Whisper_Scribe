from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.i18n import I18n
from app.ui.widgets import format_clock


class SpellingReviewDialog(QDialog):
    def __init__(self, i18n: I18n, db, job_id: int, parent=None) -> None:
        super().__init__(parent)
        self.i18n = i18n
        self.db = db
        self.job_id = job_id
        self._choices: list[tuple[int, QComboBox]] = []
        rows = db.spell_suggestions(job_id)

        self.setWindowTitle(i18n.t("spelling_review_title"))
        self.setModal(True)
        self.resize(860, 640)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(12)

        heading = QLabel(i18n.t("spelling_review_title"))
        heading.setObjectName("Heading")
        layout.addWidget(heading)

        hint = QLabel(i18n.t("spelling_review_hint"))
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host = QWidget()
        host_layout = QVBoxLayout(host)
        host_layout.setContentsMargins(0, 0, 6, 0)
        host_layout.setSpacing(8)

        for row in rows:
            host_layout.addWidget(self._build_row(row))
        host_layout.addStretch(1)
        scroll.setWidget(host)
        layout.addWidget(scroll, 1)

        if not rows:
            hint.setText(i18n.t("no_suggestions"))

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton(i18n.t("cancel"))
        cancel.setObjectName("Ghost")
        cancel.clicked.connect(self.reject)
        apply_button = QPushButton(i18n.t("apply_selected"))
        apply_button.setObjectName("Primary")
        apply_button.setEnabled(bool(rows))
        apply_button.clicked.connect(self._apply)
        buttons.addWidget(cancel)
        buttons.addWidget(apply_button)
        layout.addLayout(buttons)

    def _build_row(self, row) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Panel")
        row_layout = QHBoxLayout(frame)
        row_layout.setContentsMargins(14, 10, 14, 10)
        row_layout.setSpacing(14)

        info = QVBoxLayout()
        info.setSpacing(3)
        original = QLabel(f"{format_clock(row['start_ms'])}  {row['original']}")
        original.setObjectName("SectionTitle")
        info.addWidget(original)
        context = row["segment_text"] or ""
        if len(context) > 180:
            context = context[:180] + "…"
        context_label = QLabel(context)
        context_label.setObjectName("Muted")
        context_label.setWordWrap(True)
        info.addWidget(context_label)
        row_layout.addLayout(info, 1)

        combo = QComboBox()
        combo.setMinimumWidth(220)
        combo.addItem(self.i18n.t("keep_original"), None)
        try:
            alternatives = json.loads(row["alternatives"] or "[]")
        except (TypeError, ValueError):
            alternatives = []
        for alternative in alternatives:
            if alternative and alternative != row["original"]:
                combo.addItem(alternative, alternative)
        row_layout.addWidget(combo, 0, Qt.AlignmentFlag.AlignVCenter)
        self._choices.append((int(row["id"]), combo))
        return frame

    def _apply(self) -> None:
        choices = {
            edit_id: str(combo.currentData())
            for edit_id, combo in self._choices
            if combo.currentData()
        }
        self.db.apply_spell_suggestions(self.job_id, choices)
        self.accept()
