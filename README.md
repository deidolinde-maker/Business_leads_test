# Business_leads_test

Независимый pytest/Playwright тест бизнес-заявок **только для Самары**. Один кейс повторяет короткий пользовательский путь: открыть форму, выбрать Самару и бизнес-вариант, заполнить адрес и телефон, отправить заявку и увидеть страницу «Спасибо».

## Состояние стартовой версии

Пользователь подтвердил получение в CRM заявки последнего пилота мобильной связи Билайна с десятизначным номером. Подтверждение относится к этому конкретному сценарию; [источник и технический результат прогона](docs/evidence/production-onboarding-20260916.md) сохранены отдельно.

- Реализованы два маршрута: выбор Самары через попап (R1) и прямой вход на проверенный городской бизнес-URL (R2).
- Импортированы скоуп и исходные локаторы Everyday_test / Big_landing_test без зависимости от их кода во время запуска.
- В реестре **266 записей для уточнения**: 262 исходных кандидата и 4 самарские бизнес-страницы, заданные пользователем 16.09.2026. Всего 20 URL бизнес-страниц и 246 страниц-кандидатов на наличие бизнес-переключателей. Это не 266 подтверждённых бизнес-форм.
- Для четырёх поддоменных страниц заданы точные входные URL и режим R2; для остальных Самара также обязательна. См. [самарские маршруты](docs/SAMARA_ROUTES.md).
- Бизнес-попапы подключаются только для подтверждённых семейств: `online-beeline.ru`, `beeline-internet.online`, `beeline-ru.online` (включая городской поддомен), `rtk-home.ru`, `rtk-ru.online` (включая `city.rtk-ru.online`), `rtk-internet.online` и `mts-home-online.ru`. На остальных сайтах в скоупе остаются только `Place`/checkbox business-option сценарии.
- Подключены 15 `active` кейсов: подтверждённые MTS/Beeline сценарии и пакет business-page маршрутов на разрешённых доменах; в реестре также 243 `blocked` business-option кандидата и 8 `excluded`. Два дубликата конечных самарских страниц исключены, чтобы одна форма не отправлялась дважды. На мобильной бизнес-странице Билайна номер из 10 цифр дал переход `/thanks` и подтверждённую пользователем доставку в CRM. [Все результаты и ограничения](docs/evidence/production-onboarding-20260916.md).
- Для МТС отдельная бизнес-форма берётся только с `https://mts-home-online.ru/business`. Один production-прогон прошёл: регион и бизнес-признаки совпали, получен `mail_sent`, переход `/tilda/form1/submitted`, пользователь подтвердил корректную доставку в CRM. Остальные MTS business-page записи исключены. Отдельный MTS business-option на главной странице использует `select[name=Place]`; его exact Samara payload, HTTP 200, страница «Спасибо» и CRM-пилот подтверждены. [Business-page](docs/evidence/mts-business-scope-20260916.md), [business-option](docs/evidence/mts-home-online-business-option-20260916.md).
- Для `Place`-представителей MTS Home Online и Beeline пользователь подтвердил поступление однократных production-пилотов в CRM. Положительный признак берётся из исходных наборов: `/tilda/form1/submitted` для MTS и `/thanks` для Beeline.
- Пользователь подтвердил production и затем заменил номер на `9999999999`; текущий профиль: Самара, Ленинградская, 1. Цифры сохранены буквально. Live-команда действительно отправляет заявку: автоматических повторов нет.
- Локальные проверки работают на синтетическом HTTP-сервере. Они не создают заявки на сайтах провайдеров.
- Два основных репозитория пока не менялись: переключение выполняется после подтверждения нового live-набора.

## Установка и локальный запуск

Python 3.10+. Linux-агенту нужны системные зависимости Chromium; в GitHub Actions они устанавливаются через `playwright install --with-deps chromium`.

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
4. Задать проверенную страницу «Спасибо» для этой формы.
5. Подтвердить тестовые адресные данные/телефон и установить окружение в отдельном data profile.
6. Приложить evidence/verification и перевести запись в `active`.

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

Jenkins выполняет только production live-прогон с отправкой заявок. Базовый реестр — `config/business_cases.json`, поэтому в общий запуск входят оба потока: бизнес-попапы (`business_page`) и формы с Place/checkbox/select (`business_option`). Параметр `FLOW_SCOPE` позволяет выбрать `all`, `business_popup` или `forms`, а `DOMAIN` — конкретный домен из списка. `PROVIDER` и `CASE_ID` уточняют область дополнительно. Каждый выбранный active-кейс выполняется один раз.

Расписание Jenkins: ежедневно в **07:00 по Москве** (`04:00 UTC`). После прогона строится Allure-отчёт и формируется Telegram-алерт по схеме Everyday_test: сводка, точечные/массовые ошибки и восстановленные домены. Для отправки нужны Jenkins-переменные `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` либо proxy-переменные Everyday.

## Отправка и результат

- Перед отправкой в целевой форме проверяются Самара/36401 и выбранный бизнес-вариант.
- Браузер отправляет форму обычным способом сайта; тест не перехватывает и не анализирует запросы.
- PASS означает, что после клика открылась подтверждённая для этой формы страница «Спасибо».
- Общий runtime deadline — 75 с; длительности пользовательских шагов сохраняются.

## Отчёты и CI

`artifacts/<case_id>/result.json` содержит результат и длительности; при ошибке сохраняется скриншот с маскировкой полей. `artifacts/summary.json` показывает active/blocked/excluded, passed/failed/incomplete и полное покрытие выбранной области. Collect-only всегда обозначен как collection, не PASS.

GitHub Actions проверяет только локальные fixtures. Jenkins всегда использует production live и active-подмножество реестра; blocked/excluded URL не открываются и не отправляют заявку. Самара фиксирована, параметра произвольного города нет. Скрипт CI передаёт фильтры через argv, а не вставляет их в shell-команду.

Jenkins хранит кэш Python-пакетов и Chromium Playwright в постоянной директории Jenkins-пользователя. Первый запуск заполняет кэш, последующие используют его даже после нового checkout или очистки workspace.

## Документы

- [Функциональная спецификация](docs/specs/01-business-test-spec.md).
- [Реализация и миграция](docs/specs/02-implementation-and-migration.md).
- [Прогресс и ограничения](docs/IMPLEMENTATION_STATUS.md).
- [Исходный аудит](docs/references/AUDIT.md).
- [QA workflow](docs/references/qa/analyze-task.md), [техники тест-дизайна](docs/references/qa/techniques.md), [контекст Everyday_test](docs/references/qa/everyday-context.md), [MCP routing](docs/references/qa/mcp-routing.md).
