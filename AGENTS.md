# AGENTS.md

Правила для ИИ-агентов и контрибьюторов, работающих с этим репозиторием.

## Что это

`techwriter-super-agent` — self-hosted Discord-ассистент технического писателя с
телеметрией (Postgres) и дашбордом аналитики. Упаковка агента следует спецификации
`AGENT_SPEC.md` (эталон — отдельный корпоративный репозиторий `agentic-repository`,
он read-only для этого проекта, изменять его запрещено).

## Структура

```text
manifest.yaml            Контракт агента (skills, секреты, runtime) — держать актуальным
core/                    Runtime-независимое поведение (сценарии, правила, маршруты)
runtimes/hermes/         Runtime-упаковка: skill-пакеты, install/verify скрипты, docs
hermes/app/              Код gateway (Discord, роутер, skills runner, телеметрия)
hermes/tests/            Тесты (pytest)
dashboard-api/           Аналитический API поверх телеметрии
dashboard-ui/            React-дашборд
```

## Ключевые конвенции

1. **Промпты — это данные.** Системные промпты живут в `runtimes/hermes/skills/<skill>/instructions*.md`
   и загружаются через `app/skills/loader.py`. Хранить промпты строковыми константами в коде запрещено.
2. **Скрипты считают, LLM рассказывает.** Парсинг, выборки, фильтрация и рендеринг OpenAPI —
   детерминированный код с тестами; LLM только оформляет готовые данные.
3. **Секреты и состояние — вне git.** `.env`, `hermes/state/`, `auth.json`, `state.db`, `sessions/`
   не коммитятся (см. `.gitignore`). В репозитории — только `*.example` с пустыми значениями.
4. **Манифест = источник правды.** При добавлении/удалении skill обновлять `manifest.yaml`
   и контрактный тест `hermes/tests/test_skill_packages.py`.
5. **Legacy-черновики.** Детальные промпты из эпохи микросервисов лежат в
   `skills/<skill>/references/draft-detailed-prompt.md` и НЕ используются рантаймом.
   Их включение — отдельное изменение поведения с проверкой качества, не рефакторинг.
6. **Изменение поведения ≠ рефакторинг.** Правки `instructions*.md` меняют поведение агента
   и оформляются отдельно от структурных изменений.

## Верификация перед коммитом

```powershell
.venv/Scripts/python -m pytest hermes/tests -q
.venv/Scripts/python -m compileall hermes dashboard-api -q
docker compose config -q
runtimes\hermes\scripts\verify-install.ps1
```

Полная ручная проверка стека — `runtimes/hermes/docs/SMOKE_TEST_PLAN.md`.

## Стиль коммитов

`type(scope): subject` — типы: `feat`, `fix`, `refactor`, `docs`, `chore`
(см. `git log --oneline`).

## Примечания для Windows

- Пути в коде и документации — прямые слеши, где возможно.
- Тесты запускать из `.venv` в корне репозитория (зависимости: `hermes/requirements.txt` + `pytest`).
