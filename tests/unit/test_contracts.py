import json

import pytest

from business.cases import (
    business_popup_allowed,
    load_cases,
    load_data,
    select_cases,
    select_representatives,
    validate_case,
)
from business.errors import ConfigurationError
from tests.support import make_case


def test_valid_synthetic_case():
    validate_case(make_case())


@pytest.mark.parametrize("field,value", [
    ("target_city", "Москва"),
    ("target_city_ui_id", "77"),
    ("environment", None),
    ("case_id", "../escape"),
])
def test_reject_unsafe_case_config(field, value):
    case = make_case()
    case[field] = value
    with pytest.raises(ConfigurationError):
        validate_case(case)


@pytest.mark.parametrize("field", ["provider", "entry_url", "form", "region", "confirmation", "verification"])
def test_active_case_requires_ui_flow_contract(field):
    case = make_case()
    case.pop(field)
    with pytest.raises(ConfigurationError, match="missing"):
        validate_case(case)


def test_active_case_does_not_require_network_contract():
    case = make_case()
    assert "submission" not in case
    validate_case(case)


@pytest.mark.parametrize("url", [
    "https://online-beeline.ru/business",
    "https://beeline-internet.online/business",
    "https://beeline-ru.online/business",
    "https://samara.beeline-ru.online/business/internet-dlya-biznesa",
    "https://rtk-home.ru/business",
    "https://rtk-ru.online/business",
    "https://samara.rtk-ru.online/business",
    "https://rtk-internet.online/business",
    "https://mts-home-online.ru/business",
])
def test_business_popup_scope_is_explicit(url):
    assert business_popup_allowed(url)


@pytest.mark.parametrize("url", [
    "https://mts-home.online/business",
    "https://samara.mts-home.online/business",
    "https://mega-home-internet.ru/business",
])
def test_business_popup_scope_rejects_other_hosts(url):
    assert not business_popup_allowed(url)


def test_blocked_case_does_not_need_browser_contract():
    case = make_case()
    case["status"] = "blocked"
    case["reason"] = "awaiting UI verification"
    for field in ("entry_url", "form", "region", "confirmation", "verification"):
        case.pop(field, None)
    validate_case(case)


def test_unconfirmed_environment_data_rejected(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps({
        "city": "Самара",
        "environment": None,
        "phone": "9999999999",
        "street": "Ленинградская",
        "house": "1",
    }), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="environment"):
        load_data(path, "prod")


@pytest.mark.parametrize("phone", ["999999999", "99999999999", "+79999999999", "99999abc99"])
def test_phone_must_be_exactly_ten_digits_outside_mask(tmp_path, phone):
    path = tmp_path / "data.json"
    path.write_text(json.dumps({
        "city": "Самара",
        "environment": "prod",
        "phone": phone,
        "street": "Ленинградская",
        "house": "1",
    }), encoding="utf-8")

    with pytest.raises(ConfigurationError, match="exactly 10 digits"):
        load_data(path, "prod")


def test_duplicate_cases_are_rejected(tmp_path):
    case = make_case()
    path = tmp_path / "cases.json"
    path.write_text(json.dumps({"cases": [case, case]}), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="duplicate"):
        load_cases(path)


def test_live_scope_contains_only_active_ui_flows():
    selected = select_cases(load_cases(), "prod", active_only=True)
    assert [case["case_id"] for case in selected] == [
        "beeline-business_option-afd9e17b2c35",
        "mts-business_page-c2d4cae355e7",
        "mts-business_option-5d75c21b6980",
        "beeline-business_page-samara-internet-dlya-biznesa",
        "beeline-business_page-samara-mobilnaya-svyaz-dlya-biznesa",
    ]
    assert all(case["target_city"] == "Самара" for case in selected)
    assert all(case["confirmation"]["value"] for case in selected)


def test_representative_scope_is_explicit_and_active():
    selected = select_representatives(load_cases(), "prod")
    assert [case["case_id"] for case in selected] == [
        "beeline-business_page-samara-mobilnaya-svyaz-dlya-biznesa",
        "mts-business_page-c2d4cae355e7",
        "beeline-business_option-afd9e17b2c35",
        "mts-business_option-5d75c21b6980",
    ]
    assert all(case["status"] == "active" for case in selected)


def test_mts_business_page_scope_is_single_confirmed_landing():
    pages = [
        case for case in load_cases()
        if case["provider"] == "mts" and case["flow_kind"] == "business_page"
    ]
    included = [case for case in pages if case["status"] != "excluded"]
    assert [case["source_page_url"] for case in included] == ["https://mts-home-online.ru/business"]
    assert included[0]["confirmation"] == {
        "kind": "url",
        "value": "https://mts-home-online.ru/tilda/form1/submitted",
    }


def test_beeline_option_uses_samara_popup_and_business_select():
    case = next(
        case for case in load_cases()
        if case["case_id"] == "beeline-business_option-afd9e17b2c35"
    )
    assert case["region"]["choice"] == "a.region_item.region_link[id='36401']"
    assert case["region"]["after_choice_url"] == "https://beeline-ru.online/"
    assert case["form"]["business_control"] == {
        "kind": "select",
        "selector": "select[name='Place']",
        "business_value": "Для бизнеса",
        "alternative_value": "В квартиру",
    }
    assert case["confirmation"] == {"kind": "url_contains", "value": "/thanks"}


def test_mts_option_uses_popup_relative_samara_locators():
    case = next(
        case for case in load_cases()
        if case["case_id"] == "mts-business_option-5d75c21b6980"
    )
    assert case["region"]["popup"] == "#popup-select-city"
    assert case["region"]["search"] == "input#city-input"
    assert case["region"]["choice"] == "a.region_item.region_link[id='36401']"
    assert case["form"]["fields"][:2] == [
        {
            "selector": ".checkaddress_address_street",
            "data_key": "street",
            "suggestion": "div.autocomplete-street:visible",
        },
        {
            "selector": ".checkaddress_address_house",
            "data_key": "house",
            "suggestion": "#house-list div.autocomplete-item:visible",
        },
    ]


def test_imported_scope_retains_samara_targets_and_provenance():
    cases = load_cases()
    assert cases
    assert all(case["target_city"] == "Самара" and case["source_refs"] for case in cases)
    assert any(case["flow_kind"] == "business_option" for case in cases)
