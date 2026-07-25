"""Task API endpoints for human contractors.

Endpoints:
- GET  /api/tasks               -> List parked tasks (filtering by status, assigned_to_me, pagination)
- GET  /api/tasks/{id}          -> Get single task detail with OPC context
- POST /api/tasks/{id}/claim    -> Claim a pending task
- POST /api/tasks/{id}/unclaim  -> Release a claimed task
- POST /api/tasks/{id}/submit   -> Submit deliverable (text + files). Enforces strict limits (max 5 files, 50MB total, 10MB per file) and triggers OpenOPC resume.
- GET  /api/tasks/{id}/audit    -> Get audit trail for a task
- GET  /api/health              -> System health check endpoint
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
from shadow_adapter.models import (
    HealthResponse,
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


@router.get("", response_model=list[ShadowTask])
async def list_tasks(
    store: Annotated[ShadowStore, Depends(get_store)],
    current_contractor: Annotated[ShadowContractor, Depends(get_current_contractor)],
    task_status: str | None = Query(None, alias="status", description="Filter by status"),
    assigned_to_me: bool = Query(False, description="Only show tasks claimed by current contractor"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[ShadowTask]:
    """List parked shadow tasks with optional status and contractor filtering."""
    contractor_id = current_contractor.id if assigned_to_me else None
    return await store.list_tasks(
        status=task_status,
        contractor_id=contractor_id,
        limit=limit,
        offset=offset,
    )


@router.get("/health", response_model=HealthResponse)
async def health_check(
    store: Annotated[ShadowStore, Depends(get_store)],
    config: Annotated[ShadowConfig, Depends(get_config)],
) -> HealthResponse:
    """Public health check endpoint returning system status and pending task count."""
    try:
        pending_count = await store.count_tasks(status=ShadowTaskStatus.PENDING.value)
        db_status = "connected"
    except Exception as exc:
        logger.error(f"Health check DB error: {exc}")
        db_status = f"error: {exc}"

    return HealthResponse(
        status="ok",
        db=db_status,
        pending_tasks=pending_count,
        version="0.1.0",
    )


@router.get("/{task_id}", response_model=ShadowTask)
async def get_task_detail(
    task_id: str,
    store: Annotated[ShadowStore, Depends(get_store)],
    _: Annotated[ShadowContractor, Depends(get_current_contractor)],
) -> ShadowTask:
    """Get detailed context for a single shadow task."""
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
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{task_id}/unclaim", response_model=ShadowTask)
async def unclaim_task(
    task_id: str,
    store: Annotated[ShadowStore, Depends(get_store)],
    current_contractor: Annotated[ShadowContractor, Depends(get_current_contractor)],
) -> ShadowTask:
    """Release a claimed task back to the pending queue."""
    try:
        return await store.unclaim_task(task_id, current_contractor.id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


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

    Enforces strict upload limits:
    - Maximum 5 files per submission
    - Maximum 50MB total submission payload size
    - Maximum 10MB per individual file

    Triggers OpenOPC resume pipeline to push deliverable into store.db and set phase APPROVED.
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

    # 1. Enforce file count limit (max 5)
    try:
        upload_handler.validate_file_count(len(files))
    except UploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    saved_file_paths: list[str] = []
    total_bytes = 0

    # 2. Process & save uploaded files with single/total size limits
    for upload in files:
        if not upload.filename:
            continue

        try:
            # Read file bytes to verify size and pass stream to handler
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

        except UploadValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except Exception as exc:
            logger.error(f"Error saving upload '{upload.filename}': {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process file '{upload.filename}': {exc}",
            ) from exc

    # 3. Update shadow store task with submission deliverables
    submission = ShadowSubmission(
        deliverable_text=deliverable_text,
        deliverable_files=saved_file_paths,
    )

    submitted_task = await store.submit_task(
        task_id=task_id,
        contractor_id=current_contractor.id,
        submission=submission,
    )

    # 4. Trigger OpenOPC Resume Pipeline
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
    _: Annotated[ShadowContractor, Depends(get_current_contractor)],
) -> list[ShadowAuditEntry]:
    """Get full audit trail timeline for a task."""
    return await store.get_audit_log(task_id)
