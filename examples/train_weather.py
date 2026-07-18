"""Train a temperature forecaster on Paris weather history (Open-Meteo data)
and predict tomorrow's max temperature.

Features per day: previous 7 days of tmax, yesterday's tmin, day-of-year
seasonality (sin/cos). Target: today's tmax.

Writes into --out-dir:
  metrics.jsonl         {"epoch", "loss", "mae"} per epoch (flushed live)
  pred_vs_actual.jsonl  {"day", "actual", "predicted"} on the test window
  forecast.json         {"date", "predicted_tmax"}

Watch live:   vibe-plot runs/weather/metrics.jsonl --follow --idle-timeout 5
Then overlay: vibe-plot runs/weather/pred_vs_actual.jsonl --x day --y actual,predicted
"""

import argparse
import csv
import json
import math
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import torch

LAGS = 7
TEST_DAYS = 60
DATA = Path(__file__).resolve().parents[1] / "data" / "paris_history.csv"


def load_history():
    with DATA.open() as f:
        return [(r["date"], float(r["tmax"]), float(r["tmin"]))
                for r in csv.DictReader(f)]


def day_of_year_feats(d: date):
    angle = 2 * math.pi * d.timetuple().tm_yday / 365.25
    return [math.sin(angle), math.cos(angle)]


def build_dataset(rows):
    X, y = [], []
    for i in range(LAGS, len(rows)):
        d = date.fromisoformat(rows[i][0])
        lags = [rows[i - k][1] for k in range(1, LAGS + 1)]
        X.append(lags + [rows[i - 1][2]] + day_of_year_feats(d))
        y.append(rows[i][1])
    return torch.tensor(X), torch.tensor(y).unsqueeze(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=200)
    ap.add_argument("--out-dir", default="runs/weather")
    ap.add_argument("--delay", type=float, default=0.1)
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    metrics_path = out / "metrics.jsonl"
    metrics_path.write_text("")

    rows = load_history()
    X, y = build_dataset(rows)
    Xtr, ytr = X[:-TEST_DAYS], y[:-TEST_DAYS]
    Xte, yte = X[-TEST_DAYS:], y[-TEST_DAYS:]
    mean, std = Xtr.mean(0), Xtr.std(0).clamp_min(1e-6)
    Xtr, Xte = (Xtr - mean) / std, (Xte - mean) / std
    ymean, ystd = ytr.mean(), ytr.std().clamp_min(1e-6)
    ytr_n = (ytr - ymean) / ystd

    torch.manual_seed(42)
    model = torch.nn.Sequential(
        torch.nn.Linear(X.shape[1], 48), torch.nn.ReLU(), torch.nn.Linear(48, 1))
    opt = torch.optim.Adam(model.parameters(), lr=5e-3)

    with metrics_path.open("a") as f:
        for epoch in range(1, args.epochs + 1):
            model.train()
            opt.zero_grad()
            loss = torch.nn.functional.mse_loss(model(Xtr), ytr_n)
            loss.backward()
            opt.step()
            model.eval()
            with torch.no_grad():
                mae = (model(Xte) * ystd + ymean - yte).abs().mean().item()
            row = {"epoch": epoch, "loss": round(loss.item(), 3),
                   "mae": round(mae, 3)}
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(json.dumps(row), flush=True)
            time.sleep(args.delay)

    with torch.no_grad():
        pred = (model(Xte) * ystd + ymean).squeeze(1)
    with (out / "pred_vs_actual.jsonl").open("w") as f:
        for i in range(TEST_DAYS):
            f.write(json.dumps({
                "day": i - TEST_DAYS + 1,
                "actual": round(yte[i].item(), 1),
                "predicted": round(pred[i].item(), 1),
            }) + "\n")

    # forecast tomorrow from the freshest actuals (falls back to history tail)
    recent = [(r[0], r[1], r[2]) for r in rows]
    try:
        url = ("https://api.open-meteo.com/v1/forecast?latitude=48.8566"
               "&longitude=2.3522&daily=temperature_2m_max,temperature_2m_min"
               f"&past_days={LAGS + 1}&forecast_days=1&timezone=Europe%2FParis")
        d = json.load(urllib.request.urlopen(url, timeout=15))["daily"]
        recent = list(zip(d["time"], d["temperature_2m_max"],
                          d["temperature_2m_min"]))  # ends today
    except Exception:
        pass
    tomorrow = date.fromisoformat(recent[-1][0]) + timedelta(days=1)
    feats = ([recent[-k][1] for k in range(1, LAGS + 1)]
             + [recent[-1][2]] + day_of_year_feats(tomorrow))
    x = (torch.tensor([feats]) - mean) / std
    with torch.no_grad():
        forecast = (model(x) * ystd + ymean).item()
    (out / "forecast.json").write_text(json.dumps(
        {"date": tomorrow.isoformat(), "predicted_tmax": round(forecast, 1)}))

    with (out.parent / "index.jsonl").open("a") as idx:
        idx.write(json.dumps({
            "run": out.name, "backend": "torch", "epochs": args.epochs,
            "final_loss": round(loss.item(), 3), "final_mae": round(mae, 3),
        }) + "\n")
    print(f"test MAE: {mae:.2f} °C over the last {TEST_DAYS} days")
    print(f"forecast for {tomorrow}: {forecast:.1f} °C max in Paris")


if __name__ == "__main__":
    main()
