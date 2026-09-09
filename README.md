# Agentic HR Assistant — Workday-Style AI Tool Calling Demo

**🔗 Live demo: [agentic-hr-assistant.up.railway.app](https://agentic-hr-assistant.up.railway.app)**

An agentic AI assistant that handles Workday-style HR tasks — PTO, org lookups, expenses, policy search — using autonomous tool calling. Built two ways: an explicit hand-written loop (`agent.py`) and a LangChain implementation (`agent_langchain.py`), so you can compare both approaches side by side.

## Features

- **8 HR tools:** Look up employees, PTO, org structure, expenses, HR policy
- **Write actions:** Submit PTO requests, expense reports, update contact info
- **Tool calling loop:** Explicit, visible implementation (no magic)
- **Web UI:** FastAPI + browser chat with markdown rendering & tool traces
- **Rate limiting:** Production-grade request protection
- **Clean code:** ~130 lines for the core agent — easy to understand & extend

## Quick Start

```bash
# 1. Clone & setup
git clone <your-repo-url>
cd workday-ai-agent-demo
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env and replace GROQ_API_KEY with your actual key
# Get free key at: https://console.groq.com/keys

# 3. Run
python -m uvicorn server:app --reload

# 4. Open browser → http://127.0.0.1:8000
```

## How it works

**agent.py** — explicit loop:
1. Send conversation + tool schemas to Groq API
2. Model returns either a final answer or a tool call request
3. Execute the tool, feed result back to model
4. Repeat until done

**agent_langchain.py** — same logic, built with LangChain's `create_agent` (LangGraph under the hood) instead of a hand-written loop. Compare the two to see what the framework buys you vs. what it hides.

**server.py** (123 lines):
- FastAPI endpoint wrapping `agent.py`'s loop
- Rate limiting (10 requests/min)
- Error handling

**static/index.html**:
- Chat UI with suggestion buttons
- Markdown rendering for agent replies
- Expandable tool trace visualization

## Tools included

| Tool | Type | Purpose |
|---|---|---|
| `find_employee_by_name` | Read | Resolve names to employee IDs |
| `get_pto_balance` | Read | Check PTO balance |
| `get_org_info` | Read | Manager, department, reports |
| `get_expense_status` | Read | Expense report status |
| `search_hr_policy` | Read | Search HR handbook |
| `submit_pto_request` | Write | Submit time off |
| `submit_expense_report` | Write | Submit expenses |
| `update_contact_info` | Write | Update phone/email/address |

## Example queries

- "How much PTO does Priya have left?"
- "Who reports to Sofia Torres?"
- "Submit PTO for Sept 15-19"
- "What's the remote work policy?"

## Why two implementations?

LangChain/LangGraph handle tool calling for you, but obscure how it works under the hood. Building the loop by hand first, then re-implementing it with LangChain, makes the tradeoff concrete instead of theoretical:

**Explicit loop (`agent.py`)**
- ✅ Full visibility into prompt → tools → result → response
- ✅ Trivial to debug (print anywhere)
- ✅ No dependency lock-in

**LangChain (`agent_langchain.py`)**
- ✅ Less code to maintain
- ✅ Built-in patterns for more complex agent graphs later
- ⚠️ More abstraction between you and what's actually happening

## Project structure

```
agent.py              # Explicit tool-calling loop
agent_langchain.py    # Same agent, built with LangChain's create_agent
server.py             # FastAPI wrapper (used by both agent versions)
tools.py              # Tool definitions + dispatch (OpenAI format)
tools_langchain.py    # Tool definitions (LangChain @tool format)
workday_api.py        # "Workday API" (mock data, OAuth-ready for real API)
data/                 # Mock employee records + HR policy handbook
static/               # Web UI
requirements.txt
Procfile              # Railway deployment config
.env.example
.gitignore
```

## Design Decisions

**Q: Why not use LangChain?**
A: LangChain automates the tool-calling loop but hides how it works. I wanted to understand the mechanism, so I built it explicitly (130 lines). This makes it debuggable and customizable. You can see exactly what happens at each step.

**Q: Why mock Workday API instead of real one?**
A: Real Workday API requires enterprise license + OAuth setup + sandbox access. Mock data shows the architecture without bureaucracy. **The architecture is identical** — to swap in real API, just change `workday_api.py`'s internals. The agent loop doesn't care.

**Q: Why FastAPI for the server?**
A: HTTP is a detail. FastAPI handles it well (rate limiting, CORS, error codes, validation) so I can focus on the agent logic. The agent itself is completely separate and framework-agnostic — could run in Flask, Django, Discord, a job queue, anywhere.

**Q: Why no database persistence?**
A: Portfolio project should be readable in 5 minutes. Each request is independent (stateless). In production, you'd add persistence with Redis/PostgreSQL in server.py — but the agent loop wouldn't change at all.

**Q: Why simplified codebase (no streaming, no retries)?**
A: **Simple ≠ incomplete.** The core concept is fully visible. Streaming (Server-Sent Events) and retries (exponential backoff) are nice optimizations but obscure the main idea. Can add them later in 30 minutes.

See `DEVELOPMENT.md` for detailed thinking behind each decision.
