import pytest

from business.runner import _success_url_matches


@pytest.mark.parametrize(
    "url",
    [
        "https://rtk-ru.online/tilda/form1/submitted",
        "https://rtk-home.ru/tilda/form1/submitted",
        "https://beeline-internet.online/thanks",
    ],
)
def test_generic_success_page_is_accepted_for_url_contains_confirmation(url):
    assert _success_url_matches(url, {"kind": "url_contains", "value": "/thanks"})


def test_non_success_url_is_not_accepted():
    assert not _success_url_matches(
        "https://beeline-internet.online/",
        {"kind": "url_contains", "value": "/thanks"},
    )
