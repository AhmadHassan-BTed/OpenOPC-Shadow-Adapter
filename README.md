<!-- ============================================================
  ██████╗  █████╗  ██████╗    ███████╗██████╗ ███████╗ ██████╗
  ██╔══██╗██╔══██╗██╔════╝    ██╔════╝██╔══██╗██╔════╝██╔════╝
  ██║  ██║███████║██║  ███╗   ███████╗██████╔╝█████╗  ██║
  ██║  ██║██╔══██║██║   ██║   ╚════██║██╔═══╝ ██╔══╝  ██║
  ██████╔╝██║  ██║╚██████╔╝   ███████║██║     ███████╗╚██████╗
  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝    ╚══════╝╚═╝     ╚══════╝ ╚═════╝

  AI AGENT — IMPLEMENTATION SPECIFICATION
  ═══════════════════════════════════════════════════════════════
  Base Class  : opc.layer3_agent.adapters.base.ExternalAgentAdapter
  Registry    : ADAPTER_CLASSES["shadow"] = ShadowModeAdapter
  See full architecture spec: docs/architecture.md
  ============================================================ -->

<div align="center">

# OpenOPC-Shadow-Adapter

### Non-Blocking Human-in-the-Loop (HITL) Infrastructure for OpenOPC

**Your AI company runs itself. You — or your contractors — only touch the decisions that truly require a human.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://pypi.org/project/openopc-shadow-adapter/)
[![PyPI Package](https://img.shields.io/badge/pypi-v0.1.0--ready-0c111b?style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/openopc-shadow-adapter/)
[![MIT License](https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge)](LICENSE)

[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/portal-React%2019%20%2B%20Tailwind-61DAFB?style=flat-square&logo=react&logoColor=black)](https://github.com/AhmadHassan-BTed/OpenOPC-Shadow-Adapter)
[![SQLite WAL](https://img.shields.io/badge/storage-SQLite%20WAL-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://www.sqlite.org/wal.html)
[![JWT Auth](https://img.shields.io/badge/auth-JWT%20%2B%20bcrypt-F59E0B?style=flat-square)](https://jwt.io)
[![Zero Core Modifications](https://img.shields.io/badge/core%20modifications-zero-ef4444?style=flat-square)](https://github.com/AhmadHassan-BTed/OpenOPC-Shadow-Adapter)
[![OpenOPC Ecosystem](https://img.shields.io/badge/ecosystem-OpenOPC-6366f1?style=flat-square)](https://github.com/HKUDS/OpenOPC)

<br/>

> Built for [OpenOPC](https://github.com/HKUDS/OpenOPC) | Zero Core Modifications | Production Release v0.1.0

</div>

---

> [!IMPORTANT]
> ### Problem & Solution (PAS Framework)
> 
> **Problem:** OpenOPC multi-agent DAGs run at machine speed. Waiting for a human decision (hours or days) causes OpenOPC's 900-second execution lock to expire — **crashing the entire pipeline.**
> 
> **Agitation:** Halting your entire AI workforce because one human reviewer is offline destroys operational speed and reliability.
> 
> **Solution:** `openopc-shadow-adapter` intercepts human-backed roles in **< 50ms**, parks state safely in an isolated SQLite database, and releases the execution thread instantly. Your AI company keeps running. When the human signs off in the **React Human Portal**, the adapter resumes the DAG automatically.

---

## Quick Start (3 Steps)

### 1. Install
```bash
pip install openopc-shadow-adapter
```

### 2. Register Adapter
```python
from opc.layer3_agent.adapters.registry import ADAPTER_CLASSES
from shadow_adapter.adapter import ShadowModeAdapter

# Register Shadow Mode adapter into OpenOPC engine
ADAPTER_CLASSES["shadow"] = ShadowModeAdapter
```

### 3. Launch Human Portal Server
```bash
shadow-serve --port 8800
```
- **Web Portal:** `http://localhost:8800`
- **REST API:** `http://localhost:8800/api/v1`

---

## How It Works

```mermaid
flowchart LR
    subgraph Engine ["OpenOPC Agentic DAG Engine"]
        DAG["Multi-Agent DAG Execution\n(Parallel AI Tasks)"]
    end

    subgraph Adapter ["Shadow Mode Plugin"]
        SA["ShadowModeAdapter\n(Non-blocking Intercept < 50ms)"]
    end

    subgraph Store ["Isolated Persistence"]
        DB[("SQLite WAL Store\nshadow_tasks.db")]
    end

    subgraph Portal ["Human Operations"]
        ReactApp["React 19 Human Portal\n(JWT Authenticated)"]
        HumanReviewer["Human Contractor / Reviewer"]
    end

    subgraph ResumeLayer ["DAG Unblock & Resume"]
        OPCStore[("OpenOPC Engine Store\nstore.db (WAL Mode)")]
        UnblockNode(["Downstream DAG Nodes\nResume Automatically"])
    end

    DAG -->|1. Intercept human-backed task| SA
    SA -->|2. Park task record| DB
    SA -->|3. Return AWAITING_HUMAN and release thread| DAG
    DB <-->|4. Query pending queue & Submit deliverable| ReactApp
    HumanReviewer <-->|5. Review brief & attach files| ReactApp
    ReactApp -->|6. Submit deliverable via REST API| SA
    SA -->|7. Write Phase.APPROVED to store| OPCStore
    OPCStore -->|8. Native Phase Hooks Trigger| UnblockNode
```

For complete technical sequence diagrams, state machine maps, and database schemas, see **[docs/architecture.md](docs/architecture.md)**.

---

## Key Operational Use Cases

### 1. Augmenting Vacant or Overloaded Roles
*Lost a developer? Legal reviewer on leave? Analyst at capacity?*
AI agents perform 90% of the work (research, code generation, test suite execution, drafting). Shadow Adapter routes only the final approval decision to an available human manager.

### 2. Run Your Entire Business on AI Autopilot
*One operator with the leverage of a 10-person team.*
Your AI Research Analyst, Dev Team, Marketing Lead, and Legal Counsel operate 24/7. Shadow Adapter queues strategic checkpoints for your review without stalling non-dependent work streams.

### 3. Enterprise Regulatory Compliance
In finance, healthcare, legal, and security, frameworks (SOC 2, ISO 27001, GDPR) mandate human sign-off. Shadow Adapter records immutable audit events with timestamps and contractor attribution for complete compliance verification.

---

## Feature Comparison

| Capability | Standard OpenOPC | OpenOPC + Shadow Adapter |
|:---|:---|:---|
| **Human response time > 900s** | Engine crash (timeout failure) | **Zero timeouts (unlimited duration)** |
| **System restart resilience** | State lost | **Persisted in isolated SQLite WAL DB** |
| **Multi-user access control** | Local user only | **Multi-user queue with JWT auth** |
| **File attachments** | Text only | **Up to 5 files, 50MB payload** |
| **Audit log compliance** | Basic engine log | **Immutable timeline with user attribution** |
| **Iterative rework loop** | Manual intervention | **Built-in `rework_requested` state transition** |

---

## Architecture & Technical Deep-Dive

All detailed technical specifications are decoupled from this overview:
- **[Architecture Specification & Implementation Contracts](docs/architecture.md#1-core-architecture-contracts)**
- **[Technical Lifecycle & Sequence Diagram](docs/architecture.md#3-technical-lifecycle--sequence)**
- **[State Machine Integration Diagram](docs/architecture.md#4-state-machine-integration)**
- **[Database Schemas & Tables (`shadow_tasks.db`)](docs/architecture.md#6-database-schema-specification-shadow_tasksdb)**

---

## Configuration Reference

| Variable | Default Value | Required | Description |
|:---|:---|:---|:---|
| `SHADOW_JWT_SECRET` | None | **Yes** | Secret key for signing JWT tokens (min 32 chars). |
| `SHADOW_DB_PATH` | `./shadow_tasks.db` | No | Path for the isolated Shadow SQLite database. |
| `SHADOW_OPC_STORE_PATH` | `.opc/projects/default/store.db` | No | Path to OpenOPC's `store.db` for WAL resume writes. |
| `SHADOW_UPLOAD_DIR` | `./shadow_uploads` | No | Directory for storing deliverable attachments. |
| `SHADOW_MAX_FILES_PER_SUBMISSION` | `5` | No | Max files permitted per submission. |
| `SHADOW_MAX_FILE_SIZE_MB` | `10` | No | Max allowed size per file in MB. |
| `SHADOW_MAX_TOTAL_UPLOAD_SIZE_MB` | `50` | No | Max total upload payload per submission in MB. |
| `SHADOW_API_PORT` | `8800` | No | Network port for FastAPI server and React SPA. |

---

## Development & Testing

```bash
# Clone & install in editable mode
git clone https://github.com/AhmadHassan-BTed/openopc-shadow-adapter.git
cd openopc-shadow-adapter
pip install -e ".[dev]"

# Run full test suite (32 tests)
pytest tests/ -v

# Run engine simulator demo
python tests/mock_openopc_engine.py
```

---

<div align="center">

**OpenOPC-Shadow-Adapter** | Non-Blocking Human-in-the-Loop Layer for OpenOPC

[GitHub Repository](https://github.com/AhmadHassan-BTed/openopc-shadow-adapter) | [PyPI Package](https://pypi.org/project/openopc-shadow-adapter/) | [Issue Tracker](https://github.com/AhmadHassan-BTed/openopc-shadow-adapter/issues) | [Architecture Spec](docs/architecture.md)

[![Analytics](https://visitor-badge.laobi.icu/badge?page_id=openopc.shadow-adapter&style=for-the-badge&color=6366f1)](https://github.com/AhmadHassan-BTed/openopc-shadow-adapter)

</div>