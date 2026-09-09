"""
tools_langchain.py - LangChain Version

Tools defined using LangChain's @tool decorator.
Compare with tools.py (explicit OpenAI format) to see the difference.

Key differences:
- Uses @tool decorator instead of TOOL_DEFINITIONS dict
- Function signature = tool schema (automatically generated)
- Less verbose, more Pythonic
- LangChain extracts docstring as description
"""

from langchain.tools import tool
import workday_api


@tool
def find_employee_by_name(name: str) -> dict:
    """Look up an employee by their (partial) name to get their employee_id.
    Use this first if the user refers to someone by name instead of an employee ID."""
    return workday_api.find_employee_by_name(name)


@tool
def get_pto_balance(employee_id: str) -> dict:
    """Get the PTO balance for an employee. Returns available PTO days."""
    return workday_api.get_pto_balance(employee_id)


@tool
def get_org_info(employee_id: str) -> dict:
    """Get organizational information for an employee.
    Returns: manager, department, and direct reports."""
    return workday_api.get_org_info(employee_id)


@tool
def get_expense_status(report_id: str) -> dict:
    """Get the status of an expense report by report ID."""
    return workday_api.get_expense_status(report_id)


@tool
def search_hr_policy(query: str) -> str:
    """Search the HR policy handbook for information.
    Use keywords like 'remote', 'pto', 'expenses', 'leave'."""
    return workday_api.search_hr_policy(query)


@tool
def submit_pto_request(employee_id: str, start_date: str, 
                      end_date: str, reason: str = "") -> dict:
    """Submit a PTO (paid time off) request for an employee.
    
    Args:
        employee_id: Employee ID
        start_date: Start date (YYYY-MM-DD format)
        end_date: End date (YYYY-MM-DD format)
        reason: Optional reason for the PTO
    
    Returns: Confirmation with request ID and status
    """
    return workday_api.submit_pto_request(employee_id, start_date, end_date, reason)


@tool
def submit_expense_report(employee_id: str, description: str, 
                         amount: float, category: str = "Other") -> dict:
    """Submit an expense report for an employee.
    
    Args:
        employee_id: Employee ID
        description: Description of the expense
        amount: Amount in dollars
        category: Expense category (default: Other)
    
    Returns: Confirmation with report ID and status
    """
    return workday_api.submit_expense_report(employee_id, description, amount, category)


@tool
def update_contact_info(employee_id: str, phone: str = None, 
                       email: str = None, address: str = None) -> dict:
    """Update employee contact information.
    
    Args:
        employee_id: Employee ID
        phone: New phone number (optional)
        email: New email address (optional)
        address: New address (optional)
    
    Returns: Confirmation of updated information
    """
    return workday_api.update_contact_info(employee_id, phone, email, address)


# List of all tools for the agent to use
tools = [
    find_employee_by_name,
    get_pto_balance,
    get_org_info,
    get_expense_status,
    search_hr_policy,
    submit_pto_request,
    submit_expense_report,
    update_contact_info,
]
