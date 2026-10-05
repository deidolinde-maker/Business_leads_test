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


def build_submitted_leads_payload(artifact_dir: Path, cases: list[dict], *, run_id: str,
                                  build_number: str) -> dict:
    """Build the input file consumed by the single orders verifier.

    Only cases with a confirmed thank-you page are exported. This prevents a
    failed UI submission from being reported later as a database defect.
    """
    applications = []
    for case in cases:
        lookup_path = artifact_dir / case["case_id"] / "submission_lookup.json"
        if not lookup_path.exists():
            continue
        lookup = json.loads(lookup_path.read_text(encoding="utf-8"))
        confirmation = lookup.get("confirmation_observed") or {}
        if lookup.get("test_status") != "passed" or not confirmation:
            continue
        address = lookup.get("address") or {}
        entry_url = str(lookup.get("entry_url") or "")
        applications.append({
            "record_id": lookup.get("case_id"),
            "case_id": lookup.get("case_id"),
            "run_id": run_id,
            "build_number": build_number,
            "provider": lookup.get("provider"),
            "domain": (urlsplit(entry_url).hostname or "").lower(),
            "base_url": entry_url,
            "form_type": lookup.get("flow_kind"),
            "form_key": lookup.get("business", {}).get("business_value"),
            "business_value": lookup.get("business", {}).get("business_value"),
            "success": True,
            "url_after_submit": confirmation.get("value"),
            "submit_time": lookup.get("confirmation_observed_at_utc")
            or lookup.get("submission_started_at_utc"),
            "phone": lookup.get("phone"),
            "region": lookup.get("target_city"),
            "city": address.get("city") or lookup.get("target_city"),
            "locality": address.get("city") or lookup.get("target_city"),
            "street": address.get("street"),
            "house": address.get("house"),
            "full_address": address.get("full"),
            "target_city_ui_id": lookup.get("target_city_ui_id"),
        })

    return {
        "run_id": run_id,
        "build_number": build_number,
        "created_at": utc_now(),
        "source_iteration": "everyday_test_submitted_leads",
        "applications": applications,
    }


def write_submitted_leads(artifact_dir: Path, cases: list[dict], *, run_id: str,
                          build_number: str) -> Path:
    path = artifact_dir / "submitted_leads.json"
    payload = build_submitted_leads_payload(
        artifact_dir, cases, run_id=run_id, build_number=build_number
    )
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
