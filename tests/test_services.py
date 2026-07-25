"""Unit tests for HandoffService and AuthService N-Tier services."""

from __future__ import annotations

import pytest

from shadow_adapter.exceptions import (
    ContractorAlreadyExistsError,
    InvalidCredentialsError,
    TaskPermissionError,
)
from shadow_adapter.models import (
    JwtConfig,
    LoginRequest,
    RegisterRequest,
    ShadowTask,
    ShadowTaskStatus,
    UploadFileDTO,
    UploadLimits,
)
from shadow_adapter.repositories.opc_resume_repo import OpcResumeRepository
from shadow_adapter.security import SecurityManager
from shadow_adapter.services.auth_service import AuthService
from shadow_adapter.services.handoff_service import HandoffService
from shadow_adapter.shadow_store import ShadowStore
from shadow_adapter.upload import SecureUploadHandler

pytestmark = pytest.mark.asyncio


@pytest.fixture
def jwt_config() -> JwtConfig:
    return JwtConfig(secret="service-test-secret", algorithm="HS256", expire_hours=1)


@pytest.fixture
def upload_limits() -> UploadLimits:
    return UploadLimits(
        max_file_count=3,
        max_file_size_bytes=1024 * 1024,
        max_total_size_bytes=5 * 1024 * 1024,
        allowed_extensions={".pdf", ".txt", ".png"},
    )


@pytest.fixture
def handoff_service(
    shadow_store: ShadowStore,
    tmp_path,
    upload_limits: UploadLimits,
) -> HandoffService:
    upload_handler = SecureUploadHandler(upload_limits, upload_dir=tmp_path / "uploads")
    opc_repo = OpcResumeRepository()
    return HandoffService(
        shadow_store=shadow_store,
        opc_resume_repo=opc_repo,
        upload_handler=upload_handler,
        upload_limits=upload_limits,
    )


@pytest.fixture
def auth_service(shadow_store: ShadowStore, jwt_config: JwtConfig) -> AuthService:
    sec = SecurityManager(jwt_config)
    return AuthService(store=shadow_store, security=sec)


async def test_handoff_service_lifecycle(handoff_service: HandoffService) -> None:
    """Test park -> claim -> submit_and_resume cycle via HandoffService."""
    task = ShadowTask(opc_task_id="opc_service_1", title="Handoff Test")
    parked = await handoff_service.park_task(task)
    assert parked.id == task.id
    assert parked.status == ShadowTaskStatus.PENDING

    # Claim
    claimed = await handoff_service.claim_task(task.id, "contractor_1")
    assert claimed.status == ShadowTaskStatus.CLAIMED
    assert claimed.assigned_contractor_id == "contractor_1"

    # Cannot claim already claimed task
    with pytest.raises(ValueError, match="expected 'pending'"):
        await handoff_service.claim_task(task.id, "contractor_2")

    # Cannot unclaim by non-owner
    with pytest.raises(TaskPermissionError):
        await handoff_service.unclaim_task(task.id, "contractor_2")

    # Unclaim by owner
    unclaimed = await handoff_service.unclaim_task(task.id, "contractor_1")
    assert unclaimed.status == ShadowTaskStatus.PENDING

    # Re-claim and submit
    await handoff_service.claim_task(task.id, "contractor_1")
    file_dto = UploadFileDTO(filename="report.txt", content=b"Deliverable data", size=16)

    # Missing opc_store_path will save work locally but mark resume failed cleanly
    res = await handoff_service.submit_and_resume(
        task_id=task.id,
        contractor_id="contractor_1",
        deliverable_text="All work completed",
        files=[file_dto],
        opc_store_path="/nonexistent/store.db",
    )
    assert res.status == ShadowTaskStatus.FAILED.value
    assert res.opc_resume_status == "failed"


async def test_auth_service_flow(auth_service: AuthService) -> None:
    """Test register -> login -> get_me flow via AuthService."""
    reg_req = RegisterRequest(
        username="alice",
        password="secretpassword123",
        email="alice@example.com",
        display_name="Alice Architect",
    )
    contractor = await auth_service.register(reg_req)
    assert contractor.username == "alice"
    assert "admin" in contractor.roles  # First user gets admin

    # Duplicate register fails
    with pytest.raises(ContractorAlreadyExistsError):
        await auth_service.register(reg_req)

    # Login success
    login_res = await auth_service.login(LoginRequest(username="alice", password="secretpassword123"))
    assert login_res.access_token is not None
    assert login_res.contractor.username == "alice"

    # Login invalid password fails
    with pytest.raises(InvalidCredentialsError):
        await auth_service.login(LoginRequest(username="alice", password="wrongpassword"))
