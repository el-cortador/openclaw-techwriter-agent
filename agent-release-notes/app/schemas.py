from __future__ import annotations

from pydantic import BaseModel, Field


class GitHubRequest(BaseModel):
    owner: str = Field(..., min_length=1)
    repo: str = Field(..., min_length=1)
    since: str = Field(..., min_length=1)
    branch: str = ""


class JiraRequest(BaseModel):
    urls: list[str] = Field(..., min_length=1)


class ServiceResponse(BaseModel):
    result: str | None = None
    error: str | None = None
