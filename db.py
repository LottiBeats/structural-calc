"""
db.py — SQLite persistence layer for OMKREDS Structural Calc.

Tables:
  projects      — one row per project (full JSON blob)
  calc_library  — shared office calculation templates

All writes are protected by a threading.Lock so concurrent Streamlit
sessions on the same server never corrupt the WAL.
"""

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "projects.db"

_lock = threading.Lock()


# -- Schema -------------------------------------------------------------------

def init_db(path: Path | None = None) -> None:
    """Create tables if they do not already exist."""
    p = str(path or DB_PATH)
    with sqlite3.connect(p) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id         TEXT PRIMARY KEY,
                data       TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS calc_library (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                description TEXT DEFAULT '',
                blocks      TEXT NOT NULL,
                created_by  TEXT DEFAULT '',
                created_at  TEXT NOT NULL
            )
        """)
        conn.commit()


# -- Projects: read -----------------------------------------------------------

def load_all_projects(path: Path | None = None) -> list[dict]:
    """Return all projects, newest first."""
    p = str(path or DB_PATH)
    init_db(path)
    with sqlite3.connect(p) as conn:
        rows = conn.execute(
            "SELECT data FROM projects ORDER BY updated_at DESC"
        ).fetchall()
    projects = []
    for (data_str,) in rows:
        try:
            projects.append(json.loads(data_str))
        except Exception:
            pass
    return projects


def load_project(project_id: str, path: Path | None = None) -> dict | None:
    """Load a single project by id, or None if not found."""
    p = str(path or DB_PATH)
    with sqlite3.connect(p) as conn:
        row = conn.execute(
            "SELECT data FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
    if row:
        try:
            return json.loads(row[0])
        except Exception:
            return None
    return None


# -- Projects: write ----------------------------------------------------------

def save_project(project: dict, user: str = "", path: Path | None = None) -> None:
    """Upsert a project. Stamps _updated_at / _updated_by into the dict."""
    p = str(path or DB_PATH)
    now = datetime.now(timezone.utc).isoformat()
    project["_updated_at"] = now
    project["_updated_by"] = user
    data_str = json.dumps(project, ensure_ascii=False)
    with _lock:
        with sqlite3.connect(p) as conn:
            conn.execute("""
                INSERT INTO projects (id, data, updated_at, updated_by)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    data       = excluded.data,
                    updated_at = excluded.updated_at,
                    updated_by = excluded.updated_by
            """, (project["id"], data_str, now, user))
            conn.commit()


def delete_project(project_id: str, path: Path | None = None) -> None:
    """Permanently delete a project."""
    p = str(path or DB_PATH)
    with _lock:
        with sqlite3.connect(p) as conn:
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()


# -- Calc library: read -------------------------------------------------------

def load_all_templates(path: Path | None = None) -> list[dict]:
    """Return all saved calc templates, newest first."""
    p = str(path or DB_PATH)
    init_db(path)
    with sqlite3.connect(p) as conn:
        rows = conn.execute("""
            SELECT id, name, description, blocks, created_by, created_at
            FROM calc_library ORDER BY created_at DESC
        """).fetchall()
    templates = []
    for row in rows:
        try:
            templates.append({
                "id":          row[0],
                "name":        row[1],
                "description": row[2],
                "blocks":      json.loads(row[3]),
                "created_by":  row[4],
                "created_at":  row[5],
            })
        except Exception:
            pass
    return templates


# -- Calc library: write ------------------------------------------------------

def save_template(name: str, description: str, blocks: list,
                  user: str = "", path: Path | None = None) -> str:
    """Save a new calc template. Returns the new template id."""
    import uuid
    p = str(path or DB_PATH)
    now = datetime.now(timezone.utc).isoformat()
    tid = uuid.uuid4().hex[:8]
    blocks_str = json.dumps(blocks, ensure_ascii=False)
    with _lock:
        with sqlite3.connect(p) as conn:
            conn.execute("""
                INSERT INTO calc_library (id, name, description, blocks, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (tid, name, description, blocks_str, user, now))
            conn.commit()
    return tid


def delete_template(template_id: str, path: Path | None = None) -> None:
    """Delete a calc template."""
    p = str(path or DB_PATH)
    with _lock:
        with sqlite3.connect(p) as conn:
            conn.execute("DELETE FROM calc_library WHERE id = ?", (template_id,))
            conn.commit()


# -- Helpers ------------------------------------------------------------------

def project_count(path: Path | None = None) -> int:
    p = str(path or DB_PATH)
    init_db(path)
    with sqlite3.connect(p) as conn:
        return conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]


def fmt_updated(iso: str) -> str:
    """Format an ISO timestamp as a human-readable relative string."""
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        s = int(delta.total_seconds())
        if s < 60:
            return "just now"
        if s < 3600:
            return f"{s // 60} min ago"
        if s < 86400:
            return f"{s // 3600} h ago"
        return f"{s // 86400} d ago"
    except Exception:
        return iso[:10]
