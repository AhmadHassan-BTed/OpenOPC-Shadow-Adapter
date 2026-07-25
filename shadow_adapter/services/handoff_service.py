"""The Temporal Bridge Service (Handoff Engine).

Orchestrates the interchange between Silicon employees (AI agents) and Carbon employees (human contractors).

Contains ALL business logic and domain validation for task lifecycle transitions:
- Parking intercepted tasks (Silicon -> Desk)
- Claiming and unclaiming tasks (Carbon -> Desk)
- Submitting deliverables and resuming the OpenOPC DAG (Carbon -> Desk -> Silicon)

Tier Boundaries (Mandate 2):
- ZERO SQL (delegates data access to ShadowStore and OpcResumeRepository)
- ZERO HTTP Framework dependencies (raises pure DomainExceptions)
"""

from __future__ import annotations

import hashlib
import io
from typing import Any

from loguru import logger

from shadow_adapter.exceptions import (
    TaskNotClaimedError,
    TaskNotFoundError,
    TaskPermissionError,
)
from shadow_adapter.models import (
    CorporateArtifact,
    ShadowAuditEntry,
    ShadowSubmission,
    ShadowTask,
    ShadowTaskStatus,
    TaskSubmitResponse,
    UploadFileDTO,
    UploadLimits,
    UpstreamContextPayload,
    UpstreamContextTask,
)
from shadow_adapter.repositories.artifact_repo import CorporateArtifactsRepository
from shadow_adapter.repositories.opc_resume_repo import OpcResumeRepository
from shadow_adapter.services.org_service import OrgHierarchyService
from shadow_adapter.shadow_store import ShadowStore
from shadow_adapter.upload import SecureUploadHandler, UploadValidationError


class HandoffService:
    """The Handoff Engine / Temporal Bridge service."""

    def __init__(
        self,
        shadow_store: ShadowStore,
        opc_resume_repo: OpcResumeRepository,
        upload_handler: SecureUploadHandler,
        upload_limits: UploadLimits,
        artifact_repo: CorporateArtifactsRepository | None = None,
        org_service: OrgHierarchyService | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self._store = shadow_store
        self._opc_resume = opc_resume_repo
        self._upload = upload_handler
        self._limits = upload_limits
        self._artifact_repo = artifact_repo or CorporateArtifactsRepository(shadow_store.db_path)
        self._org_service = org_service or OrgHierarchyService()

    # ---------------------------------------------------------------------------
    # Silicon -> Desk (AI Parks Task)
    # ---------------------------------------------------------------------------

    async def park_task(self, shadow_task: ShadowTask) -> ShadowTask:
        """AI employee places work on the desk for a human."""
        return await self._store.create_task(shadow_task)

    # ---------------------------------------------------------------------------
    # Carbon -> Desk (Human Claims / Unclaims Task)
    # ---------------------------------------------------------------------------

    async def claim_task(self, task_id: str, contractor_id: str) -> ShadowTask:
        """Human employee claims work from the desk."""
        task = await self._fetch_or_raise(task_id)
        if task.status != ShadowTaskStatus.PENDING:
            raise ValueError(f"Cannot claim task {task_id}: status is '{task.status.value}', expected 'pending'")
        return await self._store.claim_task(task_id, contractor_id)

    async def unclaim_task(self, task_id: str, contractor_id: str) -> ShadowTask:
        """Human employee releases work back to the desk."""
        task = await self._fetch_or_raise(task_id)
        if task.status != ShadowTaskStatus.CLAIMED:
            raise TaskNotClaimedError(task_id, task.status.value)
        self._assert_ownership(task, contractor_id)
        return await self._store.unclaim_task(task_id, contractor_id)

    # ---------------------------------------------------------------------------
    # Carbon -> Desk -> Silicon (Human Submits Deliverable & Resumes DAG)
    # ---------------------------------------------------------------------------

    async def submit_and_resume(
        self,
        task_id: str,
        contractor_id: str,
        deliverable_text: str,
        files: list[UploadFileDTO],
        opc_store_path: str,
    ) -> TaskSubmitResponse:
        """Human completes work and submits deliverable. The AI company resumes instantly."""
        task = await self._fetch_or_raise(task_id)
        if task.status != ShadowTaskStatus.CLAIMED:
            raise TaskNotClaimedError(task_id, task.status.value)
        self._assert_ownership(task, contractor_id)

        # Process upload files and index CorporateArtifacts
        saved_file_paths = await self._process_uploads(files, task)

        submission = ShadowSubmission(
            deliverable_text=deliverable_text,
            deliverable_files=saved_file_paths,
        )

        submitted_task = await self._store.submit_task(
            task_id=task_id,
            contractor_id=contractor_id,
            submission=submission,
        )

        return await self._execute_resume_pipeline(submitted_task, opc_store_path)

    # ---------------------------------------------------------------------------
    # Task Queries
    # ---------------------------------------------------------------------------

    async def get_task(self, task_id: str) -> ShadowTask:
        """Retrieve details of a shadow task."""
        return await self._fetch_or_raise(task_id)

    async def list_tasks(
        self,
        status: str | None = None,
        contractor_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ShadowTask]:
        """List shadow tasks matching criteria."""
        return await self._store.list_tasks(
            status=status,
            contractor_id=contractor_id,
            limit=limit,
            offset=offset,
        )

    async def get_audit_log(self, task_id: str) -> list[ShadowAuditEntry]:
        """Retrieve immutable audit log for a shadow task."""
        await self._fetch_or_raise(task_id)
        return await self._store.get_audit_log(task_id)

    async def get_task_upstream_context(self, task_id: str) -> UpstreamContextPayload:
        """Assembles ancestor DAG deliverable texts and corporate artifacts for a downstream task."""
        target_task = await self._fetch_or_raise(task_id)
        all_tasks = await self._store.list_tasks(limit=1000)

        ancestors = self._org_service.resolve_ancestor_task_ids(target_task, all_tasks)
        ancestor_ids = [t.id for t in ancestors]

        artifacts: list[CorporateArtifact] = []
        if self._artifact_repo and ancestor_ids:
            try:
                artifacts = await self._artifact_repo.list_artifacts_for_tasks(ancestor_ids)
            except Exception as e:
                logger.warning(f"[HandoffService] Error listing corporate artifacts: {e}")

        artifacts_by_task: dict[str, list[CorporateArtifact]] = {}
        for art in artifacts:
            artifacts_by_task.setdefault(art.shadow_task_id, []).append(art)

        ancestor_payloads: list[UpstreamContextTask] = []
        for anc in ancestors:
            ancestor_payloads.append(
                UpstreamContextTask(
                    shadow_task_id=anc.id,
                    opc_task_id=anc.opc_task_id,
                    role=anc.assigned_role,
                    title=anc.title,
                    deliverable_text=anc.deliverable_text,
                    artifacts=artifacts_by_task.get(anc.id, []),
                )
            )

        return UpstreamContextPayload(
            target_task_id=target_task.id,
            ancestor_tasks=ancestor_payloads,
        )

    # ---------------------------------------------------------------------------
    # Private Helpers (Production Line Pipeline Workstations)
    # ---------------------------------------------------------------------------

    async def _fetch_or_raise(self, task_id: str) -> ShadowTask:
        """Workstation 1: Fetch task or raise TaskNotFoundError."""
        task = await self._store.get_task(task_id)
        if not task:
            raise TaskNotFoundError(task_id)
        return task

    @staticmethod
    def _assert_ownership(task: ShadowTask, contractor_id: str) -> None:
        """Workstation 2: Guard contractor ownership permission."""
        if task.assigned_contractor_id != contractor_id:
            raise TaskPermissionError(task.id, task.assigned_contractor_id or "")

    async def _process_uploads(self, files: list[UploadFileDTO], task: ShadowTask) -> list[str]:
        """Workstation 3: Validate upload constraints, save streams to disk, and index in Central Brain."""
        self._upload.validate_file_count(len(files))

        saved_file_paths: list[str] = []
        total_bytes = 0

        for upload in files:
            if not upload.filename:
                continue

            file_len = upload.size
            if file_len > self._limits.max_file_size_bytes:
                raise UploadValidationError(f"File '{upload.filename}' exceeds individual size limit.")

            total_bytes += file_len
            if total_bytes > self._limits.max_total_size_bytes:
                raise UploadValidationError("Total submission payload size exceeds max limit.")

            stream = io.BytesIO(upload.content)
            saved_path, _ = self._upload.save_upload_stream(
                shadow_task_id=task.id,
                filename=upload.filename,
                stream=stream,
                file_size_hint=file_len,
            )
            saved_file_paths.append(saved_path)

            # Index artifact in Central Knowledge Graph
            if self._artifact_repo:
                try:
                    import uuid

                    file_hash = hashlib.sha256(upload.content).hexdigest()
                    art = CorporateArtifact(
                        id=f"art_{uuid.uuid4().hex[:12]}",
                        shadow_task_id=task.id,
                        opc_task_id=task.opc_task_id,
                        opc_work_item_id=task.opc_work_item_id,
                        creator_role=task.assigned_role,
                        creator_contractor_id=task.assigned_contractor_id,
                        original_filename=upload.filename,
                        storage_path=saved_path,
                        file_size_bytes=file_len,
                        mime_type="application/octet-stream",
                        sha256_hash=file_hash,
                        tags=[task.assigned_role],
                    )
                    await self._artifact_repo.create_artifact(art)
                except Exception as e:
                    logger.warning(f"[HandoffService] Failed indexing corporate artifact for '{upload.filename}': {e}")

        return saved_file_paths

    async def _execute_resume_pipeline(self, shadow_task: ShadowTask, opc_store_path: str) -> TaskSubmitResponse:
        """Workstation 4: Resume OpenOPC DAG and update shadow state."""
        resume_result = await self._opc_resume.resume(
            shadow_task=shadow_task,
            opc_store_path=opc_store_path,
        )

        if resume_result.success:
            await self._store.mark_resumed(shadow_task.id)
            msg = f"Deliverable submitted and OpenOPC task '{shadow_task.opc_task_id}' resumed successfully."
            logger.info(f"[HandoffService] {msg}")
            return TaskSubmitResponse(
                shadow_task_id=shadow_task.id,
                status=ShadowTaskStatus.RESUMED.value,
                opc_resume_status="success",
                message=msg,
            )
        else:
            await self._store.mark_failed(
                shadow_task.id,
                reason=resume_result.error or "Resume pipeline failed",
            )
            msg = f"Work saved locally, but OpenOPC resume callback failed: {resume_result.error}"
            logger.warning(f"[HandoffService] {msg}")
            return TaskSubmitResponse(
                shadow_task_id=shadow_task.id,
                status=ShadowTaskStatus.FAILED.value,
                opc_resume_status="failed",
                message=msg,
            )
