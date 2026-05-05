from __future__ import annotations

import logging

from openai import OpenAI

from app.config import LLM_MAX_TOKENS, LLM_MODEL_NAME, LLM_TEMPERATURE, OPENROUTER_API_KEY

logger = logging.getLogger(__name__)


class LLMError(Exception):
    pass


class LLMRequestError(LLMError):
    pass


class LLMClient:
    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )

    def generate(self, prompt: str) -> str:
        logger.info("[llm] model=%s", LLM_MODEL_NAME)
        try:
            response = self._client.chat.completions.create(
                model=LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            raise LLMRequestError(f"OpenRouter error: {exc}") from exc

    def close(self) -> None:
        pass
