"""Selectors for the Check Status workflow (Onboarding Dashboard)."""

# Navigation (reuse existing Process + Hire/Rehire selectors from new_hire.py)
VIEW_DASHBOARD_BUTTON = '#navigateToOnboardingViewId'

# Date range filter
FROM_DATE_FIELD = '#fromDateField'
VIEW_BUTTON = '#Onboarding-Dashboard-LoadDashboardFromCalendar'

# Employee list modal
VIEW_EMPLOYEES_BUTTON = '#Onboarding-Dashboard-ClickInProgressEmpStatusList'
EMPLOYEE_SEARCH_BOX = 'input[data-id="mdf-searchbox-id"]'

# Employee name button pattern — ID contains the employee name
# Use dynamically: f'sdf-button[id="Onboarding-Dashboard-OpenEmployeeStatus{first} {last}"]'
# Fallback: search by aria-label with the employee name

# Review Onboarding Status modal (screenshot #1 captured here)

# Upload Documents View Details button — target by ID substring
UPLOAD_DOCS_VIEW_DETAILS = 'sdf-button[id*="ViewDetails Upload Documents"]'
# The OTHER View Details button (DO NOT CLICK): sdf-button[id*="ViewDetails Review Documents"]
