"""Who allows their streams to be clipped: the table that ships with PeakCut (clip_rules.json, one entry per
"platform:handle"), the entries an account adds over it, and the single state - "no" - that stops work until the
person confirms they have permission.

    allowed | ask | no | unknown   - 'no' is the only one that blocks.
"""
from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Dict, Optional, Tuple, Union
from urllib.parse import urlparse

from . import config, ctx

RULE_VALUES: Tuple[str, ...] = ("allowed", "ask", "no", "unknown")
PLATFORMS: Tuple[str, ...] = ("youtube", "twitch", "kick")
MAX_NOTE, MAX_SOURCE = 400, 500          # PeakCut caps what a person can type; the shipped notes are shorter
MAX_ENTRIES = 500                        # per call and per account's own file
KEY_RE = re.compile(r"(youtube|twitch|kick):(@?[\w.\-]{1,60})")
SEGMENT_RE = re.compile(r"@?[\w.\-]{1,60}")
# Twitch paths that look like a channel but are not one. The source only guarded /videos/; the rest are the same idea.
NOT_A_CHANNEL = ("videos", "directory", "search", "clip", "clips", "collections", "settings", "subscriptions")
# said on every page that shows the rules, so the wording lives in one place
LABELS = {"allowed": "Clipping allowed", "ask": "Has clip tips", "no": "No clipping", "unknown": "Rules unknown"}
TONES = {"allowed": "ok", "ask": "warn", "no": "bad", "unknown": ""}
UNKNOWN_TIP = "We found no public clipping rule. Check their channel rules before you post."

_lock = threading.RLock()
_ship: Dict[str, object] = {"at": None, "data": {}}     # the shipped table, read again only when it changes
_mine: Dict[str, Dict[str, object]] = {}                # user id -> their own overrides, same rule


def _shipped_file() -> Path:
    """The table next to this module. Shipped with the app and replaced whole on an update."""
    return Path(__file__).resolve().with_name("clip_rules.json")


def _cached(slot: dict, path: Path) -> dict:
    """Read a JSON object again only when its file changed. A missing, unreadable or broken file is {} - never an error,
    and a file holding null/[]/3 cannot take the server down either."""
    try:
        at = path.stat().st_mtime_ns
    except OSError:
        at = 0
    with _lock:
        if slot.get("at") != at:
            data = {}
            if at:
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    data = {}
            slot.update(at=at, data=data if isinstance(data, dict) else {})
        got = slot.get("data")
    return got if isinstance(got, dict) else {}


def _shipped() -> dict:
    return _cached(_ship, _shipped_file())


def _local_file() -> Optional[Path]:
    """This account's overrides, users/<user>/clip_rules.json - the same place creators keep their work. None when a
    background thread has no user; those see the shipped table only."""
    uid = ctx.uid_or_none()
    if not uid:
        return None
    try:
        return config.user_dir(uid) / "clip_rules.json"
    except (ValueError, OSError):
        return None


def _local() -> dict:
    path = _local_file()
    if path is None:
        return {}
    uid = path.parent.name
    with _lock:
        if len(_mine) > 128:                    # many accounts on one server: keep the list short
            _mine.clear()
        slot = _mine.setdefault(uid, {"at": None, "data": {}})
    return _cached(slot, path)


def _text(value, cap: int) -> str:
    """A stored string, cut to `cap`. Anything that is not text becomes its plain form, or empty."""
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return value[:cap]


def _row(raw) -> dict:
    """One reading of a row, normalised the way the source did it: the rule is one of three words or 'unknown', and
    anything else - 'yes', null, a number - collapses to 'unknown'. That whitelist is the only validation."""
    if not isinstance(raw, dict):
        raw = {}
    rule = raw.get("rule")
    return {"rule": rule if rule in ("allowed", "ask", "no") else "unknown",
            "note": _text(raw.get("note"), MAX_NOTE), "source": _text(raw.get("source"), MAX_SOURCE)}


def load() -> dict:
    """The merged, normalised {key: {"rule", "note", "source"}}: the shipped table with this account's file over it,
    row by row. Never raises - a broken table simply reads as everything unknown."""
    try:
        out = dict(_shipped())
        out.update(_local())
        return {key: _row(raw) for key, raw in out.items() if isinstance(key, str)}
    except Exception:
        return {}


def table() -> dict:
    """Same as load(); the name the spec used for the merged table."""
    return load()


def _platform(value) -> str:
    """A platform from whatever was handed in: 'Twitch', 'twitch.tv', 'https://www.youtube.com/...', 'yt'. '' if none."""
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = re.sub(r"^[a-z][a-z0-9+.\-]*://", "", text)
    text = text.split("/")[0].split("?")[0].split("#")[0].strip(".")
    if text.startswith("www."):
        text = text[4:]
    if text in PLATFORMS:
        return text
    for part in [text] + text.split(".") + text.split(":"):
        if part in PLATFORMS:
            return part
    return {"yt": "youtube", "twitchtv": "twitch"}.get(text.replace(".", ""), "")


def _handle(value) -> str:
    """A handle from whatever was handed in: trimmed, lowercased, YouTube's '@' kept. A whole link is accepted and
    mined for its handle. '' when nothing usable is left."""
    text = str(value or "").strip()
    if not text:
        return ""
    if "://" in text or "/" in text or " " in text:
        found = handle_of(text)
        if found:
            return found[1]
        text = text.rsplit("/", 1)[-1]
    text = text.strip().strip("/").lstrip(":")[:61].lower()
    return text if SEGMENT_RE.fullmatch(text) else ""


def _keys(platform, handle) -> list:
    """The table keys to try, most exact first. A missing platform looks in all three, because a caller may only know
    the handle; YouTube is also found without its '@'."""
    handle = _handle(handle)
    if not handle:
        return []
    platform = _platform(platform)
    out = []

    def add(key):
        if key not in out:
            out.append(key)

    if platform:
        add(f"{platform}:{handle}")
        if platform == "youtube":                   # YouTube keys carry the '@'; a handle typed without one still finds it
            add(f"youtube:@{handle.lstrip('@')}")
            add(f"youtube:{handle.lstrip('@')}")
    else:
        for plat in PLATFORMS:
            add(f"{plat}:{handle}")
            if plat == "youtube":
                add(f"youtube:@{handle.lstrip('@')}")
                add(f"youtube:{handle.lstrip('@')}")
    return out


def lookup(platform: str, handle: str) -> dict:
    """{"rule", "note", "source"} for one streamer, case-insensitive and tolerant of a platform written as a site name
    ('twitch.tv') or of the handle arriving inside a link. Never raises: no row means the 'unknown' triple."""
    try:
        merged = load()
        for key in _keys(platform, handle):
            if key in merged:
                return dict(merged[key])
    except Exception:
        pass
    return _row(None)


def rule(platform: str, handle: str) -> dict:
    """Same as lookup(); the name the spec used for the resolver."""
    return lookup(platform, handle)


def badge(info: Union[dict, str], handle: Optional[str] = None) -> dict:
    """What the page draws: the lookup triple plus label, tone (one of '', 'ok', 'warn', 'bad'), can_clip and blocked.
    Call it as badge(lookup(platform, handle)) or badge(platform, handle). Only 'no' is ever not clipable."""
    try:
        row = lookup(info, handle) if handle is not None or not isinstance(info, dict) else _row(info)
        name = row["rule"]
        return dict(row, label=LABELS.get(name, LABELS["unknown"]), tone=TONES.get(name, ""),
                    can_clip=name != "no", blocked=name == "no")
    except Exception:
        return dict(_row(None), label=LABELS["unknown"], tone="", can_clip=True, blocked=False)


def block(platform: str, handle: str, permission: bool = False) -> Optional[str]:
    """The sentence to show instead of starting work, or None. Only 'no' without permission returns text; 'ask' and
    'unknown' are advice, never a stop."""
    try:
        row = lookup(platform, handle)
        if row["rule"] != "no" or permission:
            return None
        who = _handle(handle) or str(handle or "").strip()
        why = row["note"] or "public statement"
        return (f"{who} does not allow clipping ({why})" +
                (f". {row['source']}" if row["source"] else "") +
                ". Only go on if you have their permission.")
    except Exception:
        return None


def handle_of(url: str) -> Optional[Tuple[str, str]]:
    """(platform, handle) for a channel or live link, else None. Platform is 'youtube'|'twitch'|'kick'; the handle is
    lowercased and keeps YouTube's leading '@'. A VOD id, a directory page or a bare link yields None."""
    try:
        from . import creators                  # here, not at the top, so rules -> creators stays one-way
        text = str(url or "").strip()
        if not text:
            return None
        target = text if "://" in text else "https://" + text
        platform = creators.platform_key(target)
        if not platform:
            return None
        path = urlparse(target).path.strip("/")
        if platform == "youtube":
            found = re.match(r"(@[\w.\-]+)", path)      # the @handle form only: /channel/UC... and /c/name are not it
            return ("youtube", found.group(1).lower()) if found else None
        if ":" in path.split("/")[0]:                   # a bare "kick:handle" string
            path = path.split(":", 1)[1]
        segment = path.split("/")[0]
        if not segment:
            return None
        if platform == "twitch" and segment.lower() in NOT_A_CHANNEL:
            return None
        return (platform, segment.lower()) if SEGMENT_RE.fullmatch(segment) else None
    except Exception:
        return None


def public() -> dict:
    """For the settings page: the merged table and the values it can hold, with a count per state. No paths, no
    owner id, nothing that names the account."""
    merged = load()
    counts = {value: 0 for value in RULE_VALUES}
    for row in merged.values():
        counts[row["rule"]] = counts.get(row["rule"], 0) + 1
    return {"rules": merged, "values": list(RULE_VALUES), "platforms": list(PLATFORMS),
            "counts": counts, "editable": True}


def _entry(key, raw) -> Tuple[str, dict]:
    """One entry checked the way the settings route needs it. Raises ValueError with a sentence a person can act on;
    the route turns that into a 400."""
    text = str(key or "").strip()
    if not text or len(text) > 87 or not KEY_RE.fullmatch(text):
        raise ValueError(f"'{key}' is not a streamer key. Use platform:handle, for example twitch:xqc.")
    if text != text.lower():
        raise ValueError(f"'{key}' must be lowercase, for example {text.lower()}.")
    if not isinstance(raw, dict):
        raise ValueError(f"Send the rule for {text} as an object with rule, note and source.")
    value = str(raw.get("rule") or "").strip().lower()
    if value not in RULE_VALUES:
        raise ValueError(f"'{raw.get('rule')}' is not a rule. Use one of: {', '.join(RULE_VALUES)}.")
    note = raw.get("note", "")
    if note is None:
        note = ""
    if not isinstance(note, str):
        raise ValueError(f"The note for {text} must be text.")
    source = raw.get("source", "")
    if source is None:
        source = ""
    if not isinstance(source, str):
        raise ValueError(f"The source for {text} must be a link.")
    source = source.strip()
    if source and not re.match(r"https?://\S+$", source):
        raise ValueError(f"The source for {text} must start with http:// or https://")
    if len(source) > MAX_SOURCE:
        raise ValueError(f"The source link for {text} is too long.")
    return text, {"rule": value, "note": note.strip()[:MAX_NOTE], "source": source}


def _write_local(data: dict) -> None:
    """Write this account's file whole, through a temporary file, so a torn write cannot lose it."""
    path = _local_file()
    if path is None:
        raise ValueError("Sign in first: rules are saved per account.")
    with _lock:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
            tmp.replace(path)
        except OSError as e:
            raise ValueError(f"The rules could not be saved: {e}")
        uid = path.parent.name
        if uid in _mine:
            _mine[uid]["at"] = None
    ctx.bump()


def save_local(entries: dict) -> dict:
    """Merge {key: {"rule", "note", "source"}} into this account's clip_rules.json and return public(). A key, a rule
    or a link that cannot be used raises ValueError; nothing is written in that case."""
    if not isinstance(entries, dict) or not entries:
        raise ValueError("Send the rules as an object, one per streamer.")
    if len(entries) > MAX_ENTRIES:
        raise ValueError(f"That is more than {MAX_ENTRIES} streamers at once.")
    checked = dict(_entry(key, raw) for key, raw in entries.items())
    merged = dict(_local())
    merged.update(checked)
    if len(merged) > MAX_ENTRIES:
        raise ValueError(f"An account can keep rules for {MAX_ENTRIES} streamers.")
    _write_local(merged)
    return public()


def forget_local(key: str) -> dict:
    """Drop one key from this account's file, so the shipped row (if any) is what the lookup finds again."""
    text = str(key or "").strip().lower()
    if not text or len(text) > 87 or not KEY_RE.fullmatch(text):
        raise ValueError(f"'{key}' is not a streamer key.")
    mine = dict(_local())
    if text in mine:
        del mine[text]
        _write_local(mine)
    return public()
