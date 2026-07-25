"""REST API endpoints for Corporate Artifacts and Knowledge Graph Context Routing.

Provides endpoints for downloading corporate artifacts, inspecting artifact metadata,
and fetching upstream context graph payloads for downstream tasks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from loguru import logger

from shadow_adapter.api.dependencies import get_current_contractor, get_handoff_service
from shadow_adapter.models import (
    CorporateArtifact,
    ShadowContractor,
    UpstreamContextPayload,
)
from shadow_adapter.services.handoff_service import HandoffService

artifacts_router = APIRouter()


@artifacts_router.get("/{artifact_id}", response_model=CorporateArtifact, tags=["Artifacts"])
async def get_artifact_detail(
    artifact_id: str,
    handoff: Annotated[HandoffService, Depends(get_handoff_service)],
    current_user: Annotated[ShadowContractor, Depends(get_current_contractor)],
) -> CorporateArtifact:
    """Retrieve metadata for a specific Corporate Artifact."""
    if not handoff._artifact_repo:
        raise HTTPException(status_code=500, detail="Artifact repository not configured.")

    artifact = await handoff._artifact_repo.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail=f"Corporate artifact '{artifact_id}' not found.")
    return artifact


@artifacts_router.get("/{artifact_id}/download", tags=["Artifacts"])
async def download_artifact_file(
    artifact_id: str,
    handoff: Annotated[HandoffService, Depends(get_handoff_service)],
    current_user: Annotated[ShadowContractor, Depends(get_current_contractor)],
) -> FileResponse:
    """Download the binary stream for a Corporate Artifact."""
    if not handoff._artifact_repo:
        raise HTTPException(status_code=500, detail="Artifact repository not configured.")

    artifact = await handoff._artifact_repo.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail=f"Corporate artifact '{artifact_id}' not found.")

    file_path = Path(artifact.storage_path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Physical file for artifact '{artifact_id}' not found on storage.")

    return FileResponse(
        path=str(file_path),
        filename=artifact.original_filename,
        media_type=artifact.mime_type,
    )


@artifacts_router.get("/context/{task_id}", response_model=UpstreamContextPayload, tags=["Context Routing"])
async def get_task_upstream_context(
    task_id: str,
    handoff: Annotated[HandoffService, Depends(get_handoff_service)],
    current_user: Annotated[ShadowContractor, Depends(get_current_contractor)],
) -> UpstreamContextPayload:
    """Retrieve the complete upstream context payload (ancestor deliverables & artifacts) for a task."""
    try:
        return await handoff.get_task_upstream_context(task_id)
    except Exception as e:
        logger.error(f"Error fetching upstream context for task '{task_id}': {e}")
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' context not found.")
