"""Stage 1-4: Host Integration & Symbiote Crucible tests.

Mathematical proof that openopc-shadow-adapter:
1. Survives upstream OpenOPC engine schema and signature mutations (Future-Proofing).
2. Does NOT block parallel AI DAG execution threads (Zero Thread Starvation).
3. Executes the End-to-End Temporal Bridge handoff from HTTP client to OpenOPC SQLite WAL store.
4. Traps state machine poisoning (orphaned tasks) gracefully without host engine crashes.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from shadow_adapter.adapter import ShadowModeAdapter
from shadow_adapter.api.app import create_app
from shadow_adapter.config import ShadowConfig
from shadow_adapter.models import ShadowTask, ShadowTaskStatus, UploadLimits
from shadow_adapter.repositories.opc_resume_repo import OpcResumeRepository
from shadow_adapter.security import SecurityManager
from shadow_adapter.services.handoff_service import HandoffService
from shadow_adapter.shadow_store import ShadowStore
from shadow_adapter.upload import SecureUploadHandler

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Synthetic Host Mocks
# ---------------------------------------------------------------------------


@dataclass
class SyntheticMutatedTask:
    """Synthetic OpenOPC Task model mimicking future upstream schema additions."""

    id: str
    session_id: str = "sess_999"
    title: str = "Mutated Task"
    description: str = "Testing schema mutations"
    assigned_to: str = "qa_lead"
    status: Any = "FUTURE_UNKNOWN_STATUS_ENUM"
    priority: int = 1
    project_id: str = "project_future"
    metadata: dict = field(
        default_factory=lambda: {
            "work_item_id": "wi_mutated_123",
            **{f"future_field_{i}": f"data_{i}" for i in range(50)},
        }
    )
    linked_work_item_id: str = "wi_mutated_123"
    # Undocumented attributes attached by future engine
    future_vector_embedding: list[float] = field(default_factory=lambda: [0.1, 0.2, 0.3])
    future_agent_cost_limit: float = 99.99


class MockOpenOPCEngine:
    """Lightweight simulation of OpenOPC's asynchronous DAG execution engine."""

    def __init__(self, shadow_adapter: ShadowModeAdapter) -> None:
        self.shadow_adapter = shadow_adapter

    async def run_ai_task(self, task_id: str, sleep_duration: float = 0.100) -> dict:
        """Simulate a fast AI agent task (e.g., Code Gen, Data Fetch)."""
        await asyncio.sleep(sleep_duration)
        return {"task_id": task_id, "status": "done", "cost": 0.002}

    async def run_shadow_task(self, task: SyntheticMutatedTask) -> dict:
        """Execute a human-in-the-loop task intercepted by ShadowModeAdapter."""
        result = await self.shadow_adapter.execute(task, workspace_path="/tmp")
        return {"task_id": task.id, "status": result.status, "content": result.content}

    async def execute_dag_branches(
        self,
        task_a_id: str,
        shadow_task: SyntheticMutatedTask,
        task_c_id: str,
    ) -> dict[str, Any]:
        """Execute 3 DAG branches concurrently (AI -> Human Shadow -> AI)."""
        results = await asyncio.gather(
            self.run_ai_task(task_a_id, sleep_duration=0.100),
            self.run_shadow_task(shadow_task),
            self.run_ai_task(task_c_id, sleep_duration=0.100),
        )
        return {
            "task_a": results[0],
            "task_b": results[1],
            "task_c": results[2],
        }


# ---------------------------------------------------------------------------
# STAGE 1: HOST MUTATION SURVIVAL
# ---------------------------------------------------------------------------


async def test_unknown_kwargs_bomb(shadow_store: ShadowStore, tmp_path: Path) -> None:
    """Prove adapter swallows 50 undocumented task fields and extra execution kwargs."""
    config = ShadowConfig(db_path=str(tmp_path / "mutation_test.db"))
    adapter = ShadowModeAdapter(shadow_config=config, shadow_store=shadow_store)

    mutated_task = SyntheticMutatedTask(id="opc_mutated_001")

    # Pass unexpected **kwargs into execute() via method reference dispatch
    extra_execute_kwargs = {
        "unexpected_future_engine_param": "future_val",
        "callback_url": "http://engine.internal/callback",
        "retry_count": 3,
    }
    execute_fn = adapter.execute
    result = await execute_fn(
        mutated_task,
        "/tmp",
        **extra_execute_kwargs,
    )

    assert result.status == "awaiting_human"
    assert result.artifacts["opc_task_id"] == "opc_mutated_001"
    assert "Shadow Task ID:" in result.content

    # Verify task was parked in ShadowStore cleanly with metadata fallback
    parked = await shadow_store.get_task_by_opc_id("opc_mutated_001")
    assert parked is not None
    assert parked.opc_work_item_id == "wi_mutated_123"
    assert parked.opc_metadata["future_field_0"] == "data_0"


async def test_signature_survival() -> None:
    """Prove adapter lifecycle methods accept unexpected keyword arguments without TypeError."""
    adapter = ShadowModeAdapter()
    mutated_task = SyntheticMutatedTask(id="opc_sig_001")

    avail_fn = adapter.is_available
    avail_kwargs = {"future_engine_flag": True, "timeout": 5}
    assert await avail_fn(**avail_kwargs) is True

    status_fn = adapter.get_status
    status_kwargs = {"engine_version": "v2.5", "debug": True}
    assert await status_fn(**status_kwargs) == "idle"

    build_fn = adapter.build_invocation
    build_kwargs = {"extra_opt": "opt_val"}
    cmd, env = build_fn(
        mutated_task,
        "/tmp",
        **build_kwargs,
    )
    assert cmd == []
    assert env["mode"] == "shadow_human_in_loop"


# ---------------------------------------------------------------------------
# STAGE 2: PARALLEL DAG SURVIVAL (Zero Thread Starvation)
# ---------------------------------------------------------------------------


async def test_parallel_dag_branch_execution(shadow_store: ShadowStore, tmp_path: Path) -> None:
    """Prove that parking a human task does NOT block parallel AI tasks in the DAG."""
    config = ShadowConfig(db_path=str(tmp_path / "dag_test.db"))
    adapter = ShadowModeAdapter(shadow_config=config, shadow_store=shadow_store)
    engine = MockOpenOPCEngine(adapter)

    shadow_task = SyntheticMutatedTask(id="opc_human_branch")

    start_time = time.monotonic()
    results = await engine.execute_dag_branches(
        task_a_id="ai_branch_a",
        shadow_task=shadow_task,
        task_c_id="ai_branch_c",
    )
    elapsed = time.monotonic() - start_time

    # Parallel execution must complete in ~100ms (not 200ms+ serial time)
    assert elapsed < 0.250, f"DAG execution took {elapsed:.3f}s (expected parallel < 0.250s)"

    # AI branches completed; Human branch instantly returned awaiting_human
    assert results["task_a"]["status"] == "done"
    assert results["task_b"]["status"] == "awaiting_human"
    assert results["task_c"]["status"] == "done"


# ---------------------------------------------------------------------------
# STAGE 3: THE TEMPORAL BRIDGE E2E
# ---------------------------------------------------------------------------


async def test_temporal_bridge_end_to_end(
    shadow_config: ShadowConfig,
    mock_opc_store_path: Path,
) -> None:
    """Full End-to-End test of the Carbon-Silicon handoff bridge via HTTP API."""
    import aiosqlite

    # Seed task row in OpenOPC database beforehand
    async with aiosqlite.connect(str(mock_opc_store_path)) as db:
        await db.execute(
            "INSERT INTO tasks (id, status, title) VALUES (?, 'pending', 'E2E Task')",
            ("opc_e2e_task_123",),
        )
        await db.commit()

    app = create_app(shadow_config)

    store = ShadowStore(shadow_config.db_path)
    await store.initialize()
    sec = SecurityManager(shadow_config)
    app.state.config = shadow_config
    app.state.shadow_store = store
    app.state.security = sec
    app.state.upload_handler = SecureUploadHandler(shadow_config)

    adapter = ShadowModeAdapter(shadow_config=shadow_config, shadow_store=store)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Step 1 (Silicon): Intercept AI task and park in adapter
        opc_task = SyntheticMutatedTask(id="opc_e2e_task_123")
        exec_result = await adapter.execute(opc_task, workspace_path="/tmp")
        assert exec_result.status == "awaiting_human"

        parked_task = await store.get_task_by_opc_id("opc_e2e_task_123")
        assert parked_task is not None
        shadow_id = parked_task.id

        # Step 2 (Carbon): Register contractor, login, claim task, submit deliverable
        reg_res = await client.post(
            "/api/auth/register",
            json={"username": "carbon_worker", "password": "password123", "email": "worker@co.com"},
        )
        assert reg_res.status_code == 201

        login_res = await client.post(
            "/api/auth/login",
            json={"username": "carbon_worker", "password": "password123"},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Claim
        claim_res = await client.post(f"/api/tasks/{shadow_id}/claim", headers=headers)
        assert claim_res.status_code == 200
        assert claim_res.json()["status"] == "claimed"

        # Submit deliverable
        submit_res = await client.post(
            f"/api/tasks/{shadow_id}/submit",
            headers=headers,
            data={"deliverable_text": "Completed legal compliance review for AI DAG."},
        )
        assert submit_res.status_code == 200
        body = submit_res.json()
        assert body["status"] == "resumed"
        assert body["opc_resume_status"] == "success"

        # Step 3 (The Resume Trigger): Verify direct WAL write to OpenOPC store.db
        async with aiosqlite.connect(str(mock_opc_store_path)) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM tasks WHERE id = 'opc_e2e_task_123'") as cursor:
                row = await cursor.fetchone()
                assert row is not None
                assert row["status"] == "done"
                assert "Completed legal compliance review" in row["result"]

    await store.close()


# ---------------------------------------------------------------------------
# STAGE 4: STATE MACHINE POISONING (Desynced Host Database)
# ---------------------------------------------------------------------------


async def test_desynced_host_database_poisoning(
    shadow_store: ShadowStore,
    tmp_path: Path,
) -> None:
    """Human submits deliverable, but OpenOPC store.db is missing or corrupted.

    Prove OpcResumeRepository traps the exception, marks shadow task as FAILED,
    and returns graceful error status without crashing the server.
    """
    limits = UploadLimits(
        max_file_count=5,
        max_file_size_bytes=10 * 1024 * 1024,
        max_total_size_bytes=50 * 1024 * 1024,
        allowed_extensions={".txt"},
    )
    handler = SecureUploadHandler(limits, tmp_path / "poison_uploads")
    repo = OpcResumeRepository()
    handoff = HandoffService(shadow_store, repo, handler, limits)

    # Task exists in ShadowStore, but target opc_store_path does not exist
    task = ShadowTask(opc_task_id="opc_deleted_by_admin_999", title="Poisoned Task")
    parked = await handoff.park_task(task)
    await handoff.claim_task(parked.id, "contractor_1")

    # Submit deliverable
    result = await handoff.submit_and_resume(
        task_id=parked.id,
        contractor_id="contractor_1",
        deliverable_text="Deliverable for wiped task",
        files=[],
        opc_store_path="/nonexistent/directory/store.db",
    )

    # OpcResumeRepository caught missing DB, task marked as FAILED cleanly
    assert result.status == ShadowTaskStatus.FAILED.value
    assert result.opc_resume_status == "failed"
    assert "not found" in result.message.lower()

    failed_task = await shadow_store.get_task(parked.id)
    assert failed_task is not None
    assert failed_task.status == ShadowTaskStatus.FAILED
