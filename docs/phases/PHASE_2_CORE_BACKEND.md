# Phase 2: Core Backend & Isolated Storage

> **Goal:** Build the foundational backend — the adapter class, isolated SQLite store, data models, configuration system, and the async intercept→park→resume pipeline.

---

## 2.1 — `pyproject.toml` (Package Scaffold)

**Architectural Decisions:**
- Treat `opc` as an **optional** dependency (`extras_require`), not a hard requirement. This lets the shadow API server run standalone for humans who don't have OpenOPC installed locally.
- Use `hatchling` build backend to match OpenOPC's own tooling.
- Expose a CLI entry point `shadow-serve` for the API server.

**Key Dependencies:**
```
opc (optional, for adapter integration)
fastapi + uvicorn (API server)
pydantic >= 2.0 (data models)
aiosqlite >= 0.19 (async SQLite)
python-jose[cryptography] (JWT)
passlib[bcrypt] (password hashing)
python-multipart (file uploads)
streamlit (UI, optional)
pytest + httpx (testing)
```

---

## 2.2 — `shadow_adapter/models.py` (Data Models)

**Design Principles:**
- All models are Pydantic v2 `BaseModel` subclasses for validation + serialization.
- `ShadowTaskStatus` is a `StrEnum` for forward-compatible JSON serialization.
- Every model supports `.model_dump()` for DB persistence and `.model_validate()` for hydration.
- **Extensibility hook:** `extra_metadata: dict` field on `ShadowTask` for future custom fields without schema migration.

**Models to implement:**
1. `ShadowTaskStatus` — Enum: `pending`, `claimed`, `submitted`, `resumed`, `failed`, `cancelled`
2. `ShadowTask` — Full task representation with OpenOPC provenance fields
3. `ShadowSubmission` — Inbound submission payload (text + file refs)
4. `ShadowContractor` — Human contractor account
5. `ShadowAuditEntry` — Immutable audit log record
6. `TaskResumeResult` — Outcome of pushing result back to OpenOPC

---

## 2.3 — `shadow_adapter/config.py` (Configuration)

**Design Principles:**
- Use `pydantic-settings` for 12-factor env var loading with `.env` file support.
- Every setting has a sensible default so zero-config startup works.
- **Extensibility hook:** `extra_settings: dict` for future plugin-injected config.

**Settings:**
| Setting | Env Var | Default |
|---|---|---|
| `db_path` | `SHADOW_DB_PATH` | `./shadow_tasks.db` |
| `jwt_secret` | `SHADOW_JWT_SECRET` | *required* |
| `jwt_algorithm` | `SHADOW_JWT_ALGORITHM` | `HS256` |
| `jwt_expire_hours` | `SHADOW_JWT_EXPIRE_HOURS` | `24` |
| `upload_dir` | `SHADOW_UPLOAD_DIR` | `./shadow_uploads` |
| `max_upload_size_mb` | `SHADOW_MAX_UPLOAD_SIZE_MB` | `50` |
| `allowed_extensions` | `SHADOW_ALLOWED_EXTENSIONS` | `.pdf,.docx,.xlsx,.txt,.md,.png,.jpg,.zip` |
| `opc_store_path` | `SHADOW_OPC_STORE_PATH` | `.opc/projects/default/store.db` |
| `api_port` | `SHADOW_API_PORT` | `8800` |
| `api_host` | `SHADOW_API_HOST` | `0.0.0.0` |
| `log_level` | `SHADOW_LOG_LEVEL` | `INFO` |

---

## 2.4 — `shadow_adapter/shadow_store.py` (Isolated Storage)

**Architectural Decisions:**
- **Complete isolation**: Own SQLite database, own connection pool, own schema. Never touches OpenOPC's store.db.
- **Async-first**: All operations are `async def` using `aiosqlite`.
- **Migration-ready**: Schema version table + `_ensure_schema()` method that runs on init. Future migrations append to a version chain.
- **Audit trail**: Every write operation also inserts into `shadow_audit_log`.

**CRUD Operations:**
```python
class ShadowStore:
    async def initialize(self) -> None          # Create DB + schema
    async def close(self) -> None               # Close connection

    # Tasks
    async def create_task(self, task: ShadowTask) -> ShadowTask
    async def get_task(self, task_id: str) -> ShadowTask | None
    async def get_task_by_opc_id(self, opc_task_id: str) -> ShadowTask | None
    async def list_tasks(self, status: str | None, contractor_id: str | None, limit: int, offset: int) -> list[ShadowTask]
    async def update_task_status(self, task_id: str, status: ShadowTaskStatus, **fields) -> ShadowTask
    async def claim_task(self, task_id: str, contractor_id: str) -> ShadowTask
    async def submit_task(self, task_id: str, submission: ShadowSubmission) -> ShadowTask
    async def mark_resumed(self, task_id: str) -> ShadowTask
    async def mark_failed(self, task_id: str, reason: str) -> ShadowTask

    # Contractors
    async def create_contractor(self, contractor: ShadowContractor) -> ShadowContractor
    async def get_contractor(self, contractor_id: str) -> ShadowContractor | None
    async def get_contractor_by_username(self, username: str) -> ShadowContractor | None
    async def list_contractors(self) -> list[ShadowContractor]

    # Audit
    async def log_audit(self, task_id: str, actor_id: str, action: str, details: dict) -> None
    async def get_audit_log(self, task_id: str) -> list[ShadowAuditEntry]
```

---

## 2.5 — `shadow_adapter/adapter.py` (ShadowModeAdapter)

**This is the heart of the package.** It extends `ExternalAgentAdapter` and implements the non-blocking execute→park→resume lifecycle.

**Architectural Decisions:**
- `execute()` is the **only** method that OpenOPC calls. It must return a `TaskResult` — we return `AWAITING_HUMAN` immediately.
- `build_invocation()` returns empty command (no subprocess). Required by ABC.
- `is_available()` always returns `True` (no binary dependency).
- `get_status()` returns `AgentStatus.IDLE` (we're never "running" from OpenOPC's perspective).
- **Resume pipeline** is a separate classmethod/staticmethod that the API server calls. It opens a connection to OpenOPC's store and pushes the result.

**Key Methods:**
```python
class ShadowModeAdapter(ExternalAgentAdapter):
    agent_type = "shadow"
    
    async def is_available(self) -> bool
    async def execute(self, task: Task, workspace_path: str) -> TaskResult
    async def get_status(self) -> AgentStatus
    def build_invocation(self, task, workspace_path=None) -> tuple[list[str], dict]
    
    # Resume pipeline (called by API, not by OpenOPC)
    @staticmethod
    async def resume_task(shadow_task: ShadowTask, opc_store_path: str) -> TaskResumeResult
    
    @staticmethod
    def _task_to_shadow_task(task: Task) -> ShadowTask
    
    @staticmethod
    def _shadow_to_task_result(shadow_task: ShadowTask) -> TaskResult
```

**Resume Pipeline Detail:**
1. Open a connection to OpenOPC's SQLite store (read the path from config)
2. Load the original task by `opc_task_id`
3. Construct `TaskResult(status=DONE, content=deliverable_text, artifacts={...})`
4. Update task status: `UPDATE tasks SET status='done', result=? WHERE id=?`
5. Update work item phase: `UPDATE delegation_work_items SET phase='approved' WHERE work_item_id=?`
6. The phase transition hooks fire automatically on next OpenOPC engine tick
7. Return `TaskResumeResult` with success/failure info

---

## 2.6 — `shadow_adapter/upload.py` (File Security)

**Security-first upload handler:**
```python
class SecureUploadHandler:
    def sanitize_filename(self, filename: str) -> str
    def validate_extension(self, filename: str) -> bool
    def validate_size(self, size: int) -> bool
    async def save_upload(self, file: UploadFile, task_id: str) -> str  # returns safe path
    def get_upload_path(self, task_id: str, filename: str) -> Path
```

**Invariants enforced:**
- No path separators in filename after sanitization
- UUID prefix on all stored files
- Extension allowlist check
- Size limit streaming check (no full file load into memory)
- Upload directory is task-scoped: `{upload_dir}/{task_id}/{uuid}_{safe_name}`

---

## Implementation Order

1. `models.py` — Data foundation (no dependencies)
2. `config.py` — Settings (depends on models)
3. `shadow_store.py` — Storage (depends on models, config)
4. `upload.py` — File security (depends on config)
5. `adapter.py` — Core adapter (depends on all above + opc)
6. `pyproject.toml` — Package definition
