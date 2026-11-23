"""Montages over HTTP: a Short made of several moments of one video, and the typed lines of the Chat clip type.

`studio/montage.py` does the work (choosing the moments, fitting the length, rendering each one, joining them). This
file is only the doorway, in a router of its own like the other `api_*.py` files; `server.py` mounts it with one line.
It reads the signed-in person off the request itself, so it does not import `server.py` back.

    GET    /api/montage/types                      the four joining types, with how many moments each takes
    GET    /api/montage/{jid}                      this video's montages, newest first
    POST   /api/montage/{jid}                      check the request at once, then make the montage in the background
    GET    /api/montage/{jid}/{mid}/video.mp4      the finished montage
    GET    /api/montage/{jid}/{mid}/cover.jpg      its cover picture
    DELETE /api/montage/{jid}/{mid}                take a montage away (its own files only; never a clip)
    POST   /api/montage/{jid}/chat                 set the chat lines of one clip and make that clip again

A montage never changes the video's clips. Its records live in `montages.json` and its files in `montage/`, both
inside the video's own folder, so deleting the video deletes its montages with it.

A person's request is checked here in full before anything is queued (which moments, whether their pictures are
still there, whether they fit), so a mistake comes back as a plain sentence and not as a failed job later.
"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import FileResponse

from . import brand, ctx, formats, jobs, montage, safe

router = APIRouter()

_LOCK = threading.Lock()
_ID = re.compile(r"m\d{3,6}")
_MAX_KEPT = 40                   # one video keeps at most this many montages; the oldest finished ones go first


def _me(request: Request):
    user = getattr(request.state, "user", None)
    if not user or not getattr(user, "id", None):
        raise HTTPException(401, "Please sign in.")
    return user


def _job_or_404(request: Request, jid: str) -> dict:
    _me(request)
    job = jobs.get(jid)
    if not job or job.get("user") != ctx.uid():
        raise HTTPException(404, "No such video.")
    return job


# ---------------------------------------------------------------- the records
def _file(job: dict) -> Path:
    return Path(job["dir"]) / "montages.json"


def _read(job: dict) -> list:
    try:
        got = json.loads(_file(job).read_text(encoding="utf-8"))
        return got if isinstance(got, list) else []
    except (OSError, ValueError):
        return []


def _write(job: dict, rows: list) -> None:
    f = _file(job)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    tmp.replace(f)                       # swapped in, so a crash cannot leave half a file


def _update(job: dict, mid: str, **fields) -> dict | None:
    with _LOCK:
        rows = _read(job)
        for r in rows:
            if r.get("id") == mid:
                r.update(fields)
                _write(job, rows)
                ctx.bump(job["user"])
                return r
    return None


STALE = 3600.0       # a montage still "being made" after an hour died with a restart; it is not waited for


def _busy(rows: list) -> bool:
    now = time.time()
    return any(r.get("status") in ("queued", "making") and now - float(r.get("created") or 0) < STALE for r in rows)


def _public(job: dict, r: dict) -> dict:
    return {k: r.get(k) for k in ("id", "format", "label", "status", "stage", "error", "length", "parts", "cards",
                                  "hook", "notes", "created", "layout", "gap", "file", "cover")}


# ---------------------------------------------------------------- the background work
def _work(jid: str, mid: str, args: dict) -> None:
    """Runs on the render worker as the person who asked. Never raises: the outcome is written on the record."""
    job = jobs.get(jid)
    if not job:
        return
    _update(job, mid, status="making", stage="Starting")
    try:
        try:
            doc = brand.load(job.get("user") or "default")
        except Exception:      # noqa: BLE001 - a brand that will not load means the plain look
            doc = None
        res = montage.make(job, args["format"], Path(job["dir"]) / "montage", mid, ids=args.get("clips"),
                           count=args.get("count"), hook=args.get("hook", ""), layout=args.get("layout", ""),
                           word=args.get("word", ""), brand=doc,
                           report=lambda text: _update(job, mid, stage=text))
        _update(job, mid, status="done", stage="", error=None, file=res["file"], cover=res["cover"],
                length=res["length"], parts=res["parts"], cards=res["cards"], hook=res["hook"], notes=res["notes"],
                layout=res["layout"], gap=res["gap"])
    except montage.MontageError as e:
        _update(job, mid, status="error", stage="", error=str(e))
    except Exception as e:  # noqa: BLE001 - whatever went wrong, the person gets a sentence
        _update(job, mid, status="error", stage="", error="The montage could not be made: " + safe.friendly(e, 300))


def _clean_args(body: dict) -> dict:
    fmt = str(body.get("format") or "").strip().lower()
    if fmt not in formats.JOINS:
        raise HTTPException(400, "Choose a montage type: " + ", ".join(formats.FORMATS[k]["label"] for k in formats.JOINS) + ".")
    ids = body.get("clips")
    if ids is not None and (not isinstance(ids, list) or not all(isinstance(x, str) and re.fullmatch(r"[\w\-]{1,60}", x) for x in ids)):
        raise HTTPException(400, "The chosen clips must be a list of clip names.")
    try:
        count = int(body["count"]) if body.get("count") not in (None, "") else None
    except (TypeError, ValueError):
        raise HTTPException(400, "How many moments must be a number.")
    return {"format": fmt, "clips": ids or None, "count": count, "hook": str(body.get("hook") or "")[:60],
            "layout": str(body.get("layout") or "")[:12], "word": str(body.get("word") or "")[:20]}


# ---------------------------------------------------------------- the routes
@router.get("/api/montage/types")
def montage_types(request: Request) -> dict:
    """The joining types, as `formats.public()` describes them, with the fewest and most moments each takes."""
    _me(request)
    return {"types": [r for r in formats.public() if r["id"] in formats.JOINS]}


@router.get("/api/montage/{jid}")
def montage_list(request: Request, jid: str) -> dict:
    job = _job_or_404(request, jid)
    rows = sorted(_read(job), key=lambda r: r.get("created") or 0, reverse=True)
    for r in rows:
        if r.get("status") in ("queued", "making") and time.time() - float(r.get("created") or 0) >= STALE:
            r.update(status="error", stage="", error="This montage was interrupted. Make it again.")
    return {"montages": [_public(job, r) for r in rows]}


@router.post("/api/montage/{jid}")
def montage_make(request: Request, jid: str, body: dict = Body(...)) -> dict:
    job = _job_or_404(request, jid)
    args = _clean_args(body)
    try:
        fitted = montage.prepare(job, args["format"], args["clips"], args["count"], args["hook"], args["layout"],
                                 args["word"])
    except montage.MontageError as e:
        raise HTTPException(400, str(e))
    with _LOCK:
        rows = _read(job)
        if _busy(rows):
            raise HTTPException(409, "A montage of this video is still being made. Wait for it to finish.")
        mid = "m%03d" % (max([int(r["id"][1:]) for r in rows if _ID.fullmatch(str(r.get("id")))] or [0]) + 1)
        rec = {"id": mid, "format": args["format"], "label": formats.FORMATS[args["format"]]["label"],
               "status": "queued", "stage": "Waiting its turn", "error": None, "created": time.time(),
               "parts": [m["id"] for m in fitted["moments"]], "hook": fitted["hook"], "length": None, "cards": [],
               "notes": [], "layout": fitted["layout"]}
        rows.append(rec)
        finished = [r for r in rows if r.get("status") in ("done", "error")]
        for old in sorted(finished, key=lambda r: r.get("created") or 0)[: max(0, len(rows) - _MAX_KEPT)]:
            rows.remove(old)
            _drop_files(job, old)
        _write(job, rows)
    ctx.bump(job["user"])
    run = lambda: _work(jid, mid, dict(args, clips=[m["id"] for m in fitted["moments"]]))      # noqa: E731
    (jobs.submit_live if job.get("status") == "live" else jobs.submit)(run)
    return _public(job, rec)


def _drop_files(job: dict, r: dict) -> None:
    for key in ("file", "cover"):
        name = Path(str(r.get(key) or "")).name
        if name:
            (Path(job["dir"]) / "montage" / name).unlink(missing_ok=True)


def _served(request: Request, jid: str, mid: str, key: str, kind: str) -> FileResponse:
    job = _job_or_404(request, jid)
    if not _ID.fullmatch(mid):
        raise HTTPException(404, "No such montage.")
    rec = next((r for r in _read(job) if r.get("id") == mid), None)
    f = Path(job["dir"]) / "montage" / Path(str((rec or {}).get(key) or "")).name
    if not rec or rec.get("status") != "done" or not f.is_file():
        raise HTTPException(404, "That montage is not ready.")
    return FileResponse(f, media_type=kind, headers={"Cache-Control": "private, max-age=300"})


@router.get("/api/montage/{jid}/{mid}/video.mp4")
def montage_video(request: Request, jid: str, mid: str):
    return _served(request, jid, mid, "file", "video/mp4")


@router.get("/api/montage/{jid}/{mid}/cover.jpg")
def montage_cover(request: Request, jid: str, mid: str):
    return _served(request, jid, mid, "cover", "image/jpeg")


@router.delete("/api/montage/{jid}/{mid}")
def montage_delete(request: Request, jid: str, mid: str) -> dict:
    job = _job_or_404(request, jid)
    if not _ID.fullmatch(mid):
        raise HTTPException(404, "No such montage.")
    with _LOCK:
        rows = _read(job)
        rec = next((r for r in rows if r.get("id") == mid), None)
        if not rec:
            raise HTTPException(404, "No such montage.")
        if rec.get("status") in ("queued", "making") and time.time() - float(rec.get("created") or 0) < STALE:
            raise HTTPException(409, "This montage is still being made.")
        _write(job, [r for r in rows if r is not rec])
    _drop_files(job, rec)
    ctx.bump(job["user"])
    return {"ok": True}


@router.post("/api/montage/{jid}/chat")
def montage_chat(request: Request, jid: str, body: dict = Body(...)) -> dict:
    """Gives one clip its chat lines and makes the clip again as a Chat clip. The lines are the person's own words:
    Clipstorm keeps how busy chat was, never what it said."""
    job = _job_or_404(request, jid)
    cid = str(body.get("clip") or "")
    clip = next((c for c in job.get("clips") or [] if c.get("id") == cid), None)
    if not clip:
        raise HTTPException(404, "No such clip.")
    if job.get("status") in ("queued", "running") or clip.get("status") in ("queued", "rendering"):
        raise HTTPException(409, "This clip is still being made. Try again when it has finished.")
    lines = body.get("lines")
    if not isinstance(lines, list) or not [x for x in lines if isinstance(x, str) and x.strip()]:
        raise HTTPException(400, "Write at least one line of chat.")
    try:
        jobs.request_render(jid, cid, {"format": "chat", "chat": lines})
    except (ValueError, TypeError) as e:
        raise HTTPException(400, str(e))
    return jobs.public(job)
