from __future__ import annotations

import logging

from fastapi import FastAPI
from pydantic import BaseModel

from app.reviewer import review

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="agent-reviewer", version="1.0.0")


class ReviewRequest(BaseModel):
    text: str
    styleguide: str | None = None


class ServiceResponse(BaseModel):
    result: str | None = None
    error: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/review", response_model=ServiceResponse)
def do_review(payload: ReviewRequest) -> ServiceResponse:
    text = payload.text.strip()
    if not text:
        return ServiceResponse(error="Текст для ревью не может быть пустым")
    try:
        return ServiceResponse(result=review(text, payload.styleguide))
    except Exception as exc:
        logger.error("[review] %s", exc)
        return ServiceResponse(error=str(exc))
