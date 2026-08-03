from __future__ import annotations

import asyncio
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app import config
from app.models import IncomingMessage, Route
from app.skills import api_docs, figma, release_notes, reviewer, spec2doc


REVIEW_ROUTE_KINDS = frozenset({"review", "review_file", "review_url"})


class SkillError(Exception):
    pass


@dataclass(frozen=True)
class SkillContext:
    route: Route
    message: IncomingMessage
    styleguide: str | None = None


class Skill(Protocol):
    name: str
    route_kinds: frozenset[str]

    async def run(self, context: SkillContext) -> str:
        ...


class Spec2DocSkill:
    name = "spec2doc"
    route_kinds = frozenset({"spec_text", "spec_file", "spec_merge_request"})

    async def run(self, context: SkillContext) -> str:
        route = context.route
        if route.kind == "spec_text":
            text = context.message.content.strip()
            if not text:
                raise SkillError("Текст постановки не может быть пустым")
            return await asyncio.to_thread(spec2doc.generate_draft, text)
        if route.kind == "spec_file" and route.attachment:
            return await asyncio.to_thread(spec2doc.generate_draft_from_file, route.attachment.path)
        if route.kind == "spec_merge_request" and route.urls:
            return await asyncio.to_thread(
                spec2doc.generate_draft_from_merge_request,
                route.urls[0],
                _strip_urls(context.message.content, route.urls),
            )
        raise SkillError("Маршрут spec2doc не содержит входных данных.")


class ApiDocsSkill:
    name = "api_docs"
    route_kinds = frozenset({"api_docs_text", "api_docs_file"})

    async def run(self, context: SkillContext) -> str:
        route = context.route
        if route.kind == "api_docs_text":
            text = context.message.content.strip()
        elif route.kind == "api_docs_file" and route.attachment:
            text = _read_utf8(route.attachment.path, "Файл API-спецификации должен быть в UTF-8").strip()
        else:
            raise SkillError("Маршрут api-docs не содержит входных данных.")
        if not text:
            raise SkillError("Описание API не может быть пустым")
        return await asyncio.to_thread(api_docs.generate_api_docs, text)


class ReviewerSkill:
    name = "reviewer"
    route_kinds = frozenset({"review", "review_file", "review_url"})

    async def run(self, context: SkillContext) -> str:
        route = context.route
        if route.kind == "review_file" and route.attachment:
            return await asyncio.to_thread(
                reviewer.review_document,
                route.attachment.path,
                context.styleguide,
            )
        if route.kind == "review_url" and route.urls:
            return await asyncio.to_thread(reviewer.review_url, route.urls[0], context.styleguide)
        text = context.message.content.strip()
        if not text:
            raise SkillError("Текст для ревью не может быть пустым")
        return await asyncio.to_thread(reviewer.review, text, context.styleguide)


class ReleaseNotesSkill:
    name = "release_notes"
    route_kinds = frozenset({"github_release", "jira_release", "release_request"})

    async def run(self, context: SkillContext) -> str:
        route = context.route
        if route.kind == "github_release" and route.urls:
            payload = _github_payload(context.message.content, route.urls[0], route.output_type)
            return await asyncio.to_thread(release_notes.generate_github, **payload)
        if route.kind == "jira_release":
            return await asyncio.to_thread(
                release_notes.generate_jira,
                urls=route.urls or [],
                output_type=route.output_type,
                release_notes_text=_strip_urls(context.message.content, route.urls or []),
            )
        if route.kind == "release_request":
            if route.output_type == "changelog":
                raise SkillError(
                    "Запрос распознан как changelog, но не хватает источника данных. "
                    "Пришлите ссылку на GitHub-репозиторий и даты или Jira URL задач."
                )
            raise SkillError(
                "Запрос распознан как release notes, но не хватает источника данных. "
                "Пришлите Jira URL задач или ссылку на GitHub-репозиторий с датами."
            )
        raise SkillError("Маршрут release-notes не содержит входных данных.")


class FigmaSkill:
    name = "figma"
    route_kinds = frozenset({"figma_link"})

    async def run(self, context: SkillContext) -> str:
        route = context.route
        if not route.urls:
            raise SkillError("Укажите Figma URL.")
        return await asyncio.to_thread(
            figma.generate_guide,
            figma_url=route.urls[0],
            language="ru",
            detail_level="brief",
            audience="user",
        )


_SKILLS: tuple[Skill, ...] = (
    Spec2DocSkill(),
    ApiDocsSkill(),
    ReviewerSkill(),
    ReleaseNotesSkill(),
    FigmaSkill(),
)
SKILLS_BY_ROUTE: dict[str, Skill] = {
    route_kind: skill
    for skill in _SKILLS
    for route_kind in skill.route_kinds
}


async def run_route(route: Route, message: IncomingMessage) -> str:
    styleguide = None
    if route.kind in REVIEW_ROUTE_KINDS and config.STYLEGUIDE_PATH.exists():
        styleguide = config.STYLEGUIDE_PATH.read_text(encoding="utf-8")

    skill = SKILLS_BY_ROUTE.get(route.kind)
    if not skill:
        raise SkillError("Маршрут пока не поддержан.")

    try:
        result = await skill.run(SkillContext(route=route, message=message, styleguide=styleguide))
    except SkillError:
        raise
    except Exception as exc:
        raise SkillError(str(exc)) from exc
    return _clean_result(result)


def _read_utf8(path: Path, error_message: str) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SkillError(error_message) from exc


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


def _strip_urls(text: str, urls: list[str]) -> str:
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
