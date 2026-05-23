from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ClassificationResult:
    label: str
    score: float
    stage: str
    details: str | None = None


class LightClassifier:
    """Capa 1: fastText (.ftz) o fallback heurístico si no hay modelo."""

    LABELS = ("safe", "suspicious", "abusive", "grooming_risk")

    def __init__(self, model_path: Path) -> None:
        self.model_path = model_path
        self._model = None
        self._load()

    def _load(self) -> None:
        path = self.model_path
        if not path.exists() and path.suffix == ".ftz":
            path = path.with_suffix(".bin")
        if not path.exists():
            return
        try:
            import fasttext  # type: ignore

            self._model = fasttext.load_model(str(path))
        except Exception:
            self._model = None

    def predict(self, text: str) -> ClassificationResult:
        if self._model is None:
            return ClassificationResult(
                label="safe",
                score=0.5,
                stage="light:fallback",
                details="Modelo fastText no disponible",
            )

        labels, scores = self._model.predict(text.replace("\n", " "), k=1)
        label = labels[0].replace("__label__", "")
        score = float(scores[0])
        return ClassificationResult(label=label, score=score, stage="light:fasttext")


class HeavyClassifier:
    """Capa 2: MobileBERT cuantizado vía ONNX Runtime (solo zona gris)."""

    LABELS = ("safe", "suspicious", "abusive", "grooming_risk")

    def __init__(self, model_path: Path) -> None:
        self.model_path = model_path
        self._session = None
        self._load()

    def _load(self) -> None:
        if not self.model_path.exists():
            return
        try:
            import onnxruntime as ort  # type: ignore

            self._session = ort.InferenceSession(
                str(self.model_path),
                providers=["CPUExecutionProvider"],
            )
        except Exception:
            self._session = None

    def predict(self, text: str) -> ClassificationResult:
        if self._session is None:
            return ClassificationResult(
                label="suspicious",
                score=0.5,
                stage="heavy:fallback",
                details="Modelo ONNX no disponible",
            )

        # Placeholder: sustituir por tokenización real del checkpoint exportado
        inputs = {inp.name: self._dummy_input(inp) for inp in self._session.get_inputs()}
        outputs = self._session.run(None, inputs)
        logits = outputs[0][0]
        idx = int(logits.argmax())
        score = float(self._softmax(logits)[idx])
        label = self.LABELS[min(idx, len(self.LABELS) - 1)]
        return ClassificationResult(label=label, score=score, stage="heavy:mobilebert")

    def _dummy_input(self, meta) -> object:
        import numpy as np

        shape = [1 if (d is None or isinstance(d, str)) else d for d in meta.shape]
        if meta.type == "tensor(int64)":
            return np.zeros(shape, dtype=np.int64)
        return np.zeros(shape, dtype=np.float32)

    @staticmethod
    def _softmax(x) -> list[float]:
        import numpy as np

        e = np.exp(x - np.max(x))
        return (e / e.sum()).tolist()


class RiskScorer:
    """Combina heurísticas + capas ML en puntuación final."""

    RISK_WEIGHTS = {
        "safe": 0.1,
        "suspicious": 0.6,
        "abusive": 0.85,
        "grooming_risk": 0.95,
        "malware": 1.0,
        "phishing": 1.0,
        "adult": 0.8,
        "grooming_risk_heuristic": 0.95,
        "suspicious_tld": 0.55,
    }

    @classmethod
    def score(cls, label: str, confidence: float) -> float:
        base = cls.RISK_WEIGHTS.get(label, 0.5)
        return min(1.0, base * confidence + (1 - confidence) * 0.2)
