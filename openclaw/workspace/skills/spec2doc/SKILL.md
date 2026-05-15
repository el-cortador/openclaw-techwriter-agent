---
name: spec2doc
description: Route product requirements, feature descriptions, text specs, PDF/DOCX files, and generic documentation drafts to agent-spec2doc. Use when the message is a text постановка, требования, описание фичи, or document generation request that is not API docs, review, release notes, transcription, or Figma.
---

# Spec To Doc

## Текстовая постановка

Если пользователь прислал текстовую постановку, требования или описание фичи:

```bash
curl -s -X POST http://agent-spec2doc:8001/process \
  -H "Content-Type: application/json" \
  -d '{"input": "ТЕКСТ_СООБЩЕНИЯ"}'
```

## PDF/DOCX

Если пользователь прислал PDF/DOCX-файл для документации:

```bash
curl -s -X POST http://agent-spec2doc:8001/process/file \
  -F "file=@ПУТЬ_К_ФАЙЛУ"
```

- Не составляй черновик технической документации самостоятельно вместо `agent-spec2doc`.
- Единственный источник результата — ответ сервиса.
- Если сервис вернул `result`, отправь его как есть.
