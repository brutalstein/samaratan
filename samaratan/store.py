"""SQLite job ledger and isolated project workspaces; no external database."""
from datetime import datetime, timezone
from pathlib import Path
import re
import sqlite3
from uuid import uuid4


_ID = re.compile(r"^[0-9a-f]{32}$")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class NotFound(Exception):
    pass


class Store:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "jobs").mkdir(exist_ok=True)
        self.db_path = self.root / "jobs.sqlite3"
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, provider TEXT NOT NULL, prompt TEXT NOT NULL,
                export_windows INTEGER NOT NULL, status TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                error TEXT, title TEXT, source_zip TEXT, windows_exe TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at);
            """)
            # Jobs interrupted by an unexpected process restart can be retried as new jobs.
            db.execute("UPDATE jobs SET status='failed', error='Worker interrupted; submit again', updated_at=? WHERE status IN ('running','queued')", (now(),))

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def create(self, provider: str, prompt: str, export_windows: bool) -> dict:
        job_id = uuid4().hex
        stamp = now()
        with self._connect() as db:
            db.execute("INSERT INTO jobs (id,provider,prompt,export_windows,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
                       (job_id, provider, prompt, int(export_windows), "queued", stamp, stamp))
        return self.get(job_id)

    def get(self, job_id: str) -> dict:
        if not _ID.fullmatch(job_id):
            raise NotFound("Job not found")
        with self._connect() as db:
            result = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if result is None:
            raise NotFound("Job not found")
        return dict(result)

    def update(self, job_id: str, status: str, **fields: str | None) -> dict:
        if status not in {"running", "succeeded", "failed"}:
            raise ValueError("Invalid job state")
        if not set(fields) <= {"error", "title", "source_zip", "windows_exe"}:
            raise ValueError("Invalid job update field")
        self.get(job_id)
        columns = ["status=?", "updated_at=?"]
        values = [status, now()]
        for key, value in fields.items():
            columns.append(f"{key}=?")
            values.append(value)
        with self._connect() as db:
            db.execute(f"UPDATE jobs SET {', '.join(columns)} WHERE id=?", (*values, job_id))
        return self.get(job_id)

    def directory(self, job_id: str) -> Path:
        self.get(job_id)
        job_path = self.root / "jobs" / job_id
        if job_path.is_symlink():
            raise ValueError("Unsafe project directory")
        job_path.mkdir(exist_ok=True)
        if not job_path.resolve().is_relative_to((self.root / "jobs").resolve()):
            raise ValueError("Unsafe project path")
        return job_path

    def output(self, job_id: str, field: str) -> Path:
        if field not in ("source_zip", "windows_exe"):
            raise ValueError("Invalid artifact type")
        job = self.get(job_id)
        filename = job[field]
        if not filename:
            raise NotFound("Artifact not ready")
        path = (self.root / "jobs" / job_id / filename).resolve()
        if not path.is_relative_to((self.root / "jobs" / job_id).resolve()) or not path.is_file():
            raise NotFound("Artifact not found")
        return path


def public_job(row: dict) -> dict:
    return {key: row[key] for key in (
        "id", "provider", "status", "created_at", "updated_at", "error", "title",
        "source_zip", "windows_exe",
    )}
