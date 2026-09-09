# Architecture & Flow Diagrams

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACES                            │
├─────────────────────────────┬───────────────────────────────────────┤
│   Web UI (Browser)          │   CLI (Terminal)                      │
│  - Chat interface           │  - Interactive loop                   │
│  - Suggestion buttons       │  - Direct agent interaction           │
│  - Tool trace display       │  - Same agent, different frontend     │
└────────────┬────────────────┴───────────────┬───────────────────────┘
             │ HTTP/JSON                      │ stdin/stdout
             │                                │
┌────────────▼───────────────────────────────▼───────────────────────┐
│                         FASTAPI SERVER                              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Session Management                                           │  │
│  │ - Track session_id per user                                 │  │
│  │ - Maintain conversation history (last 10 messages)          │  │
│  │ - Rate limiting (10 req/min)                                │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────┬────────────────────────────────────────────────────────┘
             │
             │ Passes full conversation history
             │
┌────────────▼───────────────────────────────────────────────────────┐
│                    CORE AGENT ENGINE                                │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Two Implementations (same logic, different frameworks)      │  │
│  │                                                              │  │
│  │ agent.py                  agent_langchain.py               │  │
│  │ ├─ Explicit loop          ├─ LangChain create_agent       │  │
│  │ ├─ Manual tool calling    ├─ LangGraph under the hood     │  │
│  │ ├─ Full visibility        ├─ Framework handles loop       │  │
│  │ └─ ~180 lines             └─ ~100 lines                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  System Prompt → Tool Definitions → Groq LLM → Response            │
└────────────┬────────────────────────────────────────────────────────┘
             │
             │ Tool names & parameters
             │
┌────────────▼───────────────────────────────────────────────────────┐
│                    TOOL DEFINITIONS & DISPATCH                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ tools.py                  tools_langchain.py                │  │
│  │ ├─ TOOL_DEFINITIONS       ├─ @tool decorated functions     │  │
│  │ │  (OpenAI format)        │  (LangChain format)            │  │
│  │ └─ TOOL_FUNCTIONS         └─ tools list                    │  │
│  │    (dispatch table)                                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  Maps tool names to functions:                                     │
│  - find_employee_by_name    - get_org_info                       │  │
│  - get_pto_balance          - get_expense_status                 │  │
│  - search_hr_policy         - submit_pto_request                 │  │
│  - submit_expense_report    - update_contact_info                │  │
└────────────┬────────────────────────────────────────────────────────┘
             │ Tool execution
             │
┌────────────▼───────────────────────────────────────────────────────┐
│              🔷 WORKDAY API LAYER (Mock & Real) 🔷                 │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ workday_api.py                                              │  │
│  │                                                              │  │
│  │ Currently: MOCK DATA ✓                                      │  │
│  │ ├─ Reads from JSON files                                    │  │
│  │ ├─ Simulates Workday responses                              │  │
│  │ └─ Returns realistic employee data                          │  │
│  │                                                              │  │
│  │ Ready for: REAL WORKDAY API ⚙️                              │  │
│  │ ├─ OAuth token management (skeleton exists)                 │  │
│  │ ├─ Real Workday REST API calls                              │  │
│  │ └─ Switch via USE_REAL_API environment variable             │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  Workday Data Models:                                              │
│  - Employees (E1001-E1018)                                         │
│  - Departments (Engineering, HR, Finance, etc.)                    │
│  - PTO Balances                                                    │
│  - Expense Reports                                                 │
│  - Org Structure (Manager/Reports)                                 │
└────────────┬───────────────────────────────────────────────────────┘
             │
             │ (Future: Real Workday OAuth + REST)
             │
             ▼
         WORKDAY
         ╭─────────────────────╮
         │ Real HR System      │
         │ (Production Only)   │
         ╰─────────────────────╯
```

---

## 2. Agent Request Flow (Single Turn)

```
USER INPUT
    │
    ▼
┌─────────────────────────────────────────────────┐
│ 1. Browser/CLI Sends Message                    │
│    - Message text                               │
│    - Session ID (maintained by server)          │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│ 2. Server Receives Request                      │
│    - Look up session from sessions dict         │
│    - Get conversation history (last 10 msgs)    │
│    - Add system prompt if new session           │
│    - Append user message to history             │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│ 3. Agent.run_turn(messages)                     │
│    - Full conversation history is passed        │
│    - Agent has complete context                 │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│ 4. LLM API Call (Groq)                          │
│    Input:                                       │
│    - system_prompt                              │
│    - conversation_history                       │
│    - tool_definitions                           │
│    - model: openai/gpt-oss-120b                 │
│                                                 │
│    Output:                                      │
│    - Either: Final answer                       │
│    - Or: Tool calls (with parameters)           │
└─────────────────────────────────────────────────┘
    │
    ├─ Has tool_calls? ─NO──→ DONE (return answer)
    │
    └─ YES ─→ LOOP FOR EACH TOOL CALL
              │
              ▼
        ┌──────────────────────┐
        │ 5. Execute Tool      │
        │    - Name            │
        │    - Parameters      │
        │    - Get result      │
        └──────────────────────┘
              │
              ▼
        ┌──────────────────────┐
        │ 6. Add to History    │
        │    - Tool call       │
        │    - Tool result     │
        │    - Message role:   │
        │      "tool"          │
        └──────────────────────┘
              │
              ▼
        ┌──────────────────────┐
        │ 7. Next LLM Call     │
        │    - With tool       │
        │      results         │
        │    - Repeat loop     │
        └──────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│ 8. Return Response                              │
│    - Agent's final message                      │
│    - Tool trace (all tools called)              │
│    - Session ID (for next message)              │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│ 9. Update Session Memory                        │
│    - Save updated messages to sessions dict     │
│    - Keep last 10 messages + system prompt      │
│    - Ready for next user message                │
└─────────────────────────────────────────────────┘
    │
    ▼
RESPONSE TO USER
- In Web UI: Display message + tool trace
- In CLI: Print to terminal
```

---

## 3. Tool Calling Loop (The Heart of the Agent)

```
┌───────────────────────────────────────────────────────┐
│         AGENT'S TOOL CALLING LOOP                     │
│       (In agent.py - explicit implementation)        │
└───────────────────────────────────────────────────────┘

while True:
    │
    ├─ Call Groq API with:
    │  ├─ messages (conversation history)
    │  ├─ tools (TOOL_DEFINITIONS)
    │  └─ system_prompt
    │
    ▼ API returns ONE of:
    │
    ├─ Case 1: FINAL ANSWER
    │  └─ response.choices[0].message.content has text
    │     └─ EXIT LOOP, return answer
    │
    └─ Case 2: TOOL CALLS
       └─ response.choices[0].message.tool_calls has calls
          │
          ├─ For each tool_call:
          │  │
          │  ├─ Extract: name, tool_call_id, arguments
          │  │
          │  ├─ Look up function from TOOL_FUNCTIONS dict
          │  │
          │  ├─ Execute function with arguments
          │  │  │
          │  │  └─ Calls workday_api.py functions
          │  │
          │  ├─ Get result (dict with data or error)
          │  │
          │  └─ Add to messages as "tool" role message
          │
          └─ Loop back to LLM with updated messages
             (LLM now sees tool results, can call more tools
              or formulate final answer)
```

---

## 4. Workday Integration Architecture

```
┌─────────────────────────────────────────────────────────┐
│        🔷 WORKDAY AI AGENT - HR TOOLS LAYER 🔷         │
└─────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                    AGENT (ask HR questions)              │
└──────────────┬───────────────────────────────────────────┘
               │
     ┌─────────┴────────────┬──────────────┬──────────┐
     │                      │              │          │
     ▼                      ▼              ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│  READ    │ │  WRITE   │ │ SEARCH   │ │REFERENCE │
│ TOOLS    │ │ TOOLS    │ │ TOOLS    │ │ TOOLS    │
└──────────┘ └──────────┘ └──────────┘ └──────────┘

READ TOOLS (Query Workday):
┌────────────────────────────────────────────────┐
│ find_employee_by_name(name)                    │
│ ├─ Search: employees.json                      │
│ └─ Return: {employee_id, name, dept, title}   │
│                                                │
│ get_pto_balance(employee_id)                   │
│ ├─ Look up: Workday PTO module                 │
│ └─ Return: {pto_balance_days, max_allowed}     │
│                                                │
│ get_org_info(employee_id)                      │
│ ├─ Look up: Workday org structure              │
│ └─ Return: {manager, dept, reports}            │
│                                                │
│ get_expense_status(report_id)                  │
│ ├─ Look up: Workday expense module             │
│ └─ Return: {status, amount, submitted_date}    │
└────────────────────────────────────────────────┘

WRITE TOOLS (Modify Workday):
┌────────────────────────────────────────────────┐
│ submit_pto_request(emp_id, dates, reason)      │
│ ├─ Write to: Workday Time Off module           │
│ └─ Return: {request_id, status}                │
│                                                │
│ submit_expense_report(emp_id, desc, amount)    │
│ ├─ Write to: Workday Expenses module           │
│ └─ Return: {report_id, status}                 │
│                                                │
│ update_contact_info(emp_id, phone, email)      │
│ ├─ Write to: Workday Employee Data             │
│ └─ Return: {status, updated_fields}            │
└────────────────────────────────────────────────┘

SEARCH TOOLS (Query Policies):
┌────────────────────────────────────────────────┐
│ search_hr_policy(query)                        │
│ ├─ Search: Workday policy docs                 │
│ └─ Return: {matching_policies}                 │
│    • PTO Policy                                │
│    • Parental Leave Policy                     │
│    • Remote Work Policy                        │
│    • Expense Policy                            │
└────────────────────────────────────────────────┘

All tools ──→ workday_api.py ──→ WORKDAY
                                  ├─ Mock (dev)
                                  └─ Real (prod)
```

---

## 5. Workday OAuth Integration (Real API)

```
┌─────────────────────────────────────────────────────────┐
│              REAL WORKDAY API FLOW (Future)             │
└─────────────────────────────────────────────────────────┘

1. OAUTH SETUP
   ┌─────────────────────────────────────────┐
   │ Workday Admin                           │
   │ ├─ Create OAuth client in Workday       │
   │ ├─ Get CLIENT_ID & CLIENT_SECRET        │
   │ ├─ Register callback URL                │
   │ └─ Grant necessary scopes                │
   │    (employees, time_off, expenses, etc.)│
   └─────────────────────────────────────────┘
        │ Store in .env
        ▼
   WORKDAY_CLIENT_ID=***
   WORKDAY_CLIENT_SECRET=***
   WORKDAY_TENANT=https://wd2-impl-services1.workday.com/

2. TOKEN EXCHANGE
   ┌─────────────────────────────────────────┐
   │ Agent needs to access Workday           │
   │                                         │
   │ POST /api/v1/oauth2/token               │
   │ ├─ auth: (CLIENT_ID, CLIENT_SECRET)     │
   │ ├─ grant_type: client_credentials       │
   │ └─ Returns: access_token (expires soon) │
   └─────────────────────────────────────────┘
        │ Cache token with expiry
        ▼
   _workday_token_cache = "eyJ0eXAi..."
   token_expiry = 3600 seconds

3. API CALLS
   ┌─────────────────────────────────────────┐
   │ GET /workers?limit=10                   │
   │ Headers: Authorization: Bearer {token}  │
   │ Returns: {workers: [{id, name, ...}]}   │
   │                                         │
   │ Other endpoints:                        │
   │ - /time_off_requests                    │
   │ - /expense_reports                      │
   │ - /employees/{id}                       │
   │ - /org_structure                        │
   └─────────────────────────────────────────┘
        │ Parse JSON response
        ▼
   Convert to our format & return to agent

4. TOKEN REFRESH
   ┌─────────────────────────────────────────┐
   │ When token expires:                     │
   │ ├─ Detect: 401 Unauthorized             │
   │ ├─ Retry: Get new token                 │
   │ └─ Retry: Original request              │
   └─────────────────────────────────────────┘
```

---

## 6. Session Memory Flow

```
USER SESSION LIFECYCLE

1. FIRST MESSAGE
   ┌─────────────────────────────┐
   │ /api/chat?session_id=null   │
   └──────────────┬──────────────┘
                  │
                  ▼
   ┌──────────────────────────────────┐
   │ Server checks: session_id exists? │
   │ ├─ No → Create new session       │
   │ │       sessions[new_id] = [      │
   │ │           system_prompt,        │
   │ │       ]                         │
   │ │   Return session_id to client   │
   │ └─ Yes → Use existing session    │
   └──────────────┬───────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────┐
   │ Add user message                 │
   │ Run agent                        │
   │ Get agent response               │
   └──────────────┬───────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────┐
   │ Save updated messages:           │
   │ sessions[session_id] = [         │
   │     system_prompt,               │
   │     user_msg_1,                  │
   │     agent_response_1,            │
   │ ]                                │
   │                                  │
   │ Memory trimming (keep last 10):  │
   │ if len(messages) > 11:           │
   │   messages = [sys] + last_10     │
   └──────────────┬───────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────┐
   │ Return to client:                │
   │ {                                │
   │     session_id: "abc123...",     │
   │     reply: "You have 12 PTO...", │
   │     trace: [...]                 │
   │ }                                │
   └──────────────────────────────────┘

2. SECOND MESSAGE (SAME SESSION)
   ┌──────────────────────────────────────┐
   │ Client sends: session_id="abc123..." │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │ Server:                              │
   │ ├─ Get messages from sessions dict   │
   │ ├─ messages already has:             │
   │ │  - system_prompt                   │
   │ │  - prev user message               │
   │ │  - prev agent response             │
   │ │  - **AGENT REMEMBERS CONTEXT!**    │
   │ │                                    │
   │ ├─ Add new user message to history   │
   │ └─ Run agent with full context       │
   └──────────────┬───────────────────────┘
                  │
                  ▼
   Agent sees conversation history:
   - "I'm Om Shankar. Update my contact"  ← From message 1
   - "You're all set, Om..."              ← Agent response 1
   - "Can you fetch my phone?"            ← New message 2
   
   Agent: "According to Workday, your phone is 9743882323"
   (It remembers the name "Om Shankar" from message 1!)
```

---

## 7. Data Flow Example: "Check My PTO"

```
USER → "I'm Om Shankar. Check my PTO balance."

           │
           ▼
    ┌──────────────────┐
    │ Agent sees:      │
    │ ├─ Name: Om      │
    │ └─ Action: PTO   │
    └────────┬─────────┘
             │
             ▼
    ┌─────────────────────────────────────┐
    │ Step 1: Find Employee               │
    │ Tool: find_employee_by_name("Om")   │
    │ Workday: employees.json             │
    │ Result: E1019 (Om Shankar)           │
    └────────┬────────────────────────────┘
             │
             ▼
    ┌─────────────────────────────────────┐
    │ Step 2: Get PTO Balance             │
    │ Tool: get_pto_balance(E1019)        │
    │ Workday: PTO module                 │
    │ Result: 16 days available            │
    └────────┬────────────────────────────┘
             │
             ▼
    ┌─────────────────────────────────────┐
    │ Step 3: Agent Formulates Answer     │
    │ "Om Shankar, you have 16 PTO days"  │
    │                                     │
    │ No more tools needed → Return       │
    └────────┬────────────────────────────┘
             │
             ▼
Response: "According to Workday, you have 16 
PTO days available."

Tool Trace:
├─ find_employee_by_name
│  ├─ Input: {"name": "Om Shankar"}
│  └─ Result: {employee_id: "E1019", ...}
│
└─ get_pto_balance
   ├─ Input: {"employee_id": "E1019"}
   └─ Result: {pto_balance_days: 16}
```

---

## 8. Technology Stack

```
┌─────────────────────────────────────────────────┐
│             TECHNOLOGY STACK                    │
├─────────────────────────────────────────────────┤
│                                                 │
│ FRONTEND                                        │
│ ├─ HTML5 + CSS3 (no framework)                 │
│ ├─ Vanilla JavaScript (no dependencies)        │
│ ├─ Marked.js (markdown rendering)              │
│ └─ LocalStorage (session tracking)             │
│                                                 │
│ BACKEND - HTTP                                  │
│ ├─ FastAPI (Python web framework)              │
│ ├─ Uvicorn (ASGI server)                       │
│ ├─ Slowapi (rate limiting)                     │
│ └─ Pydantic (request validation)               │
│                                                 │
│ BACKEND - AGENT LOGIC                           │
│ ├─ Option 1: Explicit loop (agent.py)         │
│ │  └─ Pure Python, manual tool calling        │
│ │                                              │
│ └─ Option 2: LangChain (agent_langchain.py)   │
│    ├─ LangChain 1.4.0                          │
│    ├─ LangGraph (under the hood)               │
│    └─ Same tools, different framework          │
│                                                 │
│ LLM - GROQ API                                  │
│ ├─ Groq SDK (Python client)                    │
│ ├─ Model: openai/gpt-oss-120b                  │
│ ├─ Fast inference (~200ms)                     │
│ └─ Free tier available                         │
│                                                 │
│ 🔷 WORKDAY LAYER 🔷                            │
│ ├─ Mock: data/employees.json                   │
│ ├─ Mock: data/hr_policy.md                     │
│ ├─ Real: OAuth 2.0 (ready)                     │
│ └─ Real: REST API (ready)                      │
│                                                 │
│ DEPLOYMENT                                      │
│ ├─ Local: Python + Venv                        │
│ ├─ Cloud: Railway/Heroku/AWS                   │
│ ├─ Docker: (easy to add)                       │
│ └─ Environment: .env variables                 │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## Summary

**What makes this a Workday AI Agent:**
1. ✅ **Workday-aware tools** - Understands HR domain (PTO, expenses, org structure)
2. ✅ **Realistic mock data** - employees.json mimics Workday employee records
3. ✅ **Ready for real API** - OAuth skeleton + workday_api.py abstraction layer
4. ✅ **Production patterns** - Rate limiting, session memory, error handling
5. ✅ **Two agent implementations** - Shows agentic AI understanding

**Next step to be "production-ready":**
- Real Workday OAuth + 1-2 actual API calls
- This proves you can integrate real Workday systems

Would you like me to:
1. Add these diagrams to README.md?
2. Create a separate ARCHITECTURE.md file?
3. Add a visual deployment diagram?
