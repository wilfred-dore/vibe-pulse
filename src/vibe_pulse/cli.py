"""vibe-plot: live data & ML training visualization in the terminal."""

import argparse
import json
import sys
from pathlib import Path

from . import plotter, stream

CLEAR = "\x1b[H\x1b[2J"


def _load_json(source):
    text = sys.stdin.read() if source == "-" else Path(source).read_text()
    return json.loads(text)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="vibe-plot",
        description="Live data & ML training visualization in the terminal. "
                    "Reads JSON lines (one object per line) or CSV.",
    )
    ap.add_argument("source", help="JSONL/CSV/JSON file, or '-' for stdin")
    ap.add_argument("--x", dest="x_key", help="x-axis key (default: first numeric key)")
    ap.add_argument("--y", dest="y_keys", help="comma-separated series keys (default: all numeric keys)")
    ap.add_argument("--csv", action="store_true", help="parse source as CSV")
    ap.add_argument("--follow", "-f", action="store_true", help="live-update as the file grows (JSONL only)")
    ap.add_argument("--idle-timeout", type=float, default=None,
                    help="stop --follow after N seconds without new data")
    ap.add_argument("--heatmap", action="store_true",
                    help="render a JSON matrix ({'labels': [...], 'matrix': [[...]]}) as a heatmap")
    ap.add_argument("--report", action="store_true",
                    help="render precision/recall bars from a JSON report "
                         "({'classes': [...], 'precision': [...], 'recall': [...]})")
    ap.add_argument("--scatter", action="store_true", help="draw points instead of lines")
    ap.add_argument("--hist", metavar="KEY", help="histogram of one column's values")
    ap.add_argument("--bar", action="store_true",
                    help="bar chart: --x = category column, --y = value column")
    ap.add_argument("--title")
    ap.add_argument("--width", type=int, default=70)
    ap.add_argument("--height", type=int, default=15)
    args = ap.parse_args(argv)

    if args.heatmap:
        payload = _load_json(args.source)
        matrix = payload["matrix"] if isinstance(payload, dict) else payload
        labels = payload.get("labels") if isinstance(payload, dict) else None
        title = args.title or (payload.get("title") if isinstance(payload, dict) else None)
        print(plotter.render_heatmap(matrix, labels, title))
        return 0

    if args.report:
        payload = _load_json(args.source)
        print(plotter.render_report(payload, args.title or payload.get("title")))
        return 0

    y_keys = args.y_keys.split(",") if args.y_keys else None
    as_csv = args.csv or str(args.source).endswith(".csv")

    if args.bar:
        if not (args.x_key and args.y_keys):
            print("vibe-plot: --bar needs --x (categories) and --y (values)")
            return 1
        rows = stream.read_rows(args.source, as_csv=as_csv)
        y_key = args.y_keys.split(",")[0]
        pairs = [(str(r[args.x_key]), r[y_key]) for r in rows
                 if r.get(args.x_key) is not None
                 and isinstance(r.get(y_key), (int, float))]
        if not pairs:
            print(f"vibe-plot: no data for '{args.x_key}'/'{y_key}'")
            return 1
        print(plotter.render_bar([p[0] for p in pairs], [p[1] for p in pairs],
                                 width=args.width, title=args.title))
        return 0

    if args.hist:
        rows = stream.read_rows(args.source, as_csv=as_csv)
        values = [r[args.hist] for r in rows
                  if isinstance(r.get(args.hist), (int, float))]
        if not values:
            print(f"vibe-plot: no numeric values for key '{args.hist}'")
            return 1
        print(plotter.render_hist(values, width=args.width,
                                  title=args.title or f"distribution of {args.hist}"))
        return 0

    def frame(rows):
        return plotter.render_lines(rows, args.x_key, y_keys, args.width, args.height,
                                    args.title, scatter=args.scatter)

    if not args.follow:
        print(frame(stream.read_rows(args.source, as_csv=as_csv)))
        return 0

    rows = []
    live = sys.stdout.isatty()
    try:
        for batch in stream.follow_rows(args.source, idle_timeout=args.idle_timeout):
            rows.extend(batch)
            if live:
                sys.stdout.write(CLEAR + frame(rows) + "\n")
                sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    if rows:
        if live:
            sys.stdout.write(CLEAR)
        print(frame(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
