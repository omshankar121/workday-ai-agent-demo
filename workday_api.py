"""
workday_api.py - Mock Workday API layer.

For demo purposes, reads from local JSON. Can swap for real API later.
See WORKDAY_API_INTEGRATION.md for details on integrating real Workday.
"""

import json
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
USE_REAL_API = os.getenv("USE_REAL_WORKDAY_API", "false").lower() == "true"
WORKDAY_TENANT = os.getenv("WORKDAY_TENANT_URL", "")
WORKDAY_CLIENT_ID = os.getenv("WORKDAY_CLIENT_ID", "")
WORKDAY_CLIENT_SECRET = os.getenv("WORKDAY_CLIENT_SECRET", "")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
EMPLOYEES_PATH = os.path.join(DATA_DIR, "employees.json")
POLICY_PATH = os.path.join(DATA_DIR, "hr_policy.md")

# Cache for Workday OAuth token
_workday_token_cache = None


# ============================================================================
# WORKDAY API HELPER (Real API Integration)
# ============================================================================

def _get_workday_oauth_token():
    """Get OAuth token from Workday API."""
    global _workday_token_cache

    if _workday_token_cache:
        return _workday_token_cache

    try:
        import requests

        token_url = f"{WORKDAY_TENANT}/api/v1/oauth2/token"
        auth = (WORKDAY_CLIENT_ID, WORKDAY_CLIENT_SECRET)
        data = {"grant_type": "client_credentials"}

        response = requests.post(token_url, auth=auth, data=data)
        response.raise_for_status()

        token = response.json()["access_token"]
        _workday_token_cache = token
        return token
    except Exception as e:
        raise RuntimeError(f"Failed to get Workday token: {e}")


def _load_employees():
    """Load employees from mock data (local JSON)."""
    with open(EMPLOYEES_PATH, "r") as f:
        return json.load(f)


def find_employee_by_name(name: str) -> dict:
    """Find employee by name (case-insensitive, partial match)."""
    # Use mock data for demo
    employees = _load_employees()
    name_lower = name.lower().strip()
    matches = [e for e in employees if name_lower in e["name"].lower()]

    if not matches:
        return {"error": f"No employee found matching '{name}'."}
    if len(matches) > 1:
        return {
            "error": f"Multiple employees match '{name}'.",
            "candidates": [{"employee_id": m["employee_id"], "name": m["name"]} for m in matches],
        }
    return matches[0]


def get_employee(employee_id: str) -> dict:
    employees = _load_employees()
    for e in employees:
        if e["employee_id"] == employee_id:
            return e
    return {"error": f"No employee found with id '{employee_id}'."}


def get_pto_balance(employee_id: str) -> dict:
    employee = get_employee(employee_id)
    if "error" in employee:
        return employee
    return {
        "employee_id": employee["employee_id"],
        "name": employee["name"],
        "pto_balance_days": employee["pto_balance_days"],
    }


def get_org_info(employee_id: str) -> dict:
    employees = _load_employees()
    employee = get_employee(employee_id)
    if "error" in employee:
        return employee

    manager = None
    if employee.get("manager_id"):
        manager = get_employee(employee["manager_id"])

    direct_reports = [
        {"employee_id": e["employee_id"], "name": e["name"], "title": e["title"]}
        for e in employees
        if e.get("manager_id") == employee_id
    ]

    return {
        "employee_id": employee["employee_id"],
        "name": employee["name"],
        "department": employee["department"],
        "title": employee["title"],
        "manager": {"employee_id": manager["employee_id"], "name": manager["name"]} if manager else None,
        "direct_reports": direct_reports,
    }


def get_expense_status(report_id: str) -> dict:
    employees = _load_employees()
    for e in employees:
        for report in e.get("expense_reports", []):
            if report["report_id"] == report_id:
                return {
                    "report_id": report["report_id"],
                    "employee_name": e["name"],
                    "description": report["description"],
                    "amount": report["amount"],
                    "status": report["status"],
                    "submitted_on": report["submitted_on"],
                }
    return {"error": f"No expense report found with id '{report_id}'."}


def search_hr_policy(query: str) -> dict:
    """Very simple keyword search over the mock policy handbook.

    Splits the doc into sections by markdown headers and returns any section
    whose heading or body contains a query keyword. Good enough for a demo;
    a real project could swap this for embeddings + vector search.
    """
    with open(POLICY_PATH, "r") as f:
        text = f.read()

    sections = ["## " + s for s in text.split("## ")[1:]]
    query_words = [w.lower() for w in query.split() if len(w) > 2]

    matches = []
    for section in sections:
        section_lower = section.lower()
        if any(w in section_lower for w in query_words):
            matches.append(section.strip())

    if not matches:
        return {"result": "No matching policy section found."}
    return {"result": "\n\n".join(matches)}


def submit_pto_request(employee_id: str, start_date: str, end_date: str, reason: str = "") -> dict:
    """Submit a PTO (paid time off) request.

    In a real system, this would:
    - Validate dates against the calendar
    - Check balance availability
    - Create a workflow approval task
    - Notify the manager

    For the demo, we just return success with a reference number.
    """
    employee = get_employee(employee_id)
    if "error" in employee:
        return employee

    import uuid
    request_id = f"PTO-{str(uuid.uuid4())[:8].upper()}"

    return {
        "request_id": request_id,
        "employee_id": employee_id,
        "employee_name": employee["name"],
        "start_date": start_date,
        "end_date": end_date,
        "reason": reason or "Personal time",
        "status": "Pending Manager Approval",
        "submitted_at": "2026-09-09T10:30:00Z",
        "message": f"PTO request {request_id} submitted successfully. Your manager will review it within 2 business days."
    }


def submit_expense_report(employee_id: str, description: str, amount: float, category: str = "Other") -> dict:
    """Submit an expense report for reimbursement.

    In a real system, this would:
    - Create a report in Workday
    - Require receipt attachment
    - Route to manager for approval
    - Integrate with accounting

    For the demo, we return a submission confirmation.
    """
    employee = get_employee(employee_id)
    if "error" in employee:
        return employee

    import uuid
    report_id = f"EXP-{str(uuid.uuid4())[:4].upper()}"

    valid_categories = ["Travel", "Meals", "Office", "Conference", "Other"]
    category = category if category in valid_categories else "Other"

    return {
        "report_id": report_id,
        "employee_id": employee_id,
        "employee_name": employee["name"],
        "description": description,
        "amount": amount,
        "category": category,
        "status": "Submitted - Pending Review",
        "submitted_at": "2026-09-09T10:30:00Z",
        "message": f"Expense report {report_id} (${amount:.2f}) submitted. Please upload your receipt within 24 hours."
    }


def update_contact_info(employee_id: str, phone: str = None, email: str = None, address: str = None) -> dict:
    """Update employee contact information.

    In a real system, this would:
    - Update the employee directory
    - Sync to email systems
    - Send confirmation email
    - Log audit trail

    For the demo, we return a confirmation.
    """
    employee = get_employee(employee_id)
    if "error" in employee:
        return employee

    updates = []
    if phone:
        updates.append(f"Phone: {phone}")
    if email:
        updates.append(f"Email: {email}")
    if address:
        updates.append(f"Address: {address}")

    if not updates:
        return {"error": "No fields provided to update."}

    return {
        "employee_id": employee_id,
        "employee_name": employee["name"],
        "updated_fields": updates,
        "status": "Updated",
        "updated_at": "2026-09-09T10:30:00Z",
        "message": f"Contact information updated successfully. Changes may take up to 1 hour to sync."
    }
