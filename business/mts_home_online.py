"""MTS Home Online business-page A/B flow.

The classic WordPress branch stays on the existing business-page runner.  The
new branch is selected from the site's ``site_version`` console marker, with
the documented ``data-address-form`` DOM fallback.
"""

import json
import re
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from playwright.sync_api import expect

from business.artifacts import build_submission_lookup, utc_now, write_submission_lookup
from business.errors import BusinessCheckError
from business.runner import _finish_video, _submitted_form_payload


HOST = "mts-home-online.ru"
NEW_VERSION = "wordpress_new"
OLD_VERSION = "wordpress_old"
DEBUG_QUERY = "_ym_debug=1"
SUCCESS_URL = "/tilda/form1/submitted"


def _with_debug_query(url: str) -> str:
    parsed = urlsplit(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("_ym_debug", "1")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))


def _visible(root, selector):
    candidates = root.locator(selector)
    for index in range(candidates.count()):
        candidate = candidates.nth(index)
        try:
            if candidate.is_visible():
                return candidate
        except Exception:
            pass
    return None


def _site_version_from_console(page, holder):
    value = holder[0]
    if value in {NEW_VERSION, OLD_VERSION}:
        return value
    # Hydration is asynchronous: immediately after domcontentloaded the form
    # may not exist yet.  Everyday_test waits for the marker and then falls
    # back to the data-address-form DOM, so use the same tolerant probe here.
    selectors = (
        "form[data-address-form] [data-street-input], "
        "form[data-address-form] [data-house-input], "
        "form[data-address-form] [data-lead-submit], "
        "form[data-address-form] [data-business-street-input], "
        "form[data-address-form] [data-business-house-input]",
    )
    deadline = time.monotonic() + 5
    has_new_form = False
    while time.monotonic() < deadline:
        try:
            has_new_form = page.locator(selectors[0]).count() > 0
        except Exception:
            has_new_form = False
        if has_new_form:
            break
        page.wait_for_timeout(250)
    return NEW_VERSION if has_new_form else OLD_VERSION


def _capture_version(page):
    holder = [None]

    def on_console(message):
        text = (message.text or "").strip()
        match = re.search(
            r"[\"']?site_version[\"']?\s*[:=]\s*[\"']?(wordpress_(?:new|old))",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            holder[0] = match.group(1)
        elif text in {NEW_VERSION, OLD_VERSION}:
            holder[0] = text
        if holder[0] is None:
            # Yandex debug sometimes sends the payload as a console argument
            # rather than rendered message text (the Everyday implementation
            # inspects message.args for this case).
            try:
                for argument in message.args:
                    value = argument.json_value()
                    if isinstance(value, dict):
                        candidate = value.get("site_version")
                        if candidate in {NEW_VERSION, OLD_VERSION}:
                            holder[0] = candidate
                            break
            except Exception:
                pass

    page.on("console", on_console)
    return holder


def _dismiss_cookie(page):
    for selector in ("#cookieButton", "#cookieAccept", ".cookie-accept", "[data-testid='cookie-accept']"):
        button = page.locator(selector).first
        try:
            if button.count() and button.is_visible():
                button.click(force=True, timeout=3000)
                return
        except Exception:
            pass


def _find_active_form(page, timeout_ms: int = 15_000):
    end = time.monotonic() + timeout_ms / 1000
    selector = "form[data-address-form][data-form-type='connection_address']"
    while time.monotonic() < end:
        forms = page.locator(selector)
        for index in range(forms.count() - 1, -1, -1):
            form = forms.nth(index)
            try:
                if not form.is_visible():
                    continue
                street = form.locator("[data-business-street-input]").first
                house = form.locator("[data-business-house-input]").first
                phone = form.locator("input[name='Phone']").first
                if street.count() and house.count() and phone.count():
                    return form
            except Exception:
                continue
        page.wait_for_timeout(200)
    raise BusinessCheckError("mts_home_online_business_form_not_found")


def _open_business_form(page):
    form = _visible(page, "form[data-address-form][data-form-type='connection_address']")
    if form is not None:
        return _find_active_form(page)
    trigger = _visible(page, "button")
    buttons = page.get_by_role("button", name="Проверить адрес", exact=True)
    for index in range(buttons.count()):
        candidate = buttons.nth(index)
        if candidate.is_visible():
            candidate.click(timeout=10_000)
            return _find_active_form(page)
    raise BusinessCheckError("mts_home_online_business_form_trigger_not_found")


def _select_samara(form, timeout_ms: int = 10_000):
    city = form.locator("[data-city-input]").first
    expect(city).to_be_visible(timeout=timeout_ms)
    if (city.input_value(timeout=timeout_ms) or "").strip() == "Самара":
        return
    city.click(timeout=timeout_ms)
    city.fill("Самара", timeout=timeout_ms)
    option = _visible(form, "[data-city-list] button, [data-city-list] [role='option'], .popup-select-region__item")
    if option is None:
        option = form.get_by_role("button", name="Самара", exact=True).first
    expect(option).to_be_visible(timeout=timeout_ms)
    option.click(timeout=timeout_ms)
    form.page.wait_for_timeout(400)
    expect(city).to_have_value("Самара", timeout=timeout_ms)


def _fill_phone(locator, value: str, timeout_ms: int):
    if not re.fullmatch(r"\d{10}", value):
        raise BusinessCheckError("phone_must_contain_exactly_10_digits")
    locator.click(force=True, timeout=timeout_ms)
    locator.press_sequentially(value, delay=70, timeout=timeout_ms)
    locator.blur(timeout=timeout_ms)
    digits = re.sub(r"\D", "", locator.input_value(timeout=timeout_ms))
    if len(digits) == 11 and digits.startswith(("7", "8")):
        digits = digits[1:]
    if digits != value:
        raise BusinessCheckError("phone_not_fully_entered")


def _payload(request):
    try:
        value = request.post_data_json
        return value if isinstance(value, dict) else {"raw": request.post_data or ""}
    except Exception:
        return {"raw": request.post_data or ""}


def _run_new(browser, case, data, output: Path, budget: float, context, page):
    output.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + budget
    requests = []
    page.on("request", lambda request: requests.append(request)
            if request.method == "POST" and ("/api/orders" in request.url or "feedback" in request.url)
            else None)
    result = {
        "case_id": case["case_id"],
        "environment": case["environment"],
        "region_mode": case["region"]["mode"],
        "target_city": "Самара",
        "site_variant": "mts_home_online_new",
        "status": "failed",
    }
    started = None
    confirmed = None
    payload = {}
    try:
        url = _with_debug_query(case["entry_url"])
        response = page.goto(url, wait_until="domcontentloaded", timeout=max(1_000, int((deadline - time.monotonic()) * 1000)))
        if response and response.status >= 400:
            raise BusinessCheckError("navigation_failed")
        _dismiss_cookie(page)
        form = _open_business_form(page)
        business = form.locator("[data-segment='business']").first
        if business.count() and business.is_visible():
            business.click(timeout=10_000)
        expect(form).to_have_attribute("data-active-segment", "business", timeout=10_000)
        _select_samara(form)

        street = form.locator("[data-business-street-input]").first
        house = form.locator("[data-business-house-input]").first
        phone = form.locator("input[name='Phone']").first
        expect(street).to_be_visible(timeout=10_000)
        expect(house).to_be_visible(timeout=10_000)
        street.fill(str(data["street"]), timeout=10_000)
        house.fill(str(data["house"]), timeout=10_000)
        _fill_phone(phone, str(data["phone"]), 10_000)
        if "Ленинградская" not in street.input_value(timeout=5000):
            raise BusinessCheckError("mts_home_online_street_not_samara_address")
        if not house.input_value(timeout=5000).strip().startswith("1"):
            raise BusinessCheckError("mts_home_online_house_not_samara_address")
        payload = _submitted_form_payload(form)
        started = utc_now()
        submit = form.locator("[data-lead-submit]").first
        expect(submit).to_be_visible(timeout=10_000)
        submit.click(timeout=10_000)
        page.wait_for_url("**/tilda/form1/submitted", timeout=25_000)
        confirmed = utc_now()
        initial_request = _payload(requests[-1]) if requests else {}
        result["intermediate_confirmation"] = {"kind": "url", "value": page.url}

        # The business thank-you page is a three-step flow.  The first URL
        # only confirms the address request; the lead is complete after INN,
        # email and service selection are submitted.
        details = page.locator("[data-thanks-business-details-form]").first
        expect(details).to_be_visible(timeout=20_000)
        details.locator("input[name='inn']").fill(str(data["inn"]), timeout=10_000)
        details.locator("input[name='email']").fill(str(data["email"]), timeout=10_000)
        details.locator("button.thanks__biz-submit").click(timeout=10_000)

        services_form = page.locator("[data-thanks-business-services-form]").first
        expect(services_form).to_be_visible(timeout=20_000)
        service_name = case.get("new_flow", {}).get("service_name", "Интернет в офис")
        services = services_form.locator("input[name='services[]']")
        selected = None
        for index in range(services.count()):
            candidate = services.nth(index)
            if (candidate.get_attribute("value") or "").strip() == service_name:
                selected = candidate
                break
        if selected is None:
            raise BusinessCheckError("mts_home_online_service_not_found")
        selected.check(timeout=10_000)
        expect(selected).to_be_checked(timeout=5_000)
        services_form.locator("button.thanks__biz-submit").click(timeout=10_000)
        services_form.wait_for(state="hidden", timeout=20_000)
        expect(page.get_by_role("heading", name="Заявка в работе!", exact=True)).to_be_visible(timeout=20_000)

        if not requests:
            raise BusinessCheckError("mts_home_online_order_request_not_observed")
        result["confirmation_observed"] = {"kind": "url", "value": page.url}
        result["confirmation_observed_at_utc"] = utc_now()
        result["submitted_payload"] = {
            "initial": payload,
            "address_request": initial_request,
            "final": _payload(requests[-1]),
            "inn": str(data["inn"]),
            "email": str(data["email"]),
            "services": [service_name],
        }
        result["status"] = "passed"
        return result
    except Exception as exc:
        result["error"] = str(exc)
        result["submitted_payload"] = {"final": payload}
        raise BusinessCheckError(result["error"]) from None
    finally:
        result["submission_started_at_utc"] = started
        result["phase_seconds"] = {}
        (output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        write_submission_lookup(
            output,
            build_submission_lookup(
                case,
                data,
                result,
                submission_started_at_utc=started,
                confirmation_observed_at_utc=confirmed,
                submitted_payload=result.get("submitted_payload", {}),
            ),
        )
        _finish_video(page, context, output, keep=result["status"] == "failed")


def run_mts_home_online_case(browser, case, data, output: Path, budget: float, standard_runner):
    """Run the new MTS business form, preserving the classic branch."""
    output.mkdir(parents=True, exist_ok=True)
    context = browser.new_context(
        viewport={"width": 1366, "height": 900},
        record_video_dir=str(output / ".video"),
        record_video_size={"width": 1366, "height": 900},
    )
    page = context.new_page()
    holder = _capture_version(page)
    new_variant = False
    try:
        # Everyday_test determines the MTS Online A/B branch on the root URL
        # with the diagnostic query, then reuses that decision for /business.
        root = f"{urlsplit(case['entry_url']).scheme}://{HOST}/"
        response = page.goto(_with_debug_query(root), wait_until="domcontentloaded", timeout=15_000)
        if response and response.status >= 400:
            raise BusinessCheckError("navigation_failed")
        version = _site_version_from_console(page, holder)
        if version == NEW_VERSION:
            new_variant = True
            return _run_new(browser, case, data, output, budget, context, page)
    finally:
        if not new_variant:
            context.close()
    return standard_runner(browser, case, data, output, budget)
