from __future__ import annotations

import logging
import time
from pathlib import Path

from app.config import WHISPER_DEVICE, WHISPER_MODEL_NAME
from app.exceptions import TranscriptionError

logger = logging.getLogger(__name__)

_model = None


def _load_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        import torch

        device = WHISPER_DEVICE
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        compute_type = "float16" if device == "cuda" else "int8"
        logger.info("[transcribe] loading model=%s device=%s compute=%s", WHISPER_MODEL_NAME, device, compute_type)
        _model = WhisperModel(WHISPER_MODEL_NAME, device=device, compute_type=compute_type)
        logger.info("[transcribe] model loaded")
    return _model


def transcribe_sync(wav_path: Path) -> str:
    if not wav_path.exists():
        raise TranscriptionError(f"Файл не найден: {wav_path}")

    try:
        model = _load_model()
        segments, _ = model.transcribe(
            str(wav_path),
            language="ru",
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        texts = [seg.text for seg in segments]
        result = " ".join(texts).strip()
        logger.info("[transcribe] done chars=%d", len(result))
        return result
    except TranscriptionError:
        raise
    except Exception as exc:
        raise TranscriptionError(f"Ошибка транскрибации: {exc}") from exc
