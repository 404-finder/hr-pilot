"""
Input validation for Telegram messages.

Validates user input against config_tables before creating Pydantic models.
"""

from datetime import datetime
from typing import List

from src.config_tables import (
    JOB_TITLES,
    REASON_FOR_HIRE,
    STORE_LOCATIONS,
    WORK_SCHEDULE,
)


def validate_new_hire_input(data: dict) -> List[str]:
    """Validate new hire input data against config_tables.

    Args:
        data: Raw parsed key-value dict from telegram message.

    Returns:
        List of error strings. Empty list means all valid.

    Examples:
        >>> validate_new_hire_input({"First Name": "John", "Store Number": "99999"})
        ["Store Number must be one of: 39101 (Hewitt Drive), ..."]
    """
    errors = []

    # ========================================================================
    # REQUIRED FIELDS CHECK
    # ========================================================================
    required_fields = [
        "First Name",
        "Last Name",
        "Email",
        "Phone",
        "Store Number",
        "Job Title",
        "Work Schedule",
        "Pay Rate",
        "Pay Type",
        "Start Date",
    ]

    for field in required_fields:
        # Case-insensitive check
        if not any(key.lower() == field.lower() for key in data.keys()):
            errors.append(f"Missing required field: {field}")

    # ========================================================================
    # STORE NUMBER VALIDATION
    # ========================================================================
    store_number = None
    for key, value in data.items():
        if key.lower() == "store number":
            store_number = value.strip()
            break

    if store_number and store_number not in STORE_LOCATIONS:
        options = ", ".join(
            f"{num} ({name})" for num, name in STORE_LOCATIONS.items()
        )
        errors.append(f"Store Number must be one of: {options}")

    # ========================================================================
    # JOB TITLE VALIDATION
    # ========================================================================
    job_title = None
    for key, value in data.items():
        if key.lower() == "job title":
            job_title = value.lower().strip()
            break

    if job_title and job_title not in JOB_TITLES:
        options = ", ".join(sorted(JOB_TITLES.keys()))
        errors.append(f"Job Title must be one of: {options}")

    # ========================================================================
    # WORK SCHEDULE VALIDATION
    # ========================================================================
    work_schedule = None
    for key, value in data.items():
        if key.lower() == "work schedule":
            work_schedule = value.lower().strip()
            break

    if work_schedule and work_schedule not in WORK_SCHEDULE:
        options = ", ".join(sorted(WORK_SCHEDULE.keys()))
        errors.append(f"Work Schedule must be one of: {options}")

    # ========================================================================
    # REASON VALIDATION (optional field)
    # ========================================================================
    reason = None
    for key, value in data.items():
        if key.lower() == "reason":
            reason = value.lower().strip()
            break

    if reason and reason not in REASON_FOR_HIRE:
        options = ", ".join(sorted(REASON_FOR_HIRE.keys()))
        errors.append(f"Reason must be one of: {options}")

    # ========================================================================
    # PAY TYPE VALIDATION
    # ========================================================================
    pay_type = None
    for key, value in data.items():
        if key.lower() == "pay type":
            pay_type = value.lower().strip()
            break

    if pay_type and pay_type not in {"hourly", "salary"}:
        errors.append("Pay Type must be one of: hourly, salary")

    # ========================================================================
    # PAY RATE VALIDATION
    # ========================================================================
    pay_rate = None
    for key, value in data.items():
        if key.lower() == "pay rate":
            pay_rate = value.strip()
            break

    if pay_rate:
        try:
            float(pay_rate)
        except ValueError:
            errors.append("Pay Rate must be a valid number")

    # ========================================================================
    # START DATE VALIDATION
    # ========================================================================
    start_date = None
    for key, value in data.items():
        if key.lower() == "start date":
            start_date = value.strip()
            break

    if start_date:
        try:
            datetime.strptime(start_date, "%m/%d/%Y")
        except ValueError:
            errors.append(
                "Start Date must be in MM/DD/YYYY format (e.g., 03/15/2026)"
            )

    return errors


def validate_email_change_input(data: dict) -> tuple:
    """Validate email change input data.

    Args:
        data: Raw parsed dict with keys: first_name, last_name, new_email.

    Returns:
        (True, None) on success, or (False, error_message) on failure.
    """
    required_fields = ["first_name", "last_name", "new_email"]

    for field in required_fields:
        if not data.get(field, "").strip():
            label = field.replace("_", " ").title()
            return (False, f"Missing required field: {label}")

    email = data["new_email"].strip()
    if "@" not in email or "." not in email:
        return (False, "New Email must be a valid email address (must contain @ and .)")

    return (True, None)
