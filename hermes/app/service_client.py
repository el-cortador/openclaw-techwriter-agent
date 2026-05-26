from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import httpx

from app import config
from app.models import IncomingMessage, Route


class ServiceError(Exception):
    pass


async def call_route(route: Route, message: IncomingMessage) -> str:
    async with httpx.AsyncClient() as client:
        if route.kind == "spec_text":
            return await _post_json(client, f"{config.SPEC2DOC_URL}/process", {"input": message.content}, timeout=600)
        if route.kind == "spec_file":
            return await _post_file(client, f"{config.SPEC2DOC_URL}/process/file", route.attachment.path, timeout=600)
        if route.kind == "api_docs_text":
            return await _post_json(client, f"{config.API_DOCS_URL}/generate", {"input": message.content}, timeout=600)
        if route.kind == "api_docs_file":
            return await _post_file(client, f"{config.API_DOCS_URL}/generate/file", route.attachment.path, timeout=600)
        if route.kind == "figma_link":
            return await _post_json(
                client,
                f"{config.FIGMA_URL}/guide/generate",
                {
                    "figma_url": route.urls[0],
                    "language": "ru",
                    "detail_level": "brief",
                    "audience": "user",
                },
                timeout=600,
            )
        if route.kind == "transcribe_file":
            return await _post_file(client, f"{config.TRANSCRIBE_URL}/transcribe", route.attachment.path, timeout=900)
        if route.kind == "transcribe_url":
            return await _post_json(client, f"{config.TRANSCRIBE_URL}/transcribe/url", {"url": route.urls[0]}, timeout=900)
        if route.kind == "jira_release":
            payload = {
                "urls": route.urls or [],
                "output_type": route.output_type,
                "release_notes_text": _release_notes_context(message.content, route.urls or []),
            }
            return await _post_json(client, f"{config.RELEASE_NOTES_URL}/generate-jira", payload, timeout=600)
        if route.kind == "github_release":
            payload = _github_payload(message.content, route.urls[0], route.output_type)
            return await _post_json(client, f"{config.RELEASE_NOTES_URL}/generate", payload, timeout=600)
        if route.kind == "review":
            styleguide = config.STYLEGUIDE_PATH.read_text(encoding="utf-8") if config.STYLEGUIDE_PATH.exists() else None
            return await _post_json(client, f"{config.REVIEWER_URL}/review", {"text": message.content, "styleguide": styleguide}, timeout=600)

    raise ServiceError("Маршрут пока не поддержан.")


async def _post_json(client: httpx.AsyncClient, url: str, payload: dict, timeout: float = 120) -> str:
    try:
        response = await client.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        return _extract_service_result(response)
    except httpx.TimeoutException as exc:
        raise ServiceError(f"Сервис не успел ответить за {timeout:.0f} секунд.") from exc
    except httpx.HTTPError as exc:
        raise ServiceError(f"Сервис временно недоступен: {exc}") from exc


async def _post_file(client: httpx.AsyncClient, url: str, path: Path, timeout: float = 120) -> str:
    try:
        with path.open("rb") as file_obj:
            files = {"file": (path.name, file_obj)}
            response = await client.post(url, files=files, timeout=timeout)
        response.raise_for_status()
        return _extract_service_result(response)
    except httpx.TimeoutException as exc:
        raise ServiceError(f"Сервис не успел ответить за {timeout:.0f} секунд.") from exc
    except httpx.HTTPError as exc:
        raise ServiceError(f"Сервис временно недоступен: {exc}") from exc


def _extract_service_result(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError as exc:
        raise ServiceError("Сервис вернул некорректный JSON.") from exc

    result = data.get("result")
    error = data.get("error")
    if result:
        return _clean_result(str(result))
    if error:
        raise ServiceError(str(error))
    raise ServiceError("Сервис вернул пустой результат. Повторите запрос или отправьте исходные материалы еще раз.")


def _github_payload(text: str, repository: str, output_type: str) -> dict:
    dates = re.findall(r"\b(?:\d{2}[.-]\d{2}[.-]\d{4}|\d{4}-\d{2}-\d{2})\b", text)
    date_from = _normalize_date(dates[0]) if dates else ""
    date_to = _normalize_date(dates[1]) if len(dates) > 1 else date_from
    return {
        "repository": repository,
        "date_from": date_from,
        "date_to": date_to,
        "branch": "",
        "output_type": output_type,
    }


def _normalize_date(value: str) -> str:
    if "-" in value and len(value.split("-")[0]) == 4:
        return value
    return value.replace(".", "-")


def _release_notes_context(text: str, urls: list[str]) -> str:
    cleaned = text
    for url in urls:
        cleaned = cleaned.replace(url, "")
    return cleaned.strip()


def _clean_result(text: str) -> str:
    allowed = {"\n", "\r", "\t"}
    return "".join(
        char
        for char in text
        if char in allowed or not unicodedata.category(char).startswith("C")
    ).strip()
