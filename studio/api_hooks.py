"""How the hooks on real clips read, scored by the same rules the AI is given.

    GET /api/learn/hooks    every finished clip's hook, with a score and the reasons behind it

The scoring is `studio/hookscore.py`, the same checker the Improve engine uses when it suggests hook
words, so the page and the engine cannot disagree about what a good hook is. Nothing here invents a
number: a clip with no hook is listed with no score, and a folder with no finished clips answers with
an empty list and says so.

It deliberately does not import `server.py`, for the same circular-import reason as every other `api_` module.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from . import auth, hookscore, jobs, safe

router = APIRouter()

_LIMIT = 120          # clips scored per answer; the newest ones win
_THROTTLE = (40, 60, "That is a lot of hook readings at once. Give it a moment.")


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
    from . import auth as _auth
    try:
        _auth.throttle(key, limit, window)
    except Exception:  # noqa: BLE001 - a limiter that cannot read its store must not block a read-only page
        pass


@router.get("/api/learn/hooks")
def learn_hooks(request: Request, limit: int = 40) -> dict:
    """Score the hooks of finished clips, newest first, with the reasons spelled out."""
    u = _me(request)
    lim, win, msg = _THROTTLE
    _throttle("lhooks:" + u.id, lim, win, msg)
    try:
        take = max(1, min(int(limit or 40), _LIMIT))
    except (TypeError, ValueError):
        take = 40
    rows = []
    try:
        for job in jobs.list_jobs():
            for clip in job.get("clips", []):
                if str(clip.get("status") or "") != "done":
                    continue
                hook = str(clip.get("hook") or "").strip()
                if not hook:
                    continue
                got = hookscore.score(hook)
                rows.append({
                    "job": job.get("id", ""), "clip": clip.get("id", ""),
                    "hook": hook[:200],
                    "score": int(got.get("score", 0)),
                    "verdict": str(got.get("verdict", "")),
                    "reasons": [str(r) for r in (got.get("reasons") or [])][:4],
                    "title": str(clip.get("title") or "")[:120],
                })
                if len(rows) >= take:
                    break
            if len(rows) >= take:
                break
    except Exception as e:  # noqa: BLE001 - a broken job folder must not take the page down
        raise HTTPException(500, "The clips could not be read: " + safe.friendly(e))
    counts = {"strong": 0, "workable": 0, "weak": 0}
    for r in rows:
        v = r["verdict"] if r["verdict"] in counts else "weak"
        counts[v] += 1
    note = ""
    if not rows:
        note = "No finished clips with hooks yet, so there is nothing to score."
    return {"ok": True, "hooks": rows, "count": len(rows), "strong": counts["strong"],
            "workable": counts["workable"], "weak": counts["weak"], "note": note}
