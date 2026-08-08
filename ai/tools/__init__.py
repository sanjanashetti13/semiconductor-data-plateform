"""Analytics and knowledge tools package.

Register new tools in TOOL_REGISTRY only so the router and copilot discover them
without changing orchestration code beyond registration.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypedDict

from . import (
    best_month,
    knowledge,
    monthly_yield,
    overall_summary,
    recommendations,
    sensor_comparison,
    worst_month,
)


class ToolResult(TypedDict):
    """Structured output returned by every analytics tool."""

    tool: str
    columns: list[str]
    rows: list[tuple]
    data: str


ToolFn = Callable[..., dict]

TOOL_REGISTRY: dict[str, ToolFn] = {
    "knowledge": knowledge.run,
    "overall_summary": overall_summary.run,
    "monthly_yield": monthly_yield.run,
    "sensor_comparison": sensor_comparison.run,
    "best_month": best_month.run,
    "worst_month": worst_month.run,
    "recommendations": recommendations.run,
}

TOOL_DESCRIPTIONS: dict[str, str] = {
    "knowledge": (
        "project/domain knowledge: SECOM dataset, wafers, sensors, pass/fail, yield, "
        "Azure SQL, Databricks, Power BI, architecture, how the copilot works "
        "(no live SQL metrics)"
    ),
    "overall_summary": "live SQL overall production summary (total wafers, pass/fail, yield)",
    "monthly_yield": "live SQL monthly yield breakdown across production months",
    "sensor_comparison": "live SQL compare sensor_160 and sensor_162 for pass vs fail",
    "best_month": "live SQL which month had the highest yield",
    "worst_month": "live SQL which month had the lowest yield",
    "recommendations": "live SQL metrics plus actionable manufacturing recommendations",
}

TOOL_DATA_SOURCES: dict[str, str] = {
    "knowledge": "Project Knowledge Base",
    "overall_summary": "Azure SQL · fact_sensor_readings",
    "monthly_yield": "Azure SQL · fact_sensor_readings",
    "sensor_comparison": "Azure SQL · fact_sensor_readings",
    "best_month": "Azure SQL · fact_sensor_readings",
    "worst_month": "Azure SQL · fact_sensor_readings",
    "recommendations": "Azure SQL · fact_sensor_readings",
}

TOOL_NAMES: set[str] = set(TOOL_REGISTRY.keys())


def get_tool(name: str) -> ToolFn:
    """Look up a registered tool by name."""
    try:
        return TOOL_REGISTRY[name]
    except KeyError as exc:
        raise KeyError(
            f"Tool {name!r} is not registered. Available: {sorted(TOOL_NAMES)}"
        ) from exc


def tool_catalog() -> str:
    """Build a bullet list of registered tools for the router prompt."""
    return "\n".join(
        f"- {name}: {TOOL_DESCRIPTIONS.get(name, name)}"
        for name in sorted(TOOL_REGISTRY)
    )


def run_tool(name: str, question: str = "") -> dict:
    """Execute a tool, passing the question only where supported."""
    tool = get_tool(name)
    if name == "knowledge":
        return tool(question)
    return tool()
