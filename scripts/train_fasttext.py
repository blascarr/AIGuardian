#!/usr/bin/env python3
"""Entrena un clasificador fastText de ejemplo para el pipeline ligero."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_sample_corpus(out_path: Path) -> None:
    samples = [
        ("__label__safe google.com",),
        ("__label__safe wikipedia.org",),
        ("__label__safe edu.es",),
        ("__label__suspicious free-prize.xyz",),
        ("__label__suspicious click-here-now.top",),
        ("__label__abusive insultos-gratis.example",),
        ("__label__grooming_risk chat-secreto-no-digas.example",),
    ]
    lines = [s[0] for s in samples]
    out_path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="models/risk_classifier.ftz")
    parser.add_argument("--quantize", action="store_true", default=True)
    args = parser.parse_args()

    try:
        import fasttext
    except ImportError as exc:
        raise SystemExit("Instala dependencias ML: pip install -e '.[ml]'") from exc

    base = Path(__file__).resolve().parents[1]
    train_file = base / "data" / "fasttext_train.txt"
    train_file.parent.mkdir(parents=True, exist_ok=True)
    build_sample_corpus(train_file)

    model = fasttext.train_supervised(
        input=str(train_file),
        epoch=25,
        lr=0.5,
        wordNgrams=2,
        minCount=1,
    )

    out = base / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(out.with_suffix(".bin")))

    if args.quantize:
        try:
            model.quantize(input=str(train_file), retrain=True, epoch=5, cutoff=1)
            model.save_model(str(out))
            print(f"Modelo cuantizado: {out}")
        except ValueError as exc:
            if "too small for quantization" in str(exc):
                bin_out = out.with_suffix(".bin")
                model.save_model(str(bin_out))
                print(
                    f"Corpus demasiado pequeño para cuantizar; "
                    f"guardado sin comprimir: {bin_out}"
                )
            else:
                raise
    else:
        model.save_model(str(out))
        print(f"Modelo guardado: {out}")


if __name__ == "__main__":
    main()
