"""Organization Hierarchy & Context Routing Service.

Parses OpenOPC company organization topologies, resolves DAG parent-child dependencies,
and enforces role-based artifact access control policies.
"""

from __future__ import annotations

from typing import Any

from shadow_adapter.models import ShadowTask


class OrgHierarchyService:
    """Service managing organizational role graphs and DAG context resolution."""

    def __init__(self, company_config: dict[str, Any] | None = None) -> None:
        self.company_config = company_config or {}
        self._role_graph: dict[str, dict[str, Any]] = {}
        self._build_role_graph()

    def _build_role_graph(self) -> None:
        """Parse role definitions from company_config dictionary or YAML."""
        roles = self.company_config.get("roles", {})
        if isinstance(roles, list):
            for r in roles:
                role_id = r.get("id") or r.get("role_id")
                if role_id:
                    self._role_graph[role_id] = r
        elif isinstance(roles, dict):
            for role_id, r_data in roles.items():
                if isinstance(r_data, dict):
                    self._role_graph[role_id] = {"id": role_id, **r_data}
                else:
                    self._role_graph[role_id] = {"id": role_id, "title": str(r_data)}

    def get_parent_role(self, role_id: str) -> str | None:
        """Get the reporting manager role for a given worker role."""
        role_info = self._role_graph.get(role_id, {})
        return role_info.get("reports_to") or role_info.get("manager_role")

    def resolve_ancestor_task_ids(self, task: ShadowTask, all_tasks: list[ShadowTask]) -> list[ShadowTask]:
        """Resolve ancestor parent tasks in the DAG for context inheritance.

        Inspects explicit parent_task_ids, linked_work_item_id, and session history
        to find parent tasks that executed before this task.
        """
        ancestors: list[ShadowTask] = []
        opc_meta = task.opc_metadata or {}
        parent_ids = opc_meta.get("parent_task_ids", [])

        if parent_ids:
            parent_set = set(parent_ids)
            for t in all_tasks:
                if t.opc_task_id in parent_set and t.id != task.id:
                    ancestors.append(t)
            return ancestors

        # Fallback: same session_id tasks created before current task
        if task.opc_session_id:
            for t in all_tasks:
                if (
                    t.opc_session_id == task.opc_session_id
                    and t.id != task.id
                    and t.created_at
                    and task.created_at
                    and t.created_at <= task.created_at
                ):
                    ancestors.append(t)
            return ancestors

        # Fallback: match by opc_work_item_id
        if task.opc_work_item_id:
            for t in all_tasks:
                if t.opc_work_item_id == task.opc_work_item_id and t.id != task.id:
                    ancestors.append(t)
            return ancestors

        return ancestors
