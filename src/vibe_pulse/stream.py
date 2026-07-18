"""Data sources for vibe-plot: JSON lines / CSV, read once or followed live."""

import csv
import io
import json
import sys
import time
from pathlib import Path


def parse_line(line):
    line = line.strip()
    if not line:
        return None
    try:
        row = json.loads(line)
    except json.JSONDecodeError:
        return None
    return row if isinstance(row, dict) else None


def _coerce(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def read_rows(source, as_csv=False):
    """Read every row available right now. source is a path or '-' for stdin."""
    text = sys.stdin.read() if source == "-" else Path(source).read_text()
    if as_csv:
        reader = csv.DictReader(io.StringIO(text))
        return [{k: _coerce(v) for k, v in row.items()} for row in reader]
    rows = [parse_line(line) for line in text.splitlines()]
    return [r for r in rows if r]


def follow_rows(source, idle_timeout=None, poll=0.2):
    """Yield batches of new JSONL rows as the file grows (or stdin streams).

    Stops after idle_timeout seconds without new data (None = wait forever,
    until Ctrl+C). Only complete lines are consumed, so a writer mid-line is
    never misread.
    """
    if source == "-":
        for line in sys.stdin:
            row = parse_line(line)
            if row:
                yield [row]
        return

    path = Path(source)
    pos = 0
    idle = 0.0
    while True:
        batch = []
        if path.exists():
            data = path.read_bytes()[pos:]
            if data:
                cut = data.rfind(b"\n") + 1
                for raw in data[:cut].splitlines():
                    row = parse_line(raw.decode("utf-8", "replace"))
                    if row:
                        batch.append(row)
                pos += cut
        if batch:
            idle = 0.0
            yield batch
        else:
            time.sleep(poll)
            idle += poll
            if idle_timeout is not None and idle >= idle_timeout:
                return
