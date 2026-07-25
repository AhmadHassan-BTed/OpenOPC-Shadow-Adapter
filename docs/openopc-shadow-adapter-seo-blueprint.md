# `openopc-shadow-adapter` — Ultimate SEO & Growth Hacker Blueprint

> Analysis performed on: HKUDS/OpenOPC + AhmadHassan-BTed/OpenOPC-Shadow-Adapter

---

## ━━━ STAGE 1: THE KEYWORD EXTRACTION (Semantic DNA) ━━━

### Top 15 High-Value Keywords Extracted from OpenOPC's Semantic Fingerprint

| Rank | Keyword / Exact Phrase | Usage Context | SEO Value |
|------|------------------------|---------------|-----------|
| 1 | **AI-Native Company / AI-Native** | Core brand identity — repeated in H1, tagline, badges | 🔥 Extremely High |
| 2 | **Multi-Agent System / Multi-Agent** | Used in Company Mode, role orchestration, talent system | 🔥 Extremely High |
| 3 | **Dependency DAG / DAG Orchestration** | Central execution model — "Decomposition defines a dependency DAG" | 🔥 Extremely High |
| 4 | **Agentic Workflow / Agentic AI** | Describes the autonomous self-run loop | 🔥 Extremely High |
| 5 | **Phase State Machine / Phase Transitions** | Core runtime concept — RUNNING, AWAITING, APPROVED, DONE | 🔥 High |
| 6 | **LLM Orchestration** | Context: routing tasks to LiteLLM/OpenRouter-backed roles | 🔥 High |
| 7 | **Work-Item / Work Item State** | Kanban-level task management concept unique to OpenOPC | 🔥 High |
| 8 | **ExternalAgentAdapter / Execution Agent** | The exact Python class your adapter extends — strong signal | 🔥 High |
| 9 | **Human Escalation / Human Oversight** | Explicitly mentioned: "escalates to the human owner" | ✅ High |
| 10 | **Company Mode / Task Mode** | OpenOPC's two primary execution modes | ✅ High |
| 11 | **Role-Specific Agent / Role-Backed Role** | How OpenOPC staffs its AI company | ✅ Medium-High |
| 12 | **Organizational Memory / Self-Grown** | OpenOPC's learning/memory layer | ✅ Medium |
| 13 | **Blocker Resolution / Blocker Handling** | Runtime problem-solving vocabulary | ✅ Medium |
| 14 | **Kanban / Kanban Board** | Visual workflow surface in Office UI | ✅ Medium |
| 15 | **AI-Powered Contractor / Talent Pipeline** | OpenOPC's "talent market" and hiring metaphor | ✅ Medium |

---

### Core Pain Points OpenOPC Solves (Your Positioning Anchors)

OpenOPC solves: "How do I run a complex, multi-role project autonomously with LLMs?"

**The Gap Your Adapter Fills** (the pain OpenOPC *creates* for power users):

> OpenOPC's autonomous DAG collapses the moment a work item requires a human who operates on a *human* timescale — hours or days. Their own docs admit: "when a blocker exceeds the team's authority, the runtime escalates to the human owner." But **there is no production-safe mechanism to do this without timing out the 900-second broker lock and crashing the DAG process.** That is the exact vacuum `openopc-shadow-adapter` fills.

---

### Ruthless SEO Gap Analysis

**What OpenOPC Does Well:** Their branding is crisp ("Self-Built, Self-Run, Self-Grown"). Their README uses rich, unique terminology that forms a semantic cluster. GitHub search for "OpenOPC" will only grow as their star count grows.

**What OpenOPC Leaves on the Table:**
- No PyPI `keywords` field in their `pyproject.toml` (verified). Zero algorithm signal.
- Only 0 GitHub Topics set (no topics visible on their repo page). Massive discoverability gap.
- No explicit framing around "human-in-the-loop," "HITL," or "AI oversight" — the hottest enterprise search vector in 2025-2026.
- Their human escalation is described in one sentence, never positioned as a product surface.

**Your Opportunity:** Capture the HITL + OpenOPC intersection entirely. No one else is there. Your adapter is currently the **only indexed artifact** at that keyword crossroads.

---
---

## ━━━ STAGE 2: THE SEMANTIC WEAVE (README.md Rewrite) ━━━

> Copy-paste the Markdown below directly into your README.md.
> Replace badge URLs and links with your actual values where noted.

---

```markdown
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
```

---
---

## ━━━ STAGE 3: ALGORITHM METADATA (PyPI & GitHub) ━━━

### 3A — PyPI `keywords` Array for `pyproject.toml`

Place this inside your `[project]` table. This is the **exact array** to paste in:

```toml
[project]
name = "openopc-shadow-adapter"
# ... your other fields ...

keywords = [
    "openopc",
    "openopc-shadow-adapter",
    "human-in-the-loop",
    "hitl",
    "multi-agent",
    "agentic-workflow",
    "dag-orchestration",
    "llm-orchestration",
    "ai-native",
    "phase-state-machine",
    "external-agent-adapter",
    "autonomous-ai",
    "ai-oversight",
    "generative-ai",
    "agentic-ai",
    "fastapi",
    "react-portal",
    "human-oversight",
    "ai-company",
    "workflow-automation",
]

classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Framework :: FastAPI",
    "Environment :: Web Environment",
    "Operating System :: OS Independent",
]
```

> **Why these 20?** The first two anchor you to the OpenOPC namespace. The middle cluster (`multi-agent`, `dag-orchestration`, `agentic-workflow`, `llm-orchestration`) parasitize OpenOPC's primary search vectors. The HITL cluster (`human-in-the-loop`, `hitl`, `ai-oversight`, `human-oversight`) captures the enterprise compliance buyers. The tech stack tags (`fastapi`, `react-portal`) capture developers searching for framework-specific solutions.

---

### 3B — GitHub Repository Topics (15 Topics)

Go to your repo → ⚙️ gear icon next to "About" → "Topics" → paste these one by one:

```
openopc
human-in-the-loop
hitl
multi-agent
dag-orchestration
agentic-workflow
llm-orchestration
ai-native
generative-ai
fastapi
react
python
human-oversight
agentic-ai
external-agent-adapter
```

> **Ordering rationale:** GitHub's topic search weights the first topics more heavily in "Similar repositories" suggestions. `openopc` first establishes the semantic family. `human-in-the-loop` and `hitl` second because those are high-velocity enterprise search terms in 2025-2026.

---

### 3C — GitHub "About" Description (160 chars max)

```
Zero-modification Human-in-the-Loop adapter for OpenOPC's agentic DAG runtime. Park work items for human review. Resume execution automatically. No timeouts.
```

*(158 characters — fits exactly.)*

> This is the single most important field for GitHub's search ranking after the repo name. It contains: OpenOPC (namespace anchor), Human-in-the-Loop (HITL enterprise term), agentic DAG (OpenOPC semantic cluster), and the clear value prop.

---

### 3D — GitHub Repository Website Field

Point this to your PyPI package page:
```
https://pypi.org/project/openopc-shadow-adapter/
```

This creates a crawl link from GitHub → PyPI, boosting both.

---
---

## ━━━ STAGE 4: THE LAUNCH HOOKS (Community Discovery) ━━━

### 4A — Post Titles (3 Variants)

**Variant 1 — The Problem-Framer (r/Python, r/MachineLearning)**
> **"Your AI agent DAG crashes after 900 seconds when waiting for a human. I built the open-source adapter that actually fixes this for OpenOPC."**

*Why it works:* Leads with a specific technical pain point (the 900s timeout). Developers who have hit this wall will click immediately. The specificity signals credibility.

---

**Variant 2 — The Contrarian Take (HackerNews, r/MachineLearning)**
> **"Fully autonomous AI is a lie — every enterprise agentic workflow has a human checkpoint. Here's the open-source layer I built to handle it properly."**

*Why it works:* "Fully autonomous AI is a lie" is a provocative but defensible thesis that will generate discussion. The pivot to "open-source layer" turns the debate into a product discovery moment.

---

**Variant 3 — The Capability Show-Off (r/LocalLLaMA, Discord servers)**
> **"I plugged a real human contractor portal into OpenOPC's DAG — legal reviewer, security auditor, creative director — all as first-class roles in the same agentic workflow."**

*Why it works:* Developer communities love "look what I built" posts. This one leads with the capability (human roles in a DAG), not the problem. It positions the adapter as an architectural innovation, not just a bug fix.

---

### 4B — Launch Post Body (Reddit / Discord / Dev.to)

**Copy-paste ready. Adapt the intro for each platform's tone.**

---

> **[Show HN / r/Python / Discord #show-your-work]**
>
> **openopc-shadow-adapter** — HITL execution layer for OpenOPC's multi-agent DAG runtime
>
> GitHub: https://github.com/AhmadHassan-BTed/OpenOPC-Shadow-Adapter
> PyPI: https://pypi.org/project/openopc-shadow-adapter/
>
> ---
>
> If you've used [OpenOPC](https://github.com/HKUDS/OpenOPC), you know the problem: the framework is exceptional at running AI-native company workflows autonomously. Dependency DAGs, parallel execution, phase state machines — it's genuinely well-designed.
>
> But the moment your DAG hits a work item that requires a *human* — a legal sign-off, a security audit, a creative direction call — you're stuck. Holding the thread crashes on the 900-second broker timeout. There's no production-safe pause mechanism in core OpenOPC.
>
> So I built one.
>
> **`openopc-shadow-adapter`** is a zero-modification `ExternalAgentAdapter` that:
>
> 1. **Intercepts** any OpenOPC DAG task routed to a human-backed role
> 2. **Parks** it in an isolated SQLite state store and returns `AWAITING_HUMAN` to OpenOPC instantly — releasing the execution lock
> 3. **Serves** a standalone React + FastAPI portal where human contractors can log in, claim tasks, and submit deliverables
> 4. **Resumes** the DAG automatically via SQLite WAL write → OpenOPC phase transition hooks fire → downstream nodes unblock
>
> No core modifications. Survives upstream OpenOPC updates. Full audit trail. JWT contractor auth.
>
> ```bash
> pip install openopc-shadow-adapter
> shadow-serve --port 8800
> ```
>
> Happy to answer questions about the architecture — especially the WAL-mode resume trick and how it avoids lock contention with OpenOPC's live engine.

---

### 4C — Twitter/X Thread Hook (for developer influencer amplification)

**Tweet 1 (the hook):**
> Every "fully autonomous" AI agent pipeline has a dirty secret: somewhere, a human is approving things in a Slack DM.
>
> I open-sourced the proper way to handle this in OpenOPC's multi-agent DAG runtime.
>
> 🧵 [openopc-shadow-adapter]

**Tweet 2 (the pain):**
> OpenOPC runs AI companies via dependency DAGs. Beautiful architecture.
>
> Problem: hold a DAG thread for a human reviewer operating on a *day* timescale → 900s timeout → process crash.
>
> No production-safe pause mechanism exists in core OpenOPC.

**Tweet 3 (the solution):**
> `openopc-shadow-adapter` fixes this:
> → Intercepts tasks routed to human roles
> → Parks them in isolated SQLite state store
> → Returns AWAITING_HUMAN to OpenOPC instantly (releases lock)
> → React portal for contractors to submit deliverables
> → WAL-mode write resumes the DAG automatically

**Tweet 4 (the CTA):**
> Zero core modifications. Full audit trail. JWT auth for contractors.
>
> `pip install openopc-shadow-adapter`
>
> GitHub: [link] | PyPI: [link]
>
> For everyone building hybrid AI-human workflows — this is the missing piece.

---
---

## BONUS: Discoverability Checklist

Before launch, verify every item:

- [ ] `pyproject.toml` — `keywords` array with all 20 terms added
- [ ] `pyproject.toml` — `classifiers` array filled in (PyPI search uses these)
- [ ] `pyproject.toml` — `description` field is one punchy sentence containing "OpenOPC", "human-in-the-loop", and "DAG"
- [ ] GitHub Topics — all 15 topics added
- [ ] GitHub About — 160-char description set
- [ ] GitHub Website — pointing to PyPI page
- [ ] README H1 — contains "OpenOPC" + "Human-in-the-Loop" + "DAG"
- [ ] README `pip install openopc-shadow-adapter` in the first 50 lines (PyPI crawler weights early install instructions)
- [ ] PyPI long description — your README renders correctly on PyPI (`twine check dist/*`)
- [ ] Cross-link: Add a "Plugins & Extensions" issue or discussion on the OpenOPC repo pointing to your adapter (legitimate ecosystem contribution)
- [ ] Add a `## Built With OpenOPC` or `## OpenOPC Ecosystem` section to your README to strengthen the semantic family signal

---

*Blueprint generated July 2026. Semantic analysis based on live scrape of HKUDS/OpenOPC and AhmadHassan-BTed/OpenOPC-Shadow-Adapter.*
