"""The Agent Library and Router.

A registry of specialist AI agents, each with a department, role, and a system
prompt. The Agent Router selects the right specialists for a task. Every agent
inherits the same non-negotiable guardrails (the Prime Directive, brand safety,
originality, anti-fabrication) — those are prepended to every system prompt so no
agent can be prompted out of the values.
"""

from invisable_os.agents.registry import (
    AGENT_REGISTRY,
    TEAM_ORDER,
    Agent,
    Department,
    Team,
    by_team,
    get_agent,
    pipeline,
    route,
    system_prompt_for,
)

__all__ = [
    "AGENT_REGISTRY",
    "TEAM_ORDER",
    "Agent",
    "Department",
    "Team",
    "by_team",
    "get_agent",
    "pipeline",
    "route",
    "system_prompt_for",
]
