from __future__ import annotations

import logging

import discord

from app.config import DISCORD_BOT_TOKEN
from app.discord_bot import HermesDiscordClient


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    if not DISCORD_BOT_TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set")

    intents = discord.Intents.default()
    intents.message_content = True

    client = HermesDiscordClient(intents=intents)
    client.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()
