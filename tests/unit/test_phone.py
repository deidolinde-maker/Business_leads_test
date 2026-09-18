import pytest

from business.adapters import subscriber_digits


@pytest.mark.parametrize("displayed", ["9999999999", "+7 (999) 999-99-99", "8 (999) 999-99-99"])
def test_complete_mask_contains_all_ten_subscriber_digits(displayed):
    assert subscriber_digits(displayed) == "9999999999"


def test_incomplete_mask_is_detected():
    assert subscriber_digits("+7 (999) 999-99-9") != "9999999999"
