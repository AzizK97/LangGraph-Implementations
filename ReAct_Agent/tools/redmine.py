import os
import requests
from datetime import date
from langchain_core.tools import tool

def _get(endpoint: str, params: dict = {}) -> dict:
    """Base HTTP GET helper."""
    redmine_url = os.getenv("REDMINE_URL", "http://localhost:3000")
    api_key = os.getenv("REDMINE_API_KEY", "")

    headers = {
        "X-Redmine-API-Key": api_key,
        "Content-Type": "application/json"
    }

    response = requests.get(
        f"{redmine_url}{endpoint}",
        headers=headers,
        params=params
    )
    response.raise_for_status()
    return response.json()


@tool
def get_issues(
    project_id: str,
    status_id: str = "open",
    priority_id: str = None,
    assigned_to_id: str = None,
    due_before: str = None,
    version_id: str = None,
    limit: int = 50
) -> dict:
    """
    Retrieve Redmine issues with dynamic filters.
    Use this tool for any question about tasks, their status,
    assignees, priorities, or deadlines.

    Args:
        project_id: Project identifier (e.g. 'ai-chatbot-platform')
        status_id: 'open', 'closed', or '*' for all statuses
        priority_id: '3'=low, '4'=normal, '5'=high, '6'=urgent
        assigned_to_id: Numeric user ID of the assignee
        due_before: Date string YYYY-MM-DD — returns overdue tasks
        version_id: Numeric sprint/version ID
        limit: Max number of results to return
    """
    params = {
        "project_id": project_id,
        "status_id": status_id,
        "limit": limit
    }

    if priority_id:
        params["priority_id"] = priority_id
    if assigned_to_id:
        params["assigned_to_id"] = assigned_to_id
    if due_before:
        params["due_date"] = f"<={due_before}"
    if version_id:
        params["fixed_version_id"] = version_id

    data = _get("/issues.json", params)

    # Return a clean summary instead of the full raw JSON
    issues = data.get("issues", [])
    return {
        "total_count": data.get("total_count", 0),
        "issues": [
            {
                "id": i["id"],
                "subject": i["subject"],
                "status": i["status"]["name"],
                "priority": i["priority"]["name"],
                "assigned_to": i.get("assigned_to", {}).get("name", "Unassigned"),
                "due_date": i.get("due_date", "Not set"),
                "project": i["project"]["name"]
            }
            for i in issues
        ]
    }


@tool
def get_members(project_id: str) -> dict:
    """
    Retrieve all members of a Redmine project and their roles.
    Use this tool when the user asks about the team, members,
    or who is working on a project.

    Args:
        project_id: Project identifier (e.g. 'ai-chatbot-platform')
    """
    data = _get(f"/projects/{project_id}/memberships.json")

    memberships = data.get("memberships", [])
    return {
        "total_count": len(memberships),
        "members": [
            {
                "id": m["user"]["id"],
                "name": m["user"]["name"],
                "roles": [r["name"] for r in m.get("roles", [])]
            }
            for m in memberships
            if "user" in m
        ]
    }


@tool
def get_versions(project_id: str) -> dict:
    """
    Retrieve all versions (sprints) of a Redmine project with
    their due dates and status.
    Use this tool when the user asks about sprints, milestones,
    planning, or deadlines.

    Args:
        project_id: Project identifier (e.g. 'ai-chatbot-platform')
    """
    data = _get(f"/projects/{project_id}/versions.json")

    versions = data.get("versions", [])
    today = date.today().isoformat()

    return {
        "total_count": len(versions),
        "versions": [
            {
                "id": v["id"],
                "name": v["name"],
                "status": v["status"],
                "due_date": v.get("due_date", "Not set"),
                "is_overdue": (
                    v.get("due_date", "9999") < today
                    and v["status"] != "closed"
                )
            }
            for v in versions
        ]
    }


@tool
def get_projects() -> dict:
    """
    Retrieve all available Redmine projects.
    Use this tool when the user asks about available projects
    or when you need to find a project identifier.
    """
    data = _get("/projects.json", {"limit": 100})

    projects = data.get("projects", [])
    return {
        "total_count": len(projects),
        "projects": [
            {
                "id": p["id"],
                "name": p["name"],
                "identifier": p["identifier"],
                "description": p.get("description", "")
            }
            for p in projects
        ]
    }
