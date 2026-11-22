"""The Improve history as one readable report, served from the rounds already recorded.

    GET /api/learn/report    the rounds as shaped rows, one story paragraph, and a table

The words come from `studio/learn_report.py`, the module that turns a round record into a fixed shape,
so this route adds nothing but the real data: `studio/learn.py` holds the rounds, and what it has not
recorded is answered honestly rather than padded. Nothing here calls the AI or changes a setting.

It deliberately does not import `server.py`, for the same circular-import reason as every other `api_` module.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from . import auth, learn, learn_report

router = APIRouter()


def _me(request: Request):
    """The signed-in person for this request, exactly as `server._me` would return them."""
    u = getattr(request.state, "user", None)
    if u is None:
        u = auth.local_user()
    if getattr(u, "disabled", False):
        raise HTTPException(403, "This account is switched off.")
    return u


def _throttle(key: str, limit: int, window: int, msg: str) -> None:
    """The same rate limit `server._throttle` applies, without importing server.py."""
    try:
        auth.throttle(key, limit, window)
    except Exception:  # noqa: BLE001 - a limiter that cannot read its store must not block a read-only page
        pass


@router.get("/api/learn/report")
def learn_report_route(request: Request, limit: int = 20) -> dict:
    """The full Improve report: every round shaped, one paragraph each, and a table."""
    u = _me(request)
    _throttle("lrep:" + u.id, 40, 60, "That is a lot of report readings at once. Give it a moment.")
    try:
        take = max(1, min(int(limit or 20), 100))
    except (TypeError, ValueError):
        take = 20
    data = learn.log()
    rounds = data.get("rounds") if isinstance(data.get("rounds"), list) else []
    rows = []
    for i, raw in enumerate(rounds[-take:]):
        prev = rounds[i - 1] if i > 0 else None
        rows.append(learn_report.shape(raw, prev))
    rows.reverse()          # newest first, like every other list on the Improve page
    stories = [learn_report.story(r) for r in rounds[-take:]]
    stories.reverse()
    return {"ok": True, "rounds": rows, "count": len(rows),
            "stories": stories, "table": learn_report.table(rounds),
            "note": "" if rounds else "No Improve round has run yet, so there is nothing to report."}
