from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass
class EventRecord:
    external_id: str
    timestamp: str
    client_ip: str
    hostname: str
    query_type: str | None
    status: str | None
    raw_source: str


@dataclass
class IncidentRecord:
    id: int
    event_id: int
    risk_score: float
    risk_label: str
    pipeline_stage: str
    explanation: str | None
    reviewed: bool
    hostname: str
    client_ip: str
    timestamp: str


class Repository:
    def __init__(self, db_path: Path, schema_path: Path) -> None:
        self.db_path = db_path
        self.schema_path = schema_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with self.connection() as conn:
            conn.executescript(self.schema_path.read_text())

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def get_cursor(self, key: str, default: str = "") -> str:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT value FROM pipeline_state WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else default

    def set_cursor(self, key: str, value: str) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_state (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def insert_event(self, event: EventRecord) -> int | None:
        with self.connection() as conn:
            try:
                cur = conn.execute(
                    """
                    INSERT INTO events
                    (external_id, timestamp, client_ip, hostname, query_type, status, raw_source)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.external_id,
                        event.timestamp,
                        event.client_ip,
                        event.hostname,
                        event.query_type,
                        event.status,
                        event.raw_source,
                    ),
                )
                return cur.lastrowid
            except sqlite3.IntegrityError:
                return None

    def create_incident(
        self,
        event_id: int,
        risk_score: float,
        risk_label: str,
        pipeline_stage: str,
        explanation: str | None = None,
    ) -> int:
        with self.connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO incidents
                (event_id, risk_score, risk_label, pipeline_stage, explanation)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event_id, risk_score, risk_label, pipeline_stage, explanation),
            )
            return cur.lastrowid

    def list_incidents(self, reviewed: bool | None = None, limit: int = 50) -> list[IncidentRecord]:
        query = """
            SELECT i.id, i.event_id, i.risk_score, i.risk_label, i.pipeline_stage,
                   i.explanation, i.reviewed, e.hostname, e.client_ip, e.timestamp
            FROM incidents i
            JOIN events e ON e.id = i.event_id
        """
        params: list = []
        if reviewed is not None:
            query += " WHERE i.reviewed = ?"
            params.append(1 if reviewed else 0)
        query += " ORDER BY i.created_at DESC LIMIT ?"
        params.append(limit)

        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                IncidentRecord(
                    id=row["id"],
                    event_id=row["event_id"],
                    risk_score=row["risk_score"],
                    risk_label=row["risk_label"],
                    pipeline_stage=row["pipeline_stage"],
                    explanation=row["explanation"],
                    reviewed=bool(row["reviewed"]),
                    hostname=row["hostname"],
                    client_ip=row["client_ip"],
                    timestamp=row["timestamp"],
                )
                for row in rows
            ]

    def add_feedback(self, incident_id: int, verdict: str, note: str | None = None) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO feedback (incident_id, verdict, note) VALUES (?, ?, ?)",
                (incident_id, verdict, note),
            )
            conn.execute(
                "UPDATE incidents SET reviewed = 1 WHERE id = ?",
                (incident_id,),
            )

    def stats(self) -> dict:
        with self.connection() as conn:
            events = conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"]
            incidents = conn.execute("SELECT COUNT(*) AS c FROM incidents").fetchone()["c"]
            pending = conn.execute(
                "SELECT COUNT(*) AS c FROM incidents WHERE reviewed = 0"
            ).fetchone()["c"]
            feedback = conn.execute("SELECT COUNT(*) AS c FROM feedback").fetchone()["c"]
            fp = conn.execute(
                "SELECT COUNT(*) AS c FROM feedback WHERE verdict = 'fp'"
            ).fetchone()["c"]
        return {
            "events": events,
            "incidents": incidents,
            "pending_review": pending,
            "feedback_total": feedback,
            "false_positives": fp,
        }
