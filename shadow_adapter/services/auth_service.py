"""Authentication Service for Carbon Employee identity management.

Handles login, contractor registration (with admin bootstrapping), and profile retrieval.

Tier Boundaries (Mandate 2):
- ZERO SQL (delegates data access to ShadowStore)
- ZERO HTTP dependencies (raises pure DomainExceptions)
"""

from __future__ import annotations

from loguru import logger

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
from shadow_adapter.security import SecurityManager
from shadow_adapter.shadow_store import ShadowStore


class AuthService:
    """Authentication and identity service for human contractors."""

    def __init__(self, store: ShadowStore, security: SecurityManager) -> None:
        self._store = store
        self._security = security

    async def login(self, req: LoginRequest) -> LoginResponse:
        """Authenticate a contractor and return a JWT access token."""
        contractor = await self._store.get_contractor_by_username(req.username)
        if not contractor or not contractor.is_active:
            raise InvalidCredentialsError()

        if not self._security.verify_password(req.password, contractor.password_hash):
            raise InvalidCredentialsError()

        token = self._security.create_access_token(
            contractor_id=contractor.id,
            username=contractor.username,
            roles=contractor.roles,
        )

        logger.info(f"[AuthService] Contractor logged in: {contractor.username} (id={contractor.id})")

        return LoginResponse(
            access_token=token,
            token_type="bearer",
            expires_in=self._security.token_expire_seconds,
            contractor=ContractorPublic.from_contractor(contractor),
        )

    async def register(self, req: RegisterRequest) -> ContractorPublic:
        """Register a new contractor. First registered user automatically becomes admin."""
        existing = await self._store.get_contractor_by_username(req.username)
        if existing:
            raise ContractorAlreadyExistsError(req.username)

        # First contractor bootstrapping: granting admin role
        total_count = await self._store.contractor_count()
        roles = ["admin", "contractor"] if total_count == 0 else ["contractor"]

        password_hash = self._security.hash_password(req.password)
        contractor = ShadowContractor(
            username=req.username,
            email=req.email,
            password_hash=password_hash,
            display_name=req.display_name or req.username,
            roles=roles,
        )

        created = await self._store.create_contractor(contractor)
        logger.info(f"[AuthService] New contractor registered: {created.username} (roles={roles})")

        return ContractorPublic.from_contractor(created)

    async def get_me(self, current_contractor: ShadowContractor) -> ContractorPublic:
        """Return public-safe projection of the current contractor."""
        return ContractorPublic.from_contractor(current_contractor)
