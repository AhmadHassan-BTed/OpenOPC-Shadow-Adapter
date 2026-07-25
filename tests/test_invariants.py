"""Stage 4: State Machine Invariants unit tests for HandoffService.

Strictly verifies the state transitions and authorization guards of the
Carbon-Silicon Lifecycle:
- PENDING -> CLAIMED -> SUBMITTED -> RESUMED
- CLAIMED -> PENDING (unclaim)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shadow_adapter.exceptions import (
    TaskNotClaimedError,
    TaskNotFoundError,
    TaskPermissionError,
)
from shadow_adapter.models import ShadowTask, ShadowTaskStatus, UploadLimits
from shadow_adapter.repositories.opc_resume_repo import OpcResumeRepository
from shadow_adapter.services.handoff_service import HandoffService
from shadow_adapter.shadow_store import ShadowStore
from shadow_adapter.upload import SecureUploadHandler

pytestmark = pytest.mark.asyncio


@pytest.fixture
def limits() -> UploadLimits:
    return UploadLimits(
        max_file_count=5,
        max_file_size_bytes=10 * 1024 * 1024,
        max_total_size_bytes=50 * 1024 * 1024,
        allowed_extensions={".txt"},
    )


@pytest.fixture
def handoff(shadow_store: ShadowStore, tmp_path: Path, limits: UploadLimits) -> HandoffService:
    handler = SecureUploadHandler(limits, tmp_path / "invariant_uploads")
    repo = OpcResumeRepository()
    return HandoffService(shadow_store, repo, handler, limits)


async def test_cannot_claim_already_claimed_task(handoff: HandoffService) -> None:
    """Invariant: Cannot claim a task that is already in CLAIMED status."""
    task = ShadowTask(opc_task_id="opc_inv_1", title="Invariant 1")
    parked = await handoff.park_task(task)
    await handoff.claim_task(parked.id, "contractor_1")

    with pytest.raises(ValueError, match="expected 'pending'"):
        await handoff.claim_task(parked.id, "contractor_2")


async def test_cannot_submit_pending_task(handoff: HandoffService) -> None:
    """Invariant: Cannot submit work for a task in PENDING status."""
    task = ShadowTask(opc_task_id="opc_inv_2", title="Invariant 2")
    parked = await handoff.park_task(task)

    with pytest.raises(TaskNotClaimedError):
        await handoff.submit_and_resume(
            task_id=parked.id,
            contractor_id="contractor_1",
            deliverable_text="Text",
            files=[],
            opc_store_path="/tmp/store.db",
        )


async def test_cannot_unclaim_resumed_task(handoff: HandoffService, mock_opc_store_path: Path) -> None:
    """Invariant: Cannot unclaim a task that has reached RESUMED status."""
    task = ShadowTask(opc_task_id="opc_inv_3", title="Invariant 3")
    parked = await handoff.park_task(task)
    await handoff.claim_task(parked.id, "contractor_1")

    res = await handoff.submit_and_resume(
        task_id=parked.id,
        contractor_id="contractor_1",
        deliverable_text="Text",
        files=[],
        opc_store_path=str(mock_opc_store_path),
    )
    assert res.status == ShadowTaskStatus.RESUMED.value

    with pytest.raises(TaskNotClaimedError):
        await handoff.unclaim_task(parked.id, "contractor_1")


async def test_cannot_submit_other_contractors_task(handoff: HandoffService) -> None:
    """Invariant: Cannot submit deliverables for a task claimed by someone else."""
    task = ShadowTask(opc_task_id="opc_inv_4", title="Invariant 4")
    parked = await handoff.park_task(task)
    await handoff.claim_task(parked.id, "contractor_owner")

    with pytest.raises(TaskPermissionError):
        await handoff.submit_and_resume(
            task_id=parked.id,
            contractor_id="contractor_imposter",
            deliverable_text="Text",
            files=[],
            opc_store_path="/tmp/store.db",
        )


async def test_operations_on_non_existent_task_raise_not_found(handoff: HandoffService) -> None:
    """Invariant: Actions on non-existent task IDs raise TaskNotFoundError."""
    fake_id = "non_existent_uuid_9999"

    with pytest.raises(TaskNotFoundError):
        await handoff.get_task(fake_id)

    with pytest.raises(TaskNotFoundError):
        await handoff.claim_task(fake_id, "contractor_1")

    with pytest.raises(TaskNotFoundError):
        await handoff.unclaim_task(fake_id, "contractor_1")

    with pytest.raises(TaskNotFoundError):
        await handoff.submit_and_resume(
            task_id=fake_id,
            contractor_id="contractor_1",
            deliverable_text="Text",
            files=[],
            opc_store_path="/tmp/store.db",
        )

    with pytest.raises(TaskNotFoundError):
        await handoff.get_audit_log(fake_id)
