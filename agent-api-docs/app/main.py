from __future__ import annotations

import logging

from fastapi import File, FastAPI, UploadFile
from pydantic import BaseModel

from app.generator import GenerationError, generate_api_docs

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
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
    except GenerationError as exc:
        return ServiceResponse(error=str(exc))
    except Exception as exc:
        logger.error("[generate] %s", exc)
        return ServiceResponse(error=str(exc))


@app.post("/generate/file", response_model=ServiceResponse)
async def generate_file(file: UploadFile = File(...)) -> ServiceResponse:
    try:
        raw = await file.read()
        text = raw.decode("utf-8-sig").strip()
    except UnicodeDecodeError:
        return ServiceResponse(error="Файл API-спецификации должен быть в UTF-8")

    if not text:
        return ServiceResponse(error="Файл API-спецификации пуст")

    try:
        return ServiceResponse(result=generate_api_docs(text))
    except GenerationError as exc:
        return ServiceResponse(error=str(exc))
    except Exception as exc:
        logger.error("[generate/file] %s", exc)
        return ServiceResponse(error=str(exc))
