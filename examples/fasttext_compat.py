"""Compatibilidad fastText + NumPy 2.x."""

from __future__ import annotations


def patch_fasttext_numpy2() -> None:
    """Evita ValueError en fasttext.FastText.predict con NumPy >= 2."""
    try:
        import numpy as np
        from fasttext.FastText import _FastText
    except ImportError:
        return

    if getattr(_FastText.predict, "_pihole_patched", False):
        return

    def predict(self, text, k=1, threshold=0.0, on_unicode_error="strict"):
        if isinstance(text, list):
            text = [entry + "\n" if not entry.endswith("\n") else entry for entry in text]
            all_labels, all_probs = self.f.multilinePredict(text, k, threshold, on_unicode_error)
            return all_labels, np.asarray(all_probs)

        entry = text.replace("\n", " ") if text.find("\n") != -1 else text
        if not entry.endswith("\n"):
            entry += "\n"
        predictions = self.f.predict(entry, k, threshold, on_unicode_error)
        if predictions:
            probs, labels = zip(*predictions)
        else:
            probs, labels = ([], ())
        return labels, np.asarray(probs)

    predict._pihole_patched = True  # type: ignore[attr-defined]
    _FastText.predict = predict
