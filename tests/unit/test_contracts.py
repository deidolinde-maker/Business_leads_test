import json

import pytest

from business.cases import load_cases, load_data, select_cases, validate_case
from business.errors import BusinessCheckError, ConfigurationError
from business.submission import matches, parse_payload, validate_contract
from tests.support import make_case


def test_valid_synthetic_case():
    validate_case(make_case())


@pytest.mark.parametrize("field,value", [("target_city", "Москва"), ("target_city_ui_id", "77"),
                                       ("environment", None), ("case_id", "../escape")])
def test_reject_unsafe_case_config(field, value):
    case = make_case()
    case[field] = value
    with pytest.raises(ConfigurationError):
        validate_case(case)


@pytest.mark.parametrize("field", ["region_match", "business_match", "identity_match", "evidence"])
def test_no_unknown_contract_can_send(field):
    contract = make_case()["submission"]
    contract.pop(field)
    with pytest.raises(ConfigurationError):
        validate_contract(contract)


def test_empty_selection_not_green():
    with pytest.raises(ConfigurationError, match="empty"):
        select_cases([make_case()], "prod")


def test_environment_required():
    with pytest.raises(ConfigurationError, match="required"):
        select_cases([make_case()], None)


def test_duplicate_cases(tmp_path):
    path = tmp_path / "cases.json"
    path.write_text(json.dumps({"cases": [make_case(), make_case()]}), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="duplicate"):
        load_cases(path)


def test_unconfirmed_environment_data_rejected(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps({"city": "Самара", "environment": None, "phone": "999999999", "street": "Ленинградская", "house": "1"}), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="environment"):
        load_data(path, "prod")


@pytest.mark.parametrize("media,body,expected", [
    ("application/json", b'{"region":"samara-fixture","business":true}', {"region": "samara-fixture", "business": True}),
    ("application/x-www-form-urlencoded", b"region=samara-fixture&business=1", {"region": "samara-fixture", "business": "1"}),
    ("multipart/form-data; boundary=test", b'--test\r\nContent-Disposition: form-data; name="region"\r\n\r\nsamara-fixture\r\n--test--\r\n', {"region": "samara-fixture"}),
])
def test_supported_payload_encodings(media, body, expected):
    assert parse_payload(media, body) == expected


def test_duplicate_json_city_rejected():
    with pytest.raises(BusinessCheckError, match="duplicate"):
        parse_payload("application/json", b'{"city":"samara","city":"moscow"}')


def test_browser_multipart_preserves_cyrillic_without_charset():
    body = '--boundary\r\nContent-Disposition: form-data; name="CityName"\r\n\r\nСамара\r\n--boundary--\r\n'.encode('utf-8')
    assert parse_payload('multipart/form-data; boundary=boundary', body) == {"CityName": "Самара"}


def test_invalid_utf8_multipart_is_rejected():
    body = b'--b\r\nContent-Disposition: form-data; name="CityName"\r\n\r\n\xff\r\n--b--\r\n'
    with pytest.raises(UnicodeDecodeError):
        parse_payload('multipart/form-data; boundary=b', body)


def test_shared_submit_endpoint_cannot_allowlist_post_with_other_query():
    contract = make_case()["submission"]
    contract["read_only_requests"] = [{"url": contract["url"] + "?action=search", "method": "POST", "evidence": "same endpoint"}]
    with pytest.raises(ConfigurationError, match="shared submission"):
        validate_contract(contract)


def test_submit_cannot_be_classified_as_background():
    contract = make_case()["submission"]
    contract["blocked_background_requests"] = [{"url": contract["url"], "evidence": "bad"}]
    with pytest.raises(ConfigurationError, match="background"):
        validate_contract(contract)


def test_hidden_duplicate_urlencoded_city_cannot_pass():
    payload = parse_payload("application/x-www-form-urlencoded", b"city=samara&city=moscow")
    with pytest.raises(BusinessCheckError, match="mismatch"):
        matches(payload, {"city": "samara"}, "region")


def test_exact_types_no_bool_city_alias():
    with pytest.raises(BusinessCheckError, match="mismatch"):
        matches({"city": True}, {"city": 1}, "region")


def test_missing_nested_city_rejected():
    with pytest.raises(BusinessCheckError, match="missing"):
        matches({"address": {}}, {"address.city": "Samara"}, "region")


def test_target_not_allowed_as_readonly():
    contract = make_case()["submission"]
    contract["read_only_requests"] = [{"url": contract["url"], "method": "POST", "evidence": "bad"}]
    with pytest.raises(ConfigurationError):
        validate_contract(contract)


def test_no_redirecting_post_contract():
    contract = make_case()["submission"]
    contract["response"] = {"statuses": [307], "location": "/other"}
    with pytest.raises(ConfigurationError):
        validate_contract(contract)


def test_imported_scope_has_samara_targets_and_provenance():
    cases = load_cases()
    assert cases
    assert all(c["target_city"] == "Самара" and c["source_refs"] for c in cases)
    assert any("/business" in c["source_page_url"] for c in cases)
    assert any(c["flow_kind"] == "business_option" for c in cases)


def test_mts_business_page_scope_is_single_user_confirmed_landing():
    cases = load_cases()
    pages = [c for c in cases if c["provider"] == "mts" and c["flow_kind"] == "business_page"]
    included = [c for c in pages if c["status"] != "excluded"]
    assert [c["source_page_url"] for c in included] == ["https://mts-home-online.ru/business"]
    target = included[0]
    assert target["entry_url"] == "https://mts-home-online.ru/business"
    assert target["region"]["mode"] == "popup_selection"
    assert target["region"]["choice_url"] == "https://mts-home-online.ru/samara"
    assert target["status"] == "active"
    assert target["submission"]["url"] == (
        "https://mts-home-online.ru/wp-json/contact-form-7/v1/contact-forms/837/feedback"
    )
    assert target["submission"]["region_match"] == {
        "BusinessCityId": "36401",
        "CityName": "Самара",
    }
    assert target["submission"]["business_match"] == {
        "FormName": "Заявка Бизнес",
        "lead_form_type": "forma_podklyucheniya_biznes",
        "service_id": "2",
    }
    assert target["confirmation"] == {
        "kind": "url",
        "value": "https://mts-home-online.ru/tilda/form1/submitted",
    }
    assert target["crm_verification"] == {
        "status": "confirmed",
        "source": "user",
        "date": "2026-09-16",
        "note": "User confirmed that the single MTS production pilot arrived correctly in CRM.",
    }
    assert all(c["status"] == "excluded" for c in pages if c is not target)
    option = next(c for c in cases if c["case_id"] == "mts-business_option-d5a93099ffb1")
    assert option["status"] == "blocked"
    assert option["form"]["business_control"] == {
        "kind": "select",
        "selector": "select[name='Place']",
        "business_value": "Для бизнеса",
        "alternative_value": "В квартиру",
    }
    assert option["region"]["after_choice_url"] == option["entry_url"] == option["region"]["business_url"]
    assert "unchanged base URL after popup selection is expected" in option["reason"]
    assert option["verification"] == "docs/evidence/mts-business-option-select-20260916.md"
    mts_home = next(c for c in cases if c["case_id"] == "mts-business_option-5d75c21b6980")
    assert mts_home["status"] == "blocked"
    assert mts_home["entry_url"] == mts_home["region"]["business_url"] == mts_home["region"]["after_choice_url"]
    assert mts_home["region"]["choice_url"] == "https://samara.mts-home.online/"
    assert mts_home["form"]["business_control"]["business_value"] == "Для бизнеса"
    assert "CityName=Самара and City=36401" in mts_home["reason"]
    assert "stale Info is not a failure" in mts_home["reason"]
    assert mts_home["submission"] == {
        "url": "https://mts-home.online/wp-admin/admin-ajax.php",
        "method": "POST",
        "target_city": "Самара",
        "target_city_ui_id": "36401",
        "region_match": {"CityName": "Самара", "City": "36401"},
        "business_match": {"Place": "Для бизнеса"},
        "identity_match": {
            "FormName": "Проверьте подключение",
            "lead_form_type": "forma_proverit'_adress",
            "service_id": "2",
        },
        "evidence": "Blocked production submit captured 2026-09-16; only the selected Samara/business field values and field names were retained; no request left the browser.",
        "response_pending": True,
    }
    assert mts_home["verification"] == "docs/evidence/mts-home-online-business-option-20260916.md"
    duplicate = next(c for c in cases if c["case_id"] == "mts-business_option-e34df24cb0a9")
    assert duplicate["status"] == "excluded"
    assert "Exact normalized duplicate" in duplicate["reason"]
