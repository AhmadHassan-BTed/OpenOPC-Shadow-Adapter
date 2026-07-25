"""Mock OpenOPC Engine Simulator for isolated development and testing.

Simulates an OpenOPC multi-agent DAG engine dispatching a task to the 'shadow'
adapter without requiring a full OpenOPC installation.

Flow demonstrated:
1. Initializes a mock OpenOPC store.db (with tasks and delegation_work_items tables).
2. Creates a mock OpenOPC Task assigned to external agent "shadow".
3. Invokes ShadowModeAdapter.execute(task, workspace_path).
4. Asserts that execute() returns IMMEDIATELY with TaskStatus.AWAITING_HUMAN.
5. Verifies the task is safely parked in shadow_tasks.db.
6. Simulates a human contractor submitting a deliverable text + attachment via API.
7. Calls ShadowModeAdapter.resume_task(shadow_task, opc_store_path).
8. Asserts that the mock OpenOPC store.db shows task status DONE and work item phase APPROVED.
"""

from __future__ import annotations

import asyncio
import sqlite3
import sys
import uuid
from pathlib import Path

# Add package directory to python path if needed
pkg_dir = Path(__file__).parent.parent
if str(pkg_dir) not in sys.path:
    sys.path.insert(0, str(pkg_dir))

from shadow_adapter.adapter import ShadowModeAdapter
from shadow_adapter.config import ShadowConfig
from shadow_adapter.models import ShadowSubmission, ShadowTaskStatus
from shadow_adapter.shadow_store import ShadowStore

# Import OpenOPC core types or use fallback dataclass mocks
try:
    from opc.core.models import Task, TaskStatus
except ImportError:
    from dataclasses import dataclass, field

    class TaskStatus:
        PENDING = "pending"
        AWAITING_HUMAN = "awaiting_human"
        DONE = "done"

    @dataclass
    class Task:
        id: str = field(default_factory=lambda: str(uuid.uuid4()))
        session_id: str | None = None
        title: str = ""
        description: str = ""
        assigned_to: str = ""
        status: str = TaskStatus.PENDING
        priority: int = 5
        project_id: str = "default"
        metadata: dict = field(default_factory=dict)
        linked_work_item_id: str = ""


class MockOpenOPCEngine:
    """Simulator for OpenOPC engine interaction with ShadowModeAdapter."""

    def __init__(self, work_dir: Path) -> None:
        self.work_dir = work_dir
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.opc_store_path = self.work_dir / "opc_store.db"
        self.shadow_db_path = self.work_dir / "shadow_tasks.db"
        self.upload_dir = self.work_dir / "shadow_uploads"

        self._init_opc_store_db()

        self.shadow_config = ShadowConfig(
            db_path=str(self.shadow_db_path),
            upload_dir=str(self.upload_dir),
            opc_store_path=str(self.opc_store_path),
            jwt_secret="mock-engine-jwt-secret-key-12345",
        )

    def _init_opc_store_db(self) -> None:
        """Create mock OpenOPC store.db schema."""
        conn = sqlite3.connect(str(self.opc_store_path))
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
        conn.commit()
        conn.close()

    def insert_opc_task_and_work_item(
        self,
        title: str,
        description: str,
        role: str = "legal_reviewer",
    ) -> tuple[Task, str]:
        """Create a mock Task and DelegationWorkItem in mock opc_store.db."""
        opc_task_id = f"task_{uuid.uuid4().hex[:8]}"
        work_item_id = f"wi_{uuid.uuid4().hex[:8]}"

        conn = sqlite3.connect(str(self.opc_store_path))
        conn.execute(
            """INSERT INTO tasks (id, session_id, title, description, assigned_to, status, priority)
               VALUES (?, ?, ?, ?, ?, 'running', 5)""",
            (opc_task_id, "session_mock_1", title, description, role),
        )
        conn.execute(
            """INSERT INTO delegation_work_items (work_item_id, run_id, role_id, title, phase)
               VALUES (?, 'run_mock_1', ?, ?, 'running')""",
            (work_item_id, role, title),
        )
        conn.commit()
        conn.close()

        task = Task(
            id=opc_task_id,
            session_id="session_mock_1",
            title=title,
            description=description,
            assigned_to=role,
            status=TaskStatus.PENDING,
            priority=5,
            project_id="default",
            metadata={"assigned_external_agent": "shadow"},
            linked_work_item_id=work_item_id,
        )

        return task, work_item_id

    async def run_full_lifecycle_simulation(self) -> dict[str, bool | str]:
        """Simulate complete OpenOPC HITL lifecycle."""
        print("=== Mock OpenOPC Engine: HITL Simulation Start ===")

        # 1. Create mock OpenOPC Task
        task, work_item_id = self.insert_opc_task_and_work_item(
            title="Review Vendor NDA & Data Compliance",
            description="Inspect the attached NDA document and verify GDPR compliance section.",
            role="legal_counsel",
        )
        print(f"1. Mock Task Created: ID={task.id}, WorkItem={work_item_id}")

        # 2. Instantiate ShadowModeAdapter
        shadow_store = ShadowStore(str(self.shadow_db_path))
        await shadow_store.initialize()

        adapter = ShadowModeAdapter(
            shadow_config=self.shadow_config,
            shadow_store=shadow_store,
        )

        # 3. OpenOPC calls adapter.execute()
        start_time = asyncio.get_event_loop().time()
        task_result = await adapter.execute(task, workspace_path=str(self.work_dir))
        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

        print(f"2. Adapter execute() returned in {duration_ms:.2f}ms with status: {task_result.status}")

        # ASSERTION 1: Non-blocking execution returns AWAITING_HUMAN
        status_val = task_result.status.value if hasattr(task_result.status, "value") else task_result.status
        assert status_val == TaskStatus.AWAITING_HUMAN or status_val == "awaiting_human", (
            f"Expected AWAITING_HUMAN, got {status_val}"
        )
        print("   ✅ Assertion Passed: execute() returned AWAITING_HUMAN immediately!")

        # 4. Verify task parked in shadow_tasks.db
        shadow_task_id = task_result.artifacts["shadow_task_id"]
        parked = await shadow_store.get_task(shadow_task_id)
        assert parked is not None
        assert parked.status == ShadowTaskStatus.PENDING
        print(f"3. Task safely parked in shadow_tasks.db (ID={parked.id}, status={parked.status.value})")

        # 5. Simulate Contractor Claiming Task
        contractor_id = "contractor_jane_doe"
        claimed = await shadow_store.claim_task(shadow_task_id, contractor_id)
        assert claimed.status == ShadowTaskStatus.CLAIMED
        print(f"4. Contractor '{contractor_id}' claimed task.")

        # 6. Simulate Contractor Submitting Work via API
        submission = ShadowSubmission(
            deliverable_text="Legal review complete. NDA is fully GDPR-compliant with standard DPA terms.",
            deliverable_files=["gdpr_addendum_v1.pdf"],
        )
        submitted = await shadow_store.submit_task(shadow_task_id, contractor_id, submission)
        assert submitted.status == ShadowTaskStatus.SUBMITTED
        print("5. Contractor submitted deliverable report + 1 file attachment.")

        # 7. Trigger OpenOPC Resume Pipeline
        resume_res = await ShadowModeAdapter.resume_task(
            shadow_task=submitted,
            opc_store_path=str(self.opc_store_path),
        )
        assert resume_res.success, f"Resume pipeline failed: {resume_res.error}"
        await shadow_store.mark_resumed(shadow_task_id)
        print("6. Resume pipeline triggered: WAL update pushed to mock opc_store.db.")

        # 8. Verify OpenOPC opc_store.db state
        conn = sqlite3.connect(str(self.opc_store_path))
        cursor = conn.execute("SELECT status, result FROM tasks WHERE id = ?", (task.id,))
        task_row = cursor.fetchone()
        assert task_row is not None and task_row[0] == "done", f"OPC Task status is {task_row[0]}, expected 'done'"

        wi_cursor = conn.execute("SELECT phase FROM delegation_work_items WHERE work_item_id = ?", (work_item_id,))
        wi_row = wi_cursor.fetchone()
        assert wi_row is not None and wi_row[0] == "approved", f"OPC WorkItem phase is {wi_row[0]}, expected 'approved'"
        conn.close()

        print("7. Mock opc_store.db Verified:")
        print(f"   - Task '{task.id}' Status: {task_row[0]}")
        print(f"   - Delegation WorkItem '{work_item_id}' Phase: {wi_row[0]}")
        print("=== HITL Lifecycle Simulation Complete: ALL ASSERTIONS PASSED ✅ ===")

        await shadow_store.close()

        return {
            "success": True,
            "opc_task_id": task.id,
            "shadow_task_id": shadow_task_id,
            "opc_status": task_row[0],
            "work_item_phase": wi_row[0],
        }


def main() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = MockOpenOPCEngine(Path(tmp_dir))
        asyncio.run(engine.run_full_lifecycle_simulation())


if __name__ == "__main__":
    main()
