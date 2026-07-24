#Requires -Version 5.1
<#
.SYNOPSIS
  Подготавливает локальную установку techwriter-super-agent (Docker Compose).
.DESCRIPTION
  Идемпотентно: существующий .env и состояние не перезаписываются.
#>
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$RuntimeDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $RuntimeDir '..\..')).Path

if (-not (Test-Path (Join-Path $RepoRoot 'hermes\app\main.py'))) {
  throw "Скрипт должен находиться в runtimes\hermes\ репозитория techwriter-super-agent"
}

Write-Host "==> techwriter-super-agent install"

$docker = Get-Command docker -ErrorAction SilentlyContinue
if ($docker) {
  Write-Host "  [ok] docker найден"
} else {
  Write-Host "  [warn] docker не найден в PATH. Установите Docker Desktop перед запуском."
}

$EnvExample = Join-Path $RepoRoot '.env.example'
$EnvFile = Join-Path $RepoRoot '.env'
if (Test-Path $EnvFile) {
  Write-Host "  [skip] .env уже существует — не перезаписываю"
} else {
  Copy-Item $EnvExample $EnvFile
  Write-Host "  [ok] создан .env из .env.example"
}

$StateDir = Join-Path $RepoRoot 'hermes\state'
if (Test-Path $StateDir) {
  Write-Host "  [skip] hermes\state уже существует"
} else {
  New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
  Write-Host "  [ok] создан hermes\state"
}

Write-Host @"

Готово. Следующие шаги:
  1. Заполните секреты в .env (минимум DISCORD_BOT_TOKEN и OPENROUTER_API_KEY)
  2. docker compose up -d --build
  3. Откройте дашборд: http://127.0.0.1:4173
  4. Проверьте установку: runtimes\hermes\scripts\verify-install.ps1
"@
