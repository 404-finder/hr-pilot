"""
Pydantic model for new hire data.

Validates and structures all information required to add a new employee
to ADP Workforce Now.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, SecretStr, field_validator

from src.config_tables import JOB_TITLES, STORE_LOCATIONS, WORK_SCHEDULE


class NewHire(BaseModel):
    """Represents a new hire to be entered into ADP."""

    # Required fields from Telegram
    first_name: str
    last_name: str
    email: str
    phone: str
    store_number: str
    job_title: str
    work_schedule: str
    pay_rate: float
    pay_frequency: str  # "hourly" | "salary"
    start_date: date
    reason: str = "new hire"

    # Optional fields (delegated to "Ask the New Hire" flow in ADP)
    ssn: Optional[SecretStr] = None
    date_of_birth: Optional[date] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    @field_validator("pay_frequency")
    @classmethod
    def validate_pay_frequency(cls, v: str) -> str:
        """Validate pay frequency is hourly or salary."""
        allowed = {"hourly", "salary"}
        if v.lower() not in allowed:
            raise ValueError(f"Pay frequency must be one of: {allowed}")
        return v.lower()

    @field_validator("work_schedule")
    @classmethod
    def validate_work_schedule(cls, v: str) -> str:
        """Validate work schedule against WORK_SCHEDULE keys."""
        v_lower = v.lower().strip()
        if v_lower not in WORK_SCHEDULE:
            allowed = ", ".join(sorted(WORK_SCHEDULE.keys()))
            raise ValueError(f"Work schedule must be one of: {allowed}")
        return v_lower

    @field_validator("job_title")
    @classmethod
    def validate_job_title(cls, v: str) -> str:
        """Validate job title against JOB_TITLES keys."""
        v_lower = v.lower().strip()
        if v_lower not in JOB_TITLES:
            allowed = ", ".join(sorted(JOB_TITLES.keys()))
            raise ValueError(f"Job title must be one of: {allowed}")
        return v_lower

    @field_validator("store_number")
    @classmethod
    def validate_store_number(cls, v: str) -> str:
        """Validate store number against STORE_LOCATIONS keys."""
        v_stripped = v.strip()
        if v_stripped not in STORE_LOCATIONS:
            options = ", ".join(
                f"{num} ({name})" for num, name in STORE_LOCATIONS.items()
            )
            raise ValueError(f"Store number must be one of: {options}")
        return v_stripped

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        """Normalize reason to lowercase for config lookup."""
        return v.lower().strip()
