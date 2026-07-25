"""Unit tests for isolated ShadowStore SQLite CRUD operations and audit logging."""

from __future__ import annotations

import uuid
import pytest
from shadow_adapter.models import (
    ShadowContractor,
    ShadowSubmission,
    ShadowTask,
    ShadowTaskStatus,
)
from shadow_adapter.shadow_store import ShadowStore

pytestmark = pytest.mark.asyncio


async def test_create_and_get_task(shadow_store: ShadowStore) -> None:
    """Test creating a ShadowTask and retrieving it by ID and by OPC Task ID."""
    task = ShadowTask(
        opc_task_id="opc_task_123",
        opc_session_id="session_abc",
        title="Test Security Audit",
        description="Audit python codebase",
        assigned_role="security_lead",
        priority=3,
    )

    created = await shadow_store.create_task(task)
    assert created.id == task.id
    assert created.status == ShadowTaskStatus.PENDING

    # Retrieve by shadow task ID
    fetched = await shadow_store.get_task(task.id)
    assert fetched is not None
    assert fetched.title == "Test Security Audit"
    assert fetched.opc_task_id == "opc_task_123"

    # Retrieve by OPC Task ID
    fetched_opc = await shadow_store.get_task_by_opc_id("opc_task_123")
    assert fetched_opc is not None
    assert fetched_opc.id == task.id


async def test_list_tasks_and_filter(shadow_store: ShadowStore) -> None:
    """Test task listing, status filtering, and contractor filtering."""
    t1 = ShadowTask(opc_task_id="opc_1", title="Task 1", status=ShadowTaskStatus.PENDING)
    t2 = ShadowTask(opc_task_id="opc_2", title="Task 2", status=ShadowTaskStatus.PENDING)
    t3 = ShadowTask(opc_task_id="opc_3", title="Task 3", status=ShadowTaskStatus.PENDING)

    await shadow_store.create_task(t1)
    await shadow_store.create_task(t2)
    await shadow_store.create_task(t3)

    tasks = await shadow_store.list_tasks(status="pending")
    assert len(tasks) == 3

    # Claim task t1 for contractor_a
    await shadow_store.claim_task(t1.id, "contractor_a")

    pending_tasks = await shadow_store.list_tasks(status="pending")
    assert len(pending_tasks) == 2

    claimed_tasks = await shadow_store.list_tasks(status="claimed", contractor_id="contractor_a")
    assert len(claimed_tasks) == 1
    assert claimed_tasks[0].id == t1.id


async def test_claim_and_unclaim_task(shadow_store: ShadowStore) -> None:
    """Test claiming a pending task and releasing (unclaiming) it."""
    task = ShadowTask(opc_task_id="opc_claim_test", title="Claim Test")
    await shadow_store.create_task(task)

    # Claim task
    claimed = await shadow_store.claim_task(task.id, "contractor_x")
    assert claimed.status == ShadowTaskStatus.CLAIMED
    assert claimed.assigned_contractor_id == "contractor_x"
    assert claimed.claimed_at is not None

    # Double claim should fail
    with pytest.raises(ValueError, match="expected 'pending'"):
        await shadow_store.claim_task(task.id, "contractor_y")

    # Unclaim task
    unclaimed = await shadow_store.unclaim_task(task.id, "contractor_x")
    assert unclaimed.status == ShadowTaskStatus.PENDING
    assert unclaimed.assigned_contractor_id is None
    assert unclaimed.claimed_at is None


async def test_submit_and_mark_resumed(shadow_store: ShadowStore) -> None:
    """Test task submission by contractor and transition to resumed."""
    task = ShadowTask(opc_task_id="opc_submit_test", title="Submit Test")
    await shadow_store.create_task(task)
    await shadow_store.claim_task(task.id, "contractor_z")

    submission = ShadowSubmission(
        deliverable_text="Detailed report content",
        deliverable_files=["file1.pdf", "file2.docx"],
    )

    submitted = await shadow_store.submit_task(task.id, "contractor_z", submission)
    assert submitted.status == ShadowTaskStatus.SUBMITTED
    assert submitted.deliverable_text == "Detailed report content"
    assert submitted.deliverable_files == ["file1.pdf", "file2.docx"]
    assert submitted.submitted_at is not None

    resumed = await shadow_store.mark_resumed(task.id)
    assert resumed.status == ShadowTaskStatus.RESUMED
    assert resumed.resumed_at is not None


async def test_audit_log_triggers(shadow_store: ShadowStore) -> None:
    """Test that mutating task actions generate an audit log entry."""
    task = ShadowTask(opc_task_id="opc_audit_test", title="Audit Test")
    await shadow_store.create_task(task)
    await shadow_store.claim_task(task.id, "contractor_audit")

    logs = await shadow_store.get_audit_log(task.id)
    assert len(logs) == 2
    assert logs[0].action == "created"
    assert logs[1].action == "claimed"
    assert logs[1].actor_id == "contractor_audit"


async def test_contractor_crud(shadow_store: ShadowStore) -> None:
    """Test contractor account creation and duplicate username check."""
    c = ShadowContractor(
        username="john_doe",
        email="john@example.com",
        password_hash="hash123",
        display_name="John Doe",
    )
    created = await shadow_store.create_contractor(c)
    assert created.username == "john_doe"

    fetched = await shadow_store.get_contractor_by_username("john_doe")
    assert fetched is not None
    assert fetched.id == c.id

    # Duplicate username should raise Exception
    c_dup = ShadowContractor(
        username="john_doe",
        email="john2@example.com",
        password_hash="hash456",
    )
    with pytest.raises(Exception):
        await shadow_store.create_contractor(c_dup)
