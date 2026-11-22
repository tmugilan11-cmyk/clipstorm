"""Who of PeakCut's streamers is live right now - title and viewer count on Twitch, Kick or YouTube, discovered only, never recorded or cut (studio/live.py does that), and never raising into the server."""
from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

from . import config

PLATFORMS: Tuple[str, ...] = ("twitch", "kick", "youtube")   # the keys look() accepts
LIVE_FOR = 60        # seconds a live answer is reused: a viewer count does not change every second
FAIL_FOR = 30        # seconds a failed answer is reused, so a blocked platform is asked less, not more often
BUDGET = 20.0        # seconds one watching() call may spend on the network before it answers with what it has
TIMEOUT = 8          # seconds, one address
MAX_LIST = 200       # streamers the watch list keeps; watching() asks about PEAKCUT_HUNT_MAX per call
MAX_TITLE = 200
CACHE_MAX = 2000     # answers kept; the watch list can change over a long run
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}
HANDLE_RE = re.compile(r"@?[\w.\-]{1,60}")
# The public client id Twitch's own website uses (yt-dlp uses it too). Asks one question, answers in about a second.
TWITCH_CLIENT = "kimne78kx3ncx6brgo4mv6wki5h1ko"
TWITCH_QUERY = "query($l:String!){user(login:$l){login stream{title viewersCount createdAt type}}}"
# YouTube says it two ways depending on the page it served; either one means the channel is on air.
YT_LIVE = ('"isLiveNow":true', '"isLive":true')

problem = {"text": "", "at": 0.0, "key": ""}    # why the last look failed, for whoever wants to say it, as in ai.py


def _env_int(name: str, default: int, low: int) -> int:
    """An operator override, or the default when it is missing or is not a number."""
    try:
        return max(low, int(config.env(name, str(default)) or default))
    except (TypeError, ValueError):
        return default


def key(platform: str, ident: str) -> str:
    """The one name a streamer is known by here: "twitch:somebody". Never raises, so it can key a dict."""
    return f"{str(platform or '').strip().lower()}:{str(ident or '').strip().lstrip('@').lower()}"


def _clean(platform: str, ident: str) -> Tuple[str, str]:
    """The platform and channel a caller meant, or ValueError saying what a person typed wrong."""
    p = str(platform or "").strip().lower()
    h = str(ident or "").strip()
    if p not in PLATFORMS:
        raise ValueError(f"Unknown platform. Use one of: {', '.join(PLATFORMS)}.")
    if not HANDLE_RE.fullmatch(h):
        raise ValueError("A channel name has letters, digits and . - _ only.")
    return p, h.lstrip("@")


# ---------------------------------------------------------------- asking a platform
def _get(url: str, accept: str = "application/json", limit: int = 1_500_000) -> str:
    req = urllib.request.Request(url, headers={**UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read(limit).decode("utf-8", "replace")


def _post(url: str, body: dict, headers: Optional[dict] = None) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={
        **UA, "Accept": "application/json", "Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read(1_000_000).decode("utf-8", "replace"))


def _reason(e) -> str:
    """One short line about a failed request, safe to show: no traceback and no server paths."""
    return " ".join(str(e).split())[:120] or e.__class__.__name__


def _search(text: str, patterns) -> str:
    """The first capture group of the first pattern that matches, or "" - a page that changed shape is not an error."""
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1)
    return ""


def _int(value) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _meta(html: str, prop: str) -> str:
    """A page's share tag, which is the one place the title is guaranteed to be."""
    return _search(html, (r'<meta[^>]+(?:property|name)="%s"[^>]+content="([^"]*)"' % re.escape(prop),)).replace("&amp;", "&")


def _row(live: bool, title: str, viewers, started) -> dict:
    """One platform's answer in the shape look() promises, whatever the platform left out."""
    return {"live": bool(live), "title": str(title or "")[:MAX_TITLE] if live else "",
            "viewers": _int(viewers) if live else 0, "started": str(started or "")[:40] if live else ""}


def _twitch(ident: str) -> dict:
    d = _post("https://gql.twitch.tv/gql", {"query": TWITCH_QUERY, "variables": {"l": ident.lower()}},
              {"Client-ID": TWITCH_CLIENT})
    user = (d.get("data") or {}).get("user")
    if not user:
        raise ValueError("No Twitch channel with that name.")
    st = user.get("stream") or {}
    live = bool(st) and str(st.get("type") or "live").lower() == "live"
    return _row(live, st.get("title"), st.get("viewersCount"), st.get("createdAt"))


def _kick(ident: str) -> dict:
    d = json.loads(_get("https://kick.com/api/v2/channels/" + quote(ident.lower())))
    ls = d.get("livestream") or {}
    live = bool(ls) and ls.get("is_live") is not False       # the field is absent on older answers
    return _row(live, ls.get("session_title"), ls.get("viewer_count"), ls.get("start_time") or ls.get("created_at"))


def _youtube(ident: str) -> dict:
    h = ident if ident.startswith("@") else "@" + ident
    html = _get(f"https://www.youtube.com/{quote(h, safe='@')}/live", "text/html", 3_000_000)
    live = any(mark in html for mark in YT_LIVE)
    viewers = _search(html, (r'"concurrentViewers":"(\d+)"', r'"viewCount":"(\d+)"'))
    started = _search(html, (r'"startTimestamp":"([^"]{8,40})"', r'"publishDate":"([^"]{8,40})"'))
    return _row(live, _meta(html, "og:title"), viewers, started)


_LOOK = {"twitch": _twitch, "kick": _kick, "youtube": _youtube}
_cache: Dict[str, tuple] = {}      # key -> (when, answer or None, why it failed)
_lock = threading.RLock()


def _say(k: str, text: str) -> None:
    """Keep the last failure where a page can show it, in the same shape studio/ai.py uses."""
    problem.update(text=text, at=time.time(), key=k)


def _remember(k: str, info: Optional[dict], err: str = "") -> None:
    """One answer, kept for a minute; the oldest goes when the cache is full."""
    with _lock:
        _cache[k] = (time.time(), info, err)
        for old in list(_cache)[:max(0, len(_cache) - CACHE_MAX)]:
            _cache.pop(old, None)


def look(platform: str, ident: str) -> Optional[dict]:
    """Is this one streamer live right now: {platform, ident, key, live, title, viewers, started, looked_at},
    or None when the platform could not be asked. An answer is reused for a minute (half a minute for a
    failure); `problem` says why the last one failed. Never raises."""
    try:
        p, h = _clean(platform, ident)
    except ValueError as e:
        _say(key(platform, ident), str(e))
        return None
    k = f"{p}:{h.lower()}"
    now = time.time()
    with _lock:
        got = _cache.get(k)
    if got and now - got[0] < (FAIL_FOR if got[1] is None else _env_int("PEAKCUT_HUNT_LIVE_FOR", LIVE_FOR, 5)):
        if got[1] is None:
            _say(k, got[2])
        return got[1]
    try:
        info = _LOOK[p](h)
    except Exception as e:  # noqa: BLE001 - a platform that will not answer is a fact, not an outage
        err = _reason(e)
        _say(k, err)
        _remember(k, None, err)
        return None
    out = {"platform": p, "ident": h, "key": k, "live": bool(info["live"]), "title": info["title"],
           "viewers": info["viewers"], "started": info["started"], "looked_at": int(now)}
    _remember(k, out)
    return out


# ---------------------------------------------------------------- the watch list
_roster: Dict[str, object] = {"at": None, "rows": []}


def _file() -> Path:
    return Path(config.DATA_DIR) / "hunt.json"


def _norm_rows(data) -> List[dict]:
    """Whatever the file holds, as rows that can be looked at. Anything malformed is left out, never raised."""
    items = data.get("streamers") if isinstance(data, dict) else data
    rows: List[dict] = []
    seen = set()
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        try:
            p, h = _clean(item.get("platform"), item.get("ident"))
        except ValueError:
            continue
        k = f"{p}:{h.lower()}"
        if k in seen:
            continue
        seen.add(k)
        rows.append({"platform": p, "ident": h, "name": str(item.get("name") or h)[:80]})
        if len(rows) >= MAX_LIST:
            break
    return rows


def _read() -> List[dict]:
    """The streamers on the watch list, read again only when the file changes. A missing or hand-broken
    hunt.json is an empty list, so the list can never stop the server."""
    f = _file()
    try:
        at = f.stat().st_mtime_ns
    except OSError:
        at = 0
    with _lock:
        if _roster["at"] != at:
            data = {}
            if at:
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    data = {}
            _roster.update(at=at, rows=_norm_rows(data))
        return [dict(r) for r in _roster["rows"]]


def _write(rows: List[dict]) -> None:
    """The whole list in one go, so no other reader ever sees half a file."""
    f = _file()
    with _lock:
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps({"streamers": rows}, indent=1), encoding="utf-8")
        os.replace(tmp, f)
        _roster["at"] = None


def watch(platform: str, ident: str, name: str = "") -> dict:
    """Put a streamer on the watch list, or update their name. Raises ValueError on a platform or channel
    name that cannot be looked at, because that is a thing the person who typed it can fix."""
    p, h = _clean(platform, ident)
    row = {"platform": p, "ident": h, "name": str(name or h).strip()[:80] or h}
    rows = [r for r in _read() if f"{r['platform']}:{r['ident'].lower()}" != f"{p}:{h.lower()}"]
    if len(rows) >= MAX_LIST:
        raise ValueError(f"The watch list holds at most {MAX_LIST} streamers.")
    rows.append(row)
    _write(rows)
    return dict(row, key=f"{p}:{h.lower()}")


def unwatch(platform: str, ident: str) -> bool:
    """Take a streamer off the watch list. True when they were on it."""
    p, h = _clean(platform, ident)
    k = f"{p}:{h.lower()}"
    rows = _read()
    left = [r for r in rows if f"{r['platform']}:{r['ident'].lower()}" != k]
    if len(left) == len(rows):
        return False
    _write(left)
    return True


def watching() -> List[dict]:
    """Every streamer on the watch list, looked at now: the live ones first, the busiest first.

    Rows are {key, platform, ident, name, live, title, viewers, started, checked, error}. `checked` is False
    only for a streamer this call had no time to ask about, which the next call fills in. Nothing raises: a
    list that cannot be read is an empty list, and a platform that cannot be asked is a row with an `error`."""
    rows = _read()
    deadline = time.monotonic() + BUDGET
    limit = _env_int("PEAKCUT_HUNT_MAX", 24, 1)
    out: List[dict] = []
    for row in rows[:limit]:
        p, h = row["platform"], row["ident"]
        base = {"key": f"{p}:{h.lower()}", "platform": p, "ident": h, "name": row.get("name") or h}
        if time.monotonic() >= deadline:
            out.append(dict(base, live=False, title="", viewers=0, started="", checked=False,
                            error="Not checked yet - ask again in a minute."))
            continue
        info = look(p, h)
        if info is None:
            out.append(dict(base, live=False, title="", viewers=0, started="", checked=True,
                            error=problem["text"]))
        else:
            out.append(dict(base, live=info["live"], title=info["title"], viewers=info["viewers"],
                            started=info["started"], checked=True, error=""))
    return sorted(out, key=lambda r: (not r["live"], -r["viewers"]))
