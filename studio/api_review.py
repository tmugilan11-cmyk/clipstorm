"""The review-first queue: a finished clip waits for a yes or a no before it counts as ready to post.

    PATCH /api/jobs/{jid}/clips/{cid}   {"review": "approved"} or {"review": "rejected"} decides one clip
    GET   /api/jobs/{jid}/review        a job's finished clips, and how many still wait for a decision

A decision is remembered on the clip itself (`review`, `review_at`) and saved with the job, the same way every
other clip change is, so it survives a restart and travels with the clip wherever it is shown. `remaining`
counts the finished clips of the job that have no decision yet; it reaches zero when the whole job has been
gone through. `server.py` mounts this router like the other `api_*` ones.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Body, HTTPException, Request

from . import jobs

router = APIRouter()

DECISIONS = ("approved", "rejected")      # the only answers a review accepts


def _me(request: Request):
    """The signed-in person for this request, exactly as `server._me` would return them."""
    u = getattr(request.state, "user", None)
    if not u:
        raise HTTPException(401, "Sign in first.")
    return u


def _uid(request: Request) -> str:
    """The person's id as a plain string, which is what the data files are keyed by."""
    u = _me(request)
    return str(getattr(u, "uid", None) or getattr(u, "id", None) or getattr(u, "email", "") or "default")


def _now_iso() -> str:
    """The current moment as UTC ISO text, which is how clips remember when they were decided."""
    return datetime.now(timezone.utc).isoformat()


def _job_or_404(jid: str) -> dict:
    """The job, only when it belongs to whoever this code runs for."""
    job = jobs.get(jid)
    if not job:
        raise HTTPException(404, "No such video.")
    return job


def _clip_or_404(job: dict, cid: str) -> dict:
    """The one clip of the job, found by its id."""
    clip = next((c for c in (job.get("clips") or []) if str(c.get("id")) == str(cid)), None)
    if not clip:
        raise HTTPException(404, "No such clip in this job.")
    return clip


def _decided(clip: dict) -> bool:
    """Does this clip carry a decision a person actually made?"""
    return clip.get("review") in DECISIONS


def _remaining(job: dict) -> int:
    """How many finished clips of this job are still waiting for a yes or a no."""
    return sum(1 for c in (job.get("clips") or []) if c.get("status") == "done" and not _decided(c))


def _clip_view(clip: dict) -> dict:
    """What the browser may see of a clip: the same rule `jobs.public` applies, no server file paths."""
    return {k: v for k, v in clip.items() if k not in ("src", "fixed_words", "fixed_for")}


def _clip_len(clip: dict) -> float:
    """How long the clip runs, in seconds; a clip whose times cannot be read simply shows no length."""
    try:
        return round(float(clip.get("end")) - float(clip.get("start")), 2)
    except (TypeError, ValueError):
        return 0.0


def _review_line(clip: dict) -> dict:
    """One line of the review list: what the clip is, where its file is, and what was decided."""
    return {"id": clip.get("id"), "title": clip.get("title") or "", "hook": clip.get("hook") or "",
            "file": clip.get("file") or "", "duration": _clip_len(clip), "review": clip.get("review") or None}


# ---------------------------------------------------------------- the routes
@router.get("/api/jobs/{jid}/review")
def job_review(request: Request, jid: str):
    """A job's finished clips, each with its decision so far, and how many still wait for one."""
    _uid(request)
    job = _job_or_404(jid)
    clips = [_review_line(c) for c in (job.get("clips") or []) if c.get("status") == "done"]
    return {"clips": clips, "remaining": _remaining(job)}


@router.patch("/api/jobs/{jid}/clips/{cid}")
def decide_clip(request: Request, jid: str, cid: str, body: dict = Body(...)):
    """Decide one clip: keep it (approved) or drop it (rejected), and remember when that happened.

    Saying the same thing again is fine: the decision is simply stamped again, so a changed mind is one
    call away.
    """
    _uid(request)
    job = _job_or_404(jid)
    clip = _clip_or_404(job, cid)
    review = body.get("review")
    if review not in DECISIONS:
        raise HTTPException(400, "Choose approved or rejected.")
    clip["review"] = review
    clip["review_at"] = _now_iso()
    jobs.save(job)
    return {"ok": True, "clip": _clip_view(clip), "remaining": _remaining(job)}
