"""Custom domain exceptions for OpenOPC Shadow Adapter.

Maintains strict N-Tier separation of concerns:
- Infrastructure / Repository layers raise DomainExceptions (which subclass ValueError).
- API Controller layer catches DomainExceptions and translates them to HTTP 400/403/404 responses.
"""

from __future__ import annotations


class ShadowDomainError(ValueError):
    """Base domain exception for Shadow Adapter business logic failures."""


class TaskNotFoundError(ShadowDomainError):
    """Raised when a requested shadow task does not exist."""

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        super().__init__(f"Shadow task '{task_id}' not found.")


class TaskAlreadyClaimedError(ShadowDomainError):
    """Raised when claiming a task that is already claimed by another contractor."""

    def __init__(self, task_id: str, claimed_by: str) -> None:
        self.task_id = task_id
        self.claimed_by = claimed_by
        super().__init__(f"Task '{task_id}' is already claimed by contractor '{claimed_by}'.")


class TaskNotClaimedError(ShadowDomainError):
    """Raised when attempting an action (like submit) on an unclaimed task."""

    def __init__(self, task_id: str, current_status: str) -> None:
        self.task_id = task_id
        self.current_status = current_status
        super().__init__(f"Cannot submit task '{task_id}': status is '{current_status}', expected 'claimed'.")


class TaskPermissionError(ShadowDomainError):
    """Raised when a contractor attempts an operation on a task owned by someone else."""

    def __init__(self, task_id: str, claimed_by: str) -> None:
        self.task_id = task_id
        self.claimed_by = claimed_by
        super().__init__(f"Task '{task_id}' is claimed by another contractor.")


class ContractorNotFoundError(ShadowDomainError):
    """Raised when a requested contractor account is not found."""

    def __init__(self, identifier: str) -> None:
        self.identifier = identifier
        super().__init__(f"Contractor '{identifier}' not found.")


class ContractorAlreadyExistsError(ShadowDomainError):
    """Raised when attempting to register a username that is already taken."""

    def __init__(self, username: str) -> None:
        self.username = username
        super().__init__(f"Contractor with username '{username}' already exists.")
