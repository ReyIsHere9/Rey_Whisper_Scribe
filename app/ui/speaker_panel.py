from __future__ import annotations

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.normalize_fa import has_persian
from app.ui.i18n import I18n
from app.ui.widgets import Avatar, Divider, format_clock


def _initials(name: str) -> str:
    parts = [part for part in re.split(r"\s+", (name or "").strip()) if part]
    if not parts:
        return "?"
    if has_persian(name):
        return parts[0][0]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return name[:2].upper()


class SpeakerRow(QFrame):
    toggled = Signal()
    rename_requested = Signal(int)

    def __init__(self, speaker, stats: dict, i18n: I18n, merge_mode: bool, parent=None) -> None:
        super().__init__(parent)
        self.i18n = i18n
        self.speaker_id = int(speaker["id"])
        self.setObjectName("SpeakerRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.setSpacing(10)

        name = speaker["name"]
        avatar = Avatar(_initials(name), speaker["color"] or "#9B2226", 32)
        layout.addWidget(avatar)

        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        align = (
            Qt.AlignmentFlag.AlignRight
            if i18n.rtl
            else Qt.AlignmentFlag.AlignLeft
        ) | Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignVCenter
        name_label = QLabel(name)
        name_label.setObjectName("SegName")
        name_label.setAlignment(align)
        meta = QLabel(
            f"{stats.get('turns', 0)} {i18n.t('turns')} · {format_clock(stats.get('ms', 0))}"
        )
        meta.setObjectName("SpeakMeta")
        meta.setAlignment(align)
        text_box.addWidget(name_label)
        text_box.addWidget(meta)
        layout.addLayout(text_box, 1)

        self.check = QCheckBox()
        self.check.setVisible(merge_mode)
        self.check.toggled.connect(self._on_check)
        layout.addWidget(self.check, 0, Qt.AlignmentFlag.AlignRight)

        self._merge_mode = merge_mode
        if merge_mode:
            self._apply_selected(False)

    def _on_check(self, checked: bool) -> None:
        self._apply_selected(checked)
        self.toggled.emit()

    def _apply_selected(self, selected: bool) -> None:
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def is_checked(self) -> bool:
        return self.check.isChecked()

    def set_merge_mode(self, enabled: bool) -> None:
        self._merge_mode = enabled
        self.check.setVisible(enabled)
        if not enabled:
            self.check.setChecked(False)

    def mousePressEvent(self, event) -> None:
        if self._merge_mode and event.button() == Qt.MouseButton.LeftButton:
            self.check.setChecked(not self.check.isChecked())
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if not self._merge_mode and event.button() == Qt.MouseButton.LeftButton:
            self.rename_requested.emit(self.speaker_id)
        super().mouseDoubleClickEvent(event)


class SpeakerPanel(QFrame):
    merge_requested = Signal(list)
    add_speaker_requested = Signal()
    enroll_requested = Signal()
    scope_changed = Signal(str)
    renamed = Signal()

    def __init__(self, i18n: I18n, parent=None) -> None:
        super().__init__(parent)
        self.i18n = i18n
        self.setObjectName("Panel")
        self.setFixedWidth(334)
        self._db = None
        self._job_id: int | None = None
        self._rows: list[SpeakerRow] = []
        self._merge_mode = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 14)
        outer.setSpacing(9)

        head = QHBoxLayout()
        self.title = QLabel()
        self.title.setObjectName("SectionTitle")
        self.count_chip = QLabel()
        self.count_chip.setObjectName("Chip")
        head.addWidget(self.title)
        head.addStretch(1)
        head.addWidget(self.count_chip)
        outer.addLayout(head)

        self.scope_label = QLabel()
        self.scope_label.setObjectName("Eyebrow")
        outer.addWidget(self.scope_label)

        self.scope_combo = QComboBox()
        self.scope_combo.currentIndexChanged.connect(self._on_scope_changed)
        outer.addWidget(self.scope_combo)

        self.merge_check = QCheckBox()
        self.merge_check.toggled.connect(self.set_merge_mode)
        outer.addWidget(self.merge_check)

        self.merge_hint = QLabel()
        self.merge_hint.setObjectName("Muted")
        self.merge_hint.setWordWrap(True)
        self.merge_hint.setVisible(False)
        outer.addWidget(self.merge_hint)

        outer.addWidget(Divider(height=16))

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.viewport().setAutoFillBackground(False)
        self.host = QWidget()
        self.host.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.rows_layout = QVBoxLayout(self.host)
        self.rows_layout.setContentsMargins(0, 2, 0, 2)
        self.rows_layout.setSpacing(2)
        self.rows_layout.addStretch(1)
        self.scroll.setWidget(self.host)
        outer.addWidget(self.scroll, 1)

        self.btn_merge = QPushButton()
        self.btn_merge.setObjectName("Primary")
        self.btn_merge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_merge.setVisible(False)
        self.btn_merge.setEnabled(False)
        self.btn_merge.clicked.connect(self._merge_selected)
        outer.addWidget(self.btn_merge)

        actions = QHBoxLayout()
        actions.setSpacing(6)
        self.btn_enroll = QPushButton()
        self.btn_enroll.setObjectName("Ghost")
        self.btn_enroll.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_enroll.clicked.connect(self.enroll_requested)
        self.btn_add = QPushButton()
        self.btn_add.setObjectName("Ghost")
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.clicked.connect(self.add_speaker_requested)
        actions.addWidget(self.btn_enroll)
        actions.addWidget(self.btn_add)
        outer.addLayout(actions)

        self.retranslate()

    def retranslate(self) -> None:
        self.title.setText(self.i18n.t("speakers"))
        self.scope_label.setText(self.i18n.t("scope").upper())
        self.merge_check.setText(self.i18n.t("merge_mode"))
        self.merge_hint.setText(self.i18n.t("merge_hint"))
        self.btn_merge.setText(self.i18n.t("merge_selected"))
        self.btn_enroll.setText(self.i18n.t("enroll_voice"))
        self.btn_add.setText(self.i18n.t("add_speaker"))

        self.scope_combo.blockSignals(True)
        current = self.scope_combo.currentIndex()
        self.scope_combo.clear()
        self.scope_combo.addItem(self.i18n.t("scope_global"))
        self.scope_combo.addItem(self.i18n.t("scope_job"))
        self.scope_combo.setCurrentIndex(max(0, current))
        self.scope_combo.blockSignals(False)

    def set_job(self, job_id: int | None, db) -> None:
        self._job_id = job_id
        self._db = db
        self.refresh()

    def _include_global(self) -> bool:
        return self.scope_combo.currentIndex() == 0

    def _on_scope_changed(self, _index: int) -> None:
        self.scope_changed.emit("global" if self._include_global() else "job")
        self.refresh()

    def _clear_rows(self) -> None:
        while self.rows_layout.count() > 1:
            item = self.rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._rows.clear()

    def clear(self) -> None:
        self._job_id = None
        self._clear_rows()
        self.count_chip.setText("0")

    def refresh(self) -> None:
        if self._db is None or self._job_id is None:
            return
        speakers = self._db.speakers(self._job_id, include_global=self._include_global())
        stats = self._db.speaker_stats(self._job_id)
        self._clear_rows()

        for speaker in speakers:
            row = SpeakerRow(
                speaker,
                stats.get(int(speaker["id"]), {}),
                self.i18n,
                self._merge_mode,
            )
            row.toggled.connect(self._update_merge_button)
            row.rename_requested.connect(self._rename_speaker)
            self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)
            self._rows.append(row)

        self.count_chip.setText(str(len(speakers)))
        self._update_merge_button()

    def set_merge_mode(self, enabled: bool) -> None:
        self._merge_mode = enabled
        for row in self._rows:
            row.set_merge_mode(enabled)
        self.btn_merge.setVisible(enabled)
        self.merge_hint.setVisible(enabled)
        self._update_merge_button()

    def _selected_ids(self) -> list[int]:
        return [row.speaker_id for row in self._rows if row.is_checked()]

    def _update_merge_button(self) -> None:
        self.btn_merge.setEnabled(len(self._selected_ids()) >= 2)

    def _merge_selected(self) -> None:
        ids = self._selected_ids()
        if len(ids) >= 2:
            self.merge_requested.emit(ids)

    def _rename_speaker(self, speaker_id: int) -> None:
        if self._db is None:
            return
        row = self._db.conn.execute(
            "SELECT name FROM speakers WHERE id = ?", (speaker_id,)
        ).fetchone()
        if row is None:
            return
        name, accepted = QInputDialog.getText(
            self,
            self.i18n.t("rename_speaker"),
            self.i18n.t("speaker_name"),
            text=row["name"],
        )
        name = name.strip()
        if not accepted or not name or name == row["name"]:
            return
        self._db.rename_speaker(speaker_id, name)
        self.refresh()
        self.renamed.emit()
