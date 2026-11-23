"""Posting clips through Zernio, if you would rather not connect each platform yourself.

Zernio is one API in front of sixteen social networks. You bring your own key, paste it in
Settings, Connected apps, and PeakCut sends the clip there the same way it sends it to a
platform it connected itself. Nothing else changes: the queue, the retries and the views all
work as before.

    PEAKCUT_ZERNIO_KEY      your key (or PEAKCUT_ZERNIO_KEY_FILE, a file holding it)
    PEAKCUT_ZERNIO_BASE     only to point at another address; the default is Zernio's own

What is saved from the dashboard is kept in zernio.json in the data folder and wins over .env.

The four things that matter, in Zernio's own words:

  GET  /v1/accounts                          the accounts you connected, with their ids
  POST /v1/media/presign                     {filename, contentType} -> {uploadUrl, publicUrl}
  POST /v1/posts                             {content, mediaItems:[{type, url}], platforms:[...], publishNow}
  GET  /v1/posts/{id}                        the status of one post

Uploading is two steps: ask for an upload address, PUT the file to it, then post the publicUrl.

A post with no `mediaItems` and none of `publishNow` / `scheduledFor` is saved by Zernio as an empty
draft and never reaches any platform. That is how the first clips sent through here ended up: Zernio
said "draft", nothing was on Instagram or YouTube, and the page said "posted" (2026-11-23).
"""
import json
import os
import threading
import time
from pathlib import Path
from typing import Optional

import httpx

from . import config

# 16 platforms Zernio publishes to, with the name shown on the page
PLATFORMS = {
    "youtube": "YouTube",
    "tiktok": "TikTok",
    "instagram": "Instagram",
    "facebook": "Facebook",
    "twitter": "X",
    "linkedin": "LinkedIn",
    "threads": "Threads",
    "pinterest": "Pinterest",
    "bluesky": "Bluesky",
    "reddit": "Reddit",
    "snapchat": "Snapchat",
    "discord": "Discord",
    "telegram": "Telegram",
    "googlebusiness": "Google Business",
    "wordpress": "WordPress",
    "shopify": "Shopify",
}

# what Zernio will accept as an upload, so a wrong one is refused before it is sent
TYPES = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".m4v": "video/x-m4v",
    ".webm": "video/webm",
    ".avi": "video/avi",
    ".mkv": "video/mp4",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
}

CAP = 5 * 1024 * 1024 * 1024        # Zernio takes files up to 5 GB
TIMEOUT = 120.0                     # uploading a clip takes a while; posting can queue it

_lock = threading.Lock()
_saved = {"at": None, "data": {}}
# The account list is asked for on every page draw and again for each post, so it is kept for a
# minute. Anything that changes the list (saving a key, posting) asks for a fresh one.
_cache = {"at": 0.0, "key": "", "rows": []}
CACHE_SECONDS = 60.0


# ---------------------------------------------------------------- the key in use
def _file() -> Path:
    return config.DATA_DIR / "zernio.json"


def _from_dashboard() -> dict:
    """What was saved from the dashboard, read again only when the file changes."""
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


def key() -> str:
    """The Zernio key: what the dashboard saved, or else .env."""
    saved = (_from_dashboard().get("key") or "").strip()
    return saved or config.zernio_key()


def base() -> str:
    return (config.env("PEAKCUT_ZERNIO_BASE") or "https://zernio.com/api/v1").rstrip("/")


def saved() -> dict:
    """Whether a key is in place, never the key itself."""
    k = key()
    return {"ready": bool(k), "has_key": bool(k), "key_hint": k[-4:] if len(k) >= 12 else "",
            "base": base(), "platforms": PLATFORMS}


def save(body: dict) -> dict:
    """Save the key from the dashboard. An empty key keeps the one already saved."""
    k = str(body.get("key") or "").strip()[:300]
    forget = bool(body.get("forget_key"))
    with _lock:
        data = dict(_from_dashboard())
        if forget:
            data.pop("key", None)
        elif k:
            if len(k) < 16:
                raise ValueError("That does not look like a Zernio key. Copy it whole from the dashboard.")
            data["key"] = k
        tmp = _file().with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(data), encoding="utf-8")
            os.chmod(tmp, 0o600)
            tmp.replace(_file())
        except OSError as e:
            raise ValueError(f"Could not save the Zernio key: {e}")
    return saved()


# ---------------------------------------------------------------- talking to Zernio
class ZernioError(ValueError):
    """Zernio said no, or could not be reached. The message is a sentence for a person."""


def _call(method: str, path: str, key_override: Optional[str] = None, **kw) -> dict:
    """One request to Zernio, with the errors turned into sentences."""
    k = key_override if key_override is not None else key()
    if not k:
        raise ZernioError("Paste a Zernio key in Settings, Connected apps first.")
    url = base() + path
    head = {"Authorization": "Bearer " + k, "Accept": "application/json"}
    head.update(kw.pop("headers", {}) or {})
    wait = kw.pop("timeout", TIMEOUT)
    try:
        r = httpx.request(method, url, headers=head, timeout=wait, **kw)
    except httpx.HTTPError as e:
        raise ZernioError(f"Could not reach Zernio: {type(e).__name__}. Check this machine's internet "
                          f"connection, then try again.")
    return _check(r)


def _check(r: httpx.Response) -> dict:
    if r.status_code in (200, 201, 202, 207):   # 207: published on some platforms, not all
        try:
            got = r.json()
        except ValueError:
            raise ZernioError("Zernio answered with something that was not JSON. Try again.")
        return got if isinstance(got, dict) else {"data": got}
    if r.status_code == 401:
        raise ZernioError("Zernio rejected the key. Copy a current one from Zernio, "
                          "under API keys, and paste it here.")
    if r.status_code == 403:
        raise ZernioError("This Zernio key is not allowed to do that. Check the key's plan and permissions.")
    if r.status_code == 404:
        raise ZernioError("Zernio has nothing at that address. It may have been deleted there.")
    if r.status_code == 429:
        back = r.headers.get("retry-after") or ""
        wait = f" Try again in {back} seconds." if back else " Try again in a minute."
        raise ZernioError("Zernio is rate limiting this key." + wait)
    if r.status_code == 413:
        raise ZernioError("That file is too big for Zernio. It takes files up to 5 GB.")
    detail = _detail(r)
    raise ZernioError(f"Zernio answered {r.status_code}{': ' + detail if detail else '.'}")


def _detail(r: httpx.Response) -> str:
    """The sentence Zernio put in its error body, if it put one there."""
    try:
        got = r.json()
    except ValueError:
        return (r.text or "").strip()[:200]
    if not isinstance(got, dict):
        return ""
    err = got.get("error")
    if isinstance(err, dict):
        return str(err.get("message") or "")[:200]
    if isinstance(err, str):
        return err[:200]
    for k in ("message", "detail", "error_description"):
        if got.get(k):
            return str(got[k])[:200]
    return ""


# ---------------------------------------------------------------- the things the app asks for
def accounts(key_override: Optional[str] = None) -> list:
    """The accounts connected on Zernio, in the shape the rest of the app uses.

    Every entry is {"id", "platform", "label", "name", "detail", "account_id", "zernio": True}.
    The id is prefixed so it can never be confused with an account connected here.
    """
    k = key_override if key_override is not None else key()
    if not k:
        return []
    fresh = key_override is not None
    if not fresh and _cache["key"] == k and (time.time() - _cache["at"]) < CACHE_SECONDS:
        return _cache["rows"]
    got = _call("GET", "/accounts", key_override=key_override, params={"limit": 500})
    rows = got.get("accounts")
    if rows is None:
        rows = got.get("data")
    out = []
    for a in (rows if isinstance(rows, list) else []):
        if not isinstance(a, dict):
            continue
        platform = str(a.get("platform") or "").lower()
        if platform not in PLATFORMS:
            continue
        if str(a.get("status") or "connected") != "connected":
            continue
        aid = str(a.get("_id") or a.get("id") or "")
        if not aid:
            continue
        handle = a.get("username") or a.get("displayName") or a.get("name") or ""
        out.append({
            "id": "zernio:" + aid,
            "platform": platform,
            "label": PLATFORMS[platform],
            "name": str(handle or PLATFORMS[platform])[:120],
            "detail": "through Zernio" + (f" · @{handle}" if handle and handle != PLATFORMS[platform] else ""),
            "account_id": aid,
            "zernio": True,
            "followers": a.get("followers") if isinstance(a.get("followers"), int) else None,
        })
    out.sort(key=lambda a: (a["platform"], a["name"].lower()))
    if not fresh:
        _cache.update(at=time.time(), key=k, rows=out)
    return out


def forget_cache() -> None:
    """Ask for a fresh account list next time, after anything that changes it."""
    _cache.update(at=0.0, key="", rows=[])


def test(key_override: Optional[str] = None) -> dict:
    """Ask Zernio for the accounts, which proves the key works. Says how many there are."""
    # Without a key there is nothing to prove, and accounts() answers [] before it ever asks Zernio, so a success
    # from here would only mean "no key, no error". The key-less sentence is the true answer.
    if not (str(key_override or "").strip() or key()):
        raise ZernioError("Paste a Zernio key in Settings, Connected apps first.")
    try:
        rows = accounts(key_override)
    except ZernioError as e:
        raise ZernioError(str(e))
    return {"ok": True, "accounts": len(rows), "platforms": sorted({a["platform"] for a in rows})}


def upload(path: Path, key_override: Optional[str] = None) -> str:
    """Put one file on Zernio's storage and return the address that can be posted.

    Two steps, because that is how Zernio does it: ask for a presigned address, then PUT the
    bytes to it. The address is signed, so it is the one request that carries no key.
    """
    path = Path(path)
    if not path.is_file():
        raise ZernioError("That file is not there any more. Make the clip again.")
    size = path.stat().st_size
    if size > CAP:
        raise ZernioError("That clip is over 5 GB, which is more than Zernio takes.")
    kind = TYPES.get(path.suffix.lower())
    if not kind:
        raise ZernioError(f"Zernio does not take {path.suffix or 'files without an extension'}. "
                          f"It takes mp4, mov, webm, jpg, png and mp3.")
    got = _call("POST", "/media/presign", key_override=key_override,
                json={"filename": path.name, "contentType": kind, "size": size})
    upload_url = str(got.get("uploadUrl") or "")
    public_url = str(got.get("publicUrl") or "")
    if not upload_url or not public_url:
        raise ZernioError("Zernio did not send back an upload address. Try again.")
    try:
        with path.open("rb") as fh:
            put = httpx.put(upload_url, content=fh, headers={"Content-Type": kind},
                            timeout=TIMEOUT)
    except httpx.HTTPError as e:
        raise ZernioError(f"The upload to Zernio stopped: {type(e).__name__}. Try again.")
    if put.status_code not in (200, 201, 204):
        raise ZernioError(f"Zernio's storage refused the upload ({put.status_code}). Try again.")
    return public_url


PUBLISH_WAIT = 600.0                # publishing now is done inside the request, and a video takes a while


def post(media_url: str, caption: str, targets: list, when: Optional[str] = None,
         timezone_name: str = "UTC", key_override: Optional[str] = None, title: str = "") -> dict:
    """Publish one clip to one or more Zernio accounts, now or at a time.

    targets is a list of our own account ids ("zernio:<id>"); when None is given the post is
    published as soon as Zernio takes it.
    """
    if not str(media_url or "").startswith("http"):
        raise ZernioError("The clip did not reach Zernio's storage, so there is nothing to post. Try again.")
    platforms = []
    for t in targets:
        aid = str(t)
        if not aid.startswith("zernio:"):
            raise ZernioError("That is not a Zernio account.")
        row = {"platform": _platform_of(aid, key_override), "accountId": aid.split(":", 1)[1]}
        if row["platform"] == "youtube" and title:
            # YouTube's video title; without it Zernio uses the caption's first line
            row["platformSpecificData"] = {"title": str(title)[:100], "visibility": "public"}
        platforms.append(row)
    if not platforms:
        raise ZernioError("Pick at least one Zernio account to post to.")
    body = {"content": str(caption or "")[:2000], "platforms": platforms,
            "mediaItems": [{"type": "video", "url": media_url}]}
    if when:
        body["scheduledFor"] = when
        body["timezone"] = timezone_name
    else:
        body["publishNow"] = True
    got = _call("POST", "/posts", key_override=key_override, json=body,
                timeout=TIMEOUT if when else PUBLISH_WAIT)
    out = _read_post(got)
    out["when"] = when or "now"
    if out["status"] in ("failed", "cancelled", "draft") or (out["status"] == "partial" and not out["url"]):
        raise ZernioError(_why_not(out))
    return out


def _read_post(got: dict, post_id: str = "") -> dict:
    """The parts of Zernio's post that matter: its status, the link on the platform, and why it failed."""
    p = got.get("post") if isinstance(got.get("post"), dict) else got
    rows = [r for r in (p.get("platforms") or []) if isinstance(r, dict)]
    url = str(p.get("url") or "") or next((str(r["platformPostUrl"]) for r in rows if r.get("platformPostUrl")), "")
    errs = [str(r.get("errorMessage") or r.get("error") or "") for r in rows if r.get("status") == "failed"]
    out = {"id": str(p.get("_id") or p.get("id") or post_id), "status": str(p.get("status") or ""), "url": url,
           "platforms": {str(r.get("platform") or ""): str(r.get("status") or "") for r in rows},
           "media": len(p.get("mediaItems") or [])}
    err = p.get("error") or next((e for e in errs if e), "")
    if err:
        out["error"] = str(err)[:300]
    return out


def _why_not(st: dict) -> str:
    """One sentence for the page when Zernio did not publish a post."""
    if st.get("error"):
        return "Zernio could not publish it: " + st["error"]
    if st["status"] == "draft":
        return "Zernio kept it as a draft, so it was not published. Try again."
    return f"Zernio says the post {st['status']}. Open Zernio to see why."


def _platform_of(account_id: str, key_override: Optional[str] = None) -> str:
    """Zernio wants the platform with the account id, so look it up once and remember it."""
    rows = accounts(key_override)
    for a in rows:
        if a["id"] == account_id:
            return a["platform"]
    raise ZernioError("That Zernio account is not connected any more. Open Connected apps and look again.")


def status(post_id: str, key_override: Optional[str] = None) -> dict:
    """Where one post got to: scheduled, publishing, published or failed."""
    got = _call("GET", "/posts/" + str(post_id), key_override=key_override)
    return _read_post(got, str(post_id))


def analytics(post_id: str, key_override=None) -> dict:
    """The numbers for one post, when Zernio has them: views, likes, comments.
    The live endpoint is GET /analytics?postId=... (verified against Zernio 2026-11-19);
    it answers 202 while it is still gathering, with the numbers nested under "analytics"."""
    got = _call("GET", "/analytics", key_override=key_override, params={"postId": post_id})
    row = got.get("analytics")
    if not isinstance(row, dict):
        # Older/bare shapes: a flat dict of numbers, or a list of per-platform rows.
        rows = got.get("data") or []
        if isinstance(rows, dict):
            rows = [rows]
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            row = next((r for r in rows if str(r.get("postId") or r.get("_id") or "") == str(post_id)), rows[0])
        else:
            row = got
    out = {}
    for name, keys in (("views", ("views", "totalViews", "viewCount", "impressions")),
                       ("likes", ("likes", "totalLikes", "likeCount")),
                       ("comments", ("comments", "totalComments", "commentCount")),
                       ("shares", ("shares", "shareCount", "reposts"))):
        for k in keys:
            if isinstance(row.get(k), int):
                out[name] = row[k]
                break
    if isinstance(row.get("platformPostUrl"), str) and row["platformPostUrl"]:
        out["url"] = row["platformPostUrl"]
    return out


def stamp() -> str:
    """The time in the shape Zernio reads, in this machine's zone, without a trailing Z."""
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
