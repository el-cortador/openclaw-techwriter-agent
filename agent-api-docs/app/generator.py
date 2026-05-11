from __future__ import annotations

import logging

from openai import OpenAI

from app.config import LLM_MODEL_NAME, OPENROUTER_API_KEY, SYSTEM_PROMPT_PATH
from app.openapi_renderer import render_openapi_docs

logger = logging.getLogger(__name__)


class GenerationError(Exception):
    """Raised when the LLM response cannot be used as API documentation."""


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def generate_api_docs(input_text: str) -> str:
    rendered = render_openapi_docs(input_text)
    if rendered:
        logger.info("[generator] rendered OpenAPI spec locally chars=%d", len(rendered))
        return rendered

    client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")

    logger.info("[generator] model=%s chars=%d", LLM_MODEL_NAME, len(input_text))

    response = client.chat.completions.create(
        model=LLM_MODEL_NAME,
        messages=[
            {"role": "system", "content": _load_system_prompt()},
            {"role": "user", "content": input_text},
        ],
        temperature=0.2,
        max_tokens=4096,
    )

    choice = response.choices[0]
    content = (choice.message.content or "").strip()
    logger.info(
        "[generator] finish_reason=%s output_chars=%d",
        getattr(choice, "finish_reason", None),
        len(content),
    )
    if not content:
        raise GenerationError("LLM вернул пустой черновик API-документации")
    return content
