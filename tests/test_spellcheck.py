from __future__ import annotations

import json

from app.core.spellcheck import SpellChecker, apply_spellcheck
from app.db import Database


def test_date_typo_is_corrected() -> None:
    checker = SpellChecker()
    corrected, edits = checker.check("جلسه در چارم آوریل")
    assert "چهارم آوریل" in corrected
    assert any(edit.source == "date" for edit in edits)


def test_gregorian_months_are_preserved() -> None:
    checker = SpellChecker()
    for text in ("اول ژانویه", "سوم فوریه", "پنجم مارس", "سه ژوئن 2026"):
        corrected, edits = checker.check(text)
        assert corrected == text
        assert not edits


def test_invalid_month_matches_do_not_fire() -> None:
    checker = SpellChecker()
    for text in (
        "تست های دکتوری سال 98",
        "این نکته را مورد توجه خرار بدید",
        "در این حوضه نقص جدی وجود دارد",
    ):
        corrected, edits = checker.check(text)
        assert corrected == text
        assert not edits


def test_whitelist_blocks_date_rule() -> None:
    checker = SpellChecker(["چارم"])
    corrected, edits = checker.check("جلسه در چارم آوریل")
    assert corrected == "جلسه در چارم آوریل"
    assert not edits


def test_ambiguous_words_are_suggested_not_autocorrected() -> None:
    checker = SpellChecker()
    text = "تست های دکتوری سال 98"
    corrected, edits = checker.check(text)
    assert corrected == text
    assert not edits
    suggestions = checker.suggestions(text)
    target = next(item for item in suggestions if item.original == "دکتوری")
    assert "دکتری" in target.alternatives


def test_review_applies_selected_suggestion(tmp_path) -> None:
    db = Database(tmp_path / "review.db")
    try:
        job_id = db.add_job("review")
        db.conn.execute(
            "INSERT INTO segments(job_id, start_ms, end_ms, text) VALUES(?, 0, 1000, ?)",
            (job_id, "تست های دکتوری و خرار"),
        )
        db.conn.commit()
        apply_spellcheck(db, job_id)
        suggestions = db.spell_suggestions(job_id)
        targets = {
            item["original"]: item
            for item in suggestions
            if item["original"] in {"دکتوری", "خرار"}
        }
        assert set(targets) == {"دکتوری", "خرار"}
        choices = {
            int(item["id"]): json.loads(item["alternatives"])[0]
            for item in targets.values()
        }
        db.apply_spell_suggestions(job_id, choices)
        assert not db.spell_suggestions(job_id)
        text = db.segments(job_id)[0]["text"]
        for replacement in choices.values():
            assert replacement in text
        assert len(db.spell_edits(job_id)) == 2
    finally:
        db.close()
