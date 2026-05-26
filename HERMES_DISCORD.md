# Hermes Discord Gateway

This project can run a Discord gateway next to the existing OpenClaw gateway.

Runtime path:

```text
Discord -> hermes-discord -> agent-* HTTP services
```

The specialized services stay unchanged:

- `agent-spec2doc` -> `http://agent-spec2doc:8001`
- `agent-figma` -> `http://agent-figma:8002`
- `agent-transcribe` -> `http://agent-transcribe:8003`
- `agent-release-notes` -> `http://agent-release-notes:8004`
- `agent-api-docs` -> `http://agent-api-docs:8005`
- `agent-reviewer` -> `http://agent-reviewer:8006`

## Environment

Add these values to `.env`:

```env
DISCORD_BOT_TOKEN=
DISCORD_ALLOWED_GUILD_IDS=
DISCORD_ALLOWED_CHANNEL_IDS=
DISCORD_ALLOWED_USER_IDS=
```

`DISCORD_ALLOWED_USER_IDS` is optional. Values can be comma-separated.

The Discord bot must have Message Content Intent enabled in the Discord Developer Portal.

## Run

```bash
docker compose up -d --build hermes-discord
```

Check logs:

```bash
docker compose logs hermes-discord --tail=100
```

The new stack does not publish `agent-*` ports to the host. This avoids conflicts with the existing OpenClaw stack and is enough for Hermes, because it calls services through the internal Docker network.

## Routing

The gateway uses deterministic rules:

- Jira issue URLs -> `agent-release-notes /generate-jira`
- GitHub repo plus date range -> `agent-release-notes /generate`
- `.yaml`, `.yml`, `.json` attachments -> `agent-api-docs /generate/file`
- API/REST endpoint text -> `agent-api-docs /generate`
- audio/video attachments -> `agent-transcribe /transcribe`
- direct media URL -> `agent-transcribe /transcribe/url`
- Figma links -> ask for a screenshot or text description
- UI screenshots -> Hermes vision guide generation
- review/check wording -> `agent-reviewer /review`
- `.pdf`, `.docx` attachments -> `agent-spec2doc /process/file`
- generic text -> `agent-spec2doc /process`

Style guides are stored in `hermes/state/styleguide.md` and passed to future review requests.

Figma links are acknowledged with a request for a screenshot or text description. UI screenshots are processed by the Hermes gateway through a vision model configured by `HERMES_VISION_MODEL`.
