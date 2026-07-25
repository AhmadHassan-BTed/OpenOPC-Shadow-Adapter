"""Integration tests for FastAPI endpoints and upload security guardrails."""

from __future__ import annotations

import io
import pytest
from httpx import AsyncClient
from shadow_adapter.models import ShadowContractor, ShadowTask, ShadowTaskStatus
from shadow_adapter.shadow_store import ShadowStore

pytestmark = pytest.mark.asyncio


async def test_health_check_endpoint(client: AsyncClient) -> None:
    """Test public health check endpoint."""
    res = await client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["db"] == "connected"
    assert "pending_tasks" in data


async def test_auth_flow_login_register(client: AsyncClient) -> None:
    """Test contractor registration and login flow."""
    # Register first user -> becomes admin automatically
    reg_res = await client.post("/api/auth/register", json={
        "username": "admin_user",
        "password": "Password123!",
        "email": "admin@example.com",
    })
    assert reg_res.status_code == 201
    admin_data = reg_res.json()
    assert admin_data["username"] == "admin_user"
    assert "admin" in admin_data["roles"]

    # Login
    login_res = await client.post("/api/auth/login", json={
        "username": "admin_user",
        "password": "Password123!",
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["token_type"] == "bearer"

    # Test /api/auth/me with Bearer token
    token = login_data["access_token"]
    me_res = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "admin_user"


async def test_task_lifecycle_api(
    client: AsyncClient,
    shadow_store: ShadowStore,
    auth_headers: dict[str, str],
) -> None:
    """Test full task lifecycle via API: list -> claim -> submit -> resume."""
    # Seed a task in shadow_store
    task = ShadowTask(
        opc_task_id="opc_api_100",
        title="API Integration Test Task",
        description="Verify task lifecycle endpoints",
        assigned_role="qa_tester",
    )
    await shadow_store.create_task(task)

    # 1. List tasks
    list_res = await client.get("/api/tasks", headers=auth_headers)
    assert list_res.status_code == 200
    tasks = list_res.json()
    assert len(tasks) == 1
    assert tasks[0]["id"] == task.id

    # 2. Get task detail
    detail_res = await client.get(f"/api/tasks/{task.id}", headers=auth_headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["title"] == "API Integration Test Task"

    # 3. Claim task
    claim_res = await client.post(f"/api/tasks/{task.id}/claim", headers=auth_headers)
    assert claim_res.status_code == 200
    assert claim_res.json()["status"] == "claimed"

    # 4. Submit task with deliverable text and 1 valid attachment file
    file_payload = ("test_report.pdf", b"%PDF-1.4 Mock PDF Content", "application/pdf")
    submit_res = await client.post(
        f"/api/tasks/{task.id}/submit",
        headers=auth_headers,
        data={"deliverable_text": "QA testing completed successfully."},
        files=[("files", file_payload)],
    )
    assert submit_res.status_code == 200
    sub_data = submit_res.json()
    assert sub_data["status"] == "resumed"
    assert sub_data["opc_resume_status"] == "success"

    # 5. Check audit trail
    audit_res = await client.get(f"/api/tasks/{task.id}/audit", headers=auth_headers)
    assert audit_res.status_code == 200
    actions = [entry["action"] for entry in audit_res.json()]
    assert "created" in actions
    assert "claimed" in actions
    assert "submitted" in actions
    assert "resumed" in actions


# ---------------------------------------------------------------------------
# SECURITY GUARDRAILS TESTS (Intentionally Failing Upload Limits)
# ---------------------------------------------------------------------------

async def test_upload_limit_exceed_file_count(
    client: AsyncClient,
    shadow_store: ShadowStore,
    test_contractor: ShadowContractor,
    auth_headers: dict[str, str],
) -> None:
    """Test that submitting more than 5 files fails with HTTP 400."""
    task = ShadowTask(opc_task_id="opc_max_files_test", title="Max Files Test")
    await shadow_store.create_task(task)
    await shadow_store.claim_task(task.id, test_contractor.id)

    # Create 6 files (limit is 5)
    files = [("files", (f"file_{i}.txt", f"content {i}".encode(), "text/plain")) for i in range(6)]

    res = await client.post(
        f"/api/tasks/{task.id}/submit",
        headers=auth_headers,
        data={"deliverable_text": "Too many files submission"},
        files=files,
    )
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert "Maximum allowed per submission is 5" in detail or "Too many files" in detail


async def test_upload_limit_exceed_file_size(
    client: AsyncClient,
    shadow_store: ShadowStore,
    test_contractor: ShadowContractor,
    auth_headers: dict[str, str],
) -> None:
    """Test that submitting an individual file > 10MB fails with HTTP 400."""
    task = ShadowTask(opc_task_id="opc_max_size_test", title="Max File Size Test")
    await shadow_store.create_task(task)
    await shadow_store.claim_task(task.id, test_contractor.id)

    # 10.5 MB oversized file payload
    oversized_bytes = b"0" * (10 * 1024 * 1024 + 512 * 1024)
    files = [("files", ("huge_file.pdf", oversized_bytes, "application/pdf"))]

    res = await client.post(
        f"/api/tasks/{task.id}/submit",
        headers=auth_headers,
        data={"deliverable_text": "Oversized file submission"},
        files=files,
    )
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert "exceeds individual size limit" in detail or "10MB" in detail


async def test_upload_disallowed_extension(
    client: AsyncClient,
    shadow_store: ShadowStore,
    test_contractor: ShadowContractor,
    auth_headers: dict[str, str],
) -> None:
    """Test that submitting a file with a disallowed extension (.exe) fails with HTTP 400."""
    task = ShadowTask(opc_task_id="opc_ext_test", title="Disallowed Ext Test")
    await shadow_store.create_task(task)
    await shadow_store.claim_task(task.id, test_contractor.id)

    files = [("files", ("malicious.exe", b"MZexecutable", "application/octet-stream"))]

    res = await client.post(
        f"/api/tasks/{task.id}/submit",
        headers=auth_headers,
        data={"deliverable_text": "Malicious file submission"},
        files=files,
    )
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert "not allowed" in detail or ".exe" in detail
