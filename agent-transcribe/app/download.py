from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from app.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE, TEMP_DIR
from app.exceptions import DownloadError

logger = logging.getLogger(__name__)

CONTENT_TYPE_EXTENSIONS = {
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/ogg": ".ogg",
    "audio/webm": ".webm",
    "audio/mp4": ".m4a",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/ogg": ".ogg",
}


def _normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise DownloadError("Укажите прямую http(s)-ссылку на аудио или видеофайл")

    if parsed.netloc in {"drive.google.com", "www.drive.google.com"}:
        parts = [p for p in parsed.path.split("/") if p]
        file_id = ""
        if len(parts) >= 3 and parts[0] == "file" and parts[1] == "d":
            file_id = parts[2]
        else:
            file_id = parse_qs(parsed.query).get("id", [""])[0]
        if file_id:
            return f"https://drive.google.com/uc?export=download&id={file_id}"

    return url.strip()


def _suffix_from_url(url: str) -> str | None:
    path = unquote(urlparse(url).path)
    suffix = Path(path).suffix.lower()
    if suffix in ALLOWED_EXTENSIONS:
        return suffix
    return None


def _suffix_from_content_type(content_type: str) -> str | None:
    media_type = content_type.split(";", 1)[0].strip().lower()
    suffix = CONTENT_TYPE_EXTENSIONS.get(media_type)
    if suffix in ALLOWED_EXTENSIONS:
        return suffix
    return None


async def download_media(url: str, job_id: str) -> Path:
    source_url = _normalize_url(url)
    timeout = httpx.Timeout(30.0, connect=10.0)
    headers = {"User-Agent": "openclaw-techwriter-agent/1.0"}

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, headers=headers) as client:
            async with client.stream("GET", source_url) as response:
                if response.status_code >= 400:
                    raise DownloadError(f"Не удалось скачать файл: HTTP {response.status_code}")

                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > MAX_FILE_SIZE:
                    limit_mb = MAX_FILE_SIZE // (1024 * 1024)
                    raise DownloadError(f"Файл превышает допустимый размер {limit_mb} МБ")

                suffix = (
                    _suffix_from_url(str(response.url))
                    or _suffix_from_content_type(response.headers.get("content-type", ""))
                    or ".mp4"
                )
                input_path = TEMP_DIR / f"{job_id}{suffix}"

                downloaded = 0
                with input_path.open("wb") as file:
                    async for chunk in response.aiter_bytes():
                        downloaded += len(chunk)
                        if downloaded > MAX_FILE_SIZE:
                            input_path.unlink(missing_ok=True)
                            limit_mb = MAX_FILE_SIZE // (1024 * 1024)
                            raise DownloadError(f"Файл превышает допустимый размер {limit_mb} МБ")
                        file.write(chunk)

    except DownloadError:
        raise
    except httpx.RequestError as exc:
        raise DownloadError(f"Не удалось скачать файл по ссылке: {exc}") from exc

    if not input_path.exists() or input_path.stat().st_size == 0:
        raise DownloadError("Скачанный файл пустой")

    logger.info("[download] OK %s bytes → %s", input_path.stat().st_size, input_path.name)
    return input_path
