from __future__ import annotations

import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import IncomingAttachment, IncomingMessage, Route
from app.skills import api_docs, figma, release_notes
from app.skills.runner import run_route


class SkillRunnerTest(unittest.IsolatedAsyncioTestCase):
    async def test_api_docs_text_route_runs_in_process(self) -> None:
        message = IncomingMessage(
            content="""
openapi: 3.0.0
info:
  title: Demo API
  version: 1.0.0
paths:
  /users:
    get:
      summary: List users
      responses:
        "200":
          description: OK
""",
            attachments=[],
        )

        result = await run_route(Route("api_docs_text"), message)

        self.assertIn("# Demo API", result)
        self.assertIn("## GET /users", result)
        self.assertIn("| 200 | OK |", result)

    async def test_api_docs_file_route_reads_utf8_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "openapi.yaml"
            path.write_text(
                "openapi: 3.0.0\ninfo:\n  title: File API\npaths:\n  /ping:\n    get:\n      responses:\n        '204':\n          description: No Content\n",
                encoding="utf-8",
            )
            message = IncomingMessage(
                content="",
                attachments=[IncomingAttachment(filename=path.name, content_type=None, path=path)],
            )

            result = await run_route(Route("api_docs_file", attachment=message.attachments[0]), message)

        self.assertIn("# File API", result)
        self.assertIn("## GET /ping", result)

    async def test_spec_text_route_uses_spec_skill_without_http(self) -> None:
        with patch("app.skills.spec2doc.generate_draft", return_value="# Draft") as generate:
            result = await run_route(Route("spec_text"), IncomingMessage(content="описание функции", attachments=[]))

        self.assertEqual(result, "# Draft")
        generate.assert_called_once_with("описание функции")

    async def test_review_route_passes_saved_styleguide(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            styleguide = Path(tmp) / "styleguide.md"
            styleguide.write_text("Пиши кратко", encoding="utf-8")
            with patch("app.config.STYLEGUIDE_PATH", styleguide):
                with patch("app.skills.reviewer.review", return_value="ok") as review:
                    result = await run_route(Route("review"), IncomingMessage(content="Проверь текст", attachments=[]))

        self.assertEqual(result, "ok")
        review.assert_called_once_with("Проверь текст", "Пиши кратко")

    async def test_github_release_builds_payload_from_route(self) -> None:
        route = Route(
            "github_release",
            urls=["https://github.com/acme/app"],
            output_type="changelog",
        )
        message = IncomingMessage(
            content="changelog https://github.com/acme/app с 01.01.2026 по 31.01.2026",
            attachments=[],
        )
        with patch("app.skills.release_notes.generate_github", return_value="changes") as generate:
            result = await run_route(route, message)

        self.assertEqual(result, "changes")
        generate.assert_called_once_with(
            repository="https://github.com/acme/app",
            date_from="01-01-2026",
            date_to="31-01-2026",
            branch="",
            output_type="changelog",
        )


class SkillUnitTest(unittest.TestCase):
    def test_openapi_renderer_does_not_need_llm(self) -> None:
        result = api_docs.generate_api_docs(
            """
openapi: 3.0.0
info:
  title: Local API
paths:
  /items:
    post:
      summary: Create item
      responses:
        "201":
          description: Created
"""
        )

        self.assertIn("# Local API", result)
        self.assertIn("## POST /items", result)

    def test_figma_file_id_extraction(self) -> None:
        self.assertEqual(
            figma.extract_file_id("https://www.figma.com/design/AbC123456789/Test"),
            "AbC123456789",
        )

    def test_figma_filter_extracts_wireflow_from_canvas_frames(self) -> None:
        filtered = figma.filter_figma_json(
            {
                "name": "Checkout wireframes",
                "document": {
                    "id": "doc",
                    "type": "DOCUMENT",
                    "children": [
                        {
                            "id": "page-1",
                            "name": "Happy path",
                            "type": "CANVAS",
                            "children": [
                                {
                                    "id": "screen-2",
                                    "name": "02 Payment",
                                    "type": "FRAME",
                                    "absoluteBoundingBox": {"x": 500, "y": 0, "width": 390, "height": 844},
                                    "children": [
                                        {"id": "text-2", "name": "Title", "type": "TEXT", "characters": "Payment"},
                                    ],
                                },
                                {
                                    "id": "screen-1",
                                    "name": "01 Cart",
                                    "type": "FRAME",
                                    "absoluteBoundingBox": {"x": 0, "y": 0, "width": 390, "height": 844},
                                    "children": [
                                        {"id": "text-1", "name": "Title", "type": "TEXT", "characters": "Cart"},
                                    ],
                                },
                            ],
                        }
                    ],
                },
            }
        )

        self.assertEqual(filtered["mode"], "wireflow")
        self.assertEqual([screen["id"] for screen in filtered["screens"]], ["screen-1", "screen-2"])
        self.assertEqual(filtered["flows"][0]["trigger"], "inferred_order")
        self.assertEqual(filtered["flows"][0]["from"], "screen-1")
        self.assertEqual(filtered["flows"][0]["to"], "screen-2")

    def test_figma_filter_keeps_prototype_connections(self) -> None:
        filtered = figma.filter_figma_json(
            {
                "name": "Prototype",
                "document": {
                    "id": "doc",
                    "type": "DOCUMENT",
                    "children": [
                        {
                            "id": "page-1",
                            "name": "Flow",
                            "type": "CANVAS",
                            "children": [
                                {
                                    "id": "screen-1",
                                    "name": "Start",
                                    "type": "FRAME",
                                    "absoluteBoundingBox": {"x": 0, "y": 0, "width": 390, "height": 844},
                                    "reactions": [
                                        {
                                            "trigger": {"type": "ON_CLICK"},
                                            "action": {"type": "NODE", "destinationId": "screen-2"},
                                        }
                                    ],
                                    "children": [],
                                },
                                {
                                    "id": "screen-2",
                                    "name": "Finish",
                                    "type": "FRAME",
                                    "absoluteBoundingBox": {"x": 500, "y": 0, "width": 390, "height": 844},
                                    "children": [],
                                },
                            ],
                        }
                    ],
                },
            }
        )

        self.assertEqual(filtered["flows"], [
            {
                "from": "screen-1",
                "from_order": 1,
                "from_name": "Start",
                "to": "screen-2",
                "to_order": 2,
                "trigger": "ON_CLICK",
                "action": "NODE",
            }
        ])

    def test_figma_prompt_mentions_wireflow_analysis(self) -> None:
        prompt = figma.build_prompt(
            {
                "file_name": "Flow",
                "mode": "wireflow",
                "screens": [
                    {"id": "screen-1", "order": 1, "name": "Start", "elements": []},
                    {"id": "screen-2", "order": 2, "name": "Finish", "elements": []},
                ],
                "flows": [{"from": "screen-1", "to": "screen-2", "trigger": "inferred_order"}],
            },
            language="ru",
            detail_level="brief",
            audience="user",
        )

        self.assertIn("wireflow", prompt)
        self.assertIn("пользовательский путь", prompt)

    def test_jira_url_parser_groups_by_base_url(self) -> None:
        grouped = release_notes._parse_jira_urls(
            [
                "https://example.atlassian.net/browse/ABC-123",
                "https://example.atlassian.net/browse/ABC-456",
            ]
        )

        self.assertEqual(grouped, {"https://example.atlassian.net": ["ABC-123", "ABC-456"]})


if __name__ == "__main__":
    unittest.main()
