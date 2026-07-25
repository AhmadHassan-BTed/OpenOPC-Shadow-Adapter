# OpenOPC-Shadow-Adapter — Technical Architecture Specification

This document defines the deep architectural specifications, data flows, state machine mechanics, and implementation contracts for `openopc-shadow-adapter`.

---

## 1. Core Architecture Contracts

### ExternalAgentAdapter Inheritance
- **Base Class:** `opc.layer3_agent.adapters.base.ExternalAgentAdapter`
- **Registry Injection:** `ADAPTER_CLASSES["shadow"] = ShadowModeAdapter`
- **Non-Blocking Intercept:** `execute()` MUST save task state to `shadow_tasks.db` and return `TaskResult(status=AWAITING_HUMAN)` in **< 50ms**. It MUST NOT block the calling engine execution thread.
- **WAL-Mode Resume Pipeline:** `resume_task()` MUST update OpenOPC's `store.db` setting task phase to `Phase.APPROVED` using SQLite Write-Ahead Logging (WAL mode) for safe concurrent database access.

---

## 2. Phase State Machine Contract

```text
RUNNING          -> AWAITING_HUMAN    (via execute() return value in < 50ms)
AWAITING_HUMAN   -> APPROVED          (via resume_task() WAL write upon contractor submission)
AWAITING_HUMAN   -> READY_FOR_REWORK  (via contractor rework request in portal)
READY_FOR_REWORK -> AWAITING_HUMAN    (via AI agent re-execution with feedback)
APPROVED         -> DONE              (via OpenOPC native phase hooks)
```

---

## 3. Technical Lifecycle & Sequence

```mermaid
sequenceDiagram
    autonumber
    participant Engine as OpenOPC Engine (store.db)
    participant Adapter as ShadowModeAdapter
    participant Store as ShadowStore (shadow_tasks.db)
    participant API as FastAPI Router (/api/v1)
    participant Portal as React 19 Human Portal
    participant Contractor as Human Contractor

    Engine->>Adapter: execute task for shadow role
    Adapter->>Store: create task record with pending status
    Adapter-->>Engine: TaskResult with status AWAITING_HUMAN in under 50ms

    Note over Engine: Execution lock released. Independent DAG tasks execute in parallel.

    Contractor->>Portal: Login via POST /api/v1/auth/login
    Portal->>API: GET /api/v1/tasks with status pending
    API->>Store: Query pending task records
    Store-->>API: List of ShadowTask models
    API-->>Portal: Render Task Queue

    Contractor->>Portal: Claim Task via POST /api/v1/tasks/{id}/claim
    Portal->>API: Invoke claim task logic
    API->>Store: Update task status to claimed
    Store-->>Portal: Return 200 OK

    Contractor->>Portal: Submit Deliverable via POST /api/v1/tasks/{id}/submit
    Portal->>API: Multipart upload containing notes and files
    API->>API: Validate file count, extensions, and size limits
    API->>Store: Update task status to submitted
    API->>Adapter: Trigger resume task pipeline
    Adapter->>Engine: Direct WAL write to store.db setting Phase to APPROVED

    Note over Engine: Native phase hooks trigger. Downstream DAG nodes resume execution automatically.
```

---

## 4. State Machine Integration

```mermaid
stateDiagram-v2
    direction LR

    [*] --> RUNNING : Task assigned to shadow role
    RUNNING --> AWAITING_HUMAN : execute method returns AWAITING_HUMAN status
    
    state "Shadow Adapter Status Lifecycle" as ShadowState {
        [*] --> pending : Task parked in shadow_tasks.db
        pending --> claimed : Contractor claims task
        claimed --> pending : Contractor unclaims task
        claimed --> submitted : Contractor submits deliverable
        submitted --> resumed : resume_task writes Phase.APPROVED
        submitted --> rework_requested : Contractor requests AI rework
        rework_requested --> pending : AI Agent re-runs with feedback
    }

    AWAITING_HUMAN --> APPROVED : Direct SQLite WAL write
    AWAITING_HUMAN --> READY_FOR_REWORK : Contractor requests rework
    READY_FOR_REWORK --> AWAITING_HUMAN : AI Agent re-runs
    APPROVED --> DONE : Native phase hooks unblock DAG

    DONE --> [*]
    FAILED --> [*]
    CANCELLED --> [*]
```

---

## 5. System Architecture & Component Mapping

```mermaid
flowchart TD
    subgraph HostEnv ["OpenOPC Framework Environment (HKUDS/OpenOPC)"]
        direction LR
        EngineCore["OpenOPC DAG Engine\n(opc.core.engine)"]
        Registry["Adapter Registry\nADAPTER_CLASSES['shadow']"]
        ConfigYaml["Organization Config\n(company_config.yaml)"]
        OPCStore[("OpenOPC Store DB\n(store.db - SQLite WAL Mode)")]
    end

    subgraph ShadowPackage ["openopc-shadow-adapter Package"]
        AdapterImpl["ShadowModeAdapter (adapter.py)\nSubclasses ExternalAgentAdapter\n• execute method -> TaskResult with AWAITING_HUMAN status\n• resume_task method -> Direct WAL Write"]
        
        subgraph APILayer ["FastAPI REST Application (shadow_adapter/api)"]
            AppFactory["App Factory & Server (app.py)\nCLI Entry Point: shadow-serve"]
            AuthRoutes["Auth Router (routes_auth.py)\n/api/v1/auth/login\n/api/v1/auth/register"]
            TaskRoutes["Tasks Router (routes_tasks.py)\n/api/v1/tasks\n/api/v1/tasks/{id}/claim\n/api/v1/tasks/{id}/submit"]
            UploadSecurity["Security & Upload Engine (upload.py)\nFile limit: 5 files, 10MB each, 50MB total\nExtension allowlist & path sanitization"]
        end

        StoreRepo["ShadowStore Repository (shadow_store.py)\nThread-safe SQLite WAL Access"]
        ShadowDB[("Shadow Database\n(shadow_tasks.db)\n• shadow_tasks\n• audit_log\n• contractors")]
        
        FrontendSPA["React 19 SPA (shadow_adapter/frontend/dist)\n• JWT Authentication\n• Task Queue Dashboard\n• Deliverable Upload Dropzone\n• Audit Timeline Viewer"]
    end

    ClientBrowser(["Human Contractor / Manager\n(Web Browser)"])

    ConfigYaml -->|Configures shadow preferred agent| Registry
    Registry -->|Instantiates| AdapterImpl
    EngineCore -->|Invokes execute method| AdapterImpl
    AdapterImpl -->|1. Park task| StoreRepo
    StoreRepo --> ShadowDB
    AdapterImpl -->|2. Write Phase.APPROVED| OPCStore
    OPCStore -->|Native Phase Hooks| EngineCore

    ClientBrowser <-->|HTTP / HTTPS| FrontendSPA
    FrontendSPA <-->|REST API + JWT| AppFactory
    AppFactory --> AuthRoutes
    AppFactory --> TaskRoutes
    TaskRoutes --> UploadSecurity
    TaskRoutes --> StoreRepo
    StoreRepo <--> ShadowDB
```

---

## 6. Database Schema Specification (`shadow_tasks.db`)

### `shadow_tasks` Table
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `opc_task_id`: TEXT UNIQUE NOT NULL
- `opc_session_id`: TEXT
- `title`: TEXT NOT NULL
- `brief_md`: TEXT NOT NULL
- `assigned_role`: TEXT NOT NULL
- `priority`: TEXT NOT NULL DEFAULT 'medium'
- `status`: TEXT NOT NULL DEFAULT 'pending'
- `claimed_by`: INTEGER FOREIGN KEY -> contractors(id)
- `parked_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- `claimed_at`: TIMESTAMP
- `submitted_at`: TIMESTAMP
- `resumed_at`: TIMESTAMP
- `deliverable_text`: TEXT
- `deliverable_files_json`: TEXT

### `audit_log` Table
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `shadow_task_id`: INTEGER FOREIGN KEY -> shadow_tasks(id)
- `actor_id`: INTEGER FOREIGN KEY -> contractors(id)
- `action`: TEXT NOT NULL (parked, claimed, unclaimed, submitted, resumed, rework_requested)
- `details_json`: TEXT
- `created_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### `contractors` Table
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `username`: TEXT UNIQUE NOT NULL
- `email`: TEXT UNIQUE NOT NULL
- `password_hash`: TEXT NOT NULL
- `role`: TEXT NOT NULL DEFAULT 'contractor'
- `is_active`: INTEGER DEFAULT 1
- `created_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
