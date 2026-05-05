from __future__ import annotations

import logging
from pathlib import Path

import pdfplumber
from docx import Document

logger = logging.getLogger(__name__)


class ParserError(Exception):
    pass


def extract_text(file_path: str) -> str:
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        return _extract_pdf(path)
    if ext == ".docx":
        return _extract_docx(path)
    raise ParserError(f"Неподдерживаемый формат файла: «{ext}»")


def _extract_pdf(path: Path) -> str:
    pages: list[str] = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())

    if not pages:
        raise ParserError("Файл содержит только изображения — текстовый слой не обнаружен")

    logger.debug("[parser] pdf path=%s pages=%d", path.name, len(pages))
    return "\n".join(pages)


def _extract_docx(path: Path) -> str:
    doc = Document(path)
    parts: list[str] = []

    for block in doc.element.body:
        tag = block.tag.split("}")[-1]

        if tag == "p":
            text = "".join(
                t.text
                for run in block.iterchildren()
                if run.tag.split("}")[-1] == "r"
                for t in run.iterchildren()
                if t.tag.split("}")[-1] == "t" and t.text
            )
            if text.strip():
                parts.append(text.strip())

        elif tag == "tbl":
            rows: list[str] = []
            for row in block.iterchildren():
                if row.tag.split("}")[-1] != "tr":
                    continue
                cells: list[str] = []
                for cell in row.iterchildren():
                    if cell.tag.split("}")[-1] != "tc":
                        continue
                    cell_text = "".join(
                        t.text
                        for p in cell.iterchildren()
                        for r in p.iterchildren()
                        for t in r.iterchildren()
                        if t.tag.split("}")[-1] == "t" and t.text
                    )
                    cells.append(cell_text.strip())
                if any(cells):
                    rows.append("\t".join(cells))
            if rows:
                parts.append("\n".join(rows))

    if not parts:
        raise ParserError("Файл не содержит текста")

    logger.debug("[parser] docx path=%s parts=%d", path.name, len(parts))
    return "\n\n".join(parts)
