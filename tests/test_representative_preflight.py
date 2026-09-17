"""Non-submitting CI preflight for the reviewed Samara representative scope."""


def test_representative_case_is_ready_for_live_submission(business_case):
    """Validate the reviewed contract only; this test never opens a browser or submits a lead."""
    assert business_case["status"] == "active"
    assert business_case["target_city"] == "Самара"
    assert business_case["target_city_ui_id"] == "36401"
    assert business_case["submission"]["target_city"] == "Самара"
    assert business_case["submission"]["target_city_ui_id"] == "36401"
    assert business_case["confirmation"]["value"]
