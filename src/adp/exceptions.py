"""
Custom exceptions for ADP automation.

Defines all exception types used in the ADP automation module.
"""

from typing import Optional


class ADPError(Exception):
    """Base exception for ADP automation errors."""

    pass


class LoginError(ADPError):
    """Raised when ADP login fails."""

    pass


class FormSubmissionError(ADPError):
    """Raised when an ADP form submission fails."""

    def __init__(self, message: str, screenshot_path: Optional[str] = None):
        super().__init__(message)
        self.screenshot_path = screenshot_path


class EmployeeNotFoundError(ADPError):
    """Raised when employee search returns no results during termination."""

    pass


class NavigationError(ADPError):
    """Raised when ADP page navigation fails."""

    pass
