from pathlib import Path

import allure
import pytest

from business.runner import run_case


@pytest.mark.live
def test_business_submission(business_case, request):
    case = business_case
    allure.dynamic.title(f"{case['case_id']} | Самара")
    allure.dynamic.description(
        "Бизнес-заявка: открыть форму, выбрать Самару, заполнить адрес и телефон, "
        "отправить и дождаться страницы Спасибо."
    )
    allure.dynamic.suite("Бизнес-заявки")
    allure.dynamic.sub_suite(case["provider"])
    allure.dynamic.label("provider", case["provider"])
    allure.dynamic.parameter("environment", case["environment"])
    allure.dynamic.parameter("region", "Самара")
    allure.dynamic.parameter("entry_url", case["entry_url"])
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
        screenshot = output / "failure.png"
        if screenshot.exists():
            allure.attach.file(str(screenshot), name="failure-screenshot",
                               attachment_type=allure.attachment_type.PNG)
        video = output / "failure.webm"
        if video.exists():
            allure.attach.file(str(video), name="failure-video",
                               attachment_type="video/webm", extension="webm")
