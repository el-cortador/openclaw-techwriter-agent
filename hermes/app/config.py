from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _csv_ints(name: str) -> set[int]:
    raw = os.getenv(name, "")
    values: set[int] = set()
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        values.add(int(item))
    return values


DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_ALLOWED_GUILD_IDS: set[int] = _csv_ints("DISCORD_ALLOWED_GUILD_IDS")
DISCORD_ALLOWED_CHANNEL_IDS: set[int] = _csv_ints("DISCORD_ALLOWED_CHANNEL_IDS")
DISCORD_ALLOWED_USER_IDS: set[int] = _csv_ints("DISCORD_ALLOWED_USER_IDS")

OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
HERMES_VISION_MODEL: str = os.getenv("HERMES_VISION_MODEL", "google/gemini-2.5-flash")

STATE_DIR: Path = Path(os.getenv("HERMES_STATE_DIR", "/app/state"))
STATE_DIR.mkdir(parents=True, exist_ok=True)
STYLEGUIDE_PATH: Path = STATE_DIR / "styleguide.md"

SPEC2DOC_URL: str = os.getenv("AGENT_SPEC2DOC_URL", "http://agent-spec2doc:8001")
FIGMA_URL: str = os.getenv("AGENT_FIGMA_URL", "http://agent-figma:8002")
RELEASE_NOTES_URL: str = os.getenv("AGENT_RELEASE_NOTES_URL", "http://agent-release-notes:8004")
API_DOCS_URL: str = os.getenv("AGENT_API_DOCS_URL", "http://agent-api-docs:8005")
REVIEWER_URL: str = os.getenv("AGENT_REVIEWER_URL", "http://agent-reviewer:8006")
