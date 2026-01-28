"""
Audit Trail Tool - Visualization of agent decisions and outcomes.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastmcp import FastMCP


def get_storage_path() -> Path:
    """Get the base storage path from environment or default."""
    # Try to find the .hive directory
    # Default is ~/.hive/storage
    home = Path.home()
    return home / ".hive" / "storage"

def list_agents() -> list[str]:
    """List available agents in storage."""
    base_path = get_storage_path()
    if not base_path.exists():
        return []

    return [d.name for d in base_path.iterdir() if d.is_dir()]

def get_latest_run_id(agent_name: str) -> str | None:
    """Get the ID of the latest run for an agent."""
    base_path = get_storage_path()
    runs_dir = base_path / agent_name / "runs"

    if not runs_dir.exists():
        return None

    runs = list(runs_dir.glob("*.json"))
    if not runs:
        return None

    # Sort by modification time (latest first)
    runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return runs[0].stem

def load_run(agent_name: str, run_id: str) -> dict[str, Any]:
    """Load run data from storage."""
    base_path = get_storage_path()
    run_file = base_path / agent_name / "runs" / f"{run_id}.json"

    if not run_file.exists():
        raise ValueError(f"Run {run_id} not found for agent {agent_name}")

    with open(run_file) as f:
        return json.load(f)

def format_timeline(run_data: dict[str, Any]) -> str:
    """Format a run as a markdown timeline."""
    lines = []

    # Header
    run_id = run_data.get("id", "Unknown")
    status = run_data.get("status", "unknown")
    goal = run_data.get("goal_description", "No goal description")
    started = run_data.get("started_at", "")

    lines.append(f"# Audit Trail: Run {run_id}")
    lines.append(f"**Status**: {status.upper()}")
    lines.append(f"**Goal**: {goal}")
    lines.append(f"**Started**: {started}")
    lines.append("")
    lines.append("## Timeline")
    lines.append("")

    # Combine decisions and problems into a timeline
    # Note: decisions usually have timestamps implicitly via ordering?
    # The schema doesn't show explicit timestamp on Decision, only on Run (started_at).
    # However, decisions are ordered in the list.

    decisions = run_data.get("decisions", [])
    problems = run_data.get("problems", [])

    # Simple sequential rendering
    for i, dec in enumerate(decisions, 1):
        node_id = dec.get("node_id", "unknown")
        intent = dec.get("intent", "No intent")
        chosen = dec.get("chosen_option_id", "")
        outcome = dec.get("outcome", {})

        # Icon based on success
        success = outcome.get("success", False) if outcome else False
        icon = "✅" if success else "❌"

        lines.append(f"### {i}. Node: `{node_id}` {icon}")
        lines.append(f"**Intent**: {intent}")
        lines.append(f"**Decision**: Chosen option `{chosen}`")

        if dec.get("reasoning"):
            lines.append(f"**Reasoning**: {dec['reasoning']}")

        if outcome:
            summary = outcome.get("summary", "")
            result = outcome.get("result")
            error = outcome.get("error")

            if summary:
                lines.append(f"**Outcome**: {summary}")

            if error:
                lines.append(f"**Error**: {error}")

            if result:
                # Truncate result if too long
                res_str = str(result)
                if len(res_str) > 200:
                    res_str = res_str[:200] + "..."
                lines.append(f"**Result**: `{res_str}`")

            metrics = []
            if outcome.get("tokens_used"):
                metrics.append(f"{outcome['tokens_used']} tokens")
            if outcome.get("latency_ms"):
                metrics.append(f"{outcome['latency_ms']}ms")

            if metrics:
                lines.append(f"_{', '.join(metrics)}_")

        lines.append("")

    # Add problems section if any
    if problems:
        lines.append("## Problems Encountered")
        for prob in problems:
            severity = prob.get("severity", "minor")
            desc = prob.get("description", "")
            icon = "🔴" if severity == "critical" else "Dg" if severity == "warning" else "⚪"
            lines.append(f"- {icon} **{severity.upper()}**: {desc}")

    return "\n".join(lines)


def get_audit_trail(agent_name: str, run_id: str | None = "latest") -> str:
    """
    Get a human-readable audit trail for an agent execution.

    Args:
        agent_name: Name of the agent (folder name in storage)
        run_id: ID of the run to audit, or "latest"
    """
    try:
        # Resolve latest
        if run_id == "latest" or run_id is None:
            run_id = get_latest_run_id(agent_name)
            if not run_id:
                return f"No runs found for agent '{agent_name}'."

        data = load_run(agent_name, run_id)
        return format_timeline(data)

    except Exception as e:
        return f"Error analyzing audit trail: {str(e)}"

def list_agent_runs(agent_name: str) -> str:
    """List all available runs for an agent."""
    try:
        base_path = get_storage_path()
        runs_dir = base_path / agent_name / "runs"

        if not runs_dir.exists():
            return f"No runs found for agent '{agent_name}'"

        runs_files = list(runs_dir.glob("*.json"))
        # Sort by mtime
        runs_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        lines = [f"# Runs for {agent_name}", ""]
        for p in runs_files:
            # Need to read basic info? Or just list IDs
            run_id = p.stem
            mod_time = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"- **{run_id}**: {mod_time}")

        return "\n".join(lines)

    except Exception as e:
        return f"Error listing runs: {str(e)}"


def register_tools(mcp: FastMCP, credentials: Any | None = None) -> None:
    """Register audit trail tools."""

    mcp.tool(
        name="get_audit_trail",
        description="Get a timeline of decisions and outcomes for an agent run",
    )(get_audit_trail)

    mcp.tool(
        name="list_agent_runs",
        description="List all past execution runs for an agent",
    )(list_agent_runs)
