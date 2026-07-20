"""Pattern-based snapshot analytics for natural language questions (no LLM required)."""

from __future__ import annotations

from typing import Any

from api.demo_db import demo_configured
from api.nlq_metrics import list_metric_catalog, match_metric, run_metric_nlq


def run_snapshot_analytics_nlq(
    question: str,
    *,
    metric_id: str | None = None,
    params: dict[str, Any] | None = None,
    organization_id: str,
) -> dict[str, Any] | None:
    if not demo_configured(organization_id):
        return None
    q = (question or "").strip()
    if not q and not metric_id:
        return None
    try:
        result = run_metric_nlq(q, metric_id=metric_id, params=params, organization_id=organization_id)
        if result:
            return result
    except Exception as exc:
        return {
            "narrative": f"Could not run snapshot analytics: {exc}",
            "source": "snapshot_analytics",
            "resolved_from": metric_id,
        }
    return None


def get_nlq_metric_catalog() -> list[dict[str, Any]]:
    return list_metric_catalog()


def match_nlq_metric(question: str, metric_id: str | None = None) -> dict[str, Any] | None:
    metric = match_metric(question, metric_id)
    if not metric:
        return None
    return {"id": metric.id, "snapshot_id": metric.snapshot_id, "label": metric.label}
