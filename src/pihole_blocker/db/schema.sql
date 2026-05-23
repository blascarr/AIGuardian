CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT UNIQUE,
    timestamp TEXT NOT NULL,
    client_ip TEXT NOT NULL,
    hostname TEXT NOT NULL,
    query_type TEXT,
    status TEXT,
    raw_source TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_hostname ON events(hostname);

CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES events(id),
    risk_score REAL NOT NULL,
    risk_label TEXT NOT NULL,
    pipeline_stage TEXT NOT NULL,
    explanation TEXT,
    reviewed INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (event_id) REFERENCES events(id)
);

CREATE INDEX IF NOT EXISTS idx_incidents_reviewed ON incidents(reviewed);
CREATE INDEX IF NOT EXISTS idx_incidents_created ON incidents(created_at);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id INTEGER NOT NULL REFERENCES incidents(id),
    verdict TEXT NOT NULL CHECK (verdict IN ('tp', 'fp', 'ignore', 'allow_rule')),
    note TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (incident_id) REFERENCES incidents(id)
);

CREATE TABLE IF NOT EXISTS pipeline_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
