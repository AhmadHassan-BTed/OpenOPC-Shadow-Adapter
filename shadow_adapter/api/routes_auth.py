"""Authentication API endpoints for human contractors.

Enforces strict N-Tier separation (Mandate 2):
- Route handlers do ONLY HTTP parsing, dependency resolution, and response formatting.
- Domain logic & contractor account orchestration are delegated to AuthService.
- Domain exceptions are mapped to standard HTTP response codes.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from shadow_adapter.api.dependencies import (
    get_auth_service,
    get_current_contractor,
)
from shadow_adapter.exceptions import (
    ContractorAlreadyExistsError,
    InvalidCredentialsError,
)
from shadow_adapter.models import (
    ContractorPublic,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    ShadowContractor,
)
from shadow_adapter.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    """Authenticate a human contractor and issue a JWT bearer token."""
    try:
        return await auth_service.login(credentials)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@router.post("/register", response_model=ContractorPublic, status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ContractorPublic:
    """Register a new contractor. First user automatically becomes admin."""
    try:
        return await auth_service.register(req)
    except ContractorAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get("/me", response_model=ContractorPublic)
async def get_me(
    current_contractor: Annotated[ShadowContractor, Depends(get_current_contractor)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ContractorPublic:
    """Return profile info of the currently logged-in contractor."""
    return await auth_service.get_me(current_contractor)
