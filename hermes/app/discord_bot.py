from __future__ import annotations

import asyncio
import io
import logging
import re
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import discord

from app import config, telemetry
from app.models import IncomingAttachment, IncomingMessage
from app.router import classify
from app.service_client import ServiceError, call_route
from app.styleguide import extract_styleguide_text
from app.telemetry_context import reset_current_run_id, set_current_run_id
from app.vision import describe_ui_screenshot

logger = logging.getLogger(__name__)


class HermesDiscordClient(discord.Client):
    async def on_ready(self) -> None:
        logger.info("Hermes Discord gateway logged in as %s", self.user, extra={"service": "hermes-discord"})

    async def on_message(self, discord_message: discord.Message) -> None:
        if discord_message.author.bot:
            return
        if not _is_allowed(discord_message):
            return

        async with discord_message.channel.typing():
            telemetry_state: _TelemetryState | None = None
            token = None
            try:
                async with _DownloadedAttachments(discord_message) as attachments:
                    incoming = IncomingMessage(content=discord_message.content or "", attachments=attachments)
                    route = classify(incoming)
                    telemetry_state = await asyncio.to_thread(_start_telemetry, discord_message, incoming, route.kind)
                    if telemetry_state:
                        token = set_current_run_id(telemetry_state.run_id)
                    answer = await _handle_route(route, incoming)
                    if telemetry_state:
                        await asyncio.to_thread(_complete_telemetry_success, telemetry_state, answer)
                    await _send_answer(discord_message, answer, _result_filename(route, incoming))
            except ServiceError as exc:
                if telemetry_state:
                    await asyncio.to_thread(_complete_telemetry_failure, telemetry_state, str(exc))
                await _send_answer(discord_message, f"Ошибка сервиса: {exc}")
            except Exception as exc:
                logger.exception("Unhandled Discord message error: %s", exc, extra={"service": "hermes-discord"})
                if telemetry_state:
                    await asyncio.to_thread(_complete_telemetry_failure, telemetry_state, str(exc))
                await _send_answer(discord_message, "Не удалось обработать запрос. Проверьте логи Hermes gateway.")
            finally:
                if token is not None:
                    reset_current_run_id(token)


async def _handle_route(route, incoming: IncomingMessage) -> str:
    if route.kind == "unknown_short":
        return "Я на связи. Пришлите задачу или материал."
    if route.kind == "figma_link" and route.attachment:
        answer = await asyncio.to_thread(describe_ui_screenshot, route.attachment, incoming.content)
        logger.info("route=%s answer_chars=%d", route.kind, len(answer), extra={"route_kind": route.kind})
        return answer
    if route.kind == "save_styleguide":
        text = incoming.content.strip()
        if route.attachment:
            text = extract_styleguide_text(route.attachment)
        text = _strip_styleguide_prefix(text)
        if not text:
            raise ServiceError("Стильгайд пустой.")
        config.STYLEGUIDE_PATH.write_text(text, encoding="utf-8")
        return "Стайлгайд сохранен. Буду применять его при следующих ревью."
    if route.kind == "unsupported_media":
        return "Транскрибация аудио и видео в Discord отключена из-за лимитов на размер вложений."
    answer = await call_route(route, incoming)
    logger.info("route=%s answer_chars=%d", route.kind, len(answer), extra={"route_kind": route.kind})
    return answer


@dataclass(frozen=True)
class _TelemetryState:
    run_id: int
    session_id: int
    route_kind: str
    started_at: datetime
    user_id: str
    channel_id: str


def _start_telemetry(discord_message: discord.Message, incoming: IncomingMessage, route_kind: str) -> _TelemetryState | None:
    session_handle = telemetry.ensure_session(
        source="discord",
        external_session_id=_external_session_id(discord_message),
        guild_id=str(discord_message.guild.id) if discord_message.guild else None,
        channel_id=str(discord_message.channel.id),
        user_id=str(discord_message.author.id),
        metadata={
            "author_name": str(discord_message.author),
            "channel_name": getattr(discord_message.channel, "name", None),
            "guild_name": discord_message.guild.name if discord_message.guild else None,
        },
    )
    if session_handle is None:
        return None
    run_handle = telemetry.start_run(
        session_id=session_handle.id,
        source="discord",
        route_kind=route_kind,
        model_name=config.LLM_MODEL_NAME,
        provider="openrouter",
        temperature=config.LLM_TEMPERATURE,
        input_chars=len(incoming.content),
        metadata={
            "message_id": str(discord_message.id),
            "attachment_count": len(incoming.attachments),
        },
    )
    if run_handle is None:
        return None
    telemetry.record_event(
        run_handle.id,
        "run_started",
        {"route_kind": route_kind, "message_id": str(discord_message.id)},
    )
    for attachment in incoming.attachments:
        telemetry.add_attachment(
            run_handle.id,
            filename=attachment.filename,
            content_type=attachment.content_type,
            path=attachment.path,
        )
    logger.info(
        "run_started",
        extra={
            "service": "hermes-discord",
            "event": "run_started",
            "run_id": run_handle.id,
            "session_id": session_handle.id,
            "route_kind": route_kind,
            "user_id": str(discord_message.author.id),
            "channel_id": str(discord_message.channel.id),
            "model": config.LLM_MODEL_NAME,
        },
    )
    return _TelemetryState(
        run_id=run_handle.id,
        session_id=session_handle.id,
        route_kind=route_kind,
        started_at=run_handle.started_at,
        user_id=str(discord_message.author.id),
        channel_id=str(discord_message.channel.id),
    )


def _complete_telemetry_success(state: _TelemetryState, answer: str) -> None:
    telemetry.complete_run(
        state.run_id,
        started_at=state.started_at,
        output_chars=len(answer),
        status="success",
    )
    telemetry.record_event(state.run_id, "run_completed", {"output_chars": len(answer)})
    logger.info(
        "run_completed",
        extra={
            "service": "hermes-discord",
            "event": "run_completed",
            "run_id": state.run_id,
            "session_id": state.session_id,
            "route_kind": state.route_kind,
            "user_id": state.user_id,
            "channel_id": state.channel_id,
            "model": config.LLM_MODEL_NAME,
        },
    )


def _complete_telemetry_failure(state: _TelemetryState, error_message: str) -> None:
    short_error = error_message[:2000]
    telemetry.complete_run(
        state.run_id,
        started_at=state.started_at,
        output_chars=0,
        status="error",
        error_message=short_error,
    )
    telemetry.record_event(state.run_id, "run_failed", {"error_message": short_error})
    logger.error(
        "run_failed: %s",
        short_error,
        extra={
            "service": "hermes-discord",
            "event": "run_failed",
            "run_id": state.run_id,
            "session_id": state.session_id,
            "route_kind": state.route_kind,
            "user_id": state.user_id,
            "channel_id": state.channel_id,
            "model": config.LLM_MODEL_NAME,
        },
    )


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


async def _send_answer(message: discord.Message, answer: str, filename: str = "result.md") -> None:
    if len(answer) <= 1200:
        await message.reply(answer, mention_author=False)
        return

    payload = io.BytesIO(answer.encode("utf-8"))
    file = discord.File(payload, filename=filename)
    await message.reply(f"Готово. Полный результат приложен файлом `{filename}`.", file=file, mention_author=False)


def _result_filename(route, incoming: IncomingMessage) -> str:
    kind = _route_filename_part(route)
    context = _context_filename_part(incoming)
    parts = [part for part in (context, kind, "result") if part]
    deduped: list[str] = []
    for part in parts:
        if part not in deduped:
            deduped.append(part)
    return f"{'-'.join(deduped[:4])}.md"


def _route_filename_part(route) -> str:
    if route.kind in {"spec_text", "spec_file"}:
        return "spec"
    if route.kind in {"api_docs_text", "api_docs_file"}:
        return "api-docs"
    if route.kind == "figma_link":
        return "figma-guide"
    if route.kind in {"jira_release", "github_release"}:
        return "changelog" if route.output_type == "changelog" else "release-notes"
    if route.kind == "review":
        return "review"
    if route.kind == "save_styleguide":
        return "styleguide"
    return "result"


def _context_filename_part(incoming: IncomingMessage) -> str:
    if incoming.attachments:
        slug = _slugify(incoming.attachments[0].path.stem)
        if slug:
            return slug

    first_line = next((line.strip() for line in incoming.content.splitlines() if line.strip()), "")
    first_line = re.sub(r"https?://\S+", " ", first_line)
    return _slugify(first_line)


def _slugify(value: str, max_words: int = 3) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    tokens = re.findall(r"[a-z0-9]+", ascii_text.lower())
    stop_words = {"the", "and", "for", "with", "file", "doc", "docs", "result"}
    tokens = [token for token in tokens if token not in stop_words]
    return "-".join(tokens[:max_words])


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


def _external_session_id(message: discord.Message) -> str:
    guild_id = str(message.guild.id) if message.guild else "dm"
    return f"{guild_id}:{message.channel.id}:{message.author.id}"
