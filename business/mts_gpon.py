"""MTS GPON A/B business flow.

The legacy branch remains owned by the standard business runner.  The new
branch is selected only by the landing marker in localStorage.
"""

import json
import shutil
import time
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect

from business.artifacts import build_submission_lookup, utc_now, write_submission_lookup
from business.errors import BusinessCheckError
from business.runner import _finish_video, _submitted_form_payload


MARKER_KEY = "landing-yandex-events:v1"
NEW_HOST = "mts-home-gpon.ru"


def _is_new_variant(page) -> bool:
    try:
        # The value is intentionally ignored; key presence selects the new
        # version, exactly as in Everyday_test.
        return bool(page.evaluate("key => window.localStorage.getItem(key) !== null", MARKER_KEY))
    except Exception:
        # A storage read failure must preserve the stable legacy path.
        return False


def _wait_for_variant_marker(page, timeout_ms: int = 5_000) -> bool:
    end = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < end:
        if _is_new_variant(page):
            return True
        page.wait_for_timeout(200)
    return False


def _first_visible(locator):
    for index in range(locator.count()):
        candidate = locator.nth(index)
        try:
            if candidate.is_visible():
                return candidate
        except Exception:
            continue
    return None


def _form(page, placement: str):
    form = _first_visible(page.locator(f'[data-form-placement="{placement}"]'))
    if form is None:
        raise BusinessCheckError(f"mts_gpon_{placement}_form_not_found")
    return form


def _click_region_accept(page, timeout: int) -> None:
    for selector in ("[data-testid='mts-city-selector-accept']", "#yesButton"):
        button = page.locator(selector).first
        if button.count() == 1 and button.is_visible():
            button.click(force=True, timeout=timeout)
            page.wait_for_timeout(300)
            return


def _dismiss_cookie(page, timeout: int) -> None:
    for selector in (
        "#cookieButton", "#cookieAccept", "#cookie-accept",
        ".cookie-accept", "[data-testid='cookie-accept']",
    ):
        button = page.locator(selector).first
        if button.count() == 1 and button.is_visible():
            button.click(force=True, timeout=timeout)
            page.wait_for_timeout(200)
            return


def _choose_samara(page, form, timeout: int) -> None:
    _dismiss_cookie(page, min(timeout, 3_000))
    _click_region_accept(page, min(timeout, 3_000))
    region = form.get_by_test_id("mts-address-region-input")
    if region.count() == 0:
        return
    current = region.input_value(timeout=min(timeout, 2_000))
    if current.strip() == "Самара":
        return
    region.click(timeout=timeout)
    dialog = page.get_by_role("dialog", name="Выбор региона", exact=True)
    expect(dialog).to_be_visible(timeout=timeout)
    search = dialog.get_by_test_id("mts-select-region-search")
    awaitable = search.fill("Самара")
    # Playwright sync API returns immediately; keeping this assignment makes
    # the operation explicit for the step diagnostics.
    _ = awaitable
    option = dialog.get_by_test_id("mts-select-region-option").filter(has_text="Самара").first
    expect(option).to_be_visible(timeout=timeout)
    option.click(timeout=timeout)
    expect(dialog).to_be_hidden(timeout=timeout)


def _pick_first_suggestion(form, test_id: str, timeout: int) -> None:
    suggestion = form.get_by_test_id(test_id).first
    expect(suggestion).to_be_visible(timeout=timeout)
    suggestion.click(timeout=timeout)


def _request_payload(request):
    try:
        value = request.post_data_json
        return value if isinstance(value, dict) else {"raw": request.post_data or ""}
    except Exception:
        return {"raw": request.post_data or ""}


def _run_new_variant(
    browser, case: dict, data: dict, output: Path, budget: float, storage_state=None
) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + budget
    context = browser.new_context(
        viewport={"width": 1366, "height": 900},
        record_video_dir=str(output / ".video"),
        record_video_size={"width": 1366, "height": 900},
        storage_state=storage_state,
    )
    page = context.new_page()
    final_requests = []
    page.on("request", lambda request: final_requests.append(request)
            if "/api/orders" in request.url and request.method == "POST" else None)
    started = None
    confirmed = None
    initial_payload = {}
    final_payload = {}
    result = {
        "case_id": case["case_id"],
        "environment": case["environment"],
        "region_mode": case["region"]["mode"],
        "target_city": "Самара",
        "site_variant": "mts_gpon_new",
        "status": "failed",
    }
    try:
        if (urlsplit(case["entry_url"]).hostname or "").lower() != NEW_HOST:
            raise BusinessCheckError("mts_gpon_variant_requires_root_host")
        response = page.goto(case["entry_url"], wait_until="domcontentloaded", timeout=max(1_000, int((deadline - time.monotonic()) * 1000)))
        if response and response.status >= 400:
            raise BusinessCheckError("navigation_failed")
        if not _wait_for_variant_marker(page):
            raise BusinessCheckError("mts_gpon_new_marker_missing")

        form = _form(page, "home-primary")
        region = form.get_by_test_id("mts-address-region-input")
        _choose_samara(page, form, max(1_000, int((deadline - time.monotonic()) * 1000)))
        business = form.get_by_test_id("mts-address-place-segment").filter(has_text="Для бизнеса").first
        if business.count() == 0:
            business = form.get_by_role("button", name="Для бизнеса", exact=True).first
        expect(business).to_be_visible(timeout=5_000)
        business.click(timeout=5_000)

        street = form.get_by_test_id("mts-address-street-input")
        house = form.get_by_test_id("mts-address-house-input")
        phone = form.get_by_test_id("mts-address-phone-input")
        # The business variant has separate street/house inputs, but no
        # autocomplete lists.  Suggestions belong to the ordinary
        # checkaddress flow and must not be awaited here.
        street.fill(str(data["street"]))
        house.fill(str(data["house"]))
        phone.fill(str(data["phone"]))
        expect(region).to_have_value("Самара", timeout=5_000)
        if "Ленинградская" not in street.input_value(timeout=5_000):
            raise BusinessCheckError("mts_gpon_street_not_samara_address")
        if not house.input_value(timeout=5_000).strip().startswith("1"):
            raise BusinessCheckError("mts_gpon_house_not_samara_address")
        initial_payload = _submitted_form_payload(form)
        started = utc_now()
        form.get_by_test_id("mts-address-submit").click(timeout=5_000)
        page.wait_for_url("**/tilda/form1/submitted**", timeout=25_000)
        confirmed = utc_now()

        if not data.get("inn") or not data.get("email"):
            raise BusinessCheckError("mts_gpon_final_details_missing")
        inn = page.get_by_test_id("mts-thanks-inn-input")
        email = page.get_by_test_id("mts-thanks-email-input")
        inn.fill(str(data["inn"]))
        email.fill(str(data["email"]))
        service_id = case.get("new_flow", {}).get("service_id", "office-internet")
        service = page.get_by_test_id(f"mts-thanks-service-{service_id}")
        # The service selector is present only on the corresponding Thanks
        # variant.  It is optional for business flow; never call is_checked()
        # on an absent locator because Playwright would wait 30 seconds and
        # prevent the final submit.
        if service.count() > 0:
            if not service.is_checked(timeout=5_000):
                service.check(timeout=5_000)
            expect(service).to_be_checked(timeout=5_000)
        final_submit = page.get_by_test_id("mts-thanks-services-submit-button")
        expect(final_submit).to_be_visible(timeout=10_000)
        final_submit.click(timeout=10_000)
        expect(page.get_by_test_id("mts-thanks-title")).to_have_text("Заявка в работе!", timeout=20_000)
        if not final_requests:
            raise BusinessCheckError("mts_gpon_final_order_request_not_observed")
        final_payload = _request_payload(final_requests[-1])
        result["confirmation_observed"] = {"kind": "url", "value": page.url}
        result["confirmation_observed_at_utc"] = utc_now()
        result["submitted_payload"] = {"initial": initial_payload, "final": final_payload}
        result["status"] = "passed"
        return result
    except Exception as exc:
        result["error"] = str(exc)
        result["submitted_payload"] = {"initial": initial_payload, "final": final_payload}
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
                submitted_payload={"initial": initial_payload, "final": final_payload},
            ),
        )
        _finish_video(page, context, output, keep=result["status"] == "failed")


def run_mts_gpon_case(browser, case: dict, data: dict, output: Path, budget: float, standard_runner) -> dict:
    """Detect the A/B marker, preserving the existing legacy branch."""
    probe = browser.new_context()
    page = probe.new_page()
    storage_state = None
    try:
        page.goto(case["entry_url"], wait_until="domcontentloaded", timeout=15_000)
        new_variant = _wait_for_variant_marker(page)
        if new_variant:
            # The working context must inherit localStorage; otherwise the
            # second navigation can incorrectly look like the legacy version.
            storage_state = probe.storage_state()
    finally:
        probe.close()
    if new_variant:
        return _run_new_variant(browser, case, data, output, budget, storage_state)
    return standard_runner(browser, case, data, output, budget)
