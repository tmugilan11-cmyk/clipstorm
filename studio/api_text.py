"""Clip text over HTTP: translate a line, translate a clip's captions, and change a clip by writing a note.

`studio/translate.py` already knows the offline models, the languages and how to re-time translated words;
`studio/edit.py` already knows how to read a note like "end 2 seconds earlier" or "bigger captions" and how to put
that change on a clip. This module is only the doorway. It lives in a router of its own so the clip-text feature
stays in one file, and `server.py` grows one line: `app.include_router(api_text.router)`.

It deliberately does not import `server.py`. `server.py` imports this module to mount the router, so
`from .server import _me` would come back around on itself; the signed-in user is read off the request instead,
which is the very attribute `server._me` returns, filled in by the middleware before any route runs.

    GET   /api/translate/langs                     the languages, and whether this server can translate at all
    POST  /api/translate/text                      one line (the hook) in the target language
    POST  /api/jobs/{jid}/clips/{cid}/edit         a clip, changed the way a written note asks
    POST  /api/jobs/{jid}/clips/{cid}/translate    the clip's captions in another language, kept on the clip
    GET   /api/jobs/{jid}/clips/{cid}/words        the clip's caption words, with their times, for the editor

Every route is per-person: a job belongs to whoever is signed in, and `jobs.get` hands back nothing for someone
else's. None of these is admin-only. Nothing here logs or returns a model, a key, or a server path, and every
failure becomes a plain sentence instead of a traceback.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from . import auth, edit, jobs, translate

router = APIRouter()

# What the page says when a note is a note, but not one this editor can act on. Written out once so the page and
# the tests see the same words.
NOT_UNDERSTOOD = 'I did not understand that. Try "end 2 seconds earlier" or "bigger captions".'

# The clip's own caption words, in the order `jobs` keeps them: the tidied copy first, then whatever the clip
# carries itself. Both are in source-video seconds, which is what the editor and the renderer both expect.
_WORD_KEYS = ("words", "fixed_words")

_TEXT_MAX = 2000        # one line of text to translate; a hook is never anywhere near this long
_WORDS_MAX = 4000       # a hand-edited job could claim a huge span; translating 4000 words is plenty


def _me(request: Request):
    """The signed-in person for this request, exactly as `server._me` would return them.

    Read off the request rather than imported from `server.py`, because `server.py` imports this module to mount
    the router and the import would come straight back. A request that somehow reaches a clip-text route with
    nobody signed in gets the same plain answer the rest of the app gives under /api."""
    u = getattr(request.state, "user", None)
    if not u or not getattr(u, "id", None):
        raise HTTPException(401, "Please sign in.")
    return u


def _throttle(key: str, limit: int, window: int, msg: str = "Too many requests at once. Wait a moment.") -> None:
    """The same rate limit `server._throttle` applies, without importing server.py.

    Translating runs a model on this machine's CPU, so a page in a loop must be told to slow down instead of
    pinning a core."""
    try:
        auth.throttle(key, limit, window)
    except auth.AuthError:
        raise HTTPException(429, msg)


async def _body(request: Request) -> dict:
    """The JSON body as a dict, or a plain 400.

    Read by hand instead of through `body: dict = Body(...)`: FastAPI answers a malformed or empty body with its
    own 422 report, and a person who sees that learns nothing."""
    try:
        body = await request.json()
    except ValueError as e:                       # malformed JSON, or no body at all
        raise HTTPException(400, "That request could not be read. Try again from the page.") from e
    if not isinstance(body, dict):
        raise HTTPException(400, "That request could not be read. Try again from the page.")
    return body


def _no_engine() -> HTTPException:
    """The sentence a person gets when the two translation packages are not on this server."""
    return HTTPException(400, "Offline translation isn't installed on this server yet. On the server run "
                              f"`{translate.INSTALL}` and restart PeakCut.")


def _wanted_lang(body: dict) -> str:
    """The language asked for, or the one saved in Settings; "en"/"" mean "leave it in English"."""
    code = str(body.get("lang") or "").strip().lower()
    if not code:
        try:
            code = translate.load().get("lang") or ""        # the server-wide choice, chosen once in Settings
        except Exception:                                     # noqa: BLE001 - a broken file must not fail a route
            code = ""
    return code


def _check_lang(code: str) -> str:
    """A language code this module will accept, or a plain 400 naming the ones it knows."""
    if not code:
        raise HTTPException(400, "Choose a language to translate into first.")
    if code in translate.LANGS or code in ("", "en"):
        return code
    names = ", ".join(translate.LANGS.values())
    raise HTTPException(400, f"That is not a language PeakCut translates into. Choose one of: {names}.")


# ---------------------------------------------------------------- the languages, and one line of text
@router.get("/api/translate/langs")
def translate_langs(request: Request) -> dict:
    """The languages, each code mapped to its plain name, and whether this server can translate at all.

    `available` is false on a machine without the two packages: the page can then hide the language picker or say
    what to install, instead of letting a person pick a language that cannot work."""
    _me(request)
    return {**translate.LANGS, "available": bool(translate.available())}


@router.post("/api/translate/text")
async def translate_text(request: Request) -> dict:
    """One line, in another language: what the hook of a clip is translated with.

    A line that is empty, or already English, comes back untouched and costs no model at all — which is why the
    engine check happens after the language is known rather than before."""
    u = _me(request)
    body = await _body(request)
    line = str(body.get("text") or "")
    code = _check_lang(_wanted_lang(body))
    if not line.strip():
        raise HTTPException(400, "There is nothing to translate yet. Paste the line you want first.")
    if len(line) > _TEXT_MAX:
        raise HTTPException(400, f"That is longer than one line. Keep it under {_TEXT_MAX} characters.")
    if code not in ("", "en") and not translate.available():
        raise _no_engine()
    _throttle("text:" + u.id, 60, 60, "That is a lot of translating at once. Give it a moment.")
    try:
        out = await run_in_threadpool(translate.text, line, code)
    except (ValueError, translate.TranslateError) as e:
        # both carry a sentence a person can read: an unknown code, a missing model, a broken download
        raise HTTPException(400, str(e) or "That line could not be translated.") from e
    return {"text": out, "lang": code}


# ---------------------------------------------------------------- a clip, changed by a written note
def _job_or_404(jid: str) -> dict:
    """The signed-in person's job, or the same "no such video" for anyone else's — never which one it was."""
    job = jobs.get(jid) if re.fullmatch(r"[\w\-]{8,60}", jid) else None
    if not job:
        raise HTTPException(404, "No such video")
    return job


def _clip_or_404(job: dict, cid: str) -> dict:
    clip = next((c for c in job.get("clips") or [] if isinstance(c, dict) and c.get("id") == cid), None)
    if not clip:
        raise HTTPException(404, "No such clip")
    return clip


def _public_clip(job: dict, cid: str) -> dict:
    """The clip as the browser may see it: run through `jobs.public`, so the strip list lives in one place."""
    for c in jobs.public(job).get("clips") or []:
        if c.get("id") == cid:
            return c
    return {}


def _clip_words(job: dict, clip: dict) -> list:
    """The clip's own caption words, in source-video seconds; [] when the clip carries none.

    A clip usually carries its tidied captions (`fixed_words`, written by the renderer) or the raw transcript.
    Before the first render it may carry neither, so the video's words.json is read instead, cut to the clip's
    own span — the same rule `jobs._caption_words` uses. A missing or hand-broken transcript is "no words", not an
    error: the caller turns that into one plain sentence."""
    for key in _WORD_KEYS:
        value = clip.get(key)
        if isinstance(value, list) and value and all(isinstance(w, dict) and "s" in w for w in value):
            return value[:_WORDS_MAX]
    try:
        every = json.loads((Path(job["dir"]) / "words.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError, TypeError):
        return []
    if not isinstance(every, list):
        return []
    start, end = clip.get("start"), clip.get("end")
    if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
        return [w for w in every if isinstance(w, dict) and "s" in w][:_WORDS_MAX]
    return [w for w in every
            if isinstance(w, dict) and isinstance(w.get("s"), (int, float))
            and start - 1 <= w["s"] <= end + 1][:_WORDS_MAX]


@router.post("/api/jobs/{jid}/clips/{cid}/edit")
async def edit_clip(request: Request, jid: str, cid: str) -> dict:
    """Change one clip the way a written note asks: "end 2 seconds earlier", "bigger captions", "new title: ...".

    Nothing is re-rendered here. The change is put on the clip and saved, which is exactly what the re-make button
    then renders — the same split `edit.apply` was written for. A note the editor cannot act on is a 400 with a
    sentence showing two notes it can."""
    u = _me(request)
    body = await _body(request)
    note = str(body.get("text") or "").strip()
    if not note:
        raise HTTPException(400, "Write what to change first.")
    _throttle("edit:" + u.id, 60, 60, "That is a lot of edits at once. Give it a moment.")
    job = _job_or_404(jid)
    clip = _clip_or_404(job, cid)
    if clip.get("status") in ("queued", "rendering"):
        raise HTTPException(409, "This clip is still being made. Try again when it has finished.")
    try:
        change = edit.parse(note)                 # pure reading: no file, no network, nothing to clean up
    except Exception:                             # noqa: BLE001 - a note must never take the server down
        raise HTTPException(400, NOT_UNDERSTOOD)
    understood = {k: v for k, v in change.items() if k != "note"}
    if not understood:
        # An empty note already got its own sentence above; this is a note that reads as words, not as an edit.
        raise HTTPException(400, NOT_UNDERSTOOD)
    try:
        new = await run_in_threadpool(edit.apply, clip, change)
    except Exception:                             # noqa: BLE001 - clamps are supposed to make this impossible
        raise HTTPException(400, "That change could not be put on the clip. Try wording it differently.")
    if not isinstance(new, dict) or not new:
        raise HTTPException(400, "That change could not be put on the clip. Try wording it differently.")

    # A moved cut makes the translated captions wrong: they were timed against the old start and end, and a
    # caption drawn in the wrong place is worse than one that has to be asked for again.
    moved = (new.get("start"), new.get("end")) != (clip.get("start"), clip.get("end"))
    hint = str(change.get("note") or "")
    if moved and clip.get("translated"):
        new["translated"] = {}
        hint = (hint + " " if hint else "") + "The translations were cleared because the clip now starts or ends " \
                                              "somewhere else."
    clip.clear()
    clip.update(new)                              # in place: anything already holding this clip sees the change
    await run_in_threadpool(jobs.save, job)
    return {"clip": _public_clip(job, cid), "note": hint}


# ---------------------------------------------------------------- a clip's captions, in another language
@router.post("/api/jobs/{jid}/clips/{cid}/translate")
async def translate_clip(request: Request, jid: str, cid: str) -> dict:
    """The clip's caption words in another language, kept on the clip under clip["translated"][lang].

    The words keep their source-video times, the same clock `fixed_words` uses, so the renderer can draw them over
    the clip without guessing. One entry per language: translating again replaces that language and leaves the
    others alone. Nothing is re-rendered here."""
    u = _me(request)
    body = await _body(request)
    code = _check_lang(_wanted_lang(body))
    # Whose clip this is comes before whether this machine can translate: a clip that is not there is not there,
    # whatever is or isn't installed.
    job = _job_or_404(jid)
    clip = _clip_or_404(job, cid)
    if code not in ("", "en") and not translate.available():
        raise _no_engine()
    _throttle("clips:" + u.id, 30, 600, "That is a lot of translating at once. Give it a minute.")
    raw = _clip_words(job, clip)
    if not raw:
        raise HTTPException(400, "There are no caption words on this clip to translate yet. They are read from "
                                 "the video once it has finished.")
    try:
        words = await run_in_threadpool(translate.words, raw, code)
    except (ValueError, translate.TranslateError) as e:
        raise HTTPException(400, str(e) or "Those captions could not be translated.") from e
    if not words:
        raise HTTPException(400, "Those captions could not be translated. Try again, or pick another language.")

    kept = clip.get("translated")
    if not isinstance(kept, dict):
        kept = clip["translated"] = {}
    kept[code or "en"] = words
    await run_in_threadpool(jobs.save, job)
    return {"clip": _public_clip(job, cid), "lang": code or "en", "words": words}

# ---------------------------------------------------------------- the clip's own words, for the editor
@router.get("/api/jobs/{jid}/clips/{cid}/words")
def clip_words(jid: str, cid: str, request: Request) -> dict:
    """Every caption word of this clip, with the time it is spoken, so the editor can show a transcript.

    The times are source-video seconds, the same clock `fixed_words` uses and the same clock the renderer draws
    with, so a word clicked in the editor seeks the video to the right place. Words are returned for the clip's own
    span only: a clip is a part of a video, and the rest of it is not this clip's transcript.

    Nothing here is invented. A clip that has no transcript yet answers with an empty list and a sentence saying
    so, because "no words" and "the read failed" are different things and the page says which one it got."""
    _me(request)
    job = _job_or_404(jid)
    clip = _clip_or_404(job, cid)
    words = _clip_words(job, clip)
    # The rendered clip starts at the clip's own `start` in the video, so a word at 42 s of the source sits at 12 s
    # of the clip file when the clip begins at 30 s. Both numbers are sent: `s` is the source second the transcript
    # speaks of, `l` is where that same word is in the clip file the editor is playing.
    at = clip.get("start")
    at = float(at) if isinstance(at, (int, float)) else 0.0
    clean = [{"w": str(w.get("w") or ""), "s": float(w["s"]), "e": float(w.get("e") or w["s"]),
              "l": round(max(0.0, float(w["s"]) - at), 3)}
             for w in words if isinstance(w, dict) and isinstance(w.get("s"), (int, float))]
    return {"words": clean, "count": len(clean),
            "start": clip.get("start"), "end": clip.get("end"),
            "note": "" if clean else "This clip has no transcript words yet. They are read from the video while "
                                     "the clip is being made, so they appear once it has finished."}
