# 🔴 Ruthless Compatibility Audit: `openopc-shadow-adapter` vs OpenOPC Core

> **Audit Date**: 2026-07-29  
> **OpenOPC Source**: `main` (latest pull)  
> **Shadow Adapter Source**: `main` (commit `bf6bc6e`)  
> **Verdict**: **5 Critical Failures, 4 Major Warnings, 3 Minor Misalignments**

---

## 🔴 CRITICAL FAILURES (Will Break at Runtime)

### CRITICAL-1: Execution Path Bypass — `adapter.execute()` Is Never Called by the Broker

> [!CAUTION]
> **This is the single most dangerous bug in the entire adapter. The entire architecture is wired to a method the OpenOPC engine never invokes through the standard external-agent path.**

**Evidence Chain:**
- [ExternalAgentBroker.run()](file:///home/leech/Projects/OpenOPC/opc/layer3_agent/external_broker.py#L378-L481) is the method the engine calls for **all** external agent execution
- `broker.run()` calls `adapter.build_invocation()` → then `_run_monitored_process()` → which calls `adapter.start_process()` (line 955) to spawn a **subprocess**
- `broker.run()` **never** calls `adapter.execute()`
- Our `ShadowModeAdapter.execute()` is dead code from the broker's perspective — the entire task-parking logic lives there, but the broker will never reach it
- Instead, `broker.run()` tries to launch `adapter.start_process(cmd=[], ...)` with an **empty command list** (from our `build_invocation()` returning `[]`), which will crash `asyncio.create_subprocess_exec(*[])` with `IndexError`

**When `adapter.execute()` IS called:** Only by [NativeAgent.execute()](file:///home/leech/Projects/OpenOPC/opc/engine.py#L9580) for **native** agents, not external ones. The `_run_task_once()` method (line 9033) routes external agents through `self.external_broker.run(adapter=..., task=...)`, NOT `adapter.execute()`.

**Impact:** When `preferred_external_agent: shadow` fires, the engine will:
1. Call `ShadowModeAdapter.build_invocation()` → returns `([], {...})`
2. Call `broker._run_monitored_process()` → calls `adapter.start_process(cmd=[], ...)`
3. `asyncio.create_subprocess_exec(*[])` → **IndexError crash**
4. The entire DAG node fails

---

### CRITICAL-2: Missing `agent_isolation_home_slug()` Crashes Company Mode

> [!CAUTION]
> **In Company Mode, the broker REQUIRES an `agent_isolation_home_slug()` return value. Our adapter returns `None`, which raises `RuntimeError`.**

**Evidence:** [external_broker.py L860-864](file:///home/leech/Projects/OpenOPC/opc/layer3_agent/external_broker.py#L860-L864):
```python
slug = adapter.agent_isolation_home_slug()
if not slug:
    raise RuntimeError(
        f"External adapter `{adapter.agent_type}` does not provide an opc-collab CLI isolation home."
    )
```

Our `ShadowModeAdapter` inherits the base class default `agent_isolation_home_slug()` which returns `None`. In Company Mode (which is **the primary use case** we're targeting), this line fires before `start_process()` is even reached, crashing the execution with `RuntimeError`.

---

### CRITICAL-3: `get_status()` Returns Wrong Type

> [!WARNING]
> **Our `get_status()` returns `str("idle")` instead of the required `AgentStatus` enum.**

**Evidence:**
- Base class signature: `async def get_status(self) -> AgentStatus` — returns [AgentStatus enum](file:///home/leech/Projects/OpenOPC/opc/core/models.py#L142-L146)
- Our implementation: `return getattr(TaskStatus, "IDLE", "idle")` — returns a `TaskStatus` member or a bare string
- `AgentStatus.IDLE` ≠ `TaskStatus.IDLE` — they are different enums with different semantic purposes

---

### CRITICAL-4: `ExternalAgentConfig` Not Provided — Constructor Mismatch

> [!WARNING]
> **The AdapterRegistry passes `config=agent_config` where `agent_config` is an `ExternalAgentConfig | None`. Our adapter constructor signature accepts this, but the `AgentsConfig.agents` dict does NOT contain a `"shadow"` key by default, so `agent_config = self.config.agents.get("shadow")` returns `None`.**

**Evidence:** [AgentsConfig](file:///home/leech/Projects/OpenOPC/opc/core/config.py#L364-L377) default `agents` dict only contains `claude_code`, `cursor`, `codex`, `opencode`. No `shadow`.

When [AdapterRegistry.initialize()](file:///home/leech/Projects/OpenOPC/opc/layer3_agent/adapters/registry.py#L42-L58) runs:
```python
agent_config = self.config.agents.get(agent_type)  # returns None for "shadow"
adapter = adapter_cls(config=agent_config)  # calls ShadowModeAdapter(config=None)
```

Our constructor calls `super().__init__(config)` which sets `self.config = ExternalAgentConfig(command="shadow")`. This works but means:
- `self.config.run_mode = "batch"` (default) — but Company Mode sets roles to `"interactive"`
- The broker checks `adapter.config.run_mode` to decide execution path
- Shadow can never be discovered via `self.config.agents.get("shadow")` without user configuration

---

### CRITICAL-5: Resume Repository Direct SQL Write Bypasses Phase Transition Hooks

> [!CAUTION]
> **Our `OpcResumeRepository` directly writes `UPDATE delegation_work_items SET phase = 'approved'` via raw SQL. This bypasses OpenOPC's entire phase-transition hook system, leaving `task.status`, `role_session.status`, and dispatcher wake signals permanently desynchronized.**

**Evidence:**
- [OpcResumeRepository.resume()](file:///home/leech/Projects/OpenOPC/openopc-shadow-adapter/shadow_adapter/repositories/opc_resume_repo.py#L90-L96): Raw `UPDATE delegation_work_items SET phase = ?, updated_at = ? WHERE work_item_id = ?`
- OpenOPC's phase system uses [on_phase_transition()](file:///home/leech/Projects/OpenOPC/opc/layer2_organization/phase.py#L100-L121) hooks that fire after every write via the store
- Our raw SQL bypasses `validate_transition()` ([phase.py L307-319](file:///home/leech/Projects/OpenOPC/opc/layer2_organization/phase.py#L307-L319)) — we could write an **illegal** transition (e.g., `queued → approved`) and OpenOPC would never catch it
- The `ALLOWED_TRANSITIONS` table at [phase.py L239-300](file:///home/leech/Projects/OpenOPC/opc/layer2_organization/phase.py#L239-L300) shows `AWAITING_HUMAN → {APPROVED, READY_FOR_REWORK, FAILED, CANCELLED, READY}` — only certain transitions are legal. We hard-code `approved` without checking the current phase
- Phase transition hooks that synchronize `task.status`, wake downstream DAG nodes, and update dispatcher claim state will **never fire**, leaving the engine in a permanently desynchronized state

---

## 🟡 MAJOR WARNINGS (Functional but Incorrect Behavior)

### MAJOR-1: UI Design Token Mismatch

| Token | OpenOPC Office UI | Shadow Adapter Portal |
|-------|-------------------|----------------------|
| Accent Color | `--accent: #6366f1` (Indigo) | `--opc-accent: #14b8a6` (Teal) |
| Accent Soft | `rgba(99, 102, 241, 0.15)` | `rgba(20, 184, 166, 0.15)` |
| Variable Naming | `--accent`, `--bg`, `--surface` | `--opc-accent`, `--opc-bg`, `--opc-surface` |
| Border Radius | `--radius: 12px` | Not defined (Tailwind defaults) |
| Green / Success | `--green: #34d399` | Not defined |
| Surface | `rgba(20, 27, 43, 0.7)` | `rgba(20, 27, 43, 0.75)` (close but not exact) |

**Impact:** The Contractor Portal will look visually different from the Manager Office — broken "Twin UI" promise. The accent color is **completely different** (teal vs indigo).

---

### MAJOR-2: CSS Framework Mismatch — Tailwind v4 vs Vanilla CSS

OpenOPC's office UI uses **pure vanilla CSS** with custom properties (no Tailwind). Our Shadow Adapter Portal uses **Tailwind CSS v4** with `@import "tailwindcss/..."` directives. This creates:
- Different className conventions (`className="bg-slate-900"` vs `className="app-shell"`)
- Different responsive breakpoint systems
- Tailwind's reset layer conflicts with OpenOPC's manual `* { box-sizing: border-box; }`
- Impossible to share components between the two UIs

---

### MAJOR-3: `build_invocation()` Returns Empty Command — Preflight Crash

Our `build_invocation()` returns `([], {...})`. The broker's [preflight check](file:///home/leech/Projects/OpenOPC/opc/layer3_agent/external_broker.py#L407-L413) calls `assert_external_agent_write_contract()` which validates workspace permissions. Then it passes the empty `cmd=[]` to `start_process()`. Even if `start_process` is overridden, the broker's stream monitoring (`_run_monitored_process`) expects live `stdout/stderr` streams from a real subprocess — it will hang or crash on null streams.

---

### MAJOR-4: Missing Collaboration Surface — `supports_interactive()` Returns False

All other adapters (claude_code, cursor, codex, opencode) implement:
- `supports_interactive() → True`
- `agent_isolation_home_slug() → "slug_name"`
- `agent_home_env_vars(home) → {"ENV_VAR": home}`
- `stdin_policy_for_process() → "pipe_open"`

Our adapter returns `False` for all of these, making it incompatible with Company Mode's collaboration infrastructure.

---

## 🟠 MINOR MISALIGNMENTS

### MINOR-1: Kanban Column Mapping Assumption
Our docs/UI reference a 4-column company kanban (`todo → in-progress → in-review → done`) via [COMPANY_KANBAN_COLUMNS](file:///home/leech/Projects/OpenOPC/opc/presentation/kanban.py#L42-L47). But `AWAITING_HUMAN` maps to `in-progress` column in the standard [STATUS_TO_COLUMN](file:///home/leech/Projects/OpenOPC/opc/presentation/kanban.py#L19) — NOT a separate `in-review` bucket. Our task parking as `AWAITING_HUMAN` would appear under "In Progress" on the Manager's kanban, not a human-review column.

### MINOR-2: Tailwind `@tailwind` Warning
VS Code reports `Unknown at rule @tailwind` because we use Tailwind v4's `@import` syntax incorrectly (mixing `@tailwind base` v3 directives with v4 imports). This is cosmetic but signals build configuration drift.

### MINOR-3: Documentation Claims vs Reality
README says: *"preferred_external_agent: shadow"* in company config YAML. This is a valid configuration surface, but our adapter can never actually receive execution through the broker's `_run_monitored_process()` path as currently coded.

---

## Summary Scorecard

| Area | Status | Severity |
|------|--------|----------|
| Adapter `execute()` never called by broker | 🔴 BROKEN | Critical |
| `agent_isolation_home_slug()` returns None | 🔴 BROKEN | Critical |
| `get_status()` wrong return type | 🔴 BROKEN | Critical |
| No `ExternalAgentConfig` for shadow in defaults | 🟡 DEGRADED | Critical |
| Resume SQL bypasses phase hooks | 🔴 BROKEN | Critical |
| UI accent colors mismatch | 🟡 DEGRADED | Major |
| CSS framework mismatch (Tailwind vs Vanilla) | 🟡 DEGRADED | Major |
| `build_invocation()` empty command | 🟡 DEGRADED | Major |
| Missing collaboration surface methods | 🟡 DEGRADED | Major |
| Kanban column mapping | 🟠 MINOR | Minor |
| Tailwind directive warning | 🟠 MINOR | Minor |
| Documentation claims | 🟠 MINOR | Minor |
