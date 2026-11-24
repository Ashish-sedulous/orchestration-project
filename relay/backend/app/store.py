"""Tiny SQLite persistence for finished runs (history tab)."""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing

from . import config


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(config.DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS runs (
        id TEXT PRIMARY KEY, created REAL, task TEXT, strategy TEXT, status TEXT,
        metrics TEXT, events TEXT)""")
    return c


def save(run) -> None:
    metrics = (run.final or {}).get("metrics", {})
    with closing(_conn()) as c:
        c.execute("INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?)",
                  (run.id, run.created, run.task, run.strategy, run.status,
                   json.dumps(metrics), json.dumps(run.events)))
        c.commit()


def list_runs(limit: int = 50) -> list[dict]:
    with closing(_conn()) as c:
        rows = c.execute("SELECT id, created, task, strategy, status, metrics FROM runs "
                         "ORDER BY created DESC LIMIT ?", (limit,)).fetchall()
    return [{"id": r[0], "created": r[1], "task": r[2], "strategy": r[3],
             "status": r[4], "metrics": json.loads(r[5] or "{}")} for r in rows]


def get_events(run_id: str) -> list[dict] | None:
    with closing(_conn()) as c:
        row = c.execute("SELECT events FROM runs WHERE id=?", (run_id,)).fetchone()
    return json.loads(row[0]) if row else None
