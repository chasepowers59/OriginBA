"""Pattern-based snapshot analytics for natural language questions (no LLM required)."""

from __future__ import annotations

from typing import Any

from api.demo_db import demo_configured
from api.nlq_metrics import list_metric_catalog, match_metric, run_metric_nlq
from api.warehouse_db import warehouse_configured


def _org_snapshot_ids(organization_id: str | None) -> set[str]:
    """The snapshot ids this org's catalog can actually resolve."""
    from api.snapshot_catalog import load_catalog

    try:
        return set(load_catalog(organization_id=organization_id)["snapshots"].keys())
    except Exception:  # noqa: BLE001
        return set()


def run_snapshot_analytics_nlq(
    question: str,
    *,
    metric_id: str | None = None,
    params: dict[str, Any] | None = None,
    organization_id: str,
) -> dict[str, Any] | None:
    # Either backend counts — the metric's snapshot routes to whichever database
    # serves it, exactly like the dashboards.
    if not (demo_configured(organization_id) or warehouse_configured(organization_id)):
        return None
    q = (question or "").strip()
    if not q and not metric_id:
        return None
    # Never run a metric this org's catalog cannot resolve; offering it anyway just
    # errors on click.
    metric = match_metric(q, metric_id)
    if metric and metric.snapshot_id not in _org_snapshot_ids(organization_id):
        return None
    try:
        result = run_metric_nlq(q, metric_id=metric_id, params=params, organization_id=organization_id)
        if result:
            return result
    except Exception as exc:
        from api.executive_dashboard import WAREHOUSE_NOT_BUILT_NOTE, is_missing_relation_error
        # An org whose warehouse is not built yet must not print ORA-00942 into the
        # conversation; it gets the same sentence the dashboards use.
        reason = WAREHOUSE_NOT_BUILT_NOTE if is_missing_relation_error(str(exc)) else str(exc)
        return {
            "narrative": (reason if reason is WAREHOUSE_NOT_BUILT_NOTE
                          else f"Could not run snapshot analytics: {reason}"),
            "source": "snapshot_analytics",
            "resolved_from": metric_id,
        }
    return None


def get_nlq_metric_catalog(organization_id: str | None = None) -> list[dict[str, Any]]:
    """The metric catalog, restricted to snapshots this org's catalog contains."""
    metrics = list_metric_catalog()
    if organization_id is None:
        return metrics
    available = _org_snapshot_ids(organization_id)
    return [m for m in metrics if m.get("snapshot_id") in available]


def match_nlq_metric(question: str, metric_id: str | None = None) -> dict[str, Any] | None:
    metric = match_metric(question, metric_id)
    if not metric:
        return None
    return {"id": metric.id, "snapshot_id": metric.snapshot_id, "label": metric.label}
