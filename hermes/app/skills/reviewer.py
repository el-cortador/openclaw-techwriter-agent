from __future__ import annotations

import logging
from pathlib import Path

from app import config
from app.skills.documents import read_document
from app.skills.llm import generate_text
from app.skills.loader import load_instructions
from app.skills.webdocs import fetch_documentation_text

logger = logging.getLogger(__name__)


def review(text: str, styleguide: str | None, source: str | None = None) -> str:
    blocks: list[str] = []
    if styleguide:
        blocks.append(f"Стайлгайд:\n{styleguide}")
    if source:
        blocks.append(f"Источник текста: {source}")
    blocks.append(f"Текст для ревью:\n{text}")
    user_message = "\n\n".join(blocks)

    logger.info(
        "[reviewer] model=%s styleguide=%s source=%s chars=%d",
        config.LLM_MODEL_NAME,
        bool(styleguide),
        source or "message",
        len(text),
    )
    result = generate_text(
        [
            {"role": "system", "content": load_instructions("doc-reviewer")},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,
        max_tokens=4096,
    )
    return _clean_markdown(result)


def review_document(path: str | Path, styleguide: str | None) -> str:
    document = Path(path)
    return review(read_document(document), styleguide, source=f"файл {document.name}")


def review_url(url: str, styleguide: str | None) -> str:
    return review(fetch_documentation_text(url), styleguide, source=url)


def _clean_markdown(text: str) -> str:
    lines = []
    for line in text.split("\n"):
        line = line.lstrip("#").lstrip()
        line = line.replace("**", "")
        line = line.replace("*", "")
        line = line.replace("_", "")
        lines.append(line)
    return "\n".join(lines)
