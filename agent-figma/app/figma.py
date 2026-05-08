from __future__ import annotations

import logging
import re

import httpx

from app.config import FIGMA_API_BASE, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


class FigmaError(Exception):
    """Base error for Figma integration."""


class FigmaAuthError(FigmaError):
    """Raised when Figma token is invalid or unauthorized."""


class FigmaNotFoundError(FigmaError):
    """Raised when Figma file is not found."""


class FigmaRequestError(FigmaError):
    """Raised for unexpected Figma API errors."""


class FigmaBadUrlError(FigmaError):
    """Raised when Figma file id cannot be extracted from URL."""


class FigmaRateLimitError(FigmaError):
    """Raised when Figma API rate limit is exceeded."""


def extract_file_id(value: str) -> str:
    if not value:
        raise FigmaBadUrlError("URL is empty")

    raw = value.strip()

    if re.fullmatch(r"[A-Za-z0-9]{10,}", raw):
        return raw

    match = re.search(
        r"https?://(?:www\.)?figma\.com/(?:file|proto|design)/([A-Za-z0-9]+)",
        raw,
    )
    if match:
        return match.group(1)

    raise FigmaBadUrlError("Cannot extract file id from URL")


class FigmaClient:
    def __init__(
        self,
        base_url: str = FIGMA_API_BASE,
        timeout: float = REQUEST_TIMEOUT,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=timeout, transport=transport)

    def get_file(self, file_id: str, token: str) -> dict:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        # Try without token first (for public files)
        logger.info("[figma] Trying to fetch file %s without token", file_id)
        response = self._client.get(f"/files/{file_id}", headers=headers)
        logger.info("[figma] Response status: %d", response.status_code)

        # If file is private and token provided, try with token
        if response.status_code in (401, 403) and token:
            logger.info("[figma] Got 403/401, retrying with token")
            headers["X-FIGMA-TOKEN"] = token
            response = self._client.get(f"/files/{file_id}", headers=headers)
            logger.info("[figma] Response with token: %d", response.status_code)

        if response.status_code == 404:
            raise FigmaNotFoundError("File not found")
        if response.status_code == 429:
            raise FigmaRateLimitError("Rate limit exceeded")
        if response.status_code in (401, 403):
            raise FigmaAuthError("Invalid or unauthorized token")
        if response.status_code >= 400:
            raise FigmaRequestError(f"Figma API error: {response.status_code}")

        return response.json()

    def close(self) -> None:
        self._client.close()
