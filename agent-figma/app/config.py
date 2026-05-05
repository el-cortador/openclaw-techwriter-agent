from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

FIGMA_API_BASE: str = os.getenv("FIGMA_API_BASE", "https://api.figma.com/v1")
FIGMA_API_TOKEN: str = os.getenv("FIGMA_TOKEN", "")
REQUEST_TIMEOUT: float = float(os.getenv("REQUEST_TIMEOUT", "15"))

OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "meta-llama/llama-3.3-70b-instruct")
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))
