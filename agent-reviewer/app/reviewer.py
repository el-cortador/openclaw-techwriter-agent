from __future__ import annotations

import logging

from openai import OpenAI

from app.config import LLM_MODEL_NAME, OPENROUTER_API_KEY, SYSTEM_PROMPT_PATH

logger = logging.getLogger(__name__)


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def _clean_markdown(text: str) -> str:
    """Remove markdown formatting from response."""
    lines = []
    for line in text.split("\n"):
        # Remove ### ## # headers
        line = line.lstrip("#").lstrip()
        # Remove ** bold markers
        line = line.replace("**", "")
        # Remove * italic markers (but keep - for list items)
        line = line.replace("*", "")
        # Remove _ italic markers
        line = line.replace("_", "")
        lines.append(line)
    return "\n".join(lines)


def review(text: str, styleguide: str | None) -> str:
    client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")

    system_prompt = _load_system_prompt()

    if styleguide:
        user_message = (
            f"Стайлгайд:\n{styleguide}\n\n"
            f"Текст для ревью:\n{text}"
        )
    else:
        user_message = f"Текст для ревью:\n{text}"

    logger.info("[reviewer] model=%s styleguide=%s", LLM_MODEL_NAME, bool(styleguide))

    response = client.chat.completions.create(
        model=LLM_MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,
        max_tokens=4096,
    )

    result = response.choices[0].message.content or ""
    # Remove markdown formatting if model added it
    result = _clean_markdown(result)
    return result
