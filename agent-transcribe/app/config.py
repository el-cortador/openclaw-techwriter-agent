from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "meta-llama/llama-3.3-70b-instruct")

WHISPER_MODEL_NAME: str = os.getenv("WHISPER_MODEL_NAME", "base")
WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "auto")
FFMPEG_PATH: str = os.getenv("FFMPEG_PATH", "ffmpeg")

MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE_MB", "50")) * 1024 * 1024

TEMP_DIR: Path = Path("/tmp/agent-transcribe")
TEMP_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({
    ".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".webm",
})

POSTPROCESS_CHUNK_CHARS: int = int(os.getenv("POSTPROCESS_CHUNK_CHARS", "3000"))
