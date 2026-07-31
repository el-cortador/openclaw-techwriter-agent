from __future__ import annotations

import unittest
from pathlib import Path

import yaml

from app import config
from app.skills.loader import SkillPackageError, load_instructions

REPO_ROOT = Path(__file__).resolve().parents[2]


class SkillPackageTest(unittest.TestCase):
    def test_manifest_required_skills_have_packages(self) -> None:
        manifest = yaml.safe_load((REPO_ROOT / "manifest.yaml").read_text(encoding="utf-8"))
        required = manifest["runtimes"]["hermes"]["skills"]["required"]
        self.assertEqual(sorted(required), ["api-docs", "doc-reviewer", "figma-guide", "release-notes", "spec2doc"])
        for skill in required:
            package = config.SKILLS_DIR / skill
            self.assertTrue((package / "SKILL.md").is_file(), f"SKILL.md missing for {skill}")
            self.assertTrue(
                any(package.glob("instructions*.md")),
                f"instructions*.md missing for {skill}",
            )

    def test_load_instructions_returns_nonempty_text(self) -> None:
        for skill in ("spec2doc", "api-docs", "doc-reviewer", "figma-guide"):
            self.assertTrue(load_instructions(skill), skill)

    def test_release_notes_instruction_variants(self) -> None:
        for filename in ("instructions-release_notes.md", "instructions-changelog.md", "instructions-mapping.md"):
            self.assertTrue(load_instructions("release-notes", filename), filename)

    def test_spec2doc_merge_request_instructions_exist(self) -> None:
        self.assertTrue(load_instructions("spec2doc", "instructions-merge_request.md"))

    def test_screenshot_instructions_exist(self) -> None:
        self.assertTrue(load_instructions("figma-guide", "instructions-screenshot.md"))

    def test_missing_instructions_raise_package_error(self) -> None:
        with self.assertRaises(SkillPackageError):
            load_instructions("no-such-skill")


if __name__ == "__main__":
    unittest.main()
