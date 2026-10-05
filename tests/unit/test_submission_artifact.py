from business.artifacts import build_submission_lookup


def test_submission_lookup_contains_db_search_keys():
    case = {
        "case_id": "mts-business-option",
        "provider": "mts",
        "flow_kind": "business_option",
        "environment": "prod",
        "entry_url": "https://mts-home.online/samara",
        "target_city": "Самара",
        "target_city_ui_id": "36401",
        "form": {"selector": "form#lead",
                 "business_control": {"kind": "select", "business_value": "В офис"}},
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
    assert artifact["form_key"].startswith("form")
    assert artifact["domain"] == "mts-home.online"
    assert artifact["submit_time"] == "2026-10-05T07:00:04+00:00"
    assert artifact["url_after_submit"].endswith("/thanks")
    assert artifact["success"] is True
    assert artifact["order_type_id"] == 3
    assert artifact["expected_order_type_id"] == 3
    assert artifact["test_status"] == "passed"
    assert artifact["confirmation_observed_at_utc"].endswith("+00:00")


def test_business_popup_uses_user_comment_instead_of_street_and_house():
    case = {
        "case_id": "beeline-business-page",
        "provider": "beeline",
        "flow_kind": "business_page",
        "environment": "prod",
        "entry_url": "https://samara.beeline-ru.online/business",
        "target_city": "Самара",
        "target_city_ui_id": "36401",
        "form": {"selector": "#popup-business form"},
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
        "confirmation_observed": {"kind": "url", "value": "https://samara.beeline-ru.online/thanks"},
    }
    submitted_payload = {
        "Phone": "9999999999",
        "Info": "https://samara.beeline-ru.online/business",
        "CityName": "Самара",
        "user_comment": "city: Самара, фактическая улица 7 info: https://samara.beeline-ru.online/business",
    }

    artifact = build_submission_lookup(case, data, result, submitted_payload=submitted_payload)

    assert artifact["street"] is None
    assert artifact["house"] is None
    assert artifact["address"]["street"] is None
    assert artifact["address"]["house"] is None
    assert artifact["user_comment"] == submitted_payload["user_comment"]
    assert artifact["submitted_payload"] == submitted_payload
