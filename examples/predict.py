#!/usr/bin/env python3
"""Prueba rápida de inferencia con el modelo de examples/output."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("text", nargs="?", help="Texto o dominio a clasificar")
    parser.add_argument("--model", type=Path, default=Path("output/risk_classifier.ftz"))
    parser.add_argument("--top", type=int, default=3)
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
    text = args.text or " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    if not text:
        raise SystemExit("Uso: python predict.py 'google.com'")

    try:
        import fasttext
    except ImportError as exc:
        raise SystemExit("Instala dependencias: pip install -e '../.[ml]'") from exc

    from fasttext_compat import patch_fasttext_numpy2

    patch_fasttext_numpy2()

    model = fasttext.load_model(str(resolve_model(args.model)))
    labels, scores = model.predict(text.replace("\n", " "), k=args.top)

    print(f"Input: {text}\n")
    for label, score in zip(labels, scores):
        clean = label.replace("__label__", "")
        print(f"  {clean:<18} {score:.4f}")


if __name__ == "__main__":
    main()
