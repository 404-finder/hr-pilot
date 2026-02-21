"""
Shared base models, enums, and types.

Contains common enumerations and base classes used across all HR data models.
"""

from enum import Enum


class ActionType(str, Enum):
    """Supported HR automation actions."""

    NEW_HIRE = "new_hire"
    TERMINATION = "termination"


class ActionStatus(str, Enum):
    """Status of an automation run."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
