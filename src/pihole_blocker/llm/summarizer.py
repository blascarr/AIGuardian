from __future__ import annotations

"""LLM opcional fuera del camino crítico: resúmenes y explicaciones para el panel."""


class IncidentSummarizer:
    """Qwen2.5-0.5B o similar vía llama-cpp. Solo en background."""

    def __init__(self, model_path: str, enabled: bool = False) -> None:
        self.enabled = enabled
        self.model_path = model_path
        self._llm = None

    def _ensure_loaded(self) -> None:
        if not self.enabled or self._llm is not None:
            return
        try:
            from llama_cpp import Llama  # type: ignore

            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=2048,
                n_threads=2,
                verbose=False,
            )
        except Exception:
            self._llm = None
            self.enabled = False

    def summarize_incidents(self, incidents: list[dict]) -> str:
        if not self.enabled or not incidents:
            return self._fallback_summary(incidents)

        self._ensure_loaded()
        if self._llm is None:
            return self._fallback_summary(incidents)

        prompt = self._build_prompt(incidents)
        try:
            out = self._llm.create_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un asistente de seguridad doméstica. "
                            "Resume incidentes DNS en español, sin inventar datos."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=256,
                temperature=0.2,
            )
            return out["choices"][0]["message"]["content"].strip()
        except Exception:
            return self._fallback_summary(incidents)

    @staticmethod
    def _build_prompt(incidents: list[dict]) -> str:
        lines = [
            f"- {i['hostname']} ({i['risk_label']}, score={i['risk_score']:.2f})"
            for i in incidents[:10]
        ]
        return "Resume estos incidentes DNS pendientes:\n" + "\n".join(lines)

    @staticmethod
    def _fallback_summary(incidents: list[dict]) -> str:
        if not incidents:
            return "No hay incidentes recientes."
        pending = sum(1 for i in incidents if not i.get("reviewed"))
        return f"{len(incidents)} incidentes recientes, {pending} pendientes de revisión."
