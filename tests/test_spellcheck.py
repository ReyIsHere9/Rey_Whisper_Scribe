from __future__ import annotations

from app.core.spellcheck import SpellChecker


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
