"""vibe-arena: one prompt, several models, side by side in the terminal.

LMArena-style comparison without leaving the console: answers, latency and
throughput per model, plus a CSV ready for vibe-plot.
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ENDPOINTS = {
    "mistral": ("https://api.mistral.ai/v1/chat/completions", "MISTRAL_API_KEY"),
    "openai": ("https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY"),
}


def provider_for(model: str) -> str:
    return "openai" if model.startswith(("gpt", "o")) else "mistral"


def ask(model: str, prompt: str):
    url, key_env = ENDPOINTS[provider_for(model)]
    key = os.environ.get(key_env)
    if not key:
        sys.exit(f"vibe-arena: {key_env} is not set")
    req = urllib.request.Request(
        url,
        data=json.dumps({"model": model, "max_tokens": 200,
                         "messages": [{"role": "user", "content": prompt}]}).encode(),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    start = time.time()
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
    elapsed = time.time() - start
    text = data["choices"][0]["message"]["content"].strip()
    tokens = (data.get("usage") or {}).get("completion_tokens") or max(1, len(text) // 4)
    return text, elapsed, tokens


def main():
    ap = argparse.ArgumentParser(
        prog="vibe-arena",
        description="Same prompt to several models, results side by side.")
    ap.add_argument("prompt")
    ap.add_argument("--models", default="mistral-medium-3.5,gpt-4.1-mini",
                    help="comma-separated model names (mistral-* / gpt-*)")
    ap.add_argument("--out-dir", default="runs/arena")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for model in [m.strip() for m in args.models.split(",")]:
        text, elapsed, tokens = ask(model, args.prompt)
        rows.append({"model": model, "latency_s": round(elapsed, 2),
                     "tokens": tokens, "tok_per_s": round(tokens / elapsed, 1)})
        print(f"\x1b[1m{model}\x1b[0m  ({elapsed:.1f}s · {tokens} tok · {tokens / elapsed:.0f} tok/s)")
        preview = text[:220].replace("\n", "\n  ")
        print("  " + preview + ("…" if len(text) > 220 else ""))
        print()
    with (out / "results.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"results: {out}/results.csv "
          f"(chart: vibe-plot {out}/results.csv --bar --x model --y tok_per_s)")


if __name__ == "__main__":
    main()
