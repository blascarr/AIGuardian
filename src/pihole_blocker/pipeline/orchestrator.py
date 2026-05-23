from __future__ import annotations

from dataclasses import dataclass

from pihole_blocker.collectors.base import DNSEvent
from pihole_blocker.config import PipelineConfig
from pihole_blocker.db.repository import EventRecord, Repository
from pihole_blocker.pipeline.classifier import (
    ClassificationResult,
    HeavyClassifier,
    LightClassifier,
    RiskScorer,
)
from pihole_blocker.pipeline.heuristics import HeuristicEngine, HeuristicResult


@dataclass
class PipelineDecision:
    create_incident: bool
    risk_score: float
    risk_label: str
    stage: str
    explanation: str


class PipelineOrchestrator:
    """Flujo escalonado: heurística → ligero → pesado (zona gris) → incidente."""

    def __init__(
        self,
        repo: Repository,
        heuristics: HeuristicEngine,
        light: LightClassifier,
        heavy: HeavyClassifier,
        config: PipelineConfig,
    ) -> None:
        self.repo = repo
        self.heuristics = heuristics
        self.light = light
        self.heavy = heavy
        self.config = config

    def process(self, dns_event: DNSEvent) -> PipelineDecision | None:
        event_id = self.repo.insert_event(
            EventRecord(
                external_id=dns_event.external_id,
                timestamp=dns_event.timestamp,
                client_ip=dns_event.client_ip,
                hostname=dns_event.hostname,
                query_type=dns_event.query_type,
                status=dns_event.status,
                raw_source=str(dns_event.raw),
            )
        )
        if event_id is None:
            return None

        text = dns_event.hostname
        decision = self._classify(text)

        if decision.create_incident:
            self.repo.create_incident(
                event_id=event_id,
                risk_score=decision.risk_score,
                risk_label=decision.risk_label,
                pipeline_stage=decision.stage,
                explanation=decision.explanation,
            )
        return decision

    def _classify(self, text: str) -> PipelineDecision:
        heuristic: HeuristicResult = self.heuristics.evaluate(text)

        if heuristic.matched and heuristic.score >= self.config.light_classifier_threshold:
            label = heuristic.category or "suspicious"
            return PipelineDecision(
                create_incident=True,
                risk_score=heuristic.score,
                risk_label=label,
                stage="heuristic",
                explanation=heuristic.reason,
            )

        light_result: ClassificationResult = self.light.predict(text)
        light_score = RiskScorer.score(light_result.label, light_result.score)

        if light_score >= self.config.light_classifier_threshold:
            return PipelineDecision(
                create_incident=True,
                risk_score=light_score,
                risk_label=light_result.label,
                stage=light_result.stage,
                explanation=light_result.details,
            )

        in_gray_zone = (
            self.config.gray_zone_min
            <= light_result.score
            <= self.config.gray_zone_max
        )

        if in_gray_zone:
            heavy_result: ClassificationResult = self.heavy.predict(text)
            heavy_score = RiskScorer.score(heavy_result.label, heavy_result.score)
            if heavy_score >= self.config.heavy_classifier_threshold:
                return PipelineDecision(
                    create_incident=True,
                    risk_score=heavy_score,
                    risk_label=heavy_result.label,
                    stage=heavy_result.stage,
                    explanation=f"gray_zone light={light_result.score:.2f}",
                )

        if heuristic.matched:
            return PipelineDecision(
                create_incident=True,
                risk_score=heuristic.score,
                risk_label=heuristic.category or "suspicious",
                stage="heuristic:low_confidence",
                explanation=heuristic.reason,
            )

        return PipelineDecision(
            create_incident=False,
            risk_score=light_score,
            risk_label=light_result.label,
            stage="passed",
            explanation="below_threshold",
        )
