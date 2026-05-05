from __future__ import annotations

import logging

from fastapi import FastAPI
from pydantic import BaseModel

from app.generator import generate_api_docs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="agent-api-docs", version="1.0.0")


class GenerateRequest(BaseModel):
    input: str


class ServiceResponse(BaseModel):
    result: str | None = None
    error: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/generate", response_model=ServiceResponse)
def generate(payload: GenerateRequest) -> ServiceResponse:
    text = payload.input.strip()
    if not text:
        return ServiceResponse(error="Описание API не может быть пустым")
    try:
        return ServiceResponse(result=generate_api_docs(text))
    except Exception as exc:
        logger.error("[generate] %s", exc)
        return ServiceResponse(error=str(exc))
