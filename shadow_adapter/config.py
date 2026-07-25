"""Configuration for the Shadow Adapter.

Uses ``pydantic-settings`` for 12-factor env-var loading with ``.env`` file
support.  Every setting has a sensible default so zero-config startup works
for local development (except ``jwt_secret`` which **must** be set).

Extensibility hook: ``extra_settings`` dict for plugin-injected config.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ShadowConfig(BaseSettings):
    """Central configuration for the openopc-shadow-adapter package."""

    model_config = SettingsConfigDict(
        env_prefix="SHADOW_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────
    db_path: str = Field(
        default="./shadow_tasks.db",
        description="Path to the isolated SQLite database for parked tasks.",
    )

    # ── JWT Authentication ────────────────────────────────────────────────
    jwt_secret: str = Field(
        default="CHANGE-ME-insecure-default-secret-key",
        description="Secret key for JWT signing. MUST be changed in production.",
    )
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_hours: int = Field(
        default=24,
        description="JWT token lifetime in hours.",
    )

    # ── File Uploads ──────────────────────────────────────────────────────
    upload_dir: str = Field(
        default="./shadow_uploads",
        description="Directory for securely storing uploaded deliverable files.",
    )
    max_total_upload_size_mb: int = Field(
        default=50,
        description="Maximum total payload size per submission in megabytes.",
    )
    max_file_size_mb: int = Field(
        default=10,
        description="Maximum size per individual file in megabytes.",
    )
    max_files_per_submission: int = Field(
        default=5,
        description="Maximum number of files per submission.",
    )
    allowed_extensions: str = Field(
        default=".pdf,.docx,.xlsx,.pptx,.txt,.md,.png,.jpg,.jpeg,.zip,.tar.gz",
        description="Comma-separated list of allowed file extensions.",
    )

    # ── OpenOPC Integration ───────────────────────────────────────────────
    opc_store_path: str = Field(
        default=".opc/projects/default/store.db",
        description="Path to OpenOPC's SQLite store.db for resume callbacks.",
    )

    # ── API Server ────────────────────────────────────────────────────────
    api_port: int = Field(default=8800)
    api_host: str = Field(default="0.0.0.0")

    # ── Logging ───────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")

    # ── Extensibility ─────────────────────────────────────────────────────
    extra_settings: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary key-value pairs for plugin configuration.",
    )

    # ── Future: Webhook callback ──────────────────────────────────────────
    webhook_url: str | None = Field(
        default=None,
        description="Optional webhook URL for task lifecycle notifications.",
    )

    # ── Helpers ───────────────────────────────────────────────────────────

    @property
    def allowed_extensions_set(self) -> set[str]:
        """Parse the comma-separated extensions string into a set."""
        return {
            ext.strip().lower()
            for ext in self.allowed_extensions.split(",")
            if ext.strip()
        }

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_total_upload_size_mb * 1024 * 1024

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def db_file_path(self) -> Path:
        return Path(self.db_path)
