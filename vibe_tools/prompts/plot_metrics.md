Render a chart directly in the conversation from a data file. Use it whenever
the user wants to see data or training progress visualized: after (or during)
a model training run, or for any tabular file.

Five kinds:
- `line` (default): braille line curves from a JSONL stream (one flat JSON
  object per line, e.g. `{"epoch": 3, "loss": 0.4, "accuracy": 0.88}`) or a
  CSV file with a header. Numeric keys are auto-detected; use `x`/`y` to pick
  specific columns.
- `scatter`: same inputs as `line`, drawn as points — use for raw data
  exploration (feature vs feature, feature vs target).
- `hist`: distribution of a single column; pass the column name in `y`.
- `heatmap`: a JSON file `{"title": str, "labels": [...], "matrix": [[...]]}`
  (e.g. a confusion matrix).
- `report`: a JSON file `{"classes": [...], "precision": [...], "recall": [...]}`
  rendered as per-class precision/recall bars.

The rendered chart is displayed to the user automatically. When summarizing,
do not repeat the full chart; comment on what it shows (trend, convergence,
anomalies, weakest classes).

For live training visualization: call this tool again after new epochs are
appended to the stream — each call renders the latest state of the file.
