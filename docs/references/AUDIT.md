# Аудит бизнес-заявок: Everyday_test и Big_landing_test

Дата: 15.09.2026. Область: формы на бизнес-страницах и выбор «Для бизнеса / в офис» в формах.

## Вывод

**Зелёный результат этих тестов сейчас не доказывает корректность бизнес-заявок.** Выделенные business-сценарии отключены на разных уровнях; варианты услуги и дополнительные чекбоксы обрабатываются отдельно, а ошибки могут быть обнулены после успешной отправки другой заявки.

Это аудит кода тестов. Он выявляет дефекты и ограничения проверок, а не доказывает неисправность сайта или потерю реальных заявок.

Зафиксированные версии GitHub:

- Everyday_test, master: `8e87c77a79430e1a54b110682cf9f7912a29cac5`.
- Big_landing_test, main: `04e7a4fa2554357666e2058432efab527f9c9186`.

## Подтверждённые замечания

### 1. P1 — выделенные business-сценарии не проверяют отправку

**Everyday_test:** `resolve_service_values_for_mode()` возвращает пустой список для `form_type == "business"` при любом режиме. Цикл пропускает такую форму. Открытие /business и попапа ещё возможно, но отправки распознанной business-формы не происходит. Отсутствие business-кнопок тоже возвращает `0 success, 0 failed`.

Источники: [отключение отправки](https://github.com/deidolinde-maker/Everyday_test/blob/8e87c77a79430e1a54b110682cf9f7912a29cac5/test_universal2.py#L1681-L1717), [пропуск в цикле](https://github.com/deidolinde-maker/Everyday_test/blob/8e87c77a79430e1a54b110682cf9f7912a29cac5/test_universal2.py#L2842-L2853), [отсутствие кнопок](https://github.com/deidolinde-maker/Everyday_test/blob/8e87c77a79430e1a54b110682cf9f7912a29cac5/test_universal2.py#L3069-L3081).

**Big_landing_test:** `ENABLE_BUSINESS_SUBMIT_STEPS = False` выключает шаги 3 и 4b. В URL-режиме с ожидаемой единственной формой business остальные шаги тоже неприменимы. Изолированная проверка текущей функции подтвердила: сценарий возвращается нормально, не вызвав навигацию и отправку.

Источники: [флаг](https://github.com/deidolinde-maker/Big_landing_test/blob/04e7a4fa2554357666e2058432efab527f9c9186/big_landing_code.py#L798-L803), [пропуск обычных попапов](https://github.com/deidolinde-maker/Big_landing_test/blob/04e7a4fa2554357666e2058432efab527f9c9186/big_landing_code.py#L4058-L4066), [шаг 3](https://github.com/deidolinde-maker/Big_landing_test/blob/04e7a4fa2554357666e2058432efab527f9c9186/big_landing_code.py#L4156-L4167), [шаг 4b](https://github.com/deidolinde-maker/Big_landing_test/blob/04e7a4fa2554357666e2058432efab527f9c9186/big_landing_code.py#L4323-L4344).

**Рекомендация:** отключённую обязательную бизнес-проверку явно отражать как непроверенную; после снятия временного отключения требовать успешную отправку каждого ожидаемого бизнес-сценария. Само наличие сценария с названием business недостаточно.

### 2. P1 — ошибка бизнес-варианта может превратиться в успешный тест

В обоих репозиториях при `total_success_submits > 0` счётчик ошибок `f` обнуляется до `assert f == 0`.

Пример: вариант «В квартиру» отправился, «Для бизнеса» не отправился. Обработчик вернул одну успешную и одну неуспешную попытку, но итоговый сценарий завершился без ошибки. Это воспроизведено на изолированной функции каждого репозитория с подставленным результатом цикла.

Источники: [Everyday_test](https://github.com/deidolinde-maker/Everyday_test/blob/8e87c77a79430e1a54b110682cf9f7912a29cac5/test_universal2.py#L3482-L3500), [Big_landing_test](https://github.com/deidolinde-maker/Big_landing_test/blob/04e7a4fa2554357666e2058432efab527f9c9186/big_landing_code.py#L4137-L4153). Аналогичное подавление есть в шагах /business: [Everyday_test](https://github.com/deidolinde-maker/Everyday_test/blob/8e87c77a79430e1a54b110682cf9f7912a29cac5/test_universal2.py#L3525-L3541), [Big_landing_test](https://github.com/deidolinde-maker/Big_landing_test/blob/04e7a4fa2554357666e2058432efab527f9c9186/big_landing_code.py#L4212-L4242); в Big эти шаги сейчас отключены.

**Рекомендация:** хранить результат отдельно для каждой бизнес-формы и варианта; подавление уведомления не должно менять результат проверки.

### 3. P1 — бизнес-чекбокс не отделён от остальных дополнительных чекбоксов

`apply_form_checkboxes()` просматривает все `input[type='checkbox']`, отмечает до четырёх дополнительных чекбоксов, при повторной отправке — до двенадцати. Он не проверяет назначение чекбокса. Ошибка `check()` только печатается; вызывающий код не получает признак неуспеха.

Следствия, подтверждённые на синтетических элементах:

- видимый необязательный бизнес-чекбокс автоматически включается;
- скрытый в обычной попытке пропускается, а при retry предпринимается принудительный выбор;
- неработающий чекбокс не прерывает заполнение формы;
- отдельной проверки состояний «выключен → включён → выключен» нет.

Кроме того, в `select_service_place_value()` fallback после неудачного `check()` вызывает `click()` и сразу возвращает True. Контроль `is_checked()` после fallback отсутствует. Изолированная проверка показала возврат True при неизменившемся состоянии.

Источники: [Everyday_test: общие чекбоксы](https://github.com/deidolinde-maker/Everyday_test/blob/8e87c77a79430e1a54b110682cf9f7912a29cac5/test_universal2.py#L1784-L1865), [Big_landing_test: общие чекбоксы](https://github.com/deidolinde-maker/Big_landing_test/blob/04e7a4fa2554357666e2058432efab527f9c9186/big_landing_code.py#L1827-L1908), [Everyday_test: fallback выбора](https://github.com/deidolinde-maker/Everyday_test/blob/8e87c77a79430e1a54b110682cf9f7912a29cac5/test_universal2.py#L1720-L1744), [Big_landing_test: fallback выбора](https://github.com/deidolinde-maker/Big_landing_test/blob/04e7a4fa2554357666e2058432efab527f9c9186/big_landing_code.py#L1763-L1787).

**Рекомендация:** отдельный селектор бизнес-чекбокса, явное ожидаемое состояние и обязательная проверка состояния перед отправкой; общий обработчик согласий не должен менять тип заявки.

### 4. P2 — покрытие «Для бизнеса / в офис» зависит от разметки и режима

Оба теста ищут только `input[name='Place']` с тремя точными значениями: «В квартиру», «В частный дом», «Для бизнеса».

- В `core` выбирается первый найденный вариант по этому списку — обычно «В квартиру».
- В `variants/all` перебираются только найденные варианты: исчезновение «Для бизнеса» не вызывает ошибку отсутствия обязательного варианта.
- Отдельного сопоставления «В офис» нет. **Оговорка:** если это только видимая подпись, а фактический value остаётся «Для бизнеса», существующий селектор может подойти. Текущая DOM-разметка сайтов в этом аудите не проверялась.
- В отдельном шаге checkaddress нет перебора Place: `fill_form()` вызывается без `service_place_value`. Это не исключает обработку checkaddress через общий цикл попапов там, где он собирает такую кнопку.

Источники: [Everyday_test: значения](https://github.com/deidolinde-maker/Everyday_test/blob/8e87c77a79430e1a54b110682cf9f7912a29cac5/test_universal2.py#L787-L791), [обнаружение и режимы](https://github.com/deidolinde-maker/Everyday_test/blob/8e87c77a79430e1a54b110682cf9f7912a29cac5/test_universal2.py#L1666-L1717), [checkaddress](https://github.com/deidolinde-maker/Everyday_test/blob/8e87c77a79430e1a54b110682cf9f7912a29cac5/test_universal2.py#L3400-L3417); [Big_landing_test: значения](https://github.com/deidolinde-maker/Big_landing_test/blob/04e7a4fa2554357666e2058432efab527f9c9186/big_landing_code.py#L722-L726), [обнаружение и режимы](https://github.com/deidolinde-maker/Big_landing_test/blob/04e7a4fa2554357666e2058432efab527f9c9186/big_landing_code.py#L1715-L1760), [checkaddress](https://github.com/deidolinde-maker/Big_landing_test/blob/04e7a4fa2554357666e2058432efab527f9c9186/big_landing_code.py#L3680-L3682).

В Jenkinsfile обоих проектов первым вариантом SERVICE_MODE задан core. Это описание конфигурации по умолчанию, а не утверждение о параметрах последнего фактического запуска. [Everyday_test](https://github.com/deidolinde-maker/Everyday_test/blob/8e87c77a79430e1a54b110682cf9f7912a29cac5/Jenkinsfile#L13), [Big_landing_test](https://github.com/deidolinde-maker/Big_landing_test/blob/04e7a4fa2554357666e2058432efab527f9c9186/Jenkinsfile#L31).

**Рекомендация:** для согласованных форм явно задать наличие и способ выбора бизнес-варианта; его отсутствие считать отдельным результатом проверки. Включать такие сценарии в обязательный профиль запуска.

### 5. P1 — успешная отправка не подтверждает бизнес-тип заявки

`submit_with_confirmation()` принимает переход на success URL либо CF7 `mail_sent`. В проверяемой цепочке нет проверки переданного бизнес-признака в теле запроса и типа созданной заявки в сервисе.

Следовательно, тест способен принять обычную заявку за успешное выполнение бизнес-сценария, если сайт показывает такое же подтверждение. В Everyday_test поле `service_value` локального артефакта заполняется значением из сценария, а не прочитанным результатом обработки заявки сервером.

Источники: [Everyday_test: подтверждение](https://github.com/deidolinde-maker/Everyday_test/blob/8e87c77a79430e1a54b110682cf9f7912a29cac5/test_universal2.py#L2260-L2265), [локальная запись](https://github.com/deidolinde-maker/Everyday_test/blob/8e87c77a79430e1a54b110682cf9f7912a29cac5/test_universal2.py#L2925-L2941), [Big_landing_test: подтверждение](https://github.com/deidolinde-maker/Big_landing_test/blob/04e7a4fa2554357666e2058432efab527f9c9186/big_landing_code.py#L2454-L2459).

**Рекомендация:** сверять фактический бизнес-признак отправленного запроса с контрактом; если требуется сквозная проверка, по идентификатору созданной заявки сверять тип на сервере. Название поля и допустимые значения должны быть взяты из реального контракта — в предоставленных материалах они не установлены.

## Что входит в business-набор Big_landing_test

В `config/form_allowlists/business.txt` активны только:

- https://rtk-internet.online/business
- https://rtk-home.ru/business
- https://online-beeline.ru/business

Два MTS URL закомментированы. В `urls/mts.txt` также закомментированы три business URL. Это фактическое исключение из текущего набора; корректность причины исключения аудит кода не устанавливает. [Business allowlist](https://github.com/deidolinde-maker/Big_landing_test/blob/04e7a4fa2554357666e2058432efab527f9c9186/config/form_allowlists/business.txt#L1-L5), [MTS URL](https://github.com/deidolinde-maker/Big_landing_test/blob/04e7a4fa2554357666e2058432efab527f9c9186/urls/mts.txt#L55-L62).

При этом отключение выделенного business-шагa **не отключает все потенциальные бизнес-заявки**: остаются Place-варианты в обычных формах и формы connection на некоторых /business URL. В connection allowlist присутствуют `moskva.beeline-ru.online/business`, `online-beeline.ru/business`, `beeline-internet.online/business`. [Источник](https://github.com/deidolinde-maker/Big_landing_test/blob/04e7a4fa2554357666e2058432efab527f9c9186/config/form_allowlists/connection.txt#L195-L205).

## Проверка выводов и границы

- Исходники и конфигурация получены через GitHub MCP на указанных SHA.
- Выполнены изолированные проверки оригинальных функций через AST и синтетические объекты. Проверялись ветвления, обработка результата и чекбоксы; браузер, сайт, отправка заявок и уведомления не запускались.
- [Архивные результаты изолированных проверок исходных тестов](probe-results.json). Текущий механизм нового теста проверяется отдельно в tests/unit и tests/browser.
- MCP-наблюдение: окружение **stage**, `mcp__stage_qa_mcp__orders_health({})`, сервис 101_orders вернул `ok`. Это только доступность stage-сервиса, не подтверждение типа или доставки заявки. Production не проверялся.
- Бизнес-контракта с именами полей заявки и полной матрицей обязательных форм нет. Рекомендации выше не подменяют эти требования.
- Специализированного доменного раздела docs/qa-kb/domains в доступной QA-базе нет.

## Использованная QA-база

- [Workflow анализа QA-задачи](qa/analyze-task.md): выводы привязаны к коду; отсутствие ошибки не считается доказательством корректности.
- [Техники тест-дизайна](qa/techniques.md): таблица решений «тип формы × режим × вариант» и переходы состояния бизнес-чекбокса.
- [Контекст Everyday_test](qa/everyday-context.md): назначение sender и ограниченность выводов единичного исторического прогона; исторический green не использовался как доказательство текущего покрытия.
- [Маршрутизация MCP](qa/mcp-routing.md): stage отделён от production, health отделён от бизнес-проверки.
