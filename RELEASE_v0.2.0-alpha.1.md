# techwriter-multi-agent v0.2.0-alpha.1

## Summary

Second alpha release: the repository is restructured into a portable agent package layout
(manifest + core + runtime packaging) with an installer, verification tooling, and prompts
managed as data. No changes to agent response behavior.

## Included

- agent contract in `manifest.yaml` (skills, secrets, runtime) following the agent package spec
- `core/` with runtime-independent behavior spec: scenarios, boundaries, canonical routing table
- five skill packages under `runtimes/hermes/skills/` with `SKILL.md` contracts and
  `instructions*.md` prompts loaded at runtime (prompts removed from Python code)
- legacy detailed prompts preserved as non-runtime drafts in `references/draft-detailed-prompt.md`
- idempotent installers `install.ps1` / `install.sh` (never overwrite existing `.env` or state)
- `verify-install` scripts with OK/WARN/FAIL report
- ops docs: smoke test plan, troubleshooting guide, `AGENTS.md`
- removed legacy `agent-*` microservice directories (superseded by in-process skills)
- Docker build context moved to repo root; skill packages ship in the image at `/app/skills`
- test suite runs on pytest, including a manifest-vs-packages contract test

## Operational Notes

- upgrading from v0.1.0-alpha.1: pull, then `docker compose up -d --build` (image rebuild required)
- state (`hermes/state/`, saved styleguide) is preserved by the existing volume mount
- verify the installation with `runtimes/hermes/scripts/verify-install.ps1` (or `.sh`)
- manual end-to-end checklist: `runtimes/hermes/docs/SMOKE_TEST_PLAN.md`

## Required Setup

- run `runtimes/hermes/install.ps1` (creates `.env` from `.env.example` if missing)
- set `DISCORD_BOT_TOKEN`
- set `OPENROUTER_API_KEY`
- optionally set `FIGMA_TOKEN`, `GITHUB_TOKEN`, `JIRA_EMAIL`, `JIRA_API_TOKEN`
- run `docker compose up -d --build`

## Known Limitations

- no historical backfill for old sessions
- no auth layer for dashboard/API
- no dedicated DB migration framework yet
- Discord is the only fully wired runtime channel in this repo
- intent routing is keyword/regex-based (LLM-assisted classification not implemented)

## Suggested Tag

`v0.2.0-alpha.1`
