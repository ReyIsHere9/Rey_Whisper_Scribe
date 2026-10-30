"""Conservative Persian text normalization.

Only orthography is touched. Words, repeats, and disfluencies are preserved.
"""

from __future__ import annotations

import re
import unicodedata

_CHAR_MAP = str.maketrans(
    {
        "ي": "ی",
        "ك": "ک",
        "ٱ": "ا",
        "أ": "ا",
        "إ": "ا",
        "ة": "ه",
        "ى": "ی",
        "\u0640": "",
    }
)

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

_SPACE_BEFORE_PUNCT = re.compile(r"\s+([،؛؟!.,:])")
_SPACE_AFTER_PUNCT = re.compile(r"([،؛؟!.,:])(?=[^\s\d])")
_MULTISPACE = re.compile(r"[ \t]{2,}")
_ZWNJ_EDGE = re.compile(r"\s*\u200c\s*")

_PERSIAN_RANGE = re.compile(r"[\u0600-\u06FF]")


def has_persian(text: str) -> bool:
    return bool(_PERSIAN_RANGE.search(text or ""))


def normalize_persian(text: str, *, fold_digits: bool = False) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text).translate(_CHAR_MAP)
    if fold_digits:
        text = text.translate(_ARABIC_DIGITS).translate(_PERSIAN_DIGITS)
    text = _ZWNJ_EDGE.sub("\u200c", text)
    text = _MULTISPACE.sub(" ", text)
    text = _SPACE_BEFORE_PUNCT.sub(r"\1", text)
    text = _SPACE_AFTER_PUNCT.sub(r"\1 ", text)
    return text.strip()


def display_digits(text: str) -> str:
    return text.translate(_ARABIC_DIGITS).translate(_PERSIAN_DIGITS)
