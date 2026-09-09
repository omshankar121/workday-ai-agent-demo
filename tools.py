"""
tools.py - Tool definitions and dispatch table.

Maps tool names to functions. Explicit format so you can see what's happening.
"""

import workday_api

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "find_employee_by_name",
            "description": "Look up an employee's record by their (partial) name to get their employee_id. Use this first if the user refers to someone by name instead of an employee ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Full or partial employee name, e.g. 'Priya' or 'Sofia Torres'."}
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pto_balance",
            "description": "Get an employee's remaining paid time off (PTO) balance in days.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string", "description": "The employee's ID, e.g. 'E1001'."}
                },
                "required": ["employee_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_org_info",
            "description": "Get an employee's department, title, manager, and direct reports.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string", "description": "The employee's ID, e.g. 'E1001'."}
                },
                "required": ["employee_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_expense_status",
            "description": "Get the approval status, amount, and description of an expense report by its report ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "report_id": {"type": "string", "description": "The expense report ID, e.g. 'EXP-2031'."}
                },
                "required": ["report_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_hr_policy",
            "description": "Search the company HR policy handbook for information about PTO, expenses, remote work, parental leave, or performance reviews.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keywords describing what policy info is needed, e.g. 'remote work days per week'."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_pto_request",
            "description": "Submit a paid time off (PTO) request for approval. The request will be sent to the employee's manager.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string", "description": "The employee's ID, e.g. 'E1001'."},
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format."},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format."},
                    "reason": {"type": "string", "description": "Reason for the time off (optional)."}
                },
                "required": ["employee_id", "start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_expense_report",
            "description": "Submit an expense report for reimbursement. Include a description and amount.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string", "description": "The employee's ID, e.g. 'E1001'."},
                    "description": {"type": "string", "description": "What was the expense for, e.g. 'Conference registration'."},
                    "amount": {"type": "number", "description": "Amount in USD."},
                    "category": {"type": "string", "enum": ["Travel", "Meals", "Office", "Conference", "Other"], "description": "Expense category."}
                },
                "required": ["employee_id", "description", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_contact_info",
            "description": "Update your contact information (phone, email, address).",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string", "description": "The employee's ID, e.g. 'E1001'."},
                    "phone": {"type": "string", "description": "New phone number (optional)."},
                    "email": {"type": "string", "description": "New email address (optional)."},
                    "address": {"type": "string", "description": "New mailing address (optional)."}
                },
                "required": ["employee_id"],
            },
        },
    },
]

# Maps tool names to functions - called when model wants to use a tool
TOOL_FUNCTIONS = {
    "find_employee_by_name": lambda input: workday_api.find_employee_by_name(input["name"]),
    "get_pto_balance": lambda input: workday_api.get_pto_balance(input["employee_id"]),
    "get_org_info": lambda input: workday_api.get_org_info(input["employee_id"]),
    "get_expense_status": lambda input: workday_api.get_expense_status(input["report_id"]),
    "search_hr_policy": lambda input: workday_api.search_hr_policy(input["query"]),
    "submit_pto_request": lambda input: workday_api.submit_pto_request(
        input["employee_id"], input["start_date"], input["end_date"], input.get("reason", "")
    ),
    "submit_expense_report": lambda input: workday_api.submit_expense_report(
        input["employee_id"], input["description"], input["amount"], input.get("category", "Other")
    ),
    "update_contact_info": lambda input: workday_api.update_contact_info(
        input["employee_id"], input.get("phone"), input.get("email"), input.get("address")
    ),
}
