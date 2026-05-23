#!/usr/bin/env python3
"""Entrena un clasificador fastText de ejemplo para PiholeBlocker."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Entrenar clasificador fastText de ejemplo")
    parser.add_argument("--train", type=Path, default=Path("data/train.txt"))
    parser.add_argument("--val", type=Path, default=Path("data/val.txt"))
    parser.add_argument("--output", type=Path, default=Path("output/risk_classifier"))
    parser.add_argument("--epoch", type=int, default=50)
    parser.add_argument("--lr", type=float, default=0.5)
    parser.add_argument("--wordNgrams", type=int, default=2)
    parser.add_argument("--minCount", type=int, default=1)
    parser.add_argument("--no-quantize", action="store_true")
    return parser.parse_args()


def count_lines(path: Path) -> int:
    return sum(1 for line in path.read_text().splitlines() if line.strip())


def evaluate(model, path: Path) -> dict:
    if not path.exists():
        return {"samples": 0, "accuracy": 0.0}

    labels_all: list[str] = []
    correct = 0
    total = 0

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or not line.startswith("__label__"):
            continue
        parts = line.split(" ", 1)
        if len(parts) < 2:
            continue
        true_label = parts[0].replace("__label__", "")
        text = parts[1]
        pred_labels, _ = model.predict(text.replace("\n", " "), k=1)
        pred_label = pred_labels[0].replace("__label__", "")
        labels_all.append(true_label)
        if pred_label == true_label:
            correct += 1
        total += 1

    per_label: dict[str, dict[str, float]] = {}
    for label in sorted(set(labels_all)):
        tp = sum(
            1
            for line in path.read_text().splitlines()
            if line.strip().startswith(f"__label__{label}")
            and model.predict(line.split(" ", 1)[1], k=1)[0][0].replace("__label__", "") == label
        )
        support = sum(
            1 for line in path.read_text().splitlines() if line.strip().startswith(f"__label__{label}")
        )
        per_label[label] = {
            "recall": round(tp / support, 4) if support else 0.0,
            "support": support,
        }

    return {
        "samples": total,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "per_label_recall": per_label,
    }


def main() -> None:
    args = parse_args()

    try:
        import fasttext
    except ImportError as exc:
        raise SystemExit("Instala dependencias: pip install -e '../.[ml]'") from exc

    from fasttext_compat import patch_fasttext_numpy2

    patch_fasttext_numpy2()

    if not args.train.exists():
        data_script = Path(__file__).parent / "generate_sample_data.py"
        print(f"Corpus no encontrado. Generando datos de ejemplo...")
        import subprocess
        subprocess.run([sys.executable, str(data_script)], check=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    n_train = count_lines(args.train)
    print(f"Entrenando con {n_train} muestras desde {args.train}")

    model = fasttext.train_supervised(
        input=str(args.train),
        epoch=args.epoch,
        lr=args.lr,
        wordNgrams=args.wordNgrams,
        minCount=args.minCount,
        verbose=2,
    )

    val_metrics = evaluate(model, args.val)
    print(f"Validación: accuracy={val_metrics['accuracy']}, muestras={val_metrics['samples']}")

    bin_path = args.output.with_suffix(".bin")
    model.save_model(str(bin_path))
    print(f"Modelo base guardado: {bin_path}")

    final_path = bin_path
    if not args.no_quantize:
        try:
            model.quantize(input=str(args.train), retrain=True, epoch=5, cutoff=1)
            ftz_path = args.output.with_suffix(".ftz")
            model.save_model(str(ftz_path))
            final_path = ftz_path
            print(f"Modelo cuantizado: {ftz_path} ({ftz_path.stat().st_size / 1024:.1f} KB)")
        except ValueError as exc:
            if "too small for quantization" in str(exc):
                print(f"Cuantización omitida (corpus pequeño). Usar: {bin_path}")
            else:
                raise

    metrics_path = args.output.parent / "metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "train_samples": n_train,
                "val": val_metrics,
                "model_path": str(final_path),
                "hyperparameters": {
                    "epoch": args.epoch,
                    "lr": args.lr,
                    "wordNgrams": args.wordNgrams,
                    "minCount": args.minCount,
                },
            },
            indent=2,
        )
    )
    print(f"Métricas guardadas: {metrics_path}")


if __name__ == "__main__":
    main()
