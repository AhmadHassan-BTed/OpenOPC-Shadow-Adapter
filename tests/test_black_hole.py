"""Stage 3: Exception Black Hole Verification tests.

Proves that infrastructure and repository failures (missing databases, locked files,
upload stream corruption) are safely trapped and contained without ever crashing
the host OpenOPC runtime engine.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from shadow_adapter.adapter import ShadowModeAdapter
from shadow_adapter.models import (
    ShadowTask,
    ShadowTaskStatus,
    UploadFileDTO,
    UploadLimits,
)
from shadow_adapter.repositories.opc_resume_repo import OpcResumeRepository
from shadow_adapter.services.handoff_service import HandoffService
from shadow_adapter.shadow_store import ShadowStore
from shadow_adapter.upload import SecureUploadHandler, UploadValidationError

pytestmark = pytest.mark.asyncio


@pytest.fixture
def limits() -> UploadLimits:
    return UploadLimits(
        max_file_count=2,
        max_file_size_bytes=100,  # Tiny 100-byte limit for test
        max_total_size_bytes=200,
        allowed_extensions={".txt"},
    )


@pytest.fixture
def handoff(shadow_store: ShadowStore, tmp_path: Path, limits: UploadLimits) -> HandoffService:
    handler = SecureUploadHandler(limits, tmp_path / "black_hole_uploads")
    repo = OpcResumeRepository()
    return HandoffService(shadow_store, repo, handler, limits)


async def test_missing_store_db_black_hole(handoff: HandoffService, shadow_store: ShadowStore) -> None:
    """Missing OpenOPC store.db should mark task as FAILED without raising an unhandled exception."""
    task = ShadowTask(opc_task_id="opc_missing_db", title="Missing DB Test")
    parked = await handoff.park_task(task)
    await handoff.claim_task(parked.id, "contractor_1")

    res = await handoff.submit_and_resume(
        task_id=parked.id,
        contractor_id="contractor_1",
        deliverable_text="Deliverable text",
        files=[],
        opc_store_path="/invalid/directory/that/does/not/exist/store.db",
    )

    assert res.status == ShadowTaskStatus.FAILED.value
    assert res.opc_resume_status == "failed"
    assert "not found" in res.message.lower()

    # Task status in ShadowStore must be FAILED
    updated_task = await shadow_store.get_task(parked.id)
    assert updated_task is not None
    assert updated_task.status == ShadowTaskStatus.FAILED
    assert "failure_reason" in updated_task.extra_metadata


async def test_corrupt_oversized_upload_cleanup(handoff: HandoffService, shadow_store: ShadowStore) -> None:
    """Oversized file upload stream should be aborted, cleaned up, and task left in CLAIMED state."""
    task = ShadowTask(opc_task_id="opc_upload_cleanup", title="Upload Cleanup Test")
    parked = await handoff.park_task(task)
    await handoff.claim_task(parked.id, "contractor_1")

    # File exceeding 100-byte limit
    oversized_file = UploadFileDTO(
        filename="big_payload.txt",
        content=b"X" * 500,
        size=500,
    )

    with pytest.raises(UploadValidationError, match="exceeds individual size limit"):
        await handoff.submit_and_resume(
            task_id=parked.id,
            contractor_id="contractor_1",
            deliverable_text="Text",
            files=[oversized_file],
            opc_store_path="/invalid/store.db",
        )

    # Task remains in CLAIMED state so contractor can retry
    task_after = await shadow_store.get_task(parked.id)
    assert task_after is not None
    assert task_after.status == ShadowTaskStatus.CLAIMED


async def test_adapter_execute_exception_black_hole() -> None:
    """Critical store failure during ShadowModeAdapter.execute must return TaskStatus.FAILED, never crash."""
    adapter = ShadowModeAdapter()

    # Mock store to raise an unexpected Exception during execution
    mock_store = AsyncMock()
    mock_store.get_task_by_opc_id.side_effect = RuntimeError("Database connection string corrupted")
    adapter._shadow_store = mock_store

    from shadow_adapter.adapter import Task

    fake_opc_task = Task(id="opc_crash_test", title="Crash Test Task")

    # Execute intercept
    result = await adapter.execute(fake_opc_task, workspace_path="/tmp")

    # Result must be FAILED, not an unhandled exception
    assert result.status == "failed"
    assert "Database connection string corrupted" in result.content
