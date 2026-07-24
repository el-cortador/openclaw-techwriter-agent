---
name: figma-guide
description: >
  Генерирует руководство по интерфейсу на русском языке: по ссылке на Figma-файл
  (фильтрация JSON макета + LLM) или по скриншоту интерфейса (vision-модель).
version: 1.0.0
requires:
  env: [OPENROUTER_API_KEY]
  optional_env: [FIGMA_TOKEN]
---

# figma-guide

## Продуктовый контракт

- Вход Figma (route `figma_link` с URL): ссылка `figma.com/file|proto|design/<id>` или голый file id.
- Вход скриншот (route `figma_link` с вложением `.png`/`.jpg`/`.jpeg`/`.webp`): описание видимого экрана через vision-модель.
- Выход: Markdown-руководство на русском; для wireflow — цель сценария, последовательность экранов, переходы, развилки.

## Правила

1. Обработка макета детерминирована (`hermes/app/skills/figma.py`): извлечение file id, выбор экранов из CANVAS/FRAME, сортировка, сбор переходов из reactions, лимиты 12 экранов x 16 элементов. LLM получает только отфильтрованный JSON.
2. `FIGMA_TOKEN` опционален: публичные файлы читаются без токена; при 401/403 с токеном запрос повторяется с `X-FIGMA-TOKEN`.
3. Шаблон промпта — из `instructions.md` (плейсхолдеры `{{LANGUAGE}}`, `{{DETAIL_LEVEL}}`, `{{AUDIENCE}}`, `{{DATA}}`); промпт скриншота — из `instructions-screenshot.md`.
4. Описываются только элементы и связи из данных; скрытые функции не выдумываются.

## Файлы

- `instructions.md` — шаблон промпта для Figma JSON.
- `instructions-screenshot.md` — промпт для vision-режима по скриншоту.
