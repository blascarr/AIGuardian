from __future__ import annotations

from datetime import datetime, timezone

import httpx

from pihole_blocker.collectors.base import DNSCollector, DNSEvent
from pihole_blocker.config import PiHoleConfig


class PiHoleCollector(DNSCollector):
    """Usa la API REST de la instancia instalada (autenticación por SID)."""

    def __init__(self, config: PiHoleConfig) -> None:
        self.config = config
        self._client = httpx.AsyncClient(
            base_url=config.url.rstrip("/"),
            timeout=15.0,
        )

    async def fetch_since(self, cursor: str, limit: int) -> tuple[list[DNSEvent], str]:
        if not self.config.session_id:
            return [], cursor

        # Endpoint típico v6: consultar docs locales de tu instancia
        response = await self._client.get(
            "/api/queries",
            params={"sid": self.config.session_id, "length": limit},
        )
        response.raise_for_status()
        payload = response.json()

        records = payload.get("queries", payload.get("data", []))
        events: list[DNSEvent] = []
        last_id = cursor

        for entry in records:
            entry_id = str(entry.get("id", entry.get("time", "")))
            if cursor and entry_id <= cursor:
                continue

            ts = self._parse_timestamp(entry.get("time", entry.get("timestamp")))
            hostname = (entry.get("domain") or entry.get("query") or "").rstrip(".")
            client_ip = entry.get("client") or entry.get("client_ip") or ""
            qtype = entry.get("type") or entry.get("query_type")
            status = entry.get("status") or entry.get("action")

            external_id = f"pihole:{entry_id}:{client_ip}:{hostname}"
            events.append(
                DNSEvent(
                    external_id=external_id,
                    timestamp=ts,
                    client_ip=client_ip,
                    hostname=hostname,
                    query_type=qtype,
                    status=status,
                    raw=entry,
                )
            )
            last_id = entry_id

        return events, last_id or cursor

    @staticmethod
    def _parse_timestamp(value) -> str:
        if value is None:
            return datetime.now(timezone.utc).isoformat()
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).isoformat()
        except ValueError:
            return str(value)

    async def close(self) -> None:
        await self._client.aclose()
