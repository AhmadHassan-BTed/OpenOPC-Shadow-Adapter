"""FastAPI router for Shadow Task management endpoints.

Enforces strict N-Tier separation (Mandate 2):
- Route handlers do ONLY HTTP I/O, parameter parsing, and response formatting.
- Domain logic, lifecycle orchestration, and file streaming are delegated to HandoffService.
- Domain exceptions are mapped to standard HTTP response codes.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from loguru import logger

from shadow_adapter.api.dependencies import (
    get_config,
    get_current_contractor,
    get_handoff_service,
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
    ShadowTask,
    ShadowTaskStatus,
    TaskSubmitResponse,
    UploadFileDTO,
)
from shadow_adapter.services.handoff_service import HandoffService
from shadow_adapter.shadow_store import ShadowStore
from shadow_adapter.upload import UploadValidationError

router = APIRouter()


@router.get("", response_model=list[ShadowTask])
async def list_tasks(
    handoff: Annotated[HandoffService, Depends(get_handoff_service)],
    current_contractor: Annotated[ShadowContractor, Depends(get_current_contractor)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    assigned_to_me: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ShadowTask]:
    """List parked shadow tasks with optional filtering."""
    contractor_id = current_contractor.id if assigned_to_me else None
    return await handoff.list_tasks(
        status=status_filter,
        contractor_id=contractor_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{task_id}", response_model=ShadowTask)
async def get_task(
    task_id: str,
    handoff: Annotated[HandoffService, Depends(get_handoff_service)],
    current_contractor: Annotated[ShadowContractor, Depends(get_current_contractor)],
) -> ShadowTask:
    """Get details of a specific parked shadow task."""
    try:
        return await handoff.get_task(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shadow task '{task_id}' not found",
        ) from exc


@router.post("/{task_id}/claim", response_model=ShadowTask)
async def claim_task(
    task_id: str,
    handoff: Annotated[HandoffService, Depends(get_handoff_service)],
    current_contractor: Annotated[ShadowContractor, Depends(get_current_contractor)],
) -> ShadowTask:
    """Claim a pending task for the authenticated contractor."""
    try:
        return await handoff.claim_task(task_id, current_contractor.id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (TaskAlreadyClaimedError, ShadowDomainError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{task_id}/unclaim", response_model=ShadowTask)
async def unclaim_task(
    task_id: str,
    handoff: Annotated[HandoffService, Depends(get_handoff_service)],
    current_contractor: Annotated[ShadowContractor, Depends(get_current_contractor)],
) -> ShadowTask:
    """Release a claimed task back to the pending queue."""
    try:
        return await handoff.unclaim_task(task_id, current_contractor.id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TaskPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (TaskNotClaimedError, ShadowDomainError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{task_id}/submit", response_model=TaskSubmitResponse)
async def submit_task(
    task_id: str,
    handoff: Annotated[HandoffService, Depends(get_handoff_service)],
    current_contractor: Annotated[ShadowContractor, Depends(get_current_contractor)],
    config: Annotated[ShadowConfig, Depends(get_config)],
    deliverable_text: str = Form(""),
    files: list[UploadFile] = File(default=[]),
) -> TaskSubmitResponse:
    """Submit work for a claimed task.

    HTTP Controller: Convert UploadFile -> UploadFileDTO at boundary,
    delegate workflow execution to HandoffService.
    """
    file_dtos: list[UploadFileDTO] = []
    for f in files:
        if not f.filename:
            continue
        content = await f.read()
        file_dtos.append(
            UploadFileDTO(
                filename=f.filename,
                content=content,
                size=len(content),
            )
        )

    try:
        return await handoff.submit_and_resume(
            task_id=task_id,
            contractor_id=current_contractor.id,
            deliverable_text=deliverable_text,
            files=file_dtos,
            opc_store_path=config.opc_store_path,
        )
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TaskPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (TaskNotClaimedError, UploadValidationError, ShadowDomainError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{task_id}/audit", response_model=list[ShadowAuditEntry])
async def get_task_audit_log(
    task_id: str,
    handoff: Annotated[HandoffService, Depends(get_handoff_service)],
    current_contractor: Annotated[ShadowContractor, Depends(get_current_contractor)],
) -> list[ShadowAuditEntry]:
    """Get the immutable audit trail for a task."""
    try:
        return await handoff.get_audit_log(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shadow task '{task_id}' not found",
        ) from exc


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
