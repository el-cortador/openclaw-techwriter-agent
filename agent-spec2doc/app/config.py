from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "meta-llama/llama-3.3-70b-instruct")
SYSTEM_PROMPT_PATH: Path = Path(__file__).parent.parent / "prompts" / "system_prompt.md"

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".docx"})
MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50 МБ
