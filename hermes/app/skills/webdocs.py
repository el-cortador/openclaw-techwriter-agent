from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from urllib.parse import urlparse

import requests

from app import config

logger = logging.getLogger(__name__)

MAX_PAGE_BYTES = 5 * 1024 * 1024
MAX_TEXT_CHARS = 40000

_SKIP_TAGS = frozenset(
    {
        "script",
        "style",
        "noscript",
        "svg",
        "iframe",
        "template",
        "nav",
        "header",
        "footer",
        "aside",
        "form",
        "button",
        "select",
    }
)
_BLOCK_TAGS = frozenset(
    {
        "p", "div", "section", "article", "main", "br", "hr", "pre", "blockquote",
        "h1", "h2", "h3", "h4", "h5", "h6",
        "ul", "ol", "li", "dl", "dt", "dd",
        "table", "thead", "tbody", "tr", "td", "th",
        "figure", "figcaption", "details", "summary",
    }
)
_MAIN_TAGS = frozenset({"main", "article"})
_VOID_TAGS = frozenset({"br", "hr", "img", "input", "meta", "link", "source", "col", "area", "embed"})


class WebDocsError(Exception):
    pass


def fetch_documentation_text(url: str) -> str:
    """Скачивает страницу документации и возвращает извлеченный текст без разметки."""
    normalized = _normalize_url(url)
    try:
        response = requests.get(
            normalized,
            headers={"User-Agent": "hermes-doc-reviewer/1.0", "Accept": "text/html,text/plain,*/*"},
            timeout=config.REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise WebDocsError(f"Не удалось загрузить страницу документации: {exc}") from exc

    if response.status_code in (401, 403):
        raise WebDocsError("Страница закрыта авторизацией (401/403), текст недоступен.")
    if response.status_code == 404:
        raise WebDocsError("Страница документации не найдена (404).")
    if response.status_code >= 400:
        raise WebDocsError(f"Сайт документации вернул ошибку {response.status_code}")

    content = response.content
    if len(content) > MAX_PAGE_BYTES:
        raise WebDocsError("Страница превышает допустимый размер 5 МБ")

    content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    text = _to_text(content, content_type, normalized, response.encoding)
    if not text.strip():
        raise WebDocsError(
            "На странице не найден текст. Возможно, документация рендерится скриптом — "
            "пришлите текст или файл."
        )
    logger.info("[webdocs] url=%s content_type=%s chars=%d", normalized, content_type, len(text))
    return text


def _to_text(content: bytes, content_type: str, url: str, encoding: str | None) -> str:
    if content_type == "application/pdf" or url.lower().split("?")[0].endswith(".pdf"):
        raise WebDocsError(
            "По ссылке PDF-файл. Скачайте его и пришлите вложением — PDF разбирается парсером файлов."
        )
    raw = content.decode(encoding or "utf-8", errors="replace") if encoding else content.decode("utf-8", errors="replace")
    if content_type.startswith("text/html") or content_type in ("application/xhtml+xml", ""):
        text = html_to_text(raw)
    else:
        text = _normalize_lines(raw)
    return text[:MAX_TEXT_CHARS]


def _normalize_url(url: str) -> str:
    normalized = url.strip().rstrip(".,);")
    parsed = urlparse(normalized)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise WebDocsError("Ожидается ссылка вида https://docs.example.com/page")
    return normalized


class _HtmlTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_stack: list[str] = []
        self._main_depth = 0
        self._title_parts: list[str] = []
        self._in_title = False
        self.chunks: list[tuple[bool, str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag in _SKIP_TAGS or _is_hidden(attrs):
            if tag not in _VOID_TAGS:
                self._skip_stack.append(tag)
            return
        if self._skip_stack:
            return
        if tag == "title":
            self._in_title = True
        if tag in _MAIN_TAGS:
            self._main_depth += 1
        if tag in _BLOCK_TAGS:
            self.chunks.append((self._main_depth > 0, "\n"))

    def handle_endtag(self, tag: str) -> None:
        if self._skip_stack and self._skip_stack[-1] == tag:
            self._skip_stack.pop()
            return
        if self._skip_stack:
            return
        if tag == "title":
            self._in_title = False
        if tag in _MAIN_TAGS and self._main_depth > 0:
            self._main_depth -= 1
        if tag in _BLOCK_TAGS:
            self.chunks.append((self._main_depth > 0, "\n"))

    def handle_data(self, data: str) -> None:
        if self._skip_stack or not data.strip():
            return
        if self._in_title:
            self._title_parts.append(data.strip())
            return
        self.chunks.append((self._main_depth > 0, data))

    @property
    def title(self) -> str:
        return " ".join(self._title_parts).strip()


def _is_hidden(attrs) -> bool:  # noqa: ANN001
    for name, value in attrs:
        lowered = (value or "").lower()
        if name == "hidden":
            return True
        if name == "aria-hidden" and lowered == "true":
            return True
        if name == "style" and "display:none" in lowered.replace(" ", ""):
            return True
    return False


def html_to_text(html: str) -> str:
    parser = _HtmlTextParser()
    parser.feed(html)
    parser.close()

    main_chunks = [text for in_main, text in parser.chunks if in_main]
    body = "".join(main_chunks) if any(chunk.strip() for chunk in main_chunks) else "".join(
        text for _, text in parser.chunks
    )
    text = _normalize_lines(body)
    if parser.title and parser.title not in text.split("\n")[:3]:
        text = f"{parser.title}\n\n{text}"
    return text


def _normalize_lines(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
