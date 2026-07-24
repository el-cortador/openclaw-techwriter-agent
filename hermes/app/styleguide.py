from __future__ import annotations

import zipfile
from pathlib import Path
from xml.etree import ElementTree

from app.models import IncomingAttachment
from app.skills.runner import SkillError


def extract_styleguide_text(attachment: IncomingAttachment) -> str:
    suffix = attachment.suffix
    if suffix in {".md", ".txt"}:
        return attachment.path.read_text(encoding="utf-8-sig").strip()
    if suffix == ".docx":
        return _extract_docx_text(attachment.path).strip()
    if suffix == ".pdf":
        raise SkillError("PDF-стайлгайд пока не извлекается. Пришлите стайлгайд в DOCX, MD или текстом.")
    raise SkillError("Неподдерживаемый формат стайлгайда. Пришлите DOCX, MD или текст.")


def _extract_docx_text(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise SkillError("Не удалось прочитать DOCX-стайлгайд.") from exc

    root = ElementTree.fromstring(xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        texts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
        line = "".join(texts).strip()
        if line:
            paragraphs.append(line)
    return "\n".join(paragraphs)
