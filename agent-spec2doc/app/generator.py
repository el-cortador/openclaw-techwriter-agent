from __future__ import annotations

import logging

from openai import OpenAI

from app.config import LLM_MODEL_NAME, OPENROUTER_API_KEY, SYSTEM_PROMPT_PATH

logger = logging.getLogger(__name__)


class GenerationError(Exception):
    """Raised when the LLM response cannot be used as a document draft."""


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def generate_draft(extracted_text: str) -> str:
    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )

    user_message = (
        "Обработай следующую постановку аналитика и сформируй черновик технической документации "
        "согласно инструкции.\n\n"
        f"<ПОСТАНОВКА>\n{extracted_text}\n</ПОСТАНОВКА>"
    )

    logger.info("[generator] model=%s chars=%d", LLM_MODEL_NAME, len(extracted_text))

    response = client.chat.completions.create(
        model=LLM_MODEL_NAME,
        messages=[
            {"role": "system", "content": _load_system_prompt()},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        max_tokens=4096,
    )

    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise GenerationError("LLM вернул пустой черновик документации")

    return content
