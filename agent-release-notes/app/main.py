from __future__ import annotations

import logging

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
        commits = get_commits(payload.owner, payload.repo, payload.since, payload.branch)
        if not commits:
            return ServiceResponse(result="За указанный период коммитов не найдено.")
        prompt = github_prompt(payload.owner, payload.repo, payload.since, commits)
        return ServiceResponse(result=_llm_generate(prompt))
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
