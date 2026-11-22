"""Sound over HTTP: the meme noises and music beds a clip can be given, and the settings behind them.

`studio/meme.py` synthesises its nine noises with numpy and `studio/music.py` synthesises its four beds; neither
ships an audio file. This module is only the doorway, so the page can offer the moods and ask for the cache to be
built without knowing how any of it works. `server.py` grows one line: `app.include_router(api_sound.router)`.

It deliberately does not import `server.py`, for the same circular-import reason as every other `api_*` module.

    GET   /api/moods          the meme noises and the music beds, and which are already built
    GET   /api/sounds/{kind}/{mood}
                              the wav itself, so a page can play one before a clip uses it
    POST  /api/moods/prime    build whichever are missing; safe to call twice

Building the cache is the slow part (a few seconds of numpy per sound), so it happens here, once, and the result
is a folder of WAVs the renderer reuses. Nothing here renders a clip: `studio/jobs.py` owns that."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from . import auth, meme, music

router = APIRouter()


def _me(request: Request):
    """The signed-in person for this request, exactly as `server._me` would return them."""
    u = getattr(request.state, "user", None)
    if not u or not getattr(u, "id", None):
        raise HTTPException(401, "Please sign in.")
    return u


def _throttle(key: str, limit: int, window: int, msg: str) -> None:
    """The same rate limit `server._throttle` applies, without importing server.py.

    Building the cache writes a few megabytes and pins a core for a moment, so a page that asks in a loop must be
    told to slow down."""
    try:
        auth.throttle(key, limit, window)
    except auth.AuthError:
        raise HTTPException(429, msg)


def _note(row: dict) -> str:
    """One plain sentence about a mood, taken from whatever the mood document carries.

    The two modules describe their moods with slightly different keys, so this reads the ones that exist instead of
    demanding a shape neither of them promises."""
    for key in ("hint", "note", "label", "effect", "treatment"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


@router.get("/api/moods")
def moods(request: Request) -> dict:
    """Every meme noise and music bed, and whether its audio is already on disk.

    `ready` is per mood, so a page can show "build it" only where building is actually needed."""
    _me(request)
    try:
        noises = meme.load_moods()
    except Exception:                 # noqa: BLE001 - a broken mood file must not fail the page
        noises = dict(meme.MOODS)
    try:
        beds = music.MOODS
    except Exception:                 # noqa: BLE001
        beds = {}

    # Readiness is a look at the folder, never a call to make_sounds: that writes every wav, and a page that only
    # wanted to know what exists must not spend a few seconds of numpy finding out.
    rows = []
    for name, row in (noises or {}).items():
        row = row if isinstance(row, dict) else {}
        rows.append({"name": name, "kind": "meme", "note": _note(row), "ready": meme.sound_ready(name)})
    for name, row in (beds or {}).items():
        row = row if isinstance(row, dict) else {}
        try:
            bed = music.bed_path(name)
        except Exception:             # noqa: BLE001
            bed = None
        rows.append({"name": name, "kind": "music", "note": _note(row), "ready": _have(bed)})

    return {"moods": rows, "count": len(rows),
            "meme": sorted(noises or {}), "music": sorted(beds or {})}


def _have(path) -> bool:
    """Whether an audio file is already on disk. A path that cannot even be built is simply not ready."""
    try:
        return bool(path) and path.exists()
    except OSError:
        return False


def _meme_file(mood: str):
    """The wav behind one meme noise, or None when it is not on disk yet.

    A mood is not a file name: `hype` is airhorn then bass_drop, and half the noises live in `mine/`. So the file is
    found the same way a render finds it, through the mood's own `sound` entry. Readiness is checked first, because
    `_resolve_sound` builds the whole cache when it finds nothing, and a play button must never start that."""
    try:
        row = meme.load_moods().get(mood)
    except Exception:                 # noqa: BLE001 - a broken mood file is simply "no such sound"
        return None
    if not isinstance(row, dict):
        return None
    try:
        if not meme.sound_ready(mood):
            return None
        # `_resolve_sound` is the one place that knows both the shipped and the imported files; the public helpers
        # name them but do not return a path, and a second copy of that search would drift from it.
        return meme._resolve_sound(row.get("sound"))
    except (RuntimeError, OSError):
        return None


@router.api_route("/api/sounds/{kind}/{mood}", methods=["GET", "HEAD"])
def sound_file(kind: str, mood: str, request: Request):
    """One sound as a wav, so the Sounds page can play what a clip would get.

    A 404 here means one thing the page can say plainly: this sound has not been built yet. It is not a decode
    failure and not a missing route.

    HEAD is answered as well as GET on purpose. The page asks with a HEAD before it plays, because a missing sound
    and a sound this browser cannot decode arrive at the audio element as the same error; without HEAD that cheap
    question came back 405 and the page had to say "the server could not hand over the sound" for a file that was
    sitting right there."""
    _me(request)
    key = str(mood or "").strip().lower()
    kind = str(kind or "").strip().lower()
    if kind == "music":
        # `music._mood` quietly answers "chill" for any other word, so the list has to be checked here or every
        # typo would serve the chill bed under the name that was asked for.
        if key not in music.MOODS:
            raise HTTPException(404, "There is no music bed called %s." % (key or "(none)"))
        path = music.bed_path(key)
    elif kind == "meme":
        if not key:
            raise HTTPException(404, "There is no meme noise called (none).")
        path = _meme_file(key)
        if path is None:
            raise HTTPException(404, "The %s sound has not been made yet. Build the sounds first." % key)
    else:
        raise HTTPException(404, "Sounds are served as music or meme, not %s." % (kind or "(none)"))

    if not _have(path):
        raise HTTPException(404, "The %s sound has not been made yet. Build the sounds first." % key)
    return FileResponse(path, headers={"Cache-Control": "private, max-age=300"})


@router.post("/api/moods/prime")
async def prime(request: Request) -> dict:
    """Build whichever sounds and beds are missing, then say what is there.

    Idempotent: `make_sounds` and `make_beds` skip a file that already exists, so pressing the button twice costs
    a directory listing rather than another few seconds of numpy."""
    u = _me(request)
    _throttle("moods:" + u.id, 6, 300, "The sounds were just built. Give it a moment before asking again.")

    def build() -> dict:
        out = {"sounds": 0, "beds": 0, "errors": []}
        try:
            out["sounds"] = len(meme.make_sounds())
        except Exception as e:        # noqa: BLE001 - one failing mood must not lose the rest
            out["errors"].append("Sounds: %s" % (str(e)[:160] or "could not be built"))
        try:
            out["beds"] = len(music.make_beds(music.bed_path("hype").parent))
        except Exception as e:        # noqa: BLE001
            out["errors"].append("Music: %s" % (str(e)[:160] or "could not be built"))
        return out

    result = await run_in_threadpool(build)
    return {**moods(request), "built": result}
