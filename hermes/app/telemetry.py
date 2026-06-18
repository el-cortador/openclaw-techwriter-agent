from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from app import config

logger = logging.getLogger(__name__)


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id BIGSERIAL PRIMARY KEY,
    project_slug TEXT NOT NULL,
    source TEXT NOT NULL,
    external_session_id TEXT NOT NULL,
    guild_id TEXT,
    channel_id TEXT,
    user_id TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (project_slug, source, external_session_id)
);

CREATE TABLE IF NOT EXISTS runs (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    project_slug TEXT NOT NULL,
    source TEXT NOT NULL,
    route_kind TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    model_name TEXT,
    provider TEXT,
    temperature DOUBLE PRECISION,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    duration_ms INTEGER,
    input_chars INTEGER NOT NULL DEFAULT 0,
    output_chars INTEGER NOT NULL DEFAULT 0,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    total_cost_usd NUMERIC(12, 6) NOT NULL DEFAULT 0,
    error_code TEXT,
    error_message TEXT,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS llm_calls (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    project_slug TEXT NOT NULL,
    provider TEXT,
    model_name TEXT,
    request_started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    response_finished_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    latency_ms INTEGER,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    cost_input_usd NUMERIC(12, 6) NOT NULL DEFAULT 0,
    cost_output_usd NUMERIC(12, 6) NOT NULL DEFAULT 0,
    cost_total_usd NUMERIC(12, 6) NOT NULL DEFAULT 0,
    raw_response_id TEXT,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS attachments (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    content_type TEXT,
    size_bytes BIGINT,
    storage_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES runs(id) ON DELETE CASCADE,
    project_slug TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_project_source ON sessions(project_slug, source);
CREATE INDEX IF NOT EXISTS idx_runs_project_started ON runs(project_slug, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_session_started ON runs(session_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_llm_calls_run_id ON llm_calls(run_id);
CREATE INDEX IF NOT EXISTS idx_events_run_id ON events(run_id, created_at DESC);
"""


def is_enabled() -> bool:
    return bool(config.DATABASE_URL)


def initialize() -> None:
    if not is_enabled():
        logger.warning("Telemetry database disabled: DATABASE_URL is not set")
        return
    last_error: Exception | None = None
    for attempt in range(10):
        try:
            with _connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(SCHEMA_SQL)
                conn.commit()
            return
        except Exception as exc:
            last_error = exc
            logger.warning("Telemetry init failed on attempt %s/10: %s", attempt + 1, exc)
            time.sleep(2)
    raise RuntimeError("Failed to initialize telemetry database") from last_error


@dataclass(frozen=True)
class SessionHandle:
    id: int
    external_session_id: str


@dataclass(frozen=True)
class RunHandle:
    id: int
    session_id: int
    started_at: datetime


def ensure_session(
    *,
    source: str,
    external_session_id: str,
    guild_id: str | None,
    channel_id: str | None,
    user_id: str | None,
    metadata: dict[str, Any] | None = None,
) -> SessionHandle | None:
    if not is_enabled():
        return None
    dict_row = _dict_row()
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO sessions (
                    project_slug,
                    source,
                    external_session_id,
                    guild_id,
                    channel_id,
                    user_id,
                    metadata_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (project_slug, source, external_session_id)
                DO UPDATE SET
                    guild_id = EXCLUDED.guild_id,
                    channel_id = EXCLUDED.channel_id,
                    user_id = EXCLUDED.user_id,
                    last_activity_at = NOW(),
                    metadata_json = sessions.metadata_json || EXCLUDED.metadata_json
                RETURNING id, external_session_id
                """,
                (
                    config.PROJECT_SLUG,
                    source,
                    external_session_id,
                    guild_id,
                    channel_id,
                    user_id,
                    _to_json(metadata or {}),
                ),
            )
            row = cur.fetchone()
        conn.commit()
    return SessionHandle(id=row["id"], external_session_id=row["external_session_id"])


def start_run(
    *,
    session_id: int,
    source: str,
    route_kind: str,
    model_name: str,
    provider: str,
    temperature: float,
    input_chars: int,
    metadata: dict[str, Any] | None = None,
) -> RunHandle | None:
    if not is_enabled():
        return None
    dict_row = _dict_row()
    with _connect() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO runs (
                    session_id,
                    project_slug,
                    source,
                    route_kind,
                    model_name,
                    provider,
                    temperature,
                    input_chars,
                    metadata_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                RETURNING id, session_id, started_at
                """,
                (
                    session_id,
                    config.PROJECT_SLUG,
                    source,
                    route_kind,
                    model_name,
                    provider,
                    temperature,
                    input_chars,
                    _to_json(metadata or {}),
                ),
            )
            row = cur.fetchone()
        conn.commit()
    return RunHandle(id=row["id"], session_id=row["session_id"], started_at=row["started_at"])


def add_attachment(
    run_id: int,
    *,
    filename: str,
    content_type: str | None,
    path: Path,
) -> None:
    if not is_enabled():
        return
    size_bytes = path.stat().st_size if path.exists() else None
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO attachments (run_id, filename, content_type, size_bytes, storage_path)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (run_id, filename, content_type, size_bytes, str(path)),
            )
        conn.commit()


def record_event(run_id: int | None, event_type: str, payload: dict[str, Any] | None = None) -> None:
    if not is_enabled():
        return
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO events (run_id, project_slug, event_type, payload_json)
                VALUES (%s, %s, %s, %s::jsonb)
                """,
                (run_id, config.PROJECT_SLUG, event_type, _to_json(payload or {})),
            )
        conn.commit()


def complete_run(
    run_id: int,
    *,
    started_at: datetime,
    output_chars: int,
    status: str,
    error_message: str | None = None,
) -> None:
    if not is_enabled():
        return
    finished_at = _utcnow()
    duration_ms = int((finished_at - started_at).total_seconds() * 1000)
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE runs
                SET finished_at = %s,
                    duration_ms = %s,
                    output_chars = %s,
                    status = %s,
                    error_message = %s
                WHERE id = %s
                """,
                (finished_at, duration_ms, output_chars, status, error_message, run_id),
            )
            cur.execute(
                """
                UPDATE sessions
                SET last_activity_at = NOW()
                WHERE id = (SELECT session_id FROM runs WHERE id = %s)
                """,
                (run_id,),
            )
        conn.commit()


def record_llm_call(
    run_id: int,
    *,
    provider: str,
    model_name: str,
    started_at: float,
    finished_at: float,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    raw_response_id: str | None,
    input_rate_per_million: Decimal | None = None,
    output_rate_per_million: Decimal | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    if not is_enabled():
        return
    input_cost = _cost_for_tokens(prompt_tokens, input_rate_per_million or config.LLM_COST_INPUT_PER_1M)
    output_cost = _cost_for_tokens(completion_tokens, output_rate_per_million or config.LLM_COST_OUTPUT_PER_1M)
    total_cost = input_cost + output_cost
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO llm_calls (
                    run_id,
                    project_slug,
                    provider,
                    model_name,
                    request_started_at,
                    response_finished_at,
                    latency_ms,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    cost_input_usd,
                    cost_output_usd,
                    cost_total_usd,
                    raw_response_id,
                    metadata_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    run_id,
                    config.PROJECT_SLUG,
                    provider,
                    model_name,
                    datetime.fromtimestamp(started_at, tz=timezone.utc),
                    datetime.fromtimestamp(finished_at, tz=timezone.utc),
                    int((finished_at - started_at) * 1000),
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    input_cost,
                    output_cost,
                    total_cost,
                    raw_response_id,
                    _to_json(metadata or {}),
                ),
            )
            cur.execute(
                """
                UPDATE runs
                SET input_tokens = runs.input_tokens + %s,
                    output_tokens = runs.output_tokens + %s,
                    total_tokens = runs.total_tokens + %s,
                    total_cost_usd = runs.total_cost_usd + %s
                WHERE id = %s
                """,
                (prompt_tokens, completion_tokens, total_tokens, total_cost, run_id),
            )
        conn.commit()


def _connect():
    from psycopg import connect

    return connect(config.DATABASE_URL)


def _dict_row():
    from psycopg.rows import dict_row

    return dict_row


def _to_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, default=str)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _cost_for_tokens(tokens: int, rate_per_million: Decimal) -> Decimal:
    if not tokens or not rate_per_million:
        return Decimal("0")
    amount = (Decimal(tokens) / Decimal(1_000_000)) * rate_per_million
    return amount.quantize(Decimal("0.000001"))
