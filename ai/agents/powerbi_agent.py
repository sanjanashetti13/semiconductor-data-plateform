"""Power BI Agent — dashboard integration helpers (never recreates Power BI)."""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlparse

from ai.agents.base import AgentResult, OrchestratorRequest
from ai.registry import register

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"https?://[^\s]+", re.I)


@register("powerbi")
def run(goal: str, request: OrchestratorRequest, bag: dict[str, Any]) -> AgentResult:
    """Explain Power BI purpose, validate URL if provided, suggest viz types."""
    question = (bag.get("resolved_question") or request.question).strip()
    url = request.power_bi_url or _extract_url(question)

    valid = None
    validation_note = "No dashboard URL provided in this request."
    if url:
        valid, validation_note = _validate_url(url)

    suggestions = [
        "Monthly yield trend line chart",
        "Pass vs fail stacked column by month",
        "Sensor 160 / 162 pass-vs-fail comparison",
        "Overall KPI cards (total wafers, yield %)",
    ]

    lines = [
        "## Power BI Integration",
        "",
        "This platform does **not** recreate Power BI. It links to your published "
        "Azure Power BI dashboard for executive visualization while the AI Copilot "
        "answers conversational analytics questions.",
        "",
        "### Dashboard purpose",
        "- Monitor manufacturing yield and quality outcomes",
        "- Share curated gold-layer metrics from Azure SQL with stakeholders",
        "- Complement the AI Copilot with interactive visuals",
        "",
        "### Suggested visualizations",
        *[f"- {s}" for s in suggestions],
        "",
        "### URL validation",
        validation_note,
    ]
    if url and valid:
        lines.append(f"- Connected URL host: `{urlparse(url).netloc}`")

    return AgentResult(
        agent="powerbi",
        success=True,
        summary="\n".join(lines),
        data={"url": url, "valid": valid, "suggestions": suggestions},
        meta={"goal": goal, "data_source": "Power BI (external)"},
    )


def _extract_url(text: str) -> str | None:
    match = _URL_RE.search(text or "")
    return match.group(0).rstrip(").,]") if match else None


def _validate_url(url: str) -> tuple[bool, str]:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return False, "URL must be an http(s) link with a host."
        host = parsed.netloc.lower()
        if "aaaaaaaa" in url.lower() or "00000000-0000" in url.lower():
            return False, "That looks like a placeholder report URL — paste a real Power BI share/embed link."
        if parsed.path in ("", "/") and "report" not in url.lower():
            return False, "Paste a specific report link, not the Power BI home page."
        if "powerbi.com" in host or "app.powerbi.com" in host or "analysis.windows.net" in host:
            return True, "URL looks like a Microsoft Power BI / Fabric report link."
        return True, (
            "URL is syntactically valid. Open it from the Power BI page in the app "
            "to confirm it loads your published report."
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Power BI URL validation error: %s", exc)
        return False, "Could not validate that URL."
