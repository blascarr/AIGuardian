from pihole_blocker.pipeline.heuristics import HeuristicEngine
from pihole_blocker.config import HeuristicsConfig
from pathlib import Path


def test_heuristic_blocklist_match():
    base = Path(__file__).resolve().parents[1]
    engine = HeuristicEngine(HeuristicsConfig(), base)
    result = engine.evaluate("malware.example.com")
    assert result.matched
    assert result.category == "malware"
    assert result.score >= 0.9


def test_heuristic_safe_domain():
    base = Path(__file__).resolve().parents[1]
    engine = HeuristicEngine(HeuristicsConfig(), base)
    result = engine.evaluate("google.com")
    assert not result.matched
