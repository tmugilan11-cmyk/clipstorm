"""The catalogue over HTTP: every caption look and every clip format, as lists a page can draw.

`studio/captions.py` already carries the thirty-two subtitle looks; `studio/formats.py` already knows the eight
shapes a clip can take and how to plan one. This module is only the doorway, so the page never has to hardcode a
list that would then drift away from the code that really does the work. `server.py` grows one line:
`app.include_router(api_style.router)`.

It deliberately does not import `server.py`: `server.py` imports this module to mount the router, so
`from .server import _me` would come back around on itself. The signed-in person is read off the request instead.

    GET   /api/captions/styles   every subtitle look, with its plain name and whether it is the default
    GET   /api/formats           every clip shape, with how many parts it needs and a hint
    POST  /api/formats/plan      plan one shape against some words, without rendering anything

Nothing here writes to disk, spends money, or contacts another machine."""
from __future__ import annotations

import re
import shutil
import subprocess
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Request

from . import captions, config, formats

router = APIRouter()

# The three looks `render.py` has always drawn itself, kept first in the list so the picker opens on familiar ground.
_HOUSE = ("bounce", "hype", "clean")

_MAX_WORDS = 4000       # planning against more words than this tells nobody anything useful


def _me(request: Request):
    """The signed-in person for this request, exactly as `server._me` would return them.

    Read off the request rather than imported from `server.py`, because `server.py` imports this module to mount
    the router and the import would come straight back."""
    u = getattr(request.state, "user", None)
    if not u or not getattr(u, "id", None):
        raise HTTPException(401, "Please sign in.")
    return u


@router.get("/api/captions/styles")
def caption_styles(request: Request) -> dict:
    """Every subtitle look this server can draw, plus the house looks `render.py` handles without help.

    Each entry is `{name, label, house, anim}`. `house` marks the three that render without the newer captions
    code, so a page can say which are the long-standing ones instead of presenting all thirty-two as equivalent.
    `anim` is the motion the look uses (`punch`, `karaoke`, ...), which a page needs in order to show that motion
    moving instead of printing its name."""
    _me(request)
    names = list(captions.style_names())
    house = [n for n in _HOUSE if n not in names]      # render.py draws these itself, so captions never lists them

    def row(name: str, is_house: bool) -> dict:
        # A house look has no entry in captions.ANIM: render.py gives it its own motion, so the name it reports is
        # the look itself. Saying that is better than an empty string a page would have to guess about.
        try:
            anim = str(captions.ANIM.get(name) or ("house" if is_house else ""))
        except Exception:                              # noqa: BLE001 - a motion name must never fail the catalogue
            anim = ""
        return {"name": name, "label": _label(name), "house": is_house, "anim": anim}

    plain = sorted(names)
    return {
        "default": "bounce",
        "styles": [row(n, True) for n in house] + [row(n, False) for n in plain],
        "count": len(house) + len(plain),
        "fonts": _fonts(),
    }


def _fonts() -> list:
    """Every caption font on this machine, for a picker that can show the real letterforms.

    A person choosing a font used to have to type a file name from memory, which is why the control was called
    unreliable: a typo silently fell back to the style's own face and nothing said so. Each row carries the family
    name ffmpeg needs, the file the browser can load it from, and whether the letters in a clip are likely to be
    drawn by it (a Latin font cannot draw Japanese, so it is offered for Latin text only)."""
    rows = []
    for family, file_name in sorted(captions.FONT_FILES.items()):
        path = config.ROOT / "studio" / "fonts" / file_name
        if not path.is_file():
            continue
        cjk = bool(re.search(r"JP|SC|Mplus|Yusei", file_name))
        rows.append({"name": family, "file": file_name, "url": "/assets/font/" + quote(file_name), "cjk": cjk})
    return rows


def _label(name: str) -> str:
    """The plain name for a look, falling back to the raw one rather than inventing a title.

    `captions.label` only knows the looks it ships; anything else is a name a person chose, and tidying its
    capitalisation here would hide a mismatch instead of showing it."""
    try:
        return captions.label(name) or name
    except Exception:            # noqa: BLE001 - a label must never fail the whole catalogue
        return name


@router.get("/api/formats")
def clip_formats(request: Request) -> dict:
    """Every clip shape, as `formats.public()` describes it: the id, the label, how many parts it needs, a hint."""
    _me(request)
    rows = formats.public()
    if not isinstance(rows, list):
        rows = []
    return {"formats": rows, "count": len(rows), "default": "moment"}


@router.post("/api/formats/plan")
async def plan_format(request: Request) -> dict:
    """Plan one shape against some words, and hand back the parts and cards it would use.

    This is the same `formats.plan` the job pipeline stores on a clip, so a page can preview a shape before asking
    for it. It renders nothing: no ffmpeg, no files. Both body shapes are accepted, the flat one
    (`{"format": ..., "words": [...]}`) and the nested one (`{"pick": {"format": ..., "words": [...]}}`); when
    both carry words, the top level wins."""
    _me(request)
    try:
        body = await request.json()
    except ValueError as e:
        raise HTTPException(400, "That plan could not be read. Try again from the page.") from e
    if not isinstance(body, dict):
        raise HTTPException(400, "That plan could not be read. Try again from the page.")

    nested = body.get("pick") if isinstance(body.get("pick"), dict) else None
    pick = nested or body
    name = str(pick.get("format") or pick.get("fmt") or "").strip()
    if name and name not in formats.FORMATS:
        known = ", ".join(sorted(formats.FORMATS))
        raise HTTPException(400, f"That is not a clip shape PeakCut knows. Choose one of: {known}.")

    # Words are read from the top-level body or from inside `pick`, because both shapes arrive: the page
    # plans with {"format": ..., "words": [...]} and the nested shape is {"pick": {..., "words": [...]}}.
    # The top level wins when both carry words, which is said here so the two shapes stay predictable.
    words = body.get("words")
    if words is None and nested is not None:
        words = nested.get("words")
    if words is not None and not isinstance(words, list):
        raise HTTPException(400, "The words to plan against must be a list.")
    words = (words or [])[:_MAX_WORDS]
    if words and not all(isinstance(w, dict) and "s" in w for w in words):
        raise HTTPException(400, "Those words cannot be planned: each needs a spoken time ('s') and an end time ('e') in seconds.")

    try:
        planned = formats.plan(pick, words)
    except Exception as e:       # noqa: BLE001 - a bad pick is a 400 with a sentence, never a traceback
        raise HTTPException(400, str(e) or "That shape could not be planned.") from e
    return {"format": formats.fmt_of(pick), "plan": planned}


# --------------------------------------------------------------------------- one real frame, as a look preview
# The Brand page shows what a clip would look like with a chosen caption look and the person's own colours.
# It does that with a real frame, drawn by the same code a clip is drawn with: `render.build_ass` writes the
# subtitle file and ffmpeg burns it onto a plain background. Nothing is invented, so what the preview shows
# is what the render will draw. Frames are kept for a few minutes, because a person changes one field at a time.

import asyncio                            # noqa: E402 - the per-key wait, below the router the file is known for
import hashlib                            # noqa: E402 - the cache key, below the router the file is known for
import threading                          # noqa: E402
import time as _time                      # noqa: E402

from fastapi import Response              # noqa: E402
from fastapi.concurrency import run_in_threadpool   # noqa: E402

from . import brand, render               # noqa: E402
_PREVIEW_TTL = 600.0        # seconds a drawn frame stays worth reusing
_PREVIEW_MAX = 24           # frames kept at once; the oldest one is dropped first
_PREVIEW_LOCK = threading.Lock()
_PREVIEW_CACHE: dict[str, tuple[float, bytes]] = {}
_PREVIEW_PENDING: dict[str, asyncio.Event] = {}   # frames being drawn right now, so identical requests share one draw


async def _draw_once(key: str, cache: dict, pending: dict, lock: threading.Lock, fn, args: tuple) -> bytes:
    """Draw `fn(*args)` once, even when several identical requests arrive together, and cache the result.

    The first caller for `key` does the drawing; the rest wait for it and share what it made, so the same
    frame is never rendered twice side by side. The formats page fires several previews at once, which used
    to make this race reachable. The clock is taken after the draw, so the entry's TTL counts from when the
    frame was finished rather than from when it was asked for. A draw that fails stores nothing and wakes the
    waiters, so the next caller tries its own."""
    while True:
        with lock:
            mine = pending.get(key)
            if mine is None:
                mine = asyncio.Event()     # this caller draws; the others wait on this event
                pending[key] = mine
                owner = True
            else:
                owner = False
        if owner:
            try:
                out = await run_in_threadpool(fn, *args)
            except BaseException:          # noqa: BLE001 - the mark must go and the waiters must wake on any failure
                with lock:
                    pending.pop(key, None)
                mine.set()
                raise
            with lock:
                # Stored before the waiters are woken, so the first thing a woken caller finds is the frame.
                cache[key] = (_time.monotonic(), out)
                pending.pop(key, None)
            mine.set()
            return out
        # Someone else is already drawing this exact thing: wait for them, then take the frame they stored
        # instead of drawing it a second time. When their draw failed, nothing was stored and the loop lets
        # this caller draw its own.
        await mine.wait()
        with lock:
            hit = cache.get(key)
        if hit:
            return hit[1]


# The sentence every preview says: short, with one keyword worth shouting, spread over 2.4 seconds.
_SAMPLE = [
    {"w": "he", "s": 0.00, "e": 0.24}, {"w": "did", "s": 0.24, "e": 0.52},
    {"w": "not", "s": 0.52, "e": 0.80}, {"w": "see", "s": 0.80, "e": 1.24},
    {"w": "that", "s": 1.24, "e": 1.60}, {"w": "coming", "s": 1.60, "e": 2.10},
    {"w": "at", "s": 2.10, "e": 2.24}, {"w": "all", "s": 2.24, "e": 2.60},
]
_SAMPLE_HOOK = "he did not see that coming"
_SAMPLE_KEY = "coming"                 # the keyword drawn in the brand's key colour, a word other than the one spoken
_SAMPLE_AT = 1.0                       # the moment the frame shows: mid-sentence, one word lit

def _sample_for(name: str) -> tuple[list, str, list, str]:
    """All video-style previews use the same source sentence."""
    return _SAMPLE, _SAMPLE_HOOK, [_SAMPLE_KEY], _SAMPLE_HOOK


def _known_look(name: str) -> bool:
    """True when `name` is a look this server can draw: the three house ones or any captions.py look."""
    names = set(captions.style_names()) | set(render.STYLES)
    return name in names


def _style_preview(uid: str, style: str, hook: str, doc: dict) -> bytes:
    """Draw one 1080x1920 frame: the sample sentence and hook in `style`, dressed with this person's brand."""
    sample, default_hook, keys, _ = _sample_for(style)
    words = hook if hook != _SAMPLE_HOOK else default_hook
    ass = render.build_ass(sample, 0.0, 2.6, words, style, keys, 300, 1380, brand=doc)
    work = render._workdir()           # a short, writable folder: the same one renders use
    try:
        (work / "preview.ass").write_text(ass, encoding="utf-8")
        (work / "f").mkdir()
        for f in config.FONTS_DIR.glob("*.ttf"):
            shutil.copyfile(f, work / "f" / f.name)
        # The clock has to reach the ass filter as real time: a `-ss` before the input would hand back the first
        # frame anyway (a lavfi source does not seek), and an output `-ss` runs after the subtitles are burned.
        # A trim in front of the ass filter keeps the timestamps, so the frame is genuinely at _SAMPLE_AT.
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error",
             "-f", "lavfi", "-i", "color=c=0x141821:s=1080x1920:r=30:d=4",
             "-frames:v", "1", "-vf", f"trim=start={_SAMPLE_AT:.2f},ass=preview.ass:fontsdir=f",
             "-q:v", "3", "preview.jpg"],
            cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace",
            creationflags=render.NO_WINDOW, timeout=60)
        out = work / "preview.jpg"
        if not out.is_file() or out.stat().st_size < 500:
            raise RuntimeError("The preview frame could not be drawn.")
        return out.read_bytes()
    finally:
        shutil.rmtree(work, ignore_errors=True)


@router.get("/api/style/preview")
async def style_preview(request: Request, style: str = Query("", max_length=40),
                        hook: str = Query("", max_length=120),
                        font: str = Query("", max_length=60),
                        c_text: str = Query("", max_length=7), c_spoken: str = Query("", max_length=7),
                        c_outline: str = Query("", max_length=7), c_key: str = Query("", max_length=7),
                        c_box: str = Query("", max_length=7),
                        hook_text: str = Query("", max_length=7), hook_box: str = Query("", max_length=7),
                        lang: str = Query("", max_length=2)) -> Response:
    """One real frame with a caption look on it, so a page can show a look before anyone renders anything.

    The frame is the sample sentence at the moment one word is being said, drawn by `render.build_ass` with the
    person's own brand over it - the same call a real clip takes. The colour and font query fields let a page
    preview edits that are still in the form, not yet saved: what is sent is sanitised through `brand.normalise`,
    so a malformed value falls back to what is saved rather than reaching the renderer. Results are cached for a
    few minutes per person and look, because the Brand page redraws on every small change."""
    uid = _me(request).id
    name = (style or "").strip().lstrip("#").lower() or "bounce"
    if not _known_look(name):
        known = ", ".join(sorted(captions.style_names()) + sorted(render.STYLES))
        raise HTTPException(400, f"That is not a caption look PeakCut knows. Choose one of: {known}.")
    words = (hook or "").strip() or _SAMPLE_HOOK

    saved = brand.load(uid)
    raw = dict(saved)
    colors = {}
    for field, value in (("text", c_text), ("spoken", c_spoken), ("outline", c_outline),
                         ("key", c_key), ("box", c_box), ("hook_text", hook_text), ("hook_box", hook_box)):
        v = (value or "").strip().lstrip("#")
        if v:
            if field in ("hook_text", "hook_box"):
                raw[field] = v
            else:
                colors[field] = v
    if colors:
        raw["colors"] = {**saved.get("colors", {}), **colors}
    f = (font or "").strip()
    if f:
        raw["font"] = f
    l = (lang or "").strip().lower()
    if l:
        raw["lang"] = l
    doc = brand.normalise(raw)          # junk in a query field falls back to the safe default here

    key = hashlib.sha1(repr((uid, name, words, doc)).encode("utf-8")).hexdigest()
    now = _time.monotonic()
    with _PREVIEW_LOCK:
        hit = _PREVIEW_CACHE.get(key)
        if hit and now - hit[0] < _PREVIEW_TTL:
            hit = (now, hit[1])                       # a used frame stays worth keeping
            _PREVIEW_CACHE[key] = hit
            return Response(hit[1], media_type="image/jpeg",
                            headers={"Cache-Control": "private, max-age=300"})
        if len(_PREVIEW_CACHE) >= _PREVIEW_MAX:       # the oldest frame goes, whoever asked for it
            oldest = min(_PREVIEW_CACHE, key=lambda k: _PREVIEW_CACHE[k][0])
            _PREVIEW_CACHE.pop(oldest, None)

    jpg = await _draw_once(key, _PREVIEW_CACHE, _PREVIEW_PENDING, _PREVIEW_LOCK,
                           _style_preview, (uid, name, words, doc))
    return Response(jpg, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=300"})


# ------------------------------------------------------------------ the same look, moving
#
# A still frame cannot show a caption that bounces, shakes, sweeps in or lights up word by word, and the person
# asked to SEE the motion rather than read its name. So this draws the same sample sentence as a short clip that
# a page can loop. It is deliberately small: half resolution, 12 frames a second, three seconds. At that size the
# motion is completely legible and the file stays in the tens of kilobytes, which matters because the formats page
# shows one of these per look.

_MOTION_TTL = 3600.0        # the motion of a look does not change between visits, so it is worth keeping longer
_MOTION_MAX = 40            # looks kept at once
_MOTION_LOCK = threading.Lock()
_MOTION_CACHE: dict[str, tuple[float, bytes]] = {}
_MOTION_PENDING: dict[str, asyncio.Event] = {}    # motions being drawn right now, so identical requests share one draw


def _style_motion(uid: str, style: str, hook: str, doc: dict) -> bytes:
    """Draw the sample sentence in `style` as a three-second clip, so a page can show the motion looping."""
    sample, default_hook, keys, _ = _sample_for(style)
    words = hook if hook != _SAMPLE_HOOK else default_hook
    span = float(sample[-1]["e"]) if sample else 2.6
    ass = render.build_ass(sample, 0.0, span, words, style, keys, 150, 690, brand=doc)
    work = render._workdir()
    try:
        (work / "motion.ass").write_text(ass, encoding="utf-8")
        (work / "f").mkdir()
        for f in config.FONTS_DIR.glob("*.ttf"):
            shutil.copyfile(f, work / "f" / f.name)
        # Same source shape as the still: a quarter-resolution portrait frame at 12 fps. `-t` is set past the last
        # word so the final word is seen settling rather than cut mid-bounce.
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error",
             "-f", "lavfi", "-i", f"color=c=0x141821:s=540x960:r=12:d={span + 0.4:.2f}",
             "-t", f"{span + 0.2:.2f}",
             "-vf", "ass=motion.ass:fontsdir=f",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "30",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", "motion.mp4"],
            cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace",
            creationflags=render.NO_WINDOW, timeout=90)
        out = work / "motion.mp4"
        if not out.is_file() or out.stat().st_size < 900:
            raise RuntimeError("The moving preview could not be drawn.")
        return out.read_bytes()
    finally:
        shutil.rmtree(work, ignore_errors=True)


@router.get("/api/style/motion")
async def style_motion(request: Request, style: str = Query("", max_length=40),
                       hook: str = Query("", max_length=120)) -> Response:
    """A three-second clip of one caption look moving, for a page to loop.

    The formats page shows every look; a still cannot show that "bounce" bounces and "typewriter" types, which is
    the one thing a person needs to see before choosing. Same drawing code as a real clip, same brand, half the
    resolution and 12 frames a second so the file is small enough to load dozens of."""
    uid = _me(request).id
    name = (style or "").strip().lstrip("#").lower() or "bounce"
    if not _known_look(name):
        known = ", ".join(sorted(captions.style_names()) + sorted(render.STYLES))
        raise HTTPException(400, f"That is not a caption look PeakCut knows. Choose one of: {known}.")
    words = (hook or "").strip() or _SAMPLE_HOOK
    doc = brand.load(uid)
    key = hashlib.sha1(repr(("motion", uid, name, words, doc)).encode("utf-8")).hexdigest()
    now = _time.monotonic()
    with _MOTION_LOCK:
        hit = _MOTION_CACHE.get(key)
        if hit and now - hit[0] < _MOTION_TTL:
            _MOTION_CACHE[key] = (now, hit[1])          # a used clip stays worth keeping
            return Response(hit[1], media_type="video/mp4",
                            headers={"Cache-Control": "private, max-age=1800"})
        if len(_MOTION_CACHE) >= _MOTION_MAX:
            oldest = min(_MOTION_CACHE, key=lambda k: _MOTION_CACHE[k][0])
            _MOTION_CACHE.pop(oldest, None)
    mp4 = await _draw_once(key, _MOTION_CACHE, _MOTION_PENDING, _MOTION_LOCK,
                           _style_motion, (uid, name, words, doc))
    return Response(mp4, media_type="video/mp4", headers={"Cache-Control": "private, max-age=1800"})
