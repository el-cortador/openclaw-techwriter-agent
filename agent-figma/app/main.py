from __future__ import annotations

import logging
from typing import Generator

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from app.figma import (
    FigmaAuthError,
    FigmaBadUrlError,
    FigmaClient,
    FigmaNotFoundError,
    FigmaRateLimitError,
    FigmaRequestError,
    extract_file_id,
)
from app.filtering import filter_figma_json
from app.generation import build_prompt, parse_llm_output
from app.llm import LLMClient, LLMRequestError
from app.config import FIGMA_API_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="agent-figma", version="1.0.0")


class GuideRequest(BaseModel):
    figma_url: str
    figma_token: str = ""
    language: str = "ru"
    detail_level: str = "brief"
    audience: str = "user"


class ServiceResponse(BaseModel):
    result: str | None = None
    error: str | None = None


def get_figma_client() -> Generator[FigmaClient, None, None]:
    client = FigmaClient()
    try:
        yield client
    finally:
        client.close()


def get_llm_client() -> Generator[LLMClient, None, None]:
    client = LLMClient()
    try:
        yield client
    finally:
        client.close()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/guide/generate", response_model=ServiceResponse)
def generate_guide(
    payload: GuideRequest,
    figma: FigmaClient = Depends(get_figma_client),
    llm: LLMClient = Depends(get_llm_client),
) -> ServiceResponse:
    try:
        token = payload.figma_token or FIGMA_API_TOKEN
        file_id = extract_file_id(payload.figma_url)
        data = figma.get_file(file_id, token)
        filtered = filter_figma_json(data)
        prompt = build_prompt(
            filtered,
            language=payload.language,
            detail_level=payload.detail_level,
            audience=payload.audience,
        )
        output = llm.generate(prompt)
        markdown, _ = parse_llm_output(output)
        return ServiceResponse(result=markdown)

    except FigmaBadUrlError as exc:
        return ServiceResponse(error=f"Некорректная Figma-ссылка: {exc}")
    except FigmaAuthError as exc:
        return ServiceResponse(error=f"Ошибка авторизации Figma: {exc}")
    except FigmaNotFoundError as exc:
        return ServiceResponse(error=f"Figma-файл не найден: {exc}")
    except FigmaRateLimitError as exc:
        return ServiceResponse(error=f"Превышен лимит запросов Figma: {exc}")
    except FigmaRequestError as exc:
        return ServiceResponse(error=f"Ошибка Figma API: {exc}")
    except LLMRequestError as exc:
        return ServiceResponse(error=f"Ошибка LLM: {exc}")
    except Exception as exc:
        logger.error("[guide/generate] %s", exc)
        return ServiceResponse(error=str(exc))
