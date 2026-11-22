"""Meme sounds over HTTP: the catalogue, the shelf on this machine, and the cues written on one clip.

Every route here is about a choice, never a render. `studio/jobs.py` is the only thing that mixes a sound into a
clip, and it does so from the cues this module stores, so a page that browses the catalogue cannot make a clip.

    GET    /api/memesounds/search?q=       sounds by name, alias, tag, mood or use case
    GET    /api/memesounds/for?situation=  sounds for a described moment, ranked here
    GET    /api/memesounds/trending?window= what people are playing right now
    GET    /api/memesounds/library        what is kept on this machine
    POST   /api/memesounds/keep           download one to the shelf
    POST   /api/memesounds/upload         keep a sound of the person's own on the shelf
    DELETE /api/memesounds/library/{slug} remove one from the shelf
    POST   /api/memesounds/play/{slug}    the mp3, so a page can listen before choosing
    GET    /api/jobs/{jid}/clips/{cid}/sounds   the cues on one clip
    PUT    /api/jobs/{jid}/clips/{cid}/sounds   write the cues on one clip
    POST   /api/jobs/{jid}/clips/{cid}/sounds/suggest  let the AI place them
    POST   /api/jobs/{jid}/clips/{cid}/sounds/hear     mix the cues into the clip now

It deliberately does not import `server.py`, for the same circular-import reason as every other `api_*` module.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from . import ai, auth, config, ctx, jobs, memesound, safe, soundplan

router = APIRouter()

# The words the catalogue uses for a mood, mapped onto the shorter list the picker shows. A mood outside both is
# passed through untouched, so a new catalogue word is never silently dropped.
_SHELF_BY = "title"


def _me(request: Request):
    """The signed-in person for this request, exactly as `server._me` would return them."""
    u = getattr(request.state, "user", None)
    if not u or not getattr(u, "id", None):
        raise HTTPException(401, "Please sign in.")
    return u


def _throttle(key: str, limit: int, window: int, msg: str) -> None:
    """The same rate limit `server._throttle` applies, without importing server.py."""
    try:
        auth.throttle(key, limit, window)
    except auth.AuthError:
        raise HTTPException(429, msg)


def _job_or_404(jid: str):
    """One job of the signed-in person, or 404. The owner comes from the session, never from the address."""
    job = jobs.get(jid)
    if not job or str(job.get("user") or "") != ctx.uid():
        raise HTTPException(404, "That job is not here.")
    return job


def _clip_or_404(job: dict, cid: str) -> dict:
    """One clip of a job, or 404."""
    for clip in job.get("clips") or []:
        if str(clip.get("id") or "") == str(cid):
            return clip
    raise HTTPException(404, "That clip is not here.")


def _clip_len(clip: dict) -> float:
    """How long a clip is, from its own numbers. A clip with no end is 0, never a guess."""
    try:
        return max(0.0, float(clip.get("end") or 0.0) - float(clip.get("start") or 0.0))
    except (TypeError, ValueError):
        return 0.0


@router.get("/api/memesounds/search")
def memesounds_search(request: Request, q: str = "", limit: int = 12) -> dict:
    """Sounds by name, alias, tag, mood or use case."""
    u = _me(request)
    word = str(q or "").strip()
    if not word:
        return {"query": "", "sounds": [], "kept": _kept_set()}
    _throttle("ms:" + u.id, 60, 60, "That is a lot of sound searches at once. Give it a moment.")
    try:
        rows = memesound.rank(memesound.search(word, limit=limit), word)
    except memesound.CatalogueDown as e:
        raise HTTPException(502, str(e))
    return {"query": word, "sounds": rows, "kept": _kept_set()}


@router.get("/api/memesounds/for")
def memesounds_for(request: Request, situation: str = "", limit: int = 8) -> dict:
    """Sounds for a described moment, ranked here rather than in the catalogue's own order."""
    u = _me(request)
    said = str(situation or "").strip()
    if not said:
        return {"situation": "", "sounds": [], "kept": _kept_set()}
    _throttle("msf:" + u.id, 40, 60, "That is a lot of sound lookups at once. Give it a moment.")
    try:
        rows = memesound.find(said, limit=limit)
    except memesound.CatalogueDown as e:
        raise HTTPException(502, str(e))
    return {"situation": said, "sounds": rows, "kept": _kept_set()}


@router.get("/api/memesounds/trending")
def memesounds_trending(request: Request, window: str = "24h") -> dict:
    """What people are playing right now."""
    _me(request)
    try:
        rows = memesound.rank(memesound.trending(window))
    except memesound.CatalogueDown as e:
        raise HTTPException(502, str(e))
    return {"window": window, "sounds": rows, "kept": _kept_set()}


def _kept_set() -> List[str]:
    """The slugs already on this machine, so a page can mark them without a second call."""
    try:
        return [row["slug"] for row in memesound.library()]
    except OSError:
        return []


@router.get("/api/memesounds/library")
def memesounds_library(request: Request) -> dict:
    """Every sound kept on this machine, newest first."""
    _me(request)
    return {"sounds": memesound.library(), "folder": str(memesound.shelf()),
            "note": "These are the sounds PeakCut has on this machine, so a render never needs the internet."}


@router.post("/api/memesounds/keep")
async def memesounds_keep(request: Request) -> dict:
    """Download one sound to the shelf so a later render can use it offline."""
    u = _me(request)
    _throttle("msk:" + u.id, 40, 300, "That is a lot of downloads at once. Give it a moment.")
    body = await _json(request)
    slug = str(body.get("slug") or "").strip()
    if not slug:
        raise HTTPException(400, "Which sound?")
    try:
        memesound.take(slug, str(body.get("audio_url") or ""), str(body.get("title") or ""))
    except (ValueError, RuntimeError) as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "slug": slug, "kept": _kept_set(), "seconds": round(memesound.length(memesound.path_for(slug)), 2)}


@router.delete("/api/memesounds/library/{slug}")
def memesounds_drop(slug: str, request: Request) -> dict:
    """Remove one sound from this machine."""
    _me(request)
    gone = memesound.forget(slug)
    return {"ok": gone, "slug": slug, "kept": _kept_set()}


@router.post("/api/memesounds/upload")
async def memesounds_upload(request: Request, file: UploadFile = File(...)) -> dict:
    """Keep a sound of the person's own on the shelf, next to the ones from the catalogue.

    The bytes are proved to be audio with ffprobe BEFORE they are stored — a renamed picture that passed
    the size check would sit on the shelf forever and fail every mix that picked it. The name on the file
    becomes the title; the slug is made from it and always starts with "mine-", so an upload can never
    shadow a catalogue sound."""
    u = _me(request)
    _throttle("msu:" + u.id, 10, 300, "That is a lot of uploads at once. Give it a moment.")
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "The file arrived empty.")
    try:
        if len(raw) > memesound.MAX_UPLOAD:
            raise ValueError("That file is over 8 MB. A sound effect does not need to be.")
        raw_name = str(file.filename or "").strip()
        title = raw_name.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()[:80] or "My sound"
        slug = memesound.make_slug(title)
        path = memesound.store(slug, raw, title)
        info = memesound._ffprobe(path)
        if not info.get("audio"):
            memesound.forget(slug)
            raise ValueError("That file has no audio in it, so it was not kept.")
        seconds = float(info.get("duration") or 0.0)
        if not (0.1 <= seconds <= memesound.MIX_SECONDS):
            memesound.forget(slug)
            raise ValueError(f"That file is {seconds:.1f} seconds long. Sounds between 0.1 and 300 seconds are kept.")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    row = {"slug": slug, "title": title, "seconds": round(seconds, 2), "bytes": len(raw), "source": "uploaded"}
    return {"ok": True, "sound": row, "kept": _kept_set()}


@router.api_route("/api/memesounds/play/{slug}", methods=["GET", "HEAD"])
def memesounds_play(slug: str, request: Request):
    """The mp3 itself, so a page can listen before it chooses.

    HEAD is answered as well as GET: the page asks with a HEAD first, because a missing file and a file this
    browser cannot decode arrive at an audio element as the same error."""
    _me(request)
    try:
        path = memesound.path_for(slug)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not memesound.kept(slug):
        raise HTTPException(404, "That sound is not on this machine yet.")
    return FileResponse(path, media_type="audio/mpeg", headers={"Cache-Control": "private, max-age=300"})


async def _json(request: Request) -> dict:
    """The request body, or an empty record. A body that is not JSON is a refusal, not a crash."""
    try:
        got = await request.json()
    except Exception:                 # noqa: BLE001 - an empty PUT is legal here
        return {}
    return got if isinstance(got, dict) else {}


def _cues_of(clip: dict) -> List[dict]:
    got = clip.get("sounds")
    return [c for c in got if isinstance(c, dict)] if isinstance(got, list) else []


def _clip_view(clip: dict) -> dict:
    """What the page is allowed to see about a clip's sounds. The source path is nobody's business here."""
    return {"id": clip.get("id"), "seconds": round(_clip_len(clip), 2), "cues": _cues_of(clip),
            "sounds_line": memesound.describe(_cues_of(clip)), "version": clip.get("version") or 0,
            "status": clip.get("status") or ""}


@router.get("/api/jobs/{jid}/clips/{cid}/sounds")
def clip_sounds(jid: str, cid: str, request: Request) -> dict:
    """The meme sounds written on one clip."""
    _me(request)
    job = _job_or_404(jid)
    clip = _clip_or_404(job, cid)
    return {"ok": True, "clip": _clip_view(clip)}


@router.put("/api/jobs/{jid}/clips/{cid}/sounds")
async def clip_sounds_put(jid: str, cid: str, request: Request) -> dict:
    """Write the meme sounds on one clip.

    The list is the whole truth: a cue missing from it is removed from the clip. Every cue is checked before
    anything is stored, so a clip never carries a sound this machine does not have."""
    u = _me(request)
    _throttle("msw:" + u.id, 60, 60, "That is a lot of sound changes at once. Give it a moment.")
    job = _job_or_404(jid)
    clip = _clip_or_404(job, cid)
    body = await _json(request)
    wanted = body.get("cues")
    if wanted is None or not isinstance(wanted, list):
        raise HTTPException(400, "Send a list of sounds in \"cues\", even when it is empty.")
    bad = [((c or {}).get("slug") or "(none)", memesound.cue_ok(c or {})) for c in wanted]
    bad = [(slug, why) for slug, why in bad if why]
    if bad:
        raise HTTPException(400, bad[0][1])
    got = memesound.tidy(wanted)
    # Compared against the RAW stored list, not a tidied one: tidy drops cues whose sound is no longer on
    # the shelf, so comparing tidied against tidied would call a stale cue "no change" and it could never
    # be removed from the clip.
    if got != _cues_of(clip):
        clip["sounds"] = got
        clip["sounds_at"] = _now()
        jobs.save(job)
        ctx.bump()
    return {"ok": True, "clip": _clip_view(clip)}


def _now() -> str:
    """Now, in the same shape the rest of the job files use."""
    import datetime
    return datetime.datetime.now().isoformat(timespec="seconds")


@router.post("/api/jobs/{jid}/clips/{cid}/sounds/suggest")
async def clip_sounds_suggest(jid: str, cid: str, request: Request) -> dict:
    """Let the AI place the sounds on one clip, and answer with the plan without touching the clip.

    Nothing is stored here: the page shows what the AI would do and the person presses save. That is the same
    shape the Improve page uses for a round, and for the same reason."""
    u = _me(request)
    _throttle("msg:" + u.id, 20, 60, "That is a lot of sound suggestions at once. Give it a moment.")
    job = _job_or_404(jid)
    clip = _clip_or_404(job, cid)
    body = await _json(request)
    if not ai.ready():
        raise HTTPException(400, "No AI is set up, so PeakCut cannot choose the sounds. Set one up under AI.")

    words = clip.get("fixed_words") or job.get("words") or []
    start = float(clip.get("start") or 0.0)
    end = float(clip.get("end") or 0.0)

    def ask(prompt: str) -> str:
        """Ask the configured AI, in the one shape the rest of PeakCut uses.

        `studio.ai` has no `ask()`; its entry point is `call(model, prompt, schema, timeout)`, which enforces a JSON
        answer shape. This used to pass `ai.ask` straight through and every press of the button came back as
        "Internal Server Error" with `AttributeError: module 'studio.ai' has no attribute 'ask'` in the log."""
        last = None
        tries = list(ai.models()) * 2   # one more go each: the service drops the slowest answers now and then
        for model in tries:
            try:
                # No schema on purpose. The prompt already says exactly which object it wants, and handing the
                # same request over as a JSON schema made the model think about the schema as well as the clip:
                # measured on this install, the identical prompt took 8.9 s without a schema and 38.3 s with one.
                # 150 seconds, because a real answer on a 7-second clip still measured 48 s and then 85 s, so 90
                # turned the slower half of the answers into "PeakCut couldn't reach Logfare" while the service
                # was answering fine. `soundplan.cues()` checks the answer against the rules itself.
                # A retry, because this service sometimes ends a long answer with a read timeout and
                # answers the same prompt in 48 s the next second: measured on one clip, 48 s, 85 s, 121 s and
                # then a failure, with the identical prompt. Pressing the button again should not be the only
                # way past a dropped connection.
                out, _sent, _wrote = ai.call(model, prompt, None, 150.0)
                return out if isinstance(out, str) else json.dumps(out)
            except Exception as e:  # noqa: BLE001
                last = e
        raise RuntimeError(ai.explain(last) or str(last) if last else "The AI did not answer.")

    def work() -> dict:
        got = soundplan.plan(words, start, end, brand=_brand(job), ask=ask,
                             situation=str(body.get("situation") or ""))
        picked = soundplan.sounds_for(got.get("cues") or [])
        kept_rows = []
        for mood, rows in picked.items():
            for row in rows:
                if memesound.kept(row["slug"]):
                    kept_rows.append(row)
        # A cue whose sound is only in the catalogue still has to come down to this machine before it can be
        # mixed, so the answer says which ones need keeping rather than pretending they are ready.
        cues = soundplan.with_sounds(got.get("cues") or [], picked)
        for cue in cues:
            cue["kept"] = memesound.kept(cue["slug"])
        return {"ok": True, "cues": cues, "why": got.get("why") or "", "source": got.get("source") or "none",
                "seconds": round(max(0.0, end - start), 2), "most": soundplan.most_for(max(0.0, end - start)),
                "need": [c["slug"] for c in cues if not c.get("kept")]}

    return await run_in_threadpool(work)


def _brand(job: dict) -> dict:
    """The saved brand for whoever owns this job, or an empty record. Never a failed request."""
    try:
        from . import brand
        return brand.load(str(job.get("user") or "default"))
    except Exception:                 # noqa: BLE001 - a broken brand must not stop a suggestion
        return {}


@router.post("/api/jobs/{jid}/clips/{cid}/sounds/hear")
async def clip_sounds_hear(jid: str, cid: str, request: Request) -> dict:
    """Mix the cues that are already saved on the clip into the clip file now.

    This is the one route that writes a clip's file from a sound change, and it refuses when the clip is busy:
    two encodes of one file at once is how a clip ends up half written."""
    u = _me(request)
    _throttle("msh:" + u.id, 12, 300, "The clip was just mixed. Give it a moment before asking again.")
    job = _job_or_404(jid)
    clip = _clip_or_404(job, cid)
    cues = _cues_of(clip)
    if not cues:
        raise HTTPException(400, "This clip has no meme sounds on it yet.")
    if str(clip.get("status") or "") in ("rendering", "queued"):
        raise HTTPException(409, "This clip is being made right now. Wait for it to finish.")

    def work() -> dict:
        folder = Path(job["dir"]) / "clips"
        made = folder / (clip.get("file") or f"{clip.get('id')}.mp4")
        if not made.is_file():
            raise HTTPException(404, "The clip file is not there yet.")
        tmp = folder / ("." + made.stem + ".sounds.mp4")
        try:
            memesound.mix(made, cues, tmp)
        except (ValueError, RuntimeError) as e:
            raise HTTPException(400, str(e))
        try:
            tmp.replace(made)
        except OSError as e:
            try:
                tmp.unlink()
            except OSError:
                pass
            raise HTTPException(500, "PeakCut could not replace the clip: " + safe.friendly(e))
        clip["sounds_mixed_at"] = _now()
        clip["sounds_version"] = int(clip.get("sounds_version") or 0) + 1
        jobs.save(job)
        ctx.bump()
        return {"ok": True, "clip": _clip_view(clip)}

    return await run_in_threadpool(work)


@router.post("/api/memesounds/suggest")
async def memesounds_suggest(request: Request) -> dict:
    """Sounds for a moment, chosen by the AI against the catalogue, without a clip.

    The Sounds page uses this to answer "what would fit this?" before a clip exists."""
    u = _me(request)
    _throttle("mss:" + u.id, 20, 60, "That is a lot of sound suggestions at once. Give it a moment.")
    body = await _json(request)
    said = str(body.get("situation") or "").strip()
    if not said:
        raise HTTPException(400, "Describe the moment and PeakCut will look for a sound.")
    try:
        rows = memesound.find(said, limit=8)
    except memesound.CatalogueDown as e:
        raise HTTPException(502, str(e))
    return {"situation": said, "sounds": rows, "kept": _kept_set()}


_ = (subprocess, config)      # kept for the type checkers: both are used by callers of this module
