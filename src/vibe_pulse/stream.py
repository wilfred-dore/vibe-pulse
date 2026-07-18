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


SQLITE_SUFFIXES = {".sqlite", ".sqlite3", ".db"}


def _read_xlsx(path):
    import openpyxl

    sheet = openpyxl.load_workbook(path, read_only=True, data_only=True).active
    it = sheet.iter_rows(values_only=True)
    header = [str(h) for h in next(it)]
    return [dict(zip(header, (_coerce(v) for v in row))) for row in it
            if any(v is not None for v in row)]


def _read_sqlite(path, sql=None):
    import sqlite3

    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        if not sql:
            table = con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' LIMIT 1"
            ).fetchone()
            if not table:
                return []
            sql = f'SELECT * FROM "{table[0]}" LIMIT 10000'
        cur = con.execute(sql)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, (_coerce(v) for v in row))) for row in cur.fetchall()]
    finally:
        con.close()


def read_rows(source, as_csv=False, sql=None):
    """Read every row available right now.

    source: path or '-' for stdin. Formats: JSONL (default), CSV, .xlsx
    spreadsheets, SQLite databases (optionally with a custom SELECT via sql).
    """
    path = Path(source) if source != "-" else None
    if path and path.suffix == ".xlsx":
        return _read_xlsx(path)
    if path and (path.suffix in SQLITE_SUFFIXES or sql):
        return _read_sqlite(path, sql)
    text = sys.stdin.read() if source == "-" else path.read_text()
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
            raw = path.read_bytes()
            if len(raw) < pos:  # file truncated (new run started): restart
                pos = 0
            data = raw[pos:]
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
