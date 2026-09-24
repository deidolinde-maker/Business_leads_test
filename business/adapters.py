import re
import time

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, expect

from business.errors import BusinessCheckError, ConfigurationError
from business.controls import assert_business


# The variants runner in Everyday_test deliberately resolves a form by the
# controls it contains, rather than relying on a provider-specific form id.
# Keep the same fallback profile here; the business-page navigation remains in
# runner.py and is not affected by these selectors.
FORM_FIELD_FALLBACKS = {
    "street": (
        ".connection_address_street, .checkaddress_address_street, "
        ".profit_address_street, .express-connection_address_street, "
        "input[name='AddresStreet'], input[name='Street'], "
        "#city[placeholder='Адрес'], #city"
    ),
    "house": (
        ".connection_address_house, .checkaddress_address_house, "
        ".profit_address_house, .express-connection_address_house, "
        "input[name='AddresHouse'], input[name='House']"
    ),
    "phone": (
        ".connection_address_phone, .checkaddress_address_phone, "
        ".profit_address_phone, .express-connection_address_phone, "
        "input[name='Phone'], input[type='tel']"
    ),
    "submit": (
        ".connection_address_button_send, .checkaddress_address_button_send, "
        ".profit_address_button_send, .express-connection_address_button_send, "
        "input[type='submit'], button[type='submit'], #submit"
    ),
}
SUGGESTION_FALLBACKS = (
    "[role='option']:visible",
    "[role='listbox'] li:visible",
    ".suggestions__item:visible",
    ".suggestion-item:visible",
    ".autocomplete__item:visible",
    ".autocomplete-item:visible",
    ".ui-menu-item:visible",
    "[class*='suggest'] li:visible",
    "[class*='autocomplete'] li:visible",
    "#street-list [data-value]:visible",
    "#street-list > li:visible",
    "#street-list > div.autocomplete-item:visible",
    "#house-list [data-value]:visible",
    "#house-list > li:visible",
    "#house-list > div.autocomplete-item:visible",
    "#street-list div:visible",
    "#street-list li:visible",
    "#house-list div:visible",
    "#house-list li:visible",
)


def subscriber_digits(displayed_value: str) -> str:
    digits = re.sub(r"\D", "", displayed_value)
    if len(digits) == 11 and digits.startswith(("7", "8")):
        return digits[1:]
    return digits


class FormAdapter:
    @staticmethod
    def _dismiss_profit_popup(page):
        """Close the auto-offer popup before it can cover the target form."""
        try:
            offer = page.locator(
                "#popup-lead-catcher:visible, .popup-lead-catcher:visible"
            ).first
            if offer.count() == 0 or not offer.is_visible():
                return
            for close_selector in (
                ".popup__close", ".fancybox-close-small", ".modal__close",
                "[aria-label*='close']", "[aria-label*='закры']",
            ):
                close = offer.locator(close_selector).first
                if close.count() > 0 and close.is_visible():
                    close.click(force=True)
                    page.wait_for_timeout(300)
                    return
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
        except Exception:
            pass

    @staticmethod
    def _visible_locator(root, selector):
        """Return the first visible locator, matching Everyday variants."""
        candidates = root.locator(selector)
        for index in range(candidates.count()):
            candidate = candidates.nth(index)
            try:
                if candidate.is_visible():
                    return candidate
            except Exception:
                continue
        return None

    @classmethod
    def _field_locator(cls, form, field):
        locator = cls._visible_locator(form, field.get("selector", ""))
        if locator is not None:
            return locator
        fallback = FORM_FIELD_FALLBACKS.get(field.get("data_key"))
        return cls._visible_locator(form, fallback) if fallback else None

    @classmethod
    def submit_locator(cls, form, case):
        configured = case["form"].get("submit", "")
        return cls._visible_locator(form, configured) or cls._visible_locator(
            form, FORM_FIELD_FALLBACKS["submit"]
        )

    @classmethod
    def _discover_form(cls, page, case):
        cfg = case["form"]
        selectors = [cfg.get("selector", "")]
        # Business-page forms live in a delayed popup. Do not accidentally
        # select an unrelated visible page form before the configured trigger
        # has opened #popup-business.
        popup_form = "#popup-business" in cfg.get("selector", "")
        if popup_form and not cls._visible_locator(page, cfg.get("selector", "")):
            return None
        # The variants suite accepts any visible form/container that owns the
        # address and phone controls. This also covers delayed TTK connection
        # containers and mobile/desktop duplicate form markup.
        selectors.extend([
            "form:visible",
            ".autocomplete-address:visible",
            ".connection_address_popup:visible",
            "[class*='connection']:visible",
        ])
        for selector in selectors:
            if not selector:
                continue
            candidates = page.locator(selector)
            for index in range(candidates.count()):
                candidate = candidates.nth(index)
                try:
                    if not candidate.is_visible():
                        continue
                    # A candidate must own at least a phone and an address
                    # control; this prevents selecting a navigation wrapper.
                    if cls._visible_locator(candidate, FORM_FIELD_FALLBACKS["phone"]) is None:
                        continue
                    if cls._visible_locator(candidate, FORM_FIELD_FALLBACKS["street"]) is None:
                        continue
                    return candidate
                except Exception:
                    continue
        return None

    @classmethod
    def _choose_suggestion(cls, page, preferred, field=None, timeout_ms=1500):
        """Copy Everyday's poll-and-click plus ArrowDown/Enter fallback."""
        preferred_parts = [part.strip() for part in (preferred or "").split(",") if part.strip()]
        # Prefer actual suggestion items over a generic list wrapper. Some
        # RTK templates expose both through the same #house-list container.
        preferred_parts.sort(key=lambda part: 0 if any(token in part for token in (
            "[data-value]", ".autocomplete-item", "> li", "[role=", "[role='"
        )) else 1)
        selectors = preferred_parts + list(SUGGESTION_FALLBACKS)
        end = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < end:
            for selector in selectors:
                if not selector:
                    continue
                locator = page.locator(selector)
                for index in range(locator.count()):
                    item = locator.nth(index)
                    try:
                        if not item.is_visible() or not (item.inner_text() or "").strip():
                            continue
                        # RTK renders the list container as a visible div around
                        # the actual autocomplete item; never click that wrapper.
                        item_id = item.get_attribute("id") or ""
                        item_class = item.get_attribute("class") or ""
                        if item_id in {"street-list", "house-list"} or "autocomplete-list" in item_class:
                            continue
                        item.click(timeout=3000, force=True)
                        page.wait_for_timeout(300)
                        return True
                    except Exception:
                        continue
            page.wait_for_timeout(150)
        try:
            if field is not None:
                field.scroll_into_view_if_needed()
                field.click(force=True)
            page.keyboard.press("ArrowDown")
            page.wait_for_timeout(200)
            page.keyboard.press("Enter")
            page.wait_for_timeout(300)
            return True
        except Exception:
            return False

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
        # Everyday variants close the automatic profit catcher before locating
        # any other form. It must happen before field discovery, otherwise the
        # popup can intercept clicks and make the phone appear unfilled.
        self._dismiss_profit_popup(page)
        form = self._discover_form(page, case)
        if form is None:
            if not cfg.get("trigger"):
                raise BusinessCheckError("target_form_not_visible_and_no_trigger")
            trigger = page.locator(cfg["trigger"])
            expect(trigger).to_have_count(1, timeout=deadline.ms())
            trigger.click(timeout=deadline.ms())
            self._dismiss_profit_popup(page)
            form = self._discover_form(page, case)
        if form is None:
            raise BusinessCheckError("target_form_not_visible")
        expect(form).to_be_visible(timeout=deadline.ms())
        return form

    def fill(self, form, case, data, deadline):
        for field in case["form"]["fields"]:
            key = field["data_key"]
            if key not in data or data[key] is None:
                raise ConfigurationError(f"missing data key: {key}")
            value = str(data[key])
            locator = self._field_locator(form, field)
            deadline.mark(f"fill.{key}.present")
            if locator is None:
                raise BusinessCheckError(f"fill.{key}.not_found")
            deadline.mark(f"fill.{key}.enabled")
            expect(locator).to_be_enabled(timeout=deadline.ms())
            deadline.mark(f"fill.{key}.value")
            if key == "phone":
                if not re.fullmatch(r"\d{10}", value):
                    raise ConfigurationError("phone must contain exactly 10 digits outside the mask")
                # This mask ignores atomic fill() and can also lose the first key if
                # typing starts while focus initialization is still in progress.
                # Focus it first, let the mask initialize, then type all ten digits.
                locator.click(force=True, timeout=deadline.ms())
                form.page.wait_for_timeout(250)
                try:
                    locator.press_sequentially(value, delay=50, timeout=min(8_000, deadline.ms()))
                except PlaywrightTimeoutError:
                    # Masked inputs can be replaced after focus. Re-resolve and
                    # retry once with the same real-key path used by Everyday_test.
                    locator = self._field_locator(form, field)
                    if locator is None:
                        raise BusinessCheckError(f"fill.{key}.not_found")
                    locator.click(force=True, timeout=deadline.ms())
                    try:
                        locator.press("Control+A", timeout=min(2_000, deadline.ms()))
                        locator.fill("", timeout=min(2_000, deadline.ms()))
                    except PlaywrightTimeoutError:
                        pass
                    locator.press_sequentially(value, delay=80, timeout=min(8_000, deadline.ms()))
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
                form.page.wait_for_timeout(int(field.get("suggestion_delay_ms", 300)))
                if not self._choose_suggestion(
                    form.page, field.get("suggestion"), locator,
                    timeout_ms=min(3_000, deadline.ms())
                ):
                    raise BusinessCheckError(f"fill.{key}.suggestion_not_selected")
                # Address widgets update hidden IDs and unlock the house input
                # asynchronously after the visible suggestion click.  Do not
                # continue to phone/submit while that update is still pending.
                if key in {"street", "house"}:
                    form.page.wait_for_timeout(800)
                    refreshed = self._field_locator(form, field)
                    if key == "house":
                        if refreshed is None:
                            raise BusinessCheckError("fill.house.not_found_after_suggestion")
                        try:
                            expect(refreshed).to_be_enabled(timeout=min(5_000, deadline.ms()))
                        except PlaywrightTimeoutError:
                            # A delayed list can rerender the item after the
                            # first click; select the current visible item once more.
                            self._choose_suggestion(form.page, field.get("suggestion"), refreshed,
                                                    timeout_ms=min(3_000, deadline.ms()))
                            expect(refreshed).to_be_enabled(timeout=deadline.ms())
                    if refreshed is not None:
                        expect(refreshed).not_to_have_value("", timeout=deadline.ms())
                        # RTK commits a selected address through hidden IStreet/
                        # IHouse controls. Retry the first suggestion once if the
                        # visible text changed but the hidden id is still empty.
                        hidden_name = "IStreet" if key == "street" else "IHouse"
                        hidden = form.locator(
                            f"input[name='{hidden_name}']:visible, input[name='{hidden_name}']"
                        ).first
                        if hidden.count() > 0 and not (hidden.input_value() or "").strip():
                            refreshed.click(force=True)
                            form.page.keyboard.press("ArrowDown")
                            form.page.keyboard.press("Enter")
                            form.page.wait_for_timeout(500)
                            self._choose_suggestion(
                                form.page, field.get("suggestion"), refreshed,
                                timeout_ms=min(2_000, deadline.ms())
                            )
                            form.page.wait_for_timeout(500)
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
