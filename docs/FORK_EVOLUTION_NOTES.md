# OpenOPC Shadow Adapter — Fork Evolution & Architectural History

> **Document Purpose:** Preserving the research, state machine analysis, and architectural design choices developed during the human-in-the-loop (HITL) exploration on OpenOPC.

---

## 1. Background & The Anti-Fragility Mandate

During initial research into adding Human-in-the-Loop (HITL) capabilities to OpenOPC, experimental modifications were explored on an internal fork. While direct core modifications demonstrated the power of parking long-running tasks, modifying core files (`engine.py`, `store.py`, state machines) created a fragile maintenance burden that would break on upstream updates to `HKUDS/OpenOPC`.

To ensure long-term stability and upstream compatibility, the design was evolved into **`openopc-shadow-adapter`** — a 100% standalone, non-invasive execution adapter operating strictly via public APIs and state machines.

---

## 2. Key Discoveries Preserved from Fork Research

### A. The `Phase.AWAITING_HUMAN` State Machine Target
- **Discovery:** OpenOPC's native state machine in [`Phase`](file:///home/leech/Projects/OpenOPC/opc/layer2_organization/phase.py) includes `Phase.AWAITING_HUMAN` as an in-review, non-runnable phase.
- **Impact:** By returning `TaskResult(status=TaskStatus.AWAITING_HUMAN)` from `ShadowModeAdapter.execute()`, OpenOPC parks the task in an in-review phase and immediately releases the execution thread. No thread blocks, and no idle timeouts tick.

### B. Isolated Database & WAL-Mode Resume Callback
- **Discovery:** OpenOPC uses SQLite in WAL (Write-Ahead Logging) mode for `store.db`.
- **Impact:** Rather than holding an in-memory handle across process boundaries, `ShadowModeAdapter.resume_task()` opens OpenOPC's `store.db` using WAL mode, updates task status to `DONE` and work item phase to `APPROVED`, and allows OpenOPC's native phase transition hooks to wake downstream DAG nodes.

### C. Isolated Human Portal SPA
- **Discovery:** Streamlit and inline UI components add extra server dependencies to core engine nodes.
- **Impact:** Building an independent React 19 + Tailwind SPA served statically by FastAPI under `/api` provides visual parity with OpenOPC's `office_ui` while remaining fully decoupled from core engine runtime processes.

---

## 3. Translation Matrix: Fork Research → Shadow Adapter

| Fork Mechanism | Shadow Adapter Equivalent | Benefit |
|---|---|---|
| Direct `engine.py` edit | `ShadowModeAdapter` extending `ExternalAgentAdapter` | Zero core file modifications. 100% Anti-Fragile. |
| In-process thread pause | Instant return of `TaskStatus.AWAITING_HUMAN` | Prevents process crashes and thread pool exhaustion. |
| Monolithic UI | React + Tailwind SPA served by FastAPI | Headless REST API + independent SPA portal. |
| Shared DB locks | Isolated `shadow_tasks.db` + SQLite WAL resume | Complete state isolation and high concurrency. |

---

## 4. Phase Verification Checklist

- [x] **Phase 1 (Architecture):** All design open questions resolved (React+Tailwind SPA, WAL resume, max 5 files / 50MB limits).
- [x] **Phase 2 (Core Backend):** `ShadowStore`, `SecurityManager`, `SecureUploadHandler`, and `ShadowModeAdapter` implemented and verified.
- [x] **Phase 3 (REST API & SPA):** FastAPI `/api` endpoints and compiled React + Tailwind frontend (`dist/`) verified.
- [x] **Phase 4 (Testing & Mocking):** 22/22 Pytest suite passing green in 2.09s, including mock engine simulator (1.23ms) and upload security guardrail limit tests.
- [x] **Phase 5 (Packaging):** PyPI wheel (`.whl`) and source tarball (`.tar.gz`) built and ready for release.
