from __future__ import annotations

_INSTRUCTIONS = """\
Сгенерируй на русском языке два блока:

## Релиз-ноты для пользователей
Человекочитаемый список изменений без технических деталей.
Сгруппируй по типам: Новые возможности, Улучшения, Исправления.
Убери служебные коммиты (merge, bump version, chore и т.п.).

## Changelog для разработчиков
Формат: Added / Changed / Fixed / Removed. Markdown, с версией и датой.
Используй семантику коммитов для классификации."""


def github_prompt(owner: str, repo: str, since: str, commits: list[dict]) -> str:
    lines = "\n".join(
        f"- [{c['sha']}] {c['date']} {c['author']}: {c['message']}"
        for c in commits
    )
    return (
        f"Репозиторий: {owner}/{repo}\n"
        f"Период: с {since}\n\n"
        f"Коммиты:\n{lines}\n\n"
        f"{_INSTRUCTIONS}"
    )


def jira_prompt(issues: list[dict]) -> str:
    lines = "\n".join(
        f"- [{i['key']}] ({i['type']}) {i['summary']}"
        for i in issues
    )
    return (
        f"Jira-задачи:\n{lines}\n\n"
        f"{_INSTRUCTIONS}"
    )
