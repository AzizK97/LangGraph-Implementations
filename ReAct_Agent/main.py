import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from tools.redmine import get_issues, get_members, get_versions, get_projects

load_dotenv()

# ── LLM Setup ─────────────────────────────────────────────────────────────────
llm = ChatOpenAI(
    model="openrouter/auto",
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    openai_api_base="https://openrouter.ai/api/v1",
    temperature=0
)

# ── Tools ─────────────────────────────────────────────────────────────────────
tools = [get_projects, get_issues, get_members, get_versions]

# ── Memory ────────────────────────────────────────────────────────────────────
memory = MemorySaver()

# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an intelligent project management assistant connected to Redmine in real time.

You have access to 4 tools:
- get_projects: retrieves the list of all available projects
- get_issues: retrieves tasks with dynamic filters
- get_members: retrieves the members of a project
- get_versions: retrieves the sprints and versions of a project

STRICT RULES:
- ALWAYS call a tool before responding — never invent data.
- If you don’t know the project identifier, first call get_projects.
- For overdue tasks: use due_before with today’s date.
- For urgent tasks: use priority_id = '6'.
- If the tool returns empty data, clearly state it.
"""

# ── Agent ─────────────────────────────────────────────────────────────────────
agent = create_agent(
    model=llm,
    tools=tools,
    checkpointer=memory,
    system_prompt=SYSTEM_PROMPT
)

# ── Conversation loop ─────────────────────────────────────────────────────────
def chat(question: str, thread_id: str = "default") -> None:
    """Send a message to the agent and stream its thought process."""
    config = {"configurable": {"thread_id": thread_id}}

    print()
    for step in agent.stream(
        {"messages": [HumanMessage(content=question)]},
        config=config,
        stream_mode="updates"
    ):
        # Each step is a dict with the node name as key
        for node_name, node_data in step.items():
            messages = node_data.get("messages", [])
            for message in messages:
                _print_message(message, node_name)


def _print_message(message, node_name: str) -> None:
    """Pretty print each message type."""
    from langchain_core.messages import AIMessage, ToolMessage

    if isinstance(message, AIMessage):
        # Check if it contains tool calls (Thought + Act)
        if message.tool_calls:
            print("─" * 50)
            print("THOUGHT")
            if message.content:
                print(f"   {message.content}")
            for tool_call in message.tool_calls:
                print(f"\nACT — calling tool: {tool_call['name']}")
                print(f"   Parameters: {tool_call['args']}")
            print()
        else:
            # Final answer
            print("─" * 50)
            print("FINAL ANSWER")
            print(f"   {message.content}")
            print("─" * 50)

    elif isinstance(message, ToolMessage):
        # Tool result (Observe)
        import json
        print("OBSERVE — tool result:")
        try:
            data = json.loads(message.content)
            print(f"   {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
            if len(message.content) > 500:
                print("   ... [truncated]")
        except Exception:
            print(f"   {message.content[:500]}")
        print()


def main():
    print("=== LangGraph ReAct Agent — Redmine ===")
    print("Type 'exit' to quit\n")

    thread_id = "session-1"

    while True:
        question = input("You : ").strip()

        if not question:
            continue
        if question.lower() == "exit":
            print("Bye !")
            break

        chat(question, thread_id)
        print()


if __name__ == "__main__":
    main()