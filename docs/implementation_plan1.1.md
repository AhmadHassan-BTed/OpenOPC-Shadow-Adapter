# Implementation Plan: Symbiotic Compatibility Fix

> **Goal**: Resolve all 12 issues from the [Compatibility Audit](file:///home/leech/.gemini/antigravity-ide/brain/5e36574d-1d33-47ca-9558-5489286aab6d/compatibility_audit.md) to make `openopc-shadow-adapter` a true, zero-error symbiote on OpenOPC.

---

## Phase 1: Critical Runtime Fixes (Must Ship First)

These 5 fixes prevent **hard crashes** when the OpenOPC engine dispatches a task to our adapter.

---

### Fix 1.1 — Override `start_process()` and Rewire the Execution Path

**Problem**: The broker calls `adapter.start_process()` → `asyncio.create_subprocess_exec(*[])` → crash. Our `execute()` method is dead code.

**Solution**: Override `start_process()` on `ShadowModeAdapter` to perform the task-parking logic internally (the same logic currently in `execute()`), then return a **mock process** that the broker's stream monitor can safely consume.

#### [MODIFY] [adapter.py](file:///home/leech/Projects/OpenOPC/openopc-shadow-adapter/shadow_adapter/adapter.py)

```python
import asyncio

async def start_process(
    self,
    cmd: list[str],
    workspace_path: str,
    extra_env: dict[str, str] | None = None,
    task: Task | None = None,
    launch_metadata: dict[str, Any] | None = None,
) -> asyncio.subprocess.Process:
    """Override: park the task in shadow DB instead of launching a subprocess.
    
    Returns a completed mock process so the broker's stream monitor
    exits cleanly with a DONE result containing our deliverable content.
    """
    if task is not None:
        result = await self.execute(task, workspace_path)
        # Stash the result so normalize_result_output can retrieve it
        self._last_shadow_result = result
    
    # Return a process that is already finished (exit code 0)
    # The broker reads stdout/stderr streams — we give it our result content
    proc = await asyncio.create_subprocess_exec(
        "echo", result.content if task else "shadow_mode_parked",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    return proc
```

And override `normalize_result_output()` to return the stashed shadow result:

```python
def normalize_result_output(self, output: str) -> str:
    if hasattr(self, "_last_shadow_result"):
        return self._last_shadow_result.content
    return output
```

And override `extract_structured_result_fields()` to return shadow artifacts:

```python
def extract_structured_result_fields(self, output: str) -> dict[str, Any]:
    if hasattr(self, "_last_shadow_result"):
        return self._last_shadow_result.artifacts or {}
    return {}
```

---

### Fix 1.2 — Implement `agent_isolation_home_slug()` for Company Mode

**Problem**: Broker checks `adapter.agent_isolation_home_slug()` → `None` → `RuntimeError` crash.

**Solution**: Return a slug so the broker provisions a home directory. The shadow adapter doesn't need it, but the broker mandates it.

#### [MODIFY] [adapter.py](file:///home/leech/Projects/OpenOPC/openopc-shadow-adapter/shadow_adapter/adapter.py)

```python
def agent_isolation_home_slug(self) -> str | None:
    """Provide a home slug for Company Mode collaboration surface."""
    return "shadow"

def agent_home_env_vars(self, home: str) -> dict[str, str]:
    """No agent-specific env vars needed — shadow parks, not executes."""
    return {"SHADOW_ADAPTER_HOME": home}

def post_install_agent_home(self, home: str) -> None:
    """No post-install actions needed for shadow adapter."""
    pass
```

---

### Fix 1.3 — Fix `get_status()` Return Type

**Problem**: Returns `TaskStatus.IDLE` (wrong enum) or bare string `"idle"` instead of `AgentStatus`.

**Solution**:

#### [MODIFY] [adapter.py](file:///home/leech/Projects/OpenOPC/openopc-shadow-adapter/shadow_adapter/adapter.py)

```python
async def get_status(self, *args: Any, **kwargs: Any) -> Any:
    """Return IDLE AgentStatus since human work happens asynchronously."""
    try:
        from opc.core.models import AgentStatus
        return AgentStatus.IDLE
    except ImportError:
        return "idle"
```

---

### Fix 1.4 — Handle Missing `ExternalAgentConfig` Gracefully

**Problem**: `AgentsConfig.agents` has no `"shadow"` key → `config=None` → adapter gets default `ExternalAgentConfig(command="shadow")` which is fine, but `self.config.run_mode` defaults to `"batch"`.

**Solution**: Our adapter should work correctly regardless of what config it receives. Set sensible defaults in the constructor:

#### [MODIFY] [adapter.py](file:///home/leech/Projects/OpenOPC/openopc-shadow-adapter/shadow_adapter/adapter.py)

```python
def __init__(self, config: Any = None, **kwargs: Any) -> None:
    super().__init__(config)
    self.shadow_config = kwargs.get("shadow_config") or ShadowConfig()
    self._shadow_store = kwargs.get("shadow_store")
    self._last_shadow_result = None
```

> [!NOTE]
> The user should also add `"shadow": ExternalAgentConfig(command="shadow", run_mode="batch")` to their `agents.yaml` if they want explicit control. But the adapter MUST NOT crash if absent.

---

### Fix 1.5 — Replace Raw SQL Resume with Phase-Safe Callback

**Problem**: Our `OpcResumeRepository` writes raw SQL `UPDATE delegation_work_items SET phase = 'approved'`, bypassing `validate_transition()` and `on_phase_transition()` hooks, leaving the DAG permanently desynchronized.

**Solution**: Two approaches, both symbiotic (zero core modifications):

#### Option A (Recommended): Use OpenOPC's Store API When Available

```python
async def resume(self, shadow_task, opc_store_path, ...):
    try:
        from opc.database.store import OPCStore
        from opc.core.models import Phase
        
        store = OPCStore(opc_store_path)
        await store.initialize()
        
        # Use the store's own transition method which fires hooks
        if shadow_task.opc_work_item_id:
            await store.update_delegation_work_item_phase(
                work_item_id=shadow_task.opc_work_item_id,
                phase=Phase.APPROVED,
            )
        
        # Update task status through the store's task API
        if shadow_task.opc_task_id:
            await store.update_task_status(
                task_id=shadow_task.opc_task_id,
                status="done",
                result=self._build_result_json(shadow_task, ...),
            )
        
        await store.close()
    except ImportError:
        # Fallback to raw SQL when OpenOPC is not importable (standalone mode)
        await self._raw_sql_resume(shadow_task, opc_store_path, ...)
```

#### Option B (Fallback): Raw SQL with Phase Validation

If Option A fails (standalone mode), validate the transition ourselves:

```python
# Before writing, check current phase and validate transition
async with aiosqlite.connect(str(db_path)) as db:
    cursor = await db.execute(
        "SELECT phase FROM delegation_work_items WHERE work_item_id = ?",
        (shadow_task.opc_work_item_id,)
    )
    row = await cursor.fetchone()
    current_phase = row[0] if row else None
    
    # Only AWAITING_HUMAN → APPROVED is legal for our use case
    LEGAL_SOURCE_PHASES = {"awaiting_human", "running", "awaiting_manager_review"}
    if current_phase not in LEGAL_SOURCE_PHASES:
        return TaskResumeResult(
            success=False,
            error=f"Illegal phase transition: {current_phase} → approved"
        )
```

---

## Phase 2: Major Alignment Fixes (UI & Functional Parity)

---

### Fix 2.1 — Align UI Design Tokens with OpenOPC Office

**Problem**: Our accent is teal `#14b8a6`, theirs is indigo `#6366f1`. Variable names differ.

**Solution**: Match their exact token values:

#### [MODIFY] [index.css](file:///home/leech/Projects/OpenOPC/openopc-shadow-adapter/shadow_adapter/frontend/src/index.css)

```css
:root {
  /* Exact match with OpenOPC Office UI .app-shell tokens */
  --bg: #0c111b;
  --bg-elevated: #141b2b;
  --bg-card: #141b2b;
  --bg-secondary: #1a2332;
  --text: #e2e8f0;
  --text-secondary: #8494a7;
  --text-dim: #64748b;
  --border: rgba(148, 163, 184, 0.12);
  --border-hover: rgba(148, 163, 184, 0.22);
  --surface: rgba(20, 27, 43, 0.7);
  --surface-hover: rgba(30, 41, 63, 0.7);
  --accent: #6366f1;                          /* ← CHANGED from teal to indigo */
  --accent-soft: rgba(99, 102, 241, 0.15);    /* ← CHANGED */
  --accent-glow: rgba(99, 102, 241, 0.3);     /* ← NEW */
  --green: #34d399;
  --yellow: #fbbf24;
  --red: #f87171;
  --radius: 12px;
  --radius-sm: 8px;
  --radius-xs: 6px;
  --white: #ffffff;
}
```

---

### Fix 2.2 — Migrate from Tailwind to Vanilla CSS

**Problem**: OpenOPC's Office UI uses pure vanilla CSS. We use Tailwind, creating framework incompatibility.

**Solution**: Replace `@import "tailwindcss/..."` with a vanilla CSS reset and port all Tailwind utility classes to custom CSS. This is a significant but necessary refactor to maintain the "Twin UI" symbiote promise.

#### [MODIFY] [index.css](file:///home/leech/Projects/OpenOPC/openopc-shadow-adapter/shadow_adapter/frontend/src/index.css)

Replace `@import "tailwindcss/..."` with:
```css
/* Vanilla CSS Reset — matching OpenOPC Office UI conventions */
* { box-sizing: border-box; min-width: 0; }
html, body, #root { margin: 0; padding: 0; height: 100%; }
```

All component `.tsx` files need Tailwind class names replaced with CSS module classes or vanilla `className` strings referencing custom CSS.

---

### Fix 2.3 — Fix `build_invocation()` to Return Valid Command

**Problem**: Returns `([], {...})` which crashes `asyncio.create_subprocess_exec`.

**Solution**: Since we override `start_process()` (Fix 1.1), `build_invocation()` still needs to return something the broker can log. Return a descriptive placeholder:

```python
def build_invocation(self, task, workspace_path=None, **kwargs):
    return ["shadow", "--mode", "park"], {
        "agent": self.agent_type,
        "workspace": workspace_path or "",
        "mode": "shadow_human_in_loop",
        "display_command": "shadow --mode park",
    }
```

---

### Fix 2.4 — Implement Collaboration Surface Methods

**Problem**: Missing `supports_interactive()`, `stdin_policy_for_process()`, etc.

**Solution**:

```python
def supports_interactive(self) -> bool:
    return False  # Shadow does not run interactive CLI sessions

def supports_session_resume(self) -> bool:
    return False  # Shadow tasks are stateless from the CLI perspective

def stdin_policy_for_process(self, cmd, metadata=None):
    return "devnull"  # No subprocess stdin needed

def supports_approval_prompt_handling(self, cmd, metadata=None):
    return False  # Shadow never prompts for approval
```

---

## Phase 3: Polish & Minor Alignment

---

### Fix 3.1 — Correct Kanban Column Documentation
Update docs to reflect that `AWAITING_HUMAN` maps to the `in-progress` kanban column in OpenOPC's standard mapping, not a separate review column.

### Fix 3.2 — Fix Tailwind v4 Import Syntax
(Resolved by Fix 2.2 — removing Tailwind entirely)

### Fix 3.3 — Align Documentation with Actual Execution Path
Update README and docs to accurately describe the `start_process()` override pattern instead of claiming `adapter.execute()` is invoked by the engine.

---

## Verification Plan

### Automated Tests
```bash
# 1. Run existing test suite (must stay 64/64 green)
pytest tests/ -v

# 2. Add new integration tests for:
#    - start_process() override returns valid mock process
#    - agent_isolation_home_slug() returns "shadow"
#    - get_status() returns AgentStatus.IDLE
#    - Phase validation in OpcResumeRepository
#    - build_invocation() returns non-empty command
pytest tests/ -v -k "test_start_process or test_collaboration_surface or test_phase_validation"
```

### Manual Verification
1. Install shadow-adapter into a real OpenOPC environment
2. Configure `preferred_external_agent: shadow` on a role
3. Run `opc chat --mode company` and verify the task parks without crashes
4. Submit a deliverable via the portal and verify the DAG resumes correctly
5. Compare the portal UI side-by-side with OpenOPC Office to confirm visual parity

---

## Open Questions

> [!IMPORTANT]
> **Q1: Tailwind Migration Scope** — Fix 2.2 (migrating from Tailwind to vanilla CSS) is the largest refactor. It touches every `.tsx` component file. Do you want to:
> - (A) Do a full migration to vanilla CSS matching OpenOPC's patterns?
> - (B) Keep Tailwind but align the design tokens only (faster, imperfect)?

> [!IMPORTANT]
> **Q2: Phase Resume Path** — Fix 1.5 has two options:
> - (A) Use `OPCStore` API when available (requires OpenOPC as importable dependency)
> - (B) Raw SQL with phase validation (works standalone but no hook firing)
> Which approach do you prefer? Option A is safer but creates a hard coupling.
