"""Chat spikes: how fast the crowd talked, and what it chanted, with no login and no key."""

from __future__ import annotations

import collections
import json
import math
import os
import re
import shutil
import statistics
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from . import config

try:
    import httpx
except Exception:  # noqa: BLE001
    httpx = None

# httpx ships with the server already; the flag only exists so an install without it still boots.
AVAILABLE = httpx is not None

BIN = 10                    # seconds per bucket: short enough to find the moment, long enough to not be noise
MAX_MINUTES = 30            # one job never reads more than half an hour of chat
PAGE_DELAY = 0.15           # Twitch throttles by IP, so pages are asked for gently
RATIO = 3.0                 # a spike is 3x this stream's own usual rate, not a number that fits every stream
MIN_PEOPLE = 15             # a burst still has to be a real crowd, or four friends look like a spike
MIN_COUNT = 3               # a phrase has to be said at least this often to be worth showing
BUSY_MED = 20               # above this many messages a bin the median stops moving; a local pass is needed
MAX_MSGS = 400_000          # a ceiling so a runaway replay cannot eat the box

# Twitch's public web client: the same anonymous query any logged-out browser makes.
CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"
HASH = "b70a3591ff0f4e0313d126c6a1502d79a1c02baebb288227c582044aa76adf6a"
GQL = "https://gql.twitch.tv/gql"

# The words that mean the crowd reacted. Matched lower case after punctuation is stripped.
HYPE = frozenset({
    "kekw", "lul", "lulw", "lol", "lmao", "lmfao", "omegalul", "icant", "omg", "wtf",
    "pog", "poggers", "pogchamp", "pogu", "w", "ww", "www", "l", "ll", "d:",
    "monkas", "widepeepohappy", "clipit", "letsgo", "nooo", "noooo", "no?", "holy",
    "bruh", "sheesh", "insane", "cinema", "cooked",
})

# Chat-feed bots: counting them inflates every channel that has one.
BOTS = frozenset({
    "nightbot", "streamelements", "streamlabs", "moobot", "fossabot",
    "wizebot", "botrixoficial", "sery_bot", "kofistreambot", "pokemoncommunitygame",
})

_LOCK = threading.Lock()
_SAVED: dict = {"at": None, "data": {}}

_DEFAULTS = {
    "enabled": False,
    "mult": 1.6,
    "min_msgs": 5,
    "pct": 97.0,
    "local": True,
    "min_seconds": 120,
    "max_minutes": MAX_MINUTES,
}


class ChatError(Exception):
    """Chat could not be read, with a sentence a person can act on."""


@dataclass(frozen=True)
class ChatMap:
    """What chat did during one window: a count per 10 s bin, and the bins that were a spike."""

    bins: dict = field(default_factory=dict)
    ratios: dict = field(default_factory=dict)
    phrases: dict = field(default_factory=dict)
    med: float = 0.0
    total: int = 0
    seconds: int = 0

    def between(self, s: float, e: float) -> tuple:
        """Messages and the multiple of the usual rate across a time range."""
        keys = [b for b in self.bins if float(s) <= b < float(e)]
        n = sum(self.bins[b] for b in keys)
        usual = self.med or 1.0
        per_bin = n / max(1, len(keys))
        return n, per_bin / max(usual, 1.0)

    def flag(self, s: float, e: float) -> str:
        """The chat tag for a range, or "" when nothing there was worth mentioning.

        A tag is the busiest thing in the range, so a clip that sits on a quiet second is
        not sold as a spike because a spike happened nearby.
        """
        hit = [b for b in range(int(float(s) // BIN) * BIN, int(float(e)) + 1, BIN) if b in self.ratios]
        if not hit:
            return ""
        best = max(hit, key=lambda b: self.ratios[b])
        return _tag(self.ratios[best], self.phrases.get(best, []))


# ------------------------------------------------------------------ pure functions

def hms(s: str) -> int:
    """Seconds from "2:00:00", "20:00" or "95"."""
    total = 0
    for part in str(s).strip().split(":"):
        total = total * 60 + int(part or 0)
    return int(total)


def parse_win(w: str) -> tuple:
    """Seconds from a window like 2:00:00-2:20:00, or (0, None) for the whole video."""
    text = str(w or "").strip()
    if not text:
        return (0, None)
    if "-" not in text:
        raise ValueError("Give a window like 2:00:00-2:20:00.")
    a, b = text.split("-", 1)
    try:
        start, end = hms(a), hms(b)
    except ValueError:
        raise ValueError("Give a window like 2:00:00-2:20:00.") from None
    if end <= start:
        raise ValueError("The end of the window has to be after its start.")
    return (start, end)


def top_phrases(msgs: Iterable, n: int = 5) -> list:
    """The words the crowd chanted most in these messages, as (word, count) pairs."""
    counts: collections.Counter = collections.Counter()
    shown: dict = {}
    for m in msgs or []:
        text = _text_of(m)
        if not text:
            continue
        words = [w for w in text.split() if w]
        hit = set()
        for w in words:
            k = w.lower().strip(".,!?")
            if k in HYPE:
                hit.add(k)
        low = text.lower()
        if "clip it" in low or "clip that" in low:
            hit.add("clip it")
        # A short message that is mostly one repeated word is the chat chanting, not a sentence.
        if words and len(text) <= 25 and len(words) <= 4:
            first = words[0].lower()
            hit.add(first if len({w.lower() for w in words}) == 1 else low)
        for k in hit:
            counts[k] += 1
            shown.setdefault(k, next((w for w in words if w.lower().strip(".,!?") == k),
                                     text.upper() if k == "clip it" else k))
    out = []
    for k, v in counts.most_common(int(n)):
        if v < MIN_COUNT:
            continue
        word = shown.get(k, k)
        out.append((word.upper() if word.lower() in HYPE else word, v))
    return out


def find_spikes(msgs: Iterable, ratio: float = 3.0, minimum: int = 15, *,
                pct: float = 0.0, local: bool = True) -> list:
    """Bins of chat that ran at `ratio` times this stream's own usual rate, oldest first.

    Each result is {"t", "end", "count", "ratio", "phrases"}. The baseline is the median of
    every bin in the same window, so a loud channel and a quiet one are measured the same way.
    """
    rows = _clean(msgs)
    if not rows:
        return []
    start = (rows[0]["t"] // BIN) * BIN
    nb = max(1, int(math.ceil((rows[-1]["t"] + BIN - start) / float(BIN))))
    counts = [0] * nb
    buckets: list = [[] for _ in range(nb)]
    for m in rows:
        i = int((m["t"] - start) // BIN)
        if 0 <= i < nb:
            counts[i] += 1
            buckets[i].append(m)
    return _spikes(counts, buckets, start, ratio, minimum, pct, local)


def heat(msgs: Iterable, t0: float, t1: float) -> int:
    """How hot the reaction was between t0 and t1, 0-100, against the stream's own baseline."""
    rows = _clean(msgs)
    try:
        a, b = float(t0), float(t1)
    except (TypeError, ValueError):
        return 0
    if not rows or b <= a:
        return 0
    inside = [m for m in rows if a <= m["t"] < b]
    span = b - a
    whole = max(1.0, float(rows[-1]["t"] + BIN - rows[0]["t"]))
    base = len(rows) / whole
    rate = len(inside) / span
    parts = []
    if inside:
        # Twice the usual pace is a warm room; six times is a full house.
        parts.append(min(1.0, max(0.0, rate / max(base, 1e-6) - 1.0) / 5.0) * 0.8)
        if any(_hype(m["text"]) for m in inside):
            parts.append(0.1)
    left = 1.0
    for x in parts:
        left *= 1.0 - max(0.0, min(x, 0.95))
    return max(0, min(100, int(round(100 * (1.0 - left)))))


# ------------------------------------------------------------------ readers

def fetch(platform: str, ident: str, **kw: Any) -> list:
    """Read chat for a Twitch VOD or a YouTube replay; returns [{"t", "user", "text"}].

    No login and no key: Twitch is asked through its public web client, YouTube through the
    live-chat replay that yt-dlp already knows how to fetch.
    """
    start = int(kw.get("start") or 0)
    end = kw.get("end")
    delay = kw.get("delay", PAGE_DELAY)
    p = str(platform or "").strip().lower()
    if p in ("twitch", "ttv"):
        return _twitch(str(ident or ""), start, end, delay=delay)
    if p in ("youtube", "yt"):
        return _youtube(str(ident or ""), start, end)
    if p == "kick":
        raise ChatError("Kick chat is not ported: it needs a live websocket, which this server does not ship.")
    raise ChatError("Chat is only available for Twitch VODs and YouTube replays.")


def for_job(url: str, start: float, end: float, *, log=print):
    """The chat map for a window, or None. Never raises, so a job carries on without chat."""
    cfg = saved()
    if not cfg.get("enabled") or not url:
        return None
    try:
        a, b = int(start), int(end)
    except (TypeError, ValueError):
        return None
    if b - a < int(cfg["min_seconds"]):
        return None
    where = _platform(url)
    try:
        if where == "twitch":
            msgs = fetch("twitch", url, start=a, end=b)
        elif where == "youtube":
            msgs = fetch("youtube", url, start=a, end=b)
        else:
            return None
    except ChatError as e:
        log(f"chat: {_short(e)}")
        return None
    except Exception as e:  # noqa: BLE001
        log(f"chat: could not read chat ({_short(e)}).")
        return None
    try:
        return _map(msgs, a, b, cfg)
    except Exception as e:  # noqa: BLE001
        log(f"chat: could not read chat ({_short(e)}).")
        return None


# ------------------------------------------------------------------ settings, the house pattern

def _file() -> Path:
    return config.DATA_DIR / "chat.json"


def _number(body: dict, key: str, low: float, high: float, whole: bool, what: str) -> Any:
    if key not in body:
        return None
    try:
        v = float(body[key])
    except (TypeError, ValueError):
        raise ValueError(f"{what} has to be a number.") from None
    if not low <= v <= high:
        raise ValueError(f"{what} has to be between {low:g} and {high:g}.")
    return int(v) if whole else float(v)


def saved() -> dict:
    """The settings as they are on disk, re-read only when the file changed."""
    f = _file()
    try:
        at = f.stat().st_mtime_ns
    except OSError:
        at = 0
    if _SAVED["at"] == at and _SAVED["data"]:
        return dict(_SAVED["data"])
    data = dict(_DEFAULTS)
    try:
        raw = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            data.update({k: raw[k] for k in _DEFAULTS if k in raw})
    except (OSError, ValueError):
        pass
    _SAVED["at"], _SAVED["data"] = at, data
    return dict(data)


def public() -> dict:
    """What the settings page needs: the current values and the numbers behind them."""
    return {
        "settings": saved(),
        "available": AVAILABLE,
        "bin": BIN,
        "ratio": RATIO,
        "minimum": MIN_PEOPLE,
        "max_minutes": MAX_MINUTES,
        "bots": sorted(BOTS),
    }


def save(body: dict) -> dict:
    """Check and store the chat settings, then hand back what was actually kept."""
    body = body if isinstance(body, dict) else {}
    old = saved()
    out = dict(old)
    if "enabled" in body:
        out["enabled"] = bool(body["enabled"])
    if "local" in body:
        out["local"] = bool(body["local"])
    for key, low, high, whole, what in (
        ("mult", 1.0, 4.0, False, "The spike multiple"),
        ("min_msgs", 1, 50, True, "The fewest messages in a burst"),
        ("pct", 80.0, 99.9, False, "The percentile"),
        ("max_minutes", 1, 180, True, "The longest window"),
    ):
        v = _number(body, key, low, high, whole, what)
        if v is not None:
            out[key] = v
    if "min_seconds" in body:
        try:
            v = int(float(body["min_seconds"]))
        except (TypeError, ValueError):
            raise ValueError("The shortest window has to be a number of seconds.") from None
        top = int(out["max_minutes"]) * 60
        if not 60 <= v <= top:
            raise ValueError(f"The shortest window has to be between 60 and {top} seconds.")
        out["min_seconds"] = v
    with _LOCK:
        f = _file()
        tmp = f.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(out, indent=1), encoding="utf-8")
            try:
                os.chmod(tmp, 0o600)
            except OSError:
                pass
            tmp.replace(f)
        except OSError as e:
            raise ChatError(f"The chat settings could not be saved ({_short(e)}).") from None
        _SAVED["at"] = None
    return saved()


# ------------------------------------------------------------------ spikes, shared by both paths

def _spikes(counts: list, buckets: list, start: int, ratio: float, minimum: int,
            pct: float, local: bool) -> list:
    nb = len(counts)
    if not nb:
        return []
    ratio = max(1.0, float(ratio))
    floor = max(1, int(minimum))
    med = statistics.median(counts)
    usual = max(float(med), 1.0)
    hit: dict = {}
    for i, c in enumerate(counts):
        if c >= floor and c >= ratio * usual:
            hit[i] = c / usual
    if pct and 0 < pct < 100:
        # A high percentile of this stream's own bins also has to be beaten, which stops a
        # channel with an odd quiet patch from calling every normal minute a spike.
        gate = sorted(counts)[min(nb - 1, int(nb * float(pct) / 100.0))]
        hit = {i: r for i, r in hit.items() if counts[i] >= gate}
    if local and med >= BUSY_MED:
        # On a busy stream the median never moves, so a bin is also compared with its
        # neighbours: ten minutes either side is what "normal right now" means.
        near: dict = {}
        for i, c in enumerate(counts):
            if i in hit or c < floor:
                continue
            around = counts[max(0, i - 30):i] + counts[i + 1:i + 31]
            lm = statistics.median(around or [c])
            if lm >= 1 and c >= 1.25 * lm and c >= lm + 3 * math.sqrt(lm):
                near[i] = c / lm
        for i in sorted(near, key=near.get, reverse=True)[:max(3, nb // 50)]:
            hit[i] = near[i]
    out = []
    for i in sorted(hit):
        out.append({
            "t": start + i * BIN,
            "end": start + (i + 1) * BIN,
            "count": counts[i],
            "ratio": round(float(hit[i]), 2),
            "phrases": top_phrases(buckets[i] if i < len(buckets) else [], 3),
        })
    return out


def _map(msgs: list, start: int, end: int, cfg: dict) -> ChatMap:
    rows = _clean(msgs)
    nb = max(1, int(math.ceil((end - start) / float(BIN))))
    counts = [0] * nb
    buckets: list = [[] for _ in range(nb)]
    for m in rows:
        i = int((m["t"] - start) // BIN)
        if 0 <= i < nb:
            counts[i] += 1
            buckets[i].append(m)
    spikes = _spikes(counts, buckets, start, cfg["mult"], cfg["min_msgs"], cfg["pct"], bool(cfg["local"]))
    ratios = {s["t"]: s["ratio"] for s in spikes}
    phrases = {s["t"]: s["phrases"] for s in spikes}
    return ChatMap(
        bins={start + i * BIN: c for i, c in enumerate(counts) if c},
        ratios=ratios,
        phrases=phrases,
        med=float(statistics.median(counts)) if counts else 0.0,
        total=len(rows),
        seconds=nb * BIN,
    )


def _tag(ratio: float, phrases: list) -> str:
    tail = ""
    if phrases:
        tail = ": " + ", ".join(f'"{p}" x{n}' for p, n in phrases)
    return f" [CHAT x{float(ratio):.1f}{tail}]"


# ------------------------------------------------------------------ Twitch

def _twitch(ident: str, start: int, end, *, delay: float = PAGE_DELAY) -> list:
    if not AVAILABLE:
        raise ChatError("Chat needs httpx, which is not installed on this server.")
    vid = _twitch_id(ident)
    if not vid:
        raise ChatError("That is not a Twitch VOD: the address should look like twitch.tv/videos/1234567890.")
    if end is None:
        raise ChatError("Twitch chat is read in slices: give the end of the window as well as the start.")
    a, b = _window(start, end)
    seen: set = set()
    out: list = []
    off = float(a)
    pages = int((b - a) // 25) + 40      # the API returns ~25 comments a page; this is the cap
    while off < b and pages > 0 and len(out) < MAX_MSGS:
        pages -= 1
        batch = _twitch_page(vid, off)
        if batch is None:
            break
        fresh, last = 0, None
        for node in batch:
            if not isinstance(node, dict):
                continue
            key = node.get("id")
            if key in seen:
                continue
            seen.add(key)
            s = node.get("contentOffsetSeconds")
            if isinstance(s, bool) or not isinstance(s, (int, float)):
                continue
            fresh += 1
            last = float(s) if last is None else max(last, float(s))
            if not a <= float(s) < b:
                continue
            text = _twitch_text(node)
            if not text:
                continue
            out.append({"t": int(float(s)), "user": _twitch_user(node), "text": text})
        # No new comment means the page returned nothing we can move past, so step a second.
        off = last if fresh else off + 1
        time.sleep(max(0.0, float(delay)))
    out.sort(key=lambda m: m["t"])
    return out


def _twitch_page(vid: str, off: float):
    """One page of comments, or None when Twitch will not talk to us any more."""
    body = [{
        "operationName": "VideoCommentsByOffsetOrCursor",
        "variables": {"videoID": vid, "contentOffsetSeconds": int(max(0, off))},
        "extensions": {"persistedQuery": {"version": 1, "sha256Hash": HASH}},
    }]
    headers = {"Client-ID": CLIENT_ID, "Content-Type": "application/json"}
    last = ""
    for attempt in range(4):
        try:
            r = httpx.post(GQL, json=body, headers=headers, timeout=20)
            if r.status_code != 200:
                raise ValueError(f"Twitch answered {r.status_code}")
            payload = r.json()
        except Exception as e:  # noqa: BLE001
            last = _short(e)
            if attempt == 3:
                break
            time.sleep(2 ** attempt)      # a rate limit is told to wait, not hammered
            continue
        try:
            video = payload[0]["data"]["video"]
        except (ValueError, KeyError, IndexError, TypeError):
            # The query hash rotates now and then; that is "no chat", not a broken job.
            raise ChatError("Twitch did not send its comment list back; the chat query may have changed.") from None
        if video is None:
            raise ChatError("Twitch has no chat saved for that video.")
        nodes = video.get("comments")
        if not isinstance(nodes, list):
            raise ChatError("Twitch did not send its comment list back; the chat query may have changed.")
        return nodes
    raise ChatError(f"Twitch chat could not be read ({last}).")


def _twitch_text(node: dict) -> str:
    frags = (node.get("message") or {}).get("fragments") or []
    return "".join(str(f.get("text") or "") for f in frags if isinstance(f, dict)).strip()


def _twitch_user(node: dict) -> str:
    return str((node.get("commenter") or {}).get("displayName") or "")


def _twitch_id(ident: str) -> str:
    m = re.search(r"twitch\.tv/videos/(\d+)", str(ident or ""))
    if m:
        return m.group(1)
    text = str(ident or "").strip()
    return text if text.isdigit() else ""


# ------------------------------------------------------------------ YouTube

def _youtube(ident: str, start: int = 0, end=None) -> list:
    if not AVAILABLE:
        raise ChatError("Chat needs httpx, which is not installed on this server.")
    vid = _youtube_id(ident)
    if not vid:
        raise ChatError("That is not a YouTube link or video id.")
    a, b = _window(start, end)
    try:
        work = Path(tempfile.mkdtemp(dir=str(config.TMP_DIR), prefix="chat_"))
    except OSError:
        work = Path(tempfile.mkdtemp(prefix="chat_"))     # the data folder may be read-only
    try:
        try:
            from .media import _ydl
        except Exception as e:  # noqa: BLE001
            raise ChatError(f"The downloader is not available ({_short(e)}).") from None
        try:
            ydl = _ydl({
                "skip_download": True,
                "writesubtitles": True,
                "subtitleslangs": ["live_chat"],
                "outtmpl": str(work / "c.%(ext)s"),
                "quiet": True,
            })
            ydl.download([f"https://www.youtube.com/watch?v={vid}"])
        except ChatError:
            raise
        except Exception as e:  # noqa: BLE001
            raise ChatError(f"YouTube live chat could not be read ({_short(e)}).") from None
        files = sorted(work.glob("*live_chat*"))
        if not files:
            raise ChatError("That video has no live chat replay saved.")
        out: list = []
        for f in files:
            out.extend(_read_replay(f, a, b))
        out.sort(key=lambda m: m["t"])
        return out[:MAX_MSGS]
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _read_replay(path: Path, start: int, end) -> list:
    """Messages from one yt-dlp live-chat file; a broken line is skipped, never fatal."""
    out: list = []
    try:
        handle = open(path, "r", encoding="utf-8", errors="replace")
    except OSError:
        return out
    with handle:
        for line in handle:
            if len(out) >= MAX_MSGS:
                break
            line = line.strip()
            if not line:
                continue
            try:
                act = json.loads(line)["replayChatItemAction"]
                ms = int(act["videoOffsetTimeMsec"])
            except (ValueError, KeyError, TypeError):
                continue
            s = ms / 1000.0
            if s < start or (end is not None and s >= end):
                continue
            for step in act.get("actions") or []:
                item = (step.get("addChatItemAction") or {}).get("item") or {}
                node = item.get("liveChatTextMessageRenderer")
                if not isinstance(node, dict):
                    continue
                text = _render_text(node)
                if text:
                    out.append({"t": ms // 1000, "user": _render_user(node), "text": text})
    return out


def _render_text(node: dict) -> str:
    parts = []
    for x in node.get("message", {}).get("runs") or []:
        if not isinstance(x, dict):
            continue
        if x.get("text"):
            parts.append(str(x["text"]))
        else:
            emoji = x.get("emoji") or {}
            shorts = emoji.get("shortcuts") or [emoji.get("emojiId") or ""]
            parts.append(str(shorts[0]))
    return "".join(parts).strip()


def _render_user(node: dict) -> str:
    name = node.get("authorName") or {}
    if isinstance(name, dict):
        return str(name.get("simpleText") or "".join(str(r.get("text") or "")
                                                      for r in name.get("runs") or [] if isinstance(r, dict)))
    return ""


def _youtube_id(ident: str) -> str:
    text = str(ident or "").strip()
    m = re.search(r"(?:v=|/shorts/|youtu\.be/|/live/|/embed/)([A-Za-z0-9_-]{11})", text)
    if m:
        return m.group(1)
    return text if re.fullmatch(r"[A-Za-z0-9_-]{11}", text) else ""


def _platform(url: str) -> str:
    low = str(url or "").lower()
    if "twitch.tv" in low:
        return "twitch"
    if "youtube.com" in low or "youtu.be" in low:
        return "youtube"
    if "kick.com" in low:
        return "kick"
    return ""


# ------------------------------------------------------------------ small helpers

def _window(start: Any, end: Any) -> tuple:
    try:
        a = max(0, int(start or 0))
    except (TypeError, ValueError):
        a = 0
    if end is None:
        return a, None
    try:
        b = int(end)
    except (TypeError, ValueError):
        raise ChatError("The end of the window has to be a number of seconds.") from None
    if b <= a:
        raise ChatError("The end of the window has to be after its start.")
    if b - a > MAX_MINUTES * 60:
        raise ChatError(f"That is more than {MAX_MINUTES} minutes of chat; narrow the range.")
    return a, b


def _text_of(m: Any) -> str:
    if isinstance(m, str):
        return m
    if isinstance(m, dict):
        t = m.get("text")
        return t if isinstance(t, str) else ""
    return ""


def _clean(msgs: Iterable) -> list:
    """Only messages with a usable time, oldest first: everything here is time binned."""
    out = []
    for m in msgs or []:
        if not isinstance(m, dict):
            continue
        t = m.get("t")
        if isinstance(t, bool) or not isinstance(t, (int, float)):
            continue
        out.append({"t": int(t), "user": str(m.get("user") or ""), "text": _text_of(m)})
    out.sort(key=lambda m: m["t"])
    return out


def _hype(text: str) -> bool:
    return any(w.lower().strip(".,!?") in HYPE for w in str(text or "").split())


def _short(e: Any, limit: int = 200) -> str:
    text = " ".join(str(e).split())
    return text[-limit:] if text else "no reason given"
