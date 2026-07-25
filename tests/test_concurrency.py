"""Stage 1: Concurrency & Race Condition Crucible tests.

Proves that simultaneous lock contentions and asynchronous execution races
are handled safely by isolated SQLite WAL mode transactions and state machine guards.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from shadow_adapter.exceptions import TaskNotClaimedError, TaskPermissionError
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
        allowed_extensions={".txt", ".pdf"},
    )


@pytest.fixture
def handoff(shadow_store: ShadowStore, tmp_path: Path, limits: UploadLimits) -> HandoffService:
    handler = SecureUploadHandler(limits, tmp_path / "uploads")
    repo = OpcResumeRepository()
    return HandoffService(
        shadow_store=shadow_store,
        opc_resume_repo=repo,
        upload_handler=handler,
        upload_limits=limits,
    )


async def test_double_claim_race(handoff: HandoffService) -> None:
    """Simulate two carbon contractors claiming the exact same task simultaneously."""
    task = ShadowTask(opc_task_id="opc_race_1", title="Race Condition Task")
    parked = await handoff.park_task(task)

    # Launch two simultaneous claim requests
    results = await asyncio.gather(
        handoff.claim_task(parked.id, "contractor_alpha"),
        handoff.claim_task(parked.id, "contractor_beta"),
        return_exceptions=True,
    )

    # Exactly one claim must succeed, and one must fail with a ValueError
    successes = [r for r in results if isinstance(r, ShadowTask)]
    failures = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1
    assert len(failures) == 1
    assert isinstance(failures[0], ValueError)
    assert "expected 'pending'" in str(failures[0])

    # Verify state in store is cleanly claimed by the winner
    final_task = await handoff.get_task(parked.id)
    assert final_task.status == ShadowTaskStatus.CLAIMED
    assert final_task.assigned_contractor_id in ("contractor_alpha", "contractor_beta")


async def test_submit_while_unclaiming_race(handoff: HandoffService) -> None:
    """Simulate a network race where a contractor unclaims while submitting."""
    task = ShadowTask(opc_task_id="opc_race_2", title="Unclaim vs Submit Race")
    parked = await handoff.park_task(task)
    await handoff.claim_task(parked.id, "contractor_alpha")

    # Launch simultaneous unclaim and submit
    results = await asyncio.gather(
        handoff.unclaim_task(parked.id, "contractor_alpha"),
        handoff.submit_and_resume(
            task_id=parked.id,
            contractor_id="contractor_alpha",
            deliverable_text="Race deliverable",
            files=[],
            opc_store_path="/nonexistent/path.db",
        ),
        return_exceptions=True,
    )

    # Exactly one succeeds, the other fails with TaskNotClaimedError or TaskPermissionError
    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1
    assert len(failures) == 1
    assert isinstance(failures[0], (TaskNotClaimedError, TaskPermissionError, ValueError))


async def test_concurrent_task_parking(handoff: HandoffService) -> None:
    """Simulate 20 silicon tasks being parked concurrently into SQLite WAL store."""
    tasks = [ShadowTask(opc_task_id=f"opc_bulk_{i}", title=f"Bulk Task {i}") for i in range(20)]

    parked_tasks = await asyncio.gather(*[handoff.park_task(t) for t in tasks])

    assert len(parked_tasks) == 20
    all_tasks = await handoff.list_tasks(limit=100)
    assert len(all_tasks) == 20
