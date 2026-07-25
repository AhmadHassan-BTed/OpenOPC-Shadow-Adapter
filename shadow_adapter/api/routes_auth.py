"""Authentication API endpoints for human contractors.

Endpoints:
- POST /api/auth/login     -> Issues JWT token for contractor
- POST /api/auth/register  -> Registers new contractor (First user becomes admin automatically)
- GET  /api/auth/me        -> Returns active contractor profile
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from shadow_adapter.api.dependencies import (
    get_current_contractor,
    get_security,
    get_store,
)
from shadow_adapter.models import (
    ContractorPublic,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    ShadowContractor,
)
from shadow_adapter.security import SecurityManager
from shadow_adapter.shadow_store import ShadowStore

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    store: Annotated[ShadowStore, Depends(get_store)],
    security: Annotated[SecurityManager, Depends(get_security)],
) -> LoginResponse:
    """Authenticate a human contractor and issue a JWT bearer token."""
    contractor = await store.get_contractor_by_username(credentials.username)
    if not contractor or not contractor.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not security.verify_password(credentials.password, contractor.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = security.create_access_token(
        contractor_id=contractor.id,
        username=contractor.username,
        roles=contractor.roles,
    )

    logger.info(f"Contractor logged in: {contractor.username} (id={contractor.id})")

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=security.token_expire_seconds,
        contractor=ContractorPublic(
            id=contractor.id,
            username=contractor.username,
            email=contractor.email,
            display_name=contractor.display_name,
            roles=contractor.roles,
            is_active=contractor.is_active,
        ),
    )


@router.post("/register", response_model=ContractorPublic, status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterRequest,
    store: Annotated[ShadowStore, Depends(get_store)],
    security: Annotated[SecurityManager, Depends(get_security)],
) -> ContractorPublic:
    """Register a new contractor. First user automatically becomes admin."""
    existing = await store.get_contractor_by_username(req.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{req.username}' is already taken",
        )

    # Bootstrap: if this is the first contractor, make them admin
    total_count = await store.contractor_count()
    roles = ["admin", "contractor"] if total_count == 0 else ["contractor"]

    password_hash = security.hash_password(req.password)
    contractor = ShadowContractor(
        username=req.username,
        email=req.email,
        password_hash=password_hash,
        display_name=req.display_name or req.username,
        roles=roles,
    )

    created = await store.create_contractor(contractor)
    logger.info(f"New contractor registered: {created.username} (roles={roles})")

    return ContractorPublic(
        id=created.id,
        username=created.username,
        email=created.email,
        display_name=created.display_name,
        roles=created.roles,
        is_active=created.is_active,
    )


@router.get("/me", response_model=ContractorPublic)
async def get_me(
    current_contractor: Annotated[ShadowContractor, Depends(get_current_contractor)],
) -> ContractorPublic:
    """Return profile info of the currently logged-in contractor."""
    return ContractorPublic(
        id=current_contractor.id,
        username=current_contractor.username,
        email=current_contractor.email,
        display_name=current_contractor.display_name,
        roles=current_contractor.roles,
        is_active=current_contractor.is_active,
    )
