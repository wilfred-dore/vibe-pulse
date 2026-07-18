# Vibe Pulse

**Live ML training and data visualization in the terminal — built for [Mistral Vibe](https://github.com/mistralai/vibe).**

Vibe Work (web) can chart your data in Canvas. Vibe Code (CLI) — and every other
terminal coding agent — cannot. Data scientists who live in the terminal still
have to context-switch to Jupyter or TensorBoard just to see whether a training
run converges. Vibe Pulse closes that gap.

```
User: "train a model on digits and show me the curve"
  └─ Vibe (ml-trainer skill)
       ├─ writes/runs a training script → streams {"epoch", "loss", "accuracy"} as JSON lines
       ├─ vibe-plot --follow  → live braille curves, redrawn every epoch
       └─ vibe-plot --heatmap / --report → confusion matrix + precision/recall, in the terminal
```

## Components

- **`vibe-plot`** — a zero-config terminal plotter. Reads JSON lines or CSV,
  renders Unicode/braille line charts (live with `--follow`), ANSI heatmaps
  (`--heatmap`), and per-class precision/recall bars (`--report`). Works in any
  Unicode terminal; no GUI, no notebook, no browser.
- **`plot_metrics` native Vibe tool** — a first-class `BaseTool` implementation
  ([vibe_tools/plot_metrics.py](vibe_tools/plot_metrics.py)) loaded through
  Vibe's own tool discovery (`tool_paths`), rendering charts directly in the
  Vibe conversation. Drop-in compatible with `vibe/core/tools/builtins/` —
  PR-ready for upstream.
- **`ml-trainer` skill** — teaches Vibe the whole loop: inspect a dataset,
  generate a training script that streams metrics, attach the live plot, then
  render the final report.
- **`examples/train_digits.py`** — reference training script (sklearn digits,
  trains in seconds) that emits the metrics stream and final artifacts.

## Quickstart

```bash
uv sync

# terminal 1 — train (or let Vibe do it via the ml-trainer skill)
uv run python examples/train_digits.py --epochs 40

# terminal 2 — watch it live
uv run vibe-plot runs/digits/metrics.jsonl --follow --idle-timeout 5 --title "MLP on digits"

# after training
uv run vibe-plot runs/digits/confusion.json --heatmap
uv run vibe-plot runs/digits/report.json --report

# it is also a generic terminal data-viz tool
uv run vibe-plot any_file.csv --x date --y revenue,cost
```

## Use it from Mistral Vibe

Add the skill and the native tool to `~/.vibe/config.toml`:

```toml
skill_paths = ["/path/to/vibe_pulse/skills"]
tool_paths  = ["/path/to/vibe_pulse/vibe_tools"]
```

Then ask Vibe: *"train a model on the digits dataset and show me the training
live"*.

---

Built at the Mistral AI Vibe Hackathon — Paris, July 18, 2026.
