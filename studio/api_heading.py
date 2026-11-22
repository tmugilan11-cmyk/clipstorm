"""One real frame of a clip, with the heading a person is typing drawn on it.

The problem this answers: the clip editor's "Big text" box and its Title/Description boxes were blind. A person typed
a heading, pressed "Save and re-make clip", waited for a render, and only then saw whether the words fitted the frame,
whether the look drew them somewhere sensible, or whether they were cut off at the edge. That is the "not reliable"
complaint in its original form.

This route draws one frame from the clip's own video, at a second something is actually being said, with the person's
in-progress heading in the clip's own look and brand - the same `render.build_ass` call a finished clip takes. Nothing
is written to the clip, nothing is rendered to video, and nothing costs money.

    GET /api/jobs/{jid}/clips/{cid}/preview/heading?hook=...&at=...

The caption file is built with its own clock: the moment we want to show is placed at `_SHOWN_AT` seconds, and the
ffmpeg input is trimmed so that moment really is at `_SHOWN_AT`. (An `-ss` before the input would hand back a frame
whose timestamps start at zero, and the captions would then be drawn for a different second entirely.)
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import threading
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response

from . import brand, ctx, jobs, peek, render

router = APIRouter()

_SHOWN_AT = 1.0         # the second shown in the frame, on the caption file's own clock
_LEAD = 0.6             # words this much before it and after it are enough to fill a frame
_TAIL = 1.4
_TTL = 300.0
_MAX = 40

_CACHE: dict = {}
_LOCK = threading.Lock()


def _uid(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(401, "Sign in first.")
    return user.id


def _job_or_404(jid: str) -> dict:
    job = jobs.get(jid)
    if not job:
        raise HTTPException(404, "No such video.")
    if job.get("user") != ctx.uid():
        raise HTTPException(404, "No such video.")
    return job


def _clip_or_404(job: dict, cid: str) -> dict:
    for c in job.get("clips") or []:
        if c.get("id") == cid:
            return c
    raise HTTPException(404, "No such clip.")


def _words(clip: dict, job: dict) -> list:
    """The words this clip was cut from, in the clip's own time where possible."""
    got = clip.get("fixed_words") or job.get("words") or []
    return [w for w in got if isinstance(w, dict) and w.get("w") and isinstance(w.get("s"), (int, float))]


def _span(clip: dict) -> tuple:
    start = float(clip.get("start") or 0.0)
    end = float(clip.get("end") or (start + 6.0))
    return start, max(start + 0.5, end)


def _near(words: list, when: float) -> list:
    """The words around `when` (absolute video time), re-timed so `when` lands on `_SHOWN_AT`.

    Only the ones a frame can show are kept. A clip whose words are all far from the middle still gets a frame: the
    heading is drawn either way, and a heading is what the person is looking at."""
    out = []
    for w in words:
        s = float(w["s"]) - when + _SHOWN_AT
        e = float(w.get("e", w["s"])) - when + _SHOWN_AT
        if e < 0.0 or s > _SHOWN_AT + _TAIL:
            continue
        out.append({"w": str(w["w"]), "s": max(0.0, s), "e": max(0.02, e)})
    return out


def _draw(job: dict, clip: dict, hook: str, at: float) -> bytes:
    """Writes one JPEG and hands back its bytes. Raises RuntimeError with a sentence on any failure."""
    start, end = _span(clip)
    when = at if at else start + (end - start) / 2.0
    when = min(max(when, start + 0.05), end - 0.05)
    words = _near(_words(clip, job), when)
    style = str(clip.get("style") or "bounce")
    doc = brand.load(job.get("user") or "default")
    src_w = int(job.get("width") or 1080)
    src_h = int(job.get("height") or 1920)
    try:
        layout, _fg, hook_y, cap_y = render.geometry(src_w, src_h, clip.get("layout") or "blur")
    except Exception:      # noqa: BLE001 - an odd layout must not cost a preview
        layout, hook_y, cap_y = "blur", 300, 1380

    work = render._workdir()
    try:
        ass = render.build_ass(words, 0.0, _SHOWN_AT + _TAIL, hook or "", style,
                               clip.get("highlight_words") or [], hook_y, cap_y, brand=doc)
        (work / "h.ass").write_text(ass, encoding="utf-8")
        (work / "f").mkdir()
        for f in render_paths():
            shutil.copyfile(f, work / "f" / f.name)
        src, offset = peek.source(job, clip, work)
        # Jump the input to the second before the one we want, so the reader starts close to the right frame. The
        # input seek renumbers its own first frame as zero, so `trim=start=_SHOWN_AT` then lands on exactly the moment
        # the caption file was built for. (A trim without the seek leaves the source's own timestamps in place, and
        # the captions would be drawn for a different second of the page's life entirely.)
        seek = max(0.0, (when - offset) - _SHOWN_AT)
        fit = (f"scale={render.W}:{render.H}:force_original_aspect_ratio=increase,"
               f"crop={render.W}:{render.H},setsar=1")
        p = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-ss", f"{seek:.3f}", "-i", str(src), "-frames:v", "1",
             "-vf", f"trim=start={_SHOWN_AT:.3f},{fit},ass=h.ass:fontsdir=f", "-q:v", "3", "shot.jpg"],
            cwd=str(work), capture_output=True, text=True, encoding="utf-8", errors="replace",
            creationflags=render.NO_WINDOW, timeout=90)
        out = Path(work) / "shot.jpg"
        if not out.is_file() or out.stat().st_size < 500:
            raise RuntimeError((p.stderr or "").strip()[-300:] or "The frame could not be drawn.")
        return out.read_bytes()
    finally:
        shutil.rmtree(str(work), ignore_errors=True)


def render_paths():
    from . import config
    return sorted(config.FONTS_DIR.glob("*.ttf"))


@router.get("/api/jobs/{jid}/clips/{cid}/preview/heading")
async def heading_preview(request: Request, jid: str, cid: str,
                          hook: str = Query("", max_length=120),
                          at: float = Query(0.0, ge=0.0, le=36000.0)) -> Response:
    """A frame of this clip with `hook` drawn in the clip's own look. Read-only, and cached for a few minutes."""
    uid = _uid(request)
    job = _job_or_404(jid)
    clip = _clip_or_404(job, cid)
    said = (hook or "").strip()[:120]
    key = hashlib.sha1(repr((uid, jid, cid, said, round(at, 2), clip.get("style"), clip.get("layout"),
                             clip.get("version"))).encode("utf-8")).hexdigest()
    now = time.monotonic()
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and now - hit[0] < _TTL:
            return Response(hit[1], media_type="image/jpeg",
                            headers={"Cache-Control": "private, max-age=120"})
    try:
        data = _draw(job, clip, said, at)
    except HTTPException:
        raise
    except Exception as e:      # noqa: BLE001 - a preview that cannot be made says why, in words
        raise HTTPException(502, "That frame could not be drawn: " + str(e)[:200])
    with _LOCK:
        if len(_CACHE) >= _MAX:
            for k in sorted(_CACHE, key=lambda k: _CACHE[k][0])[: max(1, _MAX // 4)]:
                _CACHE.pop(k, None)
        _CACHE[key] = (now, data)
    return Response(data, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=120"})
