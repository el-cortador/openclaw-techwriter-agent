from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


RouteKind = Literal[
    "api_docs_file",
    "api_docs_text",
    "figma_link",
    "github_release",
    "jira_release",
    "release_request",
    "review",
    "save_styleguide",
    "spec_file",
    "spec_merge_request",
    "spec_text",
    "unknown_short",
    "unsupported_media",
]


@dataclass(frozen=True)
class IncomingAttachment:
    filename: str
    content_type: str | None
    path: Path

    @property
    def suffix(self) -> str:
        return self.path.suffix.lower()


@dataclass(frozen=True)
class IncomingMessage:
    content: str
    attachments: list[IncomingAttachment]


@dataclass(frozen=True)
class Route:
    kind: RouteKind
    attachment: IncomingAttachment | None = None
    urls: list[str] | None = None
    output_type: str = "release_notes"
