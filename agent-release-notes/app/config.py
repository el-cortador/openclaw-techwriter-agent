from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "meta-llama/llama-3.3-70b-instruct")

GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

JIRA_EMAIL: str = os.getenv("JIRA_EMAIL", "")
JIRA_API_TOKEN: str = os.getenv("JIRA_API_TOKEN", "")

REQUEST_TIMEOUT: float = float(os.getenv("REQUEST_TIMEOUT", "15"))
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4096"))
