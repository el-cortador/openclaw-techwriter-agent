# OpenClaw Techwriter Agent

Telegram-бот на базе [OpenClaw](https://docs.openclaw.ai/) для задач технического писателя. Бот принимает сообщения и файлы в Telegram, определяет тип задачи и передает ее одному из специализированных сервисов: генератору документации, release notes, changelog, API-документации, транскрипций или ревью текста.

## Возможности

| Что отправить боту                                                     | Что вернет бот                            |
|------------------------------------------------------------------------|-------------------------------------------|
| Текстовую постановку, требования или описание фичи                     | Черновик технической документации         |
| Скриншот UI-макета в `.png`, `.jpg`, `.jpeg`, `.webp`                  | User guide по видимому интерфейсу         |
| Ссылку `figma.com/file/...` или `figma.com/design/...`                 | Просьбу отправить скриншот нужного экрана |
| Аудио- или видеофайл в `.mp3`, `.wav`, `.mp4`, `.ogg`, `.m4a`, `.webm` | Текст транскрибированного видео           |
| Публичную ссылку на аудио или видео в облаке                           | Транскрипт и саммари                      |
| `release notes` + GitHub-репозиторий + диапазон дат                    | Только release notes                      |
| `release notes` + ссылки на Jira-задачи                                | Только release notes                      |
| `changelog` + GitHub-репозиторий + диапазон дат                        | Только changelog                          |
| `changelog` + ссылки на Jira-задачи                                    | Только changelog                          |
| Описание API или эндпоинтов                                            | Черновик API-документации                 |
| Текст документации со словом «проверь»                                 | Отчет по ревью                            |

## Архитектура

```text
Telegram -> OpenClaw (оркестратор)
                |
    ------------+----------------
    |           |               |
 :8001       :8004           :8006
spec2doc  release-notes    reviewer
```

| Сервис                | Порт | Назначение                                                                                                |
|-----------------------|------|-----------------------------------------------------------------------------------------------------------|
| `agent-spec2doc`      | 8001 | Создает черновик технической документации из постановки                                                   |
| `agent-figma`         | 8002 | Создает черновик пользовательской инструкции на основе UI-макета из Figma                                 |
| `agent-transcribe`    | 8003 | Расшифровывает аудио и видео, формирует транскрипт и саммари                                              |
| `agent-release-notes` | 8004 | Создает release notes или changelog из GitHub-коммитов или Jira-задач                                     |
| `agent-api-docs`      | 8005 | Создает API-документацию из описания эндпоинтов                                                           |
| `agent-reviewer`      | 8006 | Проверяет текст документации по стайлгайду                                                                |

OpenClaw выступает оркестратором: классифицирует входящее сообщение, вызывает нужный HTTP-сервис и возвращает пользователю итоговый результат. Технические статусы выполнения, названия внутренних процессов и служебные URL не должны отправляться в Telegram-чат.

## Требования

- Docker и Docker Compose v2.
- Токен Telegram-бота из [@BotFather](https://t.me/BotFather).
- API-ключ [OpenRouter](https://openrouter.ai/keys).
- Для Jira-сценариев: email аккаунта Jira и Jira API token.
- Для GitHub-сценариев: GitHub token, если требуется доступ к приватным репозиториям или повышенный лимит API.

## Установка

### 1. Клонируйте репозиторий

```bash
git clone <repo-url>
cd openclaw-techwriter-agent
```

### 2. Создайте `.env`

```bash
cp .env.example .env
```

Откройте `.env` и заполните переменные окружения.

Минимальный набор:

```env
TELEGRAM_BOT_TOKEN=...
OPENROUTER_API_KEY=...
LLM_MODEL_NAME=moonshotai/kimi-k2.6
```

Дополнительные переменные:

```env
GITHUB_TOKEN=...
JIRA_EMAIL=...
JIRA_API_TOKEN=...
FIGMA_TOKEN=...
WHISPER_MODEL_NAME=base
WHISPER_DEVICE=auto
```

`FIGMA_TOKEN` оставлен для экспериментального `agent-figma`. Основной поддерживаемый Figma-сценарий сейчас работает через скриншот макета, поэтому токен Figma для него не нужен.

### 3. Запустите сервисы

```bash
docker compose up --build
```

Первый запуск может занять несколько минут: Docker соберет образы, а сервис транскрибации при необходимости загрузит Whisper-модель.

### 4. Подтвердите pairing с Telegram

Отправьте любое сообщение боту. Если бот ответит `Pairing code: ...`, выполните:

```bash
docker compose exec -T openclaw openclaw pairing approve telegram <КОД>
```

Пример:

```bash
docker compose exec -T openclaw openclaw pairing approve telegram JY79369S
```

После подтверждения pairing бот будет готов к работе.

## Проверка

Проверьте health endpoints сервисов:

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
curl http://localhost:8005/health
curl http://localhost:8006/health
```

Проверьте логи OpenClaw:

```bash
docker compose logs openclaw --tail=50
```

Проверьте состояние контейнеров:

```bash
docker compose ps
```

## Использование

Отправьте боту сообщение в Telegram. Оркестратор сам определит тип задачи и вызовет нужный сервис.

### Постановка -> документация

Отправьте файл постановки или требований:

```text
Нужна инструкция на основе этой постановки.
```

Бот вернет структурированный черновик документации.

### Figma и UI-скриншоты

> Прямая обработка Figma-ссылок отключена как основной сценарий. Если отправить ссылку `figma.com/...`, бот попросит прислать скриншот нужного экрана или фрейма.

Поддерживаемый сценарий:

1. Откройте нужный экран или фрейм в Figma.
2. Сделайте скриншот.
3. Отправьте изображение боту.
4. Бот составит user guide по видимым элементам интерфейса.

Бот не должен придумывать скрытые функции, которых нет на изображении. Если на скриншоте плохо читается текст или видна только часть интерфейса, результат должен учитывать это ограничение.

### Release notes и changelog

Для release notes и changelog используйте явные слова в запросе:

- `release notes`, `релиз-ноты`, `релизные заметки` -> только release notes.
- `changelog`, `change log`, `журнал изменений` -> только changelog.

Если нужны release notes/changelog по GitHub-репозиторию:

```text
Сделай release notes/changelog по https://github.com/owner/repo за период с 01.01.2026 по 31.01.2026.
```

Если нужны release notes/changelog по нескольким задачам из Jira, отправьте ссылки на задачи:

```text
Сделай release notes/changelog по задачам:
https://example.atlassian.net/browse/PROJ-123
https://example.atlassian.net/browse/PROJ-124
```

`agent-release-notes` читает Jira-задачи через REST API `/rest/api/3/issue/{KEY}` и передает в модель:

- summary;
- description;
- issue type;
- status;
- labels;
- components;
- fix versions.

Для доступа к Jira заполните `JIRA_EMAIL` и `JIRA_API_TOKEN`. У аккаунта должны быть права на просмотр указанных задач. Если Jira вернет 401, 403 или 404, бот должен показать точную ошибку сервиса.

### Транскрибация аудио и видео

> Ограничения при работе с этим агентом:
> - размер видео/аудио — не более 50 МБ;
> - поддерживаются только форматы mp4;
> - можно отправлять файл как напрямую в Telegram, так и в виде публичной ссылки на Google Drive.

Транскрибация может занимать несколько минут. Бот не должен отправлять промежуточные технические статусы вроде `Sifting...`, `Exec`, `Process` или названия внутренних process-сессий.

### API-документация

Отправьте описание API или спецификацию в формате JSON/YAML:

```text
Опиши API:
- GET /api/users/{id} — получить пользователя
- POST /api/users — создать пользователя
- Параметры: id (number), name (string), email (string)
```

Бот вернет черновик API-документации в Markdown.

### Ревью документации

Чтобы сохранить стайлгайд, отправьте его текстом:

```text
Это стайлгайд:
- Используйте повелительное наклонение.
- Указывайте требования в начале.
- Добавляйте команды проверки в конец.
```

Или загрузите `.md`-файл со стайлгайдом.

После этого отправьте текст на проверку:

```text
Проверь эту инструкцию:

1. Скачайте файл.
2. Распакуйте архив.
3. Запустите setup.exe.
```

Бот вернет отчет с замечаниями по стайлгайду.

## Модель

OpenClaw использует модель для классификации входящих сообщений и роутинга.

Текущая модель оркестратора:

```text
openrouter/moonshotai/kimi-k2.6
```

Модель задается в `openclaw/openclaw.json`:

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

| Переменная           | Обязательная | Описание                                                                    |
|----------------------|--------------|-----------------------------------------------------------------------------|
| `TELEGRAM_BOT_TOKEN` | Да           | Токен Telegram-бота из @BotFather                                           |
| `OPENROUTER_API_KEY` | Да           | API-ключ OpenRouter                                                         |
| `LLM_MODEL_NAME`     | Да           | Модель для специализированных сервисов, по умолчанию `moonshotai/kimi-k2.6` |
| `GITHUB_TOKEN`       | Нет          | GitHub token для получения коммитов                                         |
| `JIRA_EMAIL`         | Нет          | Email аккаунта Jira                                                         |
| `JIRA_API_TOKEN`     | Нет          | Jira API token                                                              |
| `FIGMA_TOKEN`        | Нет          | Figma Personal Access Token для экспериментального `agent-figma`            |
| `WHISPER_MODEL_NAME` | Нет          | Whisper-модель: `tiny`, `base`, `small`, `medium`, `large-v3`               |
| `WHISPER_DEVICE`     | Нет          | Устройство для Whisper: `auto`, `cpu`, `cuda`                               |

## Структура проекта

```text
.
├── docker-compose.yml
├── .env.example
├── openclaw/
│   ├── openclaw.json
│   └── workspace/
│       ├── AGENTS.md
│       └── SOUL.md
├── agent-spec2doc/
├── agent-figma/
├── agent-transcribe/
├── agent-release-notes/
├── agent-api-docs/
└── agent-reviewer/
```

Каждый сервис содержит приложение в `app/`, `requirements.txt`, `Dockerfile` и, при необходимости, дополнительные промпты или настройки.

## Логи

Посмотреть логи OpenClaw:

```bash
docker compose logs openclaw --tail=100
```

Посмотреть логи сервиса release notes:

```bash
docker compose logs agent-release-notes --tail=100
```

В обычном режиме `agent-release-notes` пишет краткую сводку по Jira-запросу и итог LLM-генерации. Подробные строки по каждой Jira-задаче переведены в `DEBUG`, чтобы не засорять логи.

## Устранение неполадок

### Бот не отвечает

Проверьте состояние контейнеров:

```bash
docker compose ps
```

Проверьте логи OpenClaw:

```bash
docker compose logs openclaw --tail=50
```

Убедитесь, что pairing с Telegram выполнен:

```bash
docker compose exec -T openclaw openclaw pairing approve telegram <КОД>
```

Проверьте health endpoints сервисов:

```bash
curl http://localhost:8001/health
curl http://localhost:8004/health
curl http://localhost:8006/health
```

### Бот отвечает после пробуждения ПК

Если проект запущен локально на рабочем ПК, бот доступен только пока компьютер не находится в спящем режиме. Когда Windows засыпает, Docker Desktop, контейнеры и сетевые подключения приостанавливаются. Telegram продолжает принимать сообщения, но OpenClaw обработает их только после пробуждения и разблокировки ПК.

Для стабильной доступности используйте один из вариантов:

- отключите спящий режим на компьютере, где запущен Docker;
- оставьте питание и сеть включенными во время простоя;
- перенесите проект на постоянно включенный хост: VPS, домашний сервер, NAS или отдельную машину без сна.

### Jira-задачи не читаются

Проверьте:

- заполнены ли `JIRA_EMAIL` и `JIRA_API_TOKEN`;
- есть ли у аккаунта доступ к указанным задачам;
- корректны ли ссылки на задачи;
- не возвращает ли Jira статусы 401, 403 или 404.

Посмотрите логи:

```bash
docker compose logs agent-release-notes --tail=100
```

### Сервис вернул пустой результат

Сервисы должны возвращать либо непустой `result`, либо понятный `error`. Если LLM вернула пустой ответ, сервис должен вернуть ошибку, а бот не должен самостоятельно сочинять документ вместо специализированного агента.

### Бот отвечает не тем стилем

Проверьте инструкции оркестратора:

```text
openclaw/workspace/AGENTS.md
openclaw/workspace/SOUL.md
```

После изменения этих файлов перезапустите OpenClaw:

```bash
docker compose restart openclaw
```

### Агент недоступен

Перезапустите контейнеры:

```bash
docker compose restart
```

Если изменяли код сервиса, пересоберите нужный контейнер:

```bash
docker compose build agent-release-notes
docker compose up -d agent-release-notes
```

## Развертывание

Для круглосуточной работы не запускайте бота на рабочем ПК, который может перейти в спящий режим. Разместите проект на постоянно включенном хосте: VPS, домашнем сервере, NAS или отдельной машине без сна.

На сервере выполните:

```bash
docker compose up -d --build
```

Проверьте статус:

```bash
docker compose ps
```

После запуска бот будет доступен в Telegram под именем, которое вы настроили через BotFather.