import re
from urllib.parse import urljoin

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, expect

from business.cases import CITY_NAME, CITY_UI_ID
from business.errors import BusinessCheckError


def assert_samara(form, region: dict, deadline):
    indicator = form.locator(region["indicator"])
    expect(indicator).to_have_count(1, timeout=deadline.ms())
    expect(indicator).to_be_visible(timeout=deadline.ms())
    expect(indicator).to_have_text(CITY_NAME, timeout=deadline.ms())
    # City subdomains can render the already-selected city without the popup's
    # numeric data-item attribute. Popup flows still require the verified ID.
    observed_id = indicator.get_attribute("data-item")
    if observed_id and observed_id != CITY_UI_ID:
        raise BusinessCheckError("unexpected_samara_indicator_id")
    return {"name": CITY_NAME, "ui_id": CITY_UI_ID}


def ensure_samara(page, form, case, adapter, deadline):
    region = case["region"]
    if region["mode"] == "direct_city_subdomain":
        expect(page).to_have_url(region["business_url"], timeout=deadline.ms())
        assert_samara(form, region, deadline)
        return form

    # Some landing pages already have Samara selected when the browser opens.
    # Do not reopen the picker and treat the unchanged popup as a failure.
    indicator = form.locator(region["indicator"])
    if indicator.count() == 1 and indicator.is_visible():
        try:
            if CITY_NAME in (indicator.inner_text(timeout=min(2_000, deadline.ms())) or ""):
                return form
        except Exception:
            pass

    # Some landing pages first ask visitors to confirm the browser-detected
    # city. Close that prompt, then open the picker from the target form: on
    # Beeline this is what writes the selected city into that form's fields.
    initial_dismiss = region.get("initial_dismiss")
    if initial_dismiss:
        initial = page.locator(initial_dismiss)
        try:
            initial.wait_for(state="visible", timeout=min(3_000, deadline.ms()))
            initial.click(timeout=deadline.ms())
        except PlaywrightTimeoutError:
            pass
    trigger = form.locator(region["trigger"])
    expect(trigger).to_have_count(1, timeout=deadline.ms())
    trigger.click(timeout=deadline.ms())
    popup = page.locator(region["popup"])
    expect(popup).to_have_count(1, timeout=deadline.ms())
    try:
        popup.wait_for(state="visible", timeout=min(1_500, deadline.ms()))
    except PlaywrightTimeoutError:
        # Some business templates render the same city control but attach the
        # popup handler to the visible city label instead of its wrapper.
        indicator = form.locator(region["indicator"])
        expect(indicator).to_have_count(1, timeout=deadline.ms())
        indicator.click(timeout=deadline.ms())
    expect(popup).to_be_visible(timeout=deadline.ms())
    popup.locator(region["search"]).fill(CITY_NAME, timeout=deadline.ms())
    choice = popup.locator(region["choice"]).filter(has_text=re.compile(r"^\s*Самара\s*$"))
    expect(choice).to_have_count(1, timeout=deadline.ms())
    expect(choice).to_be_visible(timeout=deadline.ms())
    expect(choice).to_have_attribute("id", CITY_UI_ID, timeout=deadline.ms())
    href = choice.get_attribute("href")
    actual_choice_url = urljoin(page.url, href) if href else ""
    expected_choice_url = region["choice_url"]
    if actual_choice_url.rstrip("/") != expected_choice_url.rstrip("/"):
        raise BusinessCheckError("unexpected_samara_choice_href")
    choice.click(timeout=deadline.ms())
    if region["after_choice_url"] != case["entry_url"]:
        page.wait_for_url(region["after_choice_url"], wait_until="domcontentloaded", timeout=deadline.ms())
    else:
        expect(popup).to_be_hidden(timeout=deadline.ms())
    # /samara need not be a business page. The next URL comes from a verified case, never concatenation.
    if page.url != region["business_url"]:
        response = page.goto(region["business_url"], wait_until="domcontentloaded", timeout=deadline.ms())
        if response and response.status >= 400:
            raise BusinessCheckError("samara_business_navigation_failed")
    expect(page).to_have_url(region["business_url"], timeout=deadline.ms())
    form = adapter.open_form(page, case, deadline)
    assert_samara(form, region, deadline)
    return form
