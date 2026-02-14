"""
Message parsers for Telegram bot.

Parses incoming Telegram messages into structured Pydantic models
(NewHire, Termination).
"""

from datetime import datetime
from typing import Dict

from src.models.new_hire import NewHire
from src.models.termination import Termination


def parse_new_hire_raw(text: str) -> Dict[str, str]:
    """Parse a /newhire message into a raw key-value dict.

    This function performs case-insensitive field name parsing and returns
    the raw dict for validation BEFORE creating the Pydantic model.

    Expected format:
        /newhire
        First Name: John
        Last Name: Doe
        Email: john.doe@company.com
        Phone: 555-123-4567
        Store Number: 39104
        Job Title: Crew
        Work Schedule: Part Time
        Pay Rate: 15.50
        Pay Type: hourly
        Start Date: 03/01/2026
        Reason: New Hire

    Args:
        text: The full message text from Telegram.

    Returns:
        Dict with normalized keys (title case) and trimmed values.

    Examples:
        >>> parse_new_hire_raw("/newhire\\nfirst name: John\\nlast name: Doe")
        {"First Name": "John", "Last Name": "Doe"}
    """
    lines = text.strip().split("\n")
    data = {}

    # Normalize field names to handle case-insensitive input
    field_mapping = {
        "first name": "First Name",
        "last name": "Last Name",
        "email": "Email",
        "phone": "Phone",
        "store number": "Store Number",
        "job title": "Job Title",
        "work schedule": "Work Schedule",
        "pay rate": "Pay Rate",
        "pay type": "Pay Type",
        "start date": "Start Date",
        "reason": "Reason",
    }

    # Skip the first line (/newhire command)
    for line in lines[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key_lower = key.strip().lower()
        normalized_key = field_mapping.get(key_lower, key.strip())
        data[normalized_key] = value.strip()

    return data


def parse_new_hire(text: str) -> NewHire:
    """Parse a /newhire message into a NewHire model.

    This is called AFTER validation passes. Converts the raw dict into
    the Pydantic NewHire model with all transformations applied.

    Args:
        text: The full message text from Telegram.

    Returns:
        Validated NewHire instance.

    Raises:
        ValueError: If required fields are missing or invalid.
    """
    data = parse_new_hire_raw(text)

    # Case-insensitive helper to get values
    def get_value(key: str) -> str:
        for k, v in data.items():
            if k.lower() == key.lower():
                return v
        return None

    try:
        hire_data = {
            "first_name": get_value("First Name"),
            "last_name": get_value("Last Name"),
            "email": get_value("Email"),
            "phone": get_value("Phone"),
            "store_number": get_value("Store Number"),
            "job_title": get_value("Job Title"),
            "work_schedule": get_value("Work Schedule"),
            "pay_rate": float(get_value("Pay Rate") or 0),
            "pay_frequency": get_value("Pay Type") or "hourly",
            "start_date": datetime.strptime(
                get_value("Start Date"), "%m/%d/%Y"
            ).date(),
            "reason": get_value("Reason") or "new hire",
        }

        return NewHire(**hire_data)

    except (KeyError, AttributeError) as e:
        raise ValueError(f"Missing required field: {e}")
    except ValueError as e:
        raise ValueError(f"Invalid field value: {e}")


def parse_termination(text: str) -> Termination:
    """Parse a /terminate message into a Termination model.

    Expected format:
        /terminate
        First Name: John
        Last Name: Doe
        Employee ID: 00123456
        ...

    Args:
        text: The full message text from Telegram.

    Returns:
        Validated Termination instance.

    Raises:
        ValueError: If required fields are missing or invalid.
    """
    lines = text.strip().split('\n')
    data = {}

    # Skip the first line (/terminate command)
    for line in lines[1:]:
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        data[key.strip()] = value.strip()

    # Parse Yes/No to boolean
    def parse_yes_no(value: str) -> bool:
        return value.lower() in ('yes', 'y', 'true', '1')

    # Map Telegram fields to Termination model fields
    try:
        term_data = {
            'first_name': data.get('First Name'),
            'last_name': data.get('Last Name'),
            'employee_id': data.get('Employee ID'),
            'termination_date': datetime.strptime(data.get('Termination Date'), '%m/%d/%Y').date(),
            'last_work_date': datetime.strptime(data.get('Last Work Date'), '%m/%d/%Y').date(),
            'termination_reason': data.get('Reason'),
            'termination_type': data.get('Type'),
            'eligible_for_rehire': parse_yes_no(data.get('Eligible for Rehire', 'Yes')),
            'payout_pto': parse_yes_no(data.get('Payout PTO', 'No')),
            'notes': data.get('Notes'),
        }

        return Termination(**term_data)

    except KeyError as e:
        raise ValueError(f"Missing required field: {e}")
    except ValueError as e:
        raise ValueError(f"Invalid field value: {e}")
