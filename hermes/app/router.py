from __future__ import annotations

import re
import unicodedata

from app.models import IncomingAttachment, IncomingMessage, Route

API_EXTENSIONS = {".yaml", ".yml", ".json"}
SPEC_EXTENSIONS = {".pdf", ".docx"}
MEDIA_EXTENSIONS = {".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".webm"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

JIRA_RE = re.compile(r"https?://[^\s<>()]+/browse/[A-Z][A-Z0-9]+-\d+", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)
GITHUB_RE = re.compile(r"(?:https?://)?github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", re.IGNORECASE)
DATE_RE = re.compile(r"\b(?:\d{2}[.-]\d{2}[.-]\d{4}|\d{4}-\d{2}-\d{2})\b")


def classify(message: IncomingMessage) -> Route:
    text = message.content.strip()
    lower = text.lower()
    attachment = message.attachments[0] if message.attachments else None
    short_text = _short_text(lower)

    if _is_styleguide_save(lower):
        return Route("save_styleguide", attachment=attachment)

    if not attachment and _is_short_ping(short_text):
        return Route("unknown_short")

    if attachment:
        file_route = _classify_attachment(attachment, lower)
        if file_route:
            return file_route

    jira_urls = JIRA_RE.findall(text)
    if jira_urls:
        return Route("jira_release", urls=jira_urls, output_type=_output_type(lower))

    urls = URL_RE.findall(text)
    media_url = _find_media_url(urls, lower)
    if media_url:
        return Route("transcribe_url", urls=[media_url])

    if "figma.com/" in lower:
        figma_url = next((url for url in urls if "figma.com/" in url.lower()), None)
        return Route("figma_link", urls=[figma_url] if figma_url else None)

    if GITHUB_RE.search(text) and DATE_RE.search(text):
        return Route("github_release", urls=[GITHUB_RE.search(text).group(0)], output_type=_output_type(lower))

    if _looks_like_api(lower):
        return Route("api_docs_text")

    if _looks_like_review(lower):
        return Route("review")

    return Route("spec_text")


def _classify_attachment(attachment: IncomingAttachment, lower: str) -> Route | None:
    suffix = attachment.suffix
    content_type = (attachment.content_type or "").lower()

    if suffix in API_EXTENSIONS:
        return Route("api_docs_file", attachment=attachment)
    if suffix in MEDIA_EXTENSIONS or content_type.startswith(("audio/", "video/")):
        return Route("transcribe_file", attachment=attachment)
    if suffix in SPEC_EXTENSIONS:
        return Route("spec_file", attachment=attachment)
    if suffix == ".md" and "стайлгайд" in lower:
        return Route("save_styleguide", attachment=attachment)
    if suffix in IMAGE_EXTENSIONS or content_type.startswith("image/"):
        return Route("figma_link", attachment=attachment)
    return None


def _is_styleguide_save(lower: str) -> bool:
    return (
        "это стайлгайд" in lower
        or "стайлгайд:" in lower
        or "styleguide:" in lower
        or "this is a style guide" in lower
    )


def _looks_like_api(lower: str) -> bool:
    api_words = ("openapi", "swagger", "endpoint", "endpoints", "rest", "api", "апи", "эндпоинт")
    http_methods = ("get /", "post /", "put /", "patch /", "delete /")
    return any(word in lower for word in api_words) or any(method in lower for method in http_methods)


def _looks_like_review(lower: str) -> bool:
    return any(word in lower for word in ("review", "ревью", "проверь", "проверка", "проверить"))


def _is_short_ping(cleaned: str) -> bool:
    if cleaned in {"", "?", "привет", "hello", "hi", "ты тут", "на связи", "ping"}:
        return True
    if len(cleaned) <= 24 and not any(char.isspace() for char in cleaned):
        return True
    return False


def _short_text(lower: str) -> str:
    value = re.sub(r"<@!?\d+>", "", lower)
    value = "".join(char for char in value if unicodedata.category(char) != "Cf")
    value = value.strip()
    value = value.strip(" \t\r\n?!.。,，:;\"'`")
    return re.sub(r"\s+", " ", value)


def _output_type(lower: str) -> str:
    if "changelog" in lower or "change log" in lower or "журнал изменений" in lower:
        return "changelog"
    return "release_notes"


def _find_media_url(urls: list[str], lower: str) -> str | None:
    media_words = ("audio", "video", "mp3", "mp4", "wav", "m4a", "ogg", "webm", "аудио", "видео", "расшифр")
    for url in urls:
        if any(url.lower().split("?")[0].endswith(ext) for ext in MEDIA_EXTENSIONS):
            return url
    if urls and any(word in lower for word in media_words):
        return urls[0]
    return None
