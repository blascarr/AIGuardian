#!/usr/bin/env python3
"""Genera corpus sintético de ejemplo para entrenamiento fastText."""

from __future__ import annotations

import random
from pathlib import Path

LABELS = ("safe", "suspicious", "abusive", "grooming_risk")

SAFE = [
    "google.com",
    "wikipedia.org",
    "edu.es",
    "bbc.com",
    "elpais.com",
    "python.org",
    "github.com",
    "microsoft.com",
    "apple.com",
    "cloudflare.com",
    "ubuntu.com",
    "khanacademy.org",
    "nationalgeographic.com",
    "gob.es",
    "mapfre.es salud informacion",
    "wikipedia articulo historia roma",
    "universidad complutense matricula",
    "rtve noticias espana",
    "stackoverflow.com python fastapi",
    "mozilla.org firefox download",
]

SUSPICIOUS = [
    "free-prize-now.xyz",
    "click-here-win.top",
    "urgent-verify-account.click",
    "crypto-double-money.buzz",
    "login-secure-update.loan",
    "bank-alert-{n}.xyz",
    "you-won-lottery-{n}.top",
    "verify-paypal-{n}.cam",
    "download-flash-player-{n}.rest",
    "security-check-required-{n}.gq",
    "premio-gratis-gana-{n}.xyz",
    "actualiza-tu-cuenta-{n}.top",
    "oferta-exclusiva-hoy-{n}.click",
]

ABUSIVE = [
    "insultos-gratis-{n}.example",
    "odio-directo-foro-{n}.local",
    "pagina-amezando-{n}.test",
    "foro-anonimo-agresivo-{n}.site",
    "comentarios-toxic-{n}.example",
    "grupo-discordia-{n}.local",
    "chat-insultos-{n}.test",
    "mensaje-ofensivo-{n}.example",
    "titulo odio violento foro {n}",
    "url grupo acoso escolar {n}",
]

GROOMING = [
    "chat-secreto-no-digas-{n}.example",
    "encuentro-solo-sin-padres-{n}.test",
    "envia-foto-privada-{n}.local",
    "mensaje no le digas a nadie {n}",
    "quedamos solo tu y yo {n}",
    "borra-este-chat-{n}.example",
    "video-privado-menor-{n}.test",
    "regalo-secreto-amigo-{n}.local",
    "confia en mi no se lo cuentes {n}",
    "foto sin ropa privado chat {n}",
]


def expand(templates: list[str], n_variants: int = 20) -> list[str]:
    lines: list[str] = []
    for tpl in templates:
        if "{n}" in tpl:
            for i in range(n_variants):
                lines.append(tpl.replace("{n}", str(i + 1)))
        else:
            lines.append(tpl)
    return lines


def to_fasttext(label: str, texts: list[str]) -> list[str]:
    return [f"__label__{label} {t}" for t in texts]


def build_corpus() -> dict[str, list[str]]:
    return {
        "safe": to_fasttext("safe", expand(SAFE, n_variants=20)),
        "suspicious": to_fasttext("suspicious", expand(SUSPICIOUS, n_variants=20)),
        "abusive": to_fasttext("abusive", expand(ABUSIVE, n_variants=20)),
        "grooming_risk": to_fasttext("grooming_risk", expand(GROOMING, n_variants=20)),
    }


def split_corpus(
    corpus: dict[str, list[str]], seed: int = 42
) -> tuple[list[str], list[str], list[str]]:
    random.seed(seed)
    train, val, test = [], [], []
    for lines in corpus.values():
        shuffled = lines.copy()
        random.shuffle(shuffled)
        n = len(shuffled)
        n_test = max(5, n // 10)
        n_val = max(5, n // 10)
        test.extend(shuffled[:n_test])
        val.extend(shuffled[n_test : n_test + n_val])
        train.extend(shuffled[n_test + n_val :])
    random.shuffle(train)
    random.shuffle(val)
    random.shuffle(test)
    return train, val, test


def write_splits(data_dir: Path) -> dict[str, int]:
    data_dir.mkdir(parents=True, exist_ok=True)
    train, val, test = split_corpus(build_corpus())
    paths = {
        "train.txt": train,
        "val.txt": val,
        "test.txt": test,
    }
    counts = {}
    for name, lines in paths.items():
        path = data_dir / name
        path.write_text("\n".join(lines) + "\n")
        counts[name] = len(lines)
    return counts


def main() -> None:
    data_dir = Path(__file__).parent / "data"
    counts = write_splits(data_dir)
    print("Corpus generado en examples/data/:")
    for name, n in counts.items():
        print(f"  {name}: {n} muestras")


if __name__ == "__main__":
    main()
