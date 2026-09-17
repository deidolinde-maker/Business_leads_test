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

The requested house `1` did not become the selected autocomplete result; the first offered choice was `21`. The user clarified that any address selected inside the ordinary popup is acceptable, so `Ленинградская ул, 21` was used only for the safe contract capture.

## Blocked-submit contract

The form was completed with the selected Samara address and the provided test phone, then submit was clicked while every POST was aborted before leaving the browser. One candidate request was captured:

- endpoint: `POST https://mts-home.online/wp-admin/admin-ajax.php`;
- region: `CityName=Самара`, `City=36401`, `IStreet=313620`, `IHouse=293579`;
- business selection: `Place=Для бизнеса`;
- form identity: `FormName=Проверьте подключение`, `lead_form_type=forma_proverit'_adress`, `service_id=2`.

No phone value or raw request body was saved. This proves the selected business and Samara request contract, but not the positive response or CRM delivery. The candidate remains `blocked` until one explicitly approved production pilot verifies those two outcomes.

## Production pilot

One explicitly approved production submission was sent on 16.09.2026 using the selected Samara popup address and the provided test phone. The browser reached `https://mts-home.online/tilda/form1/submitted`; no repeat was sent. A stale locator after that navigation prevented saving the response body. The user subsequently confirmed that this exact pilot arrived correctly in CRM.

The legacy suites define `/tilda/form1/submitted` as the positive «Спасибо» page for this form family. Together with the observed HTTP 200, the exact Samara/business POST contract and user-confirmed CRM delivery, it is now an `active` representative for live automation.

## Transport update — 17.09.2026

The deployed public HTML was read without opening or filling the form. Its inline Contact Form 7 transport maps feedback for form `1645` to this exact URL:

`POST https://mts-home.online/wp-admin/admin-ajax.php?action=cf7_proxy_submit_transport&cf7_form_id=1645&cf7_operation=feedback`

This replaces the former query-free `admin-ajax.php` contract. No personal data was entered and no request was sent during this verification.

## Sources

- User rule for in-place Samara selection in `checkbox`/`select Place` flows, 16.09.2026.
- Local ignored artifact `artifacts/onboarding/mts-home-online-state.json`; no production lead was sent.
- [QA analysis workflow](../references/qa/analyze-task.md).
- [Functional specification](../specs/01-business-test-spec.md).
