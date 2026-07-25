<!-- BADGES -->
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://pypi.org/project/openopc-shadow-adapter/)
[![PyPI](https://img.shields.io/pypi/v/openopc-shadow-adapter?style=flat-square&color=0c111b)](https://pypi.org/project/openopc-shadow-adapter/)
[![FastAPI Backend](https://img.shields.io/badge/backend-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 19 Portal](https://img.shields.io/badge/portal-React%2019%20%2B%20Tailwind-61DAFB?style=flat-square&logo=react&logoColor=black)](https://github.com/AhmadHassan-BTed/OpenOPC-Shadow-Adapter)
[![SQLite WAL](https://img.shields.io/badge/storage-SQLite%20WAL-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://www.sqlite.org/wal.html)
[![License MIT](https://img.shields.io/badge/license-MIT-111827?style=flat-square)](LICENSE)

---

# openopc-shadow-adapter — Human-in-the-Loop Execution Layer for OpenOPC's Agentic DAG Runtime

### Safely suspend your AI-native company's dependency DAG for hours or days while a human contractor completes a work item — then resume execution automatically. Zero timeouts. Zero thread starvation. Zero core modifications.

> **A production-ready HITL symbiote for the [OpenOPC](https://github.com/HKUDS/OpenOPC) multi-agent orchestration framework.**
> Designed to slot directly into OpenOPC's phase state machine as a first-class `ExternalAgentAdapter`.

---

## Why This Exists

OpenOPC is exceptional at orchestrating AI-native company workflows at machine speed — milliseconds to minutes. The dependency DAG pauses dependent nodes, runs independent branches in parallel, and resolves blockers through structured phase transitions. It is, in a word, elegant.

But every real-world enterprise workflow eventually hits a wall that no LLM can climb alone.

OpenOPC's own architecture acknowledges this: *"when a blocker exceeds the team's authority, the runtime escalates to the human owner, invoking human judgment precisely when needed."* What it does **not** provide is a production-safe, non-blocking mechanism for that escalation to survive hours or days — the timescale on which human contractors actually operate.

Without `openopc-shadow-adapter`, your choices are grim:
- **Hold the execution thread** → 900-second broker idle timeout kills the process.
- **Write a polling hack** → Thread starvation, lock contention, dirty state.
- **Modify OpenOPC core** → Your fork breaks on every upstream update.

`openopc-shadow-adapter` introduces **Shadow Mode**: a zero-modification intercept/park/resume pipeline that plugs into OpenOPC's `ExternalAgentAdapter` interface, parks work items in an isolated state machine, and wakes the DAG the moment a human submits their deliverable.

---

## How It Works

When an OpenOPC Company Mode DAG routes a task to a role configured with `preferred_external_agent: shadow`, the adapter's three-phase lifecycle executes:

```
┌──────────────────────────────────────────────────────────────────────┐
│  OpenOPC DAG Engine                                                  │
│                                                                      │
│  Task dispatched to "shadow" role                                    │
│         │                                                            │
│         ▼                                                            │
│  ┌─────────────────────┐    ┌──────────────────────┐                 │
│  │  1. INTERCEPT        │    │  shadow_tasks.db      │                 │
│  │  ShadowModeAdapter   │───►│  (Isolated SQLite)    │                 │
│  │  .execute() called   │    └──────────────────────┘                 │
│  └────────┬────────────┘                                             │
│           │                                                          │
│           ▼                                                          │
│  Returns TaskResult(AWAITING_HUMAN) ─► Phase → AWAITING_HUMAN        │
│  Execution lock released. Parallel DAG branches continue.            │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │  [Hours or Days Later]  Human Contractor → React Portal      │     │
│  │  POST /api/tasks/{id}/submit  (deliverable + file uploads)   │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                      │
│  ShadowModeAdapter.resume_task()                                     │
│  Opens store.db via SQLite WAL → Phase → APPROVED                    │
│  OpenOPC phase hooks fire → Downstream DAG nodes resume.             │
└──────────────────────────────────────────────────────────────────────┘
```

The adapter touches **zero OpenOPC core files**. It registers itself into `ADAPTER_CLASSES["shadow"]` at startup and communicates exclusively through OpenOPC's public `Phase` state machine and `TaskResult` interface.

---

## Enterprise Use Cases

**⚖️ Compliance Gates in Regulated Generative AI Pipelines**
Route work items requiring legal sign-off, financial authorization, or security audit to a credentialed human contractor. The DAG's independent branches — drafting, research, formatting — continue running autonomously while the legal reviewer operates on their own timeline. Full audit trail included.

**🔍 Human QA for Agentic AI Content and Code Workflows**
Insert mandatory human review checkpoints at any node in your OpenOPC Company Mode workflow. A senior engineer, creative director, or compliance officer reviews and approves AI-generated output before downstream agents consume it — without halting the entire multi-agent system or engineering a custom timeout-bypass.

**🏢 Hybrid AI-Human Contractor Orchestration at Enterprise Scale**
Staff your OpenOPC AI-native company with a mix of LLM-powered agents and real human contractors — lawyers, auditors, writers, engineers — as first-class role participants in the same dependency DAG. Each role type operates at its natural speed. The adapter handles the impedance mismatch invisibly.

---

## Quick Start

```bash
pip install openopc-shadow-adapter
# or
uv pip install openopc-shadow-adapter
```

**Register the adapter** before initializing OpenOPC's engine:

```python
from opc.layer3_agent.adapters.registry import ADAPTER_CLASSES
from shadow_adapter.adapter import ShadowModeAdapter

ADAPTER_CLASSES["shadow"] = ShadowModeAdapter
```

**Assign a role** to Shadow Mode in your OpenOPC Company Mode org config:

```yaml
roles:
  legal_reviewer:
    title: "Human Legal Counsel"
    execution_strategy: external
    preferred_external_agent: shadow
```

**Launch** the FastAPI backend + React Human Portal:

```bash
shadow-serve --port 8800
# → Human portal at http://localhost:8800
```

**Run the full demo** (intercept → park → submit → DAG resume in under 1 second):

```bash
python example_usage.py
```

See the [full Quick Start guide](#quick-start) and [React Human Portal Guide](#react-human-portal-guide) for complete setup instructions.

---

## Key Features

| Feature | What It Means |
|---------|---------------|
| **Zero Core Modifications** | Extends `ExternalAgentAdapter` via the public registry. Survives all upstream OpenOPC updates. |
| **Non-Blocking Park** | Returns `AWAITING_HUMAN` in `execute()` milliseconds. Releases the broker thread immediately. Bypasses the 900s idle timeout completely. |
| **Isolated State Store** | Parked tasks persist in `shadow_tasks.db`. Survives OpenOPC engine restarts. |
| **React Human Portal** | Standalone React 19 + Tailwind SPA matching OpenOPC's `#0c111b` design language. |
| **JWT Contractor Auth** | Built-in bcrypt + JWT auth. Contractors authenticate without touching OPC admin APIs. |
| **Full Audit Trail** | Immutable lifecycle event log: parked → claimed → submitted → resumed. |
| **WAL-Mode Resume** | Writes directly to OpenOPC's `store.db` via SQLite WAL — no REST round-trip required. |

---

## Architecture & Phase State Machine

`openopc-shadow-adapter` is a native citizen of OpenOPC's `Phase` state machine:

```
[OpenOPC RUNNING] ──► adapter.execute() ──► TaskResult(AWAITING_HUMAN)
                                                      │
                                                      ▼
                                          [AWAITING_HUMAN]
                                      (hours or days — DAG continues
                                       on all parallel, non-dependent
                                       branches without waiting)
                                                      │
                            ┌─────────────────────────┤
                            ▼                         ▼
                       [APPROVED]             [READY_FOR_REWORK]
                  (contractor submits)    (contractor requests changes)
                            │
                            ▼
              OpenOPC phase hooks fire automatically.
              Downstream DAG work items become runnable.
```

---

## API Reference

The FastAPI backend exposes a clean REST API under `/api`:

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/login` | POST | None | Authenticate contractor & issue JWT |
| `/api/auth/register` | POST | Admin JWT* | Register new contractor |
| `/api/tasks` | GET | JWT | List parked tasks (filterable) |
| `/api/tasks/{id}` | GET | JWT | Get full task brief & status |
| `/api/tasks/{id}/claim` | POST | JWT | Claim a pending task |
| `/api/tasks/{id}/submit` | POST | JWT | Submit deliverable — triggers WAL resume |
| `/api/tasks/{id}/audit` | GET | JWT | Immutable audit trail |
| `/api/health` | GET | None | Health check + pending task count |

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for dev environment setup,
Vite frontend dev server instructions, and pytest guide.

```bash
pytest tests/ -v
```

---

*Built for the [OpenOPC](https://github.com/HKUDS/OpenOPC) ecosystem.*
*Solves the human-in-the-loop problem that every agentic AI pipeline eventually hits.*
