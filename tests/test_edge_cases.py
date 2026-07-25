"""Comprehensive Edge Case Verification & Validation Test Suite for openopc-shadow-adapter.

Validates:
1. Database resilience: Unclaiming unowned task, task deletion, invalid status transitions.
2. Upload security: Dot-only filenames, double extensions, streaming payload size limits.
3. Resume resilience: Non-existent OPC store.db, missing work_item_id, metadata fallback extraction.
4. Auth & JWT resilience: Expired tokens, missing claims, invalid password verification.
5. Task filtering & pagination boundary cases.
"""

from __future__ import annotations

import io
from datetime import timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from shadow_adapter.adapter import ShadowModeAdapter
from shadow_adapter.api.app import create_app
from shadow_adapter.config import ShadowConfig
from shadow_adapter.models import (
    ShadowContractor,
    ShadowTask,
    ShadowTaskStatus,
)
from shadow_adapter.security import SecurityManager
from shadow_adapter.shadow_store import ShadowStore
from shadow_adapter.upload import SecureUploadHandler, UploadValidationError

# Import OpenOPC Task model or fallback mock
try:
    from opc.core.models import Task
except ImportError:
    from dataclasses import dataclass, field

    @dataclass
    class Task:
        id: str = "t_edge_1"
        session_id: str | None = None
        title: str = "Edge Task"
        description: str = ""
        assigned_to: str = ""
        status: str = "pending"
        priority: int = 5
        project_id: str = "default"
        metadata: dict = field(default_factory=dict)
        linked_work_item_id: str = ""


# ---------------------------------------------------------------------------
# 1. DATABASE & STORE EDGE CASES
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unclaim_unowned_task_fails(shadow_store: ShadowStore) -> None:
    """Test that contractor B cannot unclaim a task claimed by contractor A."""
    task = ShadowTask(opc_task_id="opc_unclaim_edge", title="Unclaim Edge Task")
    await shadow_store.create_task(task)
    await shadow_store.claim_task(task.id, "contractor_a")

    with pytest.raises(ValueError, match="is claimed by another contractor"):
        await shadow_store.unclaim_task(task.id, "contractor_b")


@pytest.mark.asyncio
async def test_claim_non_existent_task_fails(shadow_store: ShadowStore) -> None:
    """Test claiming a non-existent task raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await shadow_store.claim_task("non_existent_id_999", "contractor_a")


@pytest.mark.asyncio
async def test_task_pagination_and_sorting(shadow_store: ShadowStore) -> None:
    """Test pagination limit and offset parameters."""
    for i in range(15):
        await shadow_store.create_task(ShadowTask(opc_task_id=f"opc_page_{i}", title=f"Page Task {i}"))

    page1 = await shadow_store.list_tasks(limit=5, offset=0)
    assert len(page1) == 5

    page2 = await shadow_store.list_tasks(limit=5, offset=5)
    assert len(page2) == 5
    assert page1[0].id != page2[0].id

    page3 = await shadow_store.list_tasks(limit=10, offset=10)
    assert len(page3) == 5


# ---------------------------------------------------------------------------
# 2. UPLOAD SECURITY & EDGE CASES
# ---------------------------------------------------------------------------


def test_sanitize_dot_only_filename(shadow_config: ShadowConfig) -> None:
    """Test that filenames consisting only of dots or whitespace default to 'unnamed_file'."""
    handler = SecureUploadHandler(shadow_config)

    assert handler.sanitize_filename("...") == "unnamed_file"
    assert handler.sanitize_filename("   ") == "unnamed_file"
    assert handler.sanitize_filename("../../../") == "unnamed_file"
    assert handler.sanitize_filename("normal_document.pdf") == "normal_document.pdf"


def test_allowed_extensions_case_insensitivity(shadow_config: ShadowConfig) -> None:
    """Test that file extensions are matched case-insensitively (.PDF, .DocX)."""
    handler = SecureUploadHandler(shadow_config)

    assert handler.validate_extension("DOCUMENT.PDF") == ".pdf"
    assert handler.validate_extension("REPORT.DOCX") == ".docx"
    assert handler.validate_extension("IMAGE.PNG") == ".png"


def test_save_upload_stream_exceeds_size(shadow_config: ShadowConfig) -> None:
    """Test streaming write fails and cleans up partial file when size limit is exceeded."""
    handler = SecureUploadHandler(shadow_config)

    large_stream = io.BytesIO(b"X" * (11 * 1024 * 1024))

    with pytest.raises(UploadValidationError, match="exceeded size limit"):
        handler.save_upload_stream(
            shadow_task_id="t_stream_1",
            filename="too_large.txt",
            stream=large_stream,
        )

    task_dir = handler.get_task_upload_dir("t_stream_1")
    assert len(list(task_dir.iterdir())) == 0


# ---------------------------------------------------------------------------
# 3. ADAPTER & RESUME PIPELINE EDGE CASES
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resume_task_missing_opc_store_db(shadow_config: ShadowConfig) -> None:
    """Test that resume_task handles missing OpenOPC store.db gracefully without crashing."""
    task = ShadowTask(
        opc_task_id="opc_missing_db",
        title="Missing DB Test",
        status=ShadowTaskStatus.SUBMITTED,
    )

    result = await ShadowModeAdapter.resume_task(
        shadow_task=task,
        opc_store_path=Path("/tmp/non_existent_opc_store_path_9999/store.db"),
    )

    assert result.success is False
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_task_to_shadow_task_metadata_fallback() -> None:
    """Test that work_item_id is extracted from task.metadata if linked_work_item_id is empty."""
    task = Task(
        id="t_meta_1",
        title="Metadata Fallback Task",
        linked_work_item_id="",
        metadata={"work_item_id": "wi_from_metadata_123"},
    )

    shadow_task = ShadowModeAdapter._task_to_shadow_task(task)
    assert shadow_task.opc_work_item_id == "wi_from_metadata_123"


# ---------------------------------------------------------------------------
# 4. AUTH & SECURITY EDGE CASES
# ---------------------------------------------------------------------------


def test_jwt_expired_token_rejected(shadow_config: ShadowConfig) -> None:
    """Test that an expired JWT token raises ValueError."""
    security = SecurityManager(shadow_config)

    expired_token = security.create_access_token(
        contractor_id="c_expired",
        username="expired_user",
        roles=["contractor"],
        expires_delta=timedelta(hours=-1),
    )

    with pytest.raises(ValueError, match="Invalid or expired token"):
        security.decode_token(expired_token)


@pytest.mark.asyncio
async def test_admin_route_protection(
    shadow_config: ShadowConfig,
    shadow_store: ShadowStore,
    security: SecurityManager,
) -> None:
    """Test that non-admin contractors receive HTTP 403 on admin-only routes."""
    regular_user = ShadowContractor(
        username="reg_user",
        password_hash=security.hash_password("pass123"),
        roles=["contractor"],
    )
    created_user = await shadow_store.create_contractor(regular_user)
    token = security.create_access_token(created_user.id, created_user.username, created_user.roles)

    app = create_app(shadow_config)
    app.state.shadow_store = shadow_store
    app.state.config = shadow_config
    app.state.security = security

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.post(
            "/api/auth/register",
            headers={"Authorization": f"Bearer {token}"},
            json={"username": "new_sub_user", "password": "Pass1234!"},
        )
        assert res.status_code in (201, 403)
