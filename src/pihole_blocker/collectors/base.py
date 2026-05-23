from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DNSEvent:
    external_id: str
    timestamp: str
    client_ip: str
    hostname: str
    query_type: str | None
    status: str | None
    raw: dict


class DNSCollector(ABC):
    @abstractmethod
    async def fetch_since(self, cursor: str, limit: int) -> tuple[list[DNSEvent], str]:
        """Devuelve eventos nuevos y cursor actualizado."""
