"""Isolated SQLite storage for parked shadow tasks.

This module owns ``shadow_tasks.db`` — a completely independent database that
never touches OpenOPC's ``store.db``.  All operations are async via
``aiosqlite``.  Every mutating write also appends an audit-log row so the full
lifecycle of each task is traceable.

Architectural notes
───────────────────
* **Schema versioning** — a ``schema_version`` table tracks the current DDL
  revision.  ``_ensure_schema()`` runs on every ``initialize()`` and can apply
  forward migrations without losing data.
* **Audit trail** — ``_audit()`` is called after every write to produce an
  append-only log of who did what and when.
* **Extensibility** — the ``extra_metadata`` JSON column on ``shadow_tasks``
  lets callers stash arbitrary key/value pairs without schema changes.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
from loguru import logger

from shadow_adapter.exceptions import (
    TaskNotClaimedError,
    TaskNotFoundError,
    TaskPermissionError,
)
from shadow_adapter.models import (
    ShadowAuditEntry,
    ShadowContractor,
    ShadowSubmission,
    ShadowTask,
    ShadowTaskStatus,
)

_SCHEMA_VERSION = 1

_DDL_V1 = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS shadow_tasks (
    id                     TEXT PRIMARY KEY,
    opc_task_id            TEXT NOT NULL,
    opc_session_id         TEXT,
    opc_project_id         TEXT NOT NULL DEFAULT 'default',
    opc_work_item_id       TEXT DEFAULT '',
    opc_metadata_json      TEXT DEFAULT '{}',

    title                  TEXT NOT NULL,
    description            TEXT DEFAULT '',
    assigned_role          TEXT DEFAULT '',
    priority               INTEGER DEFAULT 5,

    status                 TEXT NOT NULL DEFAULT 'pending'
                           CHECK(status IN (
                               'pending','claimed','submitted',
                               'resumed','failed','cancelled'
                           )),
    assigned_contractor_id TEXT,

    deliverable_text       TEXT,
    deliverable_files_json TEXT DEFAULT '[]',

    parked_at              TEXT NOT NULL,
    claimed_at             TEXT,
    submitted_at           TEXT,
    resumed_at             TEXT,
    deadline               TEXT,

    extra_metadata_json    TEXT DEFAULT '{}',

    created_at             TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at             TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_shadow_tasks_status
    ON shadow_tasks(status);
CREATE INDEX IF NOT EXISTS idx_shadow_tasks_opc_task_id
    ON shadow_tasks(opc_task_id);
CREATE INDEX IF NOT EXISTS idx_shadow_tasks_contractor
    ON shadow_tasks(assigned_contractor_id);

CREATE TABLE IF NOT EXISTS shadow_contractors (
    id            TEXT PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    email         TEXT,
    password_hash TEXT NOT NULL,
    display_name  TEXT DEFAULT '',
    roles_json    TEXT DEFAULT '["contractor"]',
    is_active     INTEGER DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_shadow_contractors_username
    ON shadow_contractors(username);

CREATE TABLE IF NOT EXISTS shadow_audit_log (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    shadow_task_id TEXT NOT NULL,
    actor_id       TEXT,
    action         TEXT NOT NULL,
    details_json   TEXT DEFAULT '{}',
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (shadow_task_id) REFERENCES shadow_tasks(id)
);

CREATE INDEX IF NOT EXISTS idx_audit_log_task
    ON shadow_audit_log(shadow_task_id);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


class ShadowStore:
    """Async CRUD store backed by an isolated SQLite database."""

    def __init__(self, db_path: str | Path = "./shadow_tasks.db") -> None:
        self._db_path = str(db_path)
        self._db: aiosqlite.Connection | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Open the database and ensure the schema is up to date."""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._ensure_schema()
        logger.info(f"ShadowStore initialized at {self._db_path}")

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    async def _ensure_schema(self) -> None:
        assert self._db is not None
        await self._db.executescript(_DDL_V1)
        await self._db.execute(
            "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
            (_SCHEMA_VERSION,),
        )
        await self._db.commit()

    # ------------------------------------------------------------------
    # Shadow Tasks — CRUD
    # ------------------------------------------------------------------

    async def create_task(self, task: ShadowTask) -> ShadowTask:
        assert self._db is not None
        now = _now_iso()
        await self._db.execute(
            """INSERT INTO shadow_tasks (
                   id, opc_task_id, opc_session_id, opc_project_id,
                   opc_work_item_id, opc_metadata_json,
                   title, description, assigned_role, priority,
                   status, assigned_contractor_id,
                   deliverable_text, deliverable_files_json,
                   parked_at, claimed_at, submitted_at, resumed_at, deadline,
                   extra_metadata_json, created_at, updated_at
               ) VALUES (
                   ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                   ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
               )""",
            (
                task.id,
                task.opc_task_id,
                task.opc_session_id,
                task.opc_project_id,
                task.opc_work_item_id,
                json.dumps(task.opc_metadata),
                task.title,
                task.description,
                task.assigned_role,
                task.priority,
                task.status.value,
                task.assigned_contractor_id,
                task.deliverable_text,
                json.dumps(task.deliverable_files),
                task.parked_at.isoformat(),
                task.claimed_at.isoformat() if task.claimed_at else None,
                task.submitted_at.isoformat() if task.submitted_at else None,
                task.resumed_at.isoformat() if task.resumed_at else None,
                task.deadline.isoformat() if task.deadline else None,
                json.dumps(task.extra_metadata),
                now,
                now,
            ),
        )
        await self._db.commit()
        await self._audit(task.id, None, "created", {"status": task.status.value})
        logger.debug(f"Shadow task created: {task.id} (opc={task.opc_task_id})")
        return task

    async def get_task(self, task_id: str) -> ShadowTask | None:
        assert self._db is not None
        async with self._db.execute("SELECT * FROM shadow_tasks WHERE id = ?", (task_id,)) as cursor:
            row = await cursor.fetchone()
        return self._row_to_task(row) if row else None

    async def get_task_by_opc_id(self, opc_task_id: str) -> ShadowTask | None:
        assert self._db is not None
        async with self._db.execute(
            "SELECT * FROM shadow_tasks WHERE opc_task_id = ? ORDER BY created_at DESC LIMIT 1",
            (opc_task_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return self._row_to_task(row) if row else None

    async def list_tasks(
        self,
        *,
        status: str | None = None,
        contractor_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ShadowTask]:
        assert self._db is not None
        query = "SELECT * FROM shadow_tasks WHERE 1=1"
        params: list[Any] = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if contractor_id:
            query += " AND assigned_contractor_id = ?"
            params.append(contractor_id)
        query += " ORDER BY priority ASC, parked_at ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        async with self._db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
        return [self._row_to_task(row) for row in rows]

    async def count_tasks(self, *, status: str | None = None) -> int:
        assert self._db is not None
        query = "SELECT COUNT(*) FROM shadow_tasks"
        params: list[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        async with self._db.execute(query, params) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else 0

    async def claim_task(self, task_id: str, contractor_id: str) -> ShadowTask:
        """Claim a pending task for a contractor. Raises ValueError on conflict."""
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        if task.status != ShadowTaskStatus.PENDING:
            raise ValueError(f"Cannot claim task {task_id}: status is '{task.status.value}', expected 'pending'")
        now = _now_iso()
        assert self._db is not None
        await self._db.execute(
            """UPDATE shadow_tasks
               SET status = ?, assigned_contractor_id = ?,
                   claimed_at = ?, updated_at = ?
               WHERE id = ? AND status = 'pending'""",
            (ShadowTaskStatus.CLAIMED.value, contractor_id, now, now, task_id),
        )
        await self._db.commit()
        await self._audit(task_id, contractor_id, "claimed", {})
        return await self.get_task(task_id)  # type: ignore[return-value]

    async def unclaim_task(self, task_id: str, contractor_id: str) -> ShadowTask:
        """Release a claimed task back to pending."""
        task = await self.get_task(task_id)
        if not task:
            raise TaskNotFoundError(task_id)
        if task.status != ShadowTaskStatus.CLAIMED:
            raise TaskNotClaimedError(task_id, task.status.value)
        if task.assigned_contractor_id != contractor_id:
            raise TaskPermissionError(task_id, task.assigned_contractor_id or "")
        now = _now_iso()
        assert self._db is not None
        await self._db.execute(
            """UPDATE shadow_tasks
               SET status = 'pending', assigned_contractor_id = NULL,
                   claimed_at = NULL, updated_at = ?
               WHERE id = ?""",
            (now, task_id),
        )
        await self._db.commit()
        await self._audit(task_id, contractor_id, "unclaimed", {})
        return await self.get_task(task_id)  # type: ignore[return-value]

    async def submit_task(
        self,
        task_id: str,
        contractor_id: str,
        submission: ShadowSubmission,
    ) -> ShadowTask:
        """Record a deliverable submission for a claimed task."""
        task = await self.get_task(task_id)
        if not task:
            raise TaskNotFoundError(task_id)
        if task.status != ShadowTaskStatus.CLAIMED:
            raise TaskNotClaimedError(task_id, task.status.value)
        if task.assigned_contractor_id != contractor_id:
            raise TaskPermissionError(task_id, task.assigned_contractor_id or "")
        now = _now_iso()
        assert self._db is not None
        await self._db.execute(
            """UPDATE shadow_tasks
               SET status = 'submitted',
                   deliverable_text = ?,
                   deliverable_files_json = ?,
                   submitted_at = ?,
                   updated_at = ?
               WHERE id = ?""",
            (
                submission.deliverable_text,
                json.dumps(submission.deliverable_files),
                now,
                now,
                task_id,
            ),
        )
        await self._db.commit()
        await self._audit(
            task_id,
            contractor_id,
            "submitted",
            {
                "has_text": bool(submission.deliverable_text),
                "file_count": len(submission.deliverable_files),
            },
        )
        return await self.get_task(task_id)  # type: ignore[return-value]

    async def mark_resumed(self, task_id: str) -> ShadowTask:
        """Mark a submitted task as successfully resumed in OpenOPC."""
        now = _now_iso()
        assert self._db is not None
        await self._db.execute(
            """UPDATE shadow_tasks
               SET status = 'resumed', resumed_at = ?, updated_at = ?
               WHERE id = ?""",
            (now, now, task_id),
        )
        await self._db.commit()
        await self._audit(task_id, None, "resumed", {})
        return await self.get_task(task_id)  # type: ignore[return-value]

    async def mark_failed(self, task_id: str, reason: str) -> ShadowTask:
        """Mark a task as failed with a reason."""
        now = _now_iso()
        assert self._db is not None
        await self._db.execute(
            """UPDATE shadow_tasks
               SET status = 'failed', updated_at = ?,
                   extra_metadata_json = json_set(
                       COALESCE(extra_metadata_json, '{}'),
                       '$.failure_reason', ?
                   )
               WHERE id = ?""",
            (now, reason, task_id),
        )
        await self._db.commit()
        await self._audit(task_id, None, "failed", {"reason": reason})
        return await self.get_task(task_id)  # type: ignore[return-value]

    async def cancel_task(self, task_id: str, actor_id: str | None = None) -> ShadowTask:
        """Cancel a task."""
        now = _now_iso()
        assert self._db is not None
        await self._db.execute(
            "UPDATE shadow_tasks SET status = 'cancelled', updated_at = ? WHERE id = ?",
            (now, task_id),
        )
        await self._db.commit()
        await self._audit(task_id, actor_id, "cancelled", {})
        return await self.get_task(task_id)  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Contractors — CRUD
    # ------------------------------------------------------------------

    async def create_contractor(self, contractor: ShadowContractor) -> ShadowContractor:
        assert self._db is not None
        now = _now_iso()
        await self._db.execute(
            """INSERT INTO shadow_contractors (
                   id, username, email, password_hash,
                   display_name, roles_json, is_active,
                   created_at, updated_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                contractor.id,
                contractor.username,
                contractor.email,
                contractor.password_hash,
                contractor.display_name,
                json.dumps(contractor.roles),
                1 if contractor.is_active else 0,
                now,
                now,
            ),
        )
        await self._db.commit()
        logger.info(f"Contractor created: {contractor.username} ({contractor.id})")
        return contractor

    async def get_contractor(self, contractor_id: str) -> ShadowContractor | None:
        assert self._db is not None
        async with self._db.execute("SELECT * FROM shadow_contractors WHERE id = ?", (contractor_id,)) as cursor:
            row = await cursor.fetchone()
        return self._row_to_contractor(row) if row else None

    async def get_contractor_by_username(self, username: str) -> ShadowContractor | None:
        assert self._db is not None
        async with self._db.execute("SELECT * FROM shadow_contractors WHERE username = ?", (username,)) as cursor:
            row = await cursor.fetchone()
        return self._row_to_contractor(row) if row else None

    async def list_contractors(self) -> list[ShadowContractor]:
        assert self._db is not None
        async with self._db.execute("SELECT * FROM shadow_contractors ORDER BY created_at ASC") as cursor:
            rows = await cursor.fetchall()
        return [self._row_to_contractor(row) for row in rows]

    async def contractor_count(self) -> int:
        assert self._db is not None
        async with self._db.execute("SELECT COUNT(*) FROM shadow_contractors") as cursor:
            row = await cursor.fetchone()
        return row[0] if row else 0

    # ------------------------------------------------------------------
    # Audit Log
    # ------------------------------------------------------------------

    async def get_audit_log(self, task_id: str) -> list[ShadowAuditEntry]:
        assert self._db is not None
        async with self._db.execute(
            "SELECT * FROM shadow_audit_log WHERE shadow_task_id = ? ORDER BY created_at ASC",
            (task_id,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [
            ShadowAuditEntry(
                id=row["id"],
                shadow_task_id=row["shadow_task_id"],
                actor_id=row["actor_id"],
                action=row["action"],
                details=json.loads(row["details_json"] or "{}"),
                created_at=_parse_dt(row["created_at"]) or datetime.now(timezone.utc),
            )
            for row in rows
        ]

    async def _audit(
        self,
        task_id: str,
        actor_id: str | None,
        action: str,
        details: dict[str, Any],
    ) -> None:
        assert self._db is not None
        await self._db.execute(
            """INSERT INTO shadow_audit_log
               (shadow_task_id, actor_id, action, details_json, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (task_id, actor_id, action, json.dumps(details), _now_iso()),
        )
        await self._db.commit()

    # ------------------------------------------------------------------
    # Row → Model Hydration
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_task(row: aiosqlite.Row) -> ShadowTask:
        return ShadowTask(
            id=row["id"],
            opc_task_id=row["opc_task_id"],
            opc_session_id=row["opc_session_id"],
            opc_project_id=row["opc_project_id"],
            opc_work_item_id=row["opc_work_item_id"] or "",
            opc_metadata=json.loads(row["opc_metadata_json"] or "{}"),
            title=row["title"],
            description=row["description"] or "",
            assigned_role=row["assigned_role"] or "",
            priority=row["priority"] or 5,
            status=ShadowTaskStatus(row["status"]),
            assigned_contractor_id=row["assigned_contractor_id"],
            deliverable_text=row["deliverable_text"],
            deliverable_files=json.loads(row["deliverable_files_json"] or "[]"),
            parked_at=_parse_dt(row["parked_at"]) or datetime.now(timezone.utc),
            claimed_at=_parse_dt(row["claimed_at"]),
            submitted_at=_parse_dt(row["submitted_at"]),
            resumed_at=_parse_dt(row["resumed_at"]),
            deadline=_parse_dt(row["deadline"]),
            extra_metadata=json.loads(row["extra_metadata_json"] or "{}"),
        )

    @staticmethod
    def _row_to_contractor(row: aiosqlite.Row) -> ShadowContractor:
        return ShadowContractor(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            password_hash=row["password_hash"],
            display_name=row["display_name"] or "",
            roles=json.loads(row["roles_json"] or '["contractor"]'),
            is_active=bool(row["is_active"]),
            created_at=_parse_dt(row["created_at"]) or datetime.now(timezone.utc),
            updated_at=_parse_dt(row["updated_at"]) or datetime.now(timezone.utc),
        )
