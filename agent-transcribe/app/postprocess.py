from __future__ import annotations

import logging
import re

from openai import OpenAI

from app.config import LLM_MODEL_NAME, OPENROUTER_API_KEY, POSTPROCESS_CHUNK_CHARS
from app.exceptions import PostprocessError

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
Ты — профессиональный редактор транскрибаций. Улучши качество текста, полученного через распознавание речи.

Что нужно сделать:
1. Исправь ошибки распознавания (неправильные слова, искажённые термины).
2. Расставь знаки препинания.
3. Разбей текст на логические абзацы.
4. Если в тексте несколько спикеров — разметь их как «Спикер 1:», «Спикер 2:» и т.д.
5. Сохрани исходный смысл, не добавляй и не убирай информацию.

Верни только обработанный текст, без комментариев."""

_SUMMARY_PROMPT = """\
На основе транскрипта ниже составь краткое саммари: ключевые тезисы и решения, принятые в ходе разговора.
Формат: маркированный список на русском языке.

<ТРАНСКРИПТ>
{transcript}
</ТРАНСКРИПТ>"""


def _split_chunks(text: str) -> list[str]:
    if len(text) <= POSTPROCESS_CHUNK_CHARS:
        return [text]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for sent in sentences:
        if current_len + len(sent) > POSTPROCESS_CHUNK_CHARS and current:
            chunks.append(" ".join(current))
            current = [sent]
            current_len = len(sent)
        else:
            current.append(sent)
            current_len += len(sent) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


def postprocess(raw_text: str) -> tuple[str, str]:
    """Returns (cleaned_transcript, summary)."""
    client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")

    chunks = _split_chunks(raw_text)
    processed: list[str] = []

    for i, chunk in enumerate(chunks):
        logger.info("[postprocess] chunk %d/%d", i + 1, len(chunks))
        try:
            resp = client.chat.completions.create(
                model=LLM_MODEL_NAME,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": chunk},
                ],
                temperature=0.1,
                max_tokens=4096,
            )
            processed.append(resp.choices[0].message.content or chunk)
        except Exception as exc:
            logger.warning("[postprocess] chunk %d failed: %s — using raw", i + 1, exc)
            processed.append(chunk)

    transcript = "\n\n".join(processed)

    logger.info("[postprocess] generating summary")
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[{"role": "user", "content": _SUMMARY_PROMPT.format(transcript=transcript[:6000])}],
            temperature=0.2,
            max_tokens=1024,
        )
        summary = resp.choices[0].message.content or ""
    except Exception as exc:
        logger.warning("[postprocess] summary failed: %s", exc)
        summary = ""

    return transcript, summary
