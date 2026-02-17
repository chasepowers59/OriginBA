"""
Natural Language Query (NLQ) for utility data: intent extraction, entity resolution,
and RAG-based response generation. All data comes from governed SQL; no AI-generated queries.

Usage:
  python -m pipeline.nlq "What is the status of Account 2927873805?"
"""

import json
import os
import re
import sys
from pathlib import Path

# Allow running as script or module
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv

load_dotenv()

# Intent action constants (map to governed queries / workstreams)
ARREARS_SUMMARY = "ARREARS_SUMMARY"
PAYMENT_LOOKUP = "PAYMENT_LOOKUP"
PREMISE_LOOKUP = "PREMISE_LOOKUP"
ACCOUNT_STATUS = "ACCOUNT_STATUS"
# Workstream-specific intents
METER_LOOKUP = "METER_LOOKUP"
GL_LOOKUP = "GL_LOOKUP"
DEPOSIT_LOOKUP = "DEPOSIT_LOOKUP"
NEW_SERVICES_LOOKUP = "NEW_SERVICES_LOOKUP"
BILLING_LOOKUP = "BILLING_LOOKUP"
CUSTOMER_ALERTS = "CUSTOMER_ALERTS"
DEBT_MGMT_LOOKUP = "DEBT_MGMT_LOOKUP"
FIELD_OPS_LOOKUP = "FIELD_OPS_LOOKUP"

_ALL_ACTIONS = [
    ARREARS_SUMMARY, PAYMENT_LOOKUP, PREMISE_LOOKUP, ACCOUNT_STATUS,
    METER_LOOKUP, GL_LOOKUP, DEPOSIT_LOOKUP, NEW_SERVICES_LOOKUP, BILLING_LOOKUP, CUSTOMER_ALERTS,
    DEBT_MGMT_LOOKUP, FIELD_OPS_LOOKUP,
]

INTENT_EXTRACT_SYSTEM = """You are an intent classifier for a utility data assistant. Given a user question, extract structured fields. Return ONLY a JSON object with these exact keys (use null for missing):
- "action": one of "ARREARS_SUMMARY", "PAYMENT_LOOKUP", "PREMISE_LOOKUP", "ACCOUNT_STATUS", "METER_LOOKUP", "GL_LOOKUP", "DEPOSIT_LOOKUP", "NEW_SERVICES_LOOKUP", "BILLING_LOOKUP", "CUSTOMER_ALERTS", "DEBT_MGMT_LOOKUP", "FIELD_OPS_LOOKUP"
- "acct_id": numeric account ID if the user mentioned a specific account number, else null
- "address": street address or premise description if the user asked about a place (e.g. "123 Main St"), else null
- "customer_name": full name if the user asked about a person (e.g. "Olivia Powers"), else null

Use METER_LOOKUP for meter, install, installation; GL_LOOKUP for GL, distribution; DEPOSIT_LOOKUP for deposit, cashiering; NEW_SERVICES_LOOKUP for pipeline, pending; BILLING_LOOKUP for rates, bill; CUSTOMER_ALERTS for alerts; DEBT_MGMT_LOOKUP for debt, collections, credit review; FIELD_OPS_LOOKUP for field operations, service point, work order.

Examples:
- "What is the status of Account 2927873805?" -> {"action": "ACCOUNT_STATUS", "acct_id": 2927873805, "address": null, "customer_name": null}
- "When was this meter installed?" -> {"action": "METER_LOOKUP", "acct_id": null, "address": null, "customer_name": null}
- "What is the GL distribution for this deposit?" -> {"action": "GL_LOOKUP", "acct_id": null, "address": null, "customer_name": null}
- "How many payments did Olivia Powers make?" -> {"action": "PAYMENT_LOOKUP", "acct_id": null, "address": null, "customer_name": "Olivia Powers"}
Output only the JSON object, no other text."""


def _regex_acct_id(question: str) -> int | None:
    """Try to extract a numeric account ID from the question. Returns None if not found."""
    # Patterns: "Account 2927873805", "acct 2927873805", "account number 2927873805"
    patterns = [
        r"\baccount\s+(?:number\s+)?(\d{8,})\b",
        r"\bacct(?:ount)?\s+(?:#?\s*)?(\d{8,})\b",
        r"\b(\d{8,})\s*(?:account|acct)\b",
    ]
    for pat in patterns:
        m = re.search(pat, question, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                continue
    return None


def _call_llm_for_intent(question: str) -> dict:
    """Call OpenAI or Gemini to extract intent JSON. Returns dict with action, acct_id, address, customer_name."""
    if os.getenv("OPENAI_API_KEY"):
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": INTENT_EXTRACT_SYSTEM},
                {"role": "user", "content": question},
            ],
            response_format={"type": "json_object"},
        )
        text = (response.choices[0].message.content or "").strip()
    elif os.getenv("GEMINI_API_KEY"):
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        response = client.models.generate_content(
            model=model,
            contents=f"{INTENT_EXTRACT_SYSTEM}\n\nUser question: {question}",
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        text = (response.text or "").strip()
    else:
        raise ValueError("Set OPENAI_API_KEY or GEMINI_API_KEY in .env for intent extraction.")
    for prefix in ("```json\n", "```\n"):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    data = json.loads(text)
    action = data.get("action") or ACCOUNT_STATUS
    if action not in _ALL_ACTIONS:
        action = ACCOUNT_STATUS
    return {
        "action": action,
        "acct_id": data.get("acct_id"),
        "address": data.get("address"),
        "customer_name": data.get("customer_name"),
    }


# Keyword fast path: (keywords_tuple, action) pairs to trigger workstream without LLM
_WORKSTREAM_KEYWORDS = [
    # Meter Operations
    (("meter", "install", "installation", "meter number", "meter status", "reading", "last reading", 
      "device", "device type", "ami", "smart meter", "analog meter", "meter reading"), METER_LOOKUP),
    # Finance
    (("gl", "general ledger", "distribution", "gl distribution", "batch", "batch processing", 
      "reconciliation", "gl account"), GL_LOOKUP),
    # Cashiering
    (("deposit", "cashiering", "tender", "bank reconciliation", "missing deposit", "payment method", 
      "tender type", "deposit control"), DEPOSIT_LOOKUP),
    (("payment", "payments", "last payment", "paid", "payment event", "payment history"), DEPOSIT_LOOKUP),
    # New Services
    (("pipeline", "pending", "new service", "initiation", "service activation", "sa status", 
      "pending activation", "time to activation"), NEW_SERVICES_LOOKUP),
    # Billing & Rates
    (("rates", "rate schedule", "bill schedule", "billing schedule", "late fee", "rate tier", 
      "billing cycle", "bill distribution", "rate code", "rate configuration"), BILLING_LOOKUP),
    # Customer Operations
    (("customer alert", "account alert", "alerts on account", "customer class", "account class", 
      "collection class", "bill cycle"), CUSTOMER_ALERTS),
    # Debt Management
    (("debt", "collections", "credit review", "collection class", "credit review date", 
      "payment plan", "arrears management"), DEBT_MGMT_LOOKUP),
    # Field Operations (includes OCX & Field Tasks)
    (("field operations", "field ops", "service point", "work order", "sp status", 
      "service point status", "installation date", "field work", "field task", "ocx", 
      "outbound communication", "task", "tasks", "background task", "field worker"), FIELD_OPS_LOOKUP),
]


def _keyword_workstream_intent(question: str) -> str | None:
    """If question clearly mentions a workstream keyword, return the action; else None."""
    q = (question or "").lower()
    for keywords, action in _WORKSTREAM_KEYWORDS:
        for kw in keywords:
            if kw in q:
                return action
    return None


def _cross_workstream_actions(question: str) -> list[str]:
    """Return all workstream actions whose keywords appear in the question (for cross-workstream NLQ)."""
    q = (question or "").lower()
    seen = set()
    out = []
    for keywords, action in _WORKSTREAM_KEYWORDS:
        for kw in keywords:
            if kw in q and action not in seen:
                seen.add(action)
                out.append(action)
                break
    return out


def extract_intent(question: str) -> dict:
    """
    Extract intent and entities from a natural language question.
    Returns dict: action (str), acct_id (int | None), address (str | None), customer_name (str | None).
    Uses regex for account number and keywords for workstreams; falls back to LLM for full extraction.
    """
    question = (question or "").strip()
    if not question:
        return {"action": ACCOUNT_STATUS, "acct_id": None, "address": None, "customer_name": None}
    # Fast path: regex for obvious account number (keep ACCOUNT_STATUS when account given)
    acct_from_regex = _regex_acct_id(question)
    # Fast path: workstream keywords (meter, GL, deposit, pipeline, rates)
    workstream_action = _keyword_workstream_intent(question)
    if workstream_action is not None:
        return {
            "action": workstream_action,
            "acct_id": acct_from_regex,
            "address": None,
            "customer_name": None,
        }
    if acct_from_regex is not None:
        return {
            "action": ACCOUNT_STATUS,
            "acct_id": acct_from_regex,
            "address": None,
            "customer_name": None,
        }
    return _call_llm_for_intent(question)


def run_nlq(question: str) -> dict:
    """
    Run the full RAG pipeline: intent -> resolve to acct_id -> fetch slice -> generate narrative.
    Routes by action: workstream-specific intents call the corresponding fetch_*_slice; legacy
    intents use fetch_bi_slice_for_account. Returns dict with narrative, acct_id, metrics, resolved_from.
    """
    from fetch_usage import (
        fetch_bi_slice_for_account,
        fetch_billing_slice,
        fetch_cashiering_slice,
        fetch_meter_ops_slice,
        fetch_customer_ops_slice,
        fetch_new_services_slice,
        fetch_finance_gl_slice,
        fetch_debt_mgmt_slice,
        fetch_field_ops_slice,
        fetch_field_tasks_slice,
        resolve_acct_id_from_premise,
        resolve_acct_id_from_customer_name,
        _oracle_available,
    )
    from generate_narrative import generate_nlq_response

    intent = extract_intent(question)
    action = intent.get("action", ACCOUNT_STATUS)
    acct_id = intent.get("acct_id")
    address = intent.get("address")
    customer_name = intent.get("customer_name")
    resolved_from = "acct"

    if acct_id is not None:
        acct_ids = [int(acct_id)]
    elif address:
        acct_ids = resolve_acct_id_from_premise(address)
        resolved_from = "premise"
    elif customer_name:
        acct_ids = resolve_acct_id_from_customer_name(customer_name)
        resolved_from = "name"
    else:
        acct_ids = []

    first_acct = acct_ids[0] if acct_ids else None

    # Cross-workstream: e.g. "Show me the meter status and last payment for Account X"
    cross_actions = _cross_workstream_actions(question) if first_acct else []
    if len(cross_actions) >= 2:
        # Fetch BI slice and all relevant workstream slices; merge into one metrics
        metrics = fetch_bi_slice_for_account(first_acct) if first_acct else {}
        if not isinstance(metrics, dict):
            metrics = {}
        slices = metrics.get("workstream_slices") or {}
        for a in cross_actions:
            if a == METER_LOOKUP:
                s = fetch_meter_ops_slice(acct_id=first_acct)
                if s:
                    slices["meter_ops"] = s
            elif a == GL_LOOKUP:
                s = fetch_finance_gl_slice(acct_id=first_acct)
                if s:
                    slices["finance"] = s
            elif a == DEPOSIT_LOOKUP:
                s = fetch_cashiering_slice(first_acct)
                if s:
                    slices["cashiering"] = s
            elif a == NEW_SERVICES_LOOKUP:
                s = fetch_new_services_slice(acct_id=first_acct)
                if s:
                    slices["new_services"] = s
            elif a == BILLING_LOOKUP:
                s = fetch_billing_slice(first_acct)
                if s:
                    slices["billing"] = s
            elif a == CUSTOMER_ALERTS:
                s = fetch_customer_ops_slice(first_acct)
                if s:
                    slices["customer_ops"] = s
            elif a == DEBT_MGMT_LOOKUP:
                s = fetch_debt_mgmt_slice(first_acct)
                if s:
                    slices["debt_mgmt"] = s
            elif a == FIELD_OPS_LOOKUP:
                s = fetch_field_ops_slice(first_acct)
                if s:
                    slices["field_ops"] = s
                # Also fetch OCX/field tasks (F1 metadata layer)
                s_tasks = fetch_field_tasks_slice(first_acct)
                if s_tasks:
                    slices["field_tasks"] = s_tasks
        metrics["workstream_slices"] = slices
        narrative = generate_nlq_response(question, metrics)
        return {
            "narrative": narrative,
            "acct_id": first_acct,
            "metrics": metrics,
            "resolved_from": resolved_from,
        }

    # Router: workstream-specific actions use governed SQL for that slice
    if action == METER_LOOKUP:
        slice_data = fetch_meter_ops_slice(acct_id=first_acct) if first_acct else None
        metrics = {"workstream_slices": {"meter_ops": slice_data}} if slice_data else None
        if metrics and first_acct:
            bi = fetch_bi_slice_for_account(first_acct)
            if bi:
                metrics.update(bi)
    elif action == GL_LOOKUP:
        slice_data = fetch_finance_gl_slice(acct_id=first_acct)
        metrics = {"workstream_slices": {"finance": slice_data}} if slice_data else None
        if metrics and first_acct:
            bi = fetch_bi_slice_for_account(first_acct)
            if bi:
                metrics.update(bi)
    elif action == DEPOSIT_LOOKUP:
        slice_data = fetch_cashiering_slice(first_acct) if first_acct else None
        metrics = {"workstream_slices": {"cashiering": slice_data}} if slice_data else None
        if metrics and first_acct:
            bi = fetch_bi_slice_for_account(first_acct)
            if bi:
                metrics.update(bi)
    elif action == NEW_SERVICES_LOOKUP:
        slice_data = fetch_new_services_slice(acct_id=first_acct)
        metrics = {"workstream_slices": {"new_services": slice_data}} if slice_data else None
        if metrics and first_acct:
            bi = fetch_bi_slice_for_account(first_acct)
            if bi:
                metrics.update(bi)
    elif action == BILLING_LOOKUP:
        slice_data = fetch_billing_slice(first_acct) if first_acct else None
        metrics = {"workstream_slices": {"billing": slice_data}} if slice_data else None
        if metrics and first_acct:
            bi = fetch_bi_slice_for_account(first_acct)
            if bi:
                metrics.update(bi)
    elif action == CUSTOMER_ALERTS:
        slice_data = fetch_customer_ops_slice(first_acct) if first_acct else None
        metrics = {"workstream_slices": {"customer_ops": slice_data}} if slice_data else None
        if metrics and first_acct:
            bi = fetch_bi_slice_for_account(first_acct)
            if bi:
                metrics.update(bi)
    elif action == DEBT_MGMT_LOOKUP:
        slice_data = fetch_debt_mgmt_slice(first_acct) if first_acct else None
        metrics = {"workstream_slices": {"debt_mgmt": slice_data}} if slice_data else None
        if metrics and first_acct:
            bi = fetch_bi_slice_for_account(first_acct)
            if bi:
                metrics.update(bi)
    elif action == FIELD_OPS_LOOKUP:
        slice_data = fetch_field_ops_slice(first_acct) if first_acct else None
        tasks_data = fetch_field_tasks_slice(first_acct) if first_acct else None
        slices_dict = {}
        if slice_data:
            slices_dict["field_ops"] = slice_data
        if tasks_data:
            slices_dict["field_tasks"] = tasks_data
        metrics = {"workstream_slices": slices_dict} if slices_dict else None
        if metrics and first_acct:
            bi = fetch_bi_slice_for_account(first_acct)
            if bi:
                metrics.update(bi)
    else:
        # Legacy: ARREARS_SUMMARY, PAYMENT_LOOKUP, PREMISE_LOOKUP, ACCOUNT_STATUS
        if not acct_ids:
            narrative = generate_nlq_response(question, None)
            return {"narrative": narrative, "acct_id": None, "metrics": None, "resolved_from": resolved_from}
        metrics = fetch_bi_slice_for_account(first_acct)
        narrative = generate_nlq_response(question, metrics)
        return {
            "narrative": narrative,
            "acct_id": first_acct,
            "metrics": metrics,
            "resolved_from": resolved_from,
        }

    # Workstream path: we may have no acct_id (e.g. "What is the GL distribution?")
    if not metrics:
        narrative = generate_nlq_response(question, None)
        return {"narrative": narrative, "acct_id": first_acct, "metrics": None, "resolved_from": resolved_from}
    narrative = generate_nlq_response(question, metrics)
    return {
        "narrative": narrative,
        "acct_id": first_acct,
        "metrics": metrics,
        "resolved_from": resolved_from,
    }


def main() -> None:
    """CLI entrypoint for testing and for Jaspersoft (script adapter)."""
    if len(sys.argv) < 2:
        print("Usage: python -m pipeline.nlq \"What is the status of Account 2927873805?\"", file=sys.stderr)
        sys.exit(1)
    question = " ".join(sys.argv[1:])
    try:
        result = run_nlq(question)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"narrative": f"I could not process that request: {e}", "acct_id": None, "metrics": None}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
