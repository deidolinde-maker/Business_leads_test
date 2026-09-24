"""Synthetic contracts for local fixtures only, never production business rules."""


def make_case(base="http://127.0.0.1:8099", mode="direct_city_subdomain", fault=""):
    entry = base + ("/plain/business" if mode == "popup_selection" else "/direct/business")
    if fault:
        entry += "?fault=" + fault
    business_url = base + "/samara/business" if mode == "popup_selection" else entry
    return {
        "case_id": "synthetic-business", "provider": "fixture", "environment": "stage",
        "target_city": "Самара", "target_city_ui_id": "36401", "flow_kind": "business_option",
        "entry_url": entry, "status": "active", "source_refs": ["local synthetic fixture"],
        "verification": "local fixture contract, not live",
        "region": {"mode": mode, "business_url": business_url,
                   "indicator": "#autocomplete_city_name", "trigger": "#choose-region",
                   "popup": "#region-dialog", "search": "#city-input", "choice": "a[id='36401']",
                   "choice_url": base + "/samara", "after_choice_url": base + "/samara"},
        "form": {"selector": "form#lead", "submit": "#submit",
                 "fields": [{"selector": "#address", "data_key": "full_address"},
                            {"selector": "#phone", "data_key": "phone"}],
                 "business_control": {"kind": "checkbox", "selector": "#office", "click_selector": "label[for=office]"},
                 "consents": [{"selector": "#consent"}]},
        "confirmation": {"kind": "locator", "value": "#thanks:visible"},
    }


DATA = {"city": "Самара", "environment": "stage", "street": "synthetic street", "house": "1",
        "full_address": "synthetic Samara address", "phone": "9999999999"}
