from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel

from app.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE, TEMP_DIR
from app.convert import convert_to_wav
from app.exceptions import ConversionError, FileValidationError, TranscriptionError
from app.postprocess import postprocess
from app.transcribe import transcribe_sync

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="agent-transcribe", version="1.0.0")


class ServiceResponse(BaseModel):
    result: str | None = None
    error: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/transcribe", response_model=ServiceResponse)
async def transcribe(file: UploadFile = File(...)) -> ServiceResponse:
    if not file.filename:
        return ServiceResponse(error="Имя файла не указано")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return ServiceResponse(
            error=f"Неподдерживаемый формат «{ext}». Допустимы: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return ServiceResponse(error=f"Файл превышает допустимый размер {MAX_FILE_SIZE // (1024 * 1024)} МБ")

    job_id = str(uuid.uuid4())
    input_path = TEMP_DIR / f"{job_id}{ext}"
    input_path.write_bytes(content)

    wav_path: Path | None = None
    try:
        wav_path = await convert_to_wav(input_path)

        raw_text = await asyncio.to_thread(transcribe_sync, wav_path)

        if not raw_text.strip():
            return ServiceResponse(result="Речь не обнаружена в файле.")

        transcript, summary = await asyncio.to_thread(postprocess, raw_text)

        result = f"## Транскрипт\n\n{transcript}"
        if summary:
            result += f"\n\n## Саммари\n\n{summary}"

        return ServiceResponse(result=result)

    except (FileValidationError, ConversionError) as exc:
        return ServiceResponse(error=str(exc))
    except TranscriptionError as exc:
        return ServiceResponse(error=str(exc))
    except Exception as exc:
        logger.error("[transcribe] %s", exc)
        return ServiceResponse(error=str(exc))
    finally:
        for p in [input_path, wav_path]:
            if p and p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass
