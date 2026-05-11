from __future__ import annotations

from pydantic import BaseModel, Field


class GitHubRequest(BaseModel):
    repository: str = Field(..., min_length=1)
    date_from: str = Field(..., min_length=1)
    date_to: str = Field(..., min_length=1)
    branch: str = ""


class JiraRequest(BaseModel):
    urls: list[str] = Field(..., min_length=1)


class ServiceResponse(BaseModel):
    result: str | None = None
    error: str | None = None
