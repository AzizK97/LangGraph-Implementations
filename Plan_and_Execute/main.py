import os
import json
from dotenv import load_dotenv
from typing_extensions import TypedDict, Annotated
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from tools.redmine import get_issues, get_members, get_versions, get_projects

load_dotenv()

# ── State ─────────────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    plan: list[dict]
    index: int
    observations: list[dict]

# ── LLM ───────────────────────────────────────────────────────────────────────
llm = ChatOpenAI(
    model="openrouter/auto",
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    openai_api_base="https://openrouter.ai/api/v1",
    temperature=0
)

# ── Tool Registry ─────────────────────────────────────────────────────────────
tools = [get_projects, get_issues, get_members, get_versions]
TOOL_REGISTRY = {tool.name: tool for tool in tools}

# ── Planner ───────────────────────────────────────────────────────────────────
PLANNER_PROMPT = """You are a planning assistant for a Redmine project management chatbot.
You have access to ONLY these tools:
- get_projects : retrieves all available projects
- get_issues   : retrieves issues with filters (project_id, status_id, priority_id, due_before, assigned_to_id)
- get_members  : retrieves members of a project
- get_versions : retrieves sprints/versions of a project

Break the user request into an ordered list of tool calls needed to answer it.

Respond ONLY with a valid JSON array of objects, like this:
[
  {"tool": "get_projects", "args": {}},
  {"tool": "get_issues", "args": {"project_id": "e-commerce-platform", "status_id": "open"}},
  {"tool": "get_members", "args": {"project_id": "e-commerce-platform"}}
]

Rules:
- Only use tool names from the list above
- Always include "tool" and "args" keys in each step
- If you don't know the project_id yet, add get_projects as the first step
- Never add steps like "parse response" or "summarize"
"""

def planner(state: AgentState) -> AgentState:
    user_message = state["messages"][-1]

    response = llm.invoke([
        ("system", PLANNER_PROMPT),
        ("human", f"User request: {user_message.content}")
    ])

    try:
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        plan = json.loads(raw.strip())
    except json.JSONDecodeError:
        plan = [{"tool": "get_projects", "args": {}}]

    return {
        "plan": plan,
        "index": 0,
        "observations": []
    }

# ── Executor ──────────────────────────────────────────────────────────────────
def executor(state: AgentState) -> AgentState:
    plan = state["plan"]
    index = state["index"]

    if index >= len(plan):
        return {"index": index}

    step = plan[index]
    tool_name = step.get("tool", "")
    tool_args = step.get("args", {})

    if tool_name in TOOL_REGISTRY:
        try:
            result = TOOL_REGISTRY[tool_name].invoke(tool_args)
        except Exception as e:
            result = {"error": str(e)}
    else:
        result = {"error": f"Unknown tool: {tool_name}"}

    previous_observations = state.get("observations", [])
    new_observation = {
        "step": index + 1,
        "tool": tool_name,
        "args": tool_args,
        "result": result
    }

    return {
        "observations": previous_observations + [new_observation],
        "index": index + 1
    }

# ── Routing ───────────────────────────────────────────────────────────────────
def should_continue(state: AgentState) -> str:
    if state["index"] < len(state["plan"]):
        return "executor"
    return "aggregator"

# ── Aggregator ────────────────────────────────────────────────────────────────
AGGREGATOR_PROMPT = """You are a project management assistant.
You have executed a series of Redmine API calls to answer the user's question.
Below are all the results collected from those calls.
Write a clear, structured, and complete answer in French based strictly on this data.
Do not invent any data — only use what is provided in the observations.
"""

def aggregator(state: AgentState) -> dict:
    observations = state.get("observations", [])
    user_question = state["messages"][0].content

    formatted_observations = ""
    for obs in observations:
        formatted_observations += f"\nStep {obs['step']} — {obs['tool']}({obs['args']}):\n"
        formatted_observations += json.dumps(obs["result"], ensure_ascii=False, indent=2)
        formatted_observations += "\n"

    response = llm.invoke([
        ("system", AGGREGATOR_PROMPT),
        ("human", f"""User question: {user_question}

Data collected from Redmine:
{formatted_observations}

Now write the final answer for the user.""")
    ])

    return {
        "messages": [response],
        "observations": observations
    }

# ── Build Graph ───────────────────────────────────────────────────────────────
builder = StateGraph(AgentState)
builder.add_node("planner", planner)
builder.add_node("executor", executor)
builder.add_node("aggregator", aggregator)

builder.set_entry_point("planner")
builder.add_edge("planner", "executor")
builder.add_conditional_edges(
    "executor",
    should_continue,
    {"executor": "executor", "aggregator": "aggregator"}
)
builder.add_edge("aggregator", END)

app = builder.compile()

# ── Chat ──────────────────────────────────────────────────────────────────────
def chat(question: str) -> None:
    try:
        result = app.invoke({
            "messages": [HumanMessage(content=question)],
            "plan": [],
            "index": 0,
            "observations": []
        })

        if result.get("messages"):
            last_message = result["messages"][-1]
            content = (
                last_message.content
                if hasattr(last_message, "content")
                else str(last_message)
            )
            print(f"\nAgent : {content}")
        else:
            print("\nAgent : No response generated.")

    except Exception as e:
        print(f"\nError: {e}")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=== LangGraph Plan-and-Execute Agent — Redmine ===")
    print("Type 'exit' to quit\n")

    while True:
        question = input("You : ").strip()

        if not question:
            continue
        if question.lower() == "exit":
            print("Bye!")
            break

        chat(question)
        print()


if __name__ == "__main__":
    main()