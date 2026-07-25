"""Test suite for Consolidated Corporate Brain & Hierarchical Context Routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from shadow_adapter.adapter import ShadowModeAdapter
from shadow_adapter.api.app import create_app
from shadow_adapter.config import ShadowConfig
from shadow_adapter.models import CorporateArtifact, UploadFileDTO, UploadLimits
from shadow_adapter.repositories.artifact_repo import CorporateArtifactsRepository
from shadow_adapter.repositories.opc_resume_repo import OpcResumeRepository
from shadow_adapter.security import SecurityManager
from shadow_adapter.services.handoff_service import HandoffService
from shadow_adapter.shadow_store import ShadowStore
from shadow_adapter.upload import SecureUploadHandler

pytestmark = pytest.mark.asyncio


async def test_corporate_artifacts_indexing(shadow_config: ShadowConfig) -> None:
    """Test indexing corporate artifacts in CorporateArtifactsRepository."""
    repo = CorporateArtifactsRepository(shadow_config.db_path)
    await repo.initialize()

    art = CorporateArtifact(
        id="art_test_100",
        shadow_task_id="stask_100",
        opc_task_id="opc_task_100",
        creator_role="senior_developer",
        original_filename="architecture.patch",
        storage_path="/tmp/uploads/architecture.patch",
        file_size_bytes=1024,
        mime_type="text/x-diff",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        tags=["senior_developer", "code_review"],
    )

    created = await repo.create_artifact(art)
    assert created.id == "art_test_100"
    assert created.creator_role == "senior_developer"
    assert created.download_url == "/api/v1/artifacts/art_test_100/download"

    fetched = await repo.get_artifact("art_test_100")
    assert fetched is not None
    assert fetched.original_filename == "architecture.patch"

    task_artifacts = await repo.list_artifacts_for_task("stask_100")
    assert len(task_artifacts) == 1
    assert task_artifacts[0].id == "art_test_100"


async def test_upstream_context_inheritance(
    shadow_config: ShadowConfig,
    shadow_store: ShadowStore,
    security: SecurityManager,
    tmp_path: Path,
) -> None:
    """Prove downstream Manager role inherits upstream Coder role deliverables and corporate artifacts."""
    limits = UploadLimits(
        max_file_count=shadow_config.max_files_per_submission,
        max_file_size_bytes=shadow_config.max_file_size_bytes,
        max_total_size_bytes=shadow_config.max_total_upload_size_mb * 1024 * 1024,
        allowed_extensions=shadow_config.allowed_extensions_set,
    )
    handler = SecureUploadHandler(shadow_config)
    art_repo = CorporateArtifactsRepository(shadow_config.db_path)
    await art_repo.initialize()

    opc_resume = OpcResumeRepository()
    handoff = HandoffService(shadow_store, opc_resume, handler, limits, art_repo)
    adapter = ShadowModeAdapter(shadow_config=shadow_config, shadow_store=shadow_store)

    # 1. Parent Coder Task
    @dataclass
    class ParentTask:
        id: str = "opc_coder_task_01"
        title: str = "Implement Payment Gateway"
        description: str = "Write payment API integration code."
        assigned_to: str = "senior_developer"
        status: str = "pending"
        priority: int = 1
        project_id: str = "default"
        session_id: str = "sess_e2e_100"
        metadata: dict = field(default_factory=lambda: {"work_item_id": "wi_coder_100"})
        linked_work_item_id: str = "wi_coder_100"

    await adapter.execute(ParentTask(), workspace_path="/tmp")
    parent_shadow = await shadow_store.get_task_by_opc_id("opc_coder_task_01")
    assert parent_shadow is not None

    # Contractor claims & submits Coder task with file artifact
    await handoff.claim_task(parent_shadow.id, "contractor_coder")
    file1 = UploadFileDTO(filename="diff.txt", content=b"diff --git a/b", size=14)

    await handoff.submit_and_resume(
        task_id=parent_shadow.id,
        contractor_id="contractor_coder",
        deliverable_text="Completed payment gateway implementation.",
        files=[file1],
        opc_store_path="/nonexistent/store.db",
    )

    # 2. Child Manager Task (same session / linked DAG parent)
    @dataclass
    class ChildTask:
        id: str = "opc_manager_task_02"
        title: str = "Review Payment Gateway Delivery"
        description: str = "Approve senior developer deliverable."
        assigned_to: str = "engineering_manager"
        status: str = "pending"
        priority: int = 1
        project_id: str = "default"
        session_id: str = "sess_e2e_100"
        metadata: dict = field(
            default_factory=lambda: {"parent_task_ids": ["opc_coder_task_01"], "work_item_id": "wi_coder_100"}
        )
        linked_work_item_id: str = "wi_coder_100"

    await adapter.execute(ChildTask(), workspace_path="/tmp")
    child_shadow = await shadow_store.get_task_by_opc_id("opc_manager_task_02")
    assert child_shadow is not None

    # 3. Retrieve Upstream Context for Child Manager Task
    context = await handoff.get_task_upstream_context(child_shadow.id)
    assert context.target_task_id == child_shadow.id
    assert len(context.ancestor_tasks) >= 1

    ancestor = context.ancestor_tasks[0]
    assert ancestor.opc_task_id == "opc_coder_task_01"
    assert ancestor.role == "senior_developer"
    assert ancestor.deliverable_text == "Completed payment gateway implementation."
    assert len(ancestor.artifacts) == 1
    assert ancestor.artifacts[0].original_filename == "diff.txt"


async def test_artifact_download_endpoint(
    shadow_config: ShadowConfig,
    shadow_store: ShadowStore,
    security: SecurityManager,
) -> None:
    """Test REST API artifact metadata retrieval and download stream endpoint."""
    app = create_app(shadow_config)
    art_repo = CorporateArtifactsRepository(shadow_config.db_path)
    await art_repo.initialize()

    app.state.config = shadow_config
    app.state.shadow_store = shadow_store
    app.state.security = security

    # Register admin user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={"username": "art_user", "password": "password123"},
        )
        assert reg_res.status_code == 201

        login_res = await client.post(
            "/api/v1/auth/login",
            json={"username": "art_user", "password": "password123"},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Seed physical file and corporate artifact record
        test_file = Path(shadow_config.upload_dir) / "art_demo.pdf"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_bytes(b"%PDF-1.4 Corporate Knowledge Brain PDF Content")

        art = CorporateArtifact(
            id="art_demo_999",
            shadow_task_id="stask_demo",
            opc_task_id="opc_demo",
            creator_role="legal_counsel",
            original_filename="legal_review.pdf",
            storage_path=str(test_file),
            file_size_bytes=len(b"%PDF-1.4 Corporate Knowledge Brain PDF Content"),
            mime_type="application/pdf",
            sha256_hash="dummyhash",
        )
        await art_repo.create_artifact(art)

        # GET detail
        detail_res = await client.get("/api/v1/artifacts/art_demo_999", headers=headers)
        assert detail_res.status_code == 200
        assert detail_res.json()["original_filename"] == "legal_review.pdf"

        # GET download
        dl_res = await client.get("/api/v1/artifacts/art_demo_999/download", headers=headers)
        assert dl_res.status_code == 200
        assert b"%PDF-1.4 Corporate Knowledge Brain" in dl_res.content
