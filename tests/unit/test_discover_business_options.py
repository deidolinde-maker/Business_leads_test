from tools.discover_business_options import classify, clean_url, select_candidates, template_key


def test_select_candidates_deduplicates_urls_and_keeps_source_case_ids():
    cases = [
        {"case_id": "one", "status": "blocked", "flow_kind": "business_option", "provider": "mts", "source_page_url": "https://example.test/"},
        {"case_id": "two", "status": "blocked", "flow_kind": "business_option", "provider": "mts", "entry_url": "https://example.test/?region=1"},
        {"case_id": "three", "status": "active", "flow_kind": "business_option", "provider": "mts", "source_page_url": "https://active.test/"},
    ]
    assert clean_url("https://example.test/?region=1#form") == "https://example.test/"
    assert select_candidates(cases, "mts", set(), 0, 12) == [
        {"url": "https://example.test/", "case_ids": ["one", "two"]}
    ]
    assert select_candidates(cases, "mts", set(), 1, 12) == []


def test_classify_requires_city_ui_and_business_control_for_candidate():
    assert classify({"business_controls": [{"tag": "select"}], "city_ui": {
        "indicator": {"ui_id": "36401"}, "search_present": True, "samara_choice_present": True,
    }}) == (
        "candidate: business control and city UI observed"
    )
    assert classify({"business_controls": [{"tag": "input"}], "city_ui": {}}) == (
        "review: business control observed; city UI not observed"
    )
    assert classify({"business_controls": [{"tag": "input"}], "city_ui": {"search_present": True, "samara_choice_present": True}}) == (
        "review: business control observed; city UI not observed"
    )
    assert classify({"business_controls": [], "city_ui": {}}) == "skip: no business control observed"


def test_template_key_ignores_transient_form_class_and_keeps_host():
    result = {
        "url": "https://example.test/source",
        "final_url": "https://example.test/final",
        "business_controls": [{
            "tag": "select", "name": "Place", "options": ["В квартиру", "Для бизнеса"],
            "form_class": "checkaddress__form",
        }],
    }
    assert template_key(result) == (
        'example.test:[{"form_class":"checkaddress__form","name":"Place",'
        '"options":["В квартиру","Для бизнеса"],"tag":"select"}]'
    )
