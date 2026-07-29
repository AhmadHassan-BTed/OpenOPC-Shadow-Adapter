# Changelog — `openopc-shadow-adapter`

All notable changes to `openopc-shadow-adapter` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-07-29

### OpenOPC Compatibility
- **Compatible Core OpenOPC Version**: `openopc >= 0.1.0` (latest `main` architecture)
- **Supported Execution Modes**: `Company Mode` & `Task Mode`
- **Supported State Machine Phases**: `Phase.AWAITING_HUMAN`, `Phase.APPROVED`, `Phase.READY_FOR_REWORK`

### Added
- **`start_process()` Interception Mechanism**: Overrode `ExternalAgentAdapter.start_process()` so that when OpenOPC's `ExternalAgentBroker` dispatches tasks in Company or Task Mode, the adapter intercepts task execution, parks the record in `shadow_tasks.db`, and returns a completed mock subprocess without thread starvation or `IndexError` crashes.
- **Company Mode Isolation Home**: Implemented `agent_isolation_home_slug() → "shadow"`, `agent_home_env_vars()`, and `post_install_agent_home()` to satisfy `ExternalAgentBroker` isolation requirements.
- **`OPCStore` Phase Transition Hook Integration**: Replaced raw SQL resume logic in `OpcResumeRepository` with `store.update_delegation_work_item()`. This validates phase transitions (`validate_transition()`) and triggers native OpenOPC `on_phase_transition()` hooks (`task.status` sync, dispatcher wake signals).
- **Design Token Alignment**: Realigned React SPA Contractor Portal CSS tokens (`--accent: #6366f1` Indigo, `--accent-soft`, `--accent-glow`, `--radius: 12px`) to match OpenOPC Office UI (`.app-shell`) design system.
- **Non-Blocking Task Parking**: Sub-50ms intercept returning `TaskStatus.AWAITING_HUMAN` to immediately release execution threads for parallel DAG branches.
- **`shadow-serve` & `shadow-worker` CLI Tools**: Embedded FastAPI REST server (`shadow-serve`) and remote Silicon BYOC daemon (`shadow-worker`).
- **Corporate Artifacts Knowledge Graph**: Automatic file hashing (SHA-256), payload limit enforcement (5 files / 50MB cap), and upstream subagent context inheritance.

### Changed
- **`build_invocation()`**: Updated to return `["shadow", "--mode", "park"]` for OpenOPC audit trace logs instead of an empty list.
- **`get_status()`**: Aligned return type with `AgentStatus.IDLE` enum from `opc.core.models`.
- **Documentation**: Overhauled `README.md`, `docs/architecture.md`, `docs/execution_flow.md`, and `docs/implementation_guide.md` to reflect `start_process` broker interception and `OPCStore` phase transition hooks.

### Fixed
- Fixed `IndexError` crash when `ExternalAgentBroker` executed `adapter.start_process()` with empty command lists.
- Fixed `RuntimeError` crash in Company Mode caused by `agent_isolation_home_slug()` returning `None`.
- Fixed desynchronization of `task.status` and dispatcher wake signals by running phase changes through OpenOPC's transition hooks.
- Fixed UI accent color mismatch (Teal `#14b8a6` → Indigo `#6366f1`).

---

## Compatibility Matrix

| `openopc-shadow-adapter` Version | OpenOPC Core Version | Python | React / SPA | Status |
|---|---|---|---|---|
| **0.1.0** | `>= 0.1.0` (Latest `main`) | `>= 3.10` | React 19 / Vite | 🟢 Current Production Release |
