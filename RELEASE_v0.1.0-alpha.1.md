# techwriter-super-agent v0.1.0-alpha.1

## Summary

First alpha release of the self-hosted Discord documentation agent with an integrated telemetry dashboard.

## Included

- Discord gateway for documentation workflows
- local in-process skills for spec, review, API docs, release notes, and Figma guidance
- Postgres-backed telemetry for sessions, runs, LLM calls, attachments, and events
- browser dashboard for activity, sessions, runs, model usage, cost, and errors
- OpenRouter text model default: `deepseek/deepseek-v4-pro`
- OpenRouter vision model default: `google/gemini-2.5-flash`

## Operational Notes

- dashboard access is intended for local/internal use
- historical data starts from telemetry-enabled runs only
- pricing is estimated from env-configured model rates
- dashboard/API authentication is not implemented in this alpha

## Required Setup

- copy `.env.example` to `.env`
- set `DISCORD_BOT_TOKEN`
- set `OPENROUTER_API_KEY`
- optionally set `FIGMA_TOKEN`, `GITHUB_TOKEN`, `JIRA_EMAIL`, `JIRA_API_TOKEN`
- run `docker compose up -d --build`

## Known Limitations

- no historical backfill for old sessions
- no auth layer for dashboard/API
- no dedicated DB migration framework yet
- Discord is the only fully wired runtime channel in this repo

## Suggested Tag

`v0.1.0-alpha.1`
