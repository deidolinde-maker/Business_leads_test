from playwright.sync_api import expect

from business.errors import ConfigurationError


def set_business(form, case, deadline, exercise_variants: bool = False):
    control = case["form"].get("business_control")
    if not control:
        return
    kind = control["kind"]
    target = form.locator(control["selector"])
    expect(target).to_have_count(1, timeout=deadline.ms())

    if kind == "auto":
        tag = (target.evaluate("el => el.tagName.toLowerCase()") or "").lower()
        if tag == "select":
            kind = "select"
        elif tag == "input" and (target.get_attribute("type") or "").lower() in {"radio", "checkbox"}:
            kind = (target.get_attribute("type") or "radio").lower()
        elif target.locator("xpath=ancestor-or-self::button").count() > 0:
            kind = "button"
        elif target.get_attribute("class") and "custom-select-trigger" in target.get_attribute("class"):
            kind = "custom_select"
        else:
            raise ConfigurationError("auto business control type could not be detected")

    def select(locator, wanted, click_selector=None):
        if click_selector:
            if locator.is_checked() != wanted:
                form.locator(click_selector).click(timeout=deadline.ms())
        else:
            locator.set_checked(wanted, timeout=deadline.ms())
        expect(locator).to_be_checked(checked=wanted, timeout=deadline.ms())

    if kind == "checkbox":
        values = (False, True, False, True) if exercise_variants else (True,)
        for wanted in values:
            select(target, wanted, control.get("click_selector"))
    elif kind == "radio":
        if not control.get("alternative"):
            raise ConfigurationError("radio alternative must be verified")
        alternative = form.locator(control["alternative"])
        values = (False, True, False, True) if exercise_variants else (True,)
        for business in values:
            select(target if business else alternative, True,
                   control.get("click_selector" if business else "alternative_click_selector"))
            expect(target if not business else alternative).to_be_checked(checked=False, timeout=deadline.ms())
    elif kind == "select":
        for key in ("business_value", "alternative_value"):
            if not control.get(key):
                raise ConfigurationError(f"select {key} must be verified")
        values = ((control["alternative_value"], control["business_value"],
                   control["alternative_value"], control["business_value"])
                  if exercise_variants else (control["business_value"],))
        for value in values:
            target.select_option(value=value, timeout=deadline.ms())
            expect(target).to_have_value(value, timeout=deadline.ms())
    elif kind == "button":
        target.click(timeout=deadline.ms())
        if control.get("selected_attribute") and control.get("selected_value"):
            expect(target).to_have_attribute(
                control["selected_attribute"], control["selected_value"], timeout=deadline.ms()
            )
    elif kind == "custom_select":
        trigger = form.locator(control["trigger"])
        option = form.locator(control["business_option"])
        expect(trigger).to_have_count(1, timeout=deadline.ms())
        trigger.click(timeout=deadline.ms())
        expect(option).to_have_count(1, timeout=deadline.ms())
        option.click(timeout=deadline.ms())
        if control.get("selected_text"):
            expect(trigger).to_contain_text(control["selected_text"], timeout=deadline.ms())
    else:
        raise ConfigurationError("unsupported business control")
    assert_business(form, case, deadline)


def assert_business(form, case, deadline):
    control = case["form"].get("business_control")
    if control:
        target = form.locator(control["selector"])
        if control["kind"] == "select":
            expect(target).to_have_value(control["business_value"], timeout=deadline.ms())
        elif control["kind"] in {"checkbox", "radio"}:
            expect(target).to_be_checked(timeout=deadline.ms())
        elif control["kind"] == "button" and control.get("selected_attribute") and control.get("selected_value"):
            expect(target).to_have_attribute(control["selected_attribute"], control["selected_value"], timeout=deadline.ms())
        elif control["kind"] == "custom_select" and control.get("selected_text"):
            expect(form.locator(control["trigger"])).to_contain_text(control["selected_text"], timeout=deadline.ms())
