# Everyday_test

tags: project-context everyday-test sender region-popup allure

## Назначение

Основной sender для UI-проверки форм заявок на лендингах провайдеров. Основной сценарий находится в `Everyday_test/test_universal2.py`.

## Подтверждённый результат

- Jenkins build `#144` для `https://rtk-ru.online/` завершился `1 passed, 0 failed`.
- Профиль запуска: `core`, Chromium, desktop, `blocking_profile=none`, `network_profile=off`.
- Успешный submit переходил на `https://rtk-ru.online/tilda/form1/submitted`.
- После возврата на главную штатная кнопка смены города формы с классами `autocomplete-city-change button-select-city checkaddress_address_button_change_city` больше не считалась открытым region popup.
- Исправление sender зафиксировано коммитом `e20cedd` (`Fix false region popup detection`).

## Диагностическое правило

Кнопка смены города внутри address-form не является доказательством открытого регионального popup. При проверке возврата после страницы Thanks нужно отличать её от overlay регионального выбора.

## Границы вывода

Подтверждён только точечный прогон `rtk-ru.online` в build `#144`. Это не доказательство полного green по всем провайдерам и браузерам.

## Источники

- `C:/Users/Deido/OneDrive/Документы/GitHub/Everyday_test/test_universal2.py`
- `C:/Users/Deido/OneDrive/Документы/GitHub/Everyday_test/README.md`
- `C:/Users/Deido/Downloads/allure-report (7).zip`
