"""Test suite for ShadowWorker SDK and CLI Daemon for Distributed Nodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from shadow_adapter.adapter import ShadowModeAdapter
from shadow_adapter.api.app import create_app
from shadow_adapter.config import ShadowConfig
from shadow_adapter.models import ShadowTaskStatus
from shadow_adapter.security import SecurityManager
from shadow_adapter.shadow_store import ShadowStore
from shadow_adapter.worker import ShadowWorker

pytestmark = pytest.mark.asyncio


@dataclass
class MockTask:
    id: str = "opc_worker_task_001"
    title: str = "Distributed Compute Contract Review"
    description: str = "Review cloud hosting agreement for compliance."
    assigned_to: str = "legal_counsel"
    status: str = "pending"
    priority: int = 1
    project_id: str = "default"
    metadata: dict = field(default_factory=lambda: {"linked_work_item_id": "wi_legal_999"})
    linked_work_item_id: str = "wi_legal_999"


async def test_worker_login_and_auto_register(
    shadow_config: ShadowConfig,
    shadow_store: ShadowStore,
    security: SecurityManager,
) -> None:
    """Prove worker automatically registers identity and retrieves JWT access token."""
    app = create_app(shadow_config)
    app.state.config = shadow_config
    app.state.shadow_store = shadow_store
    app.state.security = security

    worker = ShadowWorker(
        server_url="http://testserver",
        username="silicon_worker_01",
        password="secure_password_123",
        role="legal_counsel",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        token = await worker.login(client)
        assert token is not None
        assert len(token) > 20
        assert worker.access_token == token


async def test_worker_claim_and_process_task(
    shadow_config: ShadowConfig,
    shadow_store: ShadowStore,
    security: SecurityManager,
    tmp_path: Path,
) -> None:
    """Full end-to-end integration test of a remote ShadowWorker processing a parked task."""
    app = create_app(shadow_config)
    app.state.config = shadow_config
    app.state.shadow_store = shadow_store
    app.state.security = security

    adapter = ShadowModeAdapter(shadow_config=shadow_config, shadow_store=shadow_store)

    # 1. Intercept and park task
    task = MockTask(id="opc_worker_task_001", assigned_to="legal_counsel")
    await adapter.execute(task, workspace_path="/tmp")

    # 2. Instantiate remote ShadowWorker
    worker = ShadowWorker(
        server_url="http://testserver",
        username="remote_legal_node",
        password="password123",
        role="legal_counsel",
        provider="mock",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Process task
        processed = await worker.process_one_task(client)
        assert processed is True

        # Verify task state in ShadowStore
        parked = await shadow_store.get_task_by_opc_id("opc_worker_task_001")
        assert parked is not None
        assert parked.status in (ShadowTaskStatus.SUBMITTED, ShadowTaskStatus.RESUMED, ShadowTaskStatus.FAILED)
        assert parked.deliverable_text is not None
        assert "[DECENTRALIZED SILICON DELIVERABLE]" in parked.deliverable_text


async def test_worker_custom_handler_callback(
    shadow_config: ShadowConfig,
    shadow_store: ShadowStore,
    security: SecurityManager,
) -> None:
    """Prove worker invokes custom Python handler callback when provided."""
    app = create_app(shadow_config)
    app.state.config = shadow_config
    app.state.shadow_store = shadow_store
    app.state.security = security

    adapter = ShadowModeAdapter(shadow_config=shadow_config, shadow_store=shadow_store)

    task = MockTask(
        id="opc_custom_handler_task",
        title="Custom Handler Task",
        description="Execute custom AI pipeline.",
        assigned_to="qa_lead",
    )
    await adapter.execute(task, workspace_path="/tmp")

    async def custom_ai_pipeline(task_dict: dict) -> str:
        return f"CUSTOM_PIPELINE_RESULT for task {task_dict.get('id')}"

    worker = ShadowWorker(
        server_url="http://testserver",
        username="custom_worker",
        password="password123",
        role="qa_lead",
        custom_handler=custom_ai_pipeline,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        processed = await worker.process_one_task(client)
        assert processed is True

        parked = await shadow_store.get_task_by_opc_id("opc_custom_handler_task")
        assert parked is not None
        assert parked.deliverable_text == f"CUSTOM_PIPELINE_RESULT for task {parked.id}"
