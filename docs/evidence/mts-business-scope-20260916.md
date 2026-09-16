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

The saved case configuration was exercised through the production runner's `FormAdapter.open_form` and `ensure_samara` functions: final URL remained `/business`, observed city was Самара / `36401`, and `submit_clicked=false`. The hidden `Info` field still contained the preselection wording `Город: Выбрать город`; its outgoing value must be checked during contract onboarding. The submit endpoint, exact business/region payload contract, positive response, and CRM delivery remain unverified, so the target case stays `blocked`.

## Sources and limits

- Business rule: user message dated 16.09.2026.
- Browser artifacts are stored locally under ignored `artifacts/onboarding-20260916/`; no dynamic signatures or analytics identifiers are committed.
- [QA workflow](../references/qa/analyze-task.md).
- [Test-design techniques](../references/qa/techniques.md).
- [Functional specification](../specs/01-business-test-spec.md).
