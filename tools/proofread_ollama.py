from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from contextlib import suppress
from pathlib import Path

API = "http://localhost:11434/api/generate"
SYSTEM = (
    "You are a Persian proofreader. Correct only spelling, spacing, ZWNJ, "
    "punctuation, and obvious homophone errors. Do not paraphrase, translate, "
    "merge, split, add, or remove content. Preserve English words, names, "
    "numbers, and technical terms. The input is a numbered list of transcript "
    "lines. Return exactly the same number of lines with the same numbering and "
    "no explanation, no extra lines, and no code fences."
)
SEGMENT_RE = re.compile(r"^\[(\d{1,2}:\d{2})\]\s+([^:]+):\s?(.*)$")
NUMBERED_RE = re.compile(r"^\s*(\d+)\s*[\.\)\-:]\s*(.*)$")


def post(payload: dict, timeout: int = 900) -> dict:
    request = urllib.request.Request(
        API,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_numbered(text: str) -> dict[int, str]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[^\n]*\n", "", cleaned)
        cleaned = re.sub(r"\n```$", "", cleaned).strip()
    result: dict[int, str] = {}
    for line in cleaned.splitlines():
        match = NUMBERED_RE.match(line)
        if not match:
            continue
        number = int(match.group(1))
        value = match.group(2).strip()
        if value:
            result[number] = value
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--diff", required=True)
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--chunk", type=int, default=12)
    parser.add_argument("--ctx", type=int, default=8192)
    args = parser.parse_args()

    source = Path(args.input)
    raw_lines = source.read_text(encoding="utf-8").splitlines()
    segments: list[tuple[int, str, str]] = []
    for index, line in enumerate(raw_lines):
        match = SEGMENT_RE.match(line)
        if match:
            prefix = f"[{match.group(1)}] {match.group(2)}: "
            segments.append((index, prefix, match.group(3)))

    corrected_lines = list(raw_lines)
    changes: list[str] = []
    started = time.monotonic()
    chunks = [
        segments[start : start + args.chunk]
        for start in range(0, len(segments), args.chunk)
    ]

    for chunk_number, chunk in enumerate(chunks, start=1):
        prompt = "Numbered transcript lines:\n" + "\n".join(
            f"{position + 1}. {text}" for position, (_index, _prefix, text) in enumerate(chunk)
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
            parsed = parse_numbered(data.get("response", ""))
        except Exception as error:  # noqa: BLE001 - keep the original chunk
            print(f"chunk {chunk_number}/{len(chunks)} failed: {error}", flush=True)
            parsed = {}

        if len(parsed) != len(chunk):
            print(
                f"chunk {chunk_number}/{len(chunks)} returned "
                f"{len(parsed)}/{len(chunk)} lines; keeping originals",
                flush=True,
            )

        for position, (line_index, prefix, original) in enumerate(chunk, start=1):
            replacement = parsed.get(position, original).strip()
            if not replacement:
                replacement = original
            if len(replacement) < len(original) * 0.5 or len(replacement) > len(original) * 2:
                replacement = original
            if replacement != original:
                changes.append(
                    f"line {line_index + 1}\n  before: {original}\n  after:  {replacement}"
                )
            corrected_lines[line_index] = prefix + replacement

        print(f"chunk {chunk_number}/{len(chunks)} done", flush=True)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(corrected_lines) + "\n", encoding="utf-8")
    Path(args.diff).write_text("\n\n".join(changes) + "\n", encoding="utf-8")

    with suppress(Exception):
        post({"model": args.model, "prompt": "", "keep_alive": 0}, timeout=30)

    print(
        json.dumps(
            {
                "segments": len(segments),
                "changed_segments": len(changes),
                "seconds": round(time.monotonic() - started, 1),
                "output": str(output),
                "diff": args.diff,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

