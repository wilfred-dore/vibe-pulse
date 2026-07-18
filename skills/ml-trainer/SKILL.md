---
name: ml-trainer
description: Train an ML model and watch it live in the terminal with vibe-plot (loss/accuracy curves, confusion-matrix heatmap, precision/recall bars). Use whenever the user asks to train, fit, or evaluate a model, or to visualize training progress or tabular data.
---

# ml-trainer

Train a model and show training live in the terminal using `vibe-plot`
(provided by the vibe-pulse project; run as `uv run vibe-plot ...` from the
project root).

## Workflow

1. **Inspect the dataset** the user points at (shape, dtypes, target column).
   If none is given, use `examples/train_digits.py` (sklearn digits, trains in
   seconds).
2. **Write or adapt a training script** that appends one JSON object per epoch
   to `runs/<name>/metrics.jsonl`, flushed after every line:
   `{"epoch": 1, "loss": 2.13, "accuracy": 0.34}`
   Any numeric keys work — vibe-plot auto-detects series. Keep total runtime
   under ~60 s unless the user asks for a full run.
3. **Run training in the background**, then attach the live plot in the
   foreground so the user sees the curves draw themselves:
   `uv run vibe-plot runs/<name>/metrics.jsonl --follow --idle-timeout 5 --title "<run name>"`
4. **After training, render the final report.** If the `plot_metrics` tool is
   available, prefer it (charts render directly in the conversation):
   `plot_metrics(source="runs/<name>/metrics.jsonl", kind="line")`, then
   `kind="heatmap"` on `confusion.json` and `kind="report"` on `report.json`.
   Otherwise use the CLI:
   - `uv run vibe-plot runs/<name>/confusion.json --heatmap`
   - `uv run vibe-plot runs/<name>/report.json --report`
5. **Summarize**: final metrics, best epoch, and anything anomalous
   (divergence, plateau, overfitting gap).

## File conventions

- Metrics stream: JSON lines, one flat object per epoch.
- Confusion matrix: `{"title": str, "labels": [str], "matrix": [[int]]}`
- Report: `{"title": str, "classes": [str], "precision": [float], "recall": [float]}`

## Generic data viz (no training involved)

`vibe-plot` also renders any JSONL or CSV file directly:
`uv run vibe-plot data.csv --x date --y revenue,cost`
