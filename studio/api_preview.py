"""Reading things without changing anything: clip rules, a look ahead at frames, who is live, and the schedule text.

This is the doorway in front of four modules that only ever look:

    GET  /api/rules                 what may be clipped for a channel, as a badge
    POST /api/jobs/{jid}/peek       a handful of frames from each clip, to see a pick before rendering it
    GET  /api/hunt/live             one streamer, live or not
    GET  /api/hunt/watching         the whole watch list
    POST /api/hunt/watch            add someone to the watch list
    POST /api/hunt/unwatch          take someone off it
    GET  /api/schedule/preview      the scheduler command for a platform and times, as text to paste
    GET  /api/schedule/round        the scheduler command that runs one Improve round by itself, as text to paste

Nothing here installs a scheduler, starts a thread, or recurses into a site. `autopilot.install` exists but is
never reached from this file: a person pastes the printed command themselves, which keeps one server from
rewriting another machine's crontab behind their back.

`api_brand` and `api_text` read the signed-in person off the request; this file does the same, for the same
reason - `server.py` imports this module to mount the router, so importing `server.py` back would cycle."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool

from . import autopilot, hunt, jobs, peek, rules, schedule_ai

router = APIRouter()


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


# ---------------------------------------------------------------- the rules
@router.get("/api/rules")
def rules_lookup(platform: str = Query("", max_length=40), handle: str = Query("", max_length=120)):
    """Whether this channel may be clipped, with the source it came from. Never raises for an unknown channel."""
    try:
        info = rules.lookup(platform, handle)
    except Exception:  # noqa: BLE001 - a broken rules file must not break the page
        info = None
    if not info:
        return {"rule": "unknown", "note": "No rule on file for this channel. Ask them, or clip and take it down if they object.",
                "source": "", "label": "Unknown", "handle": handle, "platform": platform}
    try:
        return dict(info, **rules.badge(info, handle))
    except Exception:  # noqa: BLE001
        return info


# ---------------------------------------------------------------- a look ahead
@router.post("/api/jobs/{jid}/peek")
def peek_clip(request: Request, jid: str, cid: str = Query("", max_length=64), body: dict = Body(default={})):
    """A few still frames from each chosen clip, so a person can see a pick before spending a render on it."""
    _uid(request)
    job = jobs.get(jid)
    if not job:
        raise HTTPException(404, "No such video.")
    clips = list(job.get("clips") or [])
    if cid:
        clips = [c for c in clips if str(c.get("id")) == str(cid)]
        if not clips:
            raise HTTPException(404, "No such clip in this job.")
    if not clips:
        raise HTTPException(400, "There are no clips to look at yet.")
    made, changed = [], False
    for c in clips[:12]:
        try:
            got = peek.make(job, c)
        except Exception as e:  # noqa: BLE001 - ffmpeg missing, a source gone, a bad clip
            made.append({"id": c.get("id"), "error": str(e) or "Could not take a look."})
            continue
        if isinstance(got, dict) and got.get("peek"):
            # The strip is written beside the clip; these keys are what the GET below then serves. Without them
            # the picture exists on disk and the page still gets a 404, which looks exactly like a broken feature.
            c.update(got)
            changed = True
            made.append({"id": c.get("id"), **got})
        else:
            made.append({"id": c.get("id"), "error": "No frames came back for this clip."})
    worse = [m for m in made if isinstance(m, dict) and m.get("error")]
    if len(worse) == len(made):
        raise HTTPException(400, "Could not take a look: %s" % worse[0]["error"])
    if changed:
        jobs.save(job)
    return {"ok": True, "frames": made}


@router.get("/api/jobs/{jid}/peek/{cid}")
def peek_frame(request: Request, jid: str, cid: str):
    """One clip's strip as a jpg, straight into the page."""
    _uid(request)
    job = jobs.get(jid)
    if not job:
        raise HTTPException(404, "No such video.")
    clip = next((c for c in (job.get("clips") or []) if str(c.get("id")) == str(cid)), None)
    if not clip:
        raise HTTPException(404, "No such clip in this job.")
    try:
        raw = peek.strip_bytes(job, clip)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, "Could not take a look: %s" % e)
    if not raw:
        raise HTTPException(404, "Nothing to look at yet.")
    from fastapi.responses import Response
    return Response(content=raw, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=60"})


# ---------------------------------------------------------------- who is live
@router.get("/api/hunt/live")
def hunt_live(platform: str = Query(..., max_length=20), ident: str = Query(..., max_length=120)):
    """Is this streamer on air right now, with what they are playing and how many are watching."""
    try:
        info = hunt.look(platform, ident)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, "Could not ask %s: %s" % (platform, e))
    if not info:
        return {"live": False, "platform": platform, "ident": ident,
                "note": "Not on air, or the platform would not say."}
    return info


@router.get("/api/hunt/watching")
def hunt_watching():
    """The watch list, each with the last thing known about it."""
    try:
        return {"watching": hunt.watching()}
    except Exception:  # noqa: BLE001
        return {"watching": []}


@router.post("/api/hunt/watch")
def hunt_watch(request: Request, body: dict = Body(...)):
    """Add someone to the watch list. Their handle is cleaned, never kept as a path."""
    _uid(request)
    platform = str(body.get("platform") or "").strip()
    ident = str(body.get("ident") or body.get("handle") or "").strip()
    if not platform or not ident:
        raise HTTPException(400, "Name a platform and a channel.")
    try:
        return hunt.watch(platform, ident, str(body.get("name") or ""))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, "Could not add that channel: %s" % e)


@router.post("/api/hunt/unwatch")
def hunt_unwatch(request: Request, body: dict = Body(...)):
    """Take someone off it."""
    _uid(request)
    platform = str(body.get("platform") or "").strip()
    ident = str(body.get("ident") or body.get("handle") or "").strip()
    if not platform or not ident:
        raise HTTPException(400, "Name a platform and a channel.")
    try:
        gone = bool(hunt.unwatch(platform, ident))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, "Could not remove that channel: %s" % e)
    return {"ok": gone, "removed": gone}


# ---------------------------------------------------------------- the schedule, as text
@router.get("/api/schedule/preview")
def schedule_preview(times: str = Query("", max_length=200), os: str = Query("", max_length=20),
                     command: Optional[str] = Query(None, max_length=400)):
    """The scheduler command for these times, as text for the person to paste. Nothing is installed here.

    `os` is which scheduler to write for - windows, macos or linux. Left out, it is this machine. It is not the
    streaming platform: autopilot writes an operating-system task, and the platform is already in the command."""
    when = [t.strip() for t in str(times or "").split(",") if t.strip()][:12]
    try:
        text = autopilot.preview(os or None, when, command or "")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, "Could not work out a schedule: %s" % e)
    bad = "unknown platform" in text
    return {"ok": not bad, "preview": text, "times": when, "os": os or "this machine",
            "note": "Copy this and run it yourself. PeakCut does not touch your scheduler."}


@router.get("/api/schedule/round")
def schedule_round(request: Request, times: str = Query("", max_length=200)):
    """The scheduler command that runs one Improve round by itself, as text for the person to paste.

    This is a schedule of its own, with its own task name and its own crontab marker, so it can sit beside the
    clips tick without either removing the other. Nothing is installed here.

    The command has to name the owner, because a round reads that person's numbers and a scheduled task has no
    signed-in visitor. That is why the payload sets the id first and only then calls the round."""
    me = _me(request)
    when = [t.strip() for t in str(times or "").split(",") if t.strip()][:12] or None
    # A time that is not a clock time used to be dropped without a word, and a list with nothing usable left in
    # it became the built-in 06:00 while the answer still said ok. The person asked for a time: say which one
    # could not be read.
    wrong = [t for t in (when or []) if not autopilot._clock(t)]
    if wrong:
        raise HTTPException(400, "%s is not a clock time. Write hours and minutes like 06:00, separated by commas."
                            % ", ".join('"%s"' % t[:20] for t in wrong[:3]))
    try:
        plan = schedule_ai.spec(_uid(request), when) if when else schedule_ai.spec(_uid(request))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, "Could not work out the Improve round schedule: %s" % e)
    if not plan.get("ok"):
        raise HTTPException(400, str(plan.get("error") or "Could not work out the Improve round schedule."))
    return {"ok": True, "preview": str(plan.get("text") or ""), "times": plan.get("times") or [],
            "os": plan.get("platform") or "this machine", "label": plan.get("label") or "",
            "owner": getattr(me, "id", "") or _uid(request),
            "note": "Copy this and run it yourself. PeakCut does not touch your scheduler."}
