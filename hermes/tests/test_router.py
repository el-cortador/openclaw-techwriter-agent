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
        route = classify(message("Make release notes https://example.atlassian.net/browse/ABC-123"))
        self.assertEqual(route.kind, "jira_release")
        self.assertEqual(route.output_type, "release_notes")

    def test_changelog_github_with_dates(self) -> None:
        route = classify(message("changelog https://github.com/acme/app from 2026-01-01 to 2026-01-31"))
        self.assertEqual(route.kind, "github_release")
        self.assertEqual(route.output_type, "changelog")

    def test_gitlab_merge_request_routes_to_spec2doc(self) -> None:
        route = classify(message("Опиши изменения https://gitlab.com/acme/app/-/merge_requests/42"))
        self.assertEqual(route.kind, "spec_merge_request")
        self.assertEqual(route.urls, ["https://gitlab.com/acme/app/-/merge_requests/42"])

    def test_self_hosted_gitlab_merge_request_route(self) -> None:
        route = classify(message("https://git.example.com/group/sub/app/merge_requests/7"))
        self.assertEqual(route.kind, "spec_merge_request")

    def test_github_pull_request_is_not_a_gitlab_merge_request(self) -> None:
        route = classify(message("Посмотри https://github.com/acme/app/pull/42"))
        self.assertNotEqual(route.kind, "spec_merge_request")

    def test_openapi_file_route(self) -> None:
        route = classify(message("Describe API", "openapi.yaml"))
        self.assertEqual(route.kind, "api_docs_file")

    def test_styleguide_docx_filename_route(self) -> None:
        route = classify(message("", "styleguide docs.docx"))
        self.assertEqual(route.kind, "save_styleguide")
        self.assertIsNotNone(route.attachment)

    def test_styleguide_docx_message_route(self) -> None:
        route = classify(message("styleguide:", "rules.docx"))
        self.assertEqual(route.kind, "save_styleguide")
        self.assertIsNotNone(route.attachment)

    def test_figma_link_route(self) -> None:
        route = classify(message("Create guide for https://www.figma.com/design/abc/Test"))
        self.assertEqual(route.kind, "figma_link")
        self.assertEqual(route.urls, ["https://www.figma.com/design/abc/Test"])

    def test_ui_screenshot_route_keeps_attachment(self) -> None:
        route = classify(message("Create guide for layout", "screen.png"))
        self.assertEqual(route.kind, "figma_link")
        self.assertIsNotNone(route.attachment)

    def test_media_file_route(self) -> None:
        route = classify(message("Transcribe this", "call.mp4"))
        self.assertEqual(route.kind, "unsupported_media")

    def test_review_route(self) -> None:
        route = classify(message("review this text by styleguide"))
        self.assertEqual(route.kind, "review")

    def test_review_url_route(self) -> None:
        route = classify(message("Проверь https://docs.example.com/guide/install"))
        self.assertEqual(route.kind, "review_url")
        self.assertEqual(route.urls, ["https://docs.example.com/guide/install"])

    def test_review_file_route(self) -> None:
        route = classify(message("Проверь этот документ", "guide.md"))
        self.assertEqual(route.kind, "review_file")
        self.assertIsNotNone(route.attachment)

    def test_markdown_file_routes_to_spec2doc(self) -> None:
        route = classify(message("Нужна инструкция", "postanovka.md"))
        self.assertEqual(route.kind, "spec_file")

    def test_legacy_doc_file_routes_to_spec2doc(self) -> None:
        route = classify(message("", "postanovka.doc"))
        self.assertEqual(route.kind, "spec_file")

    def test_styleguide_markdown_file_still_saves_styleguide(self) -> None:
        route = classify(message("это стайлгайд", "rules.md"))
        self.assertEqual(route.kind, "save_styleguide")

    def test_api_token_alone_does_not_route_to_api_docs(self) -> None:
        route = classify(message("MCP server setup\nX-API-Token: string\nhost: localhost:8080"))
        self.assertEqual(route.kind, "spec_text")

    def test_explicit_api_docs_route(self) -> None:
        route = classify(message("Create API docs for GET /users"))
        self.assertEqual(route.kind, "api_docs_text")

    def test_generic_text_route(self) -> None:
        route = classify(message("Need an instruction for a new feature"))
        self.assertEqual(route.kind, "spec_text")

    def test_release_notes_intent_without_source_does_not_fall_back_to_spec(self) -> None:
        route = classify(message("Collect release notes for the new feature"))
        self.assertEqual(route.kind, "release_request")
        self.assertEqual(route.output_type, "release_notes")

    def test_short_greeting_route(self) -> None:
        route = classify(message("hello"))
        self.assertEqual(route.kind, "unknown_short")

    def test_short_greeting_with_discord_mention_route(self) -> None:
        route = classify(message("<@1508830390981497062> hello\u200b"))
        self.assertEqual(route.kind, "unknown_short")


if __name__ == "__main__":
    unittest.main()
