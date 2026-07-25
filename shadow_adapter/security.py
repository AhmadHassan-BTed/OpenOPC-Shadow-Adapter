"""JWT authentication and password hashing for human contractors.

This module is the Shadow Adapter's own auth system — completely independent
of OpenOPC's internal user management.  It issues HS256 JWTs for contractors
who log in through the REST API, and uses bcrypt (via passlib) for password
storage.

Architectural notes
───────────────────
* **Standalone** — no dependency on OpenOPC auth or session management.
* **Bootstrap** — the first registered user is automatically granted the
  ``admin`` role, solving the chicken-and-egg problem.
* **Extensible** — ``create_access_token`` accepts ``custom_claims`` for
  future RBAC / scope-based extensions.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from loguru import logger
from passlib.context import CryptContext

from shadow_adapter.config import ShadowConfig

# bcrypt context with auto-salt
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityManager:
    """Handles JWT issuance/verification and password hashing."""

    def __init__(self, config: ShadowConfig) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Password hashing
    # ------------------------------------------------------------------

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plaintext password using bcrypt with auto-salt."""
        return _pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against a bcrypt hash."""
        try:
            return _pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # JWT token management
    # ------------------------------------------------------------------

    def create_access_token(
        self,
        contractor_id: str,
        username: str,
        roles: list[str],
        *,
        custom_claims: dict[str, Any] | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create a signed JWT access token.

        Parameters
        ----------
        contractor_id:
            The contractor's unique ID (becomes the ``sub`` claim).
        username:
            The contractor's login name.
        roles:
            List of role strings (e.g. ``["contractor"]``, ``["admin"]``).
        custom_claims:
            Optional extra claims merged into the payload for future
            RBAC or scope extensions.
        expires_delta:
            Override the default expiry (``config.jwt_expire_hours``).
        """
        now = datetime.now(timezone.utc)
        expire = now + (
            expires_delta
            if expires_delta is not None
            else timedelta(hours=self.config.jwt_expire_hours)
        )
        payload: dict[str, Any] = {
            "sub": contractor_id,
            "username": username,
            "roles": roles,
            "iat": now,
            "exp": expire,
        }
        if custom_claims:
            payload.update(custom_claims)

        return jwt.encode(
            payload,
            self.config.jwt_secret,
            algorithm=self.config.jwt_algorithm,
        )

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decode and validate a JWT token.

        Returns the full claims dict on success.

        Raises
        ------
        ValueError
            If the token is expired, has an invalid signature, or is
            malformed.
        """
        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret,
                algorithms=[self.config.jwt_algorithm],
            )
        except JWTError as exc:
            logger.debug(f"JWT decode failed: {exc}")
            raise ValueError(f"Invalid or expired token: {exc}") from exc

        # Validate required claims
        if not payload.get("sub"):
            raise ValueError("Token missing 'sub' claim")
        if not payload.get("username"):
            raise ValueError("Token missing 'username' claim")

        return payload

    @property
    def token_expire_seconds(self) -> int:
        """Token lifetime in seconds (for API response ``expires_in``)."""
        return self.config.jwt_expire_hours * 3600
