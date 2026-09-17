from playwright.sync_api import expect

from business.errors import BusinessCheckError, ConfigurationError
from business.controls import assert_business


class FormAdapter:
    def open_form(self, page, case, deadline):
        cfg = case["form"]
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
            expect(locator).to_have_count(1, timeout=deadline.ms())
            expect(locator).to_be_enabled(timeout=deadline.ms())
            locator.fill(value, timeout=deadline.ms())
            # A real, exact Samara address suggestion must come from the case/data contract.
            if field.get("suggestion"):
                suggestion = form.page.locator(field["suggestion"])
                expected_text = str(data[field["suggestion_text_key"]])
                expect(suggestion).to_have_count(1, timeout=deadline.ms())
                expect(suggestion).to_have_text(expected_text, timeout=deadline.ms())
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
        # Local validation, no synthetic submit or direct DOM state mutation.
        if not form.evaluate("el => typeof el.checkValidity !== 'function' || el.checkValidity()"):
            raise BusinessCheckError("form_validation_failed")
