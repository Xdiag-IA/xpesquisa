import sqlite3
from pathlib import Path

from .models import Event, Run, now


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, body TEXT NOT NULL)")
            db.execute("PRAGMA user_version=1")

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def save(self, run: Run):
        run.updated_at = now()
        with self.connect() as db:
            db.execute("INSERT INTO runs VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET body=excluded.body",
                       (run.id, run.created_at.isoformat(), run.model_dump_json()))

    def get(self, run_id: str) -> Run | None:
        with self.connect() as db:
            row = db.execute("SELECT body FROM runs WHERE id=?", (run_id,)).fetchone()
        return Run.model_validate_json(row[0]) if row else None

    def list(self, limit: int = 50):
        with self.connect() as db:
            rows = db.execute("SELECT body FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [Run.model_validate_json(row[0]) for row in rows]

    def recover(self):
        with self.connect() as db:
            rows = db.execute("SELECT body FROM runs").fetchall()
        for row in rows:
            run = Run.model_validate_json(row[0])
            if run.status in {"queued", "running"}:
                run.status = "failed"
                run.error = "Execução interrompida pelo encerramento do processo. Inicie nova pesquisa."
                run.events.append(Event(stage="interrupted", detail={"reason": "process_restart"}))
                self.save(run)
