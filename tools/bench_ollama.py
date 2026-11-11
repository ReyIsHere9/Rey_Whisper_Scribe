from __future__ import annotations

import argparse
import json
import time
import urllib.request
from contextlib import suppress
from pathlib import Path

API = "http://localhost:11434/api/generate"
SYSTEM = (
    "You are a Persian proofreader. Correct only spelling, spacing, ZWNJ, "
    "punctuation, and obvious homophone errors. Do not paraphrase, translate, "
    "merge, split, add, or remove content. Preserve English words, names, "
    "numbers, and technical terms. Return only the corrected text with no explanation."
)


def post(payload: dict, timeout: int = 900) -> dict:
    request = urllib.request.Request(
        API,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", default="models/bench/sample.txt")
    parser.add_argument("--out", default="models/bench")
    parser.add_argument("--models", nargs="+", default=["qwen2.5:3b", "qwen2.5:7b"])
    parser.add_argument("--ctx", type=int, default=4096)
    args = parser.parse_args()

    sample = Path(args.sample).read_text(encoding="utf-8")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics = []

    for model in args.models:
        with suppress(Exception):
            post({"model": model, "prompt": "", "keep_alive": 0}, timeout=30)

        payload = {
            "model": model,
            "system": SYSTEM,
            "prompt": sample,
            "stream": False,
            "keep_alive": "5m",
            "options": {"num_ctx": args.ctx, "temperature": 0},
        }
        started = time.monotonic()
        data = post(payload)
        wall = time.monotonic() - started
        output = data.get("response", "")
        safe = model.replace(":", "-").replace(".", "-")
        (out_dir / f"out-{safe}.txt").write_text(output, encoding="utf-8")

        eval_seconds = (data.get("eval_duration") or 0) / 1e9
        tokens_per_second = (
            (data.get("eval_count") or 0) / eval_seconds if eval_seconds else 0.0
        )
        row = {
            "model": model,
            "tokens_per_second": round(tokens_per_second, 1),
            "wall_seconds": round(wall, 1),
            "prompt_tokens": data.get("prompt_eval_count"),
            "output_tokens": data.get("eval_count"),
            "output_file": str(out_dir / f"out-{safe}.txt"),
        }
        metrics.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)

        with suppress(Exception):
            post({"model": model, "prompt": "", "keep_alive": 0}, timeout=30)

    (out_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

