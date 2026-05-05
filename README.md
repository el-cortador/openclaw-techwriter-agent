# Super-Agent — AI-ассистент технического писателя

Telegram-бот на базе [OpenClaw](https://docs.openclaw.ai/), который принимает задачи и файлы, автоматически определяет их тип и роутит к нужному специализированному сервису.

## Архитектура

```
Telegram → OpenClaw (оркестратор)
                │
    ┌───────────┼───────────────────────┐
    │           │                       │
 :8001       :8002        ...        :8006
spec2doc    figma    transcribe    reviewer
```

| Сервис | Порт | Что делает |
|--------|------|-----------|
| `agent-spec2doc` | 8001 | Черновик технической документации из постановки аналитика |
| `agent-figma` | 8002 | User guide из Figma-ссылки |
| `agent-transcribe` | 8003 | Транскрипт + саммари из аудио/видео |
| `agent-release-notes` | 8004 | Релиз-ноты из GitHub-репо или Jira-задач |
| `agent-api-docs` | 8005 | API-документация из описания эндпоинтов |
| `agent-reviewer` | 8006 | Ревью документации по стайлгайду |

---

## Требования

- Docker + Docker Compose v2
- Токен Telegram-бота ([@BotFather](https://t.me/BotFather) → `/newbot`)
- API-ключ [OpenRouter](https://openrouter.ai/keys)

---

## Установка и запуск

### 1. Клонировать репозиторий

```bash
git clone <repo-url>
cd openclaw-techwriter-agent
```

### 2. Заполнить переменные окружения

```bash
cp .env.example .env
# Открыть .env и заполнить значения
```

Минимально необходимые переменные:

```
TELEGRAM_BOT_TOKEN=...    # токен бота из @BotFather
OPENROUTER_API_KEY=...    # ключ OpenRouter
LLM_MODEL_NAME=meta-llama/llama-3.3-70b-instruct
```

Опциональные (для конкретных сервисов):

```
FIGMA_TOKEN=...           # для agent-figma
GITHUB_TOKEN=...          # для agent-release-notes (GitHub)
JIRA_EMAIL=...            # для agent-release-notes (Jira)
JIRA_API_TOKEN=...        # для agent-release-notes (Jira)
WHISPER_MODEL_NAME=base   # для agent-transcribe
WHISPER_DEVICE=auto       # auto / cpu / cuda
```

### 3. Запустить все сервисы

```bash
docker compose up --build
```

Первый запуск займёт несколько минут (сборка образов + загрузка Whisper-модели).

---

## Проверка работоспособности

```bash
curl http://localhost:8001/health  # {"status":"ok"}
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
curl http://localhost:8005/health
curl http://localhost:8006/health

docker compose logs openclaw        # логи OpenClaw
```

---

## Как использовать

Отправь боту сообщение в Telegram — он сам определит тип задачи:

| Что отправить | Что получишь |
|---------------|-------------|
| Текстовую постановку / требования к фиче | Черновик технической документации |
| Ссылку `figma.com/file/...` или `figma.com/design/...` | User guide по интерфейсу |
| Аудио- или видеофайл (.mp3, .wav, .mp4, .ogg, .m4a, .webm) | Транскрипт + саммари |
| Ссылку на GitHub-репо + дату (`github.com/owner/repo` + `2025-01-01`) | Релиз-ноты + Changelog |
| Ссылки на Jira-задачи | Релиз-ноты по задачам |
| Описание API / эндпоинтов | Черновик API-документации |
| Текст документации со словом «проверь» | Отчёт по ревью |

### Стайлгайд для ревьюера

```
Это стайлгайд: <текст правил>
```

Оркестратор сохранит стайлгайд и будет автоматически передавать его при каждом ревью.

---

## Переменные окружения

| Переменная | Обязательная | Описание |
|------------|:------------:|---------|
| `TELEGRAM_BOT_TOKEN` | Да | Токен бота из @BotFather |
| `OPENROUTER_API_KEY` | Да | API-ключ OpenRouter |
| `LLM_MODEL_NAME` | Да | Модель OpenRouter (default: `meta-llama/llama-3.3-70b-instruct`) |
| `FIGMA_TOKEN` | Нет | Figma Personal Access Token (Settings → Security) |
| `GITHUB_TOKEN` | Нет | GitHub PAT для получения коммитов |
| `JIRA_EMAIL` | Нет | Email аккаунта Jira |
| `JIRA_API_TOKEN` | Нет | Jira API token (id.atlassian.com → Security) |
| `WHISPER_MODEL_NAME` | Нет | `tiny`/`base`/`small`/`medium`/`large-v3` (default: `base`) |
| `WHISPER_DEVICE` | Нет | `auto`/`cpu`/`cuda` (default: `auto`) |

---

## Структура проекта

```
.
├── docker-compose.yml
├── .env.example
├── openclaw/
│   ├── openclaw.json          # конфиг OpenClaw
│   └── workspace/
│       └── AGENTS.md          # инструкции оркестратора
├── agent-spec2doc/            # PORT 8001
├── agent-figma/               # PORT 8002
├── agent-transcribe/          # PORT 8003
├── agent-release-notes/       # PORT 8004
├── agent-api-docs/            # PORT 8005
└── agent-reviewer/            # PORT 8006
```

Каждый сервис: `app/` (Python), `prompts/` (системный промпт где есть), `requirements.txt`, `Dockerfile`, `.env.example`.
