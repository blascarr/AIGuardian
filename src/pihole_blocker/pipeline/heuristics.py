from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pihole_blocker.config import HeuristicsConfig


@dataclass
class HeuristicResult:
    matched: bool
    category: str | None
    score: float
    reason: str


class HeuristicEngine:
    """Prefiltro barato: listas, regex y patrones de dominio."""

    SUSPICIOUS_TLD = re.compile(
        r"\.(xyz|top|click|loan|work|gq|tk|ml|cf|ga|buzz|cam|rest)$",
        re.IGNORECASE,
    )
    ADULT_KEYWORDS = re.compile(
        r"(porn|xxx|adult|escort|webcam|onlyfans|xnxx|xvideos)",
        re.IGNORECASE,
    )
    GROOMING_KEYWORDS = re.compile(
        r"(meet.?alone|send.?pic|dont.?tell|secreto|encuentro.?solo|foto.?priv)",
        re.IGNORECASE,
    )

    def __init__(self, config: HeuristicsConfig, base_path: Path) -> None:
        self.config = config
        self.blocklists = self._load_blocklists(base_path / config.blocklists_dir)

    def _load_blocklists(self, directory: Path) -> dict[str, set[str]]:
        lists: dict[str, set[str]] = {}
        if not directory.exists():
            return lists
        for path in directory.glob("*.txt"):
            category = path.stem
            entries = {
                line.strip().lower()
                for line in path.read_text().splitlines()
                if line.strip() and not line.startswith("#")
            }
            lists[category] = entries
        return lists

    def evaluate(self, text: str) -> HeuristicResult:
        normalized = text.lower().strip()
        hostname = normalized.split("/")[0]

        for category, entries in self.blocklists.items():
            if hostname in entries or any(hostname.endswith(f".{e}") for e in entries):
                score = 1.0 if category in self.config.hard_block_categories else 0.9
                return HeuristicResult(
                    matched=True,
                    category=category,
                    score=score,
                    reason=f"blocklist:{category}",
                )

        if self.ADULT_KEYWORDS.search(normalized):
            return HeuristicResult(
                matched=True,
                category="adult",
                score=0.85,
                reason="keyword:adult",
            )

        if self.GROOMING_KEYWORDS.search(normalized):
            return HeuristicResult(
                matched=True,
                category="grooming_risk",
                score=0.95,
                reason="keyword:grooming",
            )

        if self.SUSPICIOUS_TLD.search(hostname):
            return HeuristicResult(
                matched=True,
                category="suspicious_tld",
                score=0.55,
                reason="tld:suspicious",
            )

        return HeuristicResult(matched=False, category=None, score=0.0, reason="none")
