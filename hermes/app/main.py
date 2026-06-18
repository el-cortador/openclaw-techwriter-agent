from __future__ import annotations

import discord

from app import telemetry
from app.config import DATABASE_URL, DISCORD_BOT_TOKEN, LOG_LEVEL
from app.discord_bot import HermesDiscordClient
from app.logging_setup import configure_logging


def main() -> None:
    configure_logging(LOG_LEVEL)
    if not DISCORD_BOT_TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set")
    if DATABASE_URL:
        telemetry.initialize()

    intents = discord.Intents.default()
    intents.message_content = True

    client = HermesDiscordClient(intents=intents)
    client.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()
