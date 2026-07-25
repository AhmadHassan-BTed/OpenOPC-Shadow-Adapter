"""JWT authentication and password hashing for human contractors.

This module is the Shadow Adapter's own auth system — completely independent
of OpenOPC's internal user management. It issues HS256 JWTs for contractors
who log in through the REST API, and uses direct bcrypt hashing for password
storage.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt
from loguru import logger

from shadow_adapter.config import ShadowConfig


class SecurityManager:
    """Handles JWT issuance/verification and password hashing."""

    def __init__(self, config: ShadowConfig) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Password hashing using direct bcrypt
    # ------------------------------------------------------------------

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plaintext password using bcrypt with auto-salt."""
        pwd_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against a bcrypt hash."""
        try:
            plain_bytes = plain_password.encode("utf-8")
            hash_bytes = hashed_password.encode("utf-8")
            return bcrypt.checkpw(plain_bytes, hash_bytes)
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
        """Create a signed JWT access token."""
        now = datetime.now(timezone.utc)
        expire = now + (expires_delta if expires_delta is not None else timedelta(hours=self.config.jwt_expire_hours))
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
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret,
                algorithms=[self.config.jwt_algorithm],
            )
        except JWTError as exc:
            logger.debug(f"JWT decode failed: {exc}")
            raise ValueError(f"Invalid or expired token: {exc}") from exc

        if not payload.get("sub"):
            raise ValueError("Token missing 'sub' claim")
        if not payload.get("username"):
            raise ValueError("Token missing 'username' claim")

        return payload

    @property
    def token_expire_seconds(self) -> int:
        """Token lifetime in seconds."""
        return self.config.jwt_expire_hours * 3600
