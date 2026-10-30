from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from app.paths import PACKAGE_DIR, db_path
from app.theme.tokens import speaker_color

SCHEMA = (PACKAGE_DIR / "db" / "schema.sql").read_text(encoding="utf-8")


class Database:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else db_path()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA busy_timeout = 8000")

        columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(jobs)")}
        if "diarize" not in columns:
            self.conn.execute("ALTER TABLE jobs ADD COLUMN diarize INTEGER NOT NULL DEFAULT 1")
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def setting(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self.conn.commit()

    def jobs(self) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT j.*, "
                "(SELECT COUNT(*) FROM segments s WHERE s.job_id = j.id) AS segment_count, "
                "(SELECT COUNT(DISTINCT s.speaker_id) FROM segments s WHERE s.job_id = j.id) "
                "AS speaker_count "
                "FROM jobs j ORDER BY j.created_at DESC, j.id DESC"
            )
        )

    def job(self, job_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

    def speakers(self, job_id: int | None, include_global: bool = True) -> list[sqlite3.Row]:
        if job_id is not None and include_global:
            query = "SELECT * FROM speakers WHERE job_id = ? OR is_global = 1 ORDER BY is_global, id"
            rows = self.conn.execute(query, (job_id,)).fetchall()
        elif job_id is not None:
            rows = self.conn.execute(
                "SELECT * FROM speakers WHERE job_id = ? ORDER BY id", (job_id,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM speakers WHERE is_global = 1 ORDER BY id"
            ).fetchall()
        return list(rows)

    def segments(self, job_id: int) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT s.*, sp.name AS speaker_name, sp.color AS speaker_color "
                "FROM segments s LEFT JOIN speakers sp ON sp.id = s.speaker_id "
                "WHERE s.job_id = ? ORDER BY s.start_ms",
                (job_id,),
            )
        )

    def speaker_stats(self, job_id: int) -> dict[int, dict[str, int]]:
        rows = self.conn.execute(
            "SELECT speaker_id, COUNT(*) AS turns, COALESCE(SUM(end_ms - start_ms), 0) AS ms "
            "FROM segments WHERE job_id = ? GROUP BY speaker_id",
            (job_id,),
        ).fetchall()
        return {r["speaker_id"]: {"turns": r["turns"], "ms": r["ms"]} for r in rows}

    def add_job(
        self,
        title: str,
        source_path: str = "",
        language: str = "fa",
        model: str = "large-v3",
        speaker_scope: str = "global",
        expected_speakers: int = 0,
        diarize: bool = True,
        status: str = "queued",
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO jobs(title, source_path, language, model, speaker_scope, "
            "expected_speakers, diarize, status) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            (
                title,
                source_path,
                language,
                model,
                speaker_scope,
                expected_speakers,
                int(diarize),
                status,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def set_job_status(self, job_id: int, status: str) -> None:
        self.conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
        self.conn.commit()

    def rename_job(self, job_id: int, title: str) -> None:
        self.conn.execute("UPDATE jobs SET title = ? WHERE id = ?", (title, job_id))
        self.conn.commit()

    def delete_job(self, job_id: int) -> None:
        self.conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        self.conn.commit()

    def add_speaker(
        self,
        job_id: int | None,
        name: str,
        color: str | None = None,
        is_global: bool = False,
        voiceprint: str | None = None,
    ) -> int:
        count = self.conn.execute("SELECT COUNT(*) AS n FROM speakers").fetchone()["n"]
        cur = self.conn.execute(
            "INSERT INTO speakers(job_id, name, color, is_global, voiceprint) "
            "VALUES(?, ?, ?, ?, ?)",
            (job_id, name, color or speaker_color(count), int(is_global), voiceprint),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def rename_speaker(self, speaker_id: int, name: str) -> None:
        self.conn.execute("UPDATE speakers SET name = ? WHERE id = ?", (name, speaker_id))
        self.conn.commit()

    def merge_speakers(self, source_id: int, target_id: int) -> None:
        if source_id == target_id:
            return
        self.conn.execute(
            "UPDATE segments SET speaker_id = ? WHERE speaker_id = ?", (target_id, source_id)
        )
        self.conn.execute(
            "UPDATE speakers SET voiceprint = NULL WHERE id = ?", (source_id,)
        )
        self.conn.execute("DELETE FROM speakers WHERE id = ?", (source_id,))
        self.conn.commit()

    def assign_segments(self, segment_ids: list[int], speaker_id: int) -> int:
        ids = [int(segment_id) for segment_id in segment_ids]
        if not ids:
            return 0
        placeholders = ", ".join("?" for _ in ids)
        cursor = self.conn.execute(
            f"UPDATE segments SET speaker_id = ? WHERE id IN ({placeholders})",
            (speaker_id, *ids),
        )
        self.conn.commit()
        return int(cursor.rowcount)

    def update_segment_text(self, segment_id: int, text: str) -> None:
        self.conn.execute("UPDATE segments SET text = ? WHERE id = ?", (text, segment_id))
        self.conn.commit()

    def counts(self) -> dict[str, int]:
        jobs = self.conn.execute("SELECT COUNT(*) AS n FROM jobs").fetchone()["n"]
        speakers = self.conn.execute("SELECT COUNT(*) AS n FROM speakers").fetchone()["n"]
        segments = self.conn.execute("SELECT COUNT(*) AS n FROM segments").fetchone()["n"]
        return {"jobs": jobs, "speakers": speakers, "segments": segments}

    def seed_demo(self) -> None:
        if os.environ.get("WHISPERSCRIBE_NO_DEMO"):
            return
        if self.conn.execute("SELECT COUNT(*) AS n FROM jobs").fetchone()["n"]:
            return

        names = [
            ("مریم", True),
            ("آرش", True),
            ("نیلوفر", True),
            ("Sam", True),
            ("Dr. Rezaei", True),
            ("سارا", True),
            ("Rey", True),
        ]
        ids: dict[str, int] = {}
        for index, (name, is_global) in enumerate(names):
            cur = self.conn.execute(
                "INSERT INTO speakers(job_id, name, color, is_global) VALUES(NULL, ?, ?, ?)",
                (name, speaker_color(index), int(is_global)),
            )
            ids[name] = int(cur.lastrowid)

        demo_jobs = [
            {
                "title": "جلسهٔ تیم محصول",
                "language": "fa",
                "duration_ms": 1_458_000,
                "created_at": "2026-10-28 09:30:00",
                "segments": [
                    (12_340, 16_900, "مریم", "خب، بذارید از جلسهٔ امروز شروع کنیم. دستور جلسه رو روی تخته داریم."),
                    (17_200, 23_450, "آرش", "من فکر می‌کنم timeline پروژه یک هفته عقب افتاده، مخصوصاً بخش backend."),
                    (24_010, 29_800, "نیلوفر", "آره، ولی design تا آخر هفته نهایی می‌شه. من با تیم هماهنگ کردم."),
                    (30_300, 36_900, "مریم", "باشه، پس بیایید روی MVP تمرکز کنیم و بقیه رو بذاریم برای فاز بعد."),
                    (37_500, 44_200, "Sam", "Actually, we can ship the core flow next Tuesday and add the rest later."),
                    (45_000, 51_800, "آرش", "موافقم. فقط باید یه review نهایی هم بذاریم برای امنیت."),
                    (52_400, 59_100, "مریم", "عالیه. پس فعلاً دست نگه داریم تا نتیجهٔ تست‌ها مشخص بشه."),
                ],
            },
            {
                "title": "Therapy session — week 12",
                "language": "fa",
                "duration_ms": 3_124_000,
                "created_at": "2026-10-26 17:05:00",
                "segments": [
                    (4_100, 12_600, "Dr. Rezaei", "از هفتهٔ گذشته چطور بودی؟ چیزی بود که بخوای درباره‌ش حرف بزنیم؟"),
                    (13_200, 22_800, "سارا", "راستش خوابم بهتر شده، ولی هنوز صبح‌ها یه فشار مبهم توی سینه دارم."),
                    (23_400, 29_900, "Dr. Rezaei", "وقتی اون فشار میاد، معمولاً به چی فکر می‌کنی؟"),
                    (30_500, 41_200, "سارا", "بیشتر دربارهٔ deadline کار. حتی وقتی چیز خاصی نیست، ذهنم می‌ره سمتش."),
                ],
            },
            {
                "title": "Voice journal — Chapter 3",
                "language": "fa",
                "duration_ms": 612_000,
                "created_at": "2026-10-24 22:14:00",
                "segments": [
                    (1_200, 9_800, "Rey", "امشب دربارهٔ فصل سوم «عادت‌های اتمی» حرف می‌زنم."),
                    (10_400, 20_100, "Rey", "نکتهٔ اصلی این فصل اینه که هویت از تکرار ساخته می‌شه، نه از تصمیم."),
                    (20_900, 34_500, "Rey", "و یه جملهٔ انگلیسی که خیلی بهم چسبید: every action is a vote for the person you wish to become."),
                ],
            },
        ]

        for job in demo_jobs:
            cur = self.conn.execute(
                "INSERT INTO jobs(title, language, model, speaker_scope, expected_speakers, "
                "status, duration_ms, is_demo, created_at) "
                "VALUES(?, ?, 'large-v3', 'global', 2, 'transcribed', ?, 1, ?)",
                (job["title"], job["language"], job["duration_ms"], job["created_at"]),
            )
            job_id = int(cur.lastrowid)
            for start, end, speaker, text in job["segments"]:
                self.conn.execute(
                    "INSERT INTO segments(job_id, speaker_id, start_ms, end_ms, text, confidence) "
                    "VALUES(?, ?, ?, ?, ?, ?)",
                    (job_id, ids[speaker], start, end, text, 0.92),
                )

        self.conn.commit()
