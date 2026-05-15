---
name: styleguide-review
description: Manage styleguide memory and route review requests to agent-reviewer. Use for messages containing это стайлгайд, стайлгайд:, Markdown styleguide files, проверь, ревью, review, проверка, and text review tasks.
---

# Styleguide And Review

## Сохранение стайлгайда

Если пользователь пишет `это стайлгайд` или `стайлгайд: ...`:

1. Извлеки текст стайлгайда из сообщения.
2. Сохрани его в `styleguide.md` в workspace.
3. Ответь: `Стайлгайд сохранён. Буду применять его при следующих ревью.`

Если пользователь прислал Markdown-файл со стайлгайдом, скопируй его в `styleguide.md`.

## Ревью текста

Если сообщение содержит `проверь`, `ревью`, `review`, `проверка` и это не сохранение стайлгайда:

1. Прочитай `styleguide.md`, если файл существует.
2. Передай содержимое в поле `styleguide`.
3. Если файла нет, передай `null`.

```bash
curl -s -X POST http://agent-reviewer:8006/review \
  -H "Content-Type: application/json" \
  -d '{"text": "ТЕКСТ_СООБЩЕНИЯ", "styleguide": null}'
```

- Не переписывай результат ревью самостоятельно.
- Если сервис вернул `result`, отправь его как есть.
