from __future__ import annotations

import asyncio
import io
import logging
import tempfile
from pathlib import Path

import discord

from app import config
from app.models import IncomingAttachment, IncomingMessage
from app.router import classify
from app.service_client import ServiceError, call_route
from app.vision import describe_ui_screenshot

logger = logging.getLogger(__name__)


class HermesDiscordClient(discord.Client):
    async def on_ready(self) -> None:
        logger.info("Hermes Discord gateway logged in as %s", self.user)

    async def on_message(self, discord_message: discord.Message) -> None:
        if discord_message.author.bot:
            return
        if not _is_allowed(discord_message):
            return

        async with discord_message.channel.typing():
            try:
                async with _DownloadedAttachments(discord_message) as attachments:
                    incoming = IncomingMessage(content=discord_message.content or "", attachments=attachments)
                    route = classify(incoming)
                    answer = await _handle_route(route, incoming)
                    await _send_answer(discord_message, answer)
            except ServiceError as exc:
                await _send_answer(discord_message, f"Ошибка сервиса: {exc}")
            except Exception as exc:
                logger.exception("Unhandled Discord message error: %s", exc)
                await _send_answer(discord_message, "Не удалось обработать запрос. Проверьте логи Hermes gateway.")


async def _handle_route(route, incoming: IncomingMessage) -> str:
    if route.kind == "unknown_short":
        return "Я на связи. Пришлите задачу или материал."
    if route.kind == "figma_link":
        if route.attachment:
            answer = await asyncio.to_thread(describe_ui_screenshot, route.attachment, incoming.content)
            logger.info("route=%s answer_chars=%d", route.kind, len(answer))
            return answer
        return (
            "Figma-ссылки сейчас не разбираю напрямую. "
            "Пришлите скриншот нужного экрана или текстовое описание интерфейса."
        )
    if route.kind == "save_styleguide":
        text = incoming.content.strip()
        if route.attachment:
            text = route.attachment.path.read_text(encoding="utf-8-sig")
        text = _strip_styleguide_prefix(text)
        if not text:
            raise ServiceError("Стильгайд пустой.")
        config.STYLEGUIDE_PATH.write_text(text, encoding="utf-8")
        return "Стайлгайд сохранен. Буду применять его при следующих ревью."
    answer = await call_route(route, incoming)
    logger.info("route=%s answer_chars=%d", route.kind, len(answer))
    return answer


def _strip_styleguide_prefix(text: str) -> str:
    for marker in ("стайлгайд:", "styleguide:", "это стайлгайд"):
        index = text.lower().find(marker)
        if index >= 0:
            return text[index + len(marker):].strip()
    return text.strip()


def _is_allowed(message: discord.Message) -> bool:
    if config.DISCORD_ALLOWED_USER_IDS and message.author.id not in config.DISCORD_ALLOWED_USER_IDS:
        return False
    if config.DISCORD_ALLOWED_CHANNEL_IDS and message.channel.id not in config.DISCORD_ALLOWED_CHANNEL_IDS:
        return False
    if config.DISCORD_ALLOWED_GUILD_IDS:
        if message.guild is None or message.guild.id not in config.DISCORD_ALLOWED_GUILD_IDS:
            return False
    return True


async def _send_answer(message: discord.Message, answer: str) -> None:
    if len(answer) <= 1200:
        await message.reply(answer, mention_author=False)
        return

    payload = io.BytesIO(answer.encode("utf-8"))
    file = discord.File(payload, filename="result.md")
    await message.reply("Готово. Полный результат приложен файлом `result.md`.", file=file, mention_author=False)


class _DownloadedAttachments:
    def __init__(self, message: discord.Message) -> None:
        self.message = message
        self._tmpdir: tempfile.TemporaryDirectory[str] | None = None
        self.attachments: list[IncomingAttachment] = []

    async def __aenter__(self) -> list[IncomingAttachment]:
        if not self.message.attachments:
            return []

        self._tmpdir = tempfile.TemporaryDirectory()
        base = Path(self._tmpdir.name)
        for attachment in self.message.attachments:
            path = base / _safe_filename(attachment.filename)
            await attachment.save(path)
            self.attachments.append(
                IncomingAttachment(
                    filename=attachment.filename,
                    content_type=attachment.content_type,
                    path=path,
                )
            )
        return self.attachments

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._tmpdir:
            await asyncio.to_thread(self._tmpdir.cleanup)


def _safe_filename(filename: str) -> str:
    cleaned = Path(filename).name.strip()
    return cleaned or "attachment"
