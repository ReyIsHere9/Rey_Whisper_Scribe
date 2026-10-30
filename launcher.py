from __future__ import annotations

import sys
import traceback
from pathlib import Path


def _log_startup_error() -> None:
    try:
        base = (
            Path(sys.executable).resolve().parent
            if getattr(sys, "frozen", False)
            else Path(__file__).resolve().parent
        )
        (base / "startup-error.log").write_text(
            traceback.format_exc(), encoding="utf-8"
        )
    except Exception:  # noqa: BLE001 - last-resort logger has nowhere else to report
        return


try:
    from app.main import main
except Exception:
    _log_startup_error()
    raise

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        _log_startup_error()
        raise
