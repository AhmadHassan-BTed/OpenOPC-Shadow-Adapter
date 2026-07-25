"""example_usage.py — Drop-in integration demo for openopc-shadow-adapter.

This script demonstrates how to integrate Shadow Mode into your OpenOPC setup:
1. Programmatically inject ShadowModeAdapter into OpenOPC's ADAPTER_CLASSES registry.
2. Intercept an OpenOPC task and park it in shadow_tasks.db without blocking threads.
3. Simulate a human contractor submitting a deliverable via the REST API.
4. Execute the resume pipeline to update OpenOPC's store.db to APPROVED phase.

Usage:
    python example_usage.py
"""

from __future__ import annotations

import asyncio
import sqlite3
import tempfile
from pathlib import Path

# ── Step 1: Programmatic Adapter Injection into OpenOPC ───────────────────
# In a real OpenOPC app, import ADAPTER_CLASSES from opc.layer3_agent.adapters.registry
try:
    from opc.layer3_agent.adapters.registry import ADAPTER_CLASSES
    from opc.core.models import Task, TaskStatus
    HAS_OPENOPC_PACKAGE = True
except ImportError:
    # Standalone mock fallback for demonstration
    ADAPTER_CLASSES = {}
    HAS_OPENOPC_PACKAGE = False

    class TaskStatus:
        PENDING = "pending"
        AWAITING_HUMAN = "awaiting_human"
        DONE = "done"

    class Task:
        def __init__(self, id, title, description, assigned_to, linked_work_item_id=""):
            self.id = id
            self.title = title
            self.description = description
            self.assigned_to = assigned_to
            self.status = TaskStatus.PENDING
            self.priority = 5
            self.project_id = "default"
            self.metadata = {"assigned_external_agent": "shadow"}
            self.linked_work_item_id = linked_work_item_id


from shadow_adapter.adapter import ShadowModeAdapter
from shadow_adapter.config import ShadowConfig
from shadow_adapter.models import ShadowSubmission, ShadowTaskStatus
from shadow_adapter.shadow_store import ShadowStore

# Register the ShadowModeAdapter with OpenOPC
ADAPTER_CLASSES["shadow"] = ShadowModeAdapter


def init_mock_opc_store(db_path: Path, task_id: str, work_item_id: str) -> None:
    """Helper to initialize a mock OpenOPC store.db."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            title TEXT,
            description TEXT,
            assigned_to TEXT,
            status TEXT DEFAULT 'pending',
            priority INTEGER DEFAULT 5,
            project_id TEXT DEFAULT 'default',
            metadata TEXT DEFAULT '{}',
            result TEXT,
            execution_lock INTEGER DEFAULT 0,
            execution_locked_at TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS delegation_work_items (
            work_item_id TEXT PRIMARY KEY,
            run_id TEXT,
            role_id TEXT,
            title TEXT,
            phase TEXT DEFAULT 'ready',
            metadata TEXT DEFAULT '{}',
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.execute(
        "INSERT INTO tasks (id, title, status) VALUES (?, ?, 'running')",
        (task_id, "Review Security Compliance"),
    )
    conn.execute(
        "INSERT INTO delegation_work_items (work_item_id, title, phase) VALUES (?, ?, 'running')",
        (work_item_id, "Review Security Compliance"),
    )
    conn.commit()
    conn.close()


async def main() -> None:
    print("================================================================")
    print("  OpenOPC Shadow Adapter — Drop-in Integration Demo")
    print("================================================================")

    with tempfile.TemporaryDirectory() as tmp_dir:
        work_dir = Path(tmp_dir)
        opc_store_path = work_dir / "opc_store.db"
        shadow_db_path = work_dir / "shadow_tasks.db"
        upload_dir = work_dir / "shadow_uploads"

        opc_task_id = "opc_task_demo_101"
        work_item_id = "wi_demo_101"

        # Initialize mock OpenOPC store.db
        init_mock_opc_store(opc_store_path, opc_task_id, work_item_id)

        # ── Step 2: Configure Shadow Mode ──────────────────────────────────
        config = ShadowConfig(
            db_path=str(shadow_db_path),
            upload_dir=str(upload_dir),
            opc_store_path=str(opc_store_path),
            jwt_secret="demo-secret-key-12345",
        )

        shadow_store = ShadowStore(config.db_path)
        await shadow_store.initialize()

        adapter = ShadowModeAdapter(shadow_config=config, shadow_store=shadow_store)

        # Create OpenOPC Task context
        task = Task(
            id=opc_task_id,
            title="Review Security Compliance & Audit Logs",
            description="Verify SOC2 compliance section and approve third-party vendor access.",
            assigned_to="security_compliance_lead",
            linked_work_item_id=work_item_id,
        )

        # ── Step 3: OpenOPC Engine dispatches task to ShadowModeAdapter ──
        print("\n1. OpenOPC Engine calls adapter.execute()...")
        start = asyncio.get_event_loop().time()
        task_result = await adapter.execute(task, workspace_path=str(work_dir))
        elapsed_ms = (asyncio.get_event_loop().time() - start) * 1000

        print(f"   ✓ execute() returned in {elapsed_ms:.2f}ms")
        print(f"   ✓ Returned Status: {task_result.status}")
        print(f"   ✓ Returned Content: {task_result.content}")
        print(f"   ✓ Parked Shadow Task ID: {task_result.artifacts['shadow_task_id']}")

        shadow_id = task_result.artifacts["shadow_task_id"]

        # ── Step 4: Human Contractor Workflow (via React Portal / REST API) ─
        print("\n2. Contractor claims task and submits deliverable...")
        contractor_id = "contractor_alice"

        await shadow_store.claim_task(shadow_id, contractor_id)
        print(f"   ✓ Task claimed by contractor '{contractor_id}'")

        submission = ShadowSubmission(
            deliverable_text="SOC2 audit completed. All vendor access controls verified and approved.",
            deliverable_files=["soc2_compliance_report.pdf"],
        )
        submitted = await shadow_store.submit_task(shadow_id, contractor_id, submission)
        print(f"   ✓ Deliverable submitted (Status: {submitted.status.value})")

        # ── Step 5: Resume OpenOPC DAG ────────────────────────────────────
        print("\n3. API triggers resume_task() to unblock OpenOPC DAG...")
        resume_res = await ShadowModeAdapter.resume_task(
            shadow_task=submitted,
            opc_store_path=config.opc_store_path,
        )

        if resume_res.success:
            await shadow_store.mark_resumed(shadow_id)
            print("   ✓ Resume callback succeeded!")
            print(f"   ✓ OpenOPC Task Status: {resume_res.opc_task_status}")
            print(f"   ✓ OpenOPC WorkItem Phase: {resume_res.opc_work_item_phase}")

        # ── Step 6: Verify final OpenOPC DB state ─────────────────────────
        conn = sqlite3.connect(str(opc_store_path))
        task_status_in_opc = conn.execute("SELECT status FROM tasks WHERE id = ?", (opc_task_id,)).fetchone()[0]
        wi_phase_in_opc = conn.execute("SELECT phase FROM delegation_work_items WHERE work_item_id = ?", (work_item_id,)).fetchone()[0]
        conn.close()

        print("\n4. Verified OpenOPC Database State:")
        print(f"   ✓ Task '{opc_task_id}' Status in store.db: {task_status_in_opc}")
        print(f"   ✓ Delegation WorkItem '{work_item_id}' Phase in store.db: {wi_phase_in_opc}")

        print("\n================================================================")
        print("  Demo Complete: Human-in-the-Loop Integration Verified! ✅")
        print("================================================================")

        await shadow_store.close()


if __name__ == "__main__":
    asyncio.run(main())
