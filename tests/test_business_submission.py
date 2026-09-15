from pathlib import Path

import allure
import pytest

from business.runner import run_case


@pytest.mark.live
def test_business_submission(business_case, request):
    case = business_case
    allure.dynamic.title(f"{case['case_id']} | Самара")
    if case["status"] == "excluded":
        pytest.skip(case["reason"])
    if case["status"] == "blocked":
        pytest.fail(f"BLOCKED: {case['reason']}", pytrace=False)
    # Resolve data before browser startup. A blocked case never launches a browser.
    data = request.getfixturevalue("live_data")
    browser = request.getfixturevalue("browser")
    output = Path(request.config.getoption("--artifact-dir")) / case["case_id"]
    try:
        run_case(browser, case, data, output)
    finally:
        report = output / "result.json"
        if report.exists():
            allure.attach.file(str(report), name="business-result", attachment_type=allure.attachment_type.JSON)
