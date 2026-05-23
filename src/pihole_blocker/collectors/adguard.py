from __future__ import annotations

from datetime import datetime, timezone

import httpx

from pihole_blocker.collectors.base import DNSCollector, DNSEvent
from pihole_blocker.config import AdGuardConfig


class AdGuardCollector(DNSCollector):
    """Fuente primaria: GET /control/querylog (OpenAPI AdGuard Home)."""

    def __init__(self, config: AdGuardConfig) -> None:
        self.config = config
        self._client = httpx.AsyncClient(
            base_url=config.url.rstrip("/"),
            auth=(config.username, config.password),
            timeout=15.0,
        )

    async def fetch_since(self, cursor: str, limit: int) -> tuple[list[DNSEvent], str]:
        params: dict[str, str | int] = {"limit": limit}
        if cursor:
            params["older_than"] = cursor

        response = await self._client.get("/control/querylog", params=params)
        response.raise_for_status()
        payload = response.json()

        entries = payload.get("data", [])
        events: list[DNSEvent] = []
        new_cursor = cursor

        for entry in entries:
            ts = self._parse_timestamp(entry.get("time", ""))
            hostname = entry.get("question", {}).get("name", "").rstrip(".")
            client_ip = entry.get("client", "")
            qtype = entry.get("question", {}).get("type", "")
            status = entry.get("reason", "") or entry.get("status", "")

            external_id = f"adguard:{ts}:{client_ip}:{hostname}:{qtype}"
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
            new_cursor = entry.get("time", new_cursor)

        return events, new_cursor

    @staticmethod
    def _parse_timestamp(value: str) -> str:
        if not value:
            return datetime.now(timezone.utc).isoformat()
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
        except ValueError:
            return value

    async def close(self) -> None:
        await self._client.aclose()
