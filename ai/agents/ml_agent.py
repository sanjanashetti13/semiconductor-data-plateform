"""ML Agent — Random Forest failure model integration (on-demand only)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ai.agents.base import AgentResult, OrchestratorRequest
from ai.llm import chat
from ai.registry import register

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[2]
_MODEL_CANDIDATES = [
    _ROOT / "ml_outputs" / "failure_prediction_model.pkl",
    _ROOT / "models" / "failure_prediction_model.pkl",
    _ROOT / "data" / "failure_prediction_model.pkl",
]

_SYSTEM = """You are the ML Agent for Semiconductor Intelligence Hub.
Explain wafer failure prediction using the Random Forest model context provided.
If live predictions are unavailable, explain how the model works, typical features,
and how operators should use predictions — without inventing accuracy numbers.
"""


@register("ml")
def run(goal: str, request: OrchestratorRequest, bag: dict[str, Any]) -> AgentResult:
    """Integrate the existing Random Forest failure model when present."""
    question = bag.get("resolved_question") or request.question
    prior = list(bag.get("prior_summaries") or [])

    model_path = next((p for p in _MODEL_CANDIDATES if p.is_file()), None)
    ml_block = _model_block(model_path)

    try:
        answer = chat(
            [
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Goal: {goal}\nQuestion: {question}\n\n"
                        f"Model context:\n{ml_block}\n\n"
                        + (
                            "Prior agent findings:\n" + "\n---\n".join(prior[-3:]) + "\n\n"
                            if prior
                            else ""
                        )
                        + "Write the ML-focused answer."
                    ),
                },
            ],
            temperature=0.15,
        )
        return AgentResult(
            agent="ml",
            success=True,
            summary=answer.strip(),
            data={"model_path": str(model_path) if model_path else None},
            meta={
                "goal": goal,
                "model_loaded": bool(model_path),
                "data_source": "Random Forest failure model",
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("ML agent failed")
        return AgentResult(
            agent="ml",
            success=False,
            summary="ML explanation failed.",
            error=str(exc),
        )


def _model_block(model_path: Path | None) -> str:
    if model_path is None:
        return (
            "Saved model file not found in ml_outputs/. "
            "Training script: scripts/train_failure_model.py "
            "(RandomForestClassifier, n_estimators=300, class_weight=balanced) "
            "on gold_sensor_data.csv features excluding timestamp/target. "
            "Target is wafer pass/fail. Feature importance is available after training "
            "via model.feature_importances_."
        )

    try:
        import joblib

        model = joblib.load(model_path)
        lines = [
            f"Model file: {model_path.name}",
            f"Estimator: {type(model).__name__}",
        ]
        n_est = getattr(model, "n_estimators", None)
        if n_est is not None:
            lines.append(f"Trees: {n_est}")
        importances = getattr(model, "feature_importances_", None)
        feature_names = getattr(model, "feature_names_in_", None)
        if importances is not None:
            pairs: list[tuple[str, float]] = []
            for i, imp in enumerate(importances):
                name = (
                    str(feature_names[i])
                    if feature_names is not None and i < len(feature_names)
                    else f"feature_{i}"
                )
                pairs.append((name, float(imp)))
            pairs.sort(key=lambda x: x[1], reverse=True)
            top = pairs[:8]
            lines.append("Top feature importances:")
            for name, imp in top:
                lines.append(f"  - {name}: {imp:.4f}")
        lines.append(
            "Use predictions as decision support alongside process engineering review; "
            "not as sole disposition authority."
        )
        return "\n".join(lines)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load ML model: %s", exc)
        return (
            f"Model file exists at {model_path} but could not be loaded ({exc}). "
            "Explain Random Forest wafer failure prediction conceptually."
        )
