from __future__ import annotations

import logging

import requests

from app.config import GITHUB_TOKEN, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"


class GitHubError(Exception):
    pass


class GitHubAuthError(GitHubError):
    pass


class GitHubNotFoundError(GitHubError):
    pass


def get_commits(owner: str, repo: str, since: str, branch: str = "") -> list[dict]:
    """Returns list of commits: {sha, message, author, date}."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    params: dict = {"since": since, "per_page": 100}
    if branch:
        params["sha"] = branch

    url = f"{_GITHUB_API}/repos/{owner}/{repo}/commits"
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        raise GitHubError(f"Не удалось подключиться к GitHub: {exc}") from exc

    if resp.status_code in (401, 403):
        raise GitHubAuthError("GitHub вернул 401/403. Проверьте GITHUB_TOKEN.")
    if resp.status_code == 404:
        raise GitHubNotFoundError(f"Репозиторий {owner}/{repo} не найден.")
    if resp.status_code >= 400:
        raise GitHubError(f"GitHub API ошибка {resp.status_code}")

    commits = []
    for item in resp.json():
        commit = item.get("commit", {})
        commits.append({
            "sha": item.get("sha", "")[:7],
            "message": commit.get("message", "").split("\n")[0],
            "author": commit.get("author", {}).get("name", ""),
            "date": commit.get("author", {}).get("date", "")[:10],
        })

    logger.info("[github] repo=%s/%s since=%s commits=%d", owner, repo, since, len(commits))
    return commits
