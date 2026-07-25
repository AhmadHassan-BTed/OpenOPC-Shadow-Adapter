"""FastAPI Dependency Injection layer for Shadow Adapter API.

Provides clean DI for:
- Database store instance (ShadowStore)
- Security manager (JWT verification & password hashing)
- Secure upload handler
- Configuration settings (ShadowConfig)
- Authenticated current contractor (via OAuth2 password bearer token)
- Admin role authorization check
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from shadow_adapter.config import ShadowConfig
from shadow_adapter.models import ShadowContractor
from shadow_adapter.security import SecurityManager
from shadow_adapter.shadow_store import ShadowStore
from shadow_adapter.upload import SecureUploadHandler

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_config(request: Request) -> ShadowConfig:
    """Inject ShadowConfig from FastAPI application state."""
    config: ShadowConfig | None = getattr(request.app.state, "config", None)
    if config is None:
        config = ShadowConfig()
    return config


async def get_store(request: Request) -> ShadowStore:
    """Inject ShadowStore instance from FastAPI application state."""
    store: ShadowStore | None = getattr(request.app.state, "shadow_store", None)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database store is not initialized in application state",
        )
    return store


async def get_security(request: Request) -> SecurityManager:
    """Inject SecurityManager instance from FastAPI application state."""
    security: SecurityManager | None = getattr(request.app.state, "security", None)
    if security is None:
        config = await get_config(request)
        security = SecurityManager(config)
    return security


async def get_upload_handler(request: Request) -> SecureUploadHandler:
    """Inject SecureUploadHandler instance from FastAPI application state."""
    handler: SecureUploadHandler | None = getattr(request.app.state, "upload_handler", None)
    if handler is None:
        config = await get_config(request)
        handler = SecureUploadHandler(config)
    return handler


async def get_current_contractor(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    store: Annotated[ShadowStore, Depends(get_store)],
    security: Annotated[SecurityManager, Depends(get_security)],
) -> ShadowContractor:
    """Validate JWT token and inject current authenticated ShadowContractor.

    Raises HTTP 401 if missing, invalid, or expired.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = security.decode_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    contractor_id = payload["sub"]
    contractor = await store.get_contractor(contractor_id)
    if not contractor or not contractor.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contractor account not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return contractor


async def require_admin(
    contractor: Annotated[ShadowContractor, Depends(get_current_contractor)],
) -> ShadowContractor:
    """Ensure the current contractor has the 'admin' role."""
    if "admin" not in contractor.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for this endpoint",
        )
    return contractor
