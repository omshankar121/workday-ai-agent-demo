# Development Notes

## Why I built this

Real Workday API requires an enterprise license. Most AI projects use frameworks like LangChain, which automate tool calling but hide the actual mechanics. I wanted to understand **how tool calling actually works**, so I built the loop explicitly by hand first (`agent.py`), then rebuilt the same agent with LangChain (`agent_langchain.py`) to compare what the framework buys you.

## Architecture decisions

### 1. Explicit tool-calling loop, built by hand first

**The loop:**
1. Send conversation + tool schemas to model
2. Model returns either a final answer OR a tool call request
3. Execute the tool, feed result back to model
4. Repeat until done

**Why build it by hand?**
- ✅ Full visibility into what's happening
- ✅ Easy to debug (add print() anywhere)
- ✅ No lock-in to a framework
- ✅ Easy to customize (add retries, filtering, validation)

**Trade-off:**
- More code than LangChain (but only 130 lines)
- Responsibility for correctness is yours (but that's the point)

### 2. Pure Python for the agent (no framework)

The agent loop (`agent.py`) is framework-agnostic. It could run:
- In a FastAPI endpoint ✅ (what we do)
- In a Discord bot
- In a CLI
- In a job queue
- Anywhere

This is intentional — the agent doesn't care **how** it gets messages or **where** it sends responses.

### 3. FastAPI for the server (not building from scratch)

FastAPI is minimal but production-grade:
- ✅ Rate limiting (slowapi middleware)
- ✅ CORS handling
- ✅ Error codes (400, 500, 503)
- ✅ Request validation (Pydantic)

**Why FastAPI?** It lets us focus on the agent logic without reinventing HTTP wheels.

### 4. Mock Workday API (not real enterprise access)

Real Workday API:
- Requires enterprise license
- Requires OAuth setup
- Requires sandbox tenant
- Hides the agent architecture under API complexity

Mock data:
- ✅ Shows the agent architecture clearly
- ✅ Works immediately
- ✅ Easy to extend

**The key insight:** The architecture is identical. To connect real Workday API:
```python
# Currently: return mock data
def get_pto_balance(employee_id):
    return {"balance": 12, "unit": "days"}

# Production: swap in a real HTTP call
def get_pto_balance(employee_id):
    response = requests.get(f"https://workday.com/api/pto/{employee_id}")
    return response.json()
```

That's it. The agent loop doesn't change.

### 5. Simplified codebase (removed persistence)

**Initial version had:**
- SQLAlchemy ORM for chat persistence
- Redis-ready rate limiting
- Streaming response infrastructure

**Why I removed it:**
- Portfolio project should be **readable in 5 minutes**
- Persistence obscures the tool-calling pattern
- Can add Redis/PostgreSQL later without touching agent.py

**Design principle:** Each file has one job:
- `agent.py` = tool-calling loop (130 lines, pure logic)
- `server.py` = HTTP wrapper (123 lines, no business logic)
- `tools.py` = tool definitions (dispatch table)
- `workday_api.py` = data layer (mock or real, doesn't matter)

## Iterations I actually did

### Iteration 1: Start with LangChain
Pros: Everything works immediately
Cons: Black box. Can't understand what's happening.
Decision: Rip it out. Learn by building.

### Iteration 2: Add retry logic with exponential backoff
Pros: Handles rate limits gracefully
Cons: Adds 30 lines, obscures the core loop
Decision: Remove for clarity. Groq SDK has timeouts anyway.

### Iteration 3: Add database persistence
Pros: Users can resume conversations
Cons: SQLAlchemy ORM adds cognitive load
Decision: Remove for portfolio. KISS principle.

### Iteration 4: Add streaming responses
Pros: Better UX (word-by-word)
Cons: Requires Server-Sent Events, complicates frontend
Decision: Remove for MVP. Can add later with `response.with_streaming_response()`.

### Iteration 5: Remove localStorage session tracking
Pros: Each request is independent
Cons: No conversation memory
Decision: Correct for a stateless demo.

## What makes this production-ready (without being bloated)

✅ **Error handling** — Try/except with logging, HTTP error codes
✅ **Rate limiting** — Prevents abuse
✅ **Logging** — Debug-friendly output
✅ **Tool validation** — Each tool has error handling
✅ **Code organization** — Clear separation of concerns
✅ **No magic** — Explicit is better than implicit

What's NOT in here (but would be in production):
- ❌ Authentication (would be added to server.py)
- ❌ Database (would be added separately)
- ❌ Monitoring/metrics (would be added to server.py)
- ❌ Tests (important but not for portfolio MVP)

## What I'd add next (if continuing)

1. **True streaming** — Server-Sent Events for word-by-word responses
2. **Real Workday API** — Swap workday_api.py for real HTTP calls
3. **Conversation persistence** — Redis + sessions
4. **User authentication** — OAuth2 + session management
5. **Analytics** — Track tool usage, error rates, response times
6. **Tests** — Unit tests for tools, integration tests for agent

But for a portfolio project: **done**. The core concept is visible and the architecture is sound.

## Key insights

### 1. Tool calling is simple
Model gets: `[conversation, tool_schemas]`
Model returns: `{"role": "assistant", "tool_calls": [...]}`
You execute: the tools
You send back: `{"role": "tool", "content": json.dumps(result)}`
Loop until: `tool_calls` is empty

That's it. No magic.

### 2. Frameworks hide this
LangChain does the loop for you. But you can't see it, debug it, or change it.
Building it explicitly takes 130 lines but teaches you what actually happens.

### 3. Separation of concerns matters
- Agent doesn't know about HTTP
- Server doesn't know about tool logic
- Tools don't know about the agent

Each can be tested/debugged/replaced independently.

## For future reference

If you build another agent:
- Start with the explicit loop (this project)
- Add only what you need (persistence? auth? streaming?)
- Use frameworks **after** understanding the pattern
- Prefer explicit over magic

The time spent building this explicitly saves debugging time later.
