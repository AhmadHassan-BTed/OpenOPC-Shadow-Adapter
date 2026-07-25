# OpenOPC Shadow Adapter (Human-in-the-Loop)

<p align="center">
  <img alt="PyPI - Version" src="https://img.shields.io/pypi/v/openopc-shadow-adapter?color=6366f1&style=flat-square">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="License MIT" src="https://img.shields.io/badge/license-MIT-111827?style=flat-square">
  <img alt="GitHub Stars" src="https://img.shields.io/github/stars/openopc/openopc-shadow-adapter?style=flat-square">
</p>

OpenOPC executes multi-agent Directed Acyclic Graphs (DAGs) at machine speed (milliseconds to minutes), but complex real-world workflows frequently require human judgment, compliance sign-offs, or contractor deliverables that span hours or days. The **OpenOPC Shadow Adapter** intercepts DAG tasks assigned to human roles, safely parks their state in an isolated database without triggering DAG timeout crashes, serves an intuitive React + Tailwind human portal for work submission, and seamlessly unblocks the upstream OpenOPC orchestration.

---

## 🚀 Key Features

* 👤 **True Human-in-the-Loop (HITL):** Bridges sub-second LLM multi-agent DAG execution with asynchronous human workflows operating on human timescales (hours/days).
* 🛡️ **The Anti-Fragility Mandate (Zero Core Modifications):** Interacts strictly through OpenOPC's public `ExternalAgentAdapter` interface and phase state machine. Zero monkey-patching or modifications to core OpenOPC files.
* ⚛️ **Native-Coherent React UI:** Includes an independent React + Tailwind CSS Human Portal styled with OpenOPC's visual language (`#0c111b` theme, `--accent` tokens). Contractors view task context, upload deliverables, and submit work cleanly.
* 🔒 **State Isolation & Autonomy:** Maintains a standalone SQLite database (`shadow_tasks.db`) operating in WAL mode. Operates with independent JWT authentication, bcrypt password hashing, and input sanitization.
* ⚡ **Zero DAG Timeout Crashes:** Non-blocking design releases native threads immediately, preventing thread blockages, poll loops, or system execution timeouts.

---

## 🛠️ How It Works (Technical Architecture)

```
OpenOPC Engine                     Shadow Adapter                    Human Contractor Portal
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

### The Intercept -> Park -> Resume Lifecycle

1. **Intercept & Park:** When an OpenOPC DAG task reaches a role assigned to the `shadow` adapter, `ShadowModeAdapter.execute()` is invoked. The adapter maps the OpenOPC `Task` into a local `ShadowTask` record inside an isolated SQLite database (`shadow_tasks.db`).
2. **Immediate Lock Release:** `execute()` immediately returns a `TaskResult(status=TaskStatus.AWAITING_HUMAN)`. OpenOPC transitions the work item to `Phase.AWAITING_HUMAN` (an in-review state in the phase machine) and releases its thread and execution lock. No process blocks, and no idle timers tick.
3. **Human Work & Deliverable Upload:** A contractor logs into the standalone React Human Portal (or REST API), claims the task, reviews the task brief and OpenOPC metadata context, and submits their deliverable alongside attachments (up to 5 files, ≤50MB total).
4. **Resume & DAG Wake:** Upon submission, the backend REST API triggers `ShadowModeAdapter.resume_task()`. This opens OpenOPC's `store.db` using SQLite WAL mode, updates the task status to `DONE` with the human's deliverables formatted into `TaskResult`, and sets the work item phase to `APPROVED`. OpenOPC's `on_phase_transition` hooks automatically wake downstream dependent tasks and resume the DAG.

---

## ⚡ Quickstart

### 1. Installation

```bash
pip install openopc-shadow-adapter
```

### 2. Configuration & Registration

Register the adapter in your OpenOPC application before initializing the engine:

```python
from opc.layer3_agent.adapters.registry import ADAPTER_CLASSES
from shadow_adapter.adapter import ShadowModeAdapter

# Register the shadow adapter with OpenOPC
ADAPTER_CLASSES["shadow"] = ShadowModeAdapter
```

Add the `shadow` agent to your `.opc/config/agent_config.yaml`:

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

### 3. Launch the Server

Start the human portal REST API and static React UI server:

```bash
export SHADOW_JWT_SECRET="a-very-secure-random-secret"
shadow-serve --port 8800
```

Navigate to `http://localhost:8800` in your browser to access the Human Portal.

---

## 📖 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
