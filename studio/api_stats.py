"""What a video has done over HTTP: its own numbers, its channel's, and the deeper analytics call.

`studio/ytstats.py` already knows how to read a video id out of any link shape, how to ask YouTube's own API, and
how to explain the answer when YouTube says no. This module is only the doorway. `server.py` grows one line:
`app.include_router(api_stats.router)`.

It deliberately does not import `server.py`: `server.py` imports this module to mount the router, so
`from .server import _me` would come back around on itself.

    GET   /api/stats/video?url=&key=         one video: its numbers, and what they mean next to its peers
    GET   /api/stats/channel?handle=&key=    the channel id behind a handle, and its newest shorts
    POST  /api/stats/deep                    the deeper analytics call, which needs a separate token

Every route is read-only and per-person. The key travels with the request and is never stored, logged, or echoed
back: a response says whether the key worked, never what it was."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool

from . import auth, ytstats

router = APIRouter()

_KEY_MAX = 200          # a real Data API key is 39 characters; anything near this is not one
_ID_MAX = 64


def _me(request: Request):
    """The signed-in person for this request, exactly as `server._me` would return them."""
    u = getattr(request.state, "user", None)
    if not u or not getattr(u, "id", None):
        raise HTTPException(401, "Please sign in.")
    return u


def _throttle(key: str, limit: int, window: int, msg: str) -> None:
    """The same rate limit `server._throttle` applies. Every call here spends part of the operator's own YouTube
    quota, so a page in a loop must be told to slow down rather than burning it."""
    try:
        auth.throttle(key, limit, window)
    except auth.AuthError:
        raise HTTPException(429, msg)


def _key(raw: str) -> str:
    """The Data API key, or a plain 400. Never returned, never logged."""
    key = str(raw or "").strip()
    if not key:
        raise HTTPException(400, "A YouTube Data API key is needed for this. Paste one from the Google Cloud "
                                 "console, or leave these numbers alone.")
    if len(key) > _KEY_MAX:
        raise HTTPException(400, "That does not look like a YouTube API key. Check it and try again.")
    return key


def _wrapped(fn, *a, **kw):
    """Call ytstats and turn its own error type into a plain sentence.

    `ytstats.YouTubeError` carries a message written for a person, so it becomes a 400 with that message. Anything
    else is a genuine surprise and becomes the same 400 with a fixed sentence, because a traceback tells nobody
    which field to fix."""
    try:
        return fn(*a, **kw)
    except ytstats.YouTubeError as e:
        raise HTTPException(400, str(e) or "YouTube would not answer that.") from e
    except Exception as e:            # noqa: BLE001 - the network can fail in ways nobody enumerated
        raise HTTPException(400, "YouTube could not be reached just now. Try again in a moment.") from e


@router.get("/api/stats/video")
async def video_stats(request: Request, url: str = Query("", max_length=400),
                      key: str = Query("", max_length=_KEY_MAX)) -> dict:
    """One video's own numbers, read from its link. A link PeakCut cannot read is a 400, not an empty answer."""
    u = _me(request)
    api_key = _key(key)
    vid = ytstats.vid_id(url)
    if not vid:
        raise HTTPException(400, "That is not a YouTube link PeakCut can read. Paste a watch or shorts link.")
    _throttle("stats:" + u.id, 60, 60, "That is a lot of YouTube calls at once. Give it a moment.")
    rows = await run_in_threadpool(_wrapped, ytstats.videos, [vid], api_key)
    if not rows:
        raise HTTPException(400, "YouTube has no video with that id. Check the link.")
    return {"vid": vid, "video": rows[0], "wanted": ytstats.public()}


@router.get("/api/stats/channel")
async def channel_stats(request: Request, handle: str = Query("", max_length=_ID_MAX),
                        key: str = Query("", max_length=_KEY_MAX), n: int = Query(10, ge=1, le=50)) -> dict:
    """The channel id behind a handle, plus its newest shorts. Same rules as the video route."""
    u = _me(request)
    api_key = _key(key)
    name = str(handle or "").strip().lstrip("@")
    if not name:
        raise HTTPException(400, "Which channel? Paste a handle like @somebody.")
    if len(name) > _ID_MAX:
        raise HTTPException(400, "That is too long to be a channel handle.")
    _throttle("stats:" + u.id, 60, 60, "That is a lot of YouTube calls at once. Give it a moment.")
    cid = await run_in_threadpool(_wrapped, ytstats.channel_id, name, api_key)
    if not cid:
        raise HTTPException(400, "YouTube has no channel with that handle.")
    shorts = await run_in_threadpool(_wrapped, ytstats.latest_shorts, cid, api_key, n)
    return {"handle": name, "channel": cid, "shorts": shorts, "wanted": ytstats.public()}


@router.post("/api/stats/deep")
async def deep_stats(request: Request) -> dict:
    """The deeper analytics call, which needs an OAuth token as well as the key.

    The token comes from the browser's own Google sign-in and is used for this one call: it is not stored, not
    logged, and not kept on the job."""
    u = _me(request)
    try:
        body = await request.json()
    except ValueError as e:
        raise HTTPException(400, "That request could not be read. Try again from the page.") from e
    if not isinstance(body, dict):
        raise HTTPException(400, "That request could not be read. Try again from the page.")

    api_key = _key(body.get("key"))
    token = str(body.get("token") or "").strip()
    if not token:
        raise HTTPException(400, "The deeper analytics need a Google sign-in token as well as the key.")
    vid = ytstats.vid_id(str(body.get("vid") or body.get("url") or ""))
    if not vid:
        raise HTTPException(400, "That is not a YouTube link PeakCut can read.")

    _throttle("deep:" + u.id, 20, 300, "That is a lot of analytics calls at once. Give it a minute.")
    out = await run_in_threadpool(_wrapped, ytstats.deep, vid, api_key, token)
    return {"vid": vid, "deep": out, "wanted": ytstats.public()}
