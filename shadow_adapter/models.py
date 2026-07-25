"""Data models for the Shadow Adapter.

All models are Pydantic v2 BaseModel subclasses. They define the data contracts
between the adapter, the isolated SQLite store, the REST API, and OpenOPC.

Architectural note:
  - ``ShadowTask`` is the adapter's *own* record. It copies fields from the
    OpenOPC ``Task`` at intercept time but is fully independent afterward.
  - ``extra_metadata`` on ShadowTask is the extensibility hook — future custom
    fields can be added without schema migrations.
  - All models use ``ConfigDict(extra='ignore')`` or ``extra='allow'`` to ensure
    100% mathematical immunity to upstream OpenOPC schema changes.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:

    class StrEnum(str, Enum):
        pass


from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ShadowTaskStatus(StrEnum):
    """Lifecycle states for a parked shadow task."""

    PENDING = "pending"
    """Task intercepted from OpenOPC and waiting for a human to claim it."""

    CLAIMED = "claimed"
    """A contractor has claimed the task but not yet submitted a deliverable."""

    SUBMITTED = "submitted"
    """The contractor submitted a deliverable; resume pipeline is running."""

    RESUMED = "resumed"
    """The result was successfully pushed back into OpenOPC."""

    FAILED = "failed"
    """The resume pipeline failed, or the task was rejected."""

    CANCELLED = "cancelled"
    """The task was cancelled (by admin or upstream OpenOPC cancellation)."""


# ---------------------------------------------------------------------------
# Core Domain Models
# ---------------------------------------------------------------------------


class ShadowTask(BaseModel):
    """A human-parked task — the adapter's local record of an intercepted OpenOPC task."""

    model_config = ConfigDict(extra="allow", from_attributes=True)

    # Our own identity
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # OpenOPC provenance (immutable after creation)
    opc_task_id: str
    opc_session_id: str | None = None
    opc_project_id: str = "default"
    opc_work_item_id: str = ""
    opc_metadata: dict[str, Any] = Field(default_factory=dict)

    # Human-readable content
    title: str
    description: str = ""
    assigned_role: str = ""
    priority: int = 5

    # Lifecycle
    status: ShadowTaskStatus = ShadowTaskStatus.PENDING
    assigned_contractor_id: str | None = None

    # Deliverables
    deliverable_text: str | None = None
    deliverable_files: list[str] = Field(default_factory=list)

    # Timestamps
    parked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    claimed_at: datetime | None = None
    submitted_at: datetime | None = None
    resumed_at: datetime | None = None
    deadline: datetime | None = None

    # Extensibility — arbitrary metadata for plugins / future features
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Infrastructure Boundary DTOs (Kill God Object Config Coupling)
# ---------------------------------------------------------------------------


class UploadLimits(BaseModel):
    """Strict boundary DTO. Replaces passing full ShadowConfig to upload functions."""

    model_config = ConfigDict(extra="ignore")

    max_file_count: int
    max_file_size_bytes: int
    max_total_size_bytes: int
    allowed_extensions: set[str]


class JwtConfig(BaseModel):
    """Strict boundary DTO. Replaces passing full ShadowConfig to SecurityManager."""

    model_config = ConfigDict(extra="ignore")

    secret: str
    algorithm: str = "HS256"
    expire_hours: int = 24


class UploadFileDTO(BaseModel):
    """Framework-agnostic file upload representation.

    Decouples the Service layer from FastAPI's UploadFile type.
    Controllers convert FastAPI UploadFile -> UploadFileDTO at the boundary.
    """

    model_config = ConfigDict(extra="ignore")

    filename: str
    content: bytes
    size: int


class ShadowSubmission(BaseModel):
    """Inbound deliverable payload from a human contractor."""

    model_config = ConfigDict(extra="ignore")

    deliverable_text: str = ""
    deliverable_files: list[str] = Field(default_factory=list)
    notes: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


class ShadowContractor(BaseModel):
    """A human contractor account (stored in shadow_contractors table)."""

    model_config = ConfigDict(extra="allow", from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str | None = None
    password_hash: str = ""
    display_name: str = ""
    roles: list[str] = Field(default_factory=lambda: ["contractor"])
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ShadowAuditEntry(BaseModel):
    """Immutable audit log record — tracks every action on a shadow task."""

    model_config = ConfigDict(extra="allow", from_attributes=True)

    id: int | None = None
    shadow_task_id: str
    actor_id: str | None = None
    action: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Resume Result (outcome of pushing result back to OpenOPC)
# ---------------------------------------------------------------------------


class TaskResumeResult(BaseModel):
    """Outcome of the resume pipeline — pushing a human deliverable back into OpenOPC."""

    model_config = ConfigDict(extra="ignore")

    success: bool
    shadow_task_id: str
    opc_task_id: str
    opc_task_status: str = ""
    opc_work_item_phase: str = ""
    message: str = ""
    error: str | None = None


# ---------------------------------------------------------------------------
# API Request / Response schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    username: str
    password: str


class LoginResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    contractor: ContractorPublic | None = None


class ContractorPublic(BaseModel):
    """Public-facing contractor info (no password hash)."""

    model_config = ConfigDict(extra="ignore")

    id: str
    username: str
    email: str | None = None
    display_name: str = ""
    roles: list[str] = Field(default_factory=list)
    is_active: bool = True

    @classmethod
    def from_contractor(cls, c: ShadowContractor) -> ContractorPublic:
        """Project a full ShadowContractor into its public-safe representation."""
        return cls(
            id=c.id,
            username=c.username,
            email=c.email,
            display_name=c.display_name,
            roles=c.roles,
            is_active=c.is_active,
        )


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    username: str
    password: str
    email: str | None = None
    display_name: str | None = None


class TaskSubmitResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    shadow_task_id: str
    status: str
    opc_resume_status: str = ""
    message: str = ""


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: str = "ok"
    db: str = "connected"
    pending_tasks: int = 0
    version: str = ""


# Rebuild LoginResponse now that ContractorPublic is defined
LoginResponse.model_rebuild()
