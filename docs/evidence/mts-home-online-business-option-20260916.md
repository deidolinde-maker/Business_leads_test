# MTS Home Online business-option — 16.09.2026

## Scope

This evidence covers canonical source candidate `mts-business_option-5d75c21b6980` at `https://mts-home.online/`. The no-trailing-slash inventory record is an exact normalized duplicate and is retained as excluded provenance.

## Read-only production observation

Chromium opened the root URL with HTTP 200. No address was entered, submit was not clicked and all non-GET/HEAD/OPTIONS requests were aborted.

- visible form unit tag: `wpcf7-f1645-o1`;
- `select[name='Place']` changed from `В квартиру` to `Для бизнеса`;
- form fields: `AddresStreet`, `AddresHouse`, `Phone`;
- submit locator: `.checkaddress_address_button_send`;
- region trigger: `.autocomplete-city-change.button-select-city`;
- popup input: `#popup-select-city #city-input`;
- exact selected choice: `#popup-select-city a.region_item.region_link[id='36401']`, href `https://samara.mts-home.online/`;
- after selection the form indicator was `Самара`, UI ID `36401`, while the browser stayed on `https://mts-home.online/`.

The user-defined rule permits the unchanged base URL for `Place` flows. It is not a failure by itself. After the native street suggestion `Ленинградская ул` was selected, the form populated hidden `CityName=Самара`, `City=36401`, district and street fields. The descriptive `Info` field still contained Moscow; per the user clarification, that stale display text is not a region failure when the popup and selected address establish Samara.

## Blocking facts

The inspection did not send a request, so it does not prove the business/region payload or positive response. The requested house `1` did not become the selected autocomplete result in the read-only flow; the first offered choice was `21` and was not accepted as a substitute. This candidate remains `blocked` until the exact address is selected and a blocked request capture establishes the business and Samara payload contract.

## Sources

- User rule for in-place Samara selection in `checkbox`/`select Place` flows, 16.09.2026.
- Local ignored artifact `artifacts/onboarding/mts-home-online-state.json`; no production lead was sent.
- [QA analysis workflow](../references/qa/analyze-task.md).
- [Functional specification](../specs/01-business-test-spec.md).
