"""Core Shadow Mode Adapter for OpenOPC.

Extends OpenOPC's ExternalAgentAdapter to provide a non-blocking Human-in-the-Loop (HITL)
execution surface. Intercepts tasks, parks them in an isolated SQLite database,
and releases execution threads instantly.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from shadow_adapter.config import ShadowConfig
from shadow_adapter.models import (
    ShadowTask,
    ShadowTaskStatus,
    TaskResumeResult,
)
from shadow_adapter.shadow_store import ShadowStore

# Import OpenOPC core types or use fallback dataclass mocks for standalone testing
try:
    from opc.core.models import Task, TaskResult, TaskStatus
    from opc.layer3_agent.adapters.base import ExternalAgentAdapter

    HAS_OPENOPC = True
except ImportError:
    HAS_OPENOPC = False
    from dataclasses import dataclass, field

    class TaskStatus:  # type: ignore[no-redef]
        PENDING = "pending"
        RUNNING = "running"
        AWAITING_HUMAN = "awaiting_human"
        DONE = "done"
        FAILED = "failed"

    @dataclass
    class Task:  # type: ignore[no-redef]
        id: str
        session_id: str | None = None
        title: str = ""
        description: str = ""
        assigned_to: str = ""
        status: Any = TaskStatus.PENDING
        priority: int = 5
        project_id: str = "default"
        metadata: dict = field(default_factory=dict)
        linked_work_item_id: str = ""

    @dataclass
    class TaskResult:  # type: ignore[no-redef]
        status: Any
        content: str = ""
        artifacts: dict = field(default_factory=dict)
        escalation: dict | None = None
        cost: float = 0.0
        token_usage: dict = field(default_factory=dict)

    class ExternalAgentAdapter:  # type: ignore[no-redef]
        agent_type: str = ""

        def __init__(self, config: Any = None) -> None:
            self.config = config

        async def is_available(self) -> bool:
            return True


class ShadowModeAdapter(ExternalAgentAdapter):
    """External agent adapter that parks tasks for human contractor execution."""

    agent_type: str = "shadow"
    default_command: str = "shadow"

    def __init__(
        self,
        config: Any = None,
        shadow_config: ShadowConfig | None = None,
        shadow_store: ShadowStore | None = None,
    ) -> None:
        super().__init__(config)
        self.shadow_config = shadow_config or ShadowConfig()
        self._shadow_store = shadow_store

    async def _get_store(self) -> ShadowStore:
        if self._shadow_store is None:
            self._shadow_store = ShadowStore(self.shadow_config.db_path)
            await self._shadow_store.initialize()
        return self._shadow_store

    async def is_available(self) -> bool:
        """Shadow adapter is always available since it has no external CLI dependency."""
        return True

    async def get_status(self) -> Any:
        """Return idle status since human work happens asynchronously out-of-band."""
        return getattr(TaskStatus, "IDLE", "idle")

    def build_invocation(
        self,
        task: Task,
        workspace_path: str | None = None,
    ) -> tuple[list[str], dict[str, Any]]:
        """Return empty command list because shadow tasks do not launch subprocesses."""
        return [], {
            "agent": self.agent_type,
            "workspace": workspace_path or "",
            "mode": "shadow_human_in_loop",
        }

    async def execute(self, task: Task, workspace_path: str) -> TaskResult:
        """Intercept an OpenOPC task, park it in local DB, and return AWAITING_HUMAN immediately.

        Wrapped in an Exception Black Hole to prevent host engine process crashes.
        """
        try:
            task_id = str(getattr(task, "id", "") or "").strip()
            task_title = str(getattr(task, "title", "") or "Untitled Task").strip()
            logger.info(f"[ShadowModeAdapter] Intercepting OpenOPC task {task_id} ('{task_title}')")

            store = await self._get_store()

            # Check if already parked
            existing = await store.get_task_by_opc_id(task_id)
            if existing and existing.status in (
                ShadowTaskStatus.PENDING,
                ShadowTaskStatus.CLAIMED,
            ):
                logger.info(f"[ShadowModeAdapter] Task {task_id} is already parked as {existing.id}")
                return TaskResult(
                    status=TaskStatus.AWAITING_HUMAN,
                    content=f"Task is currently parked for human completion in Shadow Mode (shadow_id={existing.id}).",
                    artifacts={
                        "shadow_task_id": existing.id,
                        "opc_task_id": task_id,
                        "parked_at": existing.parked_at.isoformat(),
                        "status": existing.status.value,
                    },
                )

            # Defensive Map OpenOPC Task to ShadowTask
            shadow_task = self._task_to_shadow_task(task)

            # Park in isolated SQLite store
            await store.create_task(shadow_task)

            logger.info(
                f"[ShadowModeAdapter] Parked task {task_id} as shadow_id={shadow_task.id}. "
                f"Returning AWAITING_HUMAN status to release thread."
            )

            return TaskResult(
                status=TaskStatus.AWAITING_HUMAN,
                content=(
                    f"Task '{task_title}' intercepted and parked for human contractor deliverable. "
                    f"Shadow Task ID: {shadow_task.id}"
                ),
                artifacts={
                    "shadow_task_id": shadow_task.id,
                    "opc_task_id": task_id,
                    "opc_work_item_id": shadow_task.opc_work_item_id,
                    "parked_at": shadow_task.parked_at.isoformat(),
                    "status": ShadowTaskStatus.PENDING.value,
                },
            )
        except Exception as exc:
            logger.exception(f"[ShadowModeAdapter] Critical execution failure: {exc}")
            return TaskResult(
                status=TaskStatus.FAILED,
                content=f"Shadow Mode Intercept Critical Error: {exc}",
                artifacts={"error": str(exc), "source": "shadow_mode_adapter"},
            )

    # ------------------------------------------------------------------
    # Helper & Resume Methods
    # ------------------------------------------------------------------

    @staticmethod
    def _task_to_shadow_task(task: Task) -> ShadowTask:
        """Defensively convert an OpenOPC Task model to a local ShadowTask model."""
        task_id = str(getattr(task, "id", "") or "").strip()
        session_id = getattr(task, "session_id", None)
        project_id = str(getattr(task, "project_id", "default") or "default")
        title = str(getattr(task, "title", "") or "Untitled Task").strip()
        description = str(getattr(task, "description", "") or "").strip()
        assigned_to = str(getattr(task, "assigned_to", "") or "").strip()
        priority = int(getattr(task, "priority", 5) or 5)

        metadata = dict(getattr(task, "metadata", {}) or {})
        work_item_id = str(getattr(task, "linked_work_item_id", "") or "").strip()
        if not work_item_id:
            work_item_id = str(
                metadata.get("work_item_id")
                or metadata.get("linked_work_item_id")
                or metadata.get("wi_id")
                or ""
            ).strip()

        return ShadowTask(
            opc_task_id=task_id,
            opc_session_id=session_id,
            opc_project_id=project_id,
            opc_work_item_id=work_item_id,
            opc_metadata=metadata,
            title=title,
            description=description,
            assigned_role=assigned_to,
            priority=priority,
            status=ShadowTaskStatus.PENDING,
            parked_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def shadow_submission_to_task_result(shadow_task: ShadowTask) -> TaskResult:
        """Convert human submission in ShadowTask to an OpenOPC TaskResult."""
        return TaskResult(
            status=TaskStatus.DONE,
            content=shadow_task.deliverable_text or "Human deliverable submitted successfully.",
            artifacts={
                "shadow_task_id": shadow_task.id,
                "deliverable_files": shadow_task.deliverable_files,
                "contractor_id": shadow_task.assigned_contractor_id,
                "submitted_at": (
                    shadow_task.submitted_at.isoformat() if shadow_task.submitted_at else ""
                ),
                "source": "human_shadow_adapter",
            },
            cost=0.0,
            token_usage={},
        )

    @classmethod
    async def resume_task(
        cls,
        shadow_task: ShadowTask,
        opc_store_path: str | Path,
    ) -> TaskResumeResult:
        """Push human deliverable back into OpenOPC store to unblock the DAG.

        Wrapped in an Exception Black Hole for safe execution.
        """
        try:
            db_path = Path(opc_store_path)
            if not db_path.exists():
                msg = f"OpenOPC store.db not found at '{db_path}'"
                logger.error(f"[ShadowModeAdapter] {msg}")
                return TaskResumeResult(
                    success=False,
                    shadow_task_id=shadow_task.id,
                    opc_task_id=shadow_task.opc_task_id,
                    error=msg,
                )

            import aiosqlite

            task_result = cls.shadow_submission_to_task_result(shadow_task)
            result_json = json.dumps({
                "status": "done",
                "content": task_result.content,
                "summary": task_result.content,
                "artifacts": task_result.artifacts,
                "submitted_by_human": True,
                "contractor_username": shadow_task.assigned_contractor_id or "human_contractor",
                "cost": 0.0,
                "token_usage": {},
            })

            now_iso = datetime.now(timezone.utc).isoformat()

            async with aiosqlite.connect(str(db_path)) as db:
                await db.execute("PRAGMA journal_mode=WAL")

                # Update task in OpenOPC database
                cursor = await db.execute(
                    """UPDATE tasks
                       SET status = 'done',
                           result = ?,
                           execution_lock = 0,
                           execution_locked_at = NULL
                       WHERE id = ?""",
                    (result_json, shadow_task.opc_task_id),
                )

                if cursor.rowcount == 0:
                    logger.warning(f"No OpenOPC task row matched id={shadow_task.opc_task_id}")

                # If linked to a work item, advance phase from awaiting_human -> approved
                work_item_updated = False
                if shadow_task.opc_work_item_id:
                    wi_cursor = await db.execute(
                        """UPDATE delegation_work_items
                           SET phase = 'approved',
                               updated_at = ?
                           WHERE work_item_id = ?""",
                        (now_iso, shadow_task.opc_work_item_id),
                    )
                    work_item_updated = wi_cursor.rowcount > 0

                await db.commit()

            logger.info(
                f"[ShadowModeAdapter] Successfully resumed OpenOPC task {shadow_task.opc_task_id} "
                f"(work_item={shadow_task.opc_work_item_id}, wi_updated={work_item_updated})"
            )

            return TaskResumeResult(
                success=True,
                shadow_task_id=shadow_task.id,
                opc_task_id=shadow_task.opc_task_id,
                opc_task_status="done",
                opc_work_item_phase="approved" if work_item_updated else "",
                message="OpenOPC task and work item updated to completed state.",
            )

        except Exception as exc:
            logger.exception(
                f"[ShadowModeAdapter] Error resuming task {shadow_task.opc_task_id}: {exc}"
            )
            return TaskResumeResult(
                success=False,
                shadow_task_id=shadow_task.id,
                opc_task_id=shadow_task.opc_task_id,
                error=f"Resume Exception: {exc}",
            )
