"""Repository for writing resume results back into OpenOPC's store.db.

This module owns the direct WAL write to OpenOPC's SQLite database.
Previously this SQL lived inside adapter.py — it has been extracted here
to enforce N-Tier isolation (Mandate 2): the adapter is a service-tier
component and must not contain raw SQL.

Repository Tier: Pure data access. Zero business logic.
Wrapped in Exception Black Hole to never crash the host engine.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
from loguru import logger

from shadow_adapter.models import ShadowTask, TaskResumeResult


class OpcResumeRepository:
    """Direct WAL writer to OpenOPC's store.db for resume callbacks.

    Production Line:
    1. _validate_store_path()   → Verify store.db exists
    2. _build_result_json()     → Serialize human deliverable
    3. _write_task_status()     → UPDATE tasks SET status='done'
    4. _advance_work_item()     → UPDATE delegation_work_items SET phase='approved'
    """

    async def resume(
        self,
        shadow_task: ShadowTask,
        opc_store_path: str,
        task_result_content: str = "",
        task_result_artifacts: dict | None = None,
    ) -> TaskResumeResult:
        """Push human deliverable back into OpenOPC store to unblock the DAG.

        Wrapped in an Exception Black Hole for safe execution.
        """
        try:
            db_path = Path(opc_store_path)
            if not db_path.exists():
                msg = f"OpenOPC store.db not found at '{db_path}'"
                logger.error(f"[OpcResumeRepository] {msg}")
                return TaskResumeResult(
                    success=False,
                    shadow_task_id=shadow_task.id,
                    opc_task_id=shadow_task.opc_task_id,
                    error=msg,
                )

            result_json = self._build_result_json(
                shadow_task=shadow_task,
                content=task_result_content,
                artifacts=task_result_artifacts or {},
            )

            now_iso = datetime.now(timezone.utc).isoformat()

            target_phase = str(shadow_task.opc_metadata.get("target_phase") or "approved")

            async with aiosqlite.connect(str(db_path)) as db:
                await db.execute("PRAGMA journal_mode=WAL")

                # Step 3: Update task status in OpenOPC database
                cursor = await db.execute(
                    """UPDATE tasks
                       SET status = 'done',
                           result = ?,
                           execution_lock = 0,
                           execution_locked_at = NULL
                       WHERE id = ?""",
                    (result_json, shadow_task.opc_task_id),
                )

                task_found = cursor.rowcount > 0
                if not task_found:
                    logger.warning(
                        f"[OpcResumeRepository] No OpenOPC task row matched id '{shadow_task.opc_task_id}' in store.db (Orphaned task)"
                    )

                # Step 4: If linked to a work item, advance phase to OpenOPC expected phase
                work_item_updated = False
                if shadow_task.opc_work_item_id:
                    wi_cursor = await db.execute(
                        """UPDATE delegation_work_items
                           SET phase = ?,
                               updated_at = ?
                           WHERE work_item_id = ?""",
                        (target_phase, now_iso, shadow_task.opc_work_item_id),
                    )
                    work_item_updated = wi_cursor.rowcount > 0

                await db.commit()

            logger.info(
                f"[OpcResumeRepository] Resumed OpenOPC task {shadow_task.opc_task_id} "
                f"(matched={task_found}, work_item={shadow_task.opc_work_item_id}, phase={target_phase})"
            )

            return TaskResumeResult(
                success=True,
                shadow_task_id=shadow_task.id,
                opc_task_id=shadow_task.opc_task_id,
                opc_task_status="done" if task_found else "orphaned",
                opc_work_item_phase=target_phase if work_item_updated else "",
                message="OpenOPC task and work item updated to completed state."
                if task_found
                else "Task saved, host row orphaned.",
            )

        except Exception as exc:
            logger.exception(f"[OpcResumeRepository] Error resuming task {shadow_task.opc_task_id}: {exc}")
            return TaskResumeResult(
                success=False,
                shadow_task_id=shadow_task.id,
                opc_task_id=shadow_task.opc_task_id,
                error=f"Resume Exception: {exc}",
            )

    @staticmethod
    def _build_result_json(
        shadow_task: ShadowTask,
        content: str,
        artifacts: dict,
    ) -> str:
        """Serialize the human deliverable into OpenOPC's result JSON format."""
        return json.dumps(
            {
                "status": "done",
                "content": content or shadow_task.deliverable_text or "Human deliverable submitted successfully.",
                "summary": content or shadow_task.deliverable_text or "Human deliverable submitted successfully.",
                "artifacts": artifacts
                or {
                    "shadow_task_id": shadow_task.id,
                    "deliverable_files": shadow_task.deliverable_files,
                    "contractor_id": shadow_task.assigned_contractor_id or "human_contractor",
                    "submitted_at": (shadow_task.submitted_at.isoformat() if shadow_task.submitted_at else ""),
                    "source": "human_shadow_adapter",
                },
                "submitted_by_human": True,
                "contractor_username": shadow_task.assigned_contractor_id or "human_contractor",
                "cost": 0.0,
                "token_usage": {},
            }
        )
