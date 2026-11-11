from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from contextlib import suppress
from pathlib import Path

API = "http://localhost:11434/api/generate"
SEGMENT_RE = re.compile(r"^\[(\d{1,2}:\d{2})\]\s+([^:]+):\s?(.*)$")

SYSTEM = """You are a meticulous Persian copy editor for automatic speech recognition transcripts.

The text is spoken Persian. Improve spelling and grammar while preserving the speaker's colloquial style.

Apply these general rules:
1. Normalize Persian orthography: Arabic ÙŠ/Ùƒ to ÛŒ/Ú©, correct ZWNJ and spacing, punctuation, and Persian digits.
2. Fix non-words: if a token is not a valid Persian word, replace it with the intended common word that fits the context. This includes single-letter substitutions, letter transpositions, and phonetic misspellings.
3. Fix impossible collocations: if a valid word makes the phrase semantically meaningless, replace it with the common intended word.
4. Repair malformed verbs and verb endings only when the intended person and tense are clear from the context. Preserve valid colloquial forms.
5. Normalize clear date and number expressions using common Persian month names and ordinals.
6. Preserve names, English words, numbers, technical terms, and intentional repetition.
7. Be conservative: if the intended correction is not clear, do not edit it; list it as uncertain.
8. Make minimal edits. Never paraphrase, merge, split, reorder, add, or remove content, and never return a rewritten full line.

Return JSON only, with no explanation and no code fences:
{"edits":[{"line":<number>,"original":"<exact substring of that line>","replacement":"<replacement>","rule":"orthography|nonword|collocation|verb|date|spacing|punctuation","confidence":<0.0-1.0>}],"uncertain":[{"line":<number>,"text":"<span>","why":"<short reason>"}]}

Before returning, verify that every "original" appears exactly in its numbered line, that every replacement is a valid Persian word or phrase that fits the sentence, and that the edit is minimal. If no edit is needed, return {"edits":[],"uncertain":[]}."""


def post(payload: dict, timeout: int = 900) -> dict:
    request = urllib.request.Request(
        API,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_json(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--diff", required=True)
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--chunk", type=int, default=10)
    parser.add_argument("--ctx", type=int, default=8192)
    parser.add_argument("--min-confidence", type=float, default=0.55)
    args = parser.parse_args()

    raw_lines = Path(args.input).read_text(encoding="utf-8").splitlines()
    segments: list[tuple[int, str, str]] = []
    for index, line in enumerate(raw_lines):
        match = SEGMENT_RE.match(line)
        if match:
            segments.append(
                (index, f"[{match.group(1)}] {match.group(2)}: ", match.group(3))
            )

    corrected = list(raw_lines)
    applied: list[str] = []
    uncertain: list[str] = []
    failed_chunks = 0
    started = time.monotonic()
    chunks = [
        segments[start : start + args.chunk]
        for start in range(0, len(segments), args.chunk)
    ]

    for chunk_number, chunk in enumerate(chunks, start=1):
        line_map = {
            line_index + 1: text for line_index, _prefix, text in chunk
        }
        prompt = "Numbered transcript lines:\n" + "\n".join(
            f"{line_index + 1}| {text}"
            for line_index, _prefix, text in chunk
        )
        payload = {
            "model": args.model,
            "system": SYSTEM,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "10m",
            "options": {"num_ctx": args.ctx, "temperature": 0},
        }
        try:
            data = post(payload)
            result = parse_json(data.get("response", ""))
        except Exception as error:  # noqa: BLE001 - keep original chunk
            print(f"chunk {chunk_number}/{len(chunks)} failed: {error}", flush=True)
            failed_chunks += 1
            continue

        edits = result.get("edits", [])
        if not isinstance(edits, list):
            edits = []
        for item in edits:
            if not isinstance(item, dict):
                continue
            try:
                line_number = int(item.get("line"))
                original = str(item.get("original", ""))
                replacement = str(item.get("replacement", "")).strip()
                confidence = float(item.get("confidence", 0))
            except (TypeError, ValueError):
                continue
            if line_number not in line_map or not original or not replacement:
                continue
            if confidence < args.min_confidence:
                uncertain.append(
                    f"line {line_number}: {original} -> {replacement} "
                    f"(low confidence {confidence:.2f})"
                )
                continue
            line_index = line_number - 1
            current = corrected[line_index]
            if original not in current or original == replacement:
                continue
            prefix, _sep, text = current.partition(": ")
            if original not in text:
                continue
            if len(replacement) < len(original) * 0.5 or len(replacement) > len(original) * 2:
                continue
            if "\n" in replacement:
                continue
            updated_text = text.replace(original, replacement, 1)
            corrected[line_index] = prefix + ": " + updated_text
            applied.append(
                f"line {line_number}: {original} -> {replacement} "
                f"[{item.get('rule', '?')}, {confidence:.2f}]"
            )

        for item in result.get("uncertain", []) or []:
            if isinstance(item, dict):
                uncertain.append(
                    f"line {item.get('line')}: {item.get('text')} "
                    f"({item.get('why', '')})"
                )

        print(f"chunk {chunk_number}/{len(chunks)} done", flush=True)

    Path(args.output).write_text("\n".join(corrected) + "\n", encoding="utf-8")
    Path(args.diff).write_text(
        "APPLIED EDITS\n" + "\n".join(applied) + "\n\nUNCERTAIN\n" + "\n".join(uncertain) + "\n",
        encoding="utf-8",
    )

    with suppress(Exception):
        post({"model": args.model, "prompt": "", "keep_alive": 0}, timeout=30)

    print(
        json.dumps(
            {
                "segments": len(segments),
                "applied_edits": len(applied),
                "uncertain": len(uncertain),
                "failed_chunks": failed_chunks,
                "seconds": round(time.monotonic() - started, 1),
                "output": args.output,
                "diff": args.diff,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

