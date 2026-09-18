from playwright.sync_api import expect

from business.errors import ConfigurationError


def set_business(form, case, deadline, exercise_variants: bool = False):
    control = case["form"].get("business_control")
    if not control:
        return
    kind = control["kind"]
    target = form.locator(control["selector"])
    expect(target).to_have_count(1, timeout=deadline.ms())

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
    else:
        raise ConfigurationError("unsupported business control")
    assert_business(form, case, deadline)


def assert_business(form, case, deadline):
    control = case["form"].get("business_control")
    if control:
        target = form.locator(control["selector"])
        if control["kind"] == "select":
            expect(target).to_have_value(control["business_value"], timeout=deadline.ms())
        else:
            expect(target).to_be_checked(timeout=deadline.ms())
