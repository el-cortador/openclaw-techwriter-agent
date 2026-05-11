from __future__ import annotations

import logging
import re
from datetime import datetime
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException
from openai import OpenAI

from app.config import LLM_MODEL_NAME, MAX_TOKENS, OPENROUTER_API_KEY
from app.github_client import (
    GitHubAuthError,
    GitHubError,
    GitHubNotFoundError,
    get_commits,
)
from app.jira import JiraAuthError, JiraClient, JiraError, JiraRequestError
from app.prompts import github_prompt, jira_prompt
from app.schemas import GitHubRequest, JiraRequest, ServiceResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="agent-release-notes", version="1.0.0")


def _parse_repository(repository: str) -> tuple[str, str]:
    value = repository.strip()
    if not value:
        raise ValueError("Укажите GitHub-репозиторий")

    if value.startswith(("http://", "https://")):
        parsed = urlparse(value)
        parts = [p for p in parsed.path.strip("/").split("/") if p]
    else:
        parts = [p for p in value.strip("/").split("/") if p]

    if len(parts) < 2:
        raise ValueError("Укажите репозиторий в формате owner/repo или GitHub URL")

    owner = parts[0]
    repo = re.sub(r"\.git$", "", parts[1])
    if not owner or not repo:
        raise ValueError("Укажите репозиторий в формате owner/repo или GitHub URL")
    return owner, repo


def _parse_date(value: str, field_name: str) -> datetime:
    raw = value.strip()
    for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(f"{field_name} должна быть в формате ДД-ММ-ГГГГ")


def _date_range(date_from: str, date_to: str) -> tuple[str, str, str, str]:
    start = _parse_date(date_from, "date_from")
    end = _parse_date(date_to, "date_to")
    if start > end:
        raise ValueError("date_from не может быть позже date_to")
    since = start.strftime("%Y-%m-%dT00:00:00Z")
    until = end.strftime("%Y-%m-%dT23:59:59Z")
    return since, until, start.strftime("%d-%m-%Y"), end.strftime("%d-%m-%Y")


def _llm_generate(prompt: str) -> str:
    client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
    response = client.chat.completions.create(
        model=LLM_MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=MAX_TOKENS,
    )
    return response.choices[0].message.content or ""


def get_jira_client() -> JiraClient:
    try:
        return JiraClient()
    except JiraError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/generate", response_model=ServiceResponse)
def generate_github(payload: GitHubRequest) -> ServiceResponse:
    try:
        owner, repo = _parse_repository(payload.repository)
        since, until, display_from, display_to = _date_range(
            payload.date_from,
            payload.date_to,
        )
        commits = get_commits(owner, repo, since, until, payload.branch)
        if not commits:
            return ServiceResponse(result="За указанный период коммитов не найдено.")
        prompt = github_prompt(owner, repo, display_from, display_to, commits)
        return ServiceResponse(result=_llm_generate(prompt))
    except ValueError as exc:
        return ServiceResponse(error=str(exc))
    except GitHubAuthError as exc:
        return ServiceResponse(error=str(exc))
    except GitHubNotFoundError as exc:
        return ServiceResponse(error=str(exc))
    except GitHubError as exc:
        return ServiceResponse(error=str(exc))
    except Exception as exc:
        logger.error("[generate] %s", exc)
        return ServiceResponse(error=str(exc))


@app.post("/generate-jira", response_model=ServiceResponse)
def generate_jira(
    payload: JiraRequest,
    jira: JiraClient = Depends(get_jira_client),
) -> ServiceResponse:
    urls = [u for u in payload.urls if u.strip()]
    if not urls:
        return ServiceResponse(error="Укажите хотя бы один URL задачи")
    try:
        issues = jira.get_issues(urls)
        if not issues:
            return ServiceResponse(error="Не удалось распознать Jira URL")
        prompt = jira_prompt(issues)
        return ServiceResponse(result=_llm_generate(prompt))
    except JiraAuthError as exc:
        return ServiceResponse(error=str(exc))
    except JiraRequestError as exc:
        return ServiceResponse(error=str(exc))
    except Exception as exc:
        logger.error("[generate-jira] %s", exc)
        return ServiceResponse(error=str(exc))
