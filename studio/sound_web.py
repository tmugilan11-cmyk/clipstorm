"""What the web says about meme sounds: which ones people play most, and what each one is for.

The sound picker used to know a sound only by its name in a catalogue, so it could not tell "the sound people
play when someone fails" from "a laugh in Indonesian that happened to be trending". This module reads the
places that actually know, and keeps what it read for a week:

    myinstants      the biggest meme soundboard. Its "best of all time" and "trending" lists are the most
                    honest popularity ranking there is, and each sound's own page says how many times it was
                    played and how many people saved it.
    Know Your Meme  what a meme sound means, where it came from and when people use it (the "About" part of
                    its page).
    YouTube         how many people watched the sound on its own (the top "<name> sound effect" upload), and
                    the titles of the edits it is used in, which say what moment it is used for.

Only reading happens here. No sound file is ever downloaded from these sites: the files come from the catalogue
`memesound.py` already uses (dankmachine.com), which mirrors myinstants under the same names.

`studio/web.py` has a general web search, but on this machine its results page answers with unrelated pages
(asked "vine boom meme sound" it returned dictionary entries), so the sound research reads these sources
directly instead.

Nothing here can fail a render or a suggestion: with no internet, a site that changed, `PEAKCUT_SOUND_WEB=0`
or `PEAKCUT_JUDGE_WEB=0`, every function answers empty. Only the name of a sound is ever sent anywhere.
"""
from __future__ import annotations

import html
import json
import re
import threading
import time
import urllib.parse
from typing import Dict, List, Optional

import httpx

from . import config

KEEP = 7 * 24 * 3600            # a week: popularity moves slowly, and the owner asked for a weekly refresh
KEEP_EMPTY = 24 * 3600          # an empty answer is asked again after a day: the site may have been down
MI = "https://www.myinstants.com"
KYM = "https://knowyourmeme.com"
_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/126.0 Safari/537.36", "Accept-Language": "en-US,en;q=0.9"}
_lock = threading.Lock()
_book: Dict[str, dict] = {}
_loaded = {"done": False}
_gap = {"at": 0.0}              # one request at a time per site is polite, and keeps us from being blocked
MIN_SPACING = 0.25


def on() -> bool:
    """Whether the sound research may use the internet at all."""
    if config.env("PEAKCUT_SOUND_WEB", "1").strip() == "0":
        return False
    return config.env("PEAKCUT_JUDGE_WEB", "1").strip() != "0"


def _file():
    return config.DATA_DIR / "memesounds" / "web.json"


def _load() -> dict:
    with _lock:
        if not _loaded["done"]:
            try:
                got = json.loads(_file().read_text(encoding="utf-8"))
                _book.update(got if isinstance(got, dict) else {})
            except (OSError, ValueError):
                pass
            _loaded["done"] = True
        return _book


def save() -> None:
    """Write what was read to disk. Called after a batch of lookups rather than after each one."""
    with _lock:
        if len(_book) > 4000:                       # the oldest answers go first
            for k in sorted(_book, key=lambda k: _book[k].get("at", 0))[: len(_book) - 4000]:
                _book.pop(k, None)
        try:
            _file().parent.mkdir(parents=True, exist_ok=True)
            tmp = _file().with_suffix(".tmp")
            tmp.write_text(json.dumps(_book, ensure_ascii=False), encoding="utf-8")
            tmp.replace(_file())
        except OSError:
            pass


def _kept(key: str):
    hit = _load().get(key)
    if not hit:
        return None
    age = time.time() - float(hit.get("at") or 0)
    if age < (KEEP if hit.get("v") else KEEP_EMPTY):
        return hit.get("v")
    return None


def _keep(key: str, value) -> None:
    with _lock:
        _book[key] = {"at": time.time(), "v": value}


def _page(url: str, limit: int = 900_000) -> str:
    """One page as text, or "" on any trouble."""
    with _lock:
        wait = MIN_SPACING - (time.time() - _gap["at"])
        _gap["at"] = time.time() + max(0.0, wait)
    if wait > 0:
        time.sleep(wait)
    try:
        r = httpx.get(url, headers=_UA, timeout=20, follow_redirects=True)
    except httpx.HTTPError:
        return ""
    if r.status_code != 200:
        return ""
    return r.text[:limit]


def _plain(s: str, limit: int = 400) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()[:limit]


def _count(text: str) -> int:
    try:
        return int(re.sub(r"[^\d]", "", text or "") or 0)
    except ValueError:
        return 0


# ---------------------------------------------------------------- myinstants: the popularity lists
_LINK = re.compile(r'<a href="/en/instant/([A-Za-z0-9_.-]+)/"[^>]*class="instant-link[^"]*"[^>]*>([^<]+)</a>')
_LINK2 = re.compile(r'class="instant-link[^"]*"[^>]*href="/en/instant/([A-Za-z0-9_.-]+)/"[^>]*>([^<]+)</a>')


def _instants(page: str) -> List[dict]:
    rows, seen = [], set()
    for rx in (_LINK, _LINK2):
        for slug, title in rx.findall(page):
            if slug in seen:
                continue
            seen.add(slug)
            rows.append({"slug": slug, "title": _plain(title, 120)})
    if rows:
        return rows
    # The markup moves now and then; the instant addresses themselves are the part that stays.
    for slug in re.findall(r'href="/en/instant/([A-Za-z0-9_.-]+)/"', page):
        if slug not in seen:
            seen.add(slug)
            rows.append({"slug": slug, "title": slug.replace("-", " ")})
    return rows


def ranking(kind: str = "best", pages: int = 4, region: str = "us") -> List[dict]:
    """myinstants' own list, in its order: "best" is the most played of all time, "trending" is now.

    Each row is {"slug", "title", "rank"}; rank 1 is the top of the list."""
    if not on():
        return []
    kind = "trending" if kind == "trending" else "best"
    key = f"mi:{kind}:{region}:{pages}"
    hit = _kept(key)
    if hit is not None:
        return hit
    base = f"{MI}/en/index/{region}/" if kind == "trending" else f"{MI}/en/best_of_all_time/{region}/"
    rows, seen = [], set()
    for n in range(1, max(1, pages) + 1):
        got = _instants(_page(base + (f"?page={n}" if n > 1 else "")))
        if not got:
            break
        for r in got:
            if r["slug"] not in seen:
                seen.add(r["slug"])
                rows.append(dict(r, rank=len(rows) + 1))
    _keep(key, rows)
    return rows


def instant(slug: str) -> dict:
    """What one sound's own myinstants page says: {"views", "saves", "about"}, or {} when it cannot be read."""
    name = str(slug or "").strip()
    if not on() or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", name):
        return {}
    key = f"mi:i:{name}"
    hit = _kept(key)
    if hit is not None:
        return hit
    page = _page(f"{MI}/en/instant/{name}/", 300_000)
    out: dict = {}
    if page:
        m = re.search(r"([\d,\.]+)\s*views", page)
        if m:
            out["views"] = _count(m.group(1))
        m = re.search(r"([\d,\.]+)\s*users", page)
        if m:
            out["saves"] = _count(m.group(1))
        m = re.search(r'<meta name="description" content="([^"]+)"', page)
        if m:
            said = _plain(m.group(1), 300)
            said = re.sub(r"^Listen (?:&|and) share\s*", "", said)
            said = re.sub(r"[\d,\.]+ views\..*$", "", said).strip(" .")
            if said:
                out["about"] = said
        tags = re.findall(r'href="/en/search/\?name=([^"&]+)"', page)
        if tags:
            out["tags"] = sorted({urllib.parse.unquote_plus(t)[:30] for t in tags})[:10]
    _keep(key, out)
    return out


def find(words: str) -> List[dict]:
    """myinstants' own search: [{"slug", "title"}] in its order (most played first). This is how the picker looks
    for a sound for one particular moment ("deer", "voicemail", "hallelujah") beyond the ones it already knows."""
    q = re.sub(r"\s+", " ", str(words or "")).strip()[:60]
    if not on() or len(q) < 2:
        return []
    key = f"mi:f:{q.lower()}"
    hit = _kept(key)
    if hit is not None:
        return hit
    page = _page(f"{MI}/en/search/?name=" + urllib.parse.quote_plus(q))
    rows = _instants(page)[:24]
    _keep(key, rows)
    return rows


def variants(name: str) -> List[str]:
    """The other uploads of a sound under similar names on myinstants. Many re-uploads means a meme that
    spread, and their names often say what the sound is used for ("bruh moment", "sad bruh")."""
    return [r["title"] for r in find(name)]


# ---------------------------------------------------------------- Know Your Meme: what a sound means
def _kym_slugs(name: str) -> List[str]:
    base = re.sub(r"[^a-z0-9]+", "-", str(name or "").lower()).strip("-")
    base = re.sub(r"-(sound|sfx|meme|effect|sound-effect)$", "", base)
    base = re.sub(r"-\d{3,}$", "", base)
    if not base:
        return []
    out = [f"{base}-sound-effect", base, f"{base}-sound"]
    return list(dict.fromkeys(out))


def meaning(name: str, tries: Optional[List[str]] = None) -> dict:
    """Know Your Meme's explanation of a meme: {"page", "about"}, or {} when it has no page under the usual
    names. `tries` are extra page names to try (the catalogue's aliases)."""
    if not on():
        return {}
    key = f"kym:{str(name or '').lower()[:80]}"
    hit = _kept(key)
    if hit is not None:
        return hit
    out: dict = {}
    names = _kym_slugs(name)
    for extra in tries or []:
        names += [s for s in _kym_slugs(extra) if s not in names]
    for slug in names[:5]:
        page = _page(f"{KYM}/memes/{slug}", 600_000)
        if not page:
            continue
        m = re.search(r'<h2 id="about">About</h2>\s*(.*?)<h2', page, re.S)
        about = _plain(m.group(1), 900) if m else ""
        if not about:
            m = re.search(r'<meta (?:content="([^"]+)" (?:name|property)="(?:og:)?description"|'
                          r'(?:name|property)="(?:og:)?description" content="([^"]+)")', page)
            about = _plain((m.group(1) or m.group(2)) if m else "", 600)
        if about:
            title = re.search(r"<title>\s*(.*?)\s*\|", page, re.S)
            out = {"page": f"{KYM}/memes/{slug}", "title": _plain(title.group(1), 120) if title else "",
                   "about": about}
            m = re.search(r'<h2 id="spread">Spread</h2>\s*(.*?)<h2', page, re.S)
            if m:
                out["spread"] = _plain(m.group(1), 700)
            break
    _keep(key, out)
    return out


# ---------------------------------------------------------------- YouTube: how many watched, and in what
class _Quiet:
    def debug(self, m): pass
    def info(self, m): pass
    def warning(self, m): pass
    def error(self, m): pass


def youtube(query: str, n: int = 8) -> List[dict]:
    """YouTube's own search for a query: [{"title", "views", "seconds"}], in YouTube's order. Nothing is
    downloaded; this is the same flat search `web.top_clips` uses."""
    q = re.sub(r"\s+", " ", str(query or "")).strip()[:100]
    if not on() or len(q) < 2:
        return []
    key = f"yt:{q.lower()}:{n}"
    hit = _kept(key)
    if hit is not None:
        return hit
    rows: List[dict] = []
    try:
        import yt_dlp
        opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "skip_download": True,
                "logger": _Quiet(), "socket_timeout": 15}
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info(f"ytsearch{max(1, min(20, n))}:{q}", download=False)
        for e in (info or {}).get("entries") or []:
            title = _plain((e or {}).get("title") or "", 110)
            if title:
                rows.append({"title": title, "views": int((e or {}).get("view_count") or 0),
                             "seconds": int((e or {}).get("duration") or 0)})
    except Exception:  # noqa: BLE001 - no yt-dlp, no internet, a changed page: simply nothing
        rows = []
    _keep(key, rows)
    return rows
