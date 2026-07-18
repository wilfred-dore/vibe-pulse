"""Vibe post_tool hook: append one JSONL telemetry row per tool call.

Registered in .vibe/hooks.toml. Receives the PostToolInvocation JSON on
stdin; never blocks the agent (always exits 0, appends and leaves).

Watch the agent observe itself, live:
  uv run vibe-plot runs/telemetry.jsonl --follow --x call --y duration_ms
"""

import json
import sys
import time
from pathlib import Path


def main() -> None:
    inv = json.load(sys.stdin)
    out = Path(__file__).resolve().parents[1] / "runs"
    out.mkdir(exist_ok=True)
    path = out / "telemetry.jsonl"
    call = sum(1 for _ in path.open()) + 1 if path.exists() else 1
    with path.open("a") as f:
        f.write(json.dumps({
            "call": call,
            "ts": round(time.time(), 3),
            "tool": inv.get("tool_name"),
            "status": inv.get("tool_status"),
            "duration_ms": round(inv.get("duration_ms") or 0.0, 1),
            "output_chars": len(inv.get("tool_output_text") or ""),
        }) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # telemetry must never break the agent
    sys.exit(0)
