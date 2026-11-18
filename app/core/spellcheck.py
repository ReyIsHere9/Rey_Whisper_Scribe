from __future__ import annotations

import importlib.util
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from app.core.normalize_fa import has_persian, normalize_persian
from app.paths import ASSETS_DIR

_TOKEN_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?|[\u0600-\u06FF\u200c\u200d]+|\d+|[^\s]")
_PHONETIC = str.maketrans(
    {
        "ث": "س",
        "ص": "س",
        "ذ": "ز",
        "ض": "ز",
        "ظ": "ز",
        "ط": "ت",
        "غ": "ق",
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ؤ": "و",
        "ئ": "ی",
        "ة": "ه",
    }
)


def _phonetic(text: str) -> str:
    return normalize_persian(text).translate(_PHONETIC)


class SpellcheckUnavailable(RuntimeError):
    pass


@dataclass
class TextEdit:
    start: int
    end: int
    original: str
    replacement: str
    source: str
    confidence: float
    alternatives: list[str] = field(default_factory=list)


@dataclass
class Token:
    text: str
    start: int
    end: int


def available() -> bool:
    return (
        importlib.util.find_spec("spylls") is not None
        and importlib.util.find_spec("symspellpy") is not None
    )


def _distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i]
        for j, right_char in enumerate(right, start=1):
            insert = current[j - 1] + 1
            delete = previous[j] + 1
            replace = previous[j - 1] + (left_char != right_char)
            current.append(min(insert, delete, replace))
        previous = current
    return previous[-1]


def _is_number(text: str) -> bool:
    return bool(re.fullmatch(r"[0-9\u06F0-\u06F9\u0660-\u0669]+", text))


class SpellChecker:
    def __init__(self, protected_words: Iterable[str] = ()) -> None:
        if not available():
            raise SpellcheckUnavailable("spylls and symspellpy are not installed")

        from spylls.hunspell import Dictionary
        from symspellpy import SymSpell, Verbosity

        asset_dir = ASSETS_DIR / "spellcheck"
        rules_path = asset_dir / "rules_fa.json"
        dictionary_path = asset_dir / "fa-IR"
        frequency_path = asset_dir / "wiki_fa_80k.txt"
        if not rules_path.exists() or not (asset_dir / "fa-IR.dic").exists():
            raise SpellcheckUnavailable("Persian spellcheck assets are missing")

        self.rules = json.loads(rules_path.read_text(encoding="utf-8"))
        self.hunspell = Dictionary.from_files(str(dictionary_path))
        self.symspell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
        self.symspell.load_dictionary(
            str(frequency_path), term_index=0, count_index=1, encoding="utf-8"
        )
        self.verbosity = Verbosity.ALL

        self.max_month = int(self.rules.get("max_month_distance", 2))
        self.max_ordinal = int(self.rules.get("max_ordinal_distance", 2))
        self.max_suggestion = int(self.rules.get("max_suggestion_distance", 2))
        self.min_auto = float(self.rules.get("min_auto_confidence", 0.8))

        self.months = {
            normalize_persian(word): word
            for word in (
                self.rules.get("months_solar", [])
                + self.rules.get("months_gregorian", [])
            )
        }
        self.month_aliases = {
            normalize_persian(key): value
            for key, value in self.rules.get("month_aliases", {}).items()
        }
        self.ordinals = {
            normalize_persian(word): word for word in self.rules.get("ordinals", [])
        }

        protected: set[str] = set()
        base_path = asset_dir / "whitelist_base.txt"
        if base_path.exists():
            protected.update(self._parse_whitelist(base_path.read_text(encoding="utf-8")))
        protected.update(self._parse_whitelist(protected_words))
        self.protected = protected

    @staticmethod
    def _parse_whitelist(values: Iterable[str] | str) -> set[str]:
        result: set[str] = set()
        lines = [values] if isinstance(values, str) else values
        for line in lines:
            for part in re.split(r"[\n,]", str(line)):
                text = part.strip()
                if not text or text.startswith("#"):
                    continue
                result.add(normalize_persian(text))
        return result

    def _tokens(self, text: str) -> list[Token]:
        return [
            Token(match.group(0), match.start(), match.end())
            for match in _TOKEN_RE.finditer(text)
        ]

    def _match_month(self, word: str) -> tuple[str, int] | None:
        normalized = normalize_persian(word)
        if normalized in self.month_aliases:
            return self.month_aliases[normalized], 0
        if normalized in self.months:
            return self.months[normalized], 0
        if len(normalized) < 4:
            return None
        best: tuple[str, int] | None = None
        for candidate in set(self.months.values()) | set(self.month_aliases.values()):
            normalized_candidate = normalize_persian(candidate)
            if len(normalized_candidate) < 4:
                continue
            distance = min(
                _distance(normalized, normalized_candidate),
                _distance(_phonetic(normalized), _phonetic(candidate)),
            )
            if distance <= self.max_month and (best is None or distance < best[1]):
                best = (candidate, distance)
        return best

    def _match_ordinal(self, word: str) -> str | None:
        normalized = normalize_persian(word)
        if normalized in self.ordinals:
            return self.ordinals[normalized]
        if len(normalized) < 3:
            return None
        best: tuple[str, int] | None = None
        for candidate in self.ordinals.values():
            distance = min(
                _distance(normalized, normalize_persian(candidate)),
                _distance(_phonetic(normalized), _phonetic(candidate)),
            )
            if distance <= self.max_ordinal and (best is None or distance < best[1]):
                best = (candidate, distance)
        return best[0] if best else None

    def _protected(self, token: Token) -> bool:
        if token.text.isascii() or _is_number(token.text):
            return True
        return normalize_persian(token.text) in self.protected

    def _candidates(
        self, word: str, include_shorter: bool = False
    ) -> list[tuple[str, int, int, int]]:
        normalized = normalize_persian(word)
        candidates: dict[str, tuple[int, int, int]] = {}

        for candidate in self.hunspell.suggest(normalized):
            value = normalize_persian(candidate)
            if value and has_persian(value):
                distance = _distance(normalized, value)
                if distance <= self.max_suggestion:
                    candidates[value] = (distance, 1, 0)

        for item in self.symspell.lookup(
            normalized,
            self.verbosity,
            max_edit_distance=self.max_suggestion,
            include_unknown=False,
        ):
            value = normalize_persian(item.term)
            if not value or not has_persian(value):
                continue
            distance = _distance(normalized, value)
            if distance > self.max_suggestion:
                continue
            previous = candidates.get(value)
            candidates[value] = (
                distance,
                (previous[1] if previous else 0) + 1,
                item.count if previous is None else max(previous[2], item.count),
            )

        ranked = sorted(
            candidates.items(),
            key=lambda item: (
                item[1][0],
                -item[1][1],
                -(item[1][2] or 0),
                len(item[0]),
            ),
        )
        return [
            (candidate, distance, sources, count)
            for candidate, (distance, sources, count) in ranked
            if candidate != normalized
            and (
                len(candidate) >= len(normalized)
                or (
                    include_shorter
                    and candidate
                    and normalized
                    and candidate[0] == normalized[0]
                )
            )
        ]

    def _suggestions(self, word: str) -> tuple[str, float] | None:
        ranked = self._candidates(word)
        if not ranked:
            return None
        best_distance = ranked[0][1]
        best = [item for item in ranked if item[1] == best_distance]
        if len(best) != 1:
            return None
        candidate, distance, sources, _count = best[0]
        if sources < 2 and distance > 1:
            return None
        if distance == 1:
            confidence = 0.92 if sources >= 2 else 0.86
        elif sources >= 2:
            confidence = 0.82
        else:
            return None
        return (candidate, confidence) if confidence >= self.min_auto else None

    def suggestions(self, text: str) -> list[TextEdit]:
        edits: list[TextEdit] = []
        for token in self._tokens(text):
            if not has_persian(token.text) or self._protected(token):
                continue
            normalized = normalize_persian(token.text)
            if not normalized or self.hunspell.lookup(normalized):
                continue
            month = self._match_month(token.text)
            if month is not None and month[1] == 0:
                continue
            ranked = self._candidates(token.text, include_shorter=True)
            ranked.sort(
                key=lambda item: (item[1], -(item[3] or 0), -item[2], len(item[0]))
            )
            alternatives: list[str] = []
            for candidate, _distance, _sources, _count in ranked:
                if candidate not in alternatives:
                    alternatives.append(candidate)
                if len(alternatives) >= 6:
                    break
            if not alternatives:
                continue
            edits.append(
                TextEdit(
                    start=token.start,
                    end=token.end,
                    original=token.text,
                    replacement=alternatives[0],
                    source="suggestion",
                    confidence=0.55,
                    alternatives=alternatives,
                )
            )
        return edits

    def check(self, text: str) -> tuple[str, list[TextEdit]]:
        tokens = self._tokens(text)
        edits: list[TextEdit] = []
        covered: set[int] = set()

        for index, token in enumerate(tokens):
            if not has_persian(token.text) or self._protected(token):
                continue
            month_match = self._match_month(token.text)
            if month_match is None:
                continue
            month, month_distance = month_match

            previous_index = index - 1
            while previous_index >= 0 and not (
                has_persian(tokens[previous_index].text)
                or _is_number(tokens[previous_index].text)
            ):
                previous_index -= 1

            day: str | None = None
            day_token: Token | None = None
            if previous_index >= 0:
                previous = tokens[previous_index]
                if _is_number(previous.text):
                    day = previous.text
                    day_token = previous
                else:
                    ordinal = self._match_ordinal(previous.text)
                    if ordinal:
                        day = ordinal
                        day_token = previous

            if day_token is None or self._protected(day_token):
                continue

            start = day_token.start
            original = text[start : token.end]
            replacement = f"{day} {month}" if day else month
            if replacement == original:
                continue

            confidence = 0.95 if day and month_distance == 0 else 0.9
            edits.append(
                TextEdit(
                    start=start,
                    end=token.end,
                    original=original,
                    replacement=replacement,
                    source="date",
                    confidence=confidence,
                )
            )
            if day_token:
                covered.add(previous_index)
            covered.add(index)

        for index, token in enumerate(tokens):
            if index in covered or self._protected(token):
                continue
            if not has_persian(token.text):
                continue
            normalized = normalize_persian(token.text)
            if not normalized or self.hunspell.lookup(normalized):
                continue
            month = self._match_month(token.text)
            if month is not None and month[1] == 0:
                continue
            suggestion = self._suggestions(token.text)
            if suggestion is None:
                continue
            replacement, confidence = suggestion
            edits.append(
                TextEdit(
                    start=token.start,
                    end=token.end,
                    original=token.text,
                    replacement=replacement,
                    source="dictionary",
                    confidence=confidence,
                )
            )

        edits.sort(key=lambda edit: (edit.start, -edit.confidence))
        selected: list[TextEdit] = []
        last_end = -1
        for edit in edits:
            if edit.start < last_end:
                continue
            selected.append(edit)
            last_end = edit.end

        if not selected:
            return text, []

        parts: list[str] = []
        cursor = 0
        for edit in selected:
            parts.append(text[cursor : edit.start])
            parts.append(edit.replacement)
            cursor = edit.end
        parts.append(text[cursor:])
        return "".join(parts), selected


def apply_spellcheck(db: Any, job_id: int, protected_words: Iterable[str] = ()) -> int:
    checker = SpellChecker(protected_words)
    db.conn.execute("DELETE FROM spell_edits WHERE job_id = ?", (job_id,))
    total = 0
    for segment in db.segments(job_id):
        corrected, edits = checker.check(segment["text"])
        if edits:
            db.conn.execute(
                "UPDATE segments SET text = ? WHERE id = ?",
                (corrected, segment["id"]),
            )
            for edit in edits:
                db.conn.execute(
                    "INSERT INTO spell_edits(job_id, segment_id, start_char, end_char, "
                    "original, replacement, source, confidence, status, alternatives) "
                    "VALUES(?, ?, ?, ?, ?, ?, ?, ?, 'applied', '[]')",
                    (
                        job_id,
                        segment["id"],
                        edit.start,
                        edit.end,
                        edit.original,
                        edit.replacement,
                        edit.source,
                        edit.confidence,
                    ),
                )

        for suggestion in checker.suggestions(corrected):
            db.conn.execute(
                "INSERT INTO spell_edits(job_id, segment_id, start_char, end_char, "
                "original, replacement, source, confidence, status, alternatives) "
                "VALUES(?, ?, ?, ?, ?, ?, 'suggestion', ?, 'suggested', ?)",
                (
                    job_id,
                    segment["id"],
                    suggestion.start,
                    suggestion.end,
                    suggestion.original,
                    suggestion.replacement,
                    suggestion.confidence,
                    json.dumps(suggestion.alternatives, ensure_ascii=False),
                ),
            )
        total += len(edits)
    db.conn.commit()
    return total
