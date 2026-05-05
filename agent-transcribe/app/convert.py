from __future__ import annotations

import asyncio
import logging
import subprocess
from pathlib import Path

from app.config import FFMPEG_PATH
from app.exceptions import ConversionError

logger = logging.getLogger(__name__)


async def convert_to_wav(input_path: Path) -> Path:
    output_path = input_path.with_suffix(".wav")

    cmd = [
        FFMPEG_PATH,
        "-fflags", "+discardcorrupt",
        "-i", str(input_path),
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        "-y",
        str(output_path),
    ]

    def _run() -> Path:
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=600)
        except subprocess.TimeoutExpired:
            raise ConversionError("Превышено время конвертации файла")

        wav_ok = output_path.exists() and output_path.stat().st_size > 0
        if result.returncode != 0:
            if wav_ok:
                logger.warning("[convert] ffmpeg завершился с кодом %d, но WAV создан", result.returncode)
            else:
                err = result.stderr.decode("utf-8", errors="replace").strip()
                raise ConversionError(f"Ошибка конвертации (код {result.returncode}): {err[-300:]}")
        logger.info("[convert] OK → %s", output_path.name)
        return output_path

    return await asyncio.to_thread(_run)
