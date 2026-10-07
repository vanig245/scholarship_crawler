import sqlite3, json
from datetime import datetime, timezone
from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    domain TEXT,
    source_type TEXT,          -- GOVERNMENT, UNIVERSITY, CORPORATE_CSR, NGO_TRUST, AGGREGATOR, UNKNOWN
    is_official INTEGER DEFAULT 0,
    discovered_via TEXT,       -- seed / search / link
    first_seen TEXT
);

CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    http_status INTEGER,
    content_hash TEXT,
    text TEXT
);

CREATE TABLE IF NOT EXISTS scholarships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    provider TEXT,
    official_source_url TEXT UNIQUE NOT NULL,
    application_url TEXT,
    source_type TEXT,
    amount TEXT,
    eligibility_json TEXT,     -- structured criteria
    academic_requirements TEXT,
    course_level TEXT,
    income_criteria TEXT,
    age_criteria TEXT,
    gender_criteria TEXT,
    category_criteria TEXT,
    domicile TEXT,
    institution_requirements TEXT,
    opening_date TEXT,
    closing_date TEXT,
    documents_required TEXT,
    selection_process TEXT,
    renewal_requirements TEXT,
    status TEXT DEFAULT 'REVIEW_REQUIRED',   -- ACTIVE, EXPIRING_SOON, EXPIRED, REVIEW_REQUIRED, NO_LONGER_VERIFIABLE
    verification_label TEXT,                 -- VERIFIED / REVIEW REQUIRED
    confidence REAL DEFAULT 0,
    confidence_breakdown TEXT,               -- JSON: why this score
    first_discovered TEXT,
    last_verified TEXT,
    last_changed TEXT
);

-- Every extracted field with the exact quote that supports it
CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scholarship_id INTEGER NOT NULL,
    field TEXT NOT NULL,
    value TEXT,
    quote TEXT,                -- verbatim text from the page
    source_url TEXT,
    captured_at TEXT,
    FOREIGN KEY (scholarship_id) REFERENCES scholarships(id)
);

CREATE TABLE IF NOT EXISTS change_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scholarship_id INTEGER NOT NULL,
    field TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    detected_at TEXT,
    source_url TEXT,
    evidence_quote TEXT,
    FOREIGN KEY (scholarship_id) REFERENCES scholarships(id)
);

CREATE TABLE IF NOT EXISTS crawl_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT,
    finished_at TEXT,
    discovered INTEGER DEFAULT 0,
    updated INTEGER DEFAULT 0,
    expired INTEGER DEFAULT 0
);
"""

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)

if __name__ == "__main__":
    init_db()
    print("Database initialised at", DB_PATH)