---
name: api-docs
description: Route API documentation tasks to agent-api-docs. Use for OpenAPI/Swagger files, .yaml, .yml, .json API specs, REST endpoint descriptions, HTTP methods, and requests to generate API documentation.
---

# API Docs

## Текстовое описание API

Если сообщение содержит описание API, эндпоинтов, REST или HTTP-методы:

```bash
curl -s -X POST http://agent-api-docs:8005/generate \
  -H "Content-Type: application/json" \
  -d '{"input": "ТЕКСТ_СООБЩЕНИЯ"}'
```

## OpenAPI/Swagger файл

Если пользователь прислал `.yaml`, `.yml` или `.json` файл со спецификацией:

```bash
curl -s -X POST http://agent-api-docs:8005/generate/file \
  -F "file=@ПУТЬ_К_ФАЙЛУ"
```

- Не отправляй OpenAPI/Swagger-файлы в `agent-spec2doc`.
- Не составляй API-документацию самостоятельно вместо сервиса.
