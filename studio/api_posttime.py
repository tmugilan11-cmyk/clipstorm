"""When to post, read from this account's own posting record.

    GET /api/posttime    the hours this account's posts did best, and the hour it should try next

Nothing here asks a service or invents a clock. The only input is the queue's own history
(`studio/posting.overview()`), which is also why the honest answer for a quiet account is
"Not enough posts yet" instead of a made-up best time.

The hours are named in UTC, and every label says so, because a bare clock time would be
read as the person's own local time and they would post hours early or late.

It deliberately does not import `server.py`, for the same circular-import reason as every other `api_` module.
"""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, HTTPException, Request

from . import auth, ctx, posting, safe

router = APIRouter()

_MIN_POSTS = 5          # below this there is no pattern worth naming
_TOP = 3                # hours to name


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


def hours_for(posts: list) -> dict:
    """The reading itself, separated from the route so a test can feed rows straight in.

    A row needs `posted_at` and a view count that is really a number; rows without both are skipped
    rather than counted as zeros, because a post with unknown views is not proof an hour was bad."""
    by_hour_views = defaultdict(list)
    by_hour_count = defaultdict(int)
    for p in posts:
        if not isinstance(p, dict):
            continue
        when = p.get("posted_at")
        views = p.get("views")
        if not isinstance(when, (int, float)) or when <= 0:
            continue
        try:
            views_n = float(views)
        except (TypeError, ValueError):
            continue
        if views_n != views_n or views_n in (float("inf"), float("-inf")):
            continue
        hour = int((when % 86400) // 3600)          # UTC hour of the post
        by_hour_views[hour].append(views_n)
        by_hour_count[hour] += 1
    if sum(by_hour_count.values()) < _MIN_POSTS:
        return {"enough": False, "best": [], "total": int(sum(by_hour_count.values())),
                "note": f"Not enough posts yet. PeakCut names no hour until there are {_MIN_POSTS} posts with view counts."}
    means = sorted(((sum(v) / len(v), h) for h, v in by_hour_views.items()), reverse=True)
    best = []
    for mean, hour in means[:_TOP]:
        n = len(by_hour_views[hour])
        best.append({"hour": hour, "label": f"{hour:02d}:00 UTC", "mean_views": round(mean, 1),
                     "posts": n,
                     "note": f"{_word(n)} averaged {round(mean)} views at {hour:02d}:00 UTC."})
    return {"enough": True, "best": best, "total": int(sum(by_hour_count.values())),
            "note": f"Read from {sum(by_hour_count.values())} posts with view counts. Hours are UTC. Small numbers can mislead."}


def _word(n: int) -> str:
    return "1 post" if n == 1 else f"{n} posts"


@router.get("/api/posttime")
def posttime_route(request: Request) -> dict:
    """The hours this account's own posts did best, or the honest not-yet."""
    u = _me(request)
    _throttle("ptm:" + u.id, 40, 60, "That is a lot of posting-time readings at once. Give it a moment.")
    try:
        with ctx.as_user(u.id):
            got = posting.overview()
    except Exception as e:  # noqa: BLE001 - one sentence, never a stack trace on a page
        raise HTTPException(500, "The posting record could not be read: " + safe.friendly(e))
    rows = got.get("posts") if isinstance(got.get("posts"), list) else []
    out = hours_for(rows)
    out["ok"] = True
    return out
