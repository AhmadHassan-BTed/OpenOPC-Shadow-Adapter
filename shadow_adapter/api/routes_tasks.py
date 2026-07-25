"""FastAPI router for Shadow Task management endpoints.

Enforces strict N-Tier separation:
- Router handlers deal ONLY with HTTP parsing, dependency resolution, and response formatting.
- Domain logic & DB operations are delegated to ShadowStore repository.
- File streaming is delegated to SecureUploadHandler.
- Domain exceptions (TaskNotFoundError, TaskPermissionError) are translated to HTTP responses.
"""

from __future__ import annotations

import io
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from loguru import logger

from shadow_adapter.adapter import ShadowModeAdapter
from shadow_adapter.api.dependencies import (
    get_config,
    get_current_contractor,
    get_store,
    get_upload_handler,
)
from shadow_adapter.config import ShadowConfig
from shadow_adapter.exceptions import (
    ShadowDomainError,
    TaskAlreadyClaimedError,
    TaskNotClaimedError,
    TaskNotFoundError,
    TaskPermissionError,
)
from shadow_adapter.models import (
    ShadowAuditEntry,
    ShadowContractor,
    ShadowSubmission,
    ShadowTask,
    ShadowTaskStatus,
    TaskSubmitResponse,
)
from shadow_adapter.shadow_store import ShadowStore
from shadow_adapter.upload import SecureUploadHandler, UploadValidationError

router = APIRouter()


# ── Production Line Private Helpers ──────────────────────────────────────────


async def _process_upload_files(
    files: list[UploadFile],
    upload_handler: SecureUploadHandler,
    task_id: str,
    config: ShadowConfig,
) -> list[str]:
    """Production Line Helper: Validate and write upload streams to disk."""
    upload_handler.validate_file_count(len(files))

    saved_file_paths: list[str] = []
    total_bytes = 0

    for upload in files:
        if not upload.filename:
            continue

        content = await upload.read()
        file_len = len(content)

        if file_len > config.max_file_size_bytes:
            raise UploadValidationError(
                f"File '{upload.filename}' exceeds individual size limit of {config.max_file_size_mb}MB."
            )

        total_bytes += file_len
        if total_bytes > config.max_upload_size_bytes:
            raise UploadValidationError(
                f"Total submission payload size exceeds max limit of {config.max_total_upload_size_mb}MB."
            )

        stream = io.BytesIO(content)
        saved_path, _ = upload_handler.save_upload_stream(
            shadow_task_id=task_id,
            filename=upload.filename,
            stream=stream,
            file_size_hint=file_len,
        )
        saved_file_paths.append(saved_path)

    return saved_file_paths


# ── Route Handlers (HTTP Controllers) ────────────────────────────────────────


@router.get("", response_model=list[ShadowTask])
async def list_tasks(
    store: Annotated[ShadowStore, Depends(get_store)],
    current_contractor: Annotated[ShadowContractor, Depends(get_current_contractor)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    assigned_to_me: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ShadowTask]:
    """List parked shadow tasks with optional filtering."""
    contractor_id = current_contractor.id if assigned_to_me else None
    return await store.list_tasks(
        status=status_filter,
        contractor_id=contractor_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{task_id}", response_model=ShadowTask)
async def get_task(
    task_id: str,
    store: Annotated[ShadowStore, Depends(get_store)],
    current_contractor: Annotated[ShadowContractor, Depends(get_current_contractor)],
) -> ShadowTask:
    """Get details of a specific parked shadow task."""
    task = await store.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shadow task '{task_id}' not found",
        )
    return task


@router.post("/{task_id}/claim", response_model=ShadowTask)
async def claim_task(
    task_id: str,
    store: Annotated[ShadowStore, Depends(get_store)],
    current_contractor: Annotated[ShadowContractor, Depends(get_current_contractor)],
) -> ShadowTask:
    """Claim a pending task for the authenticated contractor."""
    try:
        return await store.claim_task(task_id, current_contractor.id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (TaskAlreadyClaimedError, ShadowDomainError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{task_id}/unclaim", response_model=ShadowTask)
async def unclaim_task(
    task_id: str,
    store: Annotated[ShadowStore, Depends(get_store)],
    current_contractor: Annotated[ShadowContractor, Depends(get_current_contractor)],
) -> ShadowTask:
    """Release a claimed task back to the pending queue."""
    try:
        return await store.unclaim_task(task_id, current_contractor.id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TaskPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (TaskNotClaimedError, ShadowDomainError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{task_id}/submit", response_model=TaskSubmitResponse)
async def submit_task(
    task_id: str,
    store: Annotated[ShadowStore, Depends(get_store)],
    upload_handler: Annotated[SecureUploadHandler, Depends(get_upload_handler)],
    current_contractor: Annotated[ShadowContractor, Depends(get_current_contractor)],
    config: Annotated[ShadowConfig, Depends(get_config)],
    deliverable_text: str = Form(""),
    files: list[UploadFile] = File(default=[]),
) -> TaskSubmitResponse:
    """Submit work for a claimed task.

    Production Line Controller Flow:
    1. Fetch task and check status/permission eligibility.
    2. Process upload streams via _process_upload_files.
    3. Update repository state via store.submit_task.
    4. Trigger OpenOPC Resume Pipeline via ShadowModeAdapter.resume_task.
    """
    task = await store.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shadow task '{task_id}' not found",
        )

    if task.status != ShadowTaskStatus.CLAIMED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit task '{task_id}': status is '{task.status.value}', expected 'claimed'",
        )

    if task.assigned_contractor_id != current_contractor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Task '{task_id}' is claimed by another contractor",
        )

    try:
        saved_file_paths = await _process_upload_files(
            files=files,
            upload_handler=upload_handler,
            task_id=task_id,
            config=config,
        )
    except UploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    submission = ShadowSubmission(
        deliverable_text=deliverable_text,
        deliverable_files=saved_file_paths,
    )

    submitted_task = await store.submit_task(
        task_id=task_id,
        contractor_id=current_contractor.id,
        submission=submission,
    )

    resume_result = await ShadowModeAdapter.resume_task(
        shadow_task=submitted_task,
        opc_store_path=config.opc_store_path,
    )

    if resume_result.success:
        await store.mark_resumed(task_id)
        msg = f"Deliverable submitted and OpenOPC task '{task.opc_task_id}' resumed successfully."
        logger.info(f"[TaskAPI] {msg}")
        return TaskSubmitResponse(
            shadow_task_id=task_id,
            status=ShadowTaskStatus.RESUMED.value,
            opc_resume_status="success",
            message=msg,
        )
    else:
        await store.mark_failed(task_id, reason=resume_result.error or "Resume pipeline failed")
        msg = f"Work saved locally, but OpenOPC resume callback failed: {resume_result.error}"
        logger.warning(f"[TaskAPI] {msg}")
        return TaskSubmitResponse(
            shadow_task_id=task_id,
            status=ShadowTaskStatus.FAILED.value,
            opc_resume_status="failed",
            message=msg,
        )


@router.get("/{task_id}/audit", response_model=list[ShadowAuditEntry])
async def get_task_audit_log(
    task_id: str,
    store: Annotated[ShadowStore, Depends(get_store)],
    current_contractor: Annotated[ShadowContractor, Depends(get_current_contractor)],
) -> list[ShadowAuditEntry]:
    """Get the immutable audit trail for a task."""
    task = await store.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shadow task '{task_id}' not found",
        )
    return await store.get_audit_log(task_id)


# ── Health Check Helper Function ─────────────────────────────────────────────


async def health_check(store: ShadowStore, config: ShadowConfig) -> dict:
    """Helper for health check status aggregation."""
    try:
        pending_count = await store.count_tasks(status=ShadowTaskStatus.PENDING.value)
        db_status = "connected"
    except Exception as exc:
        logger.error(f"Health check DB error: {exc}")
        db_status = f"error: {exc}"
        pending_count = 0

    return {
        "status": "ok",
        "db": db_status,
        "pending_tasks": pending_count,
        "version": "0.1.0",
    }
