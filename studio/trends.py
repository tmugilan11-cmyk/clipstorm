"""What people are joking about this week, looked up on the web once a day and kept.

The judge is told these so it recognises a reference when a streamer makes one, and so a hook can use the
words people are already searching for. It is a hint and nothing more: when the web cannot be reached the
judge simply works without it. The list is kept in `trends.json` in the data folder; nothing personal is
sent anywhere, only two public feeds are read.
"""
from __future__ import annotations

import json
import re
import threading
import time

from . import config

FEEDS = (("https://knowyourmeme.com/newsfeed.rss", 14),          # the memes being explained right now
         ("https://trends.google.com/trending/rss?geo=US", 8))   # what people are searching for today
KEEP_FOR = 24 * 3600
RETRY_AFTER = 3600           # a lookup that failed is not tried again for an hour
_lock = threading.Lock()
_state = {"at": 0.0, "tried": 0.0, "lines": []}
_TITLE = re.compile(r"<item>.*?<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", re.S)


def _file():
    return config.DATA_DIR / "trends.json"


def _fetch(url: str, most: int) -> list:
    import html
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=12) as r:
        text = r.read(600_000).decode("utf-8", "ignore")
    out = []
    for raw in _TITLE.findall(text)[:most]:
        t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", raw))).strip()
        if 2 < len(t) <= 90:
            out.append(t)
    return out


def refresh() -> list:
    """Look the feeds up now and keep what came back. Returns the lines; empty when nothing could be read."""
    got = []
    for url, most in FEEDS:
        try:
            got += _fetch(url, most)
        except Exception:  # noqa: BLE001 - a feed that is down is not a problem worth reporting
            continue
    seen, lines = set(), []
    for t in got:
        if t.lower() not in seen:
            seen.add(t.lower())
            lines.append(t)
    with _lock:
        _state["tried"] = time.time()
        if lines:
            _state.update(at=time.time(), lines=lines[:24])
            try:
                _file().write_text(json.dumps({"at": _state["at"], "lines": _state["lines"]}), encoding="utf-8")
            except OSError:
                pass
    return lines


def lines() -> list:
    """This week's references, from memory or the saved file. Never waits on the web: when the list is old a
    fresh one is fetched on a thread and used from the next call on."""
    now = time.time()
    with _lock:
        if not _state["at"] and not _state["tried"]:
            try:
                saved = json.loads(_file().read_text(encoding="utf-8"))
                if isinstance(saved, dict) and isinstance(saved.get("lines"), list):
                    _state.update(at=float(saved.get("at") or 0), lines=[str(x)[:90] for x in saved["lines"]][:24])
            except Exception:  # noqa: BLE001 - no file yet, or one that cannot be read
                pass
        stale = now - _state["at"] > KEEP_FOR and now - _state["tried"] > RETRY_AFTER
        if stale:
            _state["tried"] = now
        have = list(_state["lines"]) if now - _state["at"] <= 7 * KEEP_FOR else []
    if stale:
        threading.Thread(target=refresh, daemon=True, name="trends").start()
    return have
