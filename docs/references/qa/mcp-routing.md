---
title: MCP Stage Routing
type: integration-guide
scope: project
status: reviewed
project: 101 internet
---

# Маршрутизация QA-задач в MCP stage и production

CLI определяет вероятный сервис и предлагает узкий MCP-инструмент. Сам вызов выполняется агентом после проверки среды, входных параметров и схемы инструмента.

Для 101 internet доступны два окружения: stage для безопасной проверки изменений и production для проверки фактического пользовательского контура. Stage не удаляется при подключении production.

| Область задачи | Сервис | Пример инструмента |
|---|---|---|
| Адреса, улицы, дома | `101_address` | `mcp__stage_qa_mcp__address_search_streets` |
| Провайдеры и каталог | `101_catalog` | `mcp__stage_qa_mcp__graphql_query_providers_list_next` |
| Заказы и платежи | `101_orders` | `mcp__stage_qa_mcp__orders_health` |
| Админ-панель | `101_admin_new` | `mcp__stage_qa_mcp__admin_new_health` |
| Sitemap, robots, индексация | `101_sitemap` | `mcp__stage_qa_mcp__sitemap_health` |

Health-инструмент является безопасной проверкой доступности, а не доказательством корректности бизнес-сценария. Для предметной проверки нужно выбрать endpoint-инструмент и передать валидные тестовые данные.

Production-проверки по умолчанию должны быть read-only. Запросы, которые изменяют данные, допускаются только при явном согласовании и с безопасными тестовыми данными.
