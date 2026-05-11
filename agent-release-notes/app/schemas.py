from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


OutputType = Literal["release_notes", "changelog"]


class GitHubRequest(BaseModel):
    repository: str = Field(..., min_length=1)
    date_from: str = Field(..., min_length=1)
    date_to: str = Field(..., min_length=1)
    branch: str = ""
    output_type: OutputType = "release_notes"


class JiraRequest(BaseModel):
    urls: list[str] = Field(..., min_length=1)
    output_type: OutputType = "release_notes"


class ServiceResponse(BaseModel):
    result: str | None = None
    error: str | None = None
