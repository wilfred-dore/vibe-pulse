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

## Scene 2 — Train a forecaster on that data, live (90 s, the wow moment)

Right terminal (start it first, it waits for data):

    uv run vibe-plot runs/weather/metrics.jsonl --follow --idle-timeout 8 --title "Paris tmax forecaster - live"

In Vibe (left):
> train a temperature forecaster on the Paris history (examples/train_weather.py) and stream the training

Loss + MAE curves draw themselves epoch by epoch on the right while Vibe
works on the left. When it finishes:

> so, what's tomorrow's max temperature in Paris?

(Vibe reads `runs/weather/forecast.json` → e.g. "28.7 °C — the heatwave
breaks tomorrow")

**Say:** "Same data, one prompt later: the agent trains a forecaster, the
terminal plots it live, and we get tomorrow's temperature. Jupyter and
TensorBoard never left their browser."

## Scene 3 — Results & MLOps in the conversation (45 s)

In Vibe:
> plot predicted vs actual for the weather run

(braille overlay of the two curves on the 60-day test window)

> now show the digits confusion matrix, and compare the sklearn vs torch runs on loss

(colored heatmap in the TUI + run comparison)

**Say:** "3 °C mean error with a tiny MLP — Météo-France can sleep. The
point is the workflow: tracking, comparison, agent-driven sweeps. W&B needs
a server and a browser; we do it in the terminal, driven by the agent."

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
