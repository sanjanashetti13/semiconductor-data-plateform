"""Build safe chart specs from executed SQL results (never invents data)."""

from __future__ import annotations

import re
from typing import Any

_VIZ_HINT = re.compile(
    r"\b("
    r"show|chart|graph|plot|visuali[sz]e|trend|over\s+time|"
    r"by\s+month|by\s+day|by\s+year|compare|comparison|versus|vs\.?|"
    r"breakdown|distribution|ranking"
    r")\b",
    re.I,
)

_SCALAR_ONLY = re.compile(
    r"\b(what\s+is\s+the\s+(overall\s+)?(average\s+)?yield|how\s+many|"
    r"what\s+is\s+the\s+total)\b",
    re.I,
)


def wants_visualization(question: str, *, row_count: int, column_count: int) -> bool:
    """True when a chart adds value beyond a short text/table answer."""
    q = question or ""
    if row_count <= 0 or column_count < 2:
        return False
    if row_count == 1 and column_count <= 2 and _SCALAR_ONLY.search(q):
        return False
    if _VIZ_HINT.search(q):
        return True
    # Multi-row label/value series (e.g. monthly yield, sensor averages as rows)
    if row_count >= 2 and column_count >= 2:
        return True
    # Wide single-row multi-metric (sensor_000..sensor_007 averages)
    if row_count == 1 and column_count >= 3:
        return True
    return False


def build_visualization(
    question: str,
    columns: list[str],
    rows: list[tuple],
    *,
    title: str | None = None,
) -> dict[str, Any] | None:
    """
    Return a JSON-serializable visualization spec from real query rows.

    Returns None when a chart is not appropriate or data cannot be mapped safely.
    """
    if not columns or not rows:
        return None
    if not wants_visualization(question, row_count=len(rows), column_count=len(columns)):
        return None

    chart_type = _infer_type(question)
    chart_title = title or _infer_title(question)

    # Wide single row: columns are series labels, values are cells
    if len(rows) == 1 and len(columns) >= 3:
        data = []
        for col, val in zip(columns, rows[0], strict=False):
            num = _as_number(val)
            if num is None:
                continue
            data.append({"label": str(col), "value": num})
        if len(data) < 2:
            return None
        return {
            "type": chart_type if chart_type != "line" else "bar",
            "title": chart_title,
            "xAxis": "Category",
            "yAxis": "Value",
            "data": data[:40],
        }

    # Multi-row: first non-numeric-ish col = label, first numeric = value
    label_idx, value_idx = _pick_axes(columns, rows)
    if label_idx is None or value_idx is None:
        return None

    data = []
    for row in rows[:40]:
        if label_idx >= len(row) or value_idx >= len(row):
            continue
        num = _as_number(row[value_idx])
        if num is None:
            continue
        label = row[label_idx]
        data.append(
            {
                "label": str(label) if label is not None else "",
                "value": num,
            }
        )
    if len(data) < 2:
        return None

    return {
        "type": chart_type,
        "title": chart_title,
        "xAxis": str(columns[label_idx]),
        "yAxis": str(columns[value_idx]),
        "data": data,
    }


def _infer_type(question: str) -> str:
    q = (question or "").lower()
    if any(k in q for k in ("over time", "trend", "by month", "by day", "monthly", "daily")):
        return "line"
    if any(k in q for k in ("compare", "versus", "vs", "passed", "failed")):
        return "bar"
    return "bar"


def _infer_title(question: str) -> str:
    cleaned = re.sub(r"\s+", " ", (question or "").strip())
    if len(cleaned) > 80:
        return cleaned[:77] + "..."
    return cleaned or "Query results"


def _as_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        text = str(value).strip().replace(",", "")
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def _pick_axes(columns: list[str], rows: list[tuple]) -> tuple[int | None, int | None]:
    if not columns or not rows:
        return None, None
    numeric_scores = [0] * len(columns)
    for row in rows[:20]:
        for i, cell in enumerate(row):
            if i < len(numeric_scores) and _as_number(cell) is not None:
                numeric_scores[i] += 1

    value_idx = max(range(len(columns)), key=lambda i: numeric_scores[i], default=None)
    if value_idx is None or numeric_scores[value_idx] == 0:
        return None, None

    label_idx = next((i for i in range(len(columns)) if i != value_idx), None)
    # Prefer a less-numeric column as label
    for i, score in enumerate(numeric_scores):
        if i != value_idx and score < numeric_scores[value_idx]:
            label_idx = i
            break
    return label_idx, value_idx
