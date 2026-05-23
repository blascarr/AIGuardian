from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import uvicorn

from pihole_blocker.api.app import create_app
from pihole_blocker.collectors.adguard import AdGuardCollector
from pihole_blocker.collectors.pihole import PiHoleCollector
from pihole_blocker.config import Settings
from pihole_blocker.db.repository import Repository
from pihole_blocker.llm.summarizer import IncidentSummarizer
from pihole_blocker.pipeline.classifier import HeavyClassifier, LightClassifier
from pihole_blocker.pipeline.heuristics import HeuristicEngine
from pihole_blocker.pipeline.orchestrator import PipelineOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("pihole_blocker")

CURSOR_KEY = "dns_cursor"


class Daemon:
    def __init__(self, base_path: Path) -> None:
        settings = Settings(config_path=base_path / "config" / "config.yaml")
        self.config = settings.load()
        self.base_path = base_path

        schema = Path(__file__).resolve().parent / "db" / "schema.sql"
        db_path = settings.resolve(base_path, self.config.database.path)
        self.repo = Repository(db_path, schema)

        self.heuristics = HeuristicEngine(
            self.config.heuristics,
            base_path,
        )
        self.light = LightClassifier(
            settings.resolve(base_path, self.config.models.fasttext_path)
        )
        self.heavy = HeavyClassifier(
            settings.resolve(base_path, self.config.models.mobilebert_onnx_path)
        )
        self.pipeline = PipelineOrchestrator(
            self.repo,
            self.heuristics,
            self.light,
            self.heavy,
            self.config.pipeline,
        )
        self.summarizer = IncidentSummarizer(
            str(settings.resolve(base_path, self.config.models.llm_model_path)),
            enabled=self.config.models.llm_enabled,
        )

        if self.config.dns.provider == "adguard":
            self.collector = AdGuardCollector(self.config.dns.adguard)
        else:
            self.collector = PiHoleCollector(self.config.dns.pihole)

        self.app = create_app(self.config, self.repo, self.summarizer)
        self._running = False

    async def poll_loop(self) -> None:
        interval = self.config.dns.poll_interval_seconds
        batch = self.config.dns.batch_size
        logger.info("Iniciando poll DNS cada %ss (provider=%s)", interval, self.config.dns.provider)

        while self._running:
            cursor = self.repo.get_cursor(CURSOR_KEY)
            try:
                events, new_cursor = await self.collector.fetch_since(cursor, batch)
                incidents = 0
                for event in events:
                    decision = self.pipeline.process(event)
                    if decision and decision.create_incident:
                        incidents += 1
                if new_cursor and new_cursor != cursor:
                    self.repo.set_cursor(CURSOR_KEY, new_cursor)
                if events:
                    logger.info("Procesados %d eventos, %d incidentes", len(events), incidents)
            except Exception:
                logger.exception("Error en poll DNS")
            await asyncio.sleep(interval)

    async def run(self) -> None:
        self._running = True
        poll_task = asyncio.create_task(self.poll_loop())

        config = uvicorn.Config(
            self.app,
            host=self.config.api.host,
            port=self.config.api.port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        try:
            await server.serve()
        finally:
            self._running = False
            poll_task.cancel()
            await self.collector.close()


def main() -> None:
    base = Path(__file__).resolve().parents[2]
    daemon = Daemon(base)
    asyncio.run(daemon.run())


if __name__ == "__main__":
    main()
