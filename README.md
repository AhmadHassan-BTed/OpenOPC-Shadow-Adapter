<div align="center">

<br>

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║    ░██████╗██╗  ██╗ █████╗ ██████╗  ██████╗ ██╗    ██╗                   ║
║    ██╔════╝██║  ██║██╔══██╗██╔══██╗██╔═══██╗██║    ██║                   ║
║    ╚█████╗ ███████║███████║██║  ██║██║   ██║██║ █╗ ██║                   ║
║     ╚═══██╗██╔══██║██╔══██║██║  ██║██║   ██║██║███╗██║                   ║
║    ██████╔╝██║  ██║██║  ██║██████╔╝╚██████╔╝╚███╔███╔╝                   ║
║    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝  ╚══╝╚══╝                   ║
║                                                                           ║
║                  A D A P T E R    ◆    S H A D O W    M O D E            ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

<br>

### _Your AI Company Runs Itself. You Just Approve the Big Calls._

<br>

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://pypi.org/project/openopc-shadow-adapter/)
[![PyPI](https://img.shields.io/pypi/v/openopc-shadow-adapter?style=for-the-badge&color=0c111b&label=PyPI)](https://pypi.org/project/openopc-shadow-adapter/)
[![License MIT](https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge)](LICENSE)
[![OpenOPC Compatible](https://img.shields.io/badge/OpenOPC-Compatible-6366f1?style=for-the-badge)](https://github.com/HKUDS/OpenOPC)

<br>

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)]()
[![React 19](https://img.shields.io/badge/Portal-React%2019%20+%20Tailwind-61DAFB?style=flat-square&logo=react&logoColor=black)]()
[![SQLite WAL](https://img.shields.io/badge/Storage-SQLite%20WAL-003B57?style=flat-square&logo=sqlite&logoColor=white)]()
[![JWT Auth](https://img.shields.io/badge/Auth-JWT%20+%20bcrypt-F59E0B?style=flat-square&logo=jsonwebtokens&logoColor=white)]()
[![Zero Core Mods](https://img.shields.io/badge/Core%20Modifications-Zero-ef4444?style=flat-square)]()

<br>

> **A production-ready plugin for [OpenOPC](https://github.com/HKUDS/OpenOPC) that lets real humans participate as first-class members of an AI multi-agent company — without blocking, crashing, or timing out the automation pipeline.**

<br>

[Installation](#-quick-start) · [Use Cases](#-who-is-this-for) · [How It Works](#-how-it-works) · [Architecture](#-architecture--state-machine) · [API Reference](#-api-reference)

</div>

---

<br>

## 💡 What Does This Actually Do?

> **Plain English. No jargon. 30 seconds.**

OpenOPC lets you build an AI company — a team of AI agents that plan work, delegate tasks, review each other's output, and deliver results, all without human input.

That's incredible for things like: drafting content, writing code, doing research, creating reports.

But every real business eventually needs a **real human** to step in. A lawyer to sign off on a contract. A senior engineer to approve a deployment. A compliance officer to clear a risk assessment. A creative director to greenlight a campaign.

**The problem:** OpenOPC is built for AI speed (milliseconds to minutes). The moment you try to pause it and wait for a human who operates on a *human* timescale — hours or days — **the entire pipeline crashes**.

**`openopc-shadow-adapter` fixes this.**

It adds a "Shadow Mode" to OpenOPC that:
- **Pauses** the AI pipeline at the exact moment human input is needed
- **Notifies** the human via a web portal
- **Waits** — safely, without holding any threads — for as long as needed
- **Resumes** the entire AI pipeline automatically the moment the human approves

The AI team keeps working on everything it *can* do. The human only touches what only *they* can do.

<br>

---

<br>

## 👥 Who Is This For?

<br>

### 🏢 Use Case 1 — Run Your Existing Organization on AI Autopilot

> _"We lost our senior developer. We need a legal reviewer. Our analyst is on leave."_

You don't need to pause operations. You don't need to hire immediately.

**Deploy OpenOPC + Shadow Adapter to cover that role.** The AI agents handle 90% of the work — research, drafting, formatting, testing, communicating. The Shadow Adapter routes the critical decision points to whoever *is* available on your team to review and approve.

```
  YOUR EXISTING ORGANIZATION
  ─────────────────────────────────────────────────────────────────────────────
  
   Before                              After
   ──────                              ─────
  
   Project Manager ──────────────────► Project Manager
        │                                   │
        ▼                                   ▼
   [Empty Desk]                        ┌────────────────────────┐
   Senior Developer (left)             │  AI Shadow Agent        │
                                       │  • Writes the code      │
        │                              │  • Reviews PRs          │
        ▼                              │  • Runs tests           │
   Waiting. Blocked. Delayed.          │  • Flags blockers       │
                                       └────────────────────────┘
                                                   │
                                       Human only steps in to:
                                       ✓ Approve production deploys
                                       ✓ Sign off on architecture decisions
                                       ✓ Unblock ambiguous requirements
```

**Real-world examples:**
- **Lost your legal reviewer?** → AI drafts contracts, Shadow Adapter sends them to your remaining counsel for approval-only.
- **Need QA coverage?** → AI runs test suites, flags failures, writes bug reports. Shadow Adapter routes complex edge cases to your senior engineer.
- **Scaling a content operation?** → AI researches, drafts, and formats. Shadow Adapter sends every piece to your editor for a final read before publish.

<br>

---

<br>

### 🚀 Use Case 2 — Automate Your Job. Run a Whole Company by Yourself.

> _"I want to operate like a 10-person team. There's just one of me."_

Freelancers, consultants, solo founders, and small teams can now run AI versions of entire business functions — with themselves acting only as the final decision-maker.

```
  SOLO OPERATOR RUNNING AN AI COMPANY
  ─────────────────────────────────────────────────────────────────────────────

                         ┌─────────────────────────────┐
                         │         YOU (Human)          │
                         │  Oversee. Review. Approve.   │
                         └──────────────┬──────────────┘
                                        │
                     ┌──────────────────┼──────────────────┐
                     ▼                  ▼                   ▼
           ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐
           │  AI Research  │  │  AI Development   │  │  AI Marketing    │
           │  Analyst      │  │  Team             │  │  & Content       │
           │               │  │                   │  │                  │
           │ • Market maps │  │ • Writes code     │  │ • Writes copy    │
           │ • Due diligence│ │ • Reviews PRs     │  │ • Creates briefs │
           │ • Competitive │  │ • Fixes bugs      │  │ • Drafts emails  │
           │   analysis    │  │ • Tests features  │  │ • Social posts   │
           └──────┬───────┘  └────────┬──────────┘  └────────┬─────────┘
                  │                   │                        │
                  └───────────────────┼────────────────────────┘
                                      │
                           Shadow Adapter routes
                           ONLY these to you:
                                      │
                         ┌────────────▼────────────┐
                         │  📬 Your Approval Queue  │
                         │  • Strategic decisions   │
                         │  • Client deliverables   │
                         │  • Sensitive sign-offs   │
                         │  • Creative direction    │
                         └─────────────────────────┘
```

**You set the rules. The AI does the work. You approve what matters.**

| Without Shadow Adapter | With Shadow Adapter |
|------------------------|---------------------|
| AI pipeline freezes waiting for you | AI pipeline continues on all other tasks |
| 900-second timeout crashes everything | No timeouts — ever |
| You become the bottleneck | You become the executive |
| Hire humans for every task | AI handles 90%, you handle the 10% that counts |

<br>

---

<br>

### 🏛️ Use Case 3 — Enterprise Compliance & Regulated Workflows

For teams building AI automation in **finance, legal, healthcare, or security**, regulatory requirements demand human sign-off at specific workflow stages. Shadow Adapter makes compliance a first-class architectural feature — not an afterthought.

```
  ENTERPRISE COMPLIANCE WORKFLOW
  ─────────────────────────────────────────────────────────────────────────────

  AI drafts investment memo ──► AI does due diligence ──► [CHECKPOINT]
                                                                │
                                                    Shadow Adapter intercepts
                                                                │
                                                    ┌───────────▼────────────┐
                                                    │  Human: IC Analyst     │
                                                    │  Reviews memo          │
                                                    │  ✓ Approves            │
                                                    │  ✗ Requests rework     │
                                                    └───────────┬────────────┘
                                                                │
                                          DAG automatically resumes ──►
                                          AI formats final package ──►
                                          AI sends to stakeholders
```

<br>

---

<br>

## ⚙️ How It Works

> _Now for the mechanics. This is where it gets clever._

OpenOPC manages work through a **Dependency DAG** (a directed graph of tasks). Independent tasks run in parallel. Dependent tasks wait for their parents to finish. The whole thing is orchestrated through a **Phase State Machine** — each task moves through `RUNNING → APPROVED → DONE` as agents complete their work.

**The problem** is that OpenOPC holds an execution thread while waiting for each phase to resolve. That's fine at AI speed. At human speed, the thread times out and **the entire DAG crashes**.

**Shadow Mode** solves this by turning the human review into an *event* instead of a *wait*:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                      THE SHADOW MODE LIFECYCLE                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

  ╔════════════╗    ╔══════════════════════╗    ╔═══════════════════════════╗
  ║ OpenOPC    ║    ║  Shadow Adapter       ║    ║  React Human Portal       ║
  ║ DAG Engine ║    ║  (FastAPI + SQLite)   ║    ║  (Contractor Web App)     ║
  ╚═════╤══════╝    ╚══════════════════════╝    ╚═══════════════════════════╝
        │                      │                              │
        │  1. Route task to    │                              │
        │     "shadow" role    │                              │
        ├─────────────────────►│                              │
        │                      │                              │
        │                      │  2. Save to shadow_tasks.db  │
        │                      │     (isolated SQLite store)  │
        │                      │─────────────────┐           │
        │                      │                 │           │
        │  3. Return instantly: │◄────────────────┘           │
        │     AWAITING_HUMAN   │                              │
        │◄─────────────────────│                              │
        │                      │                              │
        │  4. Release thread.  │                              │
        │     DAG continues    │                              │
        │     on ALL parallel  │                              │
        │     branches.   ─┐   │                              │
        │                  │   │  5. Contractor logs in       │
        │    ┌─────────┐   │   │◄─────────────────────────────┤
        │    │AI Agent │◄──┘   │                              │
        │    │AI Agent │       │  6. Claims & reviews task    │
        │    │AI Agent │       │◄─────────────────────────────┤
        │    └─────────┘       │                              │
        │  (keeps working)     │  7. Submits deliverable +    │
        │                      │     files via portal         │
        │                      │◄─────────────────────────────┤
        │                      │                              │
        │                      │  8. Write to OpenOPC         │
        │                      │     store.db via SQLite WAL  │
        │                      │     Phase → APPROVED         │
        │  9. Phase hooks fire │                              │
        │◄─────────────────────│                              │
        │                      │                              │
        │  10. Downstream DAG  │                              │
        │      nodes unblock.  │                              │
        │      Execution       │                              │
        │      resumes.    ────►                              │
        │                      │                              │
```

<br>

### The 4-Phase HITL Lifecycle

| Phase | What Happens | Who Acts | Duration |
|-------|-------------|----------|----------|
| **① INTERCEPT** | Task routed to a `shadow` role. `ShadowModeAdapter.execute()` fires. | System | < 50ms |
| **② PARK** | Task saved to isolated `shadow_tasks.db`. `AWAITING_HUMAN` returned to OpenOPC. Thread released. | System | < 50ms |
| **③ WORK** | Human logs into React Portal. Claims task. Reviews brief. Uploads deliverable. | Human Contractor | Minutes → Days |
| **④ RESUME** | `resume_task()` writes APPROVED to OpenOPC store via WAL. Phase hooks fire. DAG unblocks. | System | < 100ms |

<br>

---

<br>

## 🚀 Quick Start

> **Up and running in under 5 minutes.**

<br>

### Step 1 — Install

```bash
pip install openopc-shadow-adapter
```

Or with `uv` (recommended for OpenOPC projects):

```bash
uv pip install openopc-shadow-adapter
```

<br>

### Step 2 — Configure

```bash
cp .env.example .env
```

```env
# .env
SHADOW_JWT_SECRET=your-32-char-minimum-secret-key-here
SHADOW_DB_PATH=./shadow_tasks.db
SHADOW_OPC_STORE_PATH=.opc/projects/default/store.db
SHADOW_UPLOAD_DIR=./shadow_uploads
SHADOW_API_PORT=8800
```

<br>

### Step 3 — Register the Adapter

Add this to your application entry point, **before** OpenOPC initializes:

```python
from opc.layer3_agent.adapters.registry import ADAPTER_CLASSES
from shadow_adapter.adapter import ShadowModeAdapter

# One line. That's it. Zero core modifications.
ADAPTER_CLASSES["shadow"] = ShadowModeAdapter
```

<br>

### Step 4 — Assign Human Roles in Your Org Config

In your OpenOPC Company Mode organization config, mark any role as a human-backed role:

```yaml
# .opc/config/company_orgs/my_org_config.yaml

roles:
  legal_reviewer:
    title: "Human Legal Counsel"
    execution_strategy: external
    preferred_external_agent: shadow   # ← This is all it takes

  senior_engineer:
    title: "Human Senior Engineer"
    execution_strategy: external
    preferred_external_agent: shadow

  creative_director:
    title: "Human Creative Director"
    execution_strategy: external
    preferred_external_agent: shadow
```

<br>

### Step 5 — Launch

```bash
# Start the FastAPI backend + React Human Portal
shadow-serve --port 8800

# → Human portal is now live at http://localhost:8800
# → REST API is available at http://localhost:8800/api
```

<br>

### Step 6 — Run the Full Demo (Optional)

Test the complete intercept → park → submit → resume pipeline locally:

```bash
python example_usage.py
```

```
[DEMO OUTPUT]
──────────────────────────────────────────────────────
✓ ShadowModeAdapter registered in ADAPTER_CLASSES
✓ Task "Review NDA Agreement" dispatched to shadow role
✓ Task intercepted — saved to shadow_tasks.db
✓ Returned TaskStatus.AWAITING_HUMAN to OpenOPC (47ms)
✓ DAG execution thread released
✓ Simulating contractor submission...
✓ Deliverable received — writing APPROVED to store.db (WAL)
✓ Phase hooks fired — downstream DAG nodes unblocked
✓ Full HITL lifecycle completed in 312ms (minus human time)
──────────────────────────────────────────────────────
```

<br>

---

<br>

## 🌐 The React Human Portal

> The interface your human contractors actually use.

The portal is a standalone **React 19 + Tailwind CSS** single-page application, styled to match OpenOPC's native dark theme (`#0c111b`). Contractors don't need access to your OpenOPC admin panel — they only see what they need to.

```
  PORTAL LAYOUT
  ─────────────────────────────────────────────────────────────────────────────

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  🖤  SHADOW PORTAL                                    [Ahmad Hassan] ▾  │
  ├──────────────┬──────────────────────────────────────────────────────────┤
  │              │                                                          │
  │  QUEUE       │   📋 NDA Agreement Review                                │
  │  ──────      │   ─────────────────────────────────────────────────────  │
  │  ● Pending 3 │                                                          │
  │  ○ Claimed 1 │   Priority: HIGH  │  Assigned: You  │  Parked: 2h ago    │
  │  ○ Done    8 │                                                          │
  │              │   TASK BRIEF                                             │
  │  ──────      │   ┌──────────────────────────────────────────────────┐  │
  │              │   │ Review and sign off on the vendor NDA drafted    │  │
  │              │   │ by the AI legal team. Pay attention to sections  │  │
  │              │   │ 4.2 (liability cap) and 7.1 (data processing).   │  │
  │              │   │                                                  │  │
  │              │   │ Attached context: draft_nda_v2.pdf               │  │
  │              │   └──────────────────────────────────────────────────┘  │
  │              │                                                          │
  │              │   YOUR DELIVERABLE                                       │
  │              │   ┌──────────────────────────────────────────────────┐  │
  │              │   │  Drop files here or click to upload               │  │
  │              │   │  (≤5 files, ≤10MB each, ≤50MB total)             │  │
  │              │   └──────────────────────────────────────────────────┘  │
  │              │                                                          │
  │              │   ┌──────────────────────────────────────────────────┐  │
  │              │   │ Notes / Decision rationale (markdown supported)   │  │
  │              │   │                                                   │  │
  │              │   └──────────────────────────────────────────────────┘  │
  │              │                                                          │
  │              │   [  Request Rework  ]   [  ✓ Approve & Resume DAG  ]   │
  └──────────────┴──────────────────────────────────────────────────────────┘
```

**Portal Features:**

| Feature | Description |
|---------|-------------|
| **Secure Login** | JWT + bcrypt authentication. First registered user auto-becomes admin. |
| **Dashboard Queue** | Cards for Pending, Claimed, Submitted, and Resumed tasks. Filter by status or contractor. |
| **Full Task Brief** | Complete AI-generated context, markdown brief, priority indicator, and attached files from OpenOPC. |
| **Multi-File Upload** | Browser-enforced dropzone: ≤5 files, ≤10MB each, ≤50MB total. Extension allowlist enforced server-side. |
| **Rework Flow** | Contractor can reject and request rework — DAG transitions to `READY_FOR_REWORK` and re-queues the AI agent. |
| **Audit Timeline** | Immutable event log: parked → claimed → submitted → resumed. Every action timestamped and attributed. |

<br>

---

<br>

## 🏗️ Architecture & State Machine

<br>

### The Phase State Machine

`openopc-shadow-adapter` integrates natively into OpenOPC's `Phase` state machine. It does not invent new states — it drives the existing ones:

```
  OPENOPC PHASE STATE MACHINE (with Shadow Adapter)
  ─────────────────────────────────────────────────────────────────────────────

                        ┌──────────────────────────┐
                        │   Task Dispatched to      │
                        │   "shadow" Execution Role │
                        └───────────────┬──────────┘
                                        │
                                        ▼
                               ┌────────────────┐
                               │    RUNNING      │
                               │  execute()      │
                               │  called on      │
                               │  ShadowAdapter  │
                               └────────┬───────┘
                                        │ Returns AWAITING_HUMAN in < 50ms
                                        ▼
                               ┌────────────────┐
                               │ AWAITING_HUMAN  │◄── Thread released.
                               │                 │    Parallel DAG branches
                               │  (non-runnable  │    continue without waiting.
                               │   phase — DAG   │    This phase persists for
                               │   waits here    │    hours or days safely.
                               │   safely)       │
                               └────────┬───────┘
                                        │
                  ┌─────────────────────┼─────────────────────┐
                  ▼                     ▼                      ▼
        ┌──────────────┐      ┌──────────────────┐   ┌──────────────────┐
        │   APPROVED   │      │ READY_FOR_REWORK  │   │     FAILED       │
        │              │      │                   │   │                  │
        │ Contractor   │      │ Contractor pressed │   │ Resume pipeline  │
        │ submitted.   │      │ "Request Rework". │   │ error or task    │
        │ WAL write to │      │ AI agent receives  │   │ cancelled by     │
        │ store.db.    │      │ feedback and re-   │   │ admin.           │
        │ Downstream   │      │ runs the task.     │   │                  │
        │ nodes unblock│      │                   │   │                  │
        └──────┬───────┘      └────────┬──────────┘   └──────────────────┘
               │                       │
               ▼                       ▼
        ┌──────────────┐      ┌──────────────────┐
        │     DONE     │      │   AWAITING_HUMAN  │
        │              │      │   (re-queued)     │
        │ Phase hooks  │      │                   │
        │ fire. All    │      └──────────────────┘
        │ downstream   │
        │ DAG nodes    │
        │ become       │
        │ runnable.    │
        └──────────────┘
```

<br>

### System Architecture

```
  FULL SYSTEM ARCHITECTURE
  ─────────────────────────────────────────────────────────────────────────────

  ┌──────────────────────────────────────────────────────────────────────────┐
  │                        YOUR OPENOPC PROJECT                              │
  │                                                                          │
  │  ┌──────────────────────────────────────────────────────────────────┐   │
  │  │                   OpenOPC DAG Engine                              │   │
  │  │                                                                  │   │
  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │   │
  │  │  │ AI Agent │  │ AI Agent │  │ AI Agent │  │ Shadow Agent   │  │   │
  │  │  │ (native) │  │ (codex)  │  │ (claude) │  │ ← YOUR ADAPTER │  │   │
  │  │  └──────────┘  └──────────┘  └──────────┘  └───────┬────────┘  │   │
  │  │                                                      │           │   │
  │  │         ADAPTER_CLASSES["shadow"] = ShadowModeAdapter│           │   │
  │  └──────────────────────────────────────────────────────┼───────────┘   │
  │                                                         │               │
  │  ┌──────────────────────────────────────────────────────▼───────────┐   │
  │  │                    shadow_adapter package                          │   │
  │  │                                                                   │   │
  │  │  ┌─────────────────────────┐  ┌──────────────────────────────┐   │   │
  │  │  │  adapter.py             │  │  api.py (FastAPI)             │   │   │
  │  │  │  ─────────────────────  │  │  ──────────────────────────── │   │   │
  │  │  │  ShadowModeAdapter      │  │  POST /api/auth/login         │   │   │
  │  │  │  ├── execute()          │  │  POST /api/auth/register      │   │   │
  │  │  │  │   Park task + return │  │  GET  /api/tasks              │   │   │
  │  │  │  │   AWAITING_HUMAN     │  │  POST /api/tasks/{id}/claim   │   │   │
  │  │  │  └── resume_task()      │  │  POST /api/tasks/{id}/submit  │   │   │
  │  │  │      WAL write to       │  │  POST /api/tasks/{id}/unclaim │   │   │
  │  │  │      OpenOPC store.db   │  │  GET  /api/tasks/{id}/audit   │   │   │
  │  │  └──────────┬──────────────┘  └──────────────────────────────┘   │   │
  │  │             │                                                      │   │
  │  │  ┌──────────▼──────────────┐  ┌──────────────────────────────┐   │   │
  │  │  │  shadow_tasks.db        │  │  frontend/ (React 19 SPA)     │   │   │
  │  │  │  (Isolated SQLite)      │  │  ──────────────────────────── │   │   │
  │  │  │  ─────────────────────  │  │  ✓ JWT Authentication         │   │   │
  │  │  │  shadow_tasks table     │  │  ✓ Task Queue Dashboard       │   │   │
  │  │  │  audit_log table        │  │  ✓ Task Detail View           │   │   │
  │  │  │  contractors table      │  │  ✓ Multi-file Upload          │   │   │
  │  │  │                         │  │  ✓ Audit Timeline             │   │   │
  │  │  │  Persists across:       │  │  ✓ Rework Requests           │   │   │
  │  │  │  ✓ Engine restarts      │  │                              │   │   │
  │  │  │  ✓ Crashes              │  │  Styled: #0c111b dark theme   │   │   │
  │  │  │  ✓ Long idle periods    │  │  (matches OpenOPC Office UI)  │   │   │
  │  │  └─────────────────────────┘  └──────────────────────────────┘   │   │
  │  └──────────────────────────────────────────────────────────────────┘   │
  │                                                                          │
  │  .opc/projects/default/store.db  ←─ WAL-mode resume writes go here      │
  │                               (OpenOPC's live task store — read/written  │
  │                                via WAL, safe for concurrent access)      │
  └──────────────────────────────────────────────────────────────────────────┘
                                        │
                             Served at :8800
                                        │
                                        ▼
                    ┌────────────────────────────────────┐
                    │   Human Contractor (anywhere)       │
                    │   Opens http://your-server:8800     │
                    │   Logs in → Reviews → Approves      │
                    └────────────────────────────────────┘
```

<br>

---

<br>

## ✅ Feature Matrix

| Feature | Implementation | Why It Matters |
|---------|----------------|----------------|
| **Zero Core Modifications** | Extends `ExternalAgentAdapter` via `ADAPTER_CLASSES` registry | Your OpenOPC installation stays 100% vanilla — every upstream update applies cleanly |
| **Non-Blocking Park** | Returns `AWAITING_HUMAN` in `execute()` within 50ms | Bypasses OpenOPC's 900-second broker idle timeout. No threads held. No locks. |
| **Isolated State Store** | Dedicated `shadow_tasks.db` SQLite database | Parked tasks survive OpenOPC engine restarts, crashes, and redeploys |
| **WAL-Mode Resume** | Writes to OpenOPC `store.db` via SQLite WAL | Concurrent-safe: live OpenOPC engine and Shadow Adapter can both access the DB safely |
| **Phase Hook Integration** | Sets `Phase.APPROVED` → OpenOPC native hooks fire | Downstream DAG nodes unblock automatically, no custom polling required |
| **JWT Contractor Auth** | bcrypt password hashing + JWT tokens | Contractors authenticate securely without access to internal OPC admin APIs |
| **Role-Based Access** | First registered contractor gets `admin` role | Admin manages contractor accounts; contractors only see their assigned tasks |
| **Multi-File Uploads** | Enforced: ≤5 files, ≤10MB each, ≤50MB total | Server-side path sanitization + extension allowlist prevents malicious uploads |
| **Rework Loop** | `READY_FOR_REWORK` phase transition | Human can reject AI output; AI agent receives structured feedback and re-runs |
| **Immutable Audit Trail** | `audit_log` table: parked → claimed → submitted → resumed | Full compliance trail with timestamps and contractor attribution |
| **Design Coherence** | React 19 + Tailwind, `#0c111b` dark theme | Portal matches OpenOPC's Office UI — feels native to your existing toolchain |
| **Standalone CLI** | `shadow-serve --port 8800` | No integration required with OpenOPC's `opc ui` — runs as an independent process |

<br>

---

<br>

## 🌐 API Reference

The FastAPI backend exposes a complete REST API. All authenticated endpoints require a `Bearer` JWT token in the `Authorization` header.

<br>

### Authentication

| Endpoint | Method | Auth | Request Body | Description |
|----------|--------|------|--------------|-------------|
| `/api/auth/register` | `POST` | Admin JWT* | `{username, password, email}` | Register a contractor. *First user auto-becomes admin. |
| `/api/auth/login` | `POST` | None | `{username, password}` | Returns `{access_token, token_type}` |
| `/api/auth/me` | `GET` | JWT | — | Returns current contractor profile |

<br>

### Task Queue

| Endpoint | Method | Auth | Query Params | Description |
|----------|--------|------|--------------|-------------|
| `/api/tasks` | `GET` | JWT | `?status=pending&assigned_to_me=true` | List parked tasks |
| `/api/tasks/{id}` | `GET` | JWT | — | Full task brief, metadata, status, and context |
| `/api/tasks/{id}/claim` | `POST` | JWT | — | Claim a pending task. Moves to `CLAIMED`. |
| `/api/tasks/{id}/unclaim` | `POST` | JWT | — | Release a claimed task back to pending queue |
| `/api/tasks/{id}/submit` | `POST` | JWT | Multipart: `{notes, files[]}` | Submit deliverable. Triggers WAL resume. Moves to `APPROVED`. |
| `/api/tasks/{id}/audit` | `GET` | JWT | — | Immutable audit trail timeline |
| `/api/health` | `GET` | None | — | Health check + pending task count |

<br>

### Example: Submit a Deliverable

```bash
curl -X POST http://localhost:8800/api/tasks/abc-123/submit \
  -H "Authorization: Bearer eyJ..." \
  -F "notes=Approved. See annotated PDF. Section 4.2 liability cap is acceptable." \
  -F "files=@nda_annotated.pdf" \
  -F "files=@approval_memo.docx"
```

```json
{
  "task_id": "abc-123",
  "status": "APPROVED",
  "resumed_at": "2026-07-10T14:23:01Z",
  "opc_phase_updated": true,
  "dag_nodes_unblocked": 3
}
```

<br>

---

<br>

## ⚙️ Configuration Reference

All configuration is via environment variables or a `.env` file in your working directory.

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `SHADOW_JWT_SECRET` | — | **Yes** | Secret key for JWT token signing. Minimum 32 characters. |
| `SHADOW_DB_PATH` | `./shadow_tasks.db` | No | Path to the isolated Shadow task database. |
| `SHADOW_OPC_STORE_PATH` | `.opc/projects/default/store.db` | No | Path to OpenOPC's live task store. Used for WAL resume writes. |
| `SHADOW_UPLOAD_DIR` | `./shadow_uploads` | No | Storage directory for deliverable file uploads. |
| `SHADOW_MAX_FILES_PER_SUBMISSION` | `5` | No | Maximum attachments per submission. |
| `SHADOW_MAX_FILE_SIZE_MB` | `10` | No | Maximum size per individual file, in MB. |
| `SHADOW_MAX_TOTAL_UPLOAD_SIZE_MB` | `50` | No | Maximum total payload size per submission, in MB. |
| `SHADOW_API_PORT` | `8800` | No | Port for the FastAPI server and React portal. |

<br>

---

<br>

## 🔍 Why Not Just Use OpenOPC's Built-In Human Escalation?

OpenOPC does include a human escalation mechanism — when a blocker "exceeds the team's authority, the runtime escalates to the human owner." This is designed for **synchronous, same-session** escalation: the human owner is sitting at the terminal, watches the escalation in real time, and responds immediately.

It is **not** designed for:

| Scenario | OpenOPC Built-in | Shadow Adapter |
|----------|-----------------|----------------|
| Human responds in < 60 seconds | ✅ Works | ✅ Works |
| Human responds in 2 hours | ❌ Timeout crash | ✅ Works |
| Human responds in 2 days | ❌ Timeout crash | ✅ Works |
| Multiple contractors reviewing | ❌ Not supported | ✅ Claim/unclaim queue |
| File uploads from contractors | ❌ Not supported | ✅ Multi-file upload |
| Audit trail for compliance | ❌ Not supported | ✅ Immutable log |
| Human not at the terminal | ❌ Not supported | ✅ Web portal anywhere |
| Rework loop | ❌ Not supported | ✅ READY_FOR_REWORK phase |
| Zero OpenOPC modifications | ✅ Built-in | ✅ Registry-only |

<br>

---

<br>

## 📦 Project Structure

```
openopc-shadow-adapter/
│
├── shadow_adapter/
│   ├── adapter.py          # ShadowModeAdapter — the core ExternalAgentAdapter
│   ├── api.py              # FastAPI app — all REST endpoints
│   ├── models.py           # SQLAlchemy models: ShadowTask, AuditEvent, Contractor
│   ├── auth.py             # JWT + bcrypt authentication layer
│   ├── storage.py          # SQLite WAL read/write to OpenOPC store.db
│   ├── uploads.py          # File validation, sanitization, storage
│   └── frontend/           # React 19 + Tailwind CSS SPA (pre-built dist/ included)
│       ├── src/
│       │   ├── App.tsx
│       │   ├── pages/
│       │   │   ├── Login.tsx
│       │   │   ├── Dashboard.tsx
│       │   │   └── TaskDetail.tsx
│       │   └── components/
│       └── dist/           # Pre-built. shadow-serve serves this automatically.
│
├── tests/
│   ├── test_adapter.py     # Unit tests for intercept/park/resume lifecycle
│   ├── test_api.py         # Integration tests for all REST endpoints
│   └── test_storage.py     # WAL write tests with mock OpenOPC store.db
│
├── example_usage.py        # Full demo: register → park → submit → resume
├── pyproject.toml
└── .env.example
```

<br>

---

<br>

## 🤝 Contributing

All contributions welcome — bug reports, feature requests, and pull requests.

```bash
# Clone and set up
git clone https://github.com/AhmadHassan-BTed/OpenOPC-Shadow-Adapter
cd OpenOPC-Shadow-Adapter
pip install -e ".[dev]"

# Run the test suite
pytest tests/ -v --cov=shadow_adapter

# Run the frontend dev server (hot reload)
cd shadow_adapter/frontend
npm install
npm run dev     # → Vite dev server at localhost:5173
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for full contribution guidelines and code standards.

<br>

---

<br>

<div align="center">

```
╔═════════════════════════════════════════════════════════════════════════╗
║                                                                         ║
║   Built for the OpenOPC ecosystem.                                      ║
║                                                                         ║
║   Because truly autonomous AI still needs a human in the loop —         ║
║   just not one who's forced to sit and wait.                            ║
║                                                                         ║
╚═════════════════════════════════════════════════════════════════════════╝
```

<br>

[⭐ Star this repo](https://github.com/AhmadHassan-BTed/OpenOPC-Shadow-Adapter) · [📦 View on PyPI](https://pypi.org/project/openopc-shadow-adapter/) · [🐛 Report a Bug](https://github.com/AhmadHassan-BTed/OpenOPC-Shadow-Adapter/issues) · [💡 Request a Feature](https://github.com/AhmadHassan-BTed/OpenOPC-Shadow-Adapter/issues)

<br>

[![Views](https://visitor-badge.laobi.icu/badge?page_id=openopc.shadow-adapter&style=for-the-badge&color=6366f1)](https://github.com/AhmadHassan-BTed/OpenOPC-Shadow-Adapter)

</div>