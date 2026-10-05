"""Structured per-case artifacts used for post-run lead lookup."""

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


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
    is_business_page = case.get("flow_kind") == "business_page"
    confirmation = result.get("confirmation_observed") or {}
    submit_time = confirmation_observed_at_utc or submission_started_at_utc
    success = result.get("status") == "passed" and bool(confirmation)
    entry_url = case.get("entry_url")
    business_value = (
        control.get("business_value")
        or control.get("business_option")
        or control.get("value")
    )
    user_comment = data.get("user_comment")
    if is_business_page and not user_comment:
        # The business popup sends the address and form context as one
        # multiline user_comment; it does not populate street/house columns.
        city = data.get("city") or case.get("target_city") or ""
        street = data.get("street") or ""
        house = data.get("house") or ""
        address_text = " ".join(part for part in (street, house) if part).strip()
        form_label = (case.get("form") or {}).get("user_comment_label") \
            or "Подключить услуги для бизнеса"
        user_comment = (
            f"city: {city}, {address_text} info:\n"
            f"{entry_url}\n"
            f"| {form_label} |\n"
            "Город: выбрать город"
        )
    street = None if is_business_page else data.get("street")
    house = None if is_business_page else data.get("house")
    full_address = None if is_business_page else data.get("full_address")
    return {
        "schema_version": 2,
        "case_id": case.get("case_id"),
        "record_id": case.get("case_id"),
        "provider": case.get("provider"),
        "flow_kind": case.get("flow_kind"),
        "environment": case.get("environment"),
        "entry_url": entry_url,
        "base_url": entry_url,
        "domain": (urlsplit(entry_url or "").hostname or "").lower(),
        "form_type": case.get("flow_kind"),
        "form_key": (case.get("form") or {}).get("form_key")
        or (case.get("form") or {}).get("selector"),
        "target_city": case.get("target_city", data.get("city")),
        "target_city_ui_id": case.get("target_city_ui_id"),
        "address": {
            "city": data.get("city"),
            "street": street,
            "house": house,
            "full": full_address,
        },
        "region": case.get("target_city", data.get("city")),
        "city": data.get("city"),
        "locality": data.get("city"),
        "street": street,
        "house": house,
        "full_address": full_address,
        "user_comment": user_comment,
        "phone": phone,
        "business": {
            "control_kind": control.get("kind"),
            "business_value": business_value,
        },
        "business_value": business_value,
        "order_type_id": 3,
        "expected_order_type_id": 3,
        "submission_started_at_utc": submission_started_at_utc,
        "confirmation_observed_at_utc": confirmation_observed_at_utc,
        "submit_time": submit_time,
        "url_after_submit": confirmation.get("value"),
        "success": success,
        "test_status": result.get("status"),
        "confirmation_observed": confirmation,
        "error": result.get("error"),
    }


def write_submission_lookup(output: Path, payload: dict) -> Path:
    path = output / "submission_lookup.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
