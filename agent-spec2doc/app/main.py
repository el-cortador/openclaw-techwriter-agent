from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel

from app.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from app.generator import generate_draft
from app.parser import ParserError, extract_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="agent-spec2doc", version="1.0.0")


class ProcessRequest(BaseModel):
    input: str


class ServiceResponse(BaseModel):
    result: str | None = None
    error: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/process", response_model=ServiceResponse)
def process(payload: ProcessRequest) -> ServiceResponse:
    text = payload.input.strip()
    if not text:
        return ServiceResponse(error="Текст постановки не может быть пустым")
    try:
        return ServiceResponse(result=generate_draft(text))
    except Exception as exc:
        logger.error("[process] %s", exc)
        return ServiceResponse(error=str(exc))


@app.post("/process/file", response_model=ServiceResponse)
async def process_file(file: UploadFile = File(...)) -> ServiceResponse:
    if not file.filename:
        return ServiceResponse(error="Имя файла не указано")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return ServiceResponse(error=f"Неподдерживаемый формат «{ext}». Допустимы: .pdf, .docx")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return ServiceResponse(error="Файл превышает допустимый размер 50 МБ")

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        text = extract_text(str(tmp_path))
        return ServiceResponse(result=generate_draft(text))
    except ParserError as exc:
        return ServiceResponse(error=str(exc))
    except Exception as exc:
        logger.error("[process_file] %s", exc)
        return ServiceResponse(error=str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)
