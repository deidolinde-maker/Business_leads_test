"""Structured per-case artifacts used for post-run lead lookup."""

import json
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_submission_lookup(
    case: dict,
    data: dict,
    result: dict,
    *,
    submission_started_at_utc: str | None = None,
    confirmation_observed_at_utc: str | None = None,
) -> dict:
    """Build the stable input/result key needed to search a lead in the DB.

    This is a lookup aid produced by the test run; it is not a claim that a
    database record exists. The actual positive signal remains the thank-you
    page recorded in ``result.json``.
    """
    control = (case.get("form") or {}).get("business_control") or {}
    phone = str(data.get("phone", ""))
    return {
        "schema_version": 1,
        "case_id": case.get("case_id"),
        "provider": case.get("provider"),
        "flow_kind": case.get("flow_kind"),
        "environment": case.get("environment"),
        "entry_url": case.get("entry_url"),
        "target_city": case.get("target_city", data.get("city")),
        "target_city_ui_id": case.get("target_city_ui_id"),
        "address": {
            "city": data.get("city"),
            "street": data.get("street"),
            "house": data.get("house"),
            "full": data.get("full_address"),
        },
        "phone": phone,
        "business": {
            "control_kind": control.get("kind"),
            "business_value": control.get("business_value")
            or control.get("business_option")
            or control.get("value"),
        },
        "submission_started_at_utc": submission_started_at_utc,
        "confirmation_observed_at_utc": confirmation_observed_at_utc,
        "test_status": result.get("status"),
        "confirmation_observed": result.get("confirmation_observed"),
        "error": result.get("error"),
    }


def write_submission_lookup(output: Path, payload: dict) -> Path:
    path = output / "submission_lookup.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
