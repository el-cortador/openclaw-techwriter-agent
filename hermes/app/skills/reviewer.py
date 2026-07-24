from __future__ import annotations

import logging

from app import config
from app.skills.llm import generate_text
from app.skills.loader import load_instructions

logger = logging.getLogger(__name__)


def review(text: str, styleguide: str | None) -> str:
    if styleguide:
        user_message = f"Стайлгайд:\n{styleguide}\n\nТекст для ревью:\n{text}"
    else:
        user_message = f"Текст для ревью:\n{text}"

    logger.info("[reviewer] model=%s styleguide=%s", config.LLM_MODEL_NAME, bool(styleguide))
    result = generate_text(
        [
            {"role": "system", "content": load_instructions("doc-reviewer")},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,
        max_tokens=4096,
    )
    return _clean_markdown(result)


def _clean_markdown(text: str) -> str:
    lines = []
    for line in text.split("\n"):
        line = line.lstrip("#").lstrip()
        line = line.replace("**", "")
        line = line.replace("*", "")
        line = line.replace("_", "")
        lines.append(line)
    return "\n".join(lines)
