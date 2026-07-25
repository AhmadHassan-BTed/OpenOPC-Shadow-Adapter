# Phase 4: Isolated Testing & Mocking

> **Goal:** Build a mock OpenOPC engine simulator, write comprehensive Pytest unit and integration tests guaranteeing the adapter correctly intercepts, parks, handles API submissions, and fires resume callbacks without crashing.

---

## 4.1 — `tests/mock_openopc_engine.py` (Engine Simulator)

**Purpose:** Simulate an OpenOPC DAG dispatching a task to the shadow adapter without requiring a full OpenOPC installation. This mock is also reusable as a development harness.

**What it simulates:**
1. Creates an in-memory SQLite store mimicking OpenOPC's task/work_item tables
2. Constructs a `Task` with `assigned_external_agent="shadow"`
3. Calls `adapter.execute(task, workspace)` 
4. Validates the returned `TaskResult.status == AWAITING_HUMAN`
5. Verifies the task row in the mock store reflects the parked state
6. Simulates a human submission through the shadow API
7. Verifies the resume callback updates the mock store correctly
8. Verifies dependent work items would be unblocked

**Mock Store Schema (minimal OpenOPC-compatible subset):**
```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    title TEXT,
    description TEXT,
    assigned_to TEXT,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    project_id TEXT DEFAULT 'default',
    metadata TEXT DEFAULT '{}',
    result TEXT,
    execution_lock INTEGER DEFAULT 0,
    created_at TEXT
);

CREATE TABLE delegation_work_items (
    work_item_id TEXT PRIMARY KEY,
    run_id TEXT,
    role_id TEXT,
    title TEXT,
    phase TEXT DEFAULT 'ready',
    metadata TEXT DEFAULT '{}',
    created_at TEXT
);
```

**Key Classes:**
```python
class MockOPCStore:
    """Minimal mock of OPCStore with task/work_item CRUD."""
    async def initialize(self) -> None
    async def get_task(self, task_id: str) -> dict | None
    async def save_task(self, task: dict) -> None
    async def update_task_status(self, task_id: str, status: str) -> None
    async def get_work_item(self, work_item_id: str) -> dict | None
    async def update_work_item_phase(self, work_item_id: str, phase: str) -> None

class MockDAGRunner:
    """Simulates DAG execution dispatching to the shadow adapter."""
    async def dispatch_to_shadow(self, task_title: str, task_description: str) -> TaskResult
    async def simulate_full_lifecycle(self) -> dict  # Returns lifecycle report
```

---

## 4.2 — `tests/conftest.py` (Shared Fixtures)

**Fixtures:**
```python
@pytest.fixture
async def shadow_config() -> ShadowConfig
    """Config with temp directories and test JWT secret."""

@pytest.fixture
async def shadow_store(shadow_config, tmp_path) -> AsyncGenerator[ShadowStore, None]
    """Initialized ShadowStore with ephemeral DB."""

@pytest.fixture
async def mock_opc_store(tmp_path) -> AsyncGenerator[MockOPCStore, None]
    """Initialized mock OpenOPC store."""

@pytest.fixture
def adapter(shadow_store) -> ShadowModeAdapter
    """Configured adapter instance."""

@pytest.fixture
async def api_client(shadow_config, shadow_store) -> AsyncGenerator[AsyncClient, None]
    """httpx AsyncClient against the FastAPI test app."""

@pytest.fixture
async def auth_token(api_client) -> str
    """JWT token for a test contractor."""

@pytest.fixture
def sample_task() -> Task
    """A representative OpenOPC Task for testing."""

@pytest.fixture
def sample_work_item() -> dict
    """A representative DelegationWorkItem row."""
```

---

## 4.3 — `tests/test_shadow_store.py` (Store Unit Tests)

| Test | What it verifies |
|---|---|
| `test_create_task` | Task is persisted with all fields |
| `test_get_task_by_id` | Retrieval by shadow task ID |
| `test_get_task_by_opc_id` | Retrieval by OpenOPC task ID |
| `test_list_tasks_filter_status` | Status filtering works |
| `test_list_tasks_filter_contractor` | Contractor filtering works |
| `test_list_tasks_pagination` | Limit/offset work correctly |
| `test_claim_task` | Status transitions pending→claimed, contractor assigned |
| `test_claim_already_claimed` | Raises error on double-claim |
| `test_submit_task` | Status transitions claimed→submitted, deliverables saved |
| `test_submit_unclaimed_task` | Raises error |
| `test_mark_resumed` | Status transitions submitted→resumed |
| `test_mark_failed` | Status transitions to failed with reason |
| `test_create_contractor` | Contractor persisted with hashed password |
| `test_get_contractor_by_username` | Username lookup works |
| `test_audit_log` | Audit entries created on writes |
| `test_schema_migration` | DB created from scratch with correct schema |

---

## 4.4 — `tests/test_adapter.py` (Adapter Lifecycle Tests)

| Test | What it verifies |
|---|---|
| `test_is_available` | Always returns True |
| `test_get_status` | Returns AgentStatus.IDLE |
| `test_execute_parks_task` | execute() creates shadow task and returns AWAITING_HUMAN |
| `test_execute_returns_immediately` | execute() completes in < 100ms (no blocking) |
| `test_execute_preserves_opc_metadata` | All Task fields mapped to ShadowTask |
| `test_build_invocation` | Returns empty command list |
| `test_resume_task_success` | Resume updates mock OPC store with DONE status |
| `test_resume_task_updates_work_item` | Work item phase transitions to APPROVED |
| `test_resume_task_missing_opc_task` | Handles missing task gracefully |
| `test_task_to_shadow_task_mapping` | Field mapping is complete and correct |
| `test_shadow_to_task_result_mapping` | TaskResult construction is correct |
| `test_duplicate_execute_same_task` | Idempotent — returns existing shadow task |

---

## 4.5 — `tests/test_api.py` (API Endpoint Tests)

| Test | What it verifies |
|---|---|
| `test_health_check` | GET /health returns 200 |
| `test_login_success` | Valid credentials return JWT |
| `test_login_invalid_password` | Returns 401 |
| `test_login_unknown_user` | Returns 401 |
| `test_register_first_user_is_admin` | First user gets admin role |
| `test_register_requires_admin` | Non-admin cannot register users |
| `test_list_tasks_unauthenticated` | Returns 401 |
| `test_list_tasks_authenticated` | Returns task list |
| `test_get_task_detail` | Returns full task with context |
| `test_claim_task` | Assigns contractor to task |
| `test_claim_already_claimed` | Returns 409 |
| `test_submit_with_text` | Text deliverable accepted, resume triggered |
| `test_submit_with_files` | File upload accepted, stored securely |
| `test_submit_wrong_contractor` | Cannot submit task claimed by another |
| `test_submit_unclaimed_task` | Returns 400 |
| `test_get_audit_trail` | Returns ordered audit entries |

---

## 4.6 — `tests/test_security.py` (Security Tests)

| Test | What it verifies |
|---|---|
| `test_password_hash_verify` | bcrypt round-trip works |
| `test_password_different_hashes` | Same password → different hashes (salt) |
| `test_jwt_create_decode` | Token round-trip with correct claims |
| `test_jwt_expired` | Expired token raises |
| `test_jwt_invalid_signature` | Wrong secret raises |
| `test_jwt_missing_claims` | Malformed token raises |
| `test_filename_sanitization` | Path traversal stripped |
| `test_filename_no_directory_components` | `../../etc/passwd` → `etc_passwd` |
| `test_extension_allowlist` | `.exe` rejected, `.pdf` accepted |
| `test_file_size_limit` | Oversized file rejected |
| `test_upload_uuid_prefix` | Stored files have UUID prefix |

---

## Implementation Order

1. `conftest.py` — Shared fixtures (foundation for all tests)
2. `mock_openopc_engine.py` — Engine simulator
3. `test_shadow_store.py` — Store tests (validates Phase 2 store)
4. `test_adapter.py` — Adapter tests (validates Phase 2 adapter)
5. `test_security.py` — Security tests (validates Phase 3 security)
6. `test_api.py` — API tests (validates Phase 3 API)
