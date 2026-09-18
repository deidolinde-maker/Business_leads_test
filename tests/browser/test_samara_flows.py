import json
from urllib.parse import urlsplit

import pytest

from business.errors import BusinessCheckError
from business.runner import run_case
from tests.support import DATA, make_case


@pytest.mark.parametrize("mode", ["popup_selection", "direct_city_subdomain"])
def test_samara_flow_reaches_thanks(browser, local_site, tmp_path, mode):
    base, state = local_site
    result = run_case(browser, make_case(base, mode), DATA, tmp_path, budget=10)

    assert result["status"] == "passed"
    assert result["confirmation_observed"] == {"kind": "locator", "value": "#thanks:visible"}
    assert "submission" not in result
    assert not (tmp_path / "failure.webm").exists()
    if mode == "popup_selection":
        assert "/samara" in state["gets"] and "/samara/business" in state["gets"]
    else:
        assert state["gets"][0] == "/direct/business"
        assert "/samara" not in state["gets"]


def test_business_option_allows_samara_popup_without_url_change(browser, local_site, tmp_path):
    base, state = local_site
    case = make_case(base, mode="popup_selection", fault="in-place-city")
    case["region"]["business_url"] = case["entry_url"]
    case["region"]["after_choice_url"] = case["entry_url"]

    result = run_case(browser, case, DATA, tmp_path, budget=5)

    assert result["status"] == "passed"
    assert not any(urlsplit(path).path.startswith("/samara") for path in state["gets"])


def test_city_label_opens_picker_when_wrapper_handler_is_absent(browser, local_site, tmp_path):
    base, state = local_site

    result = run_case(
        browser,
        make_case(base, mode="popup_selection", fault="trigger-fallback"),
        DATA,
        tmp_path,
        budget=8,
    )

    assert result["status"] == "passed"
    assert "/samara" in state["gets"]


def test_city_reset_stops_before_submit(browser, local_site, tmp_path):
    base, _state = local_site

    with pytest.raises(BusinessCheckError):
        run_case(browser, make_case(base, fault="city-reset"), DATA, tmp_path, budget=3)

    result = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "failed"
    assert "submission" not in result
    assert result["ui_after_error"]["url"].startswith("http://127.0.0.1:")
    assert (tmp_path / "failure.png").exists()
    assert (tmp_path / "failure.webm").exists()


def test_failed_case_cannot_be_covered_by_previous_success(browser, local_site, tmp_path):
    base, _state = local_site
    run_case(browser, make_case(base), DATA, tmp_path / "passed", budget=5)

    with pytest.raises(BusinessCheckError):
        run_case(browser, make_case(base, fault="city-reset"), DATA, tmp_path / "failed", budget=5)

    assert json.loads((tmp_path / "passed/result.json").read_text())["status"] == "passed"
    assert json.loads((tmp_path / "failed/result.json").read_text())["status"] == "failed"


def test_radio_business_option_reaches_thanks(browser, local_site, tmp_path):
    base, _state = local_site
    case = make_case(base, fault="radio")
    case["form"]["business_control"] = {"kind": "radio", "selector": "#office", "alternative": "#home"}

    assert run_case(browser, case, DATA, tmp_path, budget=5)["status"] == "passed"


def test_select_business_option_reaches_thanks(browser, local_site, tmp_path):
    base, _state = local_site
    case = make_case(base, fault="select")
    case["form"]["business_control"] = {
        "kind": "select",
        "selector": "#office",
        "business_value": "Для бизнеса",
        "alternative_value": "В квартиру",
    }

    assert run_case(browser, case, DATA, tmp_path, budget=5)["status"] == "passed"


def test_exact_city_id_required_in_popup(browser, local_site, tmp_path):
    base, _state = local_site

    with pytest.raises(BusinessCheckError):
        run_case(browser, make_case(base, mode="popup_selection", fault="wrong-choice"), DATA, tmp_path, budget=3)
