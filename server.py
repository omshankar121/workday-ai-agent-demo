"""
server.py - HTTP wrapper for the agent.

Keeps agent logic separate from HTTP stuff. Easy to swap FastAPI for Flask later.
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

# Session memory: stores conversation history by session_id
# (keeps last 10 messages to avoid memory bloat)
sessions = {}


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
    """Process a chat message through the agent with session memory."""
    try:
        session_id = req.session_id or str(uuid.uuid4())

        # Get or create session with system prompt
        if session_id not in sessions:
            sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

        messages = sessions[session_id]
        logger.info(f"[{session_id}] User: {req.message[:50]}...")

        # Add user message and run agent with full conversation history
        messages.append({"role": "user", "content": req.message})
        messages, trace = run_turn(messages)

        # Keep only last 10 messages + system prompt (prevent memory bloat)
        if len(messages) > 11:
            messages = [messages[0]] + messages[-10:]
        sessions[session_id] = messages

        # Extract agent's reply
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
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception as e:
        logger.exception(f"Error: {e}")
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

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
