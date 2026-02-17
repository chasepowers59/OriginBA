"""
Minimal FastAPI server for Natural Language Query (NLQ).
POST /nlq with body {"query": "..."} or GET /nlq?query=... (for Jaspersoft JSONQL).
Returns {"narrative": "...", "metrics": {...}, "acct_id": ...}.

API key: Set NLQ_API_KEY in .env; then send header X-API-Key: <value> on /nlq requests.
If NLQ_API_KEY is not set, /nlq is unauthenticated (for local dev only).

Run from repo root: uvicorn api.nlq_server:app --reload
"""

import os
import sys
from pathlib import Path

# Add project root and pipeline so we can import pipeline.nlq
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel

app = FastAPI(title="Origin BA NLQ API", description="Natural language query for utility data (RAG).")


def _require_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> None:
    """If NLQ_API_KEY is set in env, require X-API-Key header to match; otherwise allow."""
    expected = os.getenv("NLQ_API_KEY")
    if not expected:
        return
    if not x_api_key or x_api_key.strip() != expected.strip():
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key header.")


class NLQRequest(BaseModel):
    query: str


class NLQResponse(BaseModel):
    narrative: str
    acct_id: int | None = None
    metrics: dict | None = None
    resolved_from: str | None = None


def _run_nlq_and_return(query: str) -> NLQResponse:
    from pipeline.nlq import run_nlq
    result = run_nlq(query.strip())
    return NLQResponse(
        narrative=result["narrative"],
        acct_id=result.get("acct_id"),
        metrics=result.get("metrics"),
        resolved_from=result.get("resolved_from"),
    )


@app.post("/nlq", response_model=NLQResponse)
def nlq_post(req: NLQRequest, _: None = Depends(_require_api_key)) -> NLQResponse:
    """Run the RAG pipeline on the user's natural language question (POST body)."""
    try:
        return _run_nlq_and_return(req.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/nlq", response_model=NLQResponse)
def nlq_get(query: str = "", _: None = Depends(_require_api_key)) -> NLQResponse:
    """Run the RAG pipeline (GET). For Jaspersoft JSONQL: use URL with query param."""
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Missing query parameter.")
    try:
        return _run_nlq_and_return(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
