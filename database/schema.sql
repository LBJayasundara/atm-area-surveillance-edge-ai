-- =============================================================================
-- ATM Surveillance SQLite Schema
-- =============================================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- Alerts table
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id        TEXT    UNIQUE NOT NULL,
    activity        TEXT    NOT NULL,
    activity_type   TEXT    NOT NULL,
    detected_object TEXT    NOT NULL DEFAULT '',
    confidence      REAL    NOT NULL DEFAULT 0,
    timestamp       TEXT    NOT NULL,
    location        TEXT    NOT NULL DEFAULT '',
    image_path      TEXT    NOT NULL DEFAULT '',
    zone_name       TEXT    NOT NULL DEFAULT '',
    camera_id       TEXT    NOT NULL DEFAULT '',
    person_id       INTEGER,
    acknowledged    INTEGER NOT NULL DEFAULT 0,
    created_at      REAL    NOT NULL,
    data            TEXT    NOT NULL  -- Full JSON alert payload
);

CREATE INDEX IF NOT EXISTS idx_alerts_activity_type ON alerts(activity_type);
CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged   ON alerts(acknowledged);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at     ON alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_timestamp      ON alerts(timestamp);

-- ---------------------------------------------------------------------------
-- System logs table
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS system_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    level      TEXT NOT NULL,
    logger     TEXT NOT NULL DEFAULT '',
    message    TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_system_logs_level      ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at DESC);
