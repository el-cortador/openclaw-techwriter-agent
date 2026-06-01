from __future__ import annotations

from app import config


class GenerationError(Exception):
    pass


def generate_text(
    messages: list[dict],
    *,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int | None = None,
) -> str:
    if not config.OPENROUTER_API_KEY:
        raise GenerationError("OPENROUTER_API_KEY не задан.")

    from openai import OpenAI

    client = OpenAI(api_key=config.OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
    response = client.chat.completions.create(
        model=model or config.LLM_MODEL_NAME,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens or config.LLM_MAX_TOKENS,
    )
    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise GenerationError("LLM вернул пустой результат.")
    return content
