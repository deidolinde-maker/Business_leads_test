# Business_leads_test

Независимый pytest/Playwright тест бизнес-заявок **только для Самары**. Один кейс — одна форма, проверка бизнес-режима и региона, одна отправка, отдельный результат.

## Состояние стартовой версии

Пользователь подтвердил получение в CRM заявки последнего пилота мобильной связи Билайна с десятизначным номером. Подтверждение относится к этому конкретному сценарию; [источник и технический результат прогона](docs/evidence/production-onboarding-20260916.md) сохранены отдельно.

- Реализованы два маршрута: выбор Самары через попап (R1) и прямой вход на проверенный городской бизнес-URL (R2).
- Импортированы скоуп и исходные локаторы Everyday_test / Big_landing_test без зависимости от их кода во время запуска.
- В реестре **266 записей для уточнения**: 262 исходных кандидата и 4 самарские бизнес-страницы, заданные пользователем 16.09.2026. Всего 20 URL бизнес-страниц и 246 страниц-кандидатов на наличие бизнес-переключателей. Это не 266 подтверждённых бизнес-форм.
- Для четырёх поддоменных страниц заданы точные входные URL и режим R2; для остальных Самара также обязательна. См. [самарские маршруты](docs/SAMARA_ROUTES.md).
- Подключены 3 `active` кейса: 2 Билайна и 1 MTS; в реестре также 258 `blocked` и 5 `excluded`. На мобильной бизнес-странице Билайна номер из 10 цифр дал `mail_sent`, переход `/thanks` и подтверждённую пользователем доставку в CRM. Исправление учёта служебного запроса проверено на 16 локальных браузерных тестах. [Все результаты и ограничения](docs/evidence/production-onboarding-20260916.md).
- Для МТС отдельная бизнес-форма берётся только с `https://mts-home-online.ru/business`. Один production-прогон прошёл: регион и бизнес-признаки совпали, получен `mail_sent`, переход `/tilda/form1/submitted`, пользователь подтвердил корректную доставку в CRM. Остальные MTS business-page записи исключены. Отдельный MTS business-option на главной странице использует `select[name=Place]`, а не checkbox; его UI проверен, но он остаётся blocked до проверки адресной подготовки и payload. [Business-page](docs/evidence/mts-business-scope-20260916.md), [business-option](docs/evidence/mts-business-option-select-20260916.md).
- Пользователь подтвердил production и затем заменил номер на `9999999999`; текущий профиль: Самара, Ленинградская, 1. Цифры сохранены буквально. Live-команда действительно отправляет заявку: автоматических повторов нет.
- Локальные проверки работают на синтетическом HTTP-сервере. Они не создают заявки на сайтах провайдеров.
- Два основных репозитория пока не менялись: переключение выполняется после подтверждения нового live-набора.

## Установка и локальный запуск

Python 3.12+. Linux-агенту нужны системные зависимости Chromium; в GitHub Actions они устанавливаются через `playwright install --with-deps chromium`.

```text
python -m venv .venv
# Активируйте .venv подходящей командой своей оболочки.
python -m pip install -e .
python -m playwright install chromium
python -m pytest
```

Обычный pytest запускает только unit/browser проверки локального механизма. Это не live-прогон.

Если браузер установлен в нестандартную папку, задайте `PLAYWRIGHT_BROWSERS_PATH`. В рабочей копии разработки он установлен в `.browsers`; для запуска из PowerShell:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) '.browsers'
.venv/Scripts/python.exe -m pytest
```

## Посмотреть целевой скоуп без сайтов и заявок

```text
python -m pytest tests/test_business_submission.py --env=prod --collect-only
python -m pytest tests/test_business_submission.py --env=prod --provider=rostelecom --collect-only
```

`config/source_inventory.json` хранит все 1195 исходных записей/ссылок, включая allowlists и закомментированные URL. `config/locator_sources.json` хранит точные импортированные константы с SHA и строками источников. `config/region_locators.json` — HTML-контракт Самары из задачи. В broad legacy селекторах могут быть неподходящие city/address fallback: перед активацией выбрать точный selector нужного поля.

Импорт повторяется через `tools/import_scope.py` в новую папку с последующим ревью diff; он не перезаписывает отредактированный реестр.

## Подключение реальной формы

1. Для исходного URL установить реальную схему города и подтверждённые входной/самарский бизнес-URL. Московские URL — только происхождение, не цели запуска.
2. Записать единственный локатор формы/триггера, необходимые поля, согласия и checkbox/radio. Значение `#autocomplete_city_name` проверяется в этой форме, не глобально.
3. Для R1 заполнить `trigger`, `popup`, `search`, `choice`, `choice_url`, `after_choice_url`, `business_url`. `after_choice_url` описывает реальную навигацию либо прежний URL при обновлении формы без перехода.
4. Установить фактический POST endpoint, кодировку, `region_match`, `business_match`, `identity_match` и положительный ответ. В контракте явно задать `target_city=Самара`, `target_city_ui_id=36401` и evidence соответствия backend-значений этому городу. UI ID `36401` не считается автоматически backend ID. Match-значения имеют точные типы, JSON пути разделяются точкой.
5. Подтвердить тестовые адресные данные/телефон и установить окружение в отдельном data profile. Не менять число цифр телефона автоматически.
6. Приложить evidence/verification и перевести запись в `active`. Существующий синтетический пример — `tests/support.py`; его поля нельзя переносить как контракт провайдерского сайта.

После подтверждения конфигурации:

```text
python -m pytest tests/test_business_submission.py --env=prod --case-id=<verified-id> --data-file=<confirmed-data.json>
```

Полный запуск с blocked-кейсами завершится ошибкой и покажет неполное покрытие. Фильтр позволяет проверить конкретный уже подтверждённый кейс; отчёт относится только к выбранному скоупу. Stage URL не генерируются из production, поэтому пока stage-фильтр даёт ошибку пустого набора.

### Пакетная разведка blocked business-option

Чтобы быстрее отбирать формы с `checkbox`/`radio`/`select Place`, запускайте read-only discovery: она открывает несколько уникальных URL параллельно, не заполняет формы и отменяет каждый запрос кроме `GET`/`HEAD`/`OPTIONS`. Отчёт является только списком кандидатов: Самару и контракт заявки всё равно подтверждают перед переводом кейса в `active`.

```powershell
$env:BUSINESS_CHROMIUM_EXECUTABLE = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
python tools/discover_business_options.py --provider mts --limit 12 --concurrency 4 --output artifacts/discovery/mts.json
```

Для точечной проверки добавьте `--case-id <id>`; `--limit 0` выбирает все совпадающие уникальные URL. Для следующего батча используйте `--offset 12`. В `template_groups` отчёта одинаковые DOM-формы объединены только для приоритизации: каждый URL всё равно требует собственной проверки Самары и payload перед активацией.

## Отправка и ограничения v0.1

- Перед нажатием submit проверяются Самара/36401 и бизнес-control. Перед передачей POST проверяются фактические регион, бизнес-признак и идентичность формы. Несовпадение отменяет запрос, не исправляет payload.
- Поддержаны JSON, form-urlencoded и текстовый multipart. Варианты GET-submit, файлы и WebSocket-submit не реализованы и не должны становиться active. Service workers блокируются для перехвата запросов.
- Только один запрос по целевому endpoint передаётся. Повторная отправка не выполняется; ошибки не подавляются успехами других кейсов.
- POST передаётся через `route.fetch(max_redirects=0, max_retries=0)`, полученный ответ передаётся браузеру. Ответ 307/308 не поддержан. Для native POST redirect требуется точный положительный статус и Location; автоматический повтор POST отсутствует.
- Известные read-only POST зависимости формы допускаются только по точному URL/method с evidence. Остальные записи не отправляются; неожиданный write после submit даёт ошибку.
- Guard предназначен для изученного механизма конкретного POST-контракта. Он не является универсальной гарантией для ещё не исследованных сторонних способов отправки, GET с побочным эффектом или отложенных дублей после завершения кейса. Такие формы остаются blocked до адаптера.
- Тип доставки в CRM не проверяется этой версией. PASS означает принятый целевым endpoint бизнес-запрос Самары плюс подтверждение UI.
- Общий runtime deadline — 75 с; длительности фаз сохраняются. Фактический SLA реальных сайтов ещё не измерен.

Сетевая реализация опирается на официальные [Route API](https://playwright.dev/python/docs/api/class-route) и [Network](https://playwright.dev/python/docs/network). `fetch` разрешается только после проверки содержимого запроса.

## Отчёты и CI

`artifacts/<case_id>/result.json` содержит результат и длительности; при ошибке сохраняется скриншот с маскировкой полей. `artifacts/summary.json` показывает active/blocked/excluded, passed/failed/incomplete и полное покрытие выбранной области. Collect-only всегда обозначен как collection, не PASS.

GitHub Actions проверяет только локальные fixtures. Jenkinsfile содержит режимы local/collect/live; по умолчанию local. Самара фиксирована, параметра произвольного города нет. Скрипт CI передаёт фильтры через argv, а не вставляет их в shell-команду.

## Документы

- [Функциональная спецификация](docs/specs/01-business-test-spec.md).
- [Реализация и миграция](docs/specs/02-implementation-and-migration.md).
- [Прогресс и ограничения](docs/IMPLEMENTATION_STATUS.md).
- [Исходный аудит](docs/references/AUDIT.md).
- [QA workflow](docs/references/qa/analyze-task.md), [техники тест-дизайна](docs/references/qa/techniques.md), [контекст Everyday_test](docs/references/qa/everyday-context.md), [MCP routing](docs/references/qa/mcp-routing.md).
