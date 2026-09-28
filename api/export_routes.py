"""POST /portal/export/pdf -- the rows a person is looking at, as the server-built PDF.

It renders only what the caller already holds (the explorer or builder result on their
screen), so it reads no data; a signed-in reader is still required, and the size is capped.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field

from api.auth.dependencies import AuthContext, get_auth_context
from api.report_schedules import rows_to_pdf

router = APIRouter(prefix="/portal/export", tags=["export"])

MAX_EXPORT_ROWS = 5000


class PdfExportRequest(BaseModel):
    title: str = Field(default="Report", max_length=200)
    note: str = Field(default="", max_length=400)
    columns: list[str] = Field(min_length=1, max_length=60)
    labels: dict[str, str] = Field(default_factory=dict)
    rows: list[dict[str, Any]] = Field(max_length=MAX_EXPORT_ROWS)
    chart: bool = True


@router.post("/pdf")
def export_pdf(body: PdfExportRequest, ctx: AuthContext = Depends(get_auth_context)) -> Response:
    ctx.require_permission("portal:read")
    now = datetime.now(timezone.utc)
    data = rows_to_pdf(body.title, body.note, body.columns, body.labels, body.rows, now, chart=body.chart)
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", body.title)[:60] or "report"
    return Response(content=data, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{name}_{now:%Y-%m-%d}.pdf"'})
