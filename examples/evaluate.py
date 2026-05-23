#!/usr/bin/env python3
"""Evalúa el modelo entrenado en examples/output sobre data/test.txt."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", type=Path, default=Path("data/test.txt"))
    parser.add_argument("--model", type=Path, default=Path("output/risk_classifier.ftz"))
    return parser.parse_args()


def resolve_model(path: Path) -> Path:
    if path.exists():
        return path
    alt = path.with_suffix(".bin")
    if alt.exists():
        return alt
    raise SystemExit(f"Modelo no encontrado: {path} (ejecuta primero train.py)")


def main() -> None:
    args = parse_args()

    try:
        import fasttext
    except ImportError as exc:
        raise SystemExit("Instala dependencias: pip install -e '../.[ml]'") from exc

    from fasttext_compat import patch_fasttext_numpy2

    patch_fasttext_numpy2()

    model_path = resolve_model(args.model)
    model = fasttext.load_model(str(model_path))
    print(f"Modelo cargado: {model_path}\n")

    tp: dict[str, int] = defaultdict(int)
    fp: dict[str, int] = defaultdict(int)
    fn: dict[str, int] = defaultdict(int)
    labels_seen: set[str] = set()

    for line in args.test.read_text().splitlines():
        line = line.strip()
        if not line or not line.startswith("__label__"):
            continue
        true_label = line.split(" ", 1)[0].replace("__label__", "")
        text = line.split(" ", 1)[1]
        pred_label = model.predict(text.replace("\n", " "), k=1)[0][0].replace("__label__", "")

        labels_seen.add(true_label)
        labels_seen.add(pred_label)

        if pred_label == true_label:
            tp[true_label] += 1
        else:
            fn[true_label] += 1
            fp[pred_label] += 1

    print(f"{'Etiqueta':<18} {'Prec':>8} {'Recall':>8} {'F1':>8} {'Support':>8}")
    print("-" * 54)

    f1_scores = []
    for label in sorted(labels_seen):
        precision = tp[label] / (tp[label] + fp[label]) if (tp[label] + fp[label]) else 0.0
        recall = tp[label] / (tp[label] + fn[label]) if (tp[label] + fn[label]) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        support = tp[label] + fn[label]
        if support:
            f1_scores.append(f1)
        print(f"{label:<18} {precision:>8.3f} {recall:>8.3f} {f1:>8.3f} {support:>8}")

    if f1_scores:
        print("-" * 54)
        print(f"{'Macro-F1':<18} {'':>8} {'':>8} {sum(f1_scores)/len(f1_scores):>8.3f}")


if __name__ == "__main__":
    main()
