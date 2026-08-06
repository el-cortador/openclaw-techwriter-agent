# techwriter-multi-agent v0.3.0-alpha.1

## Summary

Third alpha release: the `doc-reviewer` skill is removed from the Discord agent. Editorial review
of documentation is being moved to a standalone CLI linter, so the chat runtime keeps only the
scenarios that fit a chat channel. Build reproducibility is improved by making the pip index
configurable.

## Removed

- skill package `runtimes/hermes/skills/doc-reviewer/` (contract, runtime prompt, legacy draft prompt)
- routes `review`, `review_file`, `review_url`, `save_styleguide`
- modules `hermes/app/skills/reviewer.py`, `hermes/app/skills/webdocs.py`, `hermes/app/styleguide.py`
- saved styleguide state (`config.STYLEGUIDE_PATH`, `hermes/state/styleguide.md`) — no consumer left
- reviewer/webdocs/styleguide tests

Remaining skills: `spec2doc`, `api-docs`, `release-notes`, `figma-guide`.

## Added

- build arg `PIP_INDEX_URL` in `hermes/Dockerfile` and `dashboard-api/Dockerfile`, wired through
  `docker-compose.yml`; pip now runs with `--timeout 60 --retries 10`. Default stays `https://pypi.org/simple`;
  a mirror can be set in `.env` when the Docker network cannot reach pypi.org.

## Operational Notes

- upgrading from v0.2.0-alpha.1: pull, then `docker compose up -d --build` (image rebuild required)
- review requests are no longer routed: text with «проверь / ревью» now falls through to `spec2doc`,
  a document attachment produces an instruction draft instead of review notes
- `hermes/state/styleguide.md` can be deleted by hand; the runtime no longer reads it
- the removed behavior is written up for the future CLI linter in `DOC_LINTER_SPEC.md`, kept in the
  working copy and ignored by git; the last commit with working code is `78abf54`
- if the build fails with pip timeouts or `SSL: UNEXPECTED_EOF_WHILE_READING` on `pypi.org`,
  set `PIP_INDEX_URL` in `.env` to a reachable mirror
- manual end-to-end checklist: `runtimes/hermes/docs/SMOKE_TEST_PLAN.md`

## Required Setup

- unchanged from v0.2.0-alpha.1: `DISCORD_BOT_TOKEN`, `OPENROUTER_API_KEY`, optional
  `FIGMA_TOKEN`, `GITHUB_TOKEN`, `GITLAB_TOKEN`, `JIRA_EMAIL`, `JIRA_API_TOKEN`
- run `docker compose up -d --build`

## Known Limitations

- documentation review is unavailable until the CLI linter is built
- no historical backfill for old sessions
- no auth layer for dashboard/API
- no dedicated DB migration framework yet
- Discord is the only fully wired runtime channel in this repo
- intent routing is keyword/regex-based (LLM-assisted classification not implemented)

## Suggested Tag

`v0.3.0-alpha.1`
