"""Inspect a business-option form state without preparing or submitting a lead."""

import argparse
import json
import os
import re
from pathlib import Path
from urllib.parse import parse_qs

from playwright.sync_api import Error, sync_playwright

try:
    from tools.discover_business_options import READ_ONLY_METHODS, clean_url
except ModuleNotFoundError:  # Direct CLI execution: python tools/inspect_business_option_state.py
    from discover_business_options import READ_ONLY_METHODS, clean_url

SUMMARY_FIELDS = ("CityName", "City", "Place", "IStreet", "IHouse", "FormName", "lead_form_type", "service_id")

def first_visible(scope, selectors: list[str]):
    for selector in selectors:
        candidate = scope.locator(selector)
        if candidate.count() and candidate.first.is_visible():
            return candidate.first, selector
    raise RuntimeError(f"No visible locator matched: {selectors}")


def payload_summary(request):
    """Keep only field names and Samara/business values from an aborted request."""
    raw = request.post_data or ""
    values = {key: value[-1] for key, value in parse_qs(raw).items()} if "multipart/form-data" not in raw and "\r\n" not in raw else {}
    names = set(values)
    for name in re.findall(r'name="([^"]+)"', raw):
        names.add(name)
        match = re.search(rf'name="{re.escape(name)}"\r?\n\r?\n([^\r\n]*)', raw)
        if match:
            values[name] = match.group(1)
    return {
        "field_names": sorted(names),
        "selected_values": {key: values[key] for key in SUMMARY_FIELDS if key in values},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only state inspection for a Place business option")
    parser.add_argument("--url", required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--street")
    parser.add_argument("--house")
    parser.add_argument("--choose-street", action="store_true")
    parser.add_argument("--choose-house", action="store_true")
    parser.add_argument("--phone")
    parser.add_argument("--capture-submit", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=20_000)
    args = parser.parse_args()
    if args.house and not args.street:
        parser.error("--house requires --street")
    if args.choose_street and not args.street:
        parser.error("--choose-street requires --street")
    if args.house and not args.choose_street:
        parser.error("--house requires --choose-street")
    if args.choose_house and not args.house:
        parser.error("--choose-house requires --house")
    if args.capture_submit and not args.phone:
        parser.error("--capture-submit requires --phone")

    writes = []
    address_probe = None
    phone_probe = None
    executable = os.getenv("BUSINESS_CHROMIUM_EXECUTABLE")
    launch = {"executable_path": executable} if executable else {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**launch)
        context = browser.new_context(service_workers="block")

        def guard(route):
            request = route.request
            if request.method in READ_ONLY_METHODS:
                route.continue_()
            else:
                writes.append({"method": request.method, "url": clean_url(request.url), "payload": payload_summary(request)})
                route.abort("blockedbyclient")

        context.route("**/*", guard)
        page = context.new_page()
        try:
            response = page.goto(args.url, wait_until="domcontentloaded", timeout=args.timeout_ms)
            page.wait_for_timeout(750)
            control, control_selector = first_visible(page, ["select[name='Place']"])
            form = control.locator("xpath=ancestor::form[1]")
            before = control.input_value()
            control.select_option(value="Для бизнеса")
            after = control.input_value()

            trigger, trigger_selector = first_visible(form, [
                ".autocomplete-city-change.button-select-city",
                ".checkaddress_address_button_change_city",
            ])
            trigger.click(timeout=args.timeout_ms)
            search, search_selector = first_visible(page, ["#popup-select-city #city-input", "#city-input"])
            search.fill("Самара")
            choice, choice_selector = first_visible(page, [
                "#popup-select-city a.region_item.region_link[id='36401']",
                "a.region_item.region_link[id='36401']",
                "a[id='36401']",
            ])
            choice.click(timeout=args.timeout_ms)
            page.wait_for_timeout(750)

            address = None
            if args.street:
                street = form.locator(".checkaddress_address_street")
                house = form.locator(".checkaddress_address_house")
                address_probe = {
                    "street_count": street.count(),
                    "street_visible": street.is_visible() if street.count() else False,
                    "street_editable": street.is_editable() if street.count() else False,
                    "house_count": house.count(),
                    "popup_visible": page.locator("#popup-select-city").is_visible()
                    if page.locator("#popup-select-city").count() else False,
                }
                if not address_probe["street_editable"]:
                    raise RuntimeError(f"Street field is not editable after region selection: {address_probe}")
                street.fill(args.street, timeout=10_000)
                page.wait_for_timeout(1_000)
                suggestions = page.evaluate(
                    """needle => [...document.querySelectorAll('body *')]
                      .filter(el => !el.children.length && (el.textContent || '').toLowerCase().includes(needle.toLowerCase()))
                      .filter(el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length))
                      .slice(0, 20)
                      .map(el => ({text:(el.textContent || '').trim().slice(0, 160), class_name:el.className || null}))""",
                    args.street,
                )
                street_selection = None
                if args.choose_street:
                    street.press("ArrowDown")
                    street.press("Enter")
                    page.wait_for_timeout(750)
                    street_selection = {
                        "street_value": street.input_value(),
                        "house_editable": house.is_editable(),
                        "hidden_fields": form.locator(
                            "input[name='CityName'], input[name='City'], input[name='Info'], input[name='IStreet'], input[name='IHouse'], input[name='IDistrict']"
                        ).evaluate_all("els => els.map(el => ({name:el.name, value:el.value}))"),
                    }
                house_suggestions = None
                house_selection = None
                if args.house:
                    house.fill(args.house, timeout=10_000)
                    page.wait_for_timeout(1_000)
                    house_suggestions = page.evaluate(
                        """needle => [...document.querySelectorAll('body *')]
                          .filter(el => !el.children.length && (el.textContent || '').toLowerCase().includes(needle.toLowerCase()))
                          .filter(el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length))
                          .slice(0, 20)
                          .map(el => ({text:(el.textContent || '').trim().slice(0, 160), class_name:el.className || null}))""",
                        args.house,
                    )
                    if args.choose_house:
                        house.press("ArrowDown")
                        house.press("Enter")
                        page.wait_for_timeout(750)
                        house_selection = {
                            "house_value": house.input_value(),
                            "hidden_fields": form.locator(
                                "input[name='CityName'], input[name='City'], input[name='Info'], input[name='IStreet'], input[name='IHouse'], input[name='IDistrict']"
                            ).evaluate_all("els => els.map(el => ({name:el.name, value:el.value}))"),
                        }
                address = {
                    "street_value": street.input_value(),
                    "house_value": house.input_value() if args.house else None,
                    "suggestions_after_street": suggestions,
                    "street_selection": street_selection,
                    "suggestions_after_house": house_suggestions,
                    "house_selection": house_selection,
                    "hidden_fields": form.locator(
                        "input[name='CityName'], input[name='City'], input[name='Info'], input[name='IStreet'], input[name='IHouse'], input[name='IDistrict']"
                    ).evaluate_all("els => els.map(el => ({name:el.name, value:el.value}))"),
                }

            submit_capture = None
            if args.capture_submit:
                phone = form.locator(".checkaddress_address_phone")
                phone_probe = {
                    "count": phone.count(),
                    "visible": phone.is_visible() if phone.count() else False,
                    "editable": phone.is_editable() if phone.count() else False,
                }
                if not phone_probe["editable"]:
                    raise RuntimeError(f"Phone field is not editable: {phone_probe}")
                phone.click()
                phone.press_sequentially(args.phone, delay=25)
                page.wait_for_timeout(500)
                form.locator(".checkaddress_address_button_send").click(timeout=args.timeout_ms)
                page.wait_for_timeout(1_000)
                submit_capture = [
                    write for write in writes
                    if {"CityName", "City", "Place"}.issubset(set(write["payload"]["field_names"]))
                ]

            indicators = form.locator("#autocomplete_city_name, .autocomplete-city-name")
            result = {
                "mode": "read_only_business_option_state",
                "safety": (
                    "The submit click was intercepted before any POST left the browser; only field names and selected Samara/business values were recorded."
                    if args.capture_submit else (
                        "Address fields were typed and only explicitly requested autocomplete choices were selected; submit was not clicked and all non-GET/HEAD/OPTIONS requests were aborted."
                        if args.street else "No address fields were filled and submit was not clicked; all non-GET/HEAD/OPTIONS requests were aborted."
                    )
                ),
                "case_id": args.case_id,
                "http_status": response.status if response else None,
                "initial_url": clean_url(args.url),
                "final_url": clean_url(page.url),
                "control": {"selector": control_selector, "before": before, "after": after},
                "form": {
                    "class": form.get_attribute("class"),
                    "unit_tag": form.locator("input[name='_wpcf7_unit_tag']").first.get_attribute("value")
                    if form.locator("input[name='_wpcf7_unit_tag']").count() else None,
                    "fields": form.locator("input, select, textarea").evaluate_all(
                        "els => els.filter(el => el.type !== 'hidden').map(el => ({tag:el.tagName.toLowerCase(), name:el.name || null, type:el.type || null, class_name:el.className || null}))"
                    ),
                    "submit_controls": form.locator("button, input[type='submit']").evaluate_all(
                        "els => els.map(el => ({tag:el.tagName.toLowerCase(), type:el.type || null, class_name:el.className || null, text:(el.textContent || el.value || '').trim()}))"
                    ),
                },
                "region": {
                    "trigger": trigger_selector,
                    "search": search_selector,
                    "choice": choice_selector,
                    "choice_href": choice.get_attribute("href"),
                    "indicators": indicators.evaluate_all(
                        "els => els.map(el => ({text:(el.textContent || '').trim(), ui_id:el.dataset.item || null}))"
                    ),
                    "hidden_city_fields": form.locator("input[name='CityName'], input[name='City'], input[name='Info']").evaluate_all(
                        "els => els.map(el => ({name:el.name, value:el.value}))"
                    ),
                },
                "address": address,
                "submit_capture": submit_capture,
                "blocked_write_count": len(writes),
                "submit_clicked": bool(args.capture_submit),
            }
        except (Error, RuntimeError) as exc:
            result = {
                "mode": "read_only_business_option_state",
                "case_id": args.case_id,
                "error": f"{type(exc).__name__}: {str(exc).splitlines()[0]}",
                "final_url": clean_url(page.url),
                "address_probe": address_probe,
                "phone_probe": phone_probe,
                "blocked_write_count": len(writes),
                "blocked_writes": writes,
                "submit_clicked": False,
            }
        finally:
            context.close()
            browser.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"case_id": args.case_id, "output": str(args.output), "error": result.get("error")}, ensure_ascii=False))
    return 0 if not result.get("error") else 1


if __name__ == "__main__":
    raise SystemExit(main())
