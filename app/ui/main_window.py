from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.core.export import default_path, export_transcript
from app.core.models import JobConfig
from app.core.transcribe import engine_available
from app.db import Database
from app.paths import ASSETS_DIR
from app.theme.qss import build_qss
from app.theme.tokens import palette_for
from app.ui.header import Header
from app.ui.i18n import I18n
from app.ui.job_dialog import JobDialog
from app.ui.player import PlayerBar
from app.ui.sidebar import Sidebar
from app.ui.speaker_panel import SpeakerPanel
from app.ui.transcript import TranscriptView
from app.ui.widgets import Divider, Ornament, TextureFrame, format_clock
from app.ui.worker import PipelineWorker


class EmptyState(QFrame):
    choose = Signal()

    def __init__(self, i18n: I18n, parent=None) -> None:
        super().__init__(parent)
        self.i18n = i18n
        self.setObjectName("DropZone")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(12)
        layout.addStretch(1)

        self.ornament = Ornament("quill.png", height=168, opacity=0.92)
        layout.addWidget(self.ornament)

        self.title = QLabel()
        self.title.setObjectName("EmptyTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title)

        self.divider = Divider(height=24)
        layout.addWidget(self.divider)

        self.hint = QLabel()
        self.hint.setObjectName("Muted")
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        self.choose_button = QPushButton()
        self.choose_button.setObjectName("Primary")
        self.choose_button.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.choose_button, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)

        self.retranslate()

    def retranslate(self) -> None:
        self.title.setText(self.i18n.t("drop_hint"))
        self.hint.setText(self.i18n.t("drop_supported"))
        self.choose_button.setText(self.i18n.t("choose_file"))


class MainWindow(QMainWindow):
    def __init__(self, theme: str | None = None, lang: str | None = None) -> None:
        super().__init__()
        self.db = Database()
        self.db.seed_demo()
        self.i18n = I18n(lang or self.db.setting("language", "en"))
        self.theme = theme or self.db.setting("theme", "light")
        self.palette = palette_for(self.theme)
        self.current_job_id: int | None = None
        self._worker: PipelineWorker | None = None
        self._busy = False
        self._job_started = 0.0
        self._stage_key = "stage_loading"
        self._stage_count = 0
        self._progress_ratio = 0.0
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._refresh_status_line)

        self.setWindowTitle("Whisper Scribe")
        self.setMinimumSize(1180, 760)
        self.resize(1400, 900)
        self.setAcceptDrops(True)
        icon_path = ASSETS_DIR / "app.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._build()
        self._apply_theme()
        self._apply_language()
        self._select_initial_job()
        self.i18n.changed.connect(self._apply_language)

        self._enable_dark_title_bar()

    def _build(self) -> None:
        self.root = TextureFrame(texture="", base=self.palette.bg)
        self.root.setObjectName("Root")
        self.setCentralWidget(self.root)

        column = QVBoxLayout(self.root)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)

        self.header = Header(self.i18n, self.theme)
        column.addWidget(self.header)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.sidebar = Sidebar(self.i18n)
        body_layout.addWidget(self.sidebar)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(18, 18, 18, 10)
        center_layout.setSpacing(0)
        self.transcript = TranscriptView(self.i18n)
        self.empty = EmptyState(self.i18n)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.transcript)
        self.stack.addWidget(self.empty)
        center_layout.addWidget(self.stack)
        body_layout.addWidget(center, 1)

        speaker_wrap = QWidget()
        speaker_layout = QHBoxLayout(speaker_wrap)
        speaker_layout.setContentsMargins(0, 18, 20, 10)
        speaker_layout.setSpacing(0)
        self.speakers = SpeakerPanel(self.i18n)
        speaker_layout.addWidget(self.speakers)
        body_layout.addWidget(speaker_wrap)

        column.addWidget(body, 1)

        self.player = PlayerBar(self.i18n)
        column.addWidget(self.player)

        status = QStatusBar()
        status.setSizeGripEnabled(False)
        status.setFixedHeight(36)
        self.setStatusBar(status)
        self.status_model = QLabel()
        self.status_model.setObjectName("StatusChip")
        self.status_engine = QLabel()
        self.status_engine.setObjectName("StatusChip")
        self.status_counts = QLabel()
        self.status_counts.setObjectName("Muted")

        self.progress_label = QLabel()
        self.progress_label.setObjectName("Muted")
        self.progress_label.setVisible(False)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedSize(170, 8)
        self.progress_bar.setVisible(False)
        self.cancel_btn = QPushButton()
        self.cancel_btn.setObjectName("CancelButton")
        self.cancel_btn.setFixedHeight(24)
        self.cancel_btn.setMinimumWidth(74)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._cancel_job)

        status.addWidget(self.status_model)
        status.addWidget(self.status_engine)
        status.addWidget(self.progress_label)
        status.addWidget(self.progress_bar)
        status.addWidget(self.cancel_btn)
        status.addPermanentWidget(self.status_counts)

        self.header.new_job.connect(self._new_job)
        self.header.theme_toggled.connect(self._toggle_theme)
        self.header.language_toggled.connect(self._toggle_language)
        self.sidebar.job_selected.connect(self._select_job)
        self.sidebar.nav_changed.connect(self._on_nav)
        self.speakers.merge_requested.connect(self._merge_speakers)
        self.speakers.add_speaker_requested.connect(self._add_speaker)
        self.speakers.enroll_requested.connect(self._enroll_voice)
        self.speakers.renamed.connect(self._on_speaker_renamed)
        self.transcript.seeked.connect(self.player.seek_ms)
        self.transcript.text_edited.connect(self._on_text_edited)
        self.transcript.export_requested.connect(self._export)
        self.transcript.assign_requested.connect(self._assign_segments)
        self.player.position_changed.connect(self.transcript.set_active_ms)
        self.empty.choose_button.clicked.connect(self._new_job)

    def _apply_theme(self) -> None:
        self.palette = palette_for(self.theme)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_qss(self.palette, self.i18n.rtl))
        self.root.configure(
            texture=self.palette.bg_tex,
            base=self.palette.bg,
            tint=self.palette.overlay,
        )
        self.header.set_theme(self.theme)
        self.player.set_palette(self.palette)
        self._enable_dark_title_bar()
        self.db.set_setting("theme", self.theme)

    def _apply_language(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.setLayoutDirection(
                Qt.LayoutDirection.RightToLeft
                if self.i18n.rtl
                else Qt.LayoutDirection.LeftToRight
            )
            app.setStyleSheet(build_qss(self.palette, self.i18n.rtl))
        self.header.retranslate()
        self.sidebar.retranslate()
        self.sidebar.refresh_jobs(self.db.jobs(), self.current_job_id)
        self.transcript.retranslate()
        self.speakers.retranslate()
        self.speakers.refresh()
        self.empty.retranslate()
        self.status_model.setText(self.i18n.t("status_model"))
        self._update_counts()
        self._refresh_status_line()
        if self._busy:
            self.transcript.show_message(self._status_text())
        self.db.set_setting("language", self.i18n.lang)

    def _update_counts(self) -> None:
        counts = self.db.counts()
        self.status_engine.setText(
            self.i18n.t("status_ready") if engine_available() else self.i18n.t("status_engine")
        )
        self.status_counts.setText(
            f"{counts['jobs']} {self.i18n.t('jobs')} · "
            f"{counts['speakers']} {self.i18n.t('total_speakers')} · "
            f"{counts['segments']} {self.i18n.t('segments')}"
        )

    def _select_initial_job(self) -> None:
        for job in self.db.jobs():
            if job["status"] in {"queued", "processing"}:
                recovered = "transcribed" if job["segment_count"] else "failed"
                self.db.set_job_status(int(job["id"]), recovered)
        jobs = self.db.jobs()
        if jobs:
            self._select_job(int(jobs[0]["id"]))
        else:
            self.current_job_id = None
            self.stack.setCurrentWidget(self.empty)
            self.speakers.clear()
            self.player.clear()

    def _select_job(self, job_id: int) -> None:
        job = self.db.job(job_id)
        if job is None:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.current_job_id = job_id
            segments = self.db.segments(job_id)
            self.transcript.load(job, segments)
            self.speakers.set_job(job_id, self.db)
            self.player.set_job(job)
            self.sidebar.refresh_jobs(self.db.jobs(), job_id)
            self.stack.setCurrentWidget(self.transcript)
            self._update_counts()
        finally:
            QApplication.restoreOverrideCursor()

    def _toggle_theme(self) -> None:
        self.theme = "dark" if self.theme == "light" else "light"
        self._apply_theme()

    def _toggle_language(self) -> None:
        self.i18n.set_lang("fa" if self.i18n.lang == "en" else "en")

    def _on_nav(self, key: str) -> None:
        if key != "transcripts":
            self.statusBar().showMessage(self.i18n.t("not_implemented"), 3000)

    def _new_job(self, initial_file: str = "") -> None:
        if self._busy:
            QMessageBox.information(
                self, self.i18n.t("new_job"), self.i18n.t("status_processing")
            )
            return
        if not isinstance(initial_file, str):
            initial_file = ""
        dialog = JobDialog(self.i18n, self.db, initial_file, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.job_id:
            self._select_job(dialog.job_id)
            self.statusBar().showMessage(self.i18n.t("job_created"), 3000)
            self._start_job(dialog.job_id)

    def _start_job(self, job_id: int) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        job = self.db.job(job_id)
        if job is None:
            return
        source = Path(job["source_path"] or "")
        if not source.exists():
            self.db.set_job_status(job_id, "failed")
            QMessageBox.critical(
                self, self.i18n.t("job_failed_title"), f"Source file not found:\n{source}"
            )
            return
        if not engine_available():
            self.db.set_job_status(job_id, "failed")
            QMessageBox.information(
                self,
                self.i18n.t("engine_missing"),
                self.i18n.t("engine_missing_hint"),
            )
            self.sidebar.refresh_jobs(self.db.jobs(), job_id)
            return

        config = JobConfig(
            language=job["language"],
            model=job["model"],
            diarize=bool(job["diarize"]),
            expected_speakers=int(job["expected_speakers"] or 0),
            speaker_scope=job["speaker_scope"],
        )
        self._job_started = time.monotonic()
        self._stage_key = "stage_loading"
        self._stage_count = 0
        self._progress_ratio = 0.0
        self.db.set_job_status(job_id, "processing")
        self.sidebar.refresh_jobs(self.db.jobs(), job_id)
        self.transcript.show_message(self.i18n.t("stage_loading"))
        self._set_busy(True)

        worker = PipelineWorker(job_id, config, self)
        worker.progress.connect(self._on_progress)
        worker.finished_job.connect(self._on_job_finished)
        worker.failed.connect(self._on_job_failed)
        worker.cancelled.connect(self._on_job_cancelled)
        worker.finished.connect(self._on_worker_finished)
        self._worker = worker
        worker.start()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.header.btn_new.setEnabled(not busy)
        self.progress_label.setVisible(busy)
        self.progress_bar.setVisible(busy)
        self.cancel_btn.setVisible(busy)
        self.cancel_btn.setEnabled(busy)
        self.cancel_btn.setText(self.i18n.t("cancel"))
        if busy:
            self.statusBar().clearMessage()
            self._elapsed_timer.start()
            self._refresh_status_line()
        else:
            self._elapsed_timer.stop()
            self.statusBar().clearMessage()

    def _on_progress(self, ratio: float, key: str, count: int) -> None:
        self._progress_ratio = ratio
        self._stage_key = key
        self._stage_count = count
        self.progress_bar.setValue(int(ratio * 1000))
        self._refresh_status_line()

    def _status_text(self) -> str:
        elapsed = format_clock(int((time.monotonic() - self._job_started) * 1000))
        text = self.i18n.t(self._stage_key)
        if self._stage_count:
            text = f"{text} · {self._stage_count}"
        return f"{text} · {elapsed}"

    def _refresh_status_line(self) -> None:
        if not self._busy:
            return
        text = self._status_text()
        self.progress_label.setText(text)
        self.transcript.update_message(text)

    def _cancel_job(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self.cancel_btn.setEnabled(False)
            self.cancel_btn.setText(self.i18n.t("cancelling"))
            self._worker.cancel()

    def _on_job_finished(self, job_id: int, count: int) -> None:
        elapsed = format_clock(int((time.monotonic() - self._job_started) * 1000))
        self._set_busy(False)
        self._select_job(job_id)
        self.statusBar().showMessage(
            self.i18n.t("job_done").format(segments=count, time=elapsed), 8000
        )

    def _on_job_failed(self, job_id: int, error: str) -> None:
        self._set_busy(False)
        self.sidebar.refresh_jobs(self.db.jobs(), job_id)
        self.transcript.show_message(self.i18n.t("job_failed_title"))
        self.statusBar().showMessage(self.i18n.t("job_failed_title"), 8000)
        QMessageBox.critical(
            self, self.i18n.t("job_failed_title"), error[:1500] or "Unknown error"
        )

    def _on_job_cancelled(self, job_id: int) -> None:
        self._set_busy(False)
        self._select_job(job_id)
        if not self.db.segments(job_id):
            self.transcript.show_message(self.i18n.t("job_cancelled_title"))
        self.statusBar().showMessage(self.i18n.t("job_cancelled_title"), 8000)

    def _on_worker_finished(self) -> None:
        worker = self.sender()
        if worker is not None:
            worker.deleteLater()
        self._worker = None

    def _assign_segments(self, segment_ids: list[int]) -> None:
        if self.current_job_id is None or not segment_ids:
            return
        speakers = self.db.speakers(self.current_job_id, include_global=True)
        names = [speaker["name"] for speaker in speakers]
        new_label = self.i18n.t("new_speaker")
        choice, accepted = QInputDialog.getItem(
            self,
            self.i18n.t("assign_to_speaker"),
            self.i18n.t("choose_speaker"),
            names + [new_label],
            0,
            False,
        )
        if not accepted or not choice:
            return

        display_name = choice
        if choice == new_label:
            name, accepted = QInputDialog.getText(
                self, self.i18n.t("new_speaker"), self.i18n.t("speaker_name")
            )
            name = name.strip()
            if not accepted or not name:
                return
            is_global = self.speakers.scope_combo.currentIndex() == 0
            speaker_id = self.db.add_speaker(
                None if is_global else self.current_job_id, name, is_global=is_global
            )
            display_name = name
        else:
            speaker_id = int(speakers[names.index(choice)]["id"])

        count = self.db.assign_segments(segment_ids, speaker_id)
        job = self.db.job(self.current_job_id)
        if job is not None:
            self.transcript.load(job, self.db.segments(self.current_job_id))
        self.speakers.refresh()
        self._update_counts()
        self.statusBar().showMessage(
            self.i18n.t("assigned_segments").format(count=count, name=display_name), 6000
        )

    def _on_speaker_renamed(self) -> None:
        if self.current_job_id is None:
            return
        job = self.db.job(self.current_job_id)
        if job is not None:
            self.transcript.load(job, self.db.segments(self.current_job_id))
            self._update_counts()

    def _merge_speakers(self, ids: list[int]) -> None:
        if len(ids) < 2 or self.current_job_id is None:
            return
        target = ids[0]
        for source in ids[1:]:
            self.db.merge_speakers(source, target)
        self._select_job(self.current_job_id)

    def _add_speaker(self) -> None:
        if self.current_job_id is None:
            return
        is_global = self.speakers.scope_combo.currentIndex() == 0
        existing = self.db.speakers(
            self.current_job_id, include_global=True
        )
        self.db.add_speaker(
            None if is_global else self.current_job_id,
            f"Speaker {len(existing) + 1}",
            is_global=is_global,
        )
        self.speakers.refresh()
        self._update_counts()

    def _enroll_voice(self) -> None:
        QMessageBox.information(
            self, self.i18n.t("enroll_voice"), self.i18n.t("not_implemented")
        )

    def _on_text_edited(self, segment_id: int, text: str) -> None:
        self.db.update_segment_text(segment_id, text)
        if self.current_job_id is not None:
            job = self.db.job(self.current_job_id)
            if job is not None:
                self.transcript.load(job, self.db.segments(self.current_job_id))

    def _export(self) -> None:
        if self.current_job_id is None:
            return
        job = self.db.job(self.current_job_id)
        if job is None:
            return
        segments = self.db.segments(self.current_job_id)
        path, _selected = QFileDialog.getSaveFileName(
            self,
            self.i18n.t("export"),
            str(default_path(job)),
            "Text (*.txt);;SubRip (*.srt)",
        )
        if not path:
            return
        if not Path(path).suffix:
            path += ".txt"
        try:
            written = export_transcript(job, segments, path)
        except OSError as error:
            QMessageBox.critical(self, self.i18n.t("export"), str(error))
            return
        self.statusBar().showMessage(str(written), 5000)

    def _enable_dark_title_bar(self) -> None:
        try:
            import ctypes

            value = ctypes.c_int(1 if self.palette.is_dark else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                int(self.winId()), 20, ctypes.byref(value), ctypes.sizeof(value)
            )
        except Exception:  # noqa: BLE001, S110 - non-Windows or API change
            pass

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                self._new_job(path)
                break

    def closeEvent(self, event) -> None:
        if self._worker is not None and self._worker.isRunning():
            reply = QMessageBox.question(
                self,
                self.i18n.t("cancel"),
                self.i18n.t("quit_while_running"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._worker.cancel()
            if not self._worker.wait(10000):
                self._worker.terminate()
                self._worker.wait(2000)
        self.db.close()
        super().closeEvent(event)

