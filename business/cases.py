import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from business.errors import ConfigurationError

CITY_NAME = "Самара"
CITY_UI_ID = "36401"
ROOT = Path(__file__).resolve().parent.parent
REPRESENTATIVES = ROOT / "config" / "representatives.json"


def valid_url(value: str) -> bool:
    parsed = urlsplit(value)
    return parsed.scheme in {"https", "http"} and bool(parsed.hostname) and not parsed.username


def validate_case(case: dict) -> None:
    ident = case.get("case_id", "")
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+", ident):
        raise ConfigurationError("case_id must be non-empty and filename-safe")
    if case.get("target_city") != CITY_NAME or case.get("target_city_ui_id") != CITY_UI_ID:
        raise ConfigurationError(f"{ident}: only Samara / 36401 is allowed")
    if case.get("environment") not in {"stage", "prod"}:
        raise ConfigurationError(f"{ident}: explicit stage/prod required")
    if case.get("status") not in {"active", "blocked", "excluded"}:
        raise ConfigurationError(f"{ident}: invalid status")
    if not case.get("source_refs"):
        raise ConfigurationError(f"{ident}: source_refs required")
    if case["status"] != "active":
        if not case.get("reason"):
            raise ConfigurationError(f"{ident}: non-active case needs a reason")
        return
    for key in ("provider", "entry_url", "form", "region", "submission", "confirmation", "verification"):
        if not case.get(key):
            raise ConfigurationError(f"{ident}: missing {key}")
    if not valid_url(case["entry_url"]):
        raise ConfigurationError(f"{ident}: invalid entry_url")
    if case.get("flow_kind") not in {"business_page", "business_option"}:
        raise ConfigurationError(f"{ident}: invalid flow_kind")
    region = case["region"]
    if region.get("mode") not in {"popup_selection", "direct_city_subdomain"}:
        raise ConfigurationError(f"{ident}: region mode required")
    for key in ("business_url", "indicator"):
        if not region.get(key):
            raise ConfigurationError(f"{ident}: region.{key} required")
    if not valid_url(region["business_url"]):
        raise ConfigurationError(f"{ident}: invalid region business_url")
    if region["mode"] == "popup_selection":
        for key in ("trigger", "popup", "search", "choice", "choice_url", "after_choice_url"):
            if not region.get(key):
                raise ConfigurationError(f"{ident}: region.{key} required")
        if not valid_url(region["choice_url"]) or not valid_url(region["after_choice_url"]):
            raise ConfigurationError(f"{ident}: invalid region choice URL")
    elif case["entry_url"] != region["business_url"]:
        raise ConfigurationError(f"{ident}: direct entry must be the verified city business URL")
    form = case["form"]
    for key in ("selector", "submit", "fields"):
        if not form.get(key):
            raise ConfigurationError(f"{ident}: form.{key} required")
    if case["flow_kind"] == "business_option":
        control = form.get("business_control", {})
        if control.get("kind") not in {"checkbox", "radio", "select"}:
            raise ConfigurationError(f"{ident}: business_option needs a verified checkbox/radio/select")
        if control["kind"] == "select":
            for key in ("business_value", "alternative_value"):
                if not isinstance(control.get(key), str) or not control[key]:
                    raise ConfigurationError(f"{ident}: select business control needs {key}")
    for field in form["fields"]:
        if not field.get("selector") or not field.get("data_key"):
            raise ConfigurationError(f"{ident}: field selector/data_key required")
    from business.submission import validate_contract
    validate_contract(case["submission"])
    confirmation = case["confirmation"]
    if confirmation.get("kind") not in {"locator", "url", "url_contains"} or not confirmation.get("value"):
        raise ConfigurationError(f"{ident}: exact confirmation required")


def load_cases(path: Path = ROOT / "config/business_cases.json") -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise ConfigurationError("cases must be a list")
    seen = set()
    for case in cases:
        validate_case(case)
        if case["case_id"] in seen:
            raise ConfigurationError(f"duplicate case_id: {case['case_id']}")
        seen.add(case["case_id"])
    return cases


def select_cases(cases: list[dict], environment: str, provider=None, case_id=None) -> list[dict]:
    if environment not in {"stage", "prod"}:
        raise ConfigurationError("--env=stage or --env=prod is required")
    selected = [c for c in cases if c["environment"] == environment
                and (not provider or c["provider"] == provider)
                and (not case_id or c["case_id"] == case_id)]
    if not selected:
        raise ConfigurationError("empty case selection; no verified coverage for these filters")
    return selected


def select_representatives(cases: list[dict], environment: str,
                           path: Path = REPRESENTATIVES) -> list[dict]:
    """Return the explicitly reviewed, non-submitting CI representative scope."""
    if environment not in {"stage", "prod"}:
        raise ConfigurationError("--env=stage or --env=prod is required")
    payload = json.loads(path.read_text(encoding="utf-8"))
    case_ids = payload.get("case_ids")
    if payload.get("environment") != environment or not isinstance(case_ids, list) or not case_ids:
        raise ConfigurationError("representative scope must name cases for the selected environment")
    if any(not isinstance(case_id, str) or not case_id for case_id in case_ids):
        raise ConfigurationError("representative scope has an invalid case ID")
    if len(set(case_ids)) != len(case_ids):
        raise ConfigurationError("representative scope has duplicate case IDs")
    by_id = {case["case_id"]: case for case in cases}
    missing = [case_id for case_id in case_ids if case_id not in by_id]
    if missing:
        raise ConfigurationError("representative scope references an unknown case")
    return [by_id[case_id] for case_id in case_ids]


def load_data(path: Path, environment: str) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("city") != CITY_NAME:
        raise ConfigurationError("data profile must belong to Samara")
    if data.get("environment") != environment:
        raise ConfigurationError("data profile environment is not confirmed for this run")
    if not data.get("phone") or not data.get("street") or not data.get("house"):
        raise ConfigurationError("phone/street/house required; values are never padded or invented")
    return data
