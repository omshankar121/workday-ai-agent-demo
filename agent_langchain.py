"""
agent_langchain.py - LangChain Version

Tool-calling agent using LangChain framework.
Compare with agent.py (explicit loop version) to see the difference.

Key differences:
- Uses LangChain's AgentExecutor instead of manual loop
- Simpler code (50 vs 180 lines)
- Less visibility into what's happening
- Framework handles tool calling automatically
"""

import os
import logging
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_groq import ChatGroq
from tools_langchain import tools

load_dotenv()

# Configuration
API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-oss-120b")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Setup logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an HR Assistant Agent for a fictional company, built on top of
Workday-style employee data. You can look up employees, PTO balances, org
structure, expense report status, and HR policy.

Rules:
- If the user refers to a person by name, use find_employee_by_name first to
  get their employee_id before calling other tools.
- If a lookup returns an error or multiple candidates, ask the user to
  clarify rather than guessing.
- IMPORTANT: If you can't find someone in the database BUT they've already
  told you about themselves earlier in THIS conversation (e.g., "I'm Om Shankar
  from Bangalore"), remember and use that information instead of asking again.
- Keep answers concise and specific to the data returned by tools -- do not
  invent numbers, statuses, or policy details that didn't come from a tool
  or from the conversation.
"""

# LangChain 1.x builds agents on LangGraph - create_agent wires up the
# tool-calling loop for us (this replaces our manual while-loop in agent.py)
llm = ChatGroq(model=MODEL_NAME, api_key=API_KEY, temperature=0)
agent = create_agent(llm, tools, system_prompt=SYSTEM_PROMPT)


def run_turn(messages: list) -> tuple[list, list]:
    """Run agent using LangChain's create_agent (LangGraph under the hood)."""
    try:
        # create_agent expects {"messages": [...]}, and returns the full
        # updated message list (including tool calls) under the same key
        result = agent.invoke({"messages": messages})
        return result["messages"], []

    except Exception as e:
        logger.error(f"Error: {e}")
        return messages, []


def main():
    """Interactive CLI - ask questions, get answers."""
    print("HR Assistant Agent (LangChain, remembers last 10 messages)\n")

    # Keep conversation history (memory) - system prompt is passed to
    # create_agent() separately, so it's not included here
    messages = []
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
        messages, _ = run_turn(messages)

        # Print the agent's answer (last message in the returned list)
        answer = messages[-1].content if hasattr(messages[-1], "content") else messages[-1]["content"]
        print(f"\nAgent: {answer}\n")

        # Keep only last 10 messages (prevents memory from growing too large)
        if len(messages) > MAX_MEMORY:
            messages = messages[-MAX_MEMORY:]


if __name__ == "__main__":
    main()
