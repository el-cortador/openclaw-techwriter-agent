from __future__ import annotations

from typing import Any, Iterable


KEYWORDS = {
    "button": ["button", "btn"],
    "input": ["input", "textfield", "text field", "textbox", "field", "search"],
    "header": ["header", "title", "heading", "h1", "h2", "h3"],
}


def _normalize_name(value: str | None) -> str:
    return (value or "").strip().lower()


def _detect_kind(node: dict[str, Any]) -> str:
    name = _normalize_name(node.get("name"))
    if node.get("type") == "TEXT":
        return "text"

    for kind, tokens in KEYWORDS.items():
        if any(token in name for token in tokens):
            return kind

    return "component"


def _is_relevant(node: dict[str, Any]) -> bool:
    if node.get("type") == "TEXT":
        return True

    name = _normalize_name(node.get("name"))
    return any(token in name for tokens in KEYWORDS.values() for token in tokens)


def _iter_children(node: dict[str, Any]) -> Iterable[dict[str, Any]]:
    return node.get("children", []) or []


def _collect_elements(node: dict[str, Any]) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    for child in _iter_children(node):
        if _is_relevant(child):
            item: dict[str, Any] = {
                "id": child.get("id"),
                "name": child.get("name"),
                "type": child.get("type"),
                "kind": _detect_kind(child),
            }
            if child.get("type") == "TEXT":
                item["text"] = child.get("characters", "")
            elements.append(item)

        elements.extend(_collect_elements(child))

    return elements


def filter_figma_json(figma_json: dict[str, Any]) -> dict[str, Any]:
    document = figma_json.get("document") or {}
    file_name = figma_json.get("name")

    frames = [child for child in _iter_children(document) if child.get("type") == "FRAME"]
    screens: list[dict[str, Any]] = []

    if frames:
        for frame in frames:
            screens.append(
                {
                    "id": frame.get("id"),
                    "name": frame.get("name"),
                    "type": frame.get("type"),
                    "elements": _collect_elements(frame),
                }
            )
    else:
        screens.append(
            {
                "id": document.get("id"),
                "name": document.get("name"),
                "type": document.get("type"),
                "elements": _collect_elements(document),
            }
        )

    return {
        "file_name": file_name,
        "screens": screens,
    }
