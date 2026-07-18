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
    ap.add_argument("source", nargs="+",
                    help="JSONL/CSV/JSON file(s), or '-' for stdin; "
                         "several files with --compare to overlay runs")
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
    ap.add_argument("--compare", action="store_true",
                    help="overlay one metric (--y, default 'loss') across several runs")
    ap.add_argument("--diagram", action="store_true",
                    help="render a PlantUML source file as an ASCII diagram")
    ap.add_argument("--sql", metavar="QUERY",
                    help="SELECT to run when source is a SQLite database")
    ap.add_argument("--table", action="store_true",
                    help="render rows as an aligned terminal table")
    ap.add_argument("--title")
    ap.add_argument("--width", type=int, default=70)
    ap.add_argument("--height", type=int, default=15)
    args = ap.parse_args(argv)
    sources = args.source
    args.source = sources[0]  # single-file modes use the first path

    if args.diagram:
        from . import diagram
        text = sys.stdin.read() if args.source == "-" else Path(args.source).read_text()
        print(diagram.render(text))
        return 0

    if args.compare:
        key = args.y_keys.split(",")[0] if args.y_keys else "loss"
        series = []
        for s in sources:
            rows = stream.read_rows(s, as_csv=args.csv or str(s).endswith(".csv"), sql=args.sql)
            keys = plotter.numeric_keys(rows)
            if not keys:
                continue
            x_key = args.x_key or keys[0]
            pts = [(r[x_key], r[key]) for r in rows
                   if isinstance(r.get(x_key), (int, float))
                   and isinstance(r.get(key), (int, float))]
            parent = Path(s).parent.name
            series.append((parent if parent not in ("", ".") else Path(s).stem, pts))
        print(plotter.render_compare(series, args.width, args.height,
                                     args.title or f"compare: {key}"))
        return 0

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

    if args.table:
        rows = stream.read_rows(args.source, as_csv=as_csv, sql=args.sql)
        columns = args.y_keys.split(",") if args.y_keys else None
        print(plotter.render_table(rows, columns, title=args.title))
        return 0

    if args.bar:
        if not (args.x_key and args.y_keys):
            print("vibe-plot: --bar needs --x (categories) and --y (values)")
            return 1
        rows = stream.read_rows(args.source, as_csv=as_csv, sql=args.sql)
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
        rows = stream.read_rows(args.source, as_csv=as_csv, sql=args.sql)
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
        print(frame(stream.read_rows(args.source, as_csv=as_csv, sql=args.sql)))
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
