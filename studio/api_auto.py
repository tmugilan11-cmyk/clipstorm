"""The schedule over HTTP: what a scheduler command would look like, and installing one only when told twice.

`studio/autopilot.py` already writes the command for a Windows, macOS or Linux scheduler and already refuses to
install one without an explicit confirmation. This module is only the doorway, and it keeps that refusal in place:
`confirm` defaults to nothing, so a page that forgets to send it changes nothing on the machine. `server.py` grows
one line: `app.include_router(api_auto.router)`.

It deliberately does not import `server.py`, for the same circular-import reason as every other `api_*` module.

    GET   /api/autopilot/spec?os=&times=&command=      the structured spec behind a schedule
    GET   /api/autopilot/preview?os=&times=&command=   the command as text, to copy and run by hand
    POST  /api/autopilot/install                       an OS scheduler entry - needs {"confirm": true}
    POST  /api/autopilot/remove                        take it away again - needs {"confirm": true}

The first argument in every route is an OPERATING SYSTEM, not a streaming platform: "windows", "macos" or "linux".
Left out, it is this machine. `studio/autopilot.py` maps it, and an unknown name is a plain 400 rather than a
command nobody can run."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool

from . import auth, autopilot

router = APIRouter()

_OS_MAX = 20
_TIMES_MAX = 200
_COMMAND_MAX = 400

# The sentence a person gets when a call would have changed this machine and nobody said yes. Written once so the
# routes and the tests read the same words.
_NEEDS_CONFIRM = ("Nothing was changed on this machine. Sending \"confirm\": true is what installs a schedule, "
                  "and it is never filled in for you.")


def _me(request: Request):
    """The signed-in person for this request, exactly as `server._me` would return them."""
    u = getattr(request.state, "user", None)
    if not u or not getattr(u, "id", None):
        raise HTTPException(401, "Please sign in.")
    return u


def _admin(request: Request):
    """Installing a scheduler entry changes the whole machine, so it is for the operator only.

    Read off the same request the rest of the module uses; `is_admin` is the attribute `server._me` returns, set by
    the middleware before any route runs."""
    u = _me(request)
    if not getattr(u, "is_admin", False):
        raise HTTPException(403, "Only the operator can change the schedule on this machine.")
    return u


def _throttle(key: str, limit: int, window: int, msg: str) -> None:
    """The same rate limit `server._throttle` applies."""
    try:
        auth.throttle(key, limit, window)
    except auth.AuthError:
        raise HTTPException(429, msg)


def _times(raw) -> list:
    """The times as a short list of "HH:MM" strings, in the order given.

    A list or a comma-separated string are both accepted, because one comes from a form and the other from a page;
    the cap keeps a hand-written request from asking for a thousand scheduler entries."""
    if isinstance(raw, str):
        asked = [t.strip() for t in raw.split(",")]
    elif isinstance(raw, (list, tuple)):
        asked = [str(t).strip() for t in raw]
    else:
        asked = []
    when = [t for t in asked if t][:12]
    for t in when:
        if len(t) > 5 or ":" not in t:
            raise HTTPException(400, f"\"{t}\" is not a time. Write it like 09:00.")
    return when


def _os(raw: str) -> str:
    """The operating system named, or this machine's. An unknown name is a plain 400 naming the three."""
    name = str(raw or "").strip().lower()
    if len(name) > _OS_MAX:
        raise HTTPException(400, "windows, macos or linux")
    return name          # autopilot checks it and puts the sentence in the returned text; see below


def _bad_os(text: str) -> bool:
    """Whether autopilot refused the operating system instead of writing a schedule."""
    return "unknown platform" in str(text or "").lower()


@router.get("/api/autopilot/spec")
async def autopilot_spec(request: Request, os: str = Query("", max_length=_OS_MAX),
                         times: str = Query("", max_length=_TIMES_MAX),
                         command: Optional[str] = Query(None, max_length=_COMMAND_MAX)) -> dict:
    """The structured spec behind a schedule: its days, times, argv, and the text of each command.

    Nothing is installed and no file is written; this is the same value `preview` renders."""
    _me(request)
    when = _times(times)
    try:
        spec = autopilot.spec(_os(os), when, command or "")
    except Exception as e:            # noqa: BLE001 - a bad request is a 400 with a sentence
        raise HTTPException(400, "Could not work out a schedule: %s" % e)
    bad = _bad_os(spec.get("text", "")) if isinstance(spec, dict) else False
    if bad:
        raise HTTPException(400, "Choose windows, macos or linux. That is which scheduler to write for, "
                                 "not which site the clips come from.")
    return spec


@router.get("/api/autopilot/preview")
async def autopilot_preview(request: Request, os: str = Query("", max_length=_OS_MAX),
                            times: str = Query("", max_length=_TIMES_MAX),
                            command: Optional[str] = Query(None, max_length=_COMMAND_MAX)) -> dict:
    """The scheduler command as text for a person to copy and run. Nothing is installed here, ever."""
    _me(request)
    when = _times(times)
    try:
        text = autopilot.preview(_os(os), when, command or "")
    except Exception as e:            # noqa: BLE001
        raise HTTPException(400, "Could not work out a schedule: %s" % e)
    if _bad_os(text):
        raise HTTPException(400, "Choose windows, macos or linux. That is which scheduler to write for, "
                                 "not which site the clips come from.")
    return {"ok": True, "preview": text, "times": when, "os": os or "this machine",
            "note": "Copy this and run it yourself. PeakCut does not touch your scheduler."}


@router.post("/api/autopilot/install")
async def autopilot_install(request: Request) -> dict:
    """Write one OS scheduler entry. Requires {"confirm": true}: without it this is a 400 and nothing changes.

    `confirm` is read as a strict boolean on purpose. A string "false", a missing field and a typo all mean no,
    because the cost of guessing wrong here is a job that quietly starts running on somebody's machine."""
    u = _admin(request)
    try:
        body = await request.json()
    except ValueError as e:
        raise HTTPException(400, "That request could not be read. " + _NEEDS_CONFIRM) from e
    if not isinstance(body, dict) or body.get("confirm") is not True:
        raise HTTPException(400, _NEEDS_CONFIRM)

    when = _times(body.get("times"))
    _throttle("auto:" + u.id, 6, 300, "The schedule was just changed. Give it a moment.")
    try:
        result = await run_in_threadpool(autopilot.install, _os(body.get("os")), when,
                                         str(body.get("command") or ""), True)
    except Exception as e:            # noqa: BLE001
        raise HTTPException(400, "Could not install that schedule: %s" % e) from e
    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(400, str(result["error"]))
    return {"ok": True, "installed": True, "schedule": result}


@router.post("/api/autopilot/remove")
async def autopilot_remove(request: Request) -> dict:
    """Take the scheduler entry away again. Same confirmation rule: nothing happens without it."""
    u = _admin(request)
    try:
        body = await request.json()
    except ValueError as e:
        raise HTTPException(400, "That request could not be read. " + _NEEDS_CONFIRM) from e
    if not isinstance(body, dict) or body.get("confirm") is not True:
        raise HTTPException(400, _NEEDS_CONFIRM)

    _throttle("auto:" + u.id, 6, 300, "The schedule was just changed. Give it a moment.")
    try:
        result = await run_in_threadpool(autopilot.remove, _os(body.get("os")), _times(body.get("times")), True)
    except Exception as e:            # noqa: BLE001
        raise HTTPException(400, "Could not remove that schedule: %s" % e) from e
    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(400, str(result["error"]))
    return {"ok": True, "removed": True, "schedule": result}
