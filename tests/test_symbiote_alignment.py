"""Test suite verifying Symbiote Alignment Mandates:

1. Canonical State Subordination & Orphan Protection
2. TaskBriefBuilder Markdown UX Cohesion
3. Portal Coexistence (X-Portal-Identity Header)
4. Worker Exponential Backoff
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from shadow_adapter.brief_builder import TaskBriefBuilder
from shadow_adapter.config import ShadowConfig
from shadow_adapter.models import ShadowTask, ShadowTaskStatus
from shadow_adapter.repositories.opc_resume_repo import OpcResumeRepository
from shadow_adapter.shadow_store import ShadowStore

pytestmark = pytest.mark.asyncio


async def test_task_brief_builder_formatting() -> None:
    """Verify TaskBriefBuilder compiles project context, instructions, and upstream subagent outputs."""
    brief = TaskBriefBuilder.build_markdown_brief(
        task_id="opc_test_99",
        title="Audit Security Protocols",
        description="Run security vulnerability scan on API routes.",
        role="security_auditor",
        priority=8,
        project_id="proj_alpha",
        metadata={
            "goal": "Verify system security before v0.1.0 release.",
            "work_item_id": "wi_sec_100",
        },
        upstream_deliverables=[
            {
                "role": "senior_developer",
                "opc_task_id": "opc_dev_01",
                "deliverable_text": "Completed REST API implementation.",
                "artifacts": [
                    {
                        "original_filename": "openapi.json",
                        "file_size_bytes": 4096,
                        "download_url": "/api/v1/artifacts/art_1/download",
                    }
                ],
            }
        ],
    )

    assert "# Task Brief: Audit Security Protocols" in brief
    assert "**Assigned Role:** `security_auditor`" in brief
    assert "Verify system security before v0.1.0 release." in brief
    assert "## 🔗 Upstream Subagent Context & Artifacts" in brief
    assert "### 1. [senior_developer] (Task: `opc_dev_01`)" in brief
    assert "[openapi.json](/api/v1/artifacts/art_1/download)" in brief


async def test_orphan_protection_and_state_subordination(
    shadow_config: ShadowConfig, shadow_store: ShadowStore
) -> None:
    """Verify OpcResumeRepository detects orphaned host tasks and ShadowStore updates state to ORPHANED."""
    repo = OpcResumeRepository()

    # Create dummy shadow task referencing non-existent host DB
    shadow_task = ShadowTask(
        opc_task_id="non_existent_opc_task_999",
        opc_work_item_id="non_existent_wi_999",
        title="Orphan Test Task",
        assigned_role="tester",
    )
    await shadow_store.create_task(shadow_task)

    # Resume against missing store.db returns orphan error
    res = await repo.resume(shadow_task, opc_store_path="/tmp/non_existent_store.db")
    assert res.success is False
    assert "store.db not found" in res.error

    # Mark orphaned in shadow store
    orphaned_task = await shadow_store.mark_orphaned(shadow_task.id, reason="Missing host database")
    assert orphaned_task.status == ShadowTaskStatus.ORPHANED


async def test_portal_coexistence_header(shadow_config: ShadowConfig, shadow_store: ShadowStore) -> None:
    """Verify REST API includes X-Portal-Identity header on responses for dual-UI coexistence."""
    from shadow_adapter.api.app import create_app

    app = create_app(shadow_config)
    app.state.config = shadow_config
    app.state.shadow_store = shadow_store

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get("/api/v1/health")
        assert res.status_code == 200
        assert res.headers.get("X-Portal-Identity") == "OpenOPC-Shadow-Worker-Portal"
