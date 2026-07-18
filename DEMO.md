# Demo script — Vibe Pulse (5 min pitch / video)

Setup before recording: fresh `vibe` session in `~/Projects/vibe_pulse`,
a second terminal on the right half of the screen, font large enough to read
braille. Dark theme.

## Scene 1 — Any data, in the terminal (30 s)

Topical hook: the July 2026 heatwave, live from Open-Meteo data.

In Vibe:
> plot a bar chart of data/france_tmax_7d.csv with x=city and y=tmax, title "Heatwave July 2026 (7-day max, °C)"

then:
> now plot data/paris_temps.csv, tmax and tmin

**Say:** "Vibe Work has charts in Canvas. The CLI had nothing — until now.
Any CSV, any JSONL, straight in the conversation."

## Scene 2 — Live ML training (90 s, the wow moment)

Right terminal (start it first, it waits for data):

    uv run vibe-plot runs/demo/metrics.jsonl --follow --idle-timeout 8 --title "MLP on digits - live"

In Vibe (left):
> train a model on the digits dataset with the ml-trainer skill, out-dir runs/demo, 40 epochs with a small delay between epochs

The curves draw themselves epoch by epoch on the right while Vibe works on
the left.

**Say:** "Data scientists leave the terminal for Jupyter or TensorBoard just
to see if a run converges. Not anymore: the agent trains, the terminal plots,
live."

## Scene 3 — Results & MLOps in the conversation (45 s)

In Vibe:
> show the confusion matrix and the per-class report

(colored heatmap + precision/recall bars appear in the TUI)

> compare the sklearn and torch runs on loss: runs/digits/metrics.jsonl vs runs/digits_torch/metrics.jsonl

**Say:** "Run tracking, run comparison, agent-driven sweeps — W&B needs a
server and a browser; we do it in the terminal, driven by the agent."

## Scene 4 — On-device + upstream (30 s)

Show `runs/digits_torch/aihub.json` and/or the AI Hub dashboard page.

**Say:** "And the model we just trained? Compiled and profiled on a real
Samsung Galaxy S24+ through Qualcomm AI Hub: 0.052 milliseconds per
inference, 24 MB peak memory. Real numbers, real silicon."

Optional flex (10 s): run `VIBE_ACTIVE_MODEL=qualcomm vibe` (or pick
"qualcomm" in the TUI model picker) — the CLI itself now talks to
Llama-3.1-8B served on Qualcomm Cloud AI 100.

**Say:** "Full Qualcomm loop: our model profiled on a Snapdragon phone, and
Vibe itself can run its inference on Qualcomm cloud silicon."

Show the draft PR: https://github.com/mistralai/mistral-vibe/pull/920

**Say:** "Everything works today through Vibe's official extension surfaces —
a skill and a native tool. And the core capability is PR-ready upstream,
built on render_braille: the primitive that animates Vibe's mascot gets its
first product feature."

## Closing line

"Vibe Pulse — the terminal is a first-class data science surface. Give your
agent eyes."
