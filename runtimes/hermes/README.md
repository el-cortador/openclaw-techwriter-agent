# Runtime: Hermes (Discord gateway)

Runtime-упаковка techwriter-super-agent: skill-пакеты, установка, проверка и эксплуатация
поверх self-hosted Docker Compose стека.

## Состав

```text
skills/                 Skill-пакеты (SKILL.md + instructions*.md + references/)
  spec2doc/             Черновик инструкции из постановки (текст, PDF, DOCX) или merge request GitLab
  api-docs/             Документация по API (OpenAPI или текст)
  doc-reviewer/         Редакторское ревью (+ стайлгайд)
  release-notes/        Release notes / changelog из GitHub и Jira
  figma-guide/          Руководство по интерфейсу (Figma URL или скриншот)
install.ps1             Установка на Windows (идемпотентная, не перезаписывает .env)
install.sh              Установка на Linux/macOS (зеркало install.ps1)
scripts/
  verify-install.ps1    Проверка установки (OK/WARN/FAIL, код выхода 1 при FAIL)
  verify-install.sh     Зеркало для Linux/macOS
docs/
  SMOKE_TEST_PLAN.md    Ручная проверка после установки/обновления
  TROUBLESHOOTING.md    Симптом → причина → исправление
```

## Установка

```powershell
# Windows
runtimes\hermes\install.ps1

# Linux/macOS
runtimes/hermes/install.sh
```

Скрипт создает `.env` из `.env.example` (если отсутствует) и каталог состояния
`hermes/state/`. Существующие файлы не перезаписываются.

## Настройка

Обязательные секреты в `.env` (см. также `manifest.yaml`):

| Переменная | Назначение |
|---|---|
| `DISCORD_BOT_TOKEN` | Токен Discord-бота (нужен Message Content Intent) |
| `OPENROUTER_API_KEY` | Ключ OpenRouter для LLM и vision |

Опциональные: `GITHUB_TOKEN` (приватные репозитории), `GITLAB_TOKEN` (merge request'ы,
для приватных проектов обязателен), `JIRA_EMAIL` + `JIRA_API_TOKEN` (Jira-маршруты),
`FIGMA_TOKEN` (приватные Figma-файлы). Полный список — в `.env.example`.

## Запуск

```powershell
docker compose up -d --build
```

Сервис `hermes-discord` собирается из контекста репозитория: код gateway (`hermes/app/`)
и skill-пакеты (`runtimes/hermes/skills/` → `/app/skills/`, переменная `HERMES_SKILLS_DIR`).

## Проверка

```powershell
runtimes\hermes\scripts\verify-install.ps1   # установка
# smoke test — по чек-листу docs/SMOKE_TEST_PLAN.md
```

## Пути

| Назначение | Локально | В контейнере |
|---|---|---|
| Skill-пакеты | `runtimes/hermes/skills/` | `/app/skills/` |
| Состояние (стайлгайд) | `hermes/state/` | `/app/state/` (volume) |
| Код gateway | `hermes/app/` | `/app/app/` |
