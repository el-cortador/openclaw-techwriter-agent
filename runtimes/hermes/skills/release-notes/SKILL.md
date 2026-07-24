---
name: release-notes
description: >
  Генерирует release notes или changelog на русском языке из коммитов GitHub
  (репозиторий + период) или из задач Jira (URL). Умеет сопоставлять готовые
  release notes с Jira-задачами.
version: 1.0.0
requires:
  env: [OPENROUTER_API_KEY]
  optional_env: [GITHUB_TOKEN, JIRA_EMAIL, JIRA_API_TOKEN]
---

# release-notes

## Продуктовый контракт

- Вход GitHub (route `github_release`): репозиторий `owner/repo` или URL + даты периода; опционально ветка.
- Вход Jira (route `jira_release`): один или несколько URL задач `https://<host>/browse/<KEY>`.
- Режим сопоставления: если кроме Jira URL в сообщении есть текст release notes, возвращается сопоставление пунктов с задачами.
- Выход: Markdown на русском; `release_notes` — группы «Новые возможности / Улучшения / Исправления», `changelog` — разделы Added / Changed / Fixed / Removed.
- Без источника данных (route `release_request`) — явная подсказка, что прислать, без вызова LLM.

## Правила

1. Сбор данных детерминирован: GitHub commits API (пагинация до 10 страниц), Jira issue API (summary, status, components, fixVersions; ADF → plain text). LLM никогда не вычисляет и не «угадывает» факты — только оформляет переданные данные.
2. Инструкции генерации загружаются из `instructions-release_notes.md` / `instructions-changelog.md`; инструкция сопоставления — из `instructions-mapping.md`.
3. `GITHUB_TOKEN` опционален (публичные репозитории), `JIRA_EMAIL` + `JIRA_API_TOKEN` обязательны для Jira-маршрутов — при их отсутствии явная ошибка.
4. Внешние системы используются только на чтение; агент ничего не публикует и не изменяет.

## Файлы

- `instructions-release_notes.md` — инструкция для output_type `release_notes`.
- `instructions-changelog.md` — инструкция для output_type `changelog`.
- `instructions-mapping.md` — инструкция режима сопоставления release notes ↔ Jira-задачи.
- `references/draft-detailed-prompt.md` — детальный legacy-промпт (черновик, не используется рантаймом).
