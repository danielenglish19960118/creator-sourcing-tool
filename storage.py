"""
Lightweight SQLite storage for briefs and scored results.

No PII is stored; only campaign briefs and public creator metrics.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data.db")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            brief_json TEXT,
            results_json TEXT
        )
        """
    )
    return conn


def save_run(brief: dict, results_df) -> int:
    conn = _conn()
    with conn:
        cur = conn.execute(
            "INSERT INTO runs (created_at, brief_json, results_json) VALUES (?, ?, ?)",
            (
                datetime.utcnow().isoformat(),
                json.dumps(brief, ensure_ascii=False),
                results_df.to_json(orient="records", force_ascii=False),
            ),
        )
        return cur.lastrowid


def list_runs(limit: int = 20) -> list[dict]:
    conn = _conn()
    rows = conn.execute(
        "SELECT id, created_at, brief_json FROM runs ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [
        {"id": r[0], "created_at": r[1], "brief": json.loads(r[2])}
        for r in rows
    ]
