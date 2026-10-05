import json

from business.artifacts import build_submitted_leads_payload, build_submission_lookup


def test_submission_lookup_contains_db_search_keys():
    case = {
        "case_id": "mts-business-option",
        "provider": "mts",
        "flow_kind": "business_option",
        "environment": "prod",
        "entry_url": "https://mts-home.online/samara",
        "target_city": "Самара",
        "target_city_ui_id": "36401",
        "form": {"business_control": {"kind": "select", "business_value": "В офис"}},
    }
    data = {
        "city": "Самара",
        "street": "Ленинградская",
        "house": "1",
        "full_address": "Самара, Ленинградская, 1",
        "phone": "9999999999",
    }
    result = {
        "status": "passed",
        "confirmation_observed": {"kind": "url", "value": "https://mts-home.online/thanks"},
    }

    artifact = build_submission_lookup(
        case,
        data,
        result,
        submission_started_at_utc="2026-10-05T07:00:00+00:00",
        confirmation_observed_at_utc="2026-10-05T07:00:04+00:00",
    )

    assert artifact["case_id"] == "mts-business-option"
    assert artifact["address"] == {
        "city": "Самара",
        "street": "Ленинградская",
        "house": "1",
        "full": "Самара, Ленинградская, 1",
    }
    assert artifact["phone"] == "9999999999"
    assert artifact["business"]["business_value"] == "В офис"
    assert artifact["test_status"] == "passed"
    assert artifact["confirmation_observed_at_utc"].endswith("+00:00")


def test_submitted_leads_contains_only_successful_cases(tmp_path):
    successful = tmp_path / "passed" / "submission_lookup.json"
    successful.parent.mkdir()
    successful.write_text(json.dumps({
        "case_id": "passed", "provider": "beeline", "flow_kind": "business_option",
        "entry_url": "https://beeline-home.online/", "target_city": "Самара",
        "target_city_ui_id": "36401", "phone": "9999999999",
        "address": {"city": "Самара", "street": "Ленинградская", "house": "1", "full": "Самара, Ленинградская, 1"},
        "business": {"business_value": "В офис"}, "test_status": "passed",
        "confirmation_observed": {"kind": "url", "value": "https://beeline-home.online/thanks"},
        "confirmation_observed_at_utc": "2026-10-05T07:00:04+00:00",
    }), encoding="utf-8")
    failed = tmp_path / "failed" / "submission_lookup.json"
    failed.parent.mkdir()
    failed.write_text(json.dumps({"case_id": "failed", "test_status": "failed"}), encoding="utf-8")

    cases = [{"case_id": "passed"}, {"case_id": "failed"}]
    payload = build_submitted_leads_payload(tmp_path, cases, run_id="jenkins-1", build_number="42")

    assert [row["case_id"] for row in payload["applications"]] == ["passed"]
    row = payload["applications"][0]
    assert row["domain"] == "beeline-home.online"
    assert row["street"] == "Ленинградская"
    assert row["house"] == "1"
    assert row["success"] is True
    assert payload["source_iteration"] == "everyday_test_submitted_leads"
