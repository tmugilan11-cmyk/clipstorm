"""The doorway to the improvement engine in `studio/learn.py`.

Three routes and no logic of their own: the sentence an operator reads, the round, the way back.

    GET  /api/learn/state   what has been changed, what the numbers said, whether a round may start
    POST /api/learn/run     one round: read the numbers, ask the AI, apply what is allowed
    POST /api/learn/undo    put the settings back to how they were before a round

Wave 3 added five more, for the parts of the engine that read deeper. Each of them imports its module
inside the route and answers with a sentence when that module is not on the build, so an older copy of
PeakCut still serves the page it has:

    GET    /api/learn/signals   where people stop watching, as sentences about the hook and the length
    GET    /api/learn/arms      the saved trial, or a plain answer that there is not one
    POST   /api/learn/arms      open a trial: two settings, each with the value it should try
    DELETE /api/learn/arms      forget the saved trial
    GET    /api/learn/cost      what today's rounds have used, and what is left

Every route answers with a sentence as well as data, because "nothing happened" is the answer
that most needs explaining.

It deliberately does not import `server.py`.
"""
from __future__ import annotations

import json
import os
import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from . import auth, config, ctx, learn

router = APIRouter()

# The same idea as `brand._file`: an id is turned into something that is only ever a file name.
_SAFE = re.compile(r"[^a-z0-9_-]+")


def _me(request: Request):
    """The signed-in person, exactly as `server._me` would return them."""
    u = getattr(request.state, "user", None)
    if not u or not getattr(u, "id", None):
        raise HTTPException(401, "Please sign in.")
    return u


def _throttle(uid: str, limit: int = 30, window: int = 60) -> None:
    """A round spends the operator's own AI budget, so it is rate limited like every other AI route."""
    try:
        auth.throttle("learn:" + uid, limit, window)
    except auth.AuthError:
        raise HTTPException(429, "That is a lot of rounds at once. Give it a moment.")


@router.get("/api/learn/state")
async def state(request: Request) -> dict:
    """Every round, newest first, plus whether another may start now and why not.

    An empty answer is a real answer: `rounds` empty and `why_not` a sentence naming what is missing."""
    u = _me(request)
    _throttle(u.id, limit=120)
    got = await run_in_threadpool(learn.log)
    if not got.get("why_not"):
        got["why_not"] = ("" if got.get("can_run") else
                          "PeakCut will run a round as soon as the AI is set up and the numbers are there.")
    got["settings"] = await run_in_threadpool(learn._current_settings, u.id)
    return got


@router.post("/api/learn/run")
async def run(request: Request) -> dict:
    """One round. Sending "dry": true answers what it would do without changing anything.

    The report always says whether anything was applied, because a round that could not read enough
    numbers still has to explain itself."""
    u = _me(request)
    _throttle(u.id, limit=20, window=60)
    body = {}
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001  - an empty body is the normal case
        body = {}
    if not isinstance(body, dict):
        raise HTTPException(400, "Send a JSON object, like {\"days\": 28}.")
    asked = body.get("days", 28)
    try:
        days = int(asked)
    except (TypeError, ValueError):
        days = None
    if days not in (7, 28, 90, 365):
        days = 28
    dry = body.get("dry") is True
    try:
        out = await run_in_threadpool(learn.run, days, dry)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:  # noqa: BLE001  - the reason is the answer
        raise HTTPException(400, "PeakCut could not finish the round: " + str(e)[:200])
    if not isinstance(out, dict):
        out = {"days": days}
    # A span the engine does not know was asked for: the answer carries "days": 28 either way, but a
    # note naming the fallback means nobody has to guess why 13 or 30 became 28.
    if asked not in (7, 28, 90, 365):
        out["note"] = ("PeakCut runs rounds over 7, 28, 90 or 365 days. The days value sent (%s) is "
                       "not one of those, so this round used the usual 28 days." % asked)
    return out


@router.post("/api/learn/undo")
async def undo(request: Request) -> dict:
    """Put the settings back to what they were before a round. Without "at", the newest round is undone."""
    u = _me(request)
    _throttle(u.id, limit=20)
    body = {}
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}
    if not isinstance(body, dict):
        raise HTTPException(400, "Send a JSON object, or leave \"at\" out to undo the newest round.")
    at = body.get("at")
    if at is not None and at != "":
        try:
            at = float(at)
        except (TypeError, ValueError):
            # A time was named but is not a time. Answering with the newest round instead would undo
            # something the person did not point at, so it is refused.
            raise HTTPException(400, "That is not a time PeakCut can read. Leave \"at\" out to undo the "
                                     "newest round.")
    else:
        at = None
    try:
        return await run_in_threadpool(learn.undo, at)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, "PeakCut could not undo that round: " + str(e)[:200])


# ---------------------------------------------------------------- wave 3
#
# Five routes that reach the new parts of the engine: the retention signals, a two arm trial, and what
# a round may spend. Each one imports its own module INSIDE the function. A build that has not shipped
# one of those files must still answer its page, so a missing module is a 200 with a sentence saying so
# and the empty shape, never a 500 and never a stack in the browser.

MISSING = "That part of PeakCut is not on this build yet."


def _trial_file(uid: str):
    """Where one person's trial lives.

    It is named the way `studio/brand.py` names its document: the signed-in id is cut down to letters,
    digits, a dash and an underscore before it is used, so the name can never be a path the client chose,
    and one person's trial can never land on another person's file."""
    safe = _SAFE.sub("_", str(uid or "").strip().lower())[:40] or "default"
    return config.DATA_DIR / ("arms_%s.json" % safe)


def _read_trial(uid: str) -> dict:
    """This person's saved trial, or `{"trial": null}` when there is none or it cannot be read.

    A trial that was hand edited into nonsense reads as no trial at all: an empty trial is a page that
    offers to start one, while a broken one would be a page that cannot draw."""
    try:
        got = json.loads(_trial_file(uid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"trial": None}
    trial = got.get("trial") if isinstance(got, dict) else None
    return {"trial": trial if isinstance(trial, dict) else None}


def _write_trial(uid: str, trial: dict | None) -> dict:
    """Save or remove the trial, the same way `studio/brand.py` writes its document.

    A temporary file is written first and then moved over the real one, so a reader never sees half a
    document. The file is made readable only by its owner. A save that fails still answers with the
    trial it was given, because losing the disk must not turn a good answer into an error page."""
    path = _trial_file(uid)
    try:
        if trial is None:
            path.unlink(missing_ok=True)
        else:
            config.DATA_DIR.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"trial": trial}, indent=2, sort_keys=True), encoding="utf-8")
            os.chmod(tmp, 0o600)
            os.replace(tmp, path)
    except OSError:
        pass
    return {"trial": trial}


@router.get("/api/learn/signals")
async def signals(request: Request, days: str = "28", video: str = "", seconds: str = "0") -> dict:
    """Where people stop watching one video, as sentences about the hook and the length.

    No channel, no curve, or a curve too short to read answers with empty sentences rather than an
    error, because a page that shows nothing is still a page that works.

    `days` and `seconds` arrive as text and are turned into numbers here on purpose. Typed as numbers,
    a stray character would be refused by the framework before this function ran, and a page that
    sends one bad value would get an error instead of the quiet answer it is built to draw."""
    u = _me(request)
    _throttle(u.id, limit=120)
    empty = {"hook": "", "length": "", "drop": {"at": None, "kept": None}, "points": 0}
    try:
        span = int(days)
    except (TypeError, ValueError):
        span = 28
    if span not in (7, 28, 90, 365):
        span = 28
    try:
        length = float(seconds or 0.0)
    except (TypeError, ValueError):
        length = 0.0
    try:
        from . import learn_signals
    except Exception:  # noqa: BLE001 - a build without this file still answers
        return {**empty, "why": MISSING}
    try:
        got = await run_in_threadpool(learn_signals.signals, video, span, length)
    except Exception:  # noqa: BLE001 - a signal is an extra, never a reason to fail a page
        return dict(empty)
    if not isinstance(got, dict):
        return dict(empty)
    return {**empty, **got}


@router.get("/api/learn/arms")
async def arms(request: Request) -> dict:
    """The trial this person has saved, or an answer that says there is not one yet."""
    u = _me(request)
    _throttle(u.id, limit=120)
    try:
        from . import ai_arms  # noqa: F401 - asked for by name so a build without it can say so
    except Exception:  # noqa: BLE001 - a build without this file still answers
        return {"trial": None, "why": MISSING}
    try:
        got = await run_in_threadpool(_read_trial, u.id)
    except Exception:  # noqa: BLE001 - an unreadable trial is no trial
        got = {"trial": None}
    if not got.get("trial"):
        # An empty answer is the one the module header says most needs explaining: without a sentence,
        # a page drawing no trial cannot tell "none yet" from a mistake.
        got["why"] = "No trial is saved yet. Start one to try two settings against each other."
    return got


@router.post("/api/learn/arms")
async def arms_start(request: Request) -> dict:
    """Open a trial: two settings, each with the value it should try, kept for the next round.

    A setting PeakCut cannot change is refused with the sentence the arms module writes, rather than
    stored as a trial that could never run."""
    u = _me(request)
    _throttle(u.id, limit=30)
    body = {}
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 - an empty body is answered, not refused here
        body = {}
    if not isinstance(body, dict):
        raise HTTPException(400, "Send a JSON object, like {\"target\": \"style\"}.")
    try:
        from . import ai_arms
    except Exception:  # noqa: BLE001 - a build without this file still answers
        return {"trial": None, "why": MISSING}
    try:
        trial = await run_in_threadpool(ai_arms.start, body.get("target", ""), body.get("value", ""),
                                        body.get("other", ""), body.get("other_value", ""))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, "PeakCut could not start that trial: " + str(e)[:200])
    out = await run_in_threadpool(_write_trial, u.id, trial)
    # A saved trial changes what the Improve page draws, and the page learns about changes from the
    # counter it polls, so the counter has to move or the new trial would not appear until a reload.
    try:
        ctx.bump(u.id)
    except Exception:  # noqa: BLE001 - a counter that cannot move must not fail the save
        pass
    return out


@router.delete("/api/learn/arms")
async def arms_stop(request: Request) -> dict:
    """Forget the saved trial. Answering with no trial is what the page then draws."""
    u = _me(request)
    _throttle(u.id, limit=30)
    out = await run_in_threadpool(_write_trial, u.id, None)
    try:
        ctx.bump(u.id)
    except Exception:  # noqa: BLE001 - see arms_start
        pass
    return out


@router.get("/api/learn/cost")
async def cost(request: Request) -> dict:
    """What this person's rounds have used today, plus one sentence about what is left."""
    u = _me(request)
    _throttle(u.id, limit=120)
    empty = {"calls": 0, "tokens": 0, "at": 0.0, "report": ""}
    try:
        from . import learn_guard
    except Exception:  # noqa: BLE001 - a build without this file still answers
        return {**empty, "why": MISSING}
    try:
        got = await run_in_threadpool(learn_guard.spent, u.id)
        said = await run_in_threadpool(learn_guard.report, u.id)
    except Exception:  # noqa: BLE001 - a budget nobody can read is a budget with nothing used
        return dict(empty)
    if not isinstance(got, dict):
        got = {}
    return {**empty, **got, "report": said if isinstance(said, str) else ""}
