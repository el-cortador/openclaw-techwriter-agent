from __future__ import annotations

from app.schemas import OutputType


_RELEASE_NOTES_INSTRUCTIONS = """\
Сгенерируй ТОЛЬКО release notes на русском языке.

Требования:
- Не добавляй changelog.
- Не добавляй разделы Added / Changed / Fixed / Removed.
- Сделай человекочитаемый список изменений для пользователей без лишних технических деталей.
- Сгруппируй изменения по типам: Новые возможности, Улучшения, Исправления.
- Убери служебные коммиты: merge, bump version, chore, dependency update и похожие.
- Если по коммитам или задачам нельзя уверенно определить пользовательскую ценность, сформулируй осторожно и без выдуманных деталей.
- Если данных мало, все равно сформируй краткие release notes по доступным названиям задач; не возвращай пустой ответ."""


_CHANGELOG_INSTRUCTIONS = """\
Сгенерируй ТОЛЬКО changelog на русском языке.

Требования:
- Не добавляй release notes для пользователей.
- Используй Markdown.
- Используй структуру: Added / Changed / Fixed / Removed, но содержимое пунктов пиши на русском языке.
- Добавь заголовок с репозиторием/источником и периодом.
- Классифицируй изменения по смыслу коммитов или задач.
- Убери служебные коммиты: merge, bump version, chore, dependency update и похожие.
- Не оставляй англоязычные описания коммитов без перевода."""


def _instructions(output_type: OutputType) -> str:
    if output_type == "changelog":
        return _CHANGELOG_INSTRUCTIONS
    return _RELEASE_NOTES_INSTRUCTIONS


def github_prompt(
    owner: str,
    repo: str,
    date_from: str,
    date_to: str,
    commits: list[dict],
    output_type: OutputType = "release_notes",
) -> str:
    lines = "\n".join(
        f"- [{c['sha']}] {c['date']} {c['author']}: {c['message']}"
        for c in commits
    )
    return (
        f"Репозиторий: {owner}/{repo}\n"
        f"Период: с {date_from} по {date_to}\n\n"
        f"Коммиты:\n{lines}\n\n"
        f"{_instructions(output_type)}"
    )


def jira_prompt(
    issues: list[dict],
    output_type: OutputType = "release_notes",
    release_notes_text: str = "",
) -> str:
    blocks = []
    for issue in issues:
        meta = [
            f"тип: {issue.get('type', '')}",
            f"статус: {issue.get('status', '')}",
        ]
        if issue.get("fix_versions"):
            meta.append(f"fixVersion: {', '.join(issue['fix_versions'])}")
        if issue.get("components"):
            meta.append(f"компоненты: {', '.join(issue['components'])}")
        if issue.get("labels"):
            meta.append(f"labels: {', '.join(issue['labels'])}")

        block = f"- [{issue['key']}] ({'; '.join(meta)}) {issue.get('summary', '')}"
        description = issue.get("description", "").strip()
        if description:
            block += f"\n  Описание:\n  {description.replace(chr(10), chr(10) + '  ')}"
        blocks.append(block)

    lines = "\n".join(blocks)
    release_notes_text = release_notes_text.strip()
    if release_notes_text:
        return (
            f"Jira-задачи:\n{lines}\n\n"
            f"Актуальные Release Notes:\n{release_notes_text}\n\n"
            "Сопоставь каждый пункт Release Notes с наиболее подходящей Jira-задачей.\n"
            "Ответь только итоговым сопоставлением на русском языке простым Markdown-списком.\n"
            "Не используй жирный шрифт, таблицы, HTML или декоративное форматирование.\n"
            "Для каждого пункта укажи ключ Jira и короткое объяснение совпадения.\n"
            "Если для пункта нет уверенного соответствия, укажи: Jira не определена.\n"
            "Не придумывай факты, которых нет в Jira-задачах или Release Notes."
        )
    return (
        f"Jira-задачи:\n{lines}\n\n"
        f"{_instructions(output_type)}"
    )
