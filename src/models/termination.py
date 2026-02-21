"""
Pydantic model for termination data.

Validates and structures all information required to process an employee
termination in ADP Workforce Now.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, field_validator


class Termination(BaseModel):
    """Represents an employee termination to be processed in ADP."""

    # Employee identification
    first_name: str
    last_name: str
    employee_id: str  # ADP employee/position ID

    # Termination details
    termination_date: date
    last_work_date: date
    termination_reason: str  # e.g., "Voluntary", "Involuntary", "Resignation"
    termination_type: str  # e.g., "Standard", "Retirement", "End of Contract"
    eligible_for_rehire: bool = True

    # Final pay
    final_pay_date: Optional[date] = None
    payout_pto: bool = False  # Pay out remaining PTO

    # Additional info
    notes: Optional[str] = None

    @field_validator("termination_reason")
    @classmethod
    def validate_termination_reason(cls, v: str) -> str:
        allowed = {
            "voluntary",
            "involuntary",
            "resignation",
            "retirement",
            "end of contract",
            "mutual agreement",
            "job abandonment",
            "layoff",
            "death",
        }
        if v.lower() not in allowed:
            raise ValueError(f"Termination reason must be one of: {allowed}")
        return v.lower()

    @field_validator("termination_type")
    @classmethod
    def validate_termination_type(cls, v: str) -> str:
        allowed = {
            "standard",
            "retirement",
            "end of contract",
            "reduction in force",
        }
        if v.lower() not in allowed:
            raise ValueError(f"Termination type must be one of: {allowed}")
        return v.lower()
