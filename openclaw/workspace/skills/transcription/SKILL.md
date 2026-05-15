---
name: transcription
description: Route audio and video transcription tasks to agent-transcribe. Use for Telegram audio/video attachments, .mp3, .mp4, .wav, .ogg, .m4a, .webm files, direct media URLs, cloud links, and requests to transcribe or расшифровать media.
---

# Transcription

## Файл

Если пользователь прислал аудио или видеофайл:

```bash
curl -s -X POST http://agent-transcribe:8003/transcribe \
  -F "file=@ПУТЬ_К_ФАЙЛУ"
```

## Ссылка

Если пользователь прислал http(s)-ссылку на аудио/видео или облачный файл:

```bash
curl -s -X POST http://agent-transcribe:8003/transcribe/url \
  -H "Content-Type: application/json" \
  -d '{"url": "ССЫЛКА_ИЗ_СООБЩЕНИЯ"}'
```

## Большие файлы

- Если Telegram/OpenClaw не смог скачать вложение из-за размера, попроси загрузить файл в облако и прислать публичную ссылку.
- Не устанавливай `yt-dlp`, `youtube-dl`, `pip`-пакеты и другие утилиты.
- Для Google Drive подходит публичная share-ссылка.
- Для Яндекс.Диска и других облаков лучше просить прямую публичную ссылку на скачивание.

## Ожидание

- Таймаут для `/transcribe` и `/transcribe/url` — не меньше 900 секунд.
- Если `exec` вернул активную process-сессию, продолжай ждать эту же сессию.
- Не запускай повторный запрос, пока первый ещё выполняется.
- Не называй процесс упавшим, пока команда или сервис реально не вернули ошибку.
