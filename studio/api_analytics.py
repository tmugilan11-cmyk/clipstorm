"""The numbers a channel earned, in the shape the Analytics page draws.

`studio/ytstats.py` already knows how to ask Google; this module is the doorway, plus the
honest fallback for a PeakCut with no YouTube connection (its own records still answer).

Two sources, one shape:

* **YouTube Analytics** (`yt-analytics.readonly`) when a YouTube account is connected. That is
  the real thing: views, watch time, impressions, click-through rate, subscriber gains, per video,
  per day, per traffic source, per country, per hour.
* **PeakCut's own records** when it is not. Clips made, posts sent, the views PeakCut already
  tracks on each post, and the queue. Less, but never a zero pretending to be a measurement.

Every answer carries `source` ("youtube" or "peakcut") and `note`, so the page can say which one
it is looking at instead of guessing. It deliberately does not import `server.py`.

    GET  /api/analytics/status
    GET  /api/analytics/summary?days=28&compare=1
    GET  /api/analytics/timeseries?metric=views&days=28
    GET  /api/analytics/videos?days=28
    GET  /api/analytics/audience?days=28
    GET  /api/analytics/traffic?days=28
    GET  /api/analytics/retention?video=
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool

from . import accounts, auth, posting, ytstats

router = APIRouter()

RANGES = {7: "Last 7 days", 28: "Last 28 days", 90: "Last 90 days", 365: "Last 365 days", 0: "Lifetime"}
_METRICS = {
    "views": "views",
    "watch_time": "estimatedMinutesWatched",
    "average_view_duration": "averageViewDuration",
    "average_view_percentage": "averageViewPercentage",
    "subscribers": "subscribersGained",
    "likes": "likes",
    "comments": "comments",
    "shares": "shares",
}
_SUMMARY = ("views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,"
            "subscribersGained,subscribersLost,likes,comments,shares")
_VIDEO_COLS = ("views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,"
               "subscribersGained,likes,comments,shares")
_TRAFFIC = ("views,estimatedMinutesWatched") 
_SOURCES = {
    "YT_SEARCH": "YouTube search", "SUGGESTED_VIDEO": "Suggested videos", "BROWSE": "Browse features",
    "SHORTS_FEED": "Shorts feed", "PLAYLIST": "Playlists", "CHANNEL": "Channel pages",
    "EXTERNAL": "External", "NO_LINK_OTHER": "No link", "NOTIFICATION": "Notifications",
    "SUBSCRIBER": "Subscriptions feed", "YT_OTHER_PAGE": "Other YouTube pages",
    "HASHTAGS": "Hashtags", "END_SCREEN": "End screens", "LIVE": "Live",
}

_CACHE: dict = {}          # one small cache: a page reload must not spend quota
_CACHE_SECONDS = 120.0


def _me(request: Request):
    """The signed-in person, exactly as `server._me` would return them."""
    u = getattr(request.state, "user", None)
    if not u or not getattr(u, "id", None):
        raise HTTPException(401, "Please sign in.")
    return u


def _throttle(uid: str, limit: int = 120, window: int = 60) -> None:
    """The same rate limit the rest of the app uses. Every call here spends the operator's own quota."""
    try:
        auth.throttle("analytics:" + uid, limit, window)
    except auth.AuthError:
        raise HTTPException(429, "That is a lot of analytics calls at once. Give it a moment.")


def _cached(key: str, build, uid: str = ""):
    """The answer for this key, rebuilt at most every two minutes. Never caches a failure.

    The rate limit is spent here, and only when the answer really has to be built. It used to be
    spent on every request, which meant a page that asked again for a number it already had still
    used up the operator's budget: the Insights page makes about a dozen calls, and simply moving
    between its tabs twice was enough to be told to wait. Asking for a number we already hold costs
    nothing, so it must count for nothing.
    """
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < _CACHE_SECONDS:
        return hit[1]
    if uid:
        _throttle(uid)
    got = build()
    _CACHE[key] = (time.time(), got)
    if len(_CACHE) > 64:
        oldest = sorted(_CACHE.items(), key=lambda kv: kv[1][0])[:24]
        for k, _ in oldest:
            _CACHE.pop(k, None)
    return got


def _window(days: int) -> tuple:
    """"(start, end) as YYYY-MM-DD, the way the Analytics API wants them. days=0 means lifetime,
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


def _own(days: int) -> dict:
    """What PeakCut knows without YouTube: clips made, posts sent, the views it already tracks."""
    o = posting.overview()
    made = sum(d.get("clips") or 0 for d in o.get("daily") or [])
    posted = sum(d.get("posted") or 0 for d in o.get("daily") or [])
    views = sum(d.get("views") or 0 for d in o.get("daily") or [])
    rows = [p for p in o.get("posts") or []]
    return {"clips": made, "posted": posted, "views": views,
            "queued": sum(1 for r in rows if r.get("status") in ("scheduled", "posting")),
            "failed": sum(1 for r in rows if r.get("status") == "failed"),
            "creators": len(o.get("creators") or []), "daily": o.get("daily") or []}


def _token() -> str:
    """A live token for the connected YouTube account, or "" when there is none."""
    return accounts.youtube_token() or ""


def _ask(token: str, start: str, end: str, metrics: str, **kw) -> list:
    """One Analytics report. Raises YouTubeError with Google's own words when it refuses."""
    return ytstats.analytics(token, start, end, metrics, **kw)


def _no_scope(e) -> bool:
    """True when Google refused because the token lacks yt-analytics.readonly."""
    text = str(e or "").lower()
    return "insufficient" in text or "forbidden" in str(getattr(e, "code", "")) or "403" in text


@router.get("/api/analytics/status")
async def status(request: Request) -> dict:
    """Whether the numbers on the next four routes are YouTube's or PeakCut's own.

    A page calls this first, so an empty chart is explained before it is drawn."""
    u = _me(request)
    token = await run_in_threadpool(_token)
    if not token:
        return {"connected": False, "source": "peakcut", "scope": False, "ranges": RANGES,
                "note": "No YouTube account is connected, so these are PeakCut's own numbers: clips "
                        "made, posts sent, and the views PeakCut already tracks. Connect a channel "
                        "under Connected apps to see YouTube's own analytics."}
    try:
        _ask(token, *_window(7), "views")
        scope = True
    except Exception as e:  # noqa: BLE001  - the answer is the point, not the exception
        scope = not _no_scope(e)
        if not scope:
            return {"connected": True, "source": "peakcut", "scope": False, "ranges": RANGES,
                    "note": "Your YouTube account is connected, but it was connected before PeakCut "
                            "asked for the analytics permission. Open Connected apps, disconnect "
                            "YouTube and connect it again, then this page fills with real numbers."}
    return {"connected": True, "source": "youtube" if scope else "peakcut", "scope": scope,
            "ranges": RANGES,
            "note": "These are YouTube's own numbers, read with your channel's permission."}


@router.get("/api/analytics/summary")
async def summary(request: Request, days: int = Query(28, ge=0, le=3650),
                  compare: int = Query(1, ge=0, le=1)) -> dict:
    """The six numbers along the top of the Analytics page, with the change against the period before."""
    u = _me(request)
    start, end = _window(days)
    token = await run_in_threadpool(_token)

    def build() -> dict:
        if not token:
            own = _own(days)
            return {"source": "peakcut", "days": days, "start": start, "end": end, "cards": [
                {"key": "clips", "label": "Clips made", "value": own["clips"], "unit": "clips"},
                {"key": "posted", "label": "Posts sent", "value": own["posted"], "unit": "posts"},
                {"key": "views", "label": "Views PeakCut tracked", "value": own["views"], "unit": "views"},
                {"key": "queued", "label": "Waiting to go out", "value": own["queued"], "unit": "posts"},
                {"key": "failed", "label": "Failed posts", "value": own["failed"], "unit": "posts"},
                {"key": "creators", "label": "Creators set up", "value": own["creators"], "unit": ""},
            ], "compare": None,
                "note": "PeakCut's own records. Connect a YouTube channel for views, watch time and "
                        "click-through rate."}
        try:
            rows = _ask(token, start, end, _SUMMARY)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(400, ytstats.explain(e) if hasattr(ytstats, "explain") else str(e))
        r = rows[0] if rows else {}
        cards = [
            {"key": "views", "label": "Views", "value": int(_num(r.get("views"))), "unit": "views"},
            {"key": "watch_time", "label": "Watch time", "value": round(_num(r.get("estimatedMinutesWatched")) / 60, 1),
             "unit": "hours"},
            {"key": "average_view_duration", "label": "Average view duration",
             "value": int(_num(r.get("averageViewDuration"))), "unit": "seconds"},
            {"key": "average_view_percentage", "label": "Average percentage viewed",
             "value": round(_num(r.get("averageViewPercentage")), 1), "unit": "percent"},
            {"key": "subscribers", "label": "Subscribers gained",
             "value": int(_num(r.get("subscribersGained")) - _num(r.get("subscribersLost"))), "unit": "subscribers"},
            {"key": "engagement", "label": "Likes and comments",
             "value": int(_num(r.get("likes")) + _num(r.get("comments"))), "unit": ""},
        ]
        out = {"source": "youtube", "days": days, "start": start, "end": end, "cards": cards,
               "compare": None, "note": "YouTube's own numbers for the dates shown."}
        if compare:
            prev_end = (datetime.fromisoformat(start) - timedelta(days=1)).date()
            prev_start = prev_end - timedelta(days=(days if days > 0 else 3650) - 1)
            try:
                old = _ask(token, prev_start.isoformat(), prev_end.isoformat(), _SUMMARY)
                o = old[0] if old else {}
                out["compare"] = {"start": prev_start.isoformat(), "end": prev_end.isoformat(),
                                  "cards": {"views": int(_num(o.get("views"))),
                                            "watch_time": round(_num(o.get("estimatedMinutesWatched")) / 60, 1),
                                            "average_view_duration": int(_num(o.get("averageViewDuration"))),
                                            "average_view_percentage": round(_num(o.get("averageViewPercentage")), 1),
                                            "subscribers": int(_num(o.get("subscribersGained")) - _num(o.get("subscribersLost"))),
                                            "engagement": int(_num(o.get("likes")) + _num(o.get("comments")))}}
            except Exception:  # noqa: BLE001  - a comparison is a nicety, never worth a failed page
                out["compare"] = None
        return out

    return await run_in_threadpool(lambda: _cached(f"sum:{u.id}:{days}:{compare}:{bool(token)}", build, u.id))


@router.get("/api/analytics/timeseries")
async def timeseries(request: Request, metric: str = Query("views", max_length=40),
                     days: int = Query(28, ge=0, le=3650)) -> dict:
    """One number per day for one metric, plus the same for the period before when comparing."""
    u = _me(request)
    name = _METRICS.get(metric) or _METRICS.get(metric.lower())
    if not name:
        raise HTTPException(400, "PeakCut does not know that metric. Ask for one of: " + ", ".join(sorted(_METRICS)) + ".")
    start, end = _window(days)
    token = await run_in_threadpool(_token)

    def build() -> dict:
        if not token:
            own = _own(days)
            daily = own["daily"][-days:] if days else own["daily"]
            rows = [{"day": d.get("day"), "value": d.get("views") if name == "views" else d.get("clips")}
                    for d in daily]
            return {"source": "peakcut", "metric": metric, "days": days, "start": start, "end": end,
                    "rows": rows, "unit": "views" if name == "views" else "clips",
                    "note": "PeakCut's own counts, one point per day."}
        try:
            rows = _ask(token, start, end, name, dimensions="day", sort="day")
        except Exception as e:  # noqa: BLE001
            raise HTTPException(400, str(e))
        pts = [{"day": str(r.get("day") or ""), "value": round(_num(r.get(name)), 2)} for r in rows]
        unit = {"views": "views", "estimatedMinutesWatched": "minutes", "averageViewDuration": "seconds",
                "averageViewPercentage": "percent", "subscribersGained": "subscribers", "likes": "likes",
                "comments": "comments", "shares": "shares"}.get(name, "")
        return {"source": "youtube", "metric": metric, "days": days, "start": start, "end": end,
                "rows": pts, "unit": unit, "note": "YouTube's own numbers, one point per day."}

    return await run_in_threadpool(lambda: _cached(f"ts:{u.id}:{metric}:{days}:{bool(token)}", build, u.id))


@router.get("/api/analytics/videos")
async def videos(request: Request, days: int = Query(28, ge=0, le=3650),
                 limit: int = Query(100, ge=1, le=200)) -> dict:
    """One row per video published in the window, with everything the Content table shows."""
    u = _me(request)
    start, end = _window(days)
    token = await run_in_threadpool(_token)

    def build() -> dict:
        if not token:
            o = posting.overview()
            rows = []
            for p in o.get("posts") or []:
                rows.append({"id": p.get("id"), "title": p.get("title") or p.get("clip") or "A post",
                             "url": p.get("url") or "", "views": p.get("views") or 0,
                             "watch_time": None, "average_view_duration": None,
                             "average_view_percentage": None, "likes": None, "comments": None,
                             "shares": None, "subscribers": None,
                             "status": p.get("status"), "account": p.get("account_name") or ""})
            return {"source": "peakcut", "days": days, "start": start, "end": end,
                    "rows": rows[:limit], "total": len(rows),
                    "note": "PeakCut's own posts. Watch time and the rest come from YouTube."}
        try:
            rows = _ask(token, start, end, _VIDEO_COLS, dimensions="video", sort="-views", max_results=limit)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(400, str(e))
        ids = [str(r.get("video") or "") for r in rows if r.get("video")]
        meta = {}
        if ids:
            try:
                for v in ytstats.videos(ids[:limit], "") or []:
                    meta[v.get("id")] = v
            except Exception:  # noqa: BLE001  - titles are a nicety; the numbers are the point
                meta = {}
        out = []
        for r in rows:
            vid = str(r.get("video") or "")
            m = meta.get(vid) or {}
            out.append({
                "id": vid, "title": m.get("title") or vid, "url": f"https://youtu.be/{vid}" if vid else "",
                "published": m.get("published") or "",
                "thumbnail": m.get("thumbnail") or "",
                "seconds": m.get("seconds"),
                "views": int(_num(r.get("views"))),
                "watch_time": round(_num(r.get("estimatedMinutesWatched")) / 60, 1),
                "average_view_duration": int(_num(r.get("averageViewDuration"))),
                "average_view_percentage": round(_num(r.get("averageViewPercentage")), 1),
                "likes": int(_num(r.get("likes"))), "comments": int(_num(r.get("comments"))),
                "shares": int(_num(r.get("shares"))),
                "subscribers": int(_num(r.get("subscribersGained")))})
        return {"source": "youtube", "days": days, "start": start, "end": end, "rows": out,
                "total": len(out), "note": "YouTube's own numbers for each video in the range."}

    return await run_in_threadpool(lambda: _cached(f"vid:{u.id}:{days}:{limit}:{bool(token)}", build, u.id))


@router.get("/api/analytics/audience")
async def audience(request: Request, days: int = Query(28, ge=0, le=3650)) -> dict:
    """Who is watching: new against returning, which countries, and which hours."""
    u = _me(request)
    start, end = _window(days)
    token = await run_in_threadpool(_token)

    def build() -> dict:
        out = {"source": "youtube" if token else "peakcut", "days": days, "start": start, "end": end,
               "returning": None, "countries": [], "hours": [], "note": ""}
        if not token:
            out["note"] = "Viewer types, countries and hours come from YouTube. Connect a channel to see them."
            return out
        try:
            rows = _ask(token, start, end, "views", dimensions="creatorContentType")
            out["content_types"] = [{"type": str(r.get("creatorContentType") or ""),
                                     "views": int(_num(r.get("views")))} for r in rows]
        except Exception:  # noqa: BLE001
            pass
        try:
            rows = _ask(token, start, end, "views,subscribersGained", dimensions="video")
            out["videos_seen"] = len(rows)
        except Exception:  # noqa: BLE001
            pass
        try:
            rows = _ask(token, start, end, "views", dimensions="country", sort="-views", max_results=10)
            total = sum(_num(r.get("views")) for r in rows) or 1.0
            out["countries"] = [{"country": str(r.get("country") or ""), "views": int(_num(r.get("views"))),
                                 "percent": round(100.0 * _num(r.get("views")) / total, 1)} for r in rows]
        except Exception:  # noqa: BLE001
            pass
        try:
            rows = _ask(token, start, end, "views", dimensions="day,hour")
            cells = [{"day": str(r.get("day") or ""), "hour": int(_num(r.get("hour"))),
                      "views": int(_num(r.get("views")))} for r in rows]
            out["hours"] = cells
            if cells:
                best = max(cells, key=lambda c: c["views"])
                out["best"] = best
        except Exception:  # noqa: BLE001
            pass
        out["note"] = "YouTube's own numbers. Hours are in your channel's own time zone."
        return out

    return await run_in_threadpool(lambda: _cached(f"aud:{u.id}:{days}:{bool(token)}", build, u.id))


@router.get("/api/analytics/traffic")
async def traffic(request: Request, days: int = Query(28, ge=0, le=3650)) -> dict:
    """Where the views came from, the Shorts feed included."""
    u = _me(request)
    start, end = _window(days)
    token = await run_in_threadpool(_token)

    def build() -> dict:
        if not token:
            return {"source": "peakcut", "days": days, "start": start, "end": end, "sources": [],
                    "note": "Traffic sources come from YouTube. Connect a channel to see them."}
        try:
            rows = _ask(token, start, end, _TRAFFIC, dimensions="insightTrafficSourceType", sort="-views")
        except Exception as e:  # noqa: BLE001
            raise HTTPException(400, str(e))
        total = sum(_num(r.get("views")) for r in rows) or 1.0
        src = [{"key": str(r.get("insightTrafficSourceType") or ""),
                "name": _SOURCES.get(str(r.get("insightTrafficSourceType") or ""),
                                     str(r.get("insightTrafficSourceType") or "Other")),
                "views": int(_num(r.get("views"))),
                "minutes": int(_num(r.get("estimatedMinutesWatched"))),
                "percent": round(100.0 * _num(r.get("views")) / total, 1)} for r in rows]
        return {"source": "youtube", "days": days, "start": start, "end": end, "sources": src,
                "note": "YouTube's own numbers. The Shorts feed is its own source here."}

    return await run_in_threadpool(lambda: _cached(f"tra:{u.id}:{days}:{bool(token)}", build, u.id))


@router.get("/api/analytics/retention")
async def retention(request: Request, video: str = Query("", max_length=200)) -> dict:
    """The audience-retention curve for one video: the share still watching at each point."""
    u = _me(request)
    vid = ytstats.vid_id(video) or ""
    if not vid:
        raise HTTPException(400, "Paste a YouTube link or a video id.")
    token = await run_in_threadpool(_token)
    if not token:
        raise HTTPException(400, "Retention comes from YouTube. Connect a channel under Connected apps.")

    def build() -> dict:
        start, end = _window(3650)
        try:
            rows = _ask(token, start, end, "audienceWatchRatio,relativeRetentionPerformance",
                        dimensions="elapsedVideoTimeRatio", filters="video==" + vid)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(400, str(e))
        pts = [{"at": round(_num(r.get("elapsedVideoTimeRatio")) * 100, 1),
                "watching": round(_num(r.get("audienceWatchRatio")) * 100, 1)} for r in rows]
        return {"vid": vid, "points": pts, "note": "How much of the video people watched."}

    return await run_in_threadpool(lambda: _cached(f"ret:{u.id}:{vid}:{bool(token)}", build, u.id))
