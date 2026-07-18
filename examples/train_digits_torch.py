"""Train a tiny PyTorch MLP on digits, then compile + profile it on a real
Snapdragon device via Qualcomm AI Hub.

Same streaming conventions as train_digits.py (metrics.jsonl / confusion.json /
report.json), so every vibe-plot rendering works unchanged. Extra artifact:
  aihub.json   {"device", "compile_job", "profile_job", "latency_ms", ...}

Requires the aihub extra:  uv sync --extra aihub
and a configured token:    qai-hub configure --api_token <TOKEN>
"""

import argparse
import json
import time
from pathlib import Path

import torch
from sklearn.datasets import load_digits
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split


class DigitsMLP(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(64, 64), torch.nn.ReLU(), torch.nn.Linear(64, 10)
        )

    def forward(self, x):
        return self.net(x / 16.0)  # normalization baked in for on-device use


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--out-dir", default="runs/digits_torch")
    ap.add_argument("--delay", type=float, default=0.0)
    ap.add_argument("--device-name", default=None,
                    help="AI Hub device (default: newest Galaxy S / X Elite found)")
    ap.add_argument("--skip-aihub", action="store_true")
    ap.add_argument("--wait", action="store_true",
                    help="block until the profile job finishes and record latency")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    metrics_path = out / "metrics.jsonl"
    metrics_path.write_text("")

    X, y = load_digits(return_X_y=True)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y)
    Xtr = torch.tensor(X_train, dtype=torch.float32)
    Xte = torch.tensor(X_test, dtype=torch.float32)
    ytr = torch.tensor(y_train)
    yte = torch.tensor(y_test)

    torch.manual_seed(42)
    model = DigitsMLP()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = torch.nn.CrossEntropyLoss()

    with metrics_path.open("a") as f:
        for epoch in range(1, args.epochs + 1):
            model.train()
            opt.zero_grad()
            loss = loss_fn(model(Xtr), ytr)
            loss.backward()
            opt.step()
            model.eval()
            with torch.no_grad():
                acc = (model(Xte).argmax(1) == yte).float().mean().item()
            row = {"epoch": epoch, "loss": round(loss.item(), 4),
                   "accuracy": round(acc, 4)}
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(json.dumps(row), flush=True)
            time.sleep(args.delay)

    with torch.no_grad():
        pred = model(Xte).argmax(1).numpy()
    (out / "confusion.json").write_text(json.dumps({
        "title": "Confusion matrix - digits (torch)",
        "labels": [str(i) for i in range(10)],
        "matrix": confusion_matrix(y_test, pred).tolist(),
    }))
    precision, recall, _, _ = precision_recall_fscore_support(y_test, pred)
    (out / "report.json").write_text(json.dumps({
        "title": "Per-class precision / recall (torch)",
        "classes": [str(i) for i in range(10)],
        "precision": [round(float(p), 4) for p in precision],
        "recall": [round(float(r), 4) for r in recall],
    }))
    final_acc = float((pred == y_test).mean())
    with (out.parent / "index.jsonl").open("a") as idx:
        idx.write(json.dumps({
            "run": out.name, "backend": "torch", "epochs": args.epochs,
            "final_loss": round(loss.item(), 4), "final_accuracy": round(final_acc, 4),
        }) + "\n")
    print(f"trained: test accuracy {final_acc:.4f}")

    if args.skip_aihub:
        return

    import qai_hub as hub

    if args.device_name:
        device = hub.Device(args.device_name)
    else:
        names = [d.name for d in hub.get_devices()]
        device = None
        for wanted in ("Samsung Galaxy S24", "Samsung Galaxy S23",
                       "Snapdragon X Elite"):
            match = [n for n in names if wanted in n]
            if match:
                device = hub.Device(match[-1])
                break
        if device is None:
            device = hub.Device(names[-1])
    print(f"aihub target device: {device.name}", flush=True)

    traced = torch.jit.trace(model.eval(), torch.zeros(1, 64))
    compile_job = hub.submit_compile_job(
        model=traced, device=device, name="vibe-pulse-digits-mlp",
        input_specs={"x": (1, 64)},
    )
    print(f"compile job: {compile_job.url}", flush=True)
    target_model = compile_job.get_target_model()  # waits for compilation

    profile_job = hub.submit_profile_job(
        model=target_model, device=device, name="vibe-pulse-digits-mlp",
    )
    print(f"profile job: {profile_job.url}", flush=True)

    result = {"device": device.name,
              "compile_job": compile_job.url, "profile_job": profile_job.url}
    if args.wait:
        profile = profile_job.download_profile()  # waits for the device run
        summary = profile.get("execution_summary", {})
        result["inference_ms"] = summary.get("estimated_inference_time") and \
            summary["estimated_inference_time"] / 1000.0
        result["peak_memory_bytes"] = summary.get(
            "inference_memory_peak_range", [None, None])[1]
        print(f"on-device inference: {result['inference_ms']} ms "
              f"on {device.name}", flush=True)
    (out / "aihub.json").write_text(json.dumps(result, indent=2))
    print(f"artifacts in {out}/")


if __name__ == "__main__":
    main()
