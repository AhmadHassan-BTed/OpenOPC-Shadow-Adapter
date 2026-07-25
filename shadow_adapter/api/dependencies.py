"""FastAPI Dependency Injection layer for Shadow Adapter API.

Provides clean DI for:
- Database store instance (ShadowStore)
- OpcResumeRepository instance
- Security manager (JWT verification & password hashing)
- Secure upload handler
- Configuration settings (ShadowConfig, UploadLimits, JwtConfig)
- HandoffService (The Temporal Bridge)
- AuthService (Carbon Employee Identity)
- Authenticated current contractor (via OAuth2 password bearer token)
- Admin role authorization check
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from shadow_adapter.config import ShadowConfig
from shadow_adapter.models import JwtConfig, ShadowContractor, UploadLimits
from shadow_adapter.repositories.opc_resume_repo import OpcResumeRepository
from shadow_adapter.security import SecurityManager
from shadow_adapter.services.auth_service import AuthService
from shadow_adapter.services.handoff_service import HandoffService
from shadow_adapter.shadow_store import ShadowStore
from shadow_adapter.upload import SecureUploadHandler

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_config(request: Request) -> ShadowConfig:
    """Inject ShadowConfig from FastAPI application state."""
    config: ShadowConfig | None = getattr(request.app.state, "config", None)
    if config is None:
        config = ShadowConfig()
    return config


async def get_jwt_config(
    config: Annotated[ShadowConfig, Depends(get_config)],
) -> JwtConfig:
    """Construct JwtConfig DTO from ShadowConfig."""
    return JwtConfig(
        secret=config.jwt_secret,
        algorithm=config.jwt_algorithm,
        expire_hours=config.jwt_expire_hours,
    )


async def get_upload_limits(
    config: Annotated[ShadowConfig, Depends(get_config)],
) -> UploadLimits:
    """Construct UploadLimits DTO from ShadowConfig."""
    return UploadLimits(
        max_file_count=config.max_files_per_submission,
        max_file_size_bytes=config.max_file_size_bytes,
        max_total_size_bytes=config.max_upload_size_bytes,
        allowed_extensions=config.allowed_extensions_set,
    )


async def get_store(request: Request) -> ShadowStore:
    """Inject ShadowStore instance from FastAPI application state."""
    store: ShadowStore | None = getattr(request.app.state, "shadow_store", None)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database store is not initialized in application state",
        )
    return store


async def get_security(
    request: Request,
    jwt_config: Annotated[JwtConfig, Depends(get_jwt_config)],
) -> SecurityManager:
    """Inject SecurityManager instance constructed with JwtConfig DTO."""
    security: SecurityManager | None = getattr(request.app.state, "security", None)
    if security is None:
        security = SecurityManager(jwt_config)
    return security


async def get_upload_handler(
    request: Request,
    limits: Annotated[UploadLimits, Depends(get_upload_limits)],
) -> SecureUploadHandler:
    """Inject SecureUploadHandler instance constructed with UploadLimits DTO."""
    handler: SecureUploadHandler | None = getattr(request.app.state, "upload_handler", None)
    if handler is None:
        config = await get_config(request)
        handler = SecureUploadHandler(limits, config.upload_path)
    return handler


async def get_opc_resume_repo() -> OpcResumeRepository:
    """Inject OpcResumeRepository instance."""
    return OpcResumeRepository()


from shadow_adapter.repositories.artifact_repo import CorporateArtifactsRepository
from shadow_adapter.services.org_service import OrgHierarchyService


async def get_artifact_repo(
    store: Annotated[ShadowStore, Depends(get_store)],
) -> CorporateArtifactsRepository:
    """Inject CorporateArtifactsRepository initialized with ShadowStore db_path."""
    repo = CorporateArtifactsRepository(store.db_path)
    await repo.initialize()
    return repo


async def get_org_service() -> OrgHierarchyService:
    """Inject OrgHierarchyService."""
    return OrgHierarchyService()


async def get_handoff_service(
    store: Annotated[ShadowStore, Depends(get_store)],
    opc_resume: Annotated[OpcResumeRepository, Depends(get_opc_resume_repo)],
    upload_handler: Annotated[SecureUploadHandler, Depends(get_upload_handler)],
    upload_limits: Annotated[UploadLimits, Depends(get_upload_limits)],
    artifact_repo: Annotated[CorporateArtifactsRepository, Depends(get_artifact_repo)],
    org_service: Annotated[OrgHierarchyService, Depends(get_org_service)],
) -> HandoffService:
    """Inject HandoffService (The Temporal Bridge)."""
    return HandoffService(
        shadow_store=store,
        opc_resume_repo=opc_resume,
        upload_handler=upload_handler,
        upload_limits=upload_limits,
        artifact_repo=artifact_repo,
        org_service=org_service,
    )


async def get_auth_service(
    store: Annotated[ShadowStore, Depends(get_store)],
    security: Annotated[SecurityManager, Depends(get_security)],
) -> AuthService:
    """Inject AuthService."""
    return AuthService(store=store, security=security)


async def get_current_contractor(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    store: Annotated[ShadowStore, Depends(get_store)],
    security: Annotated[SecurityManager, Depends(get_security)],
) -> ShadowContractor:
    """Validate JWT token and inject current authenticated ShadowContractor."""
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
