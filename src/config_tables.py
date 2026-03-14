"""
Central configuration for ADP dropdown mappings and validation.

This module defines all the lookup tables used to map user-friendly input
to ADP's internal format values (dropdown options, codes, etc.).
"""

from typing import Optional

# ============================================================================
# ADP DROPDOWN MAPPINGS
# ============================================================================

REASON_FOR_HIRE = {
    "current": "CURR - EXISTING POSITION",
    "new hire": "NEW - New Position",
}

TAX_ID_TYPE = {
    "ssn": "United States Social Security Number (SSN)",
    "ein": "United States Employer Identification Number (EIN)",
}

STORE_LOCATIONS = {
    # Texas Stores
    "39101": "Hewitt Drive",
    "39102": "Interstate 35",
    "39103": "South Valley Mills",
    "39104": "North Valley Mills",
    # Colorado Stores 
    "33561":"Austin Bluffs Parkway",
    "33562":"Galley Road",
    "33563":"Constitution Avenue",
    "33564":"Cheyenne Meadows Road",
    "33565":"Mesa Ridge Parkway",
    "33566":"South Academy Boulevard",
    "33567":"Stetson Hills Boulevard",
}

LOCATION_MANAGERS = {
    "39101": {"name": "Chandler Wilder", "search": "Wilder"},
    "39102": {"name": "Brandon Hudgens", "search": "Hudgens"},
    "39103": {"name": "Josue Gonzalez", "search": "Gonzalez"},
    "39104": {"name": "Mary De Los Rios", "search": "De Los Rios"},
    "33561": {"name": "Caleb Urrutia", "search": "Urrutia"},
    "33562": {"name": "Caleb Urrutia", "search": "Urrutia"},
    "33563": {"name": "Caleb Urrutia", "search": "Urrutia"},
    "33564": {"name": "Caleb Urrutia", "search": "Urrutia"},
    "33565": {"name": "Caleb Urrutia", "search": "Urrutia"},
    "33566": {"name": "Caleb Urrutia", "search": "Urrutia"},
    "33567": {"name": "Caleb Urrutia", "search": "Urrutia"},
}

JOB_TITLES = {
    "assist manager": "ASSTMNGR - ASSIST MANAGER",
    "co-manager": "CO-MGR-CO-MANAGER",
    "dist manager": "DISTMNGER - DISTRICT MANAGER",
    "gen manager": "GNRSMNGR - GENERAL MANAGER",
    "manager": "Manager Trainee",
    "sal manager": "SALARYMG - SALARY MANAGER",
    "crew": "TEAMMEMB - TEAM MEMBER",
}

WORK_SCHEDULE = {
    "full time": "RFT - REGULAR FULL TIME",
    "part time": "RPT - REGULAR PART TIME",
}

# Store prefix config - expandable for future states
STORE_CONFIG = {
    "3910": { # Texas Stores
        "company_code": "ZKT - LC Texas LLC",
        "worked_in_state": "TX - Texas",
        "sui_sdi_tax_code": "TX -53 -Texas",
        "onboarding_experience": "Texas Experience LC Texas",
        "benefits_eligibility": "BE - Benefit Eligible Team Members",
        "measurement_periods": True,
    },
    "3356": { # Colorado stores
        "company_code":  "FND - LC CO LLC",
        "worked_in_state": "CO - Colorado",
        "sui_sdi_tax_code": "CO -15 - Colorado",
        "onboarding_experience": "Colorado Experience LC CO",
        "benefits_eligibility": "BE - Benefit Eligible Team Members",
        "measurement_periods": True,
    }
}

# Job title categories for department suffix logic
MANAGER_JOB_TITLES = {
    "assist manager",
    "co-manager",
    "dist manager",
    "gen manager",
    "manager",
    "sal manager",
}
CREW_JOB_TITLES = {"crew"}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_search_code(adp_value: str) -> str:
    """Extract the search code from an ADP dropdown value.

    For values like 'CODE - Description', returns the code portion.
    For other values, returns the first 3 characters.

    Args:
        adp_value: Full ADP dropdown option text.

    Returns:
        Short code suitable for filtering the MDF dropdown.

    Examples:
        >>> get_search_code("BE - Benefit Eligible Team Members")
        'BE'
        >>> get_search_code("Manager Trainee")
        'Man'
    """
    if " - " in adp_value:
        return adp_value.split(" - ")[0].strip()
    return adp_value[:3]


def get_store_prefix(store_number: str) -> Optional[str]:
    """Get the matching store prefix from STORE_CONFIG.

    Args:
        store_number: Full store number (e.g., "39101").

    Returns:
        Matching prefix key from STORE_CONFIG (e.g., "3910") or None.

    Examples:
        >>> get_store_prefix("39101")
        "3910"
        >>> get_store_prefix("12345")
        None
    """
    for prefix in STORE_CONFIG.keys():
        if store_number.startswith(prefix):
            return prefix
    return None


def get_store_config(store_number: str) -> Optional[dict]:
    """Get the configuration dictionary for a store number.

    Args:
        store_number: Full store number (e.g., "39101").

    Returns:
        Store config dict from STORE_CONFIG or None if no match.

    Examples:
        >>> get_store_config("39101")
        {"company_code": "ZKT - LC Texas LLC", ...}
    """
    prefix = get_store_prefix(store_number)
    if prefix:
        return STORE_CONFIG[prefix]
    return None


def get_home_department(store_number: str, job_title_key: str) -> str:
    """Build the home department code based on store number and job title.

    Manager job titles get suffix "0", crew gets suffix "3".

    Args:
        store_number: Full store number (e.g., "39104").
        job_title_key: Lowercase job title key from JOB_TITLES.

    Returns:
        Home department code (e.g., "391043" for crew at store 39104).

    Examples:
        >>> get_home_department("39104", "crew")
        "391043"
        >>> get_home_department("39104", "assist manager")
        "391040"
    """
    if job_title_key in MANAGER_JOB_TITLES:
        suffix = "0"
    elif job_title_key in CREW_JOB_TITLES:
        suffix = "3"
    else:
        # Default to crew suffix if unknown
        suffix = "3"

    return store_number + suffix


def get_everify_location(store_number: str) -> str:
    """Get the E-Verify work location name for a store number.

    Args:
        store_number: Full store number (e.g., "39104").

    Returns:
        Store location name from STORE_LOCATIONS.

    Raises:
        KeyError: If store number not found in STORE_LOCATIONS.

    Examples:
        >>> get_everify_location("39104")
        "North Valley Mills"
    """
    return STORE_LOCATIONS[store_number]


def get_manager(store_number: str) -> dict:
    """Get the manager info dict for a store number.

    Args:
        store_number: Full store number (e.g., "39104").

    Returns:
        Dict with "name" (full name) and "search" (last name for ADP search).

    Raises:
        KeyError: If store number not found in LOCATION_MANAGERS.

    Examples:
        >>> get_manager("39104")
        {"name": "Mary De Los Rios", "search": "De Los Rios"}
    """
    return LOCATION_MANAGERS[store_number]
