# Super-Agent — AI-ассистент технического писателя

Telegram-бот на базе [OpenClaw](https://docs.openclaw.ai/), который принимает задачи и файлы, автоматически определяет их тип и роутит к нужному специализированному сервису.

## Архитектура

```
Telegram → OpenClaw (оркестратор)
                │
    ┌───────────┼───────────────────────┐
    │           │                       │
 :8001       :8002        ...        :8006
spec2doc    figma         ...       reviewer
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

### 1. Клонируйте репозиторий

```bash
git clone <repo-url>
cd openclaw-techwriter-agent
```

### 2. Заполните переменные окружения

```bash
cp .env.example .env
# Открыть .env и заполнить значения
```

Базовые переменные:

```
TELEGRAM_BOT_TOKEN=...    # токен бота из @BotFather
OPENROUTER_API_KEY=...    # ключ OpenRouter
LLM_MODEL_NAME=moonshotai/kimi-k2.6
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

### 3. Запустите все сервисы

```bash
docker compose up --build
```

Первый запуск займет несколько минут (сборка образов + загрузка Whisper-модели).

### 4. Настройте пейринг с Telegram

Отправьте сообщение боту. Если он ответит **"Pairing code: ..."** — выполните команду:

```bash
docker compose exec -T openclaw openclaw pairing approve telegram <КОД>
```

Например:
```bash
docker compose exec -T openclaw openclaw pairing approve telegram JY79369S
```

После подтверждения успешного пейринга бот будет готов к работе.

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

## Как использовать

Отправьте боту сообщение в Telegram и он сам определит тип задачи:

| Отправлю | Получу |
|---------------|-------------|
| Текстовую постановку / требования к фиче | Черновик технической документации |
| Ссылку `figma.com/file/...` или `figma.com/design/...` | User guide по интерфейсу |
| Аудио- или видеофайл (.mp3, .wav, .mp4, .ogg, .m4a, .webm) | Транскрипт + саммари |
| Ссылку на GitHub-репо + дату (`github.com/owner/repo` + `2025-01-01`) | Релиз-ноты + Changelog |
| Ссылки на Jira-задачи | Релиз-ноты по задачам |
| Описание API / эндпоинтов | Черновик API-документации |
| Текст документации со словом «проверь» | Отчт по ревью |

### Стайлгайд для ревьюера

Загрузить стайлгайд можно двумя способами:

**Способ 1: Текстом в сообщении**
```
Это стайлгайд: 
- Используй повелительное наклонение
- Укажи требования в начале
- Добавь команды проверки в конец
```

**Способ 2: Файлом .md**
Просто загрузи файл `.md` с правилами стайлгайда в Telegram.

После загрузки оркестратор сохранит стайлгайд и будет **автоматически использовать его при каждом ревью**.

## Модель оркестратора

OpenClaw использует модель для классификации входящих сообщений и роутинга к агентам.

**Текущая модель:** `moonshotai/kimi-k2.6` (OpenRouter)

### Альтернативные модели

Чтобы изменить модель, отредактируйте файл `openclaw/openclaw.json`:

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "openrouter/moonshotai/kimi-k2.6"
      }
    }
  }
}
```

## Переменные окружения

| Переменная | Обязательная | Описание |
|------------|:------------:|---------|
| `TELEGRAM_BOT_TOKEN` | Да | Токен бота из @BotFather |
| `OPENROUTER_API_KEY` | Да | API-ключ OpenRouter |
| `LLM_MODEL_NAME` | Да | Модель OpenRouter (default: `moonshotai/kimi-k2.6`) |
| `FIGMA_TOKEN` | Нет | Figma Personal Access Token (Settings → Security) |
| `GITHUB_TOKEN` | Нет | GitHub PAT для получения коммитов |
| `JIRA_EMAIL` | Нет | Email аккаунта Jira |
| `JIRA_API_TOKEN` | Нет | Jira API token (id.atlassian.com → Security) |
| `WHISPER_MODEL_NAME` | Нет | `tiny`/`base`/`small`/`medium`/`large-v3` (default: `base`) |
| `WHISPER_DEVICE` | Нет | `auto`/`cpu`/`cuda` (default: `auto`) |

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

Каждый сервис содержит `app/` (Python), `prompts/` (системный промпт где есть), `requirements.txt`, `Dockerfile`, `.env.example`.

## Примеры использования

### 1. Создать инструкцию по установке Docker

**Отправьте боту:**

```
Нужна инструкция по установке Docker на Ubuntu 22.04.
Требования: Ubuntu 22.04, минимум 2GB RAM
```

**Бот вернет:** Структурированную инструкцию с шагами, требованиями и проверкой

### 2. Проверить инструкцию по стайлгайду

**Сначала отправьте стайлгайд:**

```
Это стайлгайд:
- Используй повелительное наклонение
- Укажи требования в начале
- Добавь команды проверки в конец
```

**Затем отправьте инструкцию на проверку:**

```
Проверь эту инструкцию:

1. Скачай файл
2. Распакуй его
3. Запусти setup.exe
4. Готово!
```

**Бот вернет:** Подробный отчет с замечаниями по стайлгайду

### 3. Генерировать API документацию

**Отправьте боту:**

```
Опиши API:
- GET /api/users/{id} — получить пользователя
- POST /api/users — создать пользователя
- Параметры: id (number), name (string), email (string)
```

**Бот вернет:** Структурированную API документацию в Markdown

## Устранение неполадок

### Бот не отвечает

1. Проверьте логи OpenClaw:

```bash
docker compose logs openclaw --tail=50
```

2. Убедитесь, что пейринг пройден (`openclaw pairing approve telegram <КОД>`)

3. Убедитесь, что все агенты работают:

```bash
curl http://localhost:8001/health
curl http://localhost:8006/health
```

### Бот отвечает на английском

Используйте модель, которая поддерживает русский язык — эти модели можно найти на https://openrouter.ai/

### Ошибка "No endpoints found for <модель>"

Модель не существует на OpenRouter. Проверьте список доступных моделей на https://openrouter.ai/

### Агент недоступен

Перезагрузите контейнеры:
```bash
docker compose restart
```

## Развертывание

Для развертывания на сервере используйте Docker Compose с переменными окружения:

```bash
TELEGRAM_BOT_TOKEN=... \
OPENROUTER_API_KEY=... \
docker compose up -d
```

Бот будет доступен в Telegram как `@openclaw_techwriting_bot` (или название вашего бота)
