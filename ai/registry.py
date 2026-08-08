"""Agent registry — single place to resolve specialized agents by name."""

from __future__ import annotations

from typing import Callable

from ai.agents.base import AgentResult, OrchestratorRequest

AgentFn = Callable[[str, OrchestratorRequest, dict], AgentResult]

_REGISTRY: dict[str, AgentFn] = {}


def register(name: str, fn: AgentFn) -> AgentFn:
    _REGISTRY[name] = fn
    return fn


def get_agent(name: str) -> AgentFn:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown agent: {name}. Available: {sorted(_REGISTRY)}")
    return _REGISTRY[name]


def list_agents() -> list[str]:
    return sorted(_REGISTRY)


def ensure_registered() -> None:
    """Import agent modules so @register / side-effect registration runs."""
    # Local imports avoid circulars at package import time.
    from ai.agents import (  # noqa: F401
        analytics_agent,
        database_agent,
        knowledge_agent,
        ml_agent,
        planner_agent,
        powerbi_agent,
        recommendation_agent,
        schema_agent,
    )
