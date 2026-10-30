from __future__ import annotations

import argparse
import os
import sys
import tempfile
import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def _load_fonts() -> None:
    from app.paths import ASSETS_DIR

    font_dir = ASSETS_DIR / "fonts"
    if not font_dir.exists():
        return
    for path in sorted(font_dir.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(path))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="whisper-scribe")
    parser.add_argument("--theme", choices=["light", "dark"], default=None)
    parser.add_argument("--lang", choices=["en", "fa"], default=None)
    parser.add_argument("--screenshot", default="")
    parser.add_argument("--delay", type=int, default=900)
    parser.add_argument("--selftest", default="", metavar="AUDIO")
    parser.add_argument("--selftest-output", default="")
    return parser


def _selftest(audio: str, output: str) -> int:
    lines: list[str] = []
    try:
        with tempfile.TemporaryDirectory(prefix="whisper-scribe-selftest-") as temp:
            os.environ["WHISPERSCRIBE_DATA"] = temp
            from app.core.models import JobConfig
            from app.core.pipeline import run_job
            from app.db import Database

            db = Database()
            job_id = db.add_job(
                "Selftest",
                source_path=audio,
                language="en",
                expected_speakers=1,
                speaker_scope="job",
                diarize=True,
                status="queued",
            )
            run_job(
                db,
                job_id,
                config=JobConfig(
                    language="en",
                    expected_speakers=1,
                    diarize=True,
                    speaker_scope="job",
                ),
                progress=lambda ratio, key, count: lines.append(
                    f"{key} {ratio:.2f} {count}"
                ),
            )
            rows = db.segments(job_id)
            lines.append(f"segments: {len(rows)}")
            for row in rows:
                lines.append(f"{row['speaker_name']}: {row['text']}")
            db.close()
            code = 0 if rows else 1
    except Exception:  # noqa: BLE001 - write the traceback for windowed builds
        lines.append(traceback.format_exc())
        code = 2

    text = "\n".join(lines)
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(text, encoding="utf-8")
    print(text)
    return code


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.selftest:
        return _selftest(args.selftest, args.selftest_output)

    app = QApplication(sys.argv[:1])
    app.setApplicationName("Whisper Scribe")
    app.setOrganizationName("Rey")
    app.setStyle("Fusion")
    _load_fonts()
    app.setFont(QFont("Vazirmatn", 10))

    window = MainWindow(theme=args.theme, lang=args.lang)
    window.show()

    if args.screenshot:
        target = Path(args.screenshot)

        def capture() -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            window.grab().save(str(target))
            app.quit()

        QTimer.singleShot(args.delay, capture)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
