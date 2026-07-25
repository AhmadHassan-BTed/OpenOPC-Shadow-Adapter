<h1 align="center" style="font-size: 1.75em;">OpenOPC Shadow Adapter — Human-in-the-Loop (HITL) Extension</h1>

<p align="center">
  <b>Bridge sub-second multi-agent LLM execution with real-world human contractor workflows operating on hours & days.</b>
</p>

<p align="center">
  🛡️ <b>Zero Core Modifications</b> — 100% Anti-Fragile. Interacts via public interfaces & phase state machines.<br>
  ⏸️ <b>Non-Blocking Park</b> — Releases execution locks instantly. Zero thread blocking or DAG timeout crashes.<br>
  ⚛️ <b>Coherent React UI</b> — Standalone React + Tailwind SPA matching OpenOPC's visual language.
</p>

<p align="center">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/backend-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white">
  <img alt="React 19" src="https://img.shields.io/badge/portal-React%2019%20%2B%20Tailwind-61DAFB?style=flat-square&logo=react&logoColor=black">
  <img alt="Database" src="https://img.shields.io/badge/storage-SQLite%20WAL-003B57?style=flat-square&logo=sqlite&logoColor=white">
  <img alt="License MIT" src="https://img.shields.io/badge/license-MIT-111827?style=flat-square">
</p>

---

## News

- **Jul 2026 — Initial Release (v0.1.0):** Complete non-blocking intercept/park/resume pipeline, React + Tailwind SPA portal, JWT authentication, and automated WAL-mode state updating.

---

## Table Of Contents

- [Why OpenOPC Shadow Adapter](#why-openopc-shadow-adapter)
- [How It Works](#how-it-works)
- [Key Features Matrix](#key-features-matrix)
- [Quick Start](#quick-start)
- [React Human Portal Guide](#react-human-portal-guide)
- [Configuration Reference](#configuration-reference)
- [Architecture & State Machine](#architecture--state-machine)
- [API Reference](#api-reference)
- [Contributing](#contributing)

---

## Why OpenOPC Shadow Adapter

OpenOPC excels at orchestrating AI-native agent teams at machine speed (milliseconds to minutes). However, real-world corporate workflows frequently reach stages where automated LLM generation is insufficient — such as legal sign-offs, security audits, financial authorization, or manual code review.

Without `openopc-shadow-adapter`, attempting to pause a native thread for a human contractor to reply hours or days later causes **system thread starvation**, **execution lock timeouts**, or **fatal DAG process crashes**.

`openopc-shadow-adapter` solves this by introducing **Shadow Mode**:

<table>
  <tr>
    <td width="33%" valign="top">
      <br><strong>📥 1. Intercept</strong>
      <br><sub>OpenOPC routes a task to a human-backed role. The adapter intercepts the task context before execution begins.</sub>
    </td>
    <td width="33%" valign="top">
      <br><strong>⏸️ 2. Park</strong>
      <br><sub>The adapter saves the task to an isolated local database and immediately returns <code>TaskStatus.AWAITING_HUMAN</code> to OpenOPC, releasing the execution thread.</sub>
    </td>
    <td width="33%" valign="top">
      <br><strong>⚡ 3. Resume</strong>
      <br><sub>A human logs into the React Human Portal, submits the deliverable, and the adapter updates OpenOPC's store to <code>APPROVED</code> phase, unblocking the DAG.</sub>
    </td>
  </tr>
</table>

---

## How It Works

The Shadow Adapter integrates seamlessly into OpenOPC's 7-layer architecture without requiring a single line of modification to core OpenOPC files.

```
OpenOPC Engine                     Shadow Adapter                    React Human Portal
     │                                    │                                    │
     │ 1. Dispatch Task to "shadow"      │                                    │
     ├───────────────────────────────────►│                                    │
     │                                    │ 2. Intercept & Park in             │
     │                                    │    shadow_tasks.db                 │
     │ 3. Return TaskResult(AWAITING_HUMAN)│                                    │
     │◄───────────────────────────────────┤                                    │
     │                                    │                                    │
     │ [Phase -> AWAITING_HUMAN]          │                                    │
     │ (Thread released, DAG waits)       │ 4. Contractor logs in, claims task │
     │                                    │◄───────────────────────────────────┤
     │                                    │                                    │
     │                                    │ 5. POST /api/tasks/{id}/submit     │
     │                                    │◄───────────────────────────────────┤
     │                                    │    (Deliverable text + files)      │
     │ 6. Push TaskResult(DONE)           │                                    │
     │    & Update Phase -> APPROVED      │                                    │
     │◄───────────────────────────────────┤                                    │
     │                                    │                                    │
     │ 7. Phase hooks fire                │                                    │
     └─► [DAG Resumes Execution]          │                                    │
```

### The 4-Step HITL Lifecycle

1. **Intercept:** When an OpenOPC DAG task reaches a role assigned to the `shadow` execution agent, `ShadowModeAdapter.execute()` is invoked with the active `Task` context.
2. **Park:** The adapter converts the `Task` to a `ShadowTask` in its isolated SQLite database (`shadow_tasks.db`) and immediately returns `TaskResult(status=TaskStatus.AWAITING_HUMAN)`. OpenOPC sets the work item to `Phase.AWAITING_HUMAN` and releases its execution lock.
3. **Work:** A human contractor logs into the standalone React Human Portal (or calls the REST API), views the full task brief and context, claims the task, and uploads deliverables (up to 5 files, ≤50MB total).
4. **Resume:** Upon submission, the API server triggers `ShadowModeAdapter.resume_task()`. It opens OpenOPC's `store.db` via SQLite WAL mode, updates the task to `DONE`, formats the deliverable into `TaskResult`, and sets the phase to `APPROVED`. OpenOPC's native phase transition hooks automatically wake dependent tasks in the DAG.

---

## Key Features Matrix

| Feature | Built-in Behavior | Benefit |
|---|---|---|
| **Zero Core Modifications** | Extends `ExternalAgentAdapter` and registers in `ADAPTER_CLASSES` | Survives all upstream OpenOPC framework updates. |
| **State Isolation** | Isolated SQLite `shadow_tasks.db` | Parked tasks persist safely even if OpenOPC engine restarts. |
| **Timeout Avoidance** | Returns `AWAITING_HUMAN` immediately in `execute()` | Bypasses OpenOPC's 900s broker idle timeout completely. |
| **Standalone Auth** | Built-in JWT + bcrypt auth system | Contractors log in securely without access to internal OPC admin APIs. |
| **Upload Security** | Strict path sanitization, extension allowlist, file limits | Enforces ≤5 files, ≤50MB total, ≤10MB per file limits. |
| **Design Coherence** | Styled with OpenOPC `#0c111b` tokens | High technical parity with OpenOPC's native `office_ui`. |

---

## Quick Start

<details open>
<summary><strong>1. Installation</strong></summary>

Install `openopc-shadow-adapter` in your OpenOPC Python environment:

```bash
pip install openopc-shadow-adapter
```

Or via `uv`:

```bash
uv pip install openopc-shadow-adapter
```
</details>

<details open>
<summary><strong>2. Register the Adapter</strong></summary>

Add the programmatic registration to your application entry point before initializing OpenOPC's engine:

```python
from opc.layer3_agent.adapters.registry import ADAPTER_CLASSES
from shadow_adapter.adapter import ShadowModeAdapter

# Register the shadow adapter
ADAPTER_CLASSES["shadow"] = ShadowModeAdapter
```

Add `shadow` to your `.opc/config/agent_config.yaml`:

```yaml
external_agents:
  preferred_order:
    - claude_code
    - codex
    - cursor
    - opencode
    - shadow

  shadow:
    enabled: true
    command: ""
    run_mode: batch
    idle_timeout_seconds: 0
    approval_mode: full-auto
```
</details>

<details open>
<summary><strong>3. Start the Server</strong></summary>

Launch the FastAPI backend and static React Human Portal:

```bash
export SHADOW_JWT_SECRET="a-very-secure-random-secret-key"
shadow-serve --port 8800
```

Open `http://localhost:8800` to access the Human Portal interface.
</details>

<details>
<summary><strong>4. Assigning Tasks to Human Roles</strong></summary>

In OpenOPC Company Mode, configure a role to use the shadow adapter:

```yaml
roles:
  legal_reviewer:
    title: "Human Legal Counsel"
    execution_strategy: external
    preferred_external_agent: shadow
```

Or in Task Mode via CLI:

```bash
opc chat -p demo --mode task --agent shadow "Review and sign off on NDA agreement"
```
</details>

---

## React Human Portal Guide

The Human Portal is a single-page application built with **React 19 + Tailwind CSS** styled to match OpenOPC's native aesthetic (`#0c111b` dark theme).

<details>
<summary><strong>Portal Features & Walkthrough</strong></summary>

- **Login / Register:** JWT-based authentication. The first registered contractor automatically receives `admin` privileges.
- **Dashboard Queue:** Overview cards for `Pending`, `Claimed`, `Submitted`, and `Resumed` tasks. Filter queue by status or assigned contractor.
- **Task Detail View:** Markdown task brief, OpenOPC metadata inspector, priority indicator, and claim controls.
- **Multi-File Upload Form:** Browser-enforced file dropzone validating ≤5 files, ≤10MB per file, and ≤50MB total payload before submission.
- **Audit Log Timeline:** Immutable history of every lifecycle event (parked, claimed, submitted, resumed).

```bash
# To build the frontend SPA from source:
cd shadow_adapter/frontend
npm install
npm run build
```

The compiled SPA bundle (`dist/`) is served automatically by `shadow-serve`.
</details>

---

## Configuration Reference

Set configuration options via environment variables or a local `.env` file:

| Environment Variable | Default | Purpose |
|---|---|---|
| `SHADOW_JWT_SECRET` | *(required in prod)* | Secret key used to sign contractor JWT tokens. |
| `SHADOW_DB_PATH` | `./shadow_tasks.db` | Path to the isolated SQLite database. |
| `SHADOW_OPC_STORE_PATH` | `.opc/projects/default/store.db` | Path to OpenOPC's `store.db` for WAL resume callbacks. |
| `SHADOW_UPLOAD_DIR` | `./shadow_uploads` | Storage directory for deliverable file uploads. |
| `SHADOW_MAX_FILES_PER_SUBMISSION` | `5` | Maximum number of attachments per submission. |
| `SHADOW_MAX_FILE_SIZE_MB` | `10` | Maximum size in MB per individual file. |
| `SHADOW_MAX_TOTAL_UPLOAD_SIZE_MB` | `50` | Maximum total payload size in MB per submission. |
| `SHADOW_API_PORT` | `8800` | Port for the FastAPI server. |

---

## Architecture & State Machine

`openopc-shadow-adapter` hooks directly into OpenOPC's native [`Phase`](file:///home/leech/Projects/OpenOPC/opc/layer2_organization/phase.py) state machine:

```
  RUNNING → adapter.execute() → TaskResult(AWAITING_HUMAN)
      │
      ▼
  AWAITING_HUMAN  (hours/days pass — DAG continues on parallel branches)
      │
      ├──→ APPROVED          (human contractor submits deliverable)
      ├──→ READY_FOR_REWORK  (human contractor requests rework)
      ├──→ FAILED            (resume pipeline error)
      └──→ CANCELLED         (task cancelled)
```

Because `Phase.AWAITING_HUMAN` is a non-runnable in-review phase in OpenOPC, the engine releases its execution lock and allows parallel DAG nodes to continue without waiting for the human to finish.

---

## API Reference

The FastAPI backend exposes the following REST endpoints under `/api`:

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/auth/login` | POST | None | Authenticate contractor & issue JWT token |
| `/api/auth/register` | POST | Admin JWT* | Register new contractor (*first user becomes admin) |
| `/api/auth/me` | GET | JWT | Return current contractor profile |
| `/api/tasks` | GET | JWT | List parked tasks (filterable by `status`, `assigned_to_me`) |
| `/api/tasks/{id}` | GET | JWT | Get task brief, metadata, and current status |
| `/api/tasks/{id}/claim` | POST | JWT | Claim a pending task for the active contractor |
| `/api/tasks/{id}/unclaim` | POST | JWT | Release a claimed task back to pending queue |
| `/api/tasks/{id}/submit` | POST | JWT | Submit deliverable (text + files). Triggers OpenOPC WAL resume. |
| `/api/tasks/{id}/audit` | GET | JWT | Get immutable audit trail timeline |
| `/api/health` | GET | None | Health check & pending task count |

---

## Contributing

We welcome community contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for full development environment setup, running the Vite frontend dev server, and Pytest instructions.

```bash
# Run backend test suite
pytest tests/ -v
```

---

<p align="center">
  <em> ❤️ Built for the OpenOPC Ecosystem</em><br><br>
  <img src="https://visitor-badge.laobi.icu/badge?page_id=openopc.shadow-adapter&style=for-the-badge&color=6366f1" alt="Views">
</p>
