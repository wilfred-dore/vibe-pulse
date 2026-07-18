"""Terminal renderers: braille line charts, ANSI heatmaps, precision/recall bars."""

import plotille

COLORS = ["cyan", "magenta", "yellow", "green", "red", "blue"]

# 256-color ramp, dark -> red -> orange -> yellow (Mistral colors, conveniently)
HEAT_RAMP = [233, 52, 88, 124, 160, 196, 202, 208, 214, 220]


def _bold(text):
    return f"\x1b[1m{text}\x1b[0m"


def numeric_keys(rows):
    keys = []
    for row in rows:
        for k, v in row.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and k not in keys:
                keys.append(k)
    return keys


def render_table(rows, columns=None, max_rows=25, title=None):
    """Boxed, aligned terminal table — first brick of Canvas-to-CLI."""
    if not rows:
        return "vibe-plot: no rows"
    columns = columns or list(rows[0].keys())
    body = rows[:max_rows]

    def fmt(v):
        if isinstance(v, float):
            return f"{v:g}"
        return "" if v is None else str(v)

    widths = [max(len(c), *(len(fmt(r.get(c))) for r in body)) for c in columns]
    sep = "├" + "┼".join("─" * (w + 2) for w in widths) + "┤"
    top = "┌" + "┬".join("─" * (w + 2) for w in widths) + "┐"
    bot = "└" + "┴".join("─" * (w + 2) for w in widths) + "┘"
    head = "│" + "│".join(f" {_bold(c.ljust(w))} " for c, w in zip(columns, widths)) + "│"
    lines = ([_bold(title)] if title else []) + [top, head, sep]
    for r in body:
        lines.append("│" + "│".join(
            f" {fmt(r.get(c)).rjust(w) if isinstance(r.get(c), (int, float)) else fmt(r.get(c)).ljust(w)} "
            for c, w in zip(columns, widths)) + "│")
    lines.append(bot)
    if len(rows) > max_rows:
        lines.append(f"… {len(rows) - max_rows} more rows")
    return "\n".join(lines)


def render_compare(series, width=70, height=15, title=None):
    """Overlay one metric across several runs. series = [(label, [(x, y)])]."""
    fig = plotille.Figure()
    fig.width = width
    fig.height = height
    fig.color_mode = "names"
    plotted = 0
    for i, (label, pts) in enumerate(series):
        if len(pts) >= 2:
            fig.plot([p[0] for p in pts], [p[1] for p in pts],
                     lc=COLORS[i % len(COLORS)], label=label)
            plotted += 1
    if not plotted:
        return "vibe-plot: nothing to compare (need >= 2 points per run)"
    out = fig.show(legend=True)
    if title:
        out = f"{_bold(title)}\n{out}"
    return out


def render_bar(labels, values, width=60, height=None, title=None):
    """Horizontal bar chart via plotext (labels = categories, values = numbers)."""
    import plotext as plt

    plt.clear_figure()
    plt.theme("pro")  # transparent background, works on dark and light terminals
    plt.bar(labels, values, orientation="horizontal", color=208)
    if title:
        plt.title(title)
    plt.plotsize(width, height or max(12, len(labels) + 4))
    out = plt.build()
    plt.clear_figure()
    return out.rstrip()


def render_hist(values, bins=25, width=60, title=None):
    out = plotille.hist(values, bins=bins, width=width, lc="cyan", color_mode="names")
    if title:
        out = f"{_bold(title)}\n{out}"
    return out


def render_lines(rows, x_key=None, y_keys=None, width=70, height=15, title=None,
                 scatter=False):
    keys = numeric_keys(rows)
    if not keys:
        return "vibe-plot: waiting for data..."
    x_key = x_key or keys[0]
    y_keys = y_keys or [k for k in keys if k != x_key][:4]

    fig = plotille.Figure()
    fig.width = width
    fig.height = height
    fig.color_mode = "names"

    plotted = 0
    for i, key in enumerate(y_keys):
        pts = [
            (row[x_key], row[key])
            for row in rows
            if isinstance(row.get(x_key), (int, float)) and isinstance(row.get(key), (int, float))
        ]
        if len(pts) >= 2:
            draw = fig.scatter if scatter else fig.plot
            draw([p[0] for p in pts], [p[1] for p in pts],
                 lc=COLORS[i % len(COLORS)], label=key)
            plotted += 1
    if not plotted:
        return "vibe-plot: waiting for data..."

    out = fig.show(legend=True)
    if title:
        out = f"{_bold(title)}\n{out}"
    return out


def _fmt_cell(value):
    f = float(value)
    if f == 0:
        return "·"  # zeros recede so the diagonal pops, even without color
    return str(int(f)) if f.is_integer() else f"{f:.2f}"


def render_heatmap(matrix, labels=None, title=None):
    labels = [str(l) for l in (labels or range(len(matrix)))]
    peak = max((max(row) for row in matrix), default=0) or 1
    widths = [len(_fmt_cell(v)) for row in matrix for v in row] + [len(l) for l in labels]
    cell = max(4, max(widths) + 2)

    lines = []
    if title:
        lines.append(_bold(title))
    lines.append(" " * 7 + "".join(f"{l:^{cell}}" for l in labels) + "  (predicted)")
    for label, row in zip(labels, matrix):
        cells = []
        for v in row:
            color = HEAT_RAMP[min(int(float(v) / peak * (len(HEAT_RAMP) - 1)), len(HEAT_RAMP) - 1)]
            fg = 16 if color >= 202 else 255
            cells.append(f"\x1b[48;5;{color}m\x1b[38;5;{fg}m{_fmt_cell(v):^{cell}}\x1b[0m")
        lines.append(f"{label:>6} " + "".join(cells))
    lines.append("(true)")
    return "\n".join(lines)


def _bar(value, width, ansi_color):
    filled = max(0, min(width, round(value * width)))
    return f"\x1b[{ansi_color}m{'█' * filled}\x1b[0m{'·' * (width - filled)} {value:.2f}"


def render_report(report, title=None, width=20):
    classes = [str(c) for c in report["classes"]]
    lines = []
    if title:
        lines.append(_bold(title))
    lines.append(f"{'class':>7}  {'precision':<{width + 6}} {'recall':<{width + 6}}")
    for i, cls in enumerate(classes):
        p = _bar(report["precision"][i], width, "36")
        r = _bar(report["recall"][i], width, "35")
        lines.append(f"{cls:>7}  {p} {r}")
    return "\n".join(lines)
