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

SYSTEM_PROMPT = """You are an HR Assistant Agent for a fictional company, built on top of
Workday-style employee data. You can look up employees, PTO balances, org
structure, expense report status, and HR policy.

Rules:
- If the user refers to a person by name, use find_employee_by_name first to
  get their employee_id before calling other tools.
- If a lookup returns an error or multiple candidates, ask the user to
  clarify rather than guessing.
- Keep answers concise and specific to the data returned by tools -- do not
  invent numbers, statuses, or policy details that didn't come from a tool
  or from the conversation.
"""


def call_tool(tool_name: str, tool_input: dict) -> dict:
    """Execute a tool with error handling and logging.

    Returns the tool result or an error dict with context.
    """
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
    """Core tool-calling loop: ask the model, execute tools, repeat until done.

    The agent loop is:
    1. Send conversation + tool schemas to model
    2. Model returns either final answer OR tool call request
    3. Execute the tool, feed result back to model
    4. Repeat until model produces final answer

    Returns (messages, trace) where trace is a list of {"name", "input", "result"}
    dicts for each tool call (used by UI to show what the agent did).
    """

    trace = []
    while True:
        # Step 1: Ask the model (with available tools + conversation history)
        response = client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=1024,
            tools=TOOL_DEFINITIONS,  # Tell model what tools are available
            messages=messages,  # Full conversation history
        )
        message = response.choices[0].message

        # Step 2: Rebuild response as plain dict (avoid smuggling SDK-specific fields
        # into the next request, which would cause API errors)
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

        # Step 3: If no tool calls, model has produced final answer — return
        if not message.tool_calls:
            return messages, trace

        # Step 4: Execute each tool the model requested
        for tc in message.tool_calls:
            try:
                tool_input = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                tool_input = None
                result = {"error": f"Model sent malformed JSON arguments: {tc.function.arguments!r}"}
            else:
                result = call_tool(tc.function.name, tool_input)

            # Record for UI (what tool was called, with what input, what was returned)
            trace.append({"name": tc.function.name, "input": tool_input, "result": result})

            # Step 5: Feed tool result back to model (required by API)
            # The tool_call_id ties result to the request
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                }
            )
        # Loop back to Step 1: model can now use tool results to respond or call another tool


def main():
    """Interactive CLI for testing the agent directly.

    This shows how the agent works:
    1. Start with system prompt
    2. User enters a question
    3. Agent thinks, calls tools, returns answer
    4. See the full trace of what it did
    """
    print("=" * 60)
    print("HR Assistant Agent (CLI Mode)")
    print("=" * 60)
    print("\nTry these questions:")
    print('  - "How much PTO does Priya have left?"')
    print('  - "Who does Sofia Torres report to?"')
    print('  - "Submit PTO for Sept 15-19"')
    print('  - "What\'s the remote work policy?"')
    print("\nType 'exit' or 'quit' to stop.\n")

    # Start with system prompt (no conversation memory between turns)
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        # Exit commands
        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break
        if not user_input:
            continue

        # Run the agent: fresh conversation each turn (stateless)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.append({"role": "user", "content": user_input})
        messages, trace = run_turn(messages)

        # Print agent's response
        for msg in messages:
            if msg["role"] == "assistant":
                print(f"\nAgent: {msg['content']}\n")
                break

        # Show what tools were called (trace)
        if trace:
            print(f"─ Tool calls ({len(trace)}):")
            for i, call in enumerate(trace, 1):
                print(f"  {i}. {call['name']}({call['input']})")
                if "error" in call["result"]:
                    print(f"     → Error: {call['result']['error']}")
                else:
                    print(f"     → {call['result']}")
            print()


if __name__ == "__main__":
    main()


