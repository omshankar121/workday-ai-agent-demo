"""
agent.py

A pure-Python AI agent (no LangChain) that answers HR/Workday-style
questions using tool calling against a mock Workday API.

Requires a GROQ_API_KEY in a .env file (see .env.example).
"""

import os
import sys
import json
import logging

from dotenv import load_dotenv
from groq import Groq

from tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS

load_dotenv()

# Configuration from environment
API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-oss-120b")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Setup logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

if not API_KEY:
    print("ERROR: Set GROQ_API_KEY in a .env file (copy .env.example to .env first).")
    sys.exit(1)

client = Groq(api_key=API_KEY, timeout=API_TIMEOUT)

SYSTEM_PROMPT = """You are an HR Assistant Agent for a fictional company. You help employees
with HR questions using tools like looking up employee info, PTO balances, org
structure, expense reports, and HR policies.

Response style:
- Answer naturally without markdown formatting (no **, --, ##, etc.)
- Use simple text with line breaks for readability
- For numeric data, just state it plainly: "You have 12 PTO days available"
- For lists or structured data, use simple line-separated format, not markdown
- Keep answers concise and directly from tool results

Rules:
- If the user refers to a person by name, use find_employee_by_name first to
  get their employee_id before calling other tools.
- If a lookup returns an error or multiple candidates, ask to clarify.
- If a user identifies themselves in conversation (e.g., "I'm Om Shankar"),
  remember that and use it for subsequent queries in the same conversation.
- Never invent numbers or statuses — only use what tools return.
"""


def call_tool(tool_name: str, tool_input: dict) -> dict:
    """Execute a tool and return the result."""
    if tool_name not in TOOL_FUNCTIONS:
        msg = f"Unknown tool '{tool_name}'."
        logger.error(msg)
        return {"error": msg}

    try:
        logger.debug(f"Calling tool {tool_name} with input: {tool_input}")
        result = TOOL_FUNCTIONS[tool_name](tool_input)
        logger.debug(f"Tool {tool_name} returned: {result}")
        return result
    except KeyError as e:
        msg = f"Tool '{tool_name}' missing required parameter: {e}"
        logger.error(msg)
        return {"error": msg}
    except ValueError as e:
        msg = f"Tool '{tool_name}' validation error: {e}"
        logger.warning(msg)
        return {"error": msg}
    except Exception as exc:
        msg = f"Tool '{tool_name}' failed: {str(exc)}"
        logger.exception(msg)
        return {"error": msg}


def run_turn(messages: list) -> tuple[list, list]:
    """The core loop: ask model, execute tools it requests, repeat til we get an answer."""

    trace = []
    while True:
        # Ask the model (with tools available + full history)
        response = client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=1024,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )
        message = response.choices[0].message

        # Convert response to plain dict (SDK adds fields we don't want in next request)
        assistant_turn = {"role": "assistant", "content": message.content or ""}
        if message.tool_calls:
            assistant_turn["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in message.tool_calls
            ]
        messages.append(assistant_turn)

        # No tools? We're done - model has its answer
        if not message.tool_calls:
            return messages, trace

        # Execute each tool
        for tc in message.tool_calls:
            try:
                tool_input = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                tool_input = None
                result = {"error": f"Bad JSON args: {tc.function.arguments!r}"}
            else:
                result = call_tool(tc.function.name, tool_input)

            trace.append({"name": tc.function.name, "input": tool_input, "result": result})

            # Feed result back to model (by tool_call_id)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                }
            )


def main():
    """Interactive CLI - ask questions, get answers."""
    print("HR Assistant Agent (remembers last 10 messages)\n")

    # Keep conversation history (memory)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    MAX_MEMORY = 10  # Keep last 10 messages

    while True:
        # Get user input
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        # Exit if user wants to quit
        if question.lower() in {"exit", "quit"}:
            break

        # Skip empty input
        if not question:
            continue

        # Add user message to history
        messages.append({"role": "user", "content": question})

        # Run agent with full conversation history
        messages, trace = run_turn(messages)

        # Get and print agent's answer
        answer = messages[-1]["content"]
        print(f"\nAgent: {answer}\n")

        # Show what tools were called
        if trace:
            print(f"→ Used {len(trace)} tool(s)\n")

        # Keep only last 10 messages + system prompt
        # (prevents memory from growing too large)
        if len(messages) > MAX_MEMORY + 1:
            messages = [messages[0]] + messages[-(MAX_MEMORY):]


if __name__ == "__main__":
    main()


