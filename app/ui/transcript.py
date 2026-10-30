from __future__ import annotations

import bisect
import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.normalize_fa import has_persian
from app.ui.i18n import I18n
from app.ui.widgets import Avatar, Divider, format_clock, format_ms


def _initials(name: str) -> str:
    parts = [part for part in re.split(r"\s+", (name or "").strip()) if part]
    if not parts:
        return "?"
    if has_persian(name):
        return parts[0][0]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return name[:2].upper()


def _repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class SegmentCard(QFrame):
    seeked = Signal(int)
    text_edited = Signal(int, str)
    selection_toggled = Signal(int, bool)

    def __init__(self, segment, i18n: I18n, parent=None) -> None:
        super().__init__(parent)
        self.i18n = i18n
        self.segment_id = int(segment["id"])
        self.start_ms = int(segment["start_ms"])
        self._text = segment["text"] or ""
        self._edit_mode = False
        self._select_mode = False
        self._selected = False
        self._active = False

        self.setObjectName("SegmentCard")
        self.setProperty("active", "false")
        self.setProperty("selected", "false")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        self.check = QCheckBox()
        self.check.setVisible(False)
        self.check.toggled.connect(self._on_check_toggled)
        layout.addWidget(self.check, 0, Qt.AlignmentFlag.AlignTop)

        name = segment["speaker_name"] or "Speaker"
        color = segment["speaker_color"] or "#9B2226"
        avatar = Avatar(_initials(name), color, 36)
        layout.addWidget(avatar, 0, Qt.AlignmentFlag.AlignTop)

        body = QVBoxLayout()
        body.setSpacing(4)
        head = QHBoxLayout()
        head.setSpacing(8)
        self.name_label = QLabel(name)
        self.name_label.setObjectName("SegName")
        self.time_label = QLabel(
            f"{format_ms(self.start_ms)} — {format_ms(int(segment['end_ms']))}"
        )
        self.time_label.setObjectName("SegTime")
        head.addWidget(self.name_label)
        head.addWidget(self.time_label)
        head.addStretch(1)
        body.addLayout(head)

        self.text_label = QLabel(self._text)
        self.text_label.setObjectName("SegText")
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        _apply_direction(self.text_label, self._text)
        body.addWidget(self.text_label)

        self.editor = QLineEdit(self._text)
        self.editor.setVisible(False)
        self.editor.editingFinished.connect(self._commit_edit)
        body.addWidget(self.editor)

        layout.addLayout(body, 1)

    def _set_active(self, active: bool) -> None:
        if self._active == active:
            return
        self._active = active
        self.setProperty("active", "true" if active else "false")
        _repolish(self)

    def _on_check_toggled(self, checked: bool) -> None:
        if self._selected == checked:
            return
        self._selected = checked
        self.setProperty("selected", "true" if checked else "false")
        _repolish(self)
        self.selection_toggled.emit(self.segment_id, checked)

    def set_selected(self, selected: bool) -> None:
        self.check.blockSignals(True)
        self.check.setChecked(selected)
        self.check.blockSignals(False)
        if self._selected == selected:
            return
        self._selected = selected
        self.setProperty("selected", "true" if selected else "false")
        _repolish(self)

    def set_select_mode(self, enabled: bool) -> None:
        self._select_mode = enabled
        self.check.setVisible(enabled)
        self.text_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, enabled
        )
        if not enabled:
            self.set_selected(False)

    def set_edit_mode(self, enabled: bool) -> None:
        self._edit_mode = enabled
        if not enabled:
            self._stop_edit()
        self.setCursor(
            Qt.CursorShape.IBeamCursor if enabled else Qt.CursorShape.PointingHandCursor
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self.editor.isVisible():
            if self._select_mode:
                if not self.check.geometry().contains(event.position().toPoint()):
                    self.check.toggle()
                event.accept()
                return
            self.seeked.emit(self.start_ms)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if self._select_mode:
            return
        if self._edit_mode and event.button() == Qt.MouseButton.LeftButton:
            self._start_edit()

    def _start_edit(self) -> None:
        self.text_label.setVisible(False)
        self.editor.setText(self._text)
        self.editor.setVisible(True)
        self.editor.setFocus()
        self.editor.selectAll()

    def _stop_edit(self) -> None:
        self.editor.setVisible(False)
        self.text_label.setVisible(True)

    def _commit_edit(self) -> None:
        if not self.editor.isVisible():
            return
        value = self.editor.text().strip()
        if value and value != self._text:
            self._text = value
            self.text_label.setText(value)
            _apply_direction(self.text_label, value)
            self.text_edited.emit(self.segment_id, value)
        self._stop_edit()


def _apply_direction(label: QLabel, text: str) -> None:
    if has_persian(text):
        label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
    else:
        label.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)


class TranscriptView(QFrame):
    export_requested = Signal()
    seeked = Signal(int)
    text_edited = Signal(int, str)
    assign_requested = Signal(list)

    def __init__(self, i18n: I18n, parent=None) -> None:
        super().__init__(parent)
        self.i18n = i18n
        self.setObjectName("Panel")
        self._cards: list[SegmentCard] = []
        self._edit_mode = False
        self._select_mode = False
        self._selected_ids: set[int] = set()
        self._job = None
        self._segments = []
        self._starts: list[int] = []
        self._active_index = -1
        self._message_label: QLabel | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 12)
        outer.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(12)
        titles = QVBoxLayout()
        titles.setSpacing(3)
        self.eyebrow = QLabel()
        self.eyebrow.setObjectName("Eyebrow")
        self.title = QLabel()
        self.title.setObjectName("Heading")
        self.meta_row = QHBoxLayout()
        self.meta_row.setSpacing(6)
        titles.addWidget(self.eyebrow)
        titles.addWidget(self.title)
        titles.addLayout(self.meta_row)
        top.addLayout(titles, 1)

        self.btn_edit = QPushButton()
        self.btn_edit.setObjectName("Ghost")
        self.btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit.clicked.connect(self._toggle_edit)
        top.addWidget(self.btn_edit, 0, Qt.AlignmentFlag.AlignBottom)

        self.btn_select = QPushButton()
        self.btn_select.setObjectName("Ghost")
        self.btn_select.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select.setVisible(False)
        self.btn_select.clicked.connect(self._toggle_select)
        top.addWidget(self.btn_select, 0, Qt.AlignmentFlag.AlignBottom)

        self.btn_assign = QPushButton()
        self.btn_assign.setObjectName("Primary")
        self.btn_assign.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_assign.setVisible(False)
        self.btn_assign.setEnabled(False)
        self.btn_assign.clicked.connect(self._request_assign)
        top.addWidget(self.btn_assign, 0, Qt.AlignmentFlag.AlignBottom)

        self.btn_export = QPushButton()
        self.btn_export.setObjectName("Primary")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.clicked.connect(self.export_requested)
        top.addWidget(self.btn_export, 0, Qt.AlignmentFlag.AlignBottom)
        outer.addLayout(top)

        outer.addWidget(Divider(height=20))

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.viewport().setAutoFillBackground(False)
        self.host = QWidget()
        self.host.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.list_layout = QVBoxLayout(self.host)
        self.list_layout.setContentsMargins(2, 4, 2, 14)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch(1)
        self.scroll.setWidget(self.host)
        outer.addWidget(self.scroll, 1)

        self.retranslate()

    def retranslate(self) -> None:
        self.eyebrow.setText(self.i18n.t("transcript").upper())
        align = (
            Qt.AlignmentFlag.AlignRight
            if self.i18n.rtl
            else Qt.AlignmentFlag.AlignLeft
        )
        self.eyebrow.setAlignment(align | Qt.AlignmentFlag.AlignAbsolute)
        self.title.setAlignment(
            align | Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignVCenter
        )
        self.btn_edit.setText(
            self.i18n.t("done") if self._edit_mode else self.i18n.t("edit")
        )
        self.btn_select.setText(
            self.i18n.t("done") if self._select_mode else self.i18n.t("select")
        )
        self.btn_select.setToolTip(self.i18n.t("select_hint"))
        self.btn_export.setText(self.i18n.t("export"))
        self._update_select_texts()
        if self._job is not None:
            self.load(self._job, self._segments)

    def _toggle_edit(self) -> None:
        if not self._edit_mode and self._select_mode:
            self._set_select_mode(False)
        self._edit_mode = not self._edit_mode
        for card in self._cards:
            card.set_edit_mode(self._edit_mode)
        self.retranslate()

    def _toggle_select(self) -> None:
        if not self._segments or self._message_label is not None:
            return
        if not self._select_mode and self._edit_mode:
            self._edit_mode = False
            for card in self._cards:
                card.set_edit_mode(False)
            self.btn_edit.setText(self.i18n.t("edit"))
        self._set_select_mode(not self._select_mode)

    def _set_select_mode(self, enabled: bool) -> None:
        self._select_mode = enabled
        self._selected_ids.clear()
        for card in self._cards:
            card.set_select_mode(enabled)
            card.set_selected(False)
        self.btn_assign.setVisible(enabled)
        self._update_select_texts()

    def _update_select_texts(self) -> None:
        self.btn_select.setText(
            self.i18n.t("done") if self._select_mode else self.i18n.t("select")
        )
        count = len(self._selected_ids)
        if count:
            self.btn_assign.setText(self.i18n.t("assign_count").format(count=count))
        else:
            self.btn_assign.setText(self.i18n.t("assign_to_speaker"))
        self.btn_assign.setEnabled(count > 0)

    def _on_selection_toggled(self, segment_id: int, selected: bool) -> None:
        if selected:
            self._selected_ids.add(segment_id)
        else:
            self._selected_ids.discard(segment_id)
        self._update_select_texts()

    def _request_assign(self) -> None:
        if self._selected_ids:
            self.assign_requested.emit(sorted(self._selected_ids))

    def _clear(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.list_layout.addStretch(1)
        self._cards.clear()
        self._starts.clear()
        self._active_index = -1
        self._message_label = None
        self._select_mode = False
        self._selected_ids.clear()
        self.btn_assign.setVisible(False)

    def show_message(self, text: str) -> None:
        self._clear()
        self.btn_select.setVisible(False)
        self._message_label = QLabel(text)
        self._message_label.setObjectName("Muted")
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message_label.setWordWrap(True)
        self.list_layout.insertStretch(0, 1)
        self.list_layout.insertWidget(1, self._message_label)

    def update_message(self, text: str) -> None:
        if self._message_label is not None:
            self._message_label.setText(text)

    def load(self, job, segments) -> None:
        self._job = job
        self._segments = segments
        self._clear()
        self._select_mode = False
        self._selected_ids.clear()
        self.btn_select.setVisible(bool(segments))
        self.btn_assign.setVisible(False)
        self._starts = [int(segment["start_ms"]) for segment in segments]
        self.title.setText(job["title"])

        while self.meta_row.count():
            item = self.meta_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        created = (job["created_at"] or "")[:10]
        chips = [
            created,
            format_clock(job["duration_ms"]),
            f"{len(segments)} {self.i18n.t('segments')}",
        ]
        for text in chips:
            if not text:
                continue
            label = QLabel(text)
            label.setObjectName("MetaChip")
            self.meta_row.addWidget(label)
        self.meta_row.addStretch(1)

        if not segments:
            self.btn_select.setVisible(False)
            self.list_layout.insertStretch(0, 1)
            empty = QLabel(self.i18n.t("no_transcript"))
            empty.setObjectName("Muted")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setWordWrap(True)
            self.list_layout.insertWidget(1, empty)
            return

        for segment in segments:
            card = SegmentCard(segment, self.i18n)
            card.seeked.connect(self.seeked)
            card.text_edited.connect(self.text_edited)
            card.selection_toggled.connect(self._on_selection_toggled)
            card.set_edit_mode(self._edit_mode)
            card.set_select_mode(False)
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)
            self._cards.append(card)
        self._update_select_texts()

    def set_active_ms(self, position_ms: int) -> None:
        if not self._starts:
            return
        index = bisect.bisect_right(self._starts, position_ms) - 1
        if index < 0:
            index = -1
        if index == self._active_index:
            return
        if 0 <= self._active_index < len(self._cards):
            self._cards[self._active_index]._set_active(False)
        if 0 <= index < len(self._cards):
            self._cards[index]._set_active(True)
        self._active_index = index
