<div align="center">

# OpenOPC-Shadow-Adapter
### Non-Blocking Human-in-the-Loop (HITL) Infrastructure for OpenOPC

**AI Agent Employees For Your Company**

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

## Use AI Agents For

### Augmenting Vacant or Overloaded Roles
*Lost a developer? Legal reviewer on leave? Analyst at capacity?*
AI agents perform 90% of preliminary work (research, code generation, test suite execution, drafting). Shadow Adapter routes only the final approval decision to an available human manager.

### Running Your Entire Business on AI Autopilot
*One operator with the leverage of a 10-person team.*
Your AI Research Analyst, Dev Team, Marketing Lead, and Legal Counsel operate 24/7. Shadow Adapter queues strategic checkpoints for your review without stalling non-dependent work streams.

### Ensuring Enterprise Regulatory Compliance
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

## Symbiotic Integration & Quick Start

`openopc-shadow-adapter` is built to run as a **true symbiont** with OpenOPC. You can run the portal server embedded in your main Python process or as a standalone CLI sidecar.

### Step 1: Install Package
```bash
pip install openopc-shadow-adapter
```

### Step 2: Register & Launch Embedded (Zero Extra Commands)
In your main OpenOPC application entry point (e.g., `main.py`), register the adapter and launch the Human Portal server concurrently in a background thread:

```python
# main.py (Your OpenOPC application entry point)
from opc.layer3_agent.adapters.registry import ADAPTER_CLASSES
from shadow_adapter import ShadowModeAdapter, start_server_in_thread

# 1. Register "shadow" mode into OpenOPC's adapter registry
ADAPTER_CLASSES["shadow"] = ShadowModeAdapter

# 2. Launch Human Web Portal concurrently on port 8800 (single process)
start_server_in_thread(port=8800)

# 3. Launch your OpenOPC DAG pipeline as normal!
```

### Step 3: Configure Target Roles
In your OpenOPC organization config (`.opc/config/company_orgs/company_config.yaml`), set `preferred_external_agent: shadow` for human-backed roles:

```yaml
# .opc/config/company_orgs/company_config.yaml
roles:
  legal_counsel:
    title: "Human Legal Counsel"
    execution_strategy: external
    preferred_external_agent: shadow  # <-- Intercepted by Shadow Adapter

  senior_architect:
    title: "Human Senior Architect"
    execution_strategy: external
    preferred_external_agent: shadow  # <-- Intercepted by Shadow Adapter
```

### Alternative: Launch via CLI Sidecar
If you prefer running the Web Portal in a separate terminal or Docker container:

```bash
shadow-serve --port 8800
```
- **React Human Web Portal:** `http://localhost:8800`
- **REST API Base:** `http://localhost:8800/api/v1`

---

## Distributed Silicon Workforce (Bring Your Own Compute - BYOC)

The **`shadow-worker`** daemon allows remote PCs, GPU workstations, and dedicated cloud nodes to act as specialized silicon employees. Each remote node runs its assigned role on its own local model or API key without modifying the central OpenOPC engine.

### Launch Remote Compute Nodes (3-PC Distributed Example)

#### 1. Remote GPU Workstation (Role: Senior Developer -> Local Ollama)
```bash
export OLLAMA_HOST="http://localhost:11434"
shadow-worker \
  --server-url "http://192.168.1.100:8800" \
  --username "dev_node_1" \
  --password "secure_pass_1" \
  --role "senior_developer" \
  --provider "ollama" \
  --model "llama3.3:70b"
```

#### 2. Remote Enterprise Server (Role: Legal Counsel -> Enterprise Claude API)
```bash
export LOCAL_ANTHROPIC_KEY="sk-ant-api03-enterprise-key..."
shadow-worker \
  --server-url "http://192.168.1.100:8800" \
  --username "legal_node_2" \
  --password "secure_pass_2" \
  --role "legal_counsel" \
  --provider "anthropic" \
  --model "claude-3-5-sonnet-20241022"
```

#### 3. Remote Tester Machine (Role: QA Tester -> OpenAI GPT-4o)
```bash
export LOCAL_OPENAI_API_KEY="sk-proj-openai-key..."
shadow-worker \
  --server-url "http://192.168.1.100:8800" \
  --username "qa_node_3" \
  --password "secure_pass_3" \
  --role "qa_tester" \
  --provider "openai" \
  --model "gpt-4o"
```

### Programmatic Python SDK Usage

You can also embed `ShadowWorker` into custom Python pipelines on remote nodes:

```python
import asyncio
from shadow_adapter import ShadowWorker

# Custom task handler executing local agent pipeline
async def my_local_agent(task: dict) -> str:
    # Query your local GPU, private database, or custom agent model
    return f"Processed task '{task['title']}' on local node."

worker = ShadowWorker(
    server_url="http://192.168.1.100:8800",
    username="custom_node_01",
    password="password123",
    role="legal_counsel",
    custom_handler=my_local_agent,
)

asyncio.run(worker.run_forever())
```

---

## Architecture Deep-Dive

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
# Run full anti-fragility & host integration test suite (55 tests)
# Enforces Concurrency, Property-Based Fuzzing, Black Hole Exception Trapping, and OpenOPC Host Mutation Survival
pytest tests/ -v --cov=shadow_adapter --cov-report=term-missing

# Run engine simulator demo
python tests/mock_openopc_engine.py
```

---

<div align="center">

**OpenOPC-Shadow-Adapter** | Non-Blocking Human-in-the-Loop Layer for OpenOPC

[GitHub Repository](https://github.com/AhmadHassan-BTed/openopc-shadow-adapter) | [PyPI Package](https://pypi.org/project/openopc-shadow-adapter/) | [Issue Tracker](https://github.com/AhmadHassan-BTed/openopc-shadow-adapter/issues) | [Architecture Spec](docs/architecture.md)

[![Analytics](https://visitor-badge.laobi.icu/badge?page_id=openopc.shadow-adapter&style=for-the-badge&color=6366f1)](https://github.com/AhmadHassan-BTed/openopc-shadow-adapter)

</div>