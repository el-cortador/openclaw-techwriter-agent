from __future__ import annotations

import logging
from pathlib import Path

from app import config
from app.skills.llm import generate_text
from app.skills.loader import load_instructions

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = frozenset({".pdf", ".docx"})
MAX_FILE_SIZE = 50 * 1024 * 1024


class ParserError(Exception):
    pass


def generate_draft_from_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ParserError(f"Неподдерживаемый формат {ext}. Допустимы: .pdf, .docx")
    if path.stat().st_size > MAX_FILE_SIZE:
        raise ParserError("Файл превышает допустимый размер 50 МБ")
    text = extract_text(path)
    if not text.strip():
        raise ParserError("Файл не содержит текста постановки")
    return generate_draft(text)


def generate_draft(extracted_text: str) -> str:
    user_message = (
        "Обработай следующую постановку аналитика и сформируй черновик технической документации.\n\n"
        f"<ПОСТАНОВКА>\n{extracted_text}\n</ПОСТАНОВКА>"
    )
    logger.info("[spec2doc] model=%s chars=%d", config.LLM_MODEL_NAME, len(extracted_text))
    return generate_text(
        [
            {"role": "system", "content": load_instructions("spec2doc")},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        max_tokens=config.LLM_MAX_TOKENS,
    )


def extract_text(file_path: str | Path) -> str:
    path = Path(file_path)
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _extract_pdf(path)
    if ext == ".docx":
        return _extract_docx(path)
    raise ParserError(f"Неподдерживаемый формат файла: {ext}")


def _extract_pdf(path: Path) -> str:
    import pdfplumber

    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())
    if not pages:
        raise ParserError("Файл содержит только изображения, текстовый слой не обнаружен")
    return "\n".join(pages)


def _extract_docx(path: Path) -> str:
    from docx import Document

    doc = Document(path)
    parts: list[str] = []
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if text:
            parts.append(text)
    for table in doc.tables:
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):
                rows.append("\t".join(cells))
        if rows:
            parts.append("\n".join(rows))
    if not parts:
        raise ParserError("Файл не содержит текста")
    return "\n\n".join(parts)
