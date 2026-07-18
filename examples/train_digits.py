"""Train a small MLP on sklearn digits, streaming per-epoch metrics as JSON lines.

Writes into --out-dir:
  metrics.jsonl    one {"epoch", "loss", "accuracy"} object per epoch (flushed live)
  confusion.json   {"title", "labels", "matrix"}
  report.json      {"title", "classes", "precision", "recall"}

Watch it live from another terminal (or a backgrounded Vibe tool call):
  vibe-plot runs/digits/metrics.jsonl --follow --idle-timeout 5
"""

import argparse
import json
import time
import warnings
from pathlib import Path

from sklearn.datasets import load_digits
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore", category=ConvergenceWarning)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--out-dir", default="runs/digits")
    ap.add_argument("--delay", type=float, default=0.15,
                    help="pause between epochs so the live plot is watchable")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    metrics_path = out / "metrics.jsonl"
    metrics_path.write_text("")

    X, y = load_digits(return_X_y=True)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y)
    scaler = StandardScaler().fit(X_train)
    X_train, X_test = scaler.transform(X_train), scaler.transform(X_test)

    clf = MLPClassifier(hidden_layer_sizes=(64,), max_iter=1, warm_start=True,
                        random_state=42)

    with metrics_path.open("a") as f:
        for epoch in range(1, args.epochs + 1):
            clf.fit(X_train, y_train)  # one pass: max_iter=1 + warm_start
            row = {"epoch": epoch,
                   "loss": round(clf.loss_, 4),
                   "accuracy": round(clf.score(X_test, y_test), 4)}
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(json.dumps(row), flush=True)
            time.sleep(args.delay)

    pred = clf.predict(X_test)
    (out / "confusion.json").write_text(json.dumps({
        "title": "Confusion matrix - digits test set",
        "labels": [str(c) for c in clf.classes_],
        "matrix": confusion_matrix(y_test, pred).tolist(),
    }))
    precision, recall, _, _ = precision_recall_fscore_support(y_test, pred)
    (out / "report.json").write_text(json.dumps({
        "title": "Per-class precision / recall",
        "classes": [str(c) for c in clf.classes_],
        "precision": [round(float(p), 4) for p in precision],
        "recall": [round(float(r), 4) for r in recall],
    }))
    final_acc = clf.score(X_test, y_test)
    with (out.parent / "index.jsonl").open("a") as idx:
        idx.write(json.dumps({
            "run": out.name, "backend": "sklearn", "epochs": args.epochs,
            "final_loss": round(clf.loss_, 4), "final_accuracy": round(final_acc, 4),
        }) + "\n")
    print(f"done: test accuracy {final_acc:.4f} - artifacts in {out}/")


if __name__ == "__main__":
    main()
