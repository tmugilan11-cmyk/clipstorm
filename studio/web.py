"""What the judge looks up on the web: the references a streamer makes, and the clips of them people really watched.

Two things, both kept on disk so the web is asked rarely:

- `search(query)` - a plain web search (titles and snippets) for a meme, a name or a phrase the first read of
  a transcript could not place. Kept for three days.
- `top_clips(name)` - the most-watched clips of this streamer on YouTube, with their view counts, found
  through YouTube's own search. This is the real data the judge is shown as taste: not what somebody says
  goes viral, but the titles and lengths of clips that did. Kept for a week.

Nothing here can fail a job. With no internet, a blocked request or `PEAKCUT_JUDGE_WEB=0`, both return
nothing and the judge works from the transcript alone. Only the query is sent anywhere; nothing about the
person using the tool is.
"""
from __future__ import annotations

import html
import json
import re
import threading
import time
import urllib.parse
import urllib.request

from . import config

SEARCH_KEEP = 3 * 24 * 3600
CLIPS_KEEP = 7 * 24 * 3600
_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/126.0 Safari/537.36", "Accept-Language": "en-US,en;q=0.9"}
_HIT = re.compile(r'<li class="b_algo".*?<h2[^>]*>(.*?)</h2>.*?<p[^>]*>(.*?)</p>', re.S)
_lock = threading.Lock()
_mem: dict = {}


def on() -> bool:
    return config.env("PEAKCUT_JUDGE_WEB", "1").strip() != "0"


def _plain(s: str, limit: int) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s or ""))).strip()[:limit]


def _file(name: str):
    return config.DATA_DIR / name


def _load(name: str) -> dict:
    with _lock:
        if name not in _mem:
            try:
                got = json.loads(_file(name).read_text(encoding="utf-8"))
                _mem[name] = got if isinstance(got, dict) else {}
            except Exception:  # noqa: BLE001 - no file yet
                _mem[name] = {}
        return _mem[name]


def _save(name: str, most: int = 400) -> None:
    with _lock:
        book = _mem.get(name) or {}
        if len(book) > most:                      # the oldest answers go first
            for k in sorted(book, key=lambda k: book[k].get("at", 0))[: len(book) - most]:
                book.pop(k, None)
        try:
            tmp = _file(name + ".tmp")
            tmp.write_text(json.dumps(book), encoding="utf-8")
            tmp.replace(_file(name))
        except OSError:
            pass


def search(query: str, n: int = 4) -> list:
    """Web results for a query: [{"title", "snippet"}], possibly empty. Never raises."""
    q = re.sub(r"\s+", " ", str(query or "")).strip()[:120]
    if not q or not on():
        return []
    book = _load("websearch.json")
    hit = book.get(q.lower())
    if hit and time.time() - hit.get("at", 0) < SEARCH_KEEP:
        return hit.get("rows", [])[:n]
    rows = []
    try:
        req = urllib.request.Request("https://www.bing.com/search?q=" + urllib.parse.quote(q), headers=_UA)
        with urllib.request.urlopen(req, timeout=10) as r:
            page = r.read(700_000).decode("utf-8", "ignore")
        for a, b in _HIT.findall(page)[:8]:
            title, snippet = _plain(a, 110), _plain(b, 260)
            if title and snippet:
                rows.append({"title": title, "snippet": snippet})
    except Exception:  # noqa: BLE001 - no internet, blocked, changed page: the judge simply goes without
        return hit.get("rows", [])[:n] if hit else []
    with _lock:
        book[q.lower()] = {"at": time.time(), "rows": rows[:8]}
    _save("websearch.json")
    return rows[:n]


class _Quiet:
    def debug(self, m): pass
    def info(self, m): pass
    def warning(self, m): pass
    def error(self, m): pass


def top_clips(name: str, game: str = "", n: int = 12) -> list:
    """The most-watched clips of this streamer on YouTube: [{"title", "views", "seconds"}], best first.

    Found with YouTube's own search (no key, nothing downloaded). Clips of the streamer in the same game come
    first when a game is known. Never raises."""
    who = re.sub(r"\s+", " ", str(name or "")).strip()[:60]
    if len(who) < 3 or who.lower() in ("unknown", "u") or not on():
        return []
    key = (who + "|" + str(game or "")).lower()
    book = _load("topclips.json")
    hit = book.get(key)
    if hit and time.time() - hit.get("at", 0) < CLIPS_KEEP:
        return hit.get("rows", [])[:n]
    rows, seen = [], set()
    asks = [f"{who} shorts funny moments", f"{who} clips viral"]
    if game:
        asks.insert(0, f"{who} {game} funny moments")
    try:
        import yt_dlp
        opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "skip_download": True,
                "logger": _Quiet(), "socket_timeout": 15}
        with yt_dlp.YoutubeDL(opts) as y:
            for ask in asks:
                try:
                    info = y.extract_info(f"ytsearch20:{ask}", download=False)
                except Exception:  # noqa: BLE001
                    continue
                for e in (info or {}).get("entries") or []:
                    title = _plain((e or {}).get("title") or "", 110)
                    views = int((e or {}).get("view_count") or 0)
                    if not title or title.lower() in seen or views < 50_000:
                        continue
                    seen.add(title.lower())
                    rows.append({"title": title, "views": views, "seconds": int((e or {}).get("duration") or 0)})
    except Exception:  # noqa: BLE001
        return hit.get("rows", [])[:n] if hit else []
    # short clips teach more than ten-minute compilations, so they come first; then by how many watched
    rows.sort(key=lambda r: (0 if 0 < r["seconds"] <= 90 else 1, -r["views"]))
    with _lock:
        book[key] = {"at": time.time(), "rows": rows[:24]}
    _save("topclips.json")
    return rows[:n]
