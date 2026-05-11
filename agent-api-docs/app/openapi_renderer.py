from __future__ import annotations

import json
from typing import Any

import yaml


HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


def render_openapi_docs(input_text: str) -> str | None:
    spec = _load_spec(input_text)
    if not isinstance(spec, dict) or "paths" not in spec:
        return None

    paths = spec.get("paths")
    if not isinstance(paths, dict) or not paths:
        return None

    resolver = SchemaResolver(spec)
    title = _get(spec, "info", "title") or "API"
    version = _get(spec, "info", "version")
    servers = spec.get("servers") if isinstance(spec.get("servers"), list) else []

    lines = [f"# {title}"]
    if version:
        lines.extend(["", f"Версия: `{version}`"])
    if servers and isinstance(servers[0], dict) and servers[0].get("url"):
        lines.extend(["", f"Базовый URL: `{servers[0]['url']}`"])

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        path_parameters = path_item.get("parameters") if isinstance(path_item.get("parameters"), list) else []
        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            lines.extend(_render_operation(method.upper(), path, operation, path_parameters, resolver))

    result = "\n".join(lines).strip()
    return result if result != f"# {title}" else None


class SchemaResolver:
    def __init__(self, spec: dict[str, Any]) -> None:
        self._spec = spec

    def resolve(self, schema: Any) -> dict[str, Any]:
        if not isinstance(schema, dict):
            return {}
        ref = schema.get("$ref")
        if not isinstance(ref, str) or not ref.startswith("#/"):
            return schema

        current: Any = self._spec
        for part in ref[2:].split("/"):
            if not isinstance(current, dict):
                return schema
            current = current.get(part)
        if isinstance(current, dict):
            merged = dict(current)
            merged.update({k: v for k, v in schema.items() if k != "$ref"})
            return merged
        return schema


def _load_spec(input_text: str) -> Any:
    text = input_text.strip()
    if not text:
        return None
    try:
        if text.startswith("{"):
            return json.loads(text)
        return yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError):
        return None


def _render_operation(
    method: str,
    path: str,
    operation: dict[str, Any],
    path_parameters: list[Any],
    resolver: SchemaResolver,
) -> list[str]:
    summary = operation.get("summary") or operation.get("description") or f"{method} {path}"
    lines = [
        "",
        f"## {method} {path}",
        "",
        f"**Описание:** {_one_line(summary)}",
    ]

    parameters = []
    parameters.extend(param for param in path_parameters if isinstance(param, dict))
    parameters.extend(param for param in operation.get("parameters", []) if isinstance(param, dict))
    if parameters:
        lines.extend(_render_parameters(parameters, resolver))

    request_body = _render_request_body(operation.get("requestBody"), resolver)
    if request_body:
        lines.extend(request_body)

    responses = _render_responses(operation.get("responses"), resolver)
    if responses:
        lines.extend(responses)

    return lines


def _render_parameters(parameters: list[dict[str, Any]], resolver: SchemaResolver) -> list[str]:
    lines = [
        "",
        "### Параметры запроса",
        "",
        "| Параметр | Где передается | Тип | Обязательный | Описание |",
        "|---|---|---|:---:|---|",
    ]
    for param in parameters:
        schema = resolver.resolve(param.get("schema"))
        lines.append(
            "| {name} | {location} | {type} | {required} | {description} |".format(
                name=param.get("name", ""),
                location=param.get("in", ""),
                type=_schema_type(schema, resolver) or "",
                required="Да" if param.get("required") else "Нет",
                description=_one_line(param.get("description") or ""),
            )
        )
    return lines


def _render_request_body(request_body: Any, resolver: SchemaResolver) -> list[str]:
    if not isinstance(request_body, dict):
        return []

    schema = _first_content_schema(request_body.get("content"))
    if not schema:
        return []

    return [
        "",
        "### Тело запроса",
        "",
        "```json",
        json.dumps(_example_from_schema(schema, resolver), ensure_ascii=False, indent=2),
        "```",
    ]


def _render_responses(responses: Any, resolver: SchemaResolver) -> list[str]:
    if not isinstance(responses, dict) or not responses:
        return []

    lines: list[str] = []
    first_schema = None
    for response in responses.values():
        if isinstance(response, dict):
            first_schema = _first_content_schema(response.get("content"))
            if first_schema:
                break

    if first_schema:
        lines.extend(
            [
                "",
                "### Пример ответа",
                "",
                "```json",
                json.dumps(_example_from_schema(first_schema, resolver), ensure_ascii=False, indent=2),
                "```",
            ]
        )

    lines.extend(["", "### Коды ответов", "", "| Код | Описание |", "|---|---|"])
    for code, response in responses.items():
        description = response.get("description") if isinstance(response, dict) else ""
        lines.append(f"| {code} | {_one_line(description or '')} |")
    return lines


def _first_content_schema(content: Any) -> dict[str, Any] | None:
    if not isinstance(content, dict):
        return None
    for media in content.values():
        if isinstance(media, dict) and isinstance(media.get("schema"), dict):
            return media["schema"]
    return None


def _schema_type(schema: dict[str, Any], resolver: SchemaResolver) -> str:
    schema = resolver.resolve(schema)
    if not schema:
        return ""
    if "$ref" in schema:
        return schema["$ref"].split("/")[-1]
    if schema.get("type") == "array" and isinstance(schema.get("items"), dict):
        return f"array<{_schema_type(schema['items'], resolver)}>"
    return schema.get("type") or ""


def _example_from_schema(schema: dict[str, Any], resolver: SchemaResolver) -> Any:
    schema = resolver.resolve(schema)
    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    if "enum" in schema and isinstance(schema["enum"], list) and schema["enum"]:
        return schema["enum"][0]
    if "$ref" in schema:
        return f"<{schema['$ref'].split('/')[-1]}>"

    schema_type = schema.get("type")
    if schema_type == "object" or "properties" in schema:
        properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        return {name: _example_from_schema(value, resolver) for name, value in properties.items()}
    if schema_type == "array":
        items = schema.get("items") if isinstance(schema.get("items"), dict) else {}
        return [_example_from_schema(items, resolver)]
    if schema_type == "integer":
        return 0
    if schema_type == "number":
        return 0.0
    if schema_type == "boolean":
        return True
    if schema_type == "string":
        if schema.get("format") == "date-time":
            return "2026-01-01T00:00:00Z"
        if schema.get("format") == "date":
            return "2026-01-01"
        return "string"
    return {}


def _get(value: dict[str, Any], *keys: str) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _one_line(value: Any) -> str:
    return str(value).strip().replace("\n", " ") if value else ""
