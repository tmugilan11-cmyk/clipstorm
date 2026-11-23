"""Read-only YouTube numbers for one published Short: public statistics with the operator's own key, private retention with a token that was already obtained."""
from __future__ import annotations

import json
import os
import re
import statistics
import threading
import time
from datetime import datetime, timezone

import httpx

from . import config

# ---------------------------------------------------------------- what is called, and how
DATA = "https://www.googleapis.com/youtube/v3"
ANA = "https://youtubeanalytics.googleapis.com/v2/reports"
SHORTS_MAX_S = 180                      # a Short, by this module's own rule: 0 < seconds <= 180
_TIMEOUT = 20                           # seconds, one call
_FIELDS = "snippet,statistics,contentDetails"
_METRICS = "views,averageViewDuration,averageViewPercentage,subscribersGained"
_METRIC_KEYS = ("views", "averageViewDuration", "averageViewPercentage", "subscribersGained")
_MEDIAN_KEYS = ("averageViewDuration", "averageViewPercentage", "subscribersGained")

_LINK = re.compile(r"(?:v=|youtu\.be/|shorts/|embed/)([\w-]{11})")
_ID = re.compile(r"[\w-]{11}")
_CHANNEL = re.compile(r"UC[\w-]{22}")
_PT = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")

# ---------------------------------------------------------------- the knobs in use
# Nothing here is a secret, so all of it is shown. Same file-and-lock pattern as ai.json: a hand-edited or
# broken yt.json falls back to these defaults instead of stopping the server.
_DEFAULTS = {"hook_second": 3.0, "peer_window": 20, "median_days": 90, "median_rows": 20,
             "shorts_max_s": SHORTS_MAX_S}
_RANGES = {"hook_second": (0.5, 60.0), "peer_window": (1, 50), "median_days": (7, 730),
           "median_rows": (1, 200), "shorts_max_s": (1, 600)}
_lock = threading.Lock()
_saved = {"at": None, "data": {}}


def _file():
    """Where the knobs live: one file for the instance, next to ai.json."""
    return config.DATA_DIR / "yt.json"


def _from_file() -> dict:
    """What was saved, read again only when the file changes; {} when there is none or it is not readable."""
    f = _file()
    try:
        at = f.stat().st_mtime_ns
    except OSError:
        at = 0
    if _saved["at"] != at:
        try:
            data = json.loads(f.read_text(encoding="utf-8")) if at else {}
        except (OSError, ValueError):
            data = {}
        _saved.update(at=at, data=data if isinstance(data, dict) else {})
    return _saved["data"]


def public() -> dict:
    """Every knob with the value in use: the defaults, overridden by anything sane in yt.json."""
    saved = _from_file()
    out = dict(_DEFAULTS)
    for k, v in saved.items():
        if k in _RANGES:
            try:
                x = float(v)
            except (TypeError, ValueError):
                continue
            low, high = _RANGES[k]
            if low <= x <= high:
                out[k] = int(x) if isinstance(_DEFAULTS[k], int) else round(x, 2)
    return out


def save(**changes) -> dict:
    """Save the knobs given, keeping the ones not mentioned; a value out of range is refused."""
    out = public()
    for k, v in changes.items():
        if k not in _RANGES:
            raise ValueError(f"Unknown YouTube setting: {k}")
        try:
            x = float(v)
        except (TypeError, ValueError):
            raise ValueError(f"{k} must be a number.")
        low, high = _RANGES[k]
        if not low <= x <= high:
            raise ValueError(f"{k} must be between {low:g} and {high:g}.")
        out[k] = int(x) if isinstance(_DEFAULTS[k], int) else round(x, 2)
    with _lock:
        try:
            f = _file()
            tmp = f.with_suffix(".tmp")
            tmp.write_text(json.dumps(out, indent=1), encoding="utf-8")
            try:
                os.chmod(tmp, 0o600)     # nothing secret here, but nobody else needs to write it
            except OSError:
                pass
            tmp.replace(f)
        except OSError as e:
            raise ValueError(f"Could not save the YouTube settings: {e}")
        _saved["at"] = None
    return public()


# ---------------------------------------------------------------- failures, and how they are spoken about
class YouTubeError(RuntimeError):
    """An upstream failure, already phrased for the owner."""

    def __init__(self, message: str, code: int = 0):
        super().__init__(message)
        self.code = int(code or 0)


problem = {"text": "", "at": 0.0}       # why the last call failed, for the pages; cleared when one works


def explain(e) -> str:
    """What went wrong with a YouTube call, in words the owner can act on; "" when there is nothing to say."""
    text, low = str(e), str(e).lower()
    code = getattr(e, "code", 0)
    if "quota" in low or code == 429:
        return "YouTube's daily quota for this project is spent. Try again tomorrow."
    if "has not been used" in low or "is disabled" in low or "accessnotconfigured" in low.replace(" ", ""):
        # The most common stumble on a new Google project: the two YouTube APIs are separate switches.
        return ("A YouTube switch is still off in your Google Cloud project. Turn on both \"YouTube Data API v3\" "
                "and \"YouTube Analytics API\" (APIs & Services, Library), wait a minute, and try again.")
    if "invalid_grant" in low or "invalid credentials" in low or "unauthenticated" in low or "token has been expired" in low:
        return "Google no longer accepts the saved YouTube sign-in. Press Connect again."
    if code == 401 or "api key not valid" in low or "keyinvalid" in low:
        return "YouTube refused the key. Check the key in Settings."
    if code == 403:
        return ("YouTube would not share these numbers. Connect the channel again so it can share retention, "
                "or the daily quota is spent.")
    if code == 404:
        return "That video is private, deleted, or on another channel."
    if "could not reach" in low or "timed out" in low or "timeout" in low or "connect" in low:
        return "PeakCut could not reach YouTube. Check the internet connection."
    return ""


def note_problem(e) -> None:
    """Remember why the last call failed, so a page can say it plainly."""
    problem.update(text=explain(e) or str(e)[:200], at=time.time())


def clear_problem() -> None:
    """Forget the last failure: something got through."""
    problem.update(text="", at=0.0)


def _said(r) -> str:
    """The human part of a Google error body, or the start of the reply when it has none."""
    try:
        body = r.json()
    except ValueError:
        body = None
    err = body.get("error") if isinstance(body, dict) else None
    msg = err.get("message") if isinstance(err, dict) else (err if isinstance(err, str) else "")
    return (str(msg) or str(getattr(r, "text", "") or ""))[:300] or "no details"


def _get(path: str, params: dict, token: str = "", key: str = "", base: str = DATA) -> dict:
    """One GET against Google. A token wins over a key: the two are never sent in the same call."""
    p = {k: v for k, v in (params or {}).items() if v not in (None, "", 0)}
    head = {}
    if token:
        head["Authorization"] = f"Bearer {token}"
    elif key:
        p["key"] = key
    url = f"{base}/{path}".rstrip("/")
    try:
        r = httpx.get(url, params=p, headers=head, timeout=_TIMEOUT)
    except httpx.HTTPError as e:
        raise YouTubeError(f"Could not reach YouTube: {e}") from e
    if r.status_code != 200:
        raise YouTubeError(f"YouTube said {r.status_code}: {_said(r)}", r.status_code)
    try:
        data = r.json()
    except ValueError as e:
        raise YouTubeError("YouTube's answer was not readable.") from e
    clear_problem()
    return data if isinstance(data, dict) else {}


def _items(path: str, params: dict, key: str = "", token: str = "") -> list:
    """The 'items' of one Data API list call; [] when the call failed, with the reason kept in problem."""
    try:
        return list(_get(path, params, token=token, key=key).get("items") or [])
    except YouTubeError as e:
        note_problem(e)
        return []


# ---------------------------------------------------------------- reading what comes back
def vid_id(url: str) -> str | None:
    """The 11-character id in a watch, youtu.be, /shorts/ or /embed/ link, or the bare id; None when there is none."""
    s = str(url or "").strip()
    m = _LINK.search(s)
    if m:
        return m.group(1)
    return s if _ID.fullmatch(s) else None


def duration_s(iso: str) -> int:
    """Seconds from an ISO-8601 'PT#H#M#S' duration; 0 when it cannot be read."""
    m = _PT.fullmatch(str(iso or ""))
    if not m:
        return 0
    h, mi, s = (int(x or 0) for x in m.groups())
    return h * 3600 + mi * 60 + s


def _int(v) -> int | None:
    """A count as an integer, or None when it is absent: 0 and "hidden by the creator" are different things."""
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _float(v) -> float | None:
    """A ratio as a float, or None when it is absent."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _days_ago(days: int) -> str:
    """The UTC date that many days back, as YYYY-MM-DD."""
    return datetime.fromordinal(datetime.now(timezone.utc).date().toordinal() - max(0, int(days))).strftime("%Y-%m-%d")


def _flatten(it: dict) -> dict | None:
    """One API video object in the shape every other function uses; None when it has no id or no snippet."""
    sn, st, cd = it.get("snippet") or {}, it.get("statistics") or {}, it.get("contentDetails") or {}
    if not it.get("id") or not sn:
        return None
    return {"id": str(it["id"]), "title": str(sn.get("title") or ""),
            "published": str(sn.get("publishedAt") or ""), "seconds": duration_s(cd.get("duration")),
            "views": _int(st.get("viewCount")) or 0,
            "likes": _int(st.get("likeCount")),          # None when the creator hides likes
            "comments": _int(st.get("commentCount"))}    # None when comments are off


# ---------------------------------------------------------------- the Data API
def _videos(ids: list, key: str = "", token: str = "") -> list[dict]:
    """Flattened stats for these ids, 50 per call; a token is used when there is one, the key otherwise."""
    out, wanted = [], [str(i) for i in (ids or []) if i]
    for i in range(0, len(wanted), 50):
        for it in _items("videos", {"part": _FIELDS, "id": ",".join(wanted[i:i + 50])}, key, token):
            v = _flatten(it) if isinstance(it, dict) else None
            if v:
                out.append(v)
    return out


def videos(ids: list, key: str) -> list[dict]:
    """Public stats for these ids, 50 per call: {id, title, published, seconds, views, likes, comments}.
    An id that is private or gone is simply absent, and [] comes back when the call failed."""
    if not str(key or "").strip() or not ids:
        return []                          # nothing to read without either, and no call worth making
    return _videos(ids, key)


def _channel(ch: str, key: str = "", token: str = "") -> str:
    """The UC... id for a raw id or an @handle; "" when it cannot be resolved."""
    s = str(ch or "").strip()
    if _CHANNEL.fullmatch(s):
        return s
    handle = s.lstrip("@")
    if not handle:
        return ""
    items = _items("channels", {"part": "id", "forHandle": handle}, key, token)
    return str((items[0] if isinstance(items[0], dict) else {}).get("id") or "") if items else ""


def channel_id(handle: str, key: str) -> str:
    """The UC... id for an @handle, or the id itself when it already is one; "" when it cannot be found."""
    return _channel(handle, key)


def latest_shorts(channel_id: str, key: str, n: int = 10) -> list[dict]:
    """The channel's newest uploads that are Shorts by this module's rule (0 < seconds <= shorts_max_s),
    at most n; [] when the call failed. The uploads playlist is the channel id with UU in place of UC."""
    try:
        limit = max(1, int(n))
    except (TypeError, ValueError):
        limit = 10
    try:
        ch = _channel(channel_id, key)
        if len(ch) < 3:
            return []
        items = _items("playlistItems", {"part": "contentDetails", "playlistId": "UU" + ch[2:],
                                        "maxResults": 50}, key)
        ids = [str(((it or {}).get("contentDetails") or {}).get("videoId") or "") for it in items]
        ids = [i for i in ids if i]
        if not ids:
            return []
        top = int(public().get("shorts_max_s") or SHORTS_MAX_S)
        return [v for v in _videos(ids, key) if 0 < v["seconds"] <= top][:limit]
    except Exception as e:                  # noqa: BLE001 - one odd reply must not stop the page
        note_problem(e)
        return []


# ---------------------------------------------------------------- YouTube Analytics (needs a token)
def analytics(token: str, start: str, end: str, metrics: str, dimensions: str = "", filters: str = "",
              sort: str = "", max_results: int = 0) -> list[dict]:
    """One report for ids='channel==MINE': rows as dicts keyed by columnHeaders, [] when there is no data yet."""
    r = _get("", {"ids": "channel==MINE", "startDate": start, "endDate": end, "metrics": metrics,
                  "dimensions": dimensions, "filters": filters, "sort": sort, "maxResults": max_results},
             token=token, base=ANA)
    cols = [str(h.get("name") or "") for h in (r.get("columnHeaders") or []) if isinstance(h, dict)]
    return [dict(zip(cols, row)) for row in (r.get("rows") or []) if isinstance(row, (list, tuple))]


def kept_at(token: str, video: str, seconds: int, start: str, end: str, probe: float = 0.0) -> float | None:
    """The share of viewers (0 to 1) still watching at the hook second, read from the audience-retention curve
    Google keeps for one video; None when there is no curve or the length is unknown."""
    if not token or not video or not seconds:
        return None
    probe = float(probe or public()["hook_second"])
    curve = [r for r in analytics(token, start, end, "audienceWatchRatio",
                                  dimensions="elapsedVideoTimeRatio", filters="video==" + video)
             if _float(r.get("elapsedVideoTimeRatio")) is not None and _float(r.get("audienceWatchRatio")) is not None]
    if not curve:
        return None
    near = min(curve, key=lambda r: abs(_float(r["elapsedVideoTimeRatio"]) - probe / seconds))
    return _float(near["audienceWatchRatio"])


def bulk(token: str, ids: list, since: str = "", retention_for: int = 0) -> dict:
    """The numbers for many of the channel's own videos in as few calls as possible.

    Returns {"videos": {id: {views, likes, comments, seconds, published, averageViewDuration,
    averageViewPercentage, kept_at_3s}}, "error": ""}. The Data API gives views, likes and comments 50 at a time;
    Analytics gives the average watched for up to 100 videos per call; the 3-second curve is one call per video,
    so it is read only for the first `retention_for` ids (the caller puts the newest first). A step that fails
    leaves the rest in place and names the reason in "error". Never raises."""
    out, err = {}, ""
    wanted = list(dict.fromkeys(vid_id(i) or "" for i in (ids or [])))
    wanted = [i for i in wanted if i]
    if not token or not wanted:
        return {"videos": out, "error": ""}
    try:
        for v in _videos(wanted, "", token):
            out[v["id"]] = {k: v.get(k) for k in ("views", "likes", "comments", "seconds", "published")}
    except Exception as e:                  # noqa: BLE001
        err = explain(e) or str(e)[:200]
    start = _days_ago(int(public()["median_days"]) * 8)
    if since and _DATE.fullmatch(str(since)[:10]):
        start = str(since)[:10]
    end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for i in range(0, len(wanted), 100):
        chunk = wanted[i:i + 100]
        try:
            for r in analytics(token, start, end, _METRICS, dimensions="video",
                               filters="video==" + ",".join(chunk), max_results=len(chunk)):
                vid = str(r.get("video") or "")
                if vid in out or vid in chunk:
                    out.setdefault(vid, {}).update({k: r[k] for k in ("averageViewDuration", "averageViewPercentage") if k in r})
        except Exception as e:              # noqa: BLE001
            err = err or explain(e) or str(e)[:200]
            break
    for vid in wanted[:max(0, int(retention_for))]:
        got = out.get(vid)
        if got is None:
            continue
        try:
            at3 = kept_at(token, vid, int(got.get("seconds") or 0), start, end)
        except Exception as e:              # noqa: BLE001
            err = err or explain(e) or str(e)[:200]
            break
        if at3 is not None:
            got["kept_at_3s"] = at3
    return {"videos": out, "error": err}


def deep(vid: str, key: str, token: str) -> dict:
    """The private numbers for one video from Analytics; {} when there is no token to ask with.
    Keys when they arrive: views (Analytics' own, lagging count), averageViewDuration,
    averageViewPercentage, subscribersGained, kept_at_3s, median{...}, plus error when a call failed."""
    video = vid_id(vid) or str(vid or "").strip()
    if not video or not str(token or "").strip():
        return {}
    knobs, out = public(), {}
    try:
        v = (_videos([video], key, token) or [{}])[0] or {}
        seconds = _int(v.get("seconds")) or 0
        start = str(v.get("published") or "")[:10]
        if not _DATE.fullmatch(start):
            start = _days_ago(knobs["median_days"])
        end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rows = analytics(token, start, end, _METRICS, filters="video==" + video)
        if rows:
            out.update({k: rows[0][k] for k in _METRIC_KEYS if k in rows[0]})
        curve = [r for r in analytics(token, start, end, "audienceWatchRatio",
                                       dimensions="elapsedVideoTimeRatio", filters="video==" + video)
                 if _float(r.get("elapsedVideoTimeRatio")) is not None
                 and _float(r.get("audienceWatchRatio")) is not None]
        probe = float(knobs["hook_second"])
        if curve and seconds:                                  # nearest sample on a curve Google controls
            near = min(curve, key=lambda r: abs(_float(r["elapsedVideoTimeRatio"]) - probe / seconds))
            out["kept_at_3s"] = _float(near["audienceWatchRatio"])
        peer = analytics(token, _days_ago(knobs["median_days"]), end, _METRICS, dimensions="video",
                         sort="-views", max_results=int(knobs["median_rows"]))
        med = {}
        for k in _MEDIAN_KEYS:                                 # views are left to the public side
            vals = [x for x in (_float(r.get(k)) for r in peer) if x is not None]
            if vals:
                med[k] = statistics.median(vals)
        if med:
            out["median"] = med
    except Exception as e:                  # noqa: BLE001 - a new or unlisted video simply has no numbers yet
        out["error"] = str(e)[:200]
        note_problem(e)
    return out
