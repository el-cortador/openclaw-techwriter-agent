from __future__ import annotations

import logging

from openai import OpenAI

from app.config import LLM_MODEL_NAME, OPENROUTER_API_KEY, SYSTEM_PROMPT_PATH

logger = logging.getLogger(__name__)


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def review(text: str, styleguide: str | None) -> str:
    client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")

    system_prompt = _load_system_prompt()

    if styleguide:
        user_message = (
            f"<СТАЙЛГАЙД>\n{styleguide}\n</СТАЙЛГАЙД>\n\n"
            f"<ТЕКСТ ДЛЯ РЕВЬЮ>\n{text}\n</ТЕКСТ ДЛЯ РЕВЬЮ>"
        )
    else:
        user_message = (
            "Стайлгайд не предоставлен. Выполни базовое ревью по общим правилам технической документации.\n\n"
            f"<ТЕКСТ ДЛЯ РЕВЬЮ>\n{text}\n</ТЕКСТ ДЛЯ РЕВЬЮ>"
        )

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

    return response.choices[0].message.content or ""
