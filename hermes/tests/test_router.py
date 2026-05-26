from __future__ import annotations

import unittest
from pathlib import Path

from app.models import IncomingAttachment, IncomingMessage
from app.router import classify


def message(content: str, filename: str | None = None) -> IncomingMessage:
    attachments = []
    if filename:
        attachments.append(IncomingAttachment(filename=filename, content_type=None, path=Path(filename)))
    return IncomingMessage(content=content, attachments=attachments)


class RouterTest(unittest.TestCase):
    def test_jira_urls_route_to_release_notes(self) -> None:
        route = classify(message("Сделай release notes https://example.atlassian.net/browse/ABC-123"))
        self.assertEqual(route.kind, "jira_release")
        self.assertEqual(route.output_type, "release_notes")

    def test_changelog_github_with_dates(self) -> None:
        route = classify(message("changelog https://github.com/acme/app с 01.01.2026 по 31.01.2026"))
        self.assertEqual(route.kind, "github_release")
        self.assertEqual(route.output_type, "changelog")

    def test_openapi_file_route(self) -> None:
        route = classify(message("Опиши API", "openapi.yaml"))
        self.assertEqual(route.kind, "api_docs_file")

    def test_styleguide_docx_filename_route(self) -> None:
        route = classify(message("", "стайлгайд документации.docx"))
        self.assertEqual(route.kind, "save_styleguide")
        self.assertIsNotNone(route.attachment)

    def test_styleguide_docx_message_route(self) -> None:
        route = classify(message("это стайлгайд", "rules.docx"))
        self.assertEqual(route.kind, "save_styleguide")
        self.assertIsNotNone(route.attachment)

    def test_figma_link_route(self) -> None:
        route = classify(message("Сделай guide по https://www.figma.com/design/abc/Test"))
        self.assertEqual(route.kind, "figma_link")
        self.assertEqual(route.urls, ["https://www.figma.com/design/abc/Test"])

    def test_ui_screenshot_route_keeps_attachment(self) -> None:
        route = classify(message("Сделай guide по макету", "screen.png"))
        self.assertEqual(route.kind, "figma_link")
        self.assertIsNotNone(route.attachment)

    def test_media_file_route(self) -> None:
        route = classify(message("Расшифруй", "call.mp4"))
        self.assertEqual(route.kind, "unsupported_media")

    def test_review_route(self) -> None:
        route = classify(message("Проверь этот текст по стайлгайду"))
        self.assertEqual(route.kind, "review")

    def test_api_token_alone_does_not_route_to_api_docs(self) -> None:
        route = classify(message("Настройка MCP сервера\nX-API-Token: string\nhost: localhost:8080"))
        self.assertEqual(route.kind, "spec_text")

    def test_explicit_api_docs_route(self) -> None:
        route = classify(message("Сделай API-документацию для GET /users"))
        self.assertEqual(route.kind, "api_docs_text")

    def test_generic_text_route(self) -> None:
        route = classify(message("Нужна инструкция по новой функции"))
        self.assertEqual(route.kind, "spec_text")

    def test_short_greeting_route(self) -> None:
        route = classify(message("привет"))
        self.assertEqual(route.kind, "unknown_short")

    def test_short_greeting_with_discord_mention_route(self) -> None:
        route = classify(message("<@1508830390981497062> привет\u200b"))
        self.assertEqual(route.kind, "unknown_short")


if __name__ == "__main__":
    unittest.main()
