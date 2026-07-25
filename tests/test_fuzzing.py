"""Stage 2: Property-Based Fuzzing tests using Hypothesis.

Proves that Pydantic mutation shields and domain DTOs absorb arbitrary, malformed,
or hostile payloads without unexpected crashes or validation breaches.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    from hypothesis import HealthCheck, given, settings
    from hypothesis import strategies as st

    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False

    def given(*args, **kwargs):  # type: ignore[misc]
        def decorator(f):
            return f

        return decorator

    class HealthCheck:  # type: ignore[no-redef]
        too_slow = "too_slow"

    def settings(*args, **kwargs):  # type: ignore[misc]
        def decorator(f):
            return f

        return decorator

    st = None  # type: ignore[assignment]

from shadow_adapter.models import (
    ShadowTask,
    ShadowTaskStatus,
    TaskResumeResult,
    UploadLimits,
)
from shadow_adapter.repositories.opc_resume_repo import OpcResumeRepository
from shadow_adapter.services.handoff_service import HandoffService
from shadow_adapter.shadow_store import ShadowStore
from shadow_adapter.upload import SecureUploadHandler

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis package is not installed"),
]


# ---------------------------------------------------------------------------
# Fuzzing Strategies
# ---------------------------------------------------------------------------

hostile_strings = st.one_of(
    st.text(min_size=0, max_size=500),
    st.binary(min_size=0, max_size=500).map(lambda b: b.decode("latin1")),
    st.just("SELECT * FROM shadow_tasks; DROP TABLE shadow_tasks; --"),
    st.just("🚀🔥 Cybernetic Fluid Hybrid Workforce 🤖⚡️"),
    st.just("../../../../../etc/passwd\x00.pdf"),
    st.just("A" * 10000),
)


# ---------------------------------------------------------------------------
# Stage 2 Tests
# ---------------------------------------------------------------------------


@given(payload=hostile_strings)
@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.asyncio
async def test_fuzz_deliverable_text(tmp_path: Path, payload: str) -> None:
    """Fuzz HandoffService deliverable text with hostile string payloads."""
    db_file = tmp_path / f"fuzz_{abs(hash(payload))}.db"
    shadow_store = ShadowStore(db_file)
    await shadow_store.initialize()

    try:
        limits = UploadLimits(
            max_file_count=5,
            max_file_size_bytes=10 * 1024 * 1024,
            max_total_size_bytes=50 * 1024 * 1024,
            allowed_extensions={".txt", ".pdf"},
        )
        handler = SecureUploadHandler(limits, tmp_path / "fuzz_uploads")
        repo = OpcResumeRepository()
        handoff = HandoffService(shadow_store, repo, handler, limits)

        task = ShadowTask(opc_task_id=f"fuzz_{abs(hash(payload))}", title="Fuzz Task")
        parked = await handoff.park_task(task)
        await handoff.claim_task(parked.id, "fuzz_contractor")

        # Submit deliverable text containing hostile payload
        result = await handoff.submit_and_resume(
            task_id=parked.id,
            contractor_id="fuzz_contractor",
            deliverable_text=payload,
            files=[],
            opc_store_path="/nonexistent/fuzz.db",
        )

        # Deliverable must be persisted cleanly in ShadowStore without crashing
        fetched = await handoff.get_task(parked.id)
        assert fetched.deliverable_text == payload
        assert result.status == ShadowTaskStatus.FAILED.value
    finally:
        await shadow_store.close()


@pytest.mark.asyncio
async def test_extra_fields_mutation_survival() -> None:
    """Prove ShadowTask extra='allow' and TaskResumeResult extra='ignore' swallow 50 extra fields."""
    extra_50_fields = {f"undocumented_field_{i}": f"value_{i}" for i in range(50)}
    extra_50_fields.update(
        {
            "opc_task_id": "opc_extra_50",
            "title": "Extra Fields Task",
        }
    )

    # Instantiation with 50 undocumented fields
    task = ShadowTask.model_validate(extra_50_fields)
    assert task.opc_task_id == "opc_extra_50"
    assert task.extra_metadata is not None
    # Extra fields are preserved dynamically or ignored cleanly
    assert getattr(task, "undocumented_field_0", None) == "value_0"

    # TaskResumeResult extra='ignore'
    resume_data = {
        "success": True,
        "shadow_task_id": "st_123",
        "opc_task_id": "opc_123",
        "extra_garbage_field_99": "should_be_ignored",
    }
    result = TaskResumeResult.model_validate(resume_data)
    assert result.success is True
    assert result.shadow_task_id == "st_123"
    assert not hasattr(result, "extra_garbage_field_99")


@pytest.mark.asyncio
async def test_opc_resume_repo_result_json_serialization() -> None:
    """Verify OpcResumeRepository builds valid JSON even with hostile characters."""
    task = ShadowTask(
        opc_task_id="opc_json_test",
        title='Title with "quotes" and \n newlines \x00 nulls',
        deliverable_text='Deliverable {"key": "val"} </script><script>alert(1)</script>',
    )
    repo = OpcResumeRepository()
    json_str = repo._build_result_json(task, task.deliverable_text, {})

    # Must be valid JSON
    parsed = json.loads(json_str)
    assert parsed["status"] == "done"
    assert "alert(1)" in parsed["content"]
