# Workday API Integration Guide

This document explains how to connect real Workday API to replace the mock data layer.

---

## Step 1: Get Workday Credentials

1. Go to your **Workday tenant admin console**
2. Navigate to **System > Security > OAuth 2.0 & API Clients**
3. Create new **API Client** with "Client Credentials" grant type
4. Get these values:
   - **Tenant URL**: `https://your-tenant.workday.com`
   - **Client ID**: `abc123...`
   - **Client Secret**: `xyz789...`

---

## Step 2: Add to .env

```bash
# Real Workday API configuration
USE_REAL_WORKDAY_API=true
WORKDAY_TENANT_URL=https://your-tenant.workday.com
WORKDAY_CLIENT_ID=your_client_id_here
WORKDAY_CLIENT_SECRET=your_client_secret_here
```

---

## Step 3: Update requirements.txt

Add `requests` library (if not already there):

```bash
pip install requests
```

---

## Step 4: Replace Function Bodies in workday_api.py

### Example 1: find_employee_by_name()

**Current (Mock):**
```python
def find_employee_by_name(name: str) -> dict:
    employees = _load_employees()
    matches = [e for e in employees if name.lower() in e["name"].lower()]
    return matches[0] if matches else {"error": "Not found"}
```

**With Real API:**
```python
def find_employee_by_name(name: str) -> dict:
    if not USE_REAL_API:
        # Keep mock implementation
        employees = _load_employees()
        matches = [e for e in employees if name.lower() in e["name"].lower()]
        return matches[0] if matches else {"error": "Not found"}
    
    # Real Workday API call
    import requests
    token = _get_workday_oauth_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{WORKDAY_TENANT}/api/v1/workers?search={name}&limit=10"
    
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    data = response.json()
    if not data.get("data"):
        return {"error": f"No employee found for '{name}'"}
    
    return {
        "employee_id": data["data"][0]["id"],
        "name": data["data"][0]["name"],
        "department": data["data"][0].get("department"),
        "title": data["data"][0].get("title")
    }
```

---

### Example 2: get_pto_balance()

**Current (Mock):**
```python
def get_pto_balance(employee_id: str) -> dict:
    employee = get_employee(employee_id)
    return {"pto_balance_days": employee.get("pto_balance_days", 0)}
```

**With Real API:**
```python
def get_pto_balance(employee_id: str) -> dict:
    if not USE_REAL_API:
        # Keep mock implementation
        employee = get_employee(employee_id)
        return {"pto_balance_days": employee.get("pto_balance_days", 0)}
    
    # Real Workday API call
    import requests
    token = _get_workday_oauth_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{WORKDAY_TENANT}/api/v1/workers/{employee_id}/time-off-balances"
    
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    data = response.json()
    return {
        "employee_id": employee_id,
        "pto_balance_days": data.get("available_balance", 0),
        "unit": "days"
    }
```

---

### Example 3: get_org_info()

**With Real API:**
```python
def get_org_info(employee_id: str) -> dict:
    if not USE_REAL_API:
        # Keep mock implementation
        employee = get_employee(employee_id)
        return {
            "employee_id": employee_id,
            "manager": f"Manager of {employee['name']}",
            "department": employee.get("department")
        }
    
    # Real Workday API call
    import requests
    token = _get_workday_oauth_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{WORKDAY_TENANT}/api/v1/workers/{employee_id}"
    
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    data = response.json()
    return {
        "employee_id": employee_id,
        "name": data["name"],
        "manager_id": data.get("manager", {}).get("id"),
        "manager_name": data.get("manager", {}).get("name"),
        "department": data.get("department"),
        "title": data.get("title")
    }
```

---

## Step 5: Test Incrementally

**Start with one function:**

```python
# In .env
USE_REAL_WORKDAY_API=false  # Start with mock

# Test mock implementation works
python agent.py
```

**Then enable real API:**

```python
# In .env
USE_REAL_WORKDAY_API=true  # Switch to real

# Test real API works
python agent.py
```

---

## Step 6: Error Handling

Add proper error handling:

```python
def get_pto_balance(employee_id: str) -> dict:
    if not USE_REAL_API:
        # Mock implementation...
        pass
    
    try:
        import requests
        token = _get_workday_oauth_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{WORKDAY_TENANT}/api/v1/workers/{employee_id}/time-off-balances"
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        return response.json()
        
    except requests.exceptions.Timeout:
        return {"error": "Workday API timeout"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"Workday API error: {e.response.status_code}"}
    except Exception as e:
        return {"error": f"Failed to get PTO balance: {str(e)}"}
```

---

## Workday API Endpoints Reference

| Function | Endpoint | Method |
|---|---|---|
| Find Employee | `/api/v1/workers?search={name}` | GET |
| Get Employee | `/api/v1/workers/{id}` | GET |
| PTO Balance | `/api/v1/workers/{id}/time-off-balances` | GET |
| Expenses | `/api/v1/workers/{id}/expenses` | GET |
| Reports | `/api/v1/reports/{id}` | GET |

---

## Security Notes

- 🔐 Never commit `.env` with real credentials
- 🔐 Use environment variables for credentials
- 🔐 Token expires - implement refresh logic for production
- 🔐 Add SSL verification: `verify=True` in requests

---

## Troubleshooting

**401 Unauthorized:**
- Check CLIENT_ID and CLIENT_SECRET
- Verify OAuth client has correct permissions

**404 Not Found:**
- Verify worker ID format (usually UUID)
- Check API endpoint path is correct

**Timeout:**
- Increase timeout value
- Check network connectivity to Workday

---

## Production Checklist

- ✅ Use toggle flag (`USE_REAL_API`) for safe switching
- ✅ Implement token refresh logic
- ✅ Add retry logic for transient errors
- ✅ Log all API calls for debugging
- ✅ Cache tokens to reduce API calls
- ✅ Add rate limiting awareness
- ✅ Test with actual Workday sandbox first

---

**Next Steps:**
1. Get credentials from Workday admin
2. Add to .env
3. Replace one function at a time
4. Test thoroughly
5. Deploy with confidence!
