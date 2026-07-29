# OpenOPC-Shadow-Adapter — Technical Architecture Specification

This document defines the deep architectural specifications, data flows, state machine mechanics, and implementation contracts for `openopc-shadow-adapter`.

---

## 1. Core Architecture Contracts

### ExternalAgentAdapter Inheritance
- **Base Class:** `opc.layer3_agent.adapters.base.ExternalAgentAdapter`
- **Registry Injection:** `ADAPTER_CLASSES["shadow"] = ShadowModeAdapter`
- **Broker Intercept (`start_process` & `execute`):** `start_process()` and `execute()` save task state to `shadow_tasks.db` and return `TaskResult(status=AWAITING_HUMAN)` in **< 50ms**. Execution threads release immediately so parallel DAG tasks execute without timing out.
- **Company Mode Isolation Home:** Implements `agent_isolation_home_slug() → "shadow"` to satisfy OpenOPC ExternalAgentBroker isolation requirements in Company Mode.
- **Phase Hook Resume Pipeline:** `resume_task()` delegates to `OpcResumeRepository` which uses OpenOPC's `OPCStore` API (`update_delegation_work_item()`) to validate phase transitions (`validate_transition()`), set phase to `Phase.APPROVED`, and fire native phase transition hooks (`on_phase_transition()`).

### N-Tier Production Line Architecture
The codebase enforces strict tier boundaries across 3 decoupled layers:

1. **Controllers Tier (`shadow_adapter/api/routes_*.py`)**
   - Pure HTTP I/O, OpenAPI request parsing, file stream conversion to DTOs, and response formatting.
   - Zero business logic, zero SQL.

2. **Services Tier (`shadow_adapter/services/`)**
   - **`HandoffService` (The Temporal Bridge):** Orchestrates park, claim, unclaim, submit, and resume pipelines with 100% test coverage.
   - **`AuthService` (Carbon Employee Identity):** Manages login, contractor registration (with first-user admin bootstrapping), and profile management.
   - Boundary DTOs (`UploadLimits`, `JwtConfig`, `UploadFileDTO`) prevent God Object config coupling.
   - Pure Domain Exceptions (`TaskNotFoundError`, `TaskPermissionError`, `TaskNotClaimedError`, `InvalidCredentialsError`).

3. **Repository Tier (`shadow_adapter/repositories/` & `shadow_store.py`)**
   - **`OpcResumeRepository`:** OpenOPC `store.db` resume writer using `OPCStore` API with a direct WAL fallback, 100% test coverage, and Exception Black Hole protection.
   - **`ShadowStore`:** Thread-safe SQLite WAL repository for `shadow_tasks.db`.

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
    participant Service as HandoffService / AuthService
    participant OPCRepo as OpcResumeRepository
    participant Portal as React 19 Human Portal
    participant Contractor as Human Contractor

    Engine->>Adapter: execute task for shadow role
    Adapter->>Store: create task record with pending status
    Adapter-->>Engine: TaskResult with status AWAITING_HUMAN in under 50ms

    Note over Engine: Execution lock released. Independent DAG tasks execute in parallel.

    Contractor->>Portal: Login via POST /api/v1/auth/login
    Portal->>API: HTTP Login Request
    API->>Service: AuthService.login(credentials)
    Service->>Store: Validate credentials in contractors table
    Service-->>API: Return JWT access token
    API-->>Portal: Render Task Queue

    Contractor->>Portal: Claim Task via POST /api/v1/tasks/{id}/claim
    Portal->>API: HTTP Claim Request
    API->>Service: HandoffService.claim_task(task_id, contractor_id)
    Service->>Store: Atomic UPDATE status = claimed WHERE status = pending
    Store-->>Portal: Return 200 OK

    Contractor->>Portal: Submit Deliverable via POST /api/v1/tasks/{id}/submit
    Portal->>API: Multipart upload containing notes and files
    API->>API: Convert UploadFile -> UploadFileDTO
    API->>Service: HandoffService.submit_and_resume(...)
    Service->>Service: Validate file count & size limits (UploadLimits)
    Service->>Store: Update task status to submitted
    Service->>OPCRepo: OpcResumeRepository.resume(shadow_task, opc_store_path)
    OPCRepo->>Engine: Direct WAL write to store.db setting Phase to APPROVED

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

    subgraph ShadowPackage ["openopc-shadow-adapter Package (N-Tier Architecture)"]
        AdapterImpl["ShadowModeAdapter (adapter.py)\nSubclasses ExternalAgentAdapter\n• execute method -> TaskResult with AWAITING_HUMAN status\n• Signature Mutation Survival (*args, **kwargs)"]
        
        subgraph APILayer ["HTTP Controllers Tier (shadow_adapter/api)"]
            AppFactory["App Factory & Server (app.py)\nCLI Entry Point: shadow-serve"]
            AuthRoutes["Auth Router (routes_auth.py)\nDelegates to AuthService"]
            TaskRoutes["Tasks Router (routes_tasks.py)\nDelegates to HandoffService"]
            DILayer["Dependency Injection (dependencies.py)\nInjects Services, Repos, DTOs"]
        end

        subgraph ServiceLayer ["Services Tier (shadow_adapter/services)"]
            HandoffSvc["HandoffService (handoff_service.py)\nTemporal Bridge Engine\n• 100% Test Coverage"]
            AuthSvc["AuthService (auth_service.py)\nIdentity & Bootstrapping\n• 97% Test Coverage"]
            DTOs["Boundary DTOs (models.py)\nUploadLimits | JwtConfig | UploadFileDTO"]
        end

        subgraph RepoLayer ["Repositories Tier (shadow_adapter/repositories)"]
            OpcRepo["OpcResumeRepository (opc_resume_repo.py)\nOpenOPC WAL Writer • 100% Coverage"]
            StoreRepo["ShadowStore Repository (shadow_store.py)\nAtomic UPDATE WHERE checks"]
        end

        ShadowDB[("Shadow Database\n(shadow_tasks.db)\n• shadow_tasks\n• audit_log\n• contractors")]
        
        FrontendSPA["React 19 SPA (shadow_adapter/frontend/dist)\n• JWT Authentication\n• Task Queue Dashboard\n• Deliverable Upload Dropzone\n• Audit Timeline Viewer"]
    end

    ClientBrowser(["Human Contractor / Manager\n(Web Browser)"])

    ConfigYaml -->|Configures shadow preferred agent| Registry
    Registry -->|Instantiates| AdapterImpl
    EngineCore -->|Invokes execute method| AdapterImpl
    AdapterImpl -->|1. Park task| HandoffSvc
    HandoffSvc -->|Save pending task| StoreRepo
    StoreRepo --> ShadowDB

    ClientBrowser <-->|HTTP / HTTPS| FrontendSPA
    FrontendSPA <-->|REST API + JWT| AppFactory
    AppFactory --> DILayer
    DILayer --> AuthRoutes
    DILayer --> TaskRoutes
    AuthRoutes --> AuthSvc
    TaskRoutes --> HandoffSvc
    AuthSvc --> StoreRepo
    HandoffSvc --> StoreRepo
    HandoffSvc --> OpcRepo
    OpcRepo -->|Write Phase.APPROVED| OPCStore
    OPCStore -->|Native Phase Hooks| EngineCore
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
