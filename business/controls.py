from playwright.sync_api import expect

from business.region import assert_samara
from business.errors import ConfigurationError


def set_business(form, case, deadline):
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
        assert_samara(form, case["region"], deadline)

    if kind == "checkbox":
        for wanted in (False, True, False, True):
            select(target, wanted, control.get("click_selector"))
    elif kind == "radio":
        if not control.get("alternative"):
            raise ConfigurationError("radio alternative must be verified")
        alternative = form.locator(control["alternative"])
        for business in (False, True, False, True):
            select(target if business else alternative, True,
                   control.get("click_selector" if business else "alternative_click_selector"))
            expect(target if not business else alternative).to_be_checked(checked=False, timeout=deadline.ms())
    else:
        raise ConfigurationError("unsupported business control")
    assert_business(form, case, deadline)


def assert_business(form, case, deadline):
    control = case["form"].get("business_control")
    if control:
        expect(form.locator(control["selector"])).to_be_checked(timeout=deadline.ms())
