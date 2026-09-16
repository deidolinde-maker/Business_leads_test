# MTS business-page scope — 16.09.2026

## Business requirement

The user clarified that dedicated MTS business-page forms work only on `https://mts-home-online.ru/`. This rule concerns business pages and must not be applied to the separate checkbox / `Place=Для бизнеса` scope.

The executable MTS business-page target is therefore `https://mts-home-online.ru/business`. The other five imported MTS `business_page` records are `excluded` with this user decision as evidence. MTS `business_option` candidates remain unchanged and require separate review.

## Production UI observation

Read-only Chromium inspection opened `https://mts-home-online.ru/business` with HTTP 200. All POST requests were blocked; no form data was entered and no lead was submitted.

The page contains eight service cards:

1. Корпоративные тарифы
2. Интернет в офис
3. CloudMTS
4. Многоканальный номер 8-800
5. Объектное хранилище
6. Облачное Видеонаблюдение
7. МТС Линк
8. LocationPro

Each card opens the same dedicated business form: CF7 ID `837`, unit tag `wpcf7-f837-o3`, `FormName=Заявка Бизнес`, `service_id=2`, and popup title `Подключить услуги для бизнеса`. No service-specific form identity was observed. The A/B suffix in `Info` varies between page loads and is not evidence of a different business form. One registry case represents this shared form; it uses the exact “Корпоративные тарифы” card as a stable entry trigger.

## Samara route

- Entry and final business URL: `https://mts-home-online.ru/business`.
- Region mode: popup selection without navigation away from `/business`.
- Trigger: `.autocomplete-city-change.button-select-city` inside the target form.
- Popup: `#popup-select-city`.
- Search: `input#city-input.popup-select-city__input`.
- Exact choice: `a.region_item.region_link[id='36401']`, text `Самара`.
- Choice href: `https://mts-home-online.ru/samara`.
- After the click the business form shows `Самара`, `data-item=36401`, `CityName=Самара`, and `BusinessCityId=36401`.

The saved case configuration was exercised through the production runner's `FormAdapter.open_form` and `ensure_samara` functions: final URL remained `/business`, observed city was Самара / `36401`, and `submit_clicked=false`.

## Blocked-submit contract onboarding

The confirmed production data profile was filled, the submit control was clicked, and every POST was intercepted and aborted before network dispatch. No MTS lead was created. The target multipart request was:

- `POST https://mts-home-online.ru/wp-json/contact-form-7/v1/contact-forms/837/feedback`;
- region: `CityName=Самара`, `BusinessCityId=36401`;
- business identity: `FormName=Заявка Бизнес`, `lead_form_type=forma_podklyucheniya_biznes`, `service_id=2`;
- form identity: `_wpcf7=837`, `_wpcf7_unit_tag=wpcf7-f837-o3`.

The hidden descriptive `Info` field still contained `Город: Выбрать город`. The structured region fields are correct and are enforced before dispatch; the stale description remains a CRM-verification risk for the pilot.

The deployed page listens for `wpcf7submit`, requires `event.detail.status === 'mail_sent'`, and then assigns `/tilda/form1/submitted`. That exact success page returned HTTP 200 without a redirect during a read-only GET. At the end of blocked-submit onboarding, the case had an executable fail-closed contract and was ready for one live pilot.

## Production pilot

After explicit user approval, exactly one live run was executed with the confirmed Samara data profile. It passed in 7.84 seconds:

- UI city: `Самара`, `data-item=36401`;
- region, business, and form identity checks passed before dispatch;
- target request: observed `1`, forwarded `1`;
- HTTP `200`, response `status=mail_sent`, no invalid fields;
- exact `/tilda/form1/submitted` URL assertion passed;
- three known analytics writes were blocked;
- no guard errors and no automatic retry.

The automated production result is PASS. Delivery of this MTS request to CRM remains unconfirmed until the user checks the CRM.

## Sources and limits

- Business rule: user message dated 16.09.2026.
- Browser artifacts are stored locally under ignored `artifacts/onboarding-20260916/`; no dynamic signatures or analytics identifiers are committed.
- [QA workflow](../references/qa/analyze-task.md).
- [Test-design techniques](../references/qa/techniques.md).
- [Functional specification](../specs/01-business-test-spec.md).
