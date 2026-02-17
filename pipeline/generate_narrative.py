"""
Generate a 2-sentence utility bill narrative using OpenAI or Gemini.
Uses OPENAI_API_KEY when set; otherwise GEMINI_API_KEY. Returns valid JSON-shaped output for Jaspersoft.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
WORKSTREAM_HEALTH_PATH = _OUTPUT_DIR / "workstream_health.json"
CONFIG_COMPLETENESS_PATH = _OUTPUT_DIR / "config_completeness.json"

PROMPT_TEMPLATE = """You are a succinct utility analyst. Return a JSON object with exactly one key, "narrative", whose value is a 2-sentence summary for the customer's bill. Base it on: usage $%s this month vs $%s last month (change: $%s, %s%%); weather: %s. You may reference the dollar or percent change in the narrative. Be clear and neutral. Do not use markdown or bullet points. Output only the JSON object, no other text."""

# Senior BI Analyst system prompt (9 workstreams: Billing, Cashiering, Meter, Customer Ops, New Services, Finance, Common, Debt Mgmt, Field Ops)
BI_SYSTEM_PROMPT = """You are a Senior BI Analyst. Write a concise, data-driven narrative for leadership based only on the metrics provided. Keep the narrative to 3-4 sentences maximum (about 75 words). Be professional and avoid speculation. Insights may come from Billing, Cashiering, Meter Operations, Customer Operations, New Services, Finance, Common, Debt Management, or Field Operations; when relevant, attribute the source (e.g. "From meter operations...", "From cashiering..."). Return a JSON object with exactly one key: "narrative" (string). Do not use markdown or bullet points. Output only the JSON object, no other text."""

# NLQ: answer from provided workstream data; when only some data is present, state what you can from the present data and only then say what is not available.
NLQ_SYSTEM_PROMPT = """You are a Senior BI Analyst for the utility. You answer only questions about accounts, arrears, payments, meters, GL, deposits, new services, debt management, field operations, and related utility data. Use only the provided database row/metrics to answer the user's question. Insights may come from Billing, Cashiering, Meter Operations, Customer Operations, New Services, Finance, Common, Debt Management, or Field Operations; phrase answers by workstream when relevant (e.g. "From cashiering, ..."; "From meter operations, ..."). When the user asks about multiple topics (e.g. meter and payment) but only some workstream data is provided: answer fully from the data that IS provided, then briefly state what is not available (e.g. "From cashiering, there was 1 payment totaling $92. I do not have meter status for this account."). Do not say "I do not have information" for the whole answer if you have partial data. Do not speculate or use external knowledge. If no data at all was found for the requested account or address, state that clearly. Do not answer non-utility questions. Return a JSON object with exactly one key: "narrative" (string). Output only the JSON object, no other text."""

# Business Snapshot persona: plain-language story, why it matters, and next steps for City staff with no SQL background.
BUSINESS_SNAPSHOT_SYSTEM_PROMPT = """You are a Business Snapshot explainer for City utility staff. Using only the structured metrics and domain context provided, write a short, plain-language summary that explains:
- What is happening for this account or scenario (key facts, trends).
- Why it matters to the City or customer (business impact, policy context, risk).
- Recommended next steps or actions for staff (e.g. follow-up, monitoring, communication).

Keep the summary to 3-4 sentences maximum (about 75 words). Avoid technical jargon (e.g. CI_FT, CI_SA); instead, use the table descriptions, designer notes, and Business Impact text from Domain Designs when relevant. Do not speculate beyond the provided data. Return a JSON object with exactly one key: "narrative" (string). Do not use markdown or bullet points. Output only the JSON object, no other text."""


def _get_data_currency_risk_text() -> str:
    """If validate_tables wrote workstream_health.json with stale workstreams, return a line for the prompt."""
    if not WORKSTREAM_HEALTH_PATH.exists():
        return ""
    try:
        with open(WORKSTREAM_HEALTH_PATH, encoding="utf-8") as f:
            data = json.load(f)
        stale = data.get("stale_workstreams") or []
        if not stale:
            return ""
        return (
            " Data Currency Risk: the following workstreams have had no records created/frozen in the last 7 days: "
            + ", ".join(stale)
            + ". When referencing these areas, consider flagging recency to the client."
        )
    except Exception:
        return ""


def _get_config_risk_text() -> str:
    """
    If validate_tables wrote config_completeness.json with configuration risks
    (e.g. billing gaps), return a short line for the prompt.
    """
    if not CONFIG_COMPLETENESS_PATH.exists():
        return ""
    try:
        with open(CONFIG_COMPLETENESS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        rules = data.get("rules") or {}
        parts: list[str] = []
        gap = rules.get("billing_gap_60d") or {}
        if gap.get("applies") and isinstance(gap.get("count"), int) and gap.get("count", 0) > 0:
            parts.append(
                f"Billing Gap: {gap['count']} active service agreements have no financial transactions "
                f"in the last 60 days."
            )
        missing_rate = rules.get("active_sa_missing_rate") or {}
        if missing_rate.get("applies") and isinstance(missing_rate.get("count"), int) and missing_rate.get("count", 0) > 0:
            parts.append(
                f"Rate configuration issues: {missing_rate['count']} active service agreements are missing a rate code."
            )
        if not parts:
            return ""
        return " Configuration risks: " + " ".join(parts)
    except Exception:
        return ""


def _domain_context_suffix() -> str:
    """Append domain table descriptions and Designer Notes/Justifications for client-facing insights."""
    try:
        from .domain_context import get_workstream_table_descriptions, get_semantic_layer_prompt_suffix
        s = get_workstream_table_descriptions()
        j = get_semantic_layer_prompt_suffix()
        out = ""
        if s:
            out += "\n\n" + s
        if j:
            out += "\n\n" + j
        return out
    except Exception:
        return ""


def _format_amount(value: float | int) -> str:
    """
    Friendly amount formatting for narratives:
    - >= 1,000,000: show in millions with 1 decimal (e.g. 228.7M)
    - >= 1,000: whole number with thousands separator (e.g. 226,555)
    - otherwise: 1 decimal (e.g. 2,259.7)
    """
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        v = 0.0
    abs_v = abs(v)
    if abs_v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if abs_v >= 1_000:
        return f"{v:,.0f}"
    return f"{v:,.1f}"


def _format_weather(heatwave_days: int) -> str:
    if heatwave_days and heatwave_days > 0:
        return f"{heatwave_days} heatwave day(s)"
    return "no significant heatwaves"


def _parse_narrative_response(text: str) -> str:
    """Parse JSON from model response; strip markdown fences if present."""
    text = text.strip()
    for prefix in ("```json\n", "```\n"):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    data = json.loads(text)
    narrative = data.get("narrative")
    if not narrative or not isinstance(narrative, str):
        raise RuntimeError("Model response JSON missing or invalid 'narrative' string.")
    return narrative.strip()


def _format_workstream_slices(slices: dict) -> str:
    """Format workstream_slices dict into bullet text for the AI (ground truth fields included)."""
    parts = []
    for name, data in (slices or {}).items():
        if not isinstance(data, dict):
            continue
        workstream = data.get("workstream", name)
        if workstream == "billing":
            base = (
                f"Billing: total amount ${_format_amount(data.get('billing_total_amount', 0))}, "
                f"last bill date {data.get('billing_last_bill_dt') or 'N/A'}, row count {data.get('billing_row_count', 0)}."
            )
            rate_cfg = data.get("billing_rate_config")
            if isinstance(rate_cfg, list) and rate_cfg:
                example = rate_cfg[0]
                rs_cd = example.get("rs_cd") or example.get("RS_CD")
                rs_name = example.get("rate_descr") or example.get("rate_desrc") or example.get("rate_descr")  # defensive
                if rs_cd or rs_name:
                    base += f" Example rate schedule RS_CD {rs_cd or ''} {rs_name or ''}."
            parts.append(base)
        elif workstream == "cashiering":
            parts.append(
                f"Cashiering: TNDR_STATUS valid (25) count {data.get('cashiering_tndr_status_valid_count', 0)}, "
                f"total pay ${_format_amount(data.get('cashiering_total_pay_amt', 0))}, "
                f"payments {data.get('cashiering_payment_count', 0)}."
            )
        elif workstream == "meter_ops":
            parts.append(
                f"Meter operations: D1_INSTALL_DTTM {data.get('meter_install_dttm') or 'N/A'}, "
                f"device ID {data.get('d1_device_id') or data.get('meter_nbr') or 'N/A'}, "
                f"device type {data.get('device_type_cd') or 'N/A'}."
            )
        elif workstream == "customer_ops":
            parts.append(
                f"Customer: account {data.get('customer_acct_nbr')}, "
                f"entity name {data.get('customer_entity_name')}, "
                f"cust class {data.get('customer_cust_cl_cd')}, coll class {data.get('customer_coll_cl_cd')}, "
                f"alerts {data.get('customer_alert_types', [])}."
            )
        elif workstream == "new_services":
            parts.append(
                f"New services: SA_STATUS_FLG pending (10) count {data.get('new_services_sa_status_pending_count', 0)}, "
                f"latest initiation {data.get('new_services_latest_initiation_dttm') or 'N/A'}."
            )
        elif workstream == "finance":
            parts.append(
                f"Finance: GL_DISTRIB_STATUS values {data.get('finance_gl_distrib_status_list', [])}, "
                f"total amt ${_format_amount(data.get('finance_total_amt', 0))}."
            )
        elif workstream == "debt_mgmt":
            parts.append(
                f"Debt Management: collection class {data.get('debt_mgmt_coll_cl_cd')}, "
                f"CR review dt {data.get('debt_mgmt_cr_review_dt') or 'N/A'}."
            )
        elif workstream == "field_ops":
            parts.append(
                f"Field Operations: SP_ID {data.get('field_ops_sp_id')}, "
                f"install dt {data.get('field_ops_install_dt') or 'N/A'}, status {data.get('field_ops_sp_status_flg') or 'N/A'}, SP count {data.get('field_ops_sp_count', 0)}."
            )
        else:
            parts.append(f"{workstream}: {data}.")
    return " ".join(parts) if parts else ""


def _format_risk_metrics(metrics: dict) -> str:
    """Format Risk Data metrics for BI and Business Snapshot prompts; return empty if none present."""
    n = metrics.get("revenue_leakage_acct_count") or 0
    amt = metrics.get("revenue_leakage_total_amt") or 0
    pend_amt = metrics.get("liquidity_pending_amt") or 0
    pend_48 = metrics.get("liquidity_pending_count_48h") or 0
    unfr_amt = metrics.get("liquidity_unfrozen_amt") or 0
    unfr_48 = metrics.get("liquidity_unfrozen_count_48h") or 0
    stale = metrics.get("stale_pending_sa_count") or 0
    if n == 0 and (pend_amt == 0 and pend_48 == 0 and unfr_amt == 0 and unfr_48 == 0) and stale == 0:
        return ""
    parts = ["Risk Data (Audit): "]
    if n > 0:
        parts.append(
            f"Unresolved debt on canceled service: {n} account(s), ${_format_amount(amt)} total; "
            "state 'Unresolved Debt on Canceled Service' and recommend final bill or write-off. "
        )
    if pend_48 > 0 or unfr_48 > 0 or pend_amt != 0 or unfr_amt != 0:
        parts.append(
            f"Liquidity: pending payment amount ${_format_amount(pend_amt)}, {pend_48} pending >48h; "
            f"unfrozen FT amount ${_format_amount(unfr_amt)}, {unfr_48} unfrozen >48h. "
            "If any payment/FT is unfrozen >48 hours, state 'Suspense Account Alert' (batch or drawer may need follow-up). "
        )
    if stale > 0:
        parts.append(
            f"Stale pending service: {stale} SA(s) with start date in the past. "
            "State: 'Service delay detected: X accounts pending start dates from last week; check Field Task status in F1_TSK.' "
        )
    return "".join(parts)


def _build_business_snapshot_message(metrics: dict, question: str | None = None) -> str:
    """
    Build the user message for the Business Snapshot persona from metrics/workstream slices.
    Focus on story, impact, and next steps rather than raw metrics only.
    """
    msg = "Business Snapshot data context: "
    if metrics:
        if "total_debt" in metrics:
            msg += (
                f"Total arrears debt ${_format_amount(metrics.get('total_debt', 0))} "
                f"(0-30: ${_format_amount(metrics.get('debt_30_days', 0))}, "
                f"31-60: ${_format_amount(metrics.get('debt_60_days', 0))}, "
                f">60: ${_format_amount(metrics.get('debt_over_60', 0))}). "
            )
        if "current_amount" in metrics and "prior_amount" in metrics:
            msg += (
                f"Bill comparison: current amount ${_format_amount(metrics.get('current_amount', 0))} "
                f"vs prior ${_format_amount(metrics.get('prior_amount', 0))}, "
                f"delta ${_format_amount(metrics.get('amount_delta', 0))} "
                f"({metrics.get('percent_change', 0):+.1f}%). "
            )
    slices_text = _format_workstream_slices((metrics or {}).get("workstream_slices"))
    if slices_text:
        msg += "Workstream data: " + slices_text + " "
    risk_data = _format_risk_metrics(metrics or {})
    if risk_data:
        msg += risk_data
    if question:
        msg += f"User question (if provided): {question!r}. "
    msg += (
        "Explain this situation in plain language for City staff with no SQL knowledge in 3-4 sentences (max 75 words). "
        "Describe what is happening, why it matters (using Business Impact / designer notes when applicable), "
        "and clear next steps or actions for staff."
    )
    risk = _get_data_currency_risk_text()
    if risk:
        msg += risk
    cfg_risk = _get_config_risk_text()
    if cfg_risk:
        msg += cfg_risk
    return msg


def _build_bi_user_message(metrics: dict) -> str:
    """Build the user message for the AI from the BI metrics dict (incl. workstream slices and Risk Data)."""
    base = (
        "Metrics: "
        f"Total debt: ${_format_amount(metrics.get('total_debt', 0))}. "
        f"Debt 0-30 days: ${_format_amount(metrics.get('debt_30_days', 0))}; "
        f"31-60 days: ${_format_amount(metrics.get('debt_60_days', 0))}; "
        f"over 60 days: ${_format_amount(metrics.get('debt_over_60', 0))}. "
        f"Large bill count (>$500): {metrics.get('large_bill_count', 0)}. "
        f"Potential duplicate payment accounts: {metrics.get('duplicate_payment_account_count', 0)} "
        f"(example amount: ${_format_amount(metrics.get('duplicate_payment_example_amt', 0))}). "
        f"Bankruptcy-flagged accounts with payments: {metrics.get('bankruptcy_alert_count', 0)} accounts, "
        f"${_format_amount(metrics.get('bankruptcy_pym_amt', 0))} total. "
    )
    risk_data = _format_risk_metrics(metrics or {})
    if risk_data:
        base += risk_data
    slices_text = _format_workstream_slices(metrics.get("workstream_slices"))
    if slices_text:
        base += "Workstream data: " + slices_text + " "
    base += "Write a short narrative (3-4 sentences, max 75 words) summarizing arrears risk, payment integrity, and bankruptcy risk"
    if risk_data:
        base += "; when Risk Data is present, include Unresolved Debt on Canceled Service, Suspense Account Alert, or Service delay (F1_TSK) as applicable"
    if slices_text:
        base += ", and any relevant workstream insights (Billing, Meter, Finance, etc.)"
    base += "."
    risk = _get_data_currency_risk_text()
    if risk:
        base += risk
    return base


def _build_nlq_user_message(question: str, metrics: dict | None) -> str:
    """Build user message for NLQ: either provided metrics + question (incl. workstream slices), or no-data instruction."""
    if metrics is None:
        return (
            "No database row was found for the requested account, premise, or customer. "
            f"The user asked: {question!r}. "
            "Respond that you do not have access to that specific record."
        )
    msg = (
        "Data for this account: "
        f"Total debt: ${metrics.get('total_debt', 0):,.2f}. "
        f"Debt 0-30 days: ${metrics.get('debt_30_days', 0):,.2f}; 31-60 days: ${metrics.get('debt_60_days', 0):,.2f}; over 60 days: ${metrics.get('debt_over_60', 0):,.2f}. "
        f"Large bill count (>$500): {metrics.get('large_bill_count', 0)}. "
        f"Duplicate payment flag: {metrics.get('duplicate_payment_account_count', 0)} (example amount: ${metrics.get('duplicate_payment_example_amt', 0):,.2f}). "
        f"Bankruptcy alert: {metrics.get('bankruptcy_alert_count', 0)} accounts, ${metrics.get('bankruptcy_pym_amt', 0):,.2f} total. "
    )
    slices_text = _format_workstream_slices(metrics.get("workstream_slices"))
    if slices_text:
        msg += "Workstream data: " + slices_text + " "
    msg += f"User question: {question!r}. Answer the user's question using only this data."
    risk = _get_data_currency_risk_text()
    if risk:
        msg += risk
    return msg


def _generate_openai(
    prompt: str,
    model: str,
    messages: list | None = None,
) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if messages is not None:
        msg_list = messages
    else:
        msg_list = [{"role": "user", "content": prompt}]
    response = client.chat.completions.create(
        model=model,
        messages=msg_list,
        response_format={"type": "json_object"},
    )
    if not response.choices or not response.choices[0].message.content:
        raise RuntimeError("OpenAI returned no content.")
    return response.choices[0].message.content


def _generate_gemini(
    prompt: str,
    model: str,
    system_prompt: str | None = None,
) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    if not response or not response.text:
        raise RuntimeError("Gemini returned no text.")
    return response.text


def generate_narrative(
    current_amount: float,
    prior_amount: float,
    heatwave_days: int = 0,
    amount_delta: float = 0,
    percent_change: float = 0,
    *,
    model_name: str | None = None,
) -> str:
    """
    Produce a 2-sentence bill summary using OpenAI (if OPENAI_API_KEY set) or Gemini (if GEMINI_API_KEY set).
    """
    if os.getenv("OPENAI_API_KEY"):
        api_key_name = "OPENAI_API_KEY"
        default_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        generator = _generate_openai
    elif os.getenv("GEMINI_API_KEY"):
        api_key_name = "GEMINI_API_KEY"
        default_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        generator = _generate_gemini
    else:
        raise ValueError(
            "Set OPENAI_API_KEY or GEMINI_API_KEY in .env (or environment)."
        )

    model = model_name or default_model
    weather_text = _format_weather(heatwave_days)
    prompt = PROMPT_TEMPLATE % (
        f"{current_amount:.2f}",
        f"{prior_amount:.2f}",
        f"{amount_delta:+.2f}",
        f"{percent_change:+.1f}",
        weather_text,
    )

    text = generator(prompt, model)
    return _parse_narrative_response(text)


def generate_business_snapshot(
    metrics: dict,
    *,
    user_question: str | None = None,
    model_name: str | None = None,
) -> str:
    """
    Produce a Business Snapshot narrative for City staff using metrics/workstream slices
    and Domain Designs semantic context. Intended for training, CSR dashboards, and
    change-management views.
    """
    if os.getenv("OPENAI_API_KEY"):
        default_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        generator = _generate_openai
    elif os.getenv("GEMINI_API_KEY"):
        default_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        generator = _generate_gemini
    else:
        raise ValueError(
            "Set OPENAI_API_KEY or GEMINI_API_KEY in .env (or environment) for Business Snapshot generation."
        )

    model = model_name or default_model
    system_prompt = BUSINESS_SNAPSHOT_SYSTEM_PROMPT + _domain_context_suffix()
    user_msg = _build_business_snapshot_message(metrics or {}, user_question)

    if generator is _generate_openai:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ]
        text = generator("", model, messages=messages)
    else:
        text = generator(user_msg, model, system_prompt=system_prompt)
    return _parse_narrative_response(text)


def generate_bi_narrative(
    metrics: dict,
    *,
    model_name: str | None = None,
) -> str:
    """
    Produce a data-driven BI narrative (arrears, payment integrity, bankruptcy) using
    the Senior BI Analyst system prompt and the provided metrics dict from fetch_bi_summary().
    """
    bi_prompt = BI_SYSTEM_PROMPT + _domain_context_suffix()
    if os.getenv("OPENAI_API_KEY"):
        model = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        messages = [
            {"role": "system", "content": bi_prompt},
            {"role": "user", "content": _build_bi_user_message(metrics)},
        ]
        text = _generate_openai("", model, messages=messages)
    elif os.getenv("GEMINI_API_KEY"):
        model = model_name or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        user_msg = _build_bi_user_message(metrics)
        text = _generate_gemini(user_msg, model, system_prompt=bi_prompt)
    else:
        raise ValueError(
            "Set OPENAI_API_KEY or GEMINI_API_KEY in .env (or environment)."
        )
    return _parse_narrative_response(text)


def generate_nlq_response(user_question: str, retrieved_metrics: dict | None) -> str:
    """
    Generate an NLQ answer with guardrails: only from provided data; if no data, say no access.
    Uses OPENAI_API_KEY or GEMINI_API_KEY. Returns the narrative string.
    """
    nlq_prompt = NLQ_SYSTEM_PROMPT + _domain_context_suffix()
    if os.getenv("OPENAI_API_KEY"):
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        messages = [
            {"role": "system", "content": nlq_prompt},
            {"role": "user", "content": _build_nlq_user_message(user_question, retrieved_metrics)},
        ]
        text = _generate_openai("", model, messages=messages)
    elif os.getenv("GEMINI_API_KEY"):
        model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        user_msg = _build_nlq_user_message(user_question, retrieved_metrics)
        text = _generate_gemini(user_msg, model, system_prompt=nlq_prompt)
    else:
        raise ValueError("Set OPENAI_API_KEY or GEMINI_API_KEY in .env for NLQ.")
    return _parse_narrative_response(text)
