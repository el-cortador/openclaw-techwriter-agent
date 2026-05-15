---
name: release-notes
description: Route release notes and changelog requests to agent-release-notes. Use for GitHub repositories with date ranges, Jira issue URLs, release notes, changelog, release-note diffs, and fix-to-task mapping.
---

# Release Notes

## Absolute Rules

- Always answer the user in Russian.
- For Jira issue URLs, never use `web_fetch`, `web_search`, browser tools, or direct page scraping.
- Jira pages often return huge Atlassian HTML/JS. Fetching them pollutes context and can break the next model call.
- Jira URLs must be passed only to `agent-release-notes` via `/generate-jira`.
- `agent-release-notes` is an HTTP service. Do not use OpenClaw sessions, subagents, or agent spawning for it.
- Do not produce release notes from Jira links yourself unless the user explicitly asks to work only from pasted text and no Jira URLs need to be opened.

## Format

- If the user asks for release notes, use `output_type=release_notes`.
- If the user asks for changelog, change log, or journal of changes, use `output_type=changelog`.
- If the user explicitly asks for both formats, ask one concise clarification question in Russian: release notes or changelog.

## Jira

For Jira tasks, always call:

```bash
curl -s -X POST http://agent-release-notes:8004/generate-jira \
  -H "Content-Type: application/json" \
  -d '{"urls": ["URL1", "URL2"], "output_type": "release_notes"}'
```

- For changelog, set `"output_type": "changelog"`.
- Timeout for Jira release notes/changelog must be at least 600 seconds.
- If `curl` returns an active process session, keep waiting for that same session.
- Start only one `/generate-jira` curl per user request. If the call becomes a process session, never start a retry curl; poll the existing session.
- If process polling says `Process still running` or `(no new output)`, do not answer the user yet. Poll the same session again until completed output, an exit code, or a concrete error appears.
- Poll long Jira/release-notes processes with a long timeout, for example `timeout: 60000`. Several minutes of runtime is normal and is not service unavailability.
- If the user sends Jira URLs plus pasted release-note text and asks to map tasks to fixes, call `/generate-jira` with the URLs and include the pasted text in `release_notes_text`.
- Do not save pasted Release Notes to a temporary file. Pass them in the JSON payload.

## GitHub

For a GitHub repository plus date range:

```bash
curl -s -X POST http://agent-release-notes:8004/generate \
  -H "Content-Type: application/json" \
  -d '{"repository": "github.com/OWNER/REPO", "date_from": "DD-MM-YYYY", "date_to": "DD-MM-YYYY", "branch": "", "output_type": "release_notes"}'
```

## Errors

- If the service returns `result`, return exactly that `result` text to the user. Do not add prefixes, explanations, summaries, or formatting changes.
- If the service returns `error`, reply in Russian with a short "service error" message and include the error text.
- Do not replace a concrete service error with generic requests for exports, screenshots, or pasted task text.
