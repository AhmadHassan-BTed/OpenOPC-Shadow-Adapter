"""Unit and integration tests for ShadowModeAdapter lifecycle and WAL resume pipeline."""

from __future__ import annotations

import sqlite3
import pytest
from shadow_adapter.adapter import ShadowModeAdapter
from shadow_adapter.config import ShadowConfig
from shadow_adapter.models import ShadowTaskStatus
from shadow_adapter.shadow_store import ShadowStore

# Import OpenOPC Task model or fallback mock
try:
    from opc.core.models import Task, TaskStatus
except ImportError:
    from dataclasses import dataclass, field

    class TaskStatus:
        PENDING = "pending"
        AWAITING_HUMAN = "awaiting_human"
        DONE = "done"

    @dataclass
    class Task:
        id: str = "opc_task_test"
        session_id: str | None = "session_1"
        title: str = "Test Task"
        description: str = "Description"
        assigned_to: str = "reviewer"
        status: str = TaskStatus.PENDING
        priority: int = 5
        project_id: str = "default"
        metadata: dict = field(default_factory=dict)
        linked_work_item_id: str = "wi_1"

pytestmark = pytest.mark.asyncio


async def test_adapter_availability_and_status(shadow_config: ShadowConfig) -> None:
    """Test that adapter reports available and idle status."""
    adapter = ShadowModeAdapter(shadow_config=shadow_config)
    assert await adapter.is_available() is True
    status = await adapter.get_status()
    status_str = status.value if hasattr(status, "value") else str(status)
    assert status_str.lower() == "idle"


async def test_build_invocation(shadow_config: ShadowConfig) -> None:
    """Test build_invocation returns an empty command list."""
    adapter = ShadowModeAdapter(shadow_config=shadow_config)
    task = Task(id="t_inv_1", title="Invocation Test")
    cmd, env = adapter.build_invocation(task, workspace_path="/tmp/workspace")
    assert cmd == []
    assert env["agent"] == "shadow"
    assert env["workspace"] == "/tmp/workspace"


async def test_adapter_execute_parks_task(
    shadow_config: ShadowConfig,
    shadow_store: ShadowStore,
) -> None:
    """Test that execute() parks task in shadow_store and returns AWAITING_HUMAN immediately."""
    adapter = ShadowModeAdapter(shadow_config=shadow_config, shadow_store=shadow_store)

    task = Task(
        id="opc_exec_77",
        session_id="session_77",
        title="Approve Quarterly Budget",
        description="Verify Q3 budget allocation",
        assigned_to="cfo",
        priority=1,
        linked_work_item_id="wi_777",
    )

    result = await adapter.execute(task, workspace_path="/tmp")

    # Assert status returned is AWAITING_HUMAN
    res_status = result.status.value if hasattr(result.status, "value") else result.status
    assert res_status == TaskStatus.AWAITING_HUMAN or res_status == "awaiting_human"

    # Assert task artifacts contains shadow_task_id
    assert "shadow_task_id" in result.artifacts
    shadow_id = result.artifacts["shadow_task_id"]

    # Verify task row in ShadowStore
    parked = await shadow_store.get_task(shadow_id)
    assert parked is not None
    assert parked.opc_task_id == "opc_exec_77"
    assert parked.opc_work_item_id == "wi_777"
    assert parked.title == "Approve Quarterly Budget"
    assert parked.status == ShadowTaskStatus.PENDING


async def test_adapter_execute_idempotent(
    shadow_config: ShadowConfig,
    shadow_store: ShadowStore,
) -> None:
    """Test calling execute() on an already parked task returns existing parked info."""
    adapter = ShadowModeAdapter(shadow_config=shadow_config, shadow_store=shadow_store)
    task = Task(id="opc_dup_1", title="Duplicate Exec Test")

    res1 = await adapter.execute(task, workspace_path="/tmp")
    res2 = await adapter.execute(task, workspace_path="/tmp")

    assert res1.artifacts["shadow_task_id"] == res2.artifacts["shadow_task_id"]


async def test_resume_task_updates_opc_store(
    shadow_config: ShadowConfig,
    shadow_store: ShadowStore,
    mock_opc_store_path: Path,
) -> None:
    """Test resume_task() updating OpenOPC store.db task status to 'done' and work item phase to 'approved'."""
    opc_task_id = "opc_resume_99"
    work_item_id = "wi_resume_99"

    # Insert initial rows in mock opc_store.db
    conn = sqlite3.connect(str(mock_opc_store_path))
    conn.execute(
        "INSERT INTO tasks (id, title, status) VALUES (?, ?, 'running')",
        (opc_task_id, "Resume OPC Test"),
    )
    conn.execute(
        "INSERT INTO delegation_work_items (work_item_id, title, phase) VALUES (?, ?, 'running')",
        (work_item_id, "Resume OPC Test"),
    )
    conn.commit()
    conn.close()

    # Park task in shadow_store
    task = Task(
        id=opc_task_id,
        title="Resume OPC Test",
        linked_work_item_id=work_item_id,
    )
    adapter = ShadowModeAdapter(shadow_config=shadow_config, shadow_store=shadow_store)
    exec_res = await adapter.execute(task, workspace_path="/tmp")
    shadow_id = exec_res.artifacts["shadow_task_id"]

    # Claim & submit task
    await shadow_store.claim_task(shadow_id, "contractor_resume")
    from shadow_adapter.models import ShadowSubmission
    sub = await shadow_store.submit_task(
        shadow_id,
        "contractor_resume",
        submission=ShadowSubmission(
            deliverable_text="Approved budget report",
            deliverable_files=["budget_v1.pdf"],
        ),
    )

    # Resume task via adapter static method
    resume_res = await ShadowModeAdapter.resume_task(
        shadow_task=sub,
        opc_store_path=mock_opc_store_path,
    )

    assert resume_res.success is True
    assert resume_res.opc_task_status == "done"
    assert resume_res.opc_work_item_phase == "approved"

    # Verify mock store.db tables
    conn = sqlite3.connect(str(mock_opc_store_path))
    task_row = conn.execute("SELECT status FROM tasks WHERE id = ?", (opc_task_id,)).fetchone()
    wi_row = conn.execute("SELECT phase FROM delegation_work_items WHERE work_item_id = ?", (work_item_id,)).fetchone()
    conn.close()

    assert task_row[0] == "done"
    assert wi_row[0] == "approved"
