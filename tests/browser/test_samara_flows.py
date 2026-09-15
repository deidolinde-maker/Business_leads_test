import json

import pytest

from business.errors import BusinessCheckError
from business.runner import run_case
from tests.support import DATA, make_case


@pytest.mark.parametrize("mode", ["popup_selection", "direct_city_subdomain"])
def test_samara_flow_sends_once(browser, local_site, tmp_path, mode):
    base, state = local_site
    result = run_case(browser, make_case(base, mode), DATA, tmp_path, budget=10)
    assert result["status"] == "passed"
    assert state["received"] == [{"form": "lead-fixture", "business": True, "region": "samara-fixture"}]
    if mode == "popup_selection":
        assert "/samara" in state["gets"] and "/samara/business" in state["gets"]
    else:
        assert state["gets"][0] == "/direct/business"
        assert "/samara" not in state["gets"]


@pytest.mark.parametrize("fault,reason", [("payload", "region_mismatch"), ("ordinary", "business_mismatch"),
                                          ("city-reset", None), ("false-thanks", "submission_not_confirmed")])
def test_wrong_city_or_nonbusiness_never_reaches_server(browser, local_site, tmp_path, fault, reason):
    base, state = local_site
    with pytest.raises(BusinessCheckError, match=reason):
        run_case(browser, make_case(base, fault=fault), DATA, tmp_path, budget=3)
    assert state["received"] == []
    result = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "failed"
    assert result["submission"]["forwarded"] == 0


def test_duplicate_click_request_is_blocked(browser, local_site, tmp_path):
    base, state = local_site
    with pytest.raises(BusinessCheckError, match="duplicate_submission"):
        run_case(browser, make_case(base, fault="duplicate"), DATA, tmp_path, budget=5)
    assert len(state["received"]) == 1


def test_rejected_response_is_failure_without_retry(browser, local_site, tmp_path):
    base, state = local_site
    state["reject"] = True
    with pytest.raises(BusinessCheckError, match="response_mismatch"):
        run_case(browser, make_case(base), DATA, tmp_path, budget=5)
    assert len(state["received"]) == 1


def test_failed_case_cannot_be_covered_by_previous_success(browser, local_site, tmp_path):
    base, state = local_site
    run_case(browser, make_case(base), DATA, tmp_path / "passed", budget=5)
    with pytest.raises(BusinessCheckError):
        run_case(browser, make_case(base, fault="payload"), DATA, tmp_path / "failed", budget=5)
    assert len(state["received"]) == 1
    assert json.loads((tmp_path / "passed/result.json").read_text())["status"] == "passed"
    assert json.loads((tmp_path / "failed/result.json").read_text())["status"] == "failed"


def test_radio_variants_finish_in_business_samara(browser, local_site, tmp_path):
    base, state = local_site
    case = make_case(base, fault="radio")
    case["form"]["business_control"] = {"kind": "radio", "selector": "#office", "alternative": "#home"}
    result = run_case(browser, case, DATA, tmp_path, budget=5)
    assert result["status"] == "passed"
    assert len(state["received"]) == 1 and state["received"][0]["business"] is True


def test_exact_city_id_required_in_popup(browser, local_site, tmp_path):
    base, state = local_site
    with pytest.raises(BusinessCheckError):
        run_case(browser, make_case(base, mode="popup_selection", fault="wrong-choice"), DATA, tmp_path, budget=3)
    assert not state["received"]
