import re

from playwright.sync_api import expect

from business.errors import BusinessCheckError, ConfigurationError
from business.controls import assert_business
from business.cases import CITY_NAME


def subscriber_digits(displayed_value: str) -> str:
    digits = re.sub(r"\D", "", displayed_value)
    if len(digits) == 11 and digits.startswith(("7", "8")):
        return digits[1:]
    return digits


class FormAdapter:
    def open_form(self, page, case, deadline):
        cfg = case["form"]
        # Legacy suites wait for delayed region/cookie overlays before opening
        # checkaddress.  Reuse the same selectors so the form is not covered.
        page.wait_for_timeout(600)
        overlay_selectors = [
            "#noButton", "#yesButton",
            ".popup-select-region__button.city",
            ".popup-select-region__content-wrapper .popup__close",
            ".Backdrop[data-modal='city'] button.city",
            "#cookieButton", "#cookieAccept", ".cookie-btn", "#cookie-accept",
            ".cookie-accept", ".t886__btn",
        ]
        for selector in overlay_selectors:
            overlay = page.locator(selector).first
            if overlay.count() == 1 and overlay.is_visible():
                overlay.click(force=True, timeout=deadline.ms())
                page.wait_for_timeout(300)
        for selector in cfg.get("dismiss", []):
            overlay_close = page.locator(selector)
            if overlay_close.count() == 1 and overlay_close.is_visible():
                overlay_close.click(timeout=deadline.ms())
        form = page.locator(cfg["selector"])
        if not (form.count() == 1 and form.is_visible()):
            if not cfg.get("trigger"):
                raise BusinessCheckError("target_form_not_visible_and_no_trigger")
            trigger = page.locator(cfg["trigger"])
            expect(trigger).to_have_count(1, timeout=deadline.ms())
            trigger.click(timeout=deadline.ms())
        expect(form).to_have_count(1, timeout=deadline.ms())
        expect(form).to_be_visible(timeout=deadline.ms())
        return form

    def fill(self, form, case, data, deadline):
        for field in case["form"]["fields"]:
            key = field["data_key"]
            if key not in data or data[key] is None:
                raise ConfigurationError(f"missing data key: {key}")
            value = str(data[key])
            locator = form.locator(field["selector"])
            deadline.mark(f"fill.{key}.present")
            expect(locator).to_have_count(1, timeout=deadline.ms())
            deadline.mark(f"fill.{key}.enabled")
            expect(locator).to_be_enabled(timeout=deadline.ms())
            deadline.mark(f"fill.{key}.value")
            if key == "phone":
                if not re.fullmatch(r"\d{10}", value):
                    raise ConfigurationError("phone must contain exactly 10 digits outside the mask")
                # This mask ignores atomic fill() and can also lose the first key if
                # typing starts while focus initialization is still in progress.
                # Focus it first, let the mask initialize, then type all ten digits.
                locator.click(timeout=deadline.ms())
                form.page.wait_for_timeout(250)
                locator.press_sequentially(value, delay=50, timeout=deadline.ms())
                form.page.wait_for_timeout(200)
                locator.blur(timeout=deadline.ms())
                deadline.mark("fill.phone.complete")
                if subscriber_digits(locator.input_value(timeout=deadline.ms())) != value:
                    raise BusinessCheckError("phone_not_fully_entered")
            else:
                # Address autocomplete widgets need real keystrokes to load
                # street/house suggestions; atomic fill() can outrun them.
                if key in {"street", "house"}:
                    locator.click(timeout=deadline.ms())
                    locator.press_sequentially(value, delay=80, timeout=deadline.ms())
                    form.page.wait_for_timeout(500)
                else:
                    locator.fill(value, timeout=deadline.ms())
            # A real, exact Samara address suggestion must come from the case/data contract.
            if field.get("suggestion"):
                deadline.mark(f"fill.{key}.suggestion")
                candidates = form.page.locator(field["suggestion"])
                # Address APIs return several cities for the same street name.
                # Select the Samara item itself instead of the first result
                # (which is often the same street in another locality).
                if key == "street":
                    city_items = form.page.locator("div.autocomplete-item:visible").filter(
                        has_text=re.compile(rf"\b{re.escape(CITY_NAME)}\b")
                    )
                    if city_items.count():
                        candidates = city_items
                # House suggestions can contain 21/100 before the exact house
                # 1. Match the complete displayed value, not a substring.
                if key == "house":
                    exact = candidates.filter(has_text=re.compile(rf"^\s*{re.escape(value)}\s*$"))
                    if exact.count():
                        candidates = exact
                suggestion = candidates.first
                form.page.wait_for_timeout(300)
                expect(suggestion).to_be_visible(timeout=deadline.ms())
                if field.get("suggestion_text_key"):
                    expected_text = str(data[field["suggestion_text_key"]])
                    expect(suggestion).to_contain_text(expected_text, timeout=deadline.ms())
                suggestion.click(timeout=deadline.ms())
        for consent in case["form"].get("consents", []):
            box = form.locator(consent["selector"])
            if consent.get("click_selector"):
                if not box.is_checked():
                    form.locator(consent["click_selector"]).click(timeout=deadline.ms())
            else:
                box.check(timeout=deadline.ms())
            expect(box).to_be_checked(timeout=deadline.ms())
        assert_business(form, case, deadline)
        # Do not gate provider forms with form.checkValidity(): unrelated hidden
        # controls can be invalid even though the site's own submit handler accepts
        # this form. The browser performs its normal validation on click, while the
        # submission guard validates the exact outgoing business/Samara payload.
