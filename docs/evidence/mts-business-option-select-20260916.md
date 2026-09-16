# MTS business-option select — 16.09.2026

## Scope

This evidence covers the separate `business_option` candidate `mts-business_option-d5a93099ffb1` for `https://mts-home-online.ru/`. It is not the confirmed MTS business-page form at `/business`.

The source inventory contains this root URL in both original repositories as a business-option candidate. The current page has a regular link `Для бизнеса` to `/business`, but its ordinary connection forms also contain a distinct `Place` control. The latter is the subject of this evidence.

## Read-only production observation

Chromium opened `https://mts-home-online.ru/` with HTTP 200 while every POST was blocked. Five CF7 forms were present. The inspected visible check-address form had:

- form ID `_wpcf7=995`, unit tag `wpcf7-f995-o1`;
- `select[name='Place']` with the exact options `В квартиру`, `В частный дом`, and `Для бизнеса`;
- the default value `В квартиру`;
- address fields `AddresStreet`, `AddresHouse`, `Phone` and submit `.checkaddress_address_button_send`.

The control is a `select`, not a checkbox or radio. Selecting `Для бизнеса` through the browser's native select interaction succeeded. The form's city popup then selected the exact Samara link `a.region_item.region_link[id='36401']`, whose href is `https://mts-home-online.ru/samara`. The page stayed at the root URL and the active form indicator became `Самара` with `data-item=36401`.

## Blocking facts

No address fields were filled and submit was not clicked. After the UI city selection, the inspected form still had empty hidden `CityName` and `City`; its descriptive `Info` field still said `Город: Москве`. These facts do not establish the region carried in a business-option submission.

The candidate therefore remains `blocked` until a non-submitting address preparation proves the exact city fields, a blocked multipart capture proves the business/region payload, and the positive response contract is identified. No MTS business-option lead was sent.

## Adapter change

The shared adapter now supports a verified `business_control.kind="select"`. An active select case must provide exact `business_value` and `alternative_value`; the runner switches alternative → business → alternative → business and checks Samara after every transition. A local browser fixture verifies that the final submitted payload is business after this sequence.

## Sources

- User requirement separating MTS business pages from checkbox/business-option scope, 16.09.2026.
- Local ignored browser artifacts under `artifacts/onboarding-20260916/`; all production POSTs were aborted.
- [QA analysis workflow](../references/qa/analyze-task.md).
- [Test-design techniques](../references/qa/techniques.md).
- [Functional specification](../specs/01-business-test-spec.md).
