from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="whisper-scribe")
    parser.add_argument("--theme", choices=["light", "dark"], default=None)
    parser.add_argument("--lang", choices=["en", "fa"], default=None)
    parser.add_argument("--screenshot", default="")
    parser.add_argument("--delay", type=int, default=900)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Whisper Scribe")
    app.setOrganizationName("Rey")
    app.setStyle("Fusion")

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
