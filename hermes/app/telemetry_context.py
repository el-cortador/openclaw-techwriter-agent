from __future__ import annotations

from contextvars import ContextVar, Token


CURRENT_RUN_ID: ContextVar[int | None] = ContextVar("current_run_id", default=None)


def set_current_run_id(run_id: int | None) -> Token:
    return CURRENT_RUN_ID.set(run_id)


def reset_current_run_id(token: Token) -> None:
    CURRENT_RUN_ID.reset(token)


def get_current_run_id() -> int | None:
    return CURRENT_RUN_ID.get()
