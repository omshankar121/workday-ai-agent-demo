"""
server.py

HTTP wrapper around the tool-calling agent (agent.py).

Design:
- Agent loop (agent.py) is framework-agnostic and standalone
- Server (this file) handles only HTTP concerns (rate limiting, CORS, errors)
- They're completely separated — agent doesn't know about HTTP

Could easily replace FastAPI with Flask/Django/etc without touching agent.py
"""

import os
import uuid
import logging
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from agent import SYSTEM_PROMPT, run_turn, logger

app = FastAPI(title="Workday HR Assistant Agent")

# Rate limiting: prevent abuse by limiting requests per IP
RATE_LIMIT = os.getenv("RATE_LIMIT", "10/minute")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# CORS: allow browser requests from any origin (fine for demo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info(f"Rate limit: {RATE_LIMIT}")


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    trace: list
    timestamp: str


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."},
    )


@app.post("/api/chat", response_model=ChatResponse)
@limiter.limit(RATE_LIMIT)
def chat(request: Request, req: ChatRequest):
    """Chat endpoint: stateless request that runs the agent once.

    Each request gets a fresh session with SYSTEM_PROMPT. The agent processes
    the user message and returns a final answer (no conversation memory between
    requests — that's a feature you'd add with a database).

    Returns:
    - session_id: unique ID for this request
    - reply: agent's final answer
    - trace: list of tool calls made (for UI visibility)
    - timestamp: when response was generated
    """
    try:
        # Generate a unique session_id for this request (for logging/tracing)
        session_id = req.session_id or str(uuid.uuid4())

        # Start fresh conversation with system prompt
        # (In production with memory: would load previous messages from DB)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        logger.info(f"[{session_id}] User: {req.message[:50]}...")

        # Add user message and run the agent loop
        messages.append({"role": "user", "content": req.message})
        messages, trace = run_turn(messages)

        # Extract the agent's final answer (last assistant message)
        reply = ""
        for msg in reversed(messages):
            if msg["role"] == "assistant":
                reply = msg["content"]
                break

        logger.info(f"[{session_id}] Agent replied with {len(trace)} tool calls")

        return ChatResponse(
            session_id=session_id,
            reply=reply,
            trace=trace,
            timestamp=datetime.utcnow().isoformat(),
        )

    except ValueError as e:
        # Bad input (e.g., missing required field)
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception as e:
        # Unexpected error (log full traceback for debugging)
        logger.exception(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="An error occurred. Please try again.")


@app.get("/api/health")
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/")
def index():
    """Serve the main UI."""
    return FileResponse("static/index.html")


# Static files (CSS, JS, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
