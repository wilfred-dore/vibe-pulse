Render a chart directly in the conversation from a data file. Use it whenever
the user wants to see data or training progress visualized: after (or during)
a model training run, or for any tabular file.

Five kinds:
- `line` (default): braille line curves from a JSONL stream (one flat JSON
  object per line, e.g. `{"epoch": 3, "loss": 0.4, "accuracy": 0.88}`), a
  CSV file with a header, an Excel spreadsheet (.xlsx), or a SQLite database
  (.sqlite/.db — pass a custom SELECT via the CLI `--sql`). Numeric keys are
  auto-detected; use `x`/`y` to pick specific columns.
- `scatter`: same inputs as `line`, drawn as points — use for raw data
  exploration (feature vs feature, feature vs target).
- `hist`: distribution of a single column; pass the column name in `y`.
- `bar`: horizontal bar chart for categorical data; `x` = label column,
  `y` = value column (e.g. cities vs temperature, classes vs count).
- `heatmap`: a JSON file `{"title": str, "labels": [...], "matrix": [[...]]}`
  (e.g. a confusion matrix).
- `report`: a JSON file `{"classes": [...], "precision": [...], "recall": [...]}`
  rendered as per-class precision/recall bars.
- `compare`: overlay one metric (`y`, default `loss`) across several training
  runs — pass 2+ comma-separated JSONL paths in `source`, e.g.
  `source="runs/a/metrics.jsonl,runs/b/metrics.jsonl"`. Use it to compare
  experiments (W&B-style run comparison, in the terminal).
- `diagram`: render a PlantUML source file (.puml) as an ASCII diagram —
  sequence, class, component, state diagrams. Write the .puml file first,
  then call this. Great for explaining architectures without leaving the
  terminal.

The rendered chart is displayed to the user automatically. When summarizing,
do not repeat the full chart; comment on what it shows (trend, convergence,
anomalies, weakest classes).

For live training visualization: call this tool again after new epochs are
appended to the stream — each call renders the latest state of the file.
