from __future__ import annotations

from app.models import IncomingMessage, Route
from app.skills.runner import SkillError, run_route


class ServiceError(Exception):
    pass


async def call_route(route: Route, message: IncomingMessage) -> str:
    try:
        return await run_route(route, message)
    except SkillError as exc:
        raise ServiceError(str(exc)) from exc
