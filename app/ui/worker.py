from __future__ import annotations

import threading
import time

from PySide6.QtCore import QThread, Signal

from app.core.models import JobCancelled, JobConfig
from app.core.pipeline import run_job
from app.db import Database


class PipelineWorker(QThread):
    progress = Signal(float, str, int)
    finished_job = Signal(int, int)
    failed = Signal(int, str)
    cancelled = Signal(int)

    def __init__(self, job_id: int, config: JobConfig, parent=None) -> None:
        super().__init__(parent)
        self.job_id = job_id
        self.config = config
        self._stop = threading.Event()
        self._last_emit = 0.0
        self._last_key = ""

    def cancel(self) -> None:
        self._stop.set()

    def _emit_progress(self, ratio: float, key: str, count: int) -> None:
        now = time.monotonic()
        if ratio >= 1.0 or key != self._last_key or now - self._last_emit >= 0.25:
            self._last_emit = now
            self._last_key = key
            self.progress.emit(ratio, key, count)

    def run(self) -> None:
        db = Database()
        try:
            segments = run_job(
                db,
                self.job_id,
                self.config,
                progress=self._emit_progress,
                should_stop=self._stop.is_set,
            )
            self.finished_job.emit(self.job_id, len(segments))
        except JobCancelled:
            db.set_job_status(self.job_id, "cancelled")
            self.cancelled.emit(self.job_id)
        except Exception as error:  # noqa: BLE001 - report to the UI
            db.set_job_status(self.job_id, "failed")
            self.failed.emit(self.job_id, str(error))
        finally:
            db.close()
