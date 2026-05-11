from __future__ import annotations

import logging
from urllib.parse import urlparse

import requests
from requests.auth import HTTPBasicAuth

from app.config import JIRA_API_TOKEN, JIRA_EMAIL, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


class JiraError(Exception):
    """Base Jira error."""


class JiraAuthError(JiraError):
    """Auth failed or insufficient permissions (401/403/404)."""


class JiraRequestError(JiraError):
    """Generic connectivity or HTTP error."""


class JiraClient:
    def __init__(
        self,
        email: str = JIRA_EMAIL,
        api_token: str = JIRA_API_TOKEN,
    ) -> None:
        if not email or not api_token:
            raise JiraError("JIRA_EMAIL и JIRA_API_TOKEN не заданы в .env")
        self._auth = HTTPBasicAuth(email, api_token)

    def get_issue(self, base_url: str, key: str) -> dict:
        logger.debug("[jira] fetching issue key=%s base=%s", key, base_url)
        try:
            resp = requests.get(
                f"{base_url}/rest/api/3/issue/{key}",
                auth=self._auth,
                params={
                    "fields": "summary,issuetype,status,description,labels,components,fixVersions"
                },
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status in (401, 403, 404):
                raise JiraAuthError(
                    f"Jira вернул {status}. Проверьте JIRA_EMAIL и JIRA_API_TOKEN в .env, "
                    "а также доступ к задачам."
                ) from e
            raise JiraRequestError(f"Jira API ошибка {status}") from e
        except requests.RequestException as e:
            raise JiraRequestError(f"Не удалось подключиться к Jira: {e}") from e

        fields = resp.json()["fields"]
        issue = {
            "key": key,
            "summary": fields.get("summary", ""),
            "type": fields.get("issuetype", {}).get("name", ""),
            "status": fields.get("status", {}).get("name", ""),
            "description": _adf_to_text(fields.get("description")),
            "labels": fields.get("labels") or [],
            "components": [
                item.get("name", "")
                for item in fields.get("components") or []
                if item.get("name")
            ],
            "fix_versions": [
                item.get("name", "")
                for item in fields.get("fixVersions") or []
                if item.get("name")
            ],
        }
        logger.debug(
            "[jira] fetched issue key=%s summary_chars=%d description_chars=%d",
            key,
            len(issue["summary"]),
            len(issue["description"]),
        )
        return issue

    def get_issues(self, urls: list[str]) -> list[dict]:
        grouped = _parse_jira_urls(urls)
        return [
            self.get_issue(base_url, key)
            for base_url, keys in grouped.items()
            for key in keys
        ]


def _parse_jira_urls(urls: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for url in urls:
        parsed = urlparse(url.strip())
        base = f"{parsed.scheme}://{parsed.netloc}"
        parts = parsed.path.strip("/").split("/")
        key = next((p for p in reversed(parts) if p and "-" in p), None)
        if key:
            result.setdefault(base, []).append(key)
    return result


def _adf_to_text(value: object) -> str:
    """Convert Atlassian Document Format into plain text."""
    if not value:
        return ""
    if isinstance(value, str):
        return value.strip()

    chunks: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return

        node_type = node.get("type")
        if node_type == "text":
            chunks.append(str(node.get("text", "")))
        elif node_type == "hardBreak":
            chunks.append("\n")

        content = node.get("content")
        if content:
            walk(content)

        if node_type in {"paragraph", "heading", "bulletList", "orderedList", "listItem"}:
            chunks.append("\n")

    walk(value)
    text = "".join(chunks)
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    return text[:4000]
