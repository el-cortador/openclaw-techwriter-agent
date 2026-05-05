from __future__ import annotations

import json


def _limit_elements(filtered_json: dict, limit: int = 20) -> dict:
    if not filtered_json or "screens" not in filtered_json:
        return filtered_json

    trimmed = {"file_name": filtered_json.get("file_name"), "screens": []}
    remaining = limit
    for screen in filtered_json.get("screens", []):
        if remaining <= 0:
            break
        elements = screen.get("elements", [])
        trimmed_elements = elements[:remaining]
        remaining -= len(trimmed_elements)
        trimmed["screens"].append(
            {
                "id": screen.get("id"),
                "name": screen.get("name"),
                "type": screen.get("type"),
                "elements": trimmed_elements,
            }
        )

    return trimmed


def build_prompt(
    filtered_json: dict,
    language: str,
    detail_level: str,
    audience: str,
) -> str:
    limited_json = _limit_elements(filtered_json, limit=20)
    return (
        "Ты — технический писатель. Сгенерируй пошаговое руководство по интерфейсу. "
        "Ответ должен содержать два раздела: MARKDOWN и JSON. "
        "В JSON укажи: title, steps (массив объектов с полями index, title, description).\n\n"
        f"Язык: {language}\n"
        f"Детализация: {detail_level}\n"
        f"Аудитория: {audience}\n\n"
        "Данные об интерфейсе (JSON):\n"
        f"{json.dumps(limited_json, ensure_ascii=False)}\n\n"
        "Формат ответа:\n"
        "MARKDOWN:\n<текст>\n\nJSON:\n<json>"
    )


def parse_llm_output(text: str) -> tuple[str, dict]:
    cleaned = text
    while "<think>" in cleaned and "</think>" in cleaned:
        start = cleaned.find("<think>")
        end = cleaned.find("</think>", start)
        if end == -1:
            break
        cleaned = cleaned[:start] + cleaned[end + len("</think>") :]

    cleaned = cleaned.replace("<think>", "").replace("</think>", "")

    if "JSON:" not in cleaned:
        return cleaned.strip(), {"markdown": cleaned.strip()}

    markdown_part, json_part = cleaned.split("JSON:", 1)
    markdown = markdown_part.replace("MARKDOWN:", "").strip()
    json_str = json_part.strip()

    try:
        data = json.loads(json_str)
        return markdown, data
    except json.JSONDecodeError:
        return markdown, {"markdown": markdown}
