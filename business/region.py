import re
from urllib.parse import urljoin

from playwright.sync_api import expect

from business.cases import CITY_NAME, CITY_UI_ID
from business.errors import BusinessCheckError


def assert_samara(form, region: dict, deadline):
    indicator = form.locator(region["indicator"])
    expect(indicator).to_have_count(1, timeout=deadline.ms())
    expect(indicator).to_be_visible(timeout=deadline.ms())
    expect(indicator).to_have_text(CITY_NAME, timeout=deadline.ms())
    expect(indicator).to_have_attribute("data-item", CITY_UI_ID, timeout=deadline.ms())
    return {"name": CITY_NAME, "ui_id": CITY_UI_ID}


def ensure_samara(page, form, case, adapter, deadline):
    region = case["region"]
    if region["mode"] == "direct_city_subdomain":
        expect(page).to_have_url(region["business_url"], timeout=deadline.ms())
        assert_samara(form, region, deadline)
        return form

    # Some landing pages first ask visitors to confirm the browser-detected
    # city. Choosing "change region" is the only route into the verified city
    # picker; clicking the form-level trigger underneath leaves both dialogs
    # open and prevents selecting Samara.
    initial_trigger = region.get("initial_trigger")
    if initial_trigger:
        initial = page.locator(initial_trigger)
        if initial.count() == 1 and initial.is_visible():
            initial.click(timeout=deadline.ms())
        else:
            initial_trigger = None
    if not initial_trigger:
        trigger = form.locator(region["trigger"])
        expect(trigger).to_have_count(1, timeout=deadline.ms())
        trigger.click(timeout=deadline.ms())
    popup = page.locator(region["popup"])
    expect(popup).to_have_count(1, timeout=deadline.ms())
    expect(popup).to_be_visible(timeout=deadline.ms())
    popup.locator(region["search"]).fill(CITY_NAME, timeout=deadline.ms())
    choice = popup.locator(region["choice"]).filter(has_text=re.compile(r"^\s*Самара\s*$"))
    expect(choice).to_have_count(1, timeout=deadline.ms())
    expect(choice).to_be_visible(timeout=deadline.ms())
    expect(choice).to_have_attribute("id", CITY_UI_ID, timeout=deadline.ms())
    href = choice.get_attribute("href")
    if not href or urljoin(page.url, href) != region["choice_url"]:
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
