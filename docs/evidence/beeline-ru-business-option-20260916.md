# Beeline RU business-option — 16.09.2026

`beeline-business_option-afd9e17b2c35` at `https://beeline-ru.online/` represents the largest discovered Beeline option-form template group.

Read-only inspection found form `wpcf7-f430-o1`, `select[name='Place']`, address fields and `.checkaddress_address_button_send`. The popup selected Samara through `#popup-select-city a.region_item.region_link[id='36401']`; the form showed `Самара`, UI ID `36401`, while the base URL stayed unchanged. After selecting a Samara street and house from the ordinary address popup, hidden `CityName=Самара`, `City=36401`, `IStreet=313620` and `IHouse=293579` were populated. The user confirmed that any popup-selected address is acceptable.

A blocked-submit capture proved `POST https://beeline-ru.online/wp-admin/admin-ajax.php` with `Place=Для бизнеса`, the Samara fields and form identity `FormName=Проверьте подключение`, `lead_form_type=forma_proverit'_adress`, `service_id=2`.

One explicitly approved production pilot forwarded exactly one target POST; all other writes were blocked. The response was non-JSON and the page stayed at the root URL, so CRM delivery remains pending user confirmation. No repeat was sent.

Sources: user requirements, 16.09.2026; ignored local onboarding artifacts; [QA workflow](../references/qa/analyze-task.md).
