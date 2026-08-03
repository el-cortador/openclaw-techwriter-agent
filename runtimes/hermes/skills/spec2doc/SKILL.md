---
name: spec2doc
description: >
  Генерирует черновик технической документации из постановки аналитика
  (route spec_text, spec_file: PDF, DOC, DOCX, MD) или из merge request GitLab (route spec_merge_request).
version: 1.2.0
requires:
  env: [OPENROUTER_API_KEY]
  optional_env: [GITLAB_TOKEN]
---

# spec2doc

## Продуктовый контракт

- Вход: текст постановки аналитика, файл `.pdf` / `.doc` / `.docx` / `.md` / `.markdown` / `.txt` размером до 50 МБ либо ссылка на merge request GitLab.
- Выход: Markdown-черновик документации на русском языке; первый символ ответа — `#`.
- Если данных не хватает, в текст ставится `[PLACEHOLDER: уточнить у аналитика]`; факты не выдумываются.

## Правила

1. Системные промпты загружаются только из `instructions*.md` — это единый источник правды.
2. Извлечение текста из файлов детерминировано (`hermes/app/skills/documents.py`): PDF — pdfplumber, DOCX — python-docx, DOC — разбор OLE-потока `WordDocument` через olefile (piece table), MD/TXT — чтение UTF-8 или CP1251. LLM не извлекает текст из файлов.
3. LLM получает только извлеченный текст и `instructions.md`; пустой файл или неподдерживаемый формат — явная ошибка без вызова LLM.
4. Merge request читается через GitLab API v4 (только чтение): метаданные, коммиты и диффы забираются кодом, LLM получает готовый текстовый блок.
5. `GITLAB_TOKEN` опционален для публичных проектов и обязателен для приватных — при 401/403 возвращается явная ошибка без вызова LLM.
6. Объем диффа ограничен детерминированно: до 50 файлов, до 4000 символов на файл и до 20000 символов суммарно; факт усечения передается в промпт.

## Файлы

- `instructions.md` — живой системный промпт для постановок (текст, PDF, DOC, DOCX, MD).
- `instructions-merge_request.md` — системный промпт для анализа merge request GitLab.
- `references/draft-detailed-prompt.md` — детальный legacy-промпт (черновик, не используется рантаймом).
