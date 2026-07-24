from __future__ import annotations

from functools import lru_cache

from app import config


class SkillPackageError(Exception):
    pass


@lru_cache(maxsize=None)
def load_instructions(skill: str, filename: str = "instructions.md") -> str:
    path = config.SKILLS_DIR / skill / filename
    if not path.is_file():
        raise SkillPackageError(f"Skill instructions not found: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise SkillPackageError(f"Skill instructions are empty: {path}")
    return text
