"""What people typed to find the channel, and which videos gained the views, in the shape the Trends page draws.

`studio/ytstats.py` already knows how to ask Google. This module is the doorway, plus the honest fallback for a
PeakCut with no YouTube connection: an empty list and a sentence that says why, never a made-up number.

Two sources, one shape:

* **YouTube Analytics** when a YouTube account is connected. The search terms come from the traffic source
  detail, filtered to searches, which is what the YouTube Studio "Search terms" report reads.
* **Nothing** when it is not. There is no local stand-in for a search term: PeakCut does not record what
  people search on YouTube, so the honest answer is an empty list and a note naming the missing connection.

One route is deliberately not about other people's videos. `GET /api/trends/videos` answers with this
channel's own videos ranked by views, because YouTube's public trending chart needs a YouTube Data API key
and PeakCut does not keep one. The note on that route says so in as many words.

Saved search terms are the operator's own list, kept in `users/<id>/trends.json` and written in one move so a
crash cannot leave half a list behind. A hand-edited or broken file reads as an empty list, never an error.

    GET    /api/trends/status
    GET    /api/trends/searches?days=28&limit=25
    GET    /api/trends/videos?days=28&limit=25
    GET    /api/trends/saved
    POST   /api/trends/saved        {"term": "..."}
    DELETE /api/trends/saved?term=...

Every answer carries `note`, so the page can say which source it is looking at instead of guessing, and no
route fails just because Google did. It deliberately does not import `server.py`.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool

from . import accounts, auth, config, ytstats

router = APIRouter()

_CACHE: dict = {}          # one small cache: a page reload must not spend quota
_CACHE_SECONDS = 120.0

_FILE = "trends.json"      # under the person's own folder, next to learn.json and the rest
MAX_SAVED = 50             # the cap the page promises
MAX_TERM = 120             # longer than any search term worth keeping, and short enough to draw

# A term's share of the search views this range, in words. The shares are YouTube's own views counted up
# here, so the word describes a number the server did receive. `_interest` reads these from the top down.
_INTEREST = ((20.0, "Very high"), (10.0, "High"), (4.0, "Medium"), (1.0, "Low"))

_NO_CONNECTION = ("No YouTube account is connected, so PeakCut cannot read what people typed to find your "
                  "videos. Connect a channel under Connected apps, then this page fills with the real terms.")

_NO_CONNECTION_VIDEOS = ("No YouTube account is connected, so PeakCut cannot read which videos gained views. "
                         "Connect a channel under Connected apps, then this page fills with the real videos.")


def _me(request: Request):
    """The signed-in person, exactly as `server._me` would return them."""
    u = getattr(request.state, "user", None)
    if not u or not getattr(u, "id", None):
        raise HTTPException(401, "Please sign in.")
    return u


def _throttle(uid: str, limit: int = 120, window: int = 60) -> None:
    """The same rate limit the rest of the app uses. The routes that cannot be cached spend it on
    every request; the cached reads spend it only when they rebuild (see `_cached`)."""
    try:
        auth.throttle("trends:" + uid, limit, window)
    except auth.AuthError:
        raise HTTPException(429, "That is a lot of trends calls at once. Give it a moment.")


def _cached(key: str, build, uid: str = "", limit: int = 120):
    """The answer for this key, rebuilt at most every two minutes. Never caches a failure.

    The rate limit is spent here, and only when the answer really has to be built. It used to be
    spent on every request, so a page reload that asked again for a number already in the cache
    still used up the operator's budget: asking for a number we already hold costs nothing, so it
    must count for nothing."""
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < _CACHE_SECONDS:
        return hit[1]
    if uid:
        _throttle(uid, limit=limit)
    got = build()
    _CACHE[key] = (time.time(), got)
    if len(_CACHE) > 64:
        oldest = sorted(_CACHE.items(), key=lambda kv: kv[1][0])[:24]
        for k, _ in oldest:
            _CACHE.pop(k, None)
    return got


def _window(days: int) -> tuple:
    """(start, end) as YYYY-MM-DD, the way the Analytics API wants them. days=0 means lifetime,
    which the API treats as the channel's first day, so a wide window is sent instead."""
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=(days if days > 0 else 3650) - 1)
    return start.isoformat(), end.isoformat()


def _num(v) -> float:
    """One Analytics value as a number. Rows arrive as int, float or a numeric string."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _token() -> str:
    """A live token for the connected YouTube account, or "" when there is none."""
    return accounts.youtube_token() or ""


def _account_name() -> str:
    """The connected channel's own name as PeakCut stored it, or "" when nothing is connected.

    It is read, not guessed: the rows on `/api/trends/videos` are this channel's own videos, so the name on
    them is this account's name."""
    try:
        acc = accounts.youtube_account() or {}
        return str(acc.get("name") or "").strip()[:120]
    except Exception:  # noqa: BLE001  - a name is a nicety; the numbers are the point
        return ""


def _interest(share: float) -> str:
    """A share of the search views as the words the Trends page shows. 0.0 reads as "Very low"."""
    for floor, word in _INTEREST:
        if share >= floor:
            return word
    return "Very low"


def _no_scope(e) -> bool:
    """True when Google refused because the token lacks yt-analytics.readonly."""
    text = str(e or "").lower()
    return "insufficient" in text or "403" in text or "forbidden" in str(getattr(e, "code", ""))


def _why(e) -> str:
    """Google's failure as a sentence, in PeakCut's own words where it has them."""
    return ytstats.explain(e) or str(e)[:200] or "YouTube did not say why."


# ---------------------------------------------------------------- the saved list
def _saved_file(user_id: str) -> Path:
    """Where this person's saved search terms live: one small file next to their other settings."""
    return config.user_dir(user_id) / _FILE


def _read_saved(user_id: str) -> list:
    """The saved terms, newest first, or an empty list when there is no file or it is not readable.

    A hand-edited or broken file must never stop the page: it reads as "nothing saved yet". A bare list is
    accepted as well as {"terms": [...]} so an older or hand-written file still works."""
    try:
        got = json.loads(_saved_file(user_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if isinstance(got, dict):
        got = got.get("terms")
    if not isinstance(got, list):
        return []
    out, seen = [], set()
    for item in got:
        term = str(item or "").strip()
        if not term or term.casefold() in seen:
            continue
        seen.add(term.casefold())
        out.append(term[:MAX_TERM])
    return out[:MAX_SAVED]


def _write_saved(user_id: str, terms: list) -> None:
    """Save the list in one move, so a crash cannot leave half a file behind."""
    f = _saved_file(user_id)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps({"terms": list(terms)}, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(f)


def _without(terms: list, term: str) -> list:
    """The same list with this term gone, matched without regard to case."""
    want = term.casefold()
    return [t for t in terms if t.casefold() not in (want,)]


# ---------------------------------------------------------------- the routes
@router.get("/api/trends/status")
async def status(request: Request) -> dict:
    """Whether the search terms on the next route are YouTube's or missing.

    A page calls this first, so an empty table is explained before it is drawn."""
    u = _me(request)
    token = await run_in_threadpool(_token)

    def build() -> dict:
        # `source` matches the sibling analytics status and the searches route: "peakcut" when the
        # terms will not come from YouTube, "youtube" when they will.
        if not token:
            return {"connected": False, "source": "peakcut", "note": _NO_CONNECTION}
        try:
            ytstats.analytics(token, *_window(7), "views")
        except Exception as e:  # noqa: BLE001  - the answer is the point, not the exception
            if _no_scope(e):
                return {"connected": True, "source": "peakcut",
                        "note": "Your YouTube account is connected, but it was connected before PeakCut asked "
                                "for the analytics permission. Open Connected apps, disconnect YouTube and "
                                "connect it again, then this page fills with real terms."}
            return {"connected": True, "source": "youtube",
                    "note": "YouTube is connected, but it did not answer just now. " + _why(e)}
        return {"connected": True, "source": "youtube",
                "note": "YouTube is connected. Search terms and video views come from your channel's own "
                        "analytics."}

    return await run_in_threadpool(
        lambda: _cached(f"trend_status:{u.id}:{bool(token)}", build, u.id, limit=240))


@router.get("/api/trends/searches")
async def searches(request: Request, days: int = Query(28, ge=0, le=3650),
                   limit: int = Query(25, ge=1, le=200)) -> dict:
    """The search terms that found this channel, with the views each brought and how big its share was."""
    u = _me(request)
    start, end = _window(days)
    token = await run_in_threadpool(_token)

    def build() -> dict:
        out = {"rows": [], "source": "peakcut", "days": days, "start": start, "end": end,
               "note": _NO_CONNECTION}
        if not token:
            return out
        try:
            raw = ytstats.analytics(token, start, end, "views", dimensions="insightTrafficSourceDetail",
                                    filters="insightTrafficSourceType==YT_SEARCH", sort="-views",
                                    max_results=limit)
        except Exception as e:  # noqa: BLE001  - an empty table with a reason beats a broken page
            out["source"] = "youtube"
            out["note"] = ("YouTube would not share the search terms this time. " + _why(e) +
                           " The rest of the page still works.")
            return out
        total = sum(_num(r.get("views")) for r in raw)
        rows = []
        for r in raw:
            term = str(r.get("insightTrafficSourceDetail") or "").strip()
            if not term:
                continue
            views = int(_num(r.get("views")))
            share = (100.0 * views / total) if total else 0.0
            rows.append({"term": term[:200], "interest": _interest(share), "views": views})
        out["rows"] = rows[:limit]
        out["source"] = "youtube"
        if rows:
            out["note"] = ("The searches people typed before they found your videos, from YouTube Analytics. "
                           "The interest words are each term's share of those search views, in plain words. "
                           "YouTube does not send an interest score to PeakCut, so the share is what is shown.")
        else:
            out["note"] = ("YouTube answered, but it has no search terms for this range yet. A channel with "
                           "no search traffic shows nothing here. Try a longer range.")
        return out

    return await run_in_threadpool(
        lambda: _cached(f"trend_search:{u.id}:{days}:{limit}:{bool(token)}", build, u.id))


@router.get("/api/trends/videos")
async def videos(request: Request, days: int = Query(28, ge=0, le=3650),
                 limit: int = Query(25, ge=1, le=200)) -> dict:
    """This channel's own videos in the range, most views first, with the link to each one.

    It is not YouTube's trending chart and the note says so: that chart needs a Data API key PeakCut does
    not keep, so a page cannot draw other channels' videos from this route."""
    u = _me(request)
    start, end = _window(days)
    token = await run_in_threadpool(_token)

    def build() -> dict:
        out = {"rows": [], "days": days, "start": start, "end": end, "note": _NO_CONNECTION_VIDEOS}
        if not token:
            return out
        try:
            raw = ytstats.analytics(token, start, end, "views", dimensions="video", sort="-views",
                                    max_results=limit)
        except Exception as e:  # noqa: BLE001
            out["note"] = ("YouTube would not share this channel's videos this time. " + _why(e) +
                           " Try again in a minute.")
            return out
        ids = [str(r.get("video") or "") for r in raw if r.get("video")]
        meta = {}
        if ids:
            try:
                # Titles and publish dates are the Data API's job. Its public reader wants an API key, which
                # PeakCut does not keep; the connected channel's own token answers the same call, so it is
                # handed to the same read rather than every row arriving as a bare video id.
                for v in ytstats._videos(ids, token=token) or []:   # noqa: SLF001
                    meta[str(v.get("id") or "")] = v
            except Exception:  # noqa: BLE001  - titles are a nicety; the numbers are the point
                meta = {}
        channel = _account_name()
        rows = []
        for r in raw:
            vid = str(r.get("video") or "")
            if not vid:
                continue
            m = meta.get(vid) or {}
            rows.append({"id": vid, "title": str(m.get("title") or "") or vid, "channel": channel,
                         "views": int(_num(r.get("views"))),
                         "published": str(m.get("published") or "")[:10],
                         "url": f"https://youtu.be/{vid}"})
        out["rows"] = rows[:limit]
        out["note"] = ("Your channel's own videos in this range, most views first. This is not YouTube's "
                       "public trending chart: that read needs a YouTube Data API key, and PeakCut does not "
                       "keep one, so other channels' videos are not shown here.")
        return out

    return await run_in_threadpool(
        lambda: _cached(f"trend_videos:{u.id}:{days}:{limit}:{bool(token)}", build, u.id))


@router.get("/api/trends/saved")
async def saved(request: Request) -> dict:
    """The search terms this person kept, newest first. An empty list is a real answer."""
    u = _me(request)
    _throttle(u.id, limit=240)
    return {"terms": await run_in_threadpool(_read_saved, u.id)}


@router.post("/api/trends/saved")
async def save(request: Request) -> dict:
    """Keep one search term. A blank one is refused, and so is the fifty-first."""
    u = _me(request)
    _throttle(u.id)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001  - a body that cannot be read is answered with its own sentence below
        # The person did send something; the answer names what went wrong instead of asking for a term.
        raise HTTPException(400, "That body could not be read as JSON. Send a JSON object, like "
                                 "{\"term\": \"...\"}.")
    if not isinstance(body, dict):
        raise HTTPException(400, "Send a JSON object, like {\"term\": \"how to clip a stream\"}.")
    term = str(body.get("term") or "").strip()
    if not term:
        raise HTTPException(400, "Type a search term first, then save it.")
    if len(term) > MAX_TERM:
        raise HTTPException(400, f"That search term is longer than {MAX_TERM} characters. Save the start of "
                                 f"it instead.")

    def add() -> list:
        terms = _without(_read_saved(u.id), term)
        terms.insert(0, term)
        if len(terms) > MAX_SAVED:
            # Silently dropping the oldest would lose something the person chose to keep, so it is refused
            # with the number they can act on.
            raise HTTPException(400, f"You can keep {MAX_SAVED} search terms. Remove one before adding "
                                     f"another.")
        _write_saved(u.id, terms)
        return terms

    try:
        return {"terms": await run_in_threadpool(add)}
    except ValueError:
        raise HTTPException(400, "PeakCut could not store that search term for this account.")


@router.delete("/api/trends/saved")
async def forget(request: Request, term: str = Query("", max_length=200)) -> dict:
    """Remove one kept term, matched without regard to case. A term that is not there leaves the list as is."""
    u = _me(request)
    _throttle(u.id)
    want = str(term or "").strip()
    if not want:
        raise HTTPException(400, "Name the search term to remove.")

    def drop() -> list:
        terms = _without(_read_saved(u.id), want)
        _write_saved(u.id, terms)
        return terms

    try:
        return {"terms": await run_in_threadpool(drop)}
    except ValueError:
        raise HTTPException(400, "PeakCut could not read that list for this account.")
