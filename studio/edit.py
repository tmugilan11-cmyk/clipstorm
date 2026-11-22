"""Turns a plain-language note about a clip into a small change dict, and puts that change on a copy of the clip."""
from __future__ import annotations

import copy
import math
import re
from typing import List, Optional, Tuple

from . import config

# A note is read by rules, never by an AI: the same sentence always gives the same change, offline and free.
# These numbers mirror jobs.request_render, so a change this module accepts is one the render will also accept.
MIN_LEN, MAX_LEN = 3.0, 180.0        # jobs.py:359 "A clip can be 3 to 180 seconds long."
SNAP_S = 0.9                         # how far a cut may be nudged onto a word or a sentence end
PROMPT_MAX = 2000                    # the edit box carries the same maxlength in the source app
CAPS = {"hook": 60, "title": 100, "description": 2000}      # jobs.py:363
MAX_TAGS = 8                         # brain.py:137 keeps eight hashtags
try:
    MAX_SHIFT = float(config.env("PEAKCUT_EDIT_MAX_SHIFT", "120"))
except (TypeError, ValueError):
    MAX_SHIFT = 120.0                # a bad .env value must not stop the server importing this module
# "Bigger captions" is a style, not a size: render.STYLES has no size knob (100 < 132 < 152 px).
CAPTION_LADDER = ("clean", "bounce", "hype")
CAPTION_WORD_STYLE = "hype"          # two words a line, the closest look to word by word
FALLBACK_STYLES = frozenset(CAPTION_LADDER)
FALLBACK_LAYOUTS = frozenset({"blur", "zoom", "crop", "gameplay"})

# ---------------------------------------------------------------- the words a note is made of
_NUM_WORDS = {"zero": 0.0, "one": 1.0, "two": 2.0, "three": 3.0, "four": 4.0, "five": 5.0, "six": 6.0,
              "seven": 7.0, "eight": 8.0, "nine": 9.0, "ten": 10.0, "eleven": 11.0, "twelve": 12.0,
              "fifteen": 15.0, "twenty": 20.0, "thirty": 30.0, "half": 0.5, "a": 1.0, "an": 1.0}
_NUM = r"(?:\d+(?:\.\d+)?|" + "|".join(sorted(_NUM_WORDS, key=len, reverse=True)) + r")"
_SEC = r"(?:s|secs?|seconds?)"
_CUT = r"(?:cut|trim|take|shave|pull|drop)"
_EARLIER = frozenset({"earlier", "sooner", "before", "back", "shorter"})

# Each rule reads one clause; a rule with no direction word carries its own sign (cutting is always earlier).
_END_RULES = (
    (re.compile(rf"\bend\s+(?:it\s+)?(?:by\s+)?(?P<n>{_NUM})\s*{_SEC}?\s*"
                r"(?P<dir>earlier|sooner|before|back|later|after|longer)\b", re.I), 0),
    (re.compile(rf"\bend\s+(?:it\s+)?(?P<dir>earlier|sooner|later|after)\s+by\s+(?P<n>{_NUM})\s*{_SEC}\b", re.I), 0),
    (re.compile(rf"\b(?P<n>{_NUM})\s*{_SEC}\s+(?P<dir>earlier|sooner|later|after)\s+"
                r"(?:at\s+|on\s+)?the\s+end\b", re.I), 0),
    (re.compile(rf"\b{_CUT}\s+(?P<n>{_NUM})\s*{_SEC}?\s+(?:off|from)\s+(?:the\s+)?end\b", re.I), -1),
    (re.compile(rf"\b(?:make\s+it|end\s+it)\s+(?P<n>{_NUM})\s*{_SEC}?\s+"
                r"(?P<dir>shorter|longer)\b", re.I), 0),
)
_START_RULES = (
    (re.compile(rf"\b(?:start|begin)\s+(?:it\s+)?(?:by\s+)?(?P<n>{_NUM})\s*{_SEC}?\s*"
                r"(?P<dir>earlier|sooner|before|later|after|deeper)\b", re.I), 0),
    (re.compile(rf"\b(?:start|begin)\s+(?:it\s+)?(?P<dir>earlier|sooner|later|after)\s+by\s+"
                rf"(?P<n>{_NUM})\s*{_SEC}\b", re.I), 0),
    (re.compile(rf"\b{_CUT}\s+(?P<n>{_NUM})\s*{_SEC}?\s+(?:off|from)\s+(?:the\s+)?"
                r"(?:start|beginning|top)\b", re.I), 1),
)
# Text fields are taken out of the note before anything else is looked at, so "hook: BIGGER CAPTIONS"
# changes no caption at all.
_HOOK = re.compile(r"\b(?:new\s+)?hook\b\s*(?:to|as|is|=|:)\s*(?P<text>.+)$", re.I)
_TITLE = re.compile(r"\btitle\b\s*(?:to|as|is|=|:)\s*(?P<text>.+)$", re.I)
_DESC = re.compile(r"\bdescription\b\s*(?:to|as|is|=|:)\s*(?P<text>.+)$", re.I)
_TAGS = re.compile(r"\bhashtags?\b\s*(?:to|as|is|=|:)?\s*(?P<text>[^.]*)$", re.I)
_CAP_WORD = re.compile(r"\bword[\s-]*(?:by[\s-]*)?word\b", re.I)
_CAP_BIG = re.compile(r"\b(?:bigger|larger|bolder|huge|massive|big)\b[^.]*\bcaptions?\b|"
                      r"\bcaptions?\b[^.]*\b(?:bigger|larger|bolder)\b", re.I)
_CAP_SMALL = re.compile(r"\b(?:smaller|tinier|subtler|less)\b[^.]*\bcaptions?\b|"
                        r"\bcaptions?\b[^.]*\b(?:smaller|tinier)\b", re.I)
_CAP_OFF = re.compile(r"\b(?:turn off|switch off|no|without|remove|hide|kill|drop)\b[^.]*\bcaptions?\b|"
                      r"\bcaptions?\b\s*(?:off|gone|away)\b", re.I)
_CAP_ON = re.compile(r"\b(?:turn on|switch on|add|bring back|put back)\b[^.]*\bcaptions?\b|"
                     r"\bcaptions?\b\s*(?:on|back)\b", re.I)
_LAYOUT_WORDS = ((re.compile(r"\bfill(?:s|ing)?\s+the\s+(?:screen|frame)\b", re.I), "crop"),
                 (re.compile(r"\bzoomed?\s+in\b", re.I), "zoom"),
                 (re.compile(r"\bcentre\s+crop\b|\bcenter\s+crop\b", re.I), "crop"))


# ---------------------------------------------------------------- what a clip may be set to
def _styles() -> set:
    """The look names the renderer knows. Imported late: a broken render import must not break this module."""
    try:
        from . import render
        return set(render.STYLES)
    except Exception:                                    # noqa: BLE001 - any import trouble means the fallback
        return set(FALLBACK_STYLES)


def _layouts() -> set:
    try:
        from . import render
        return set(render.LAYOUTS)
    except Exception:                                    # noqa: BLE001
        return set(FALLBACK_LAYOUTS)


# ---------------------------------------------------------------- reading the note
def _num(value) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in _NUM_WORDS:
        return _NUM_WORDS[text]
    try:
        out = float(text)
    except ValueError:
        return None
    return out if math.isfinite(out) and out >= 0 else None


def _sign(word) -> int:
    text = str(word or "").strip().lower()
    if not text:
        return 0
    return -1 if text in _EARLIER else 1


def _text(value) -> str:
    """A line from the note: no quotes around it, no run of spaces, no full stop hung on the end."""
    out = re.sub(r"\s+", " ", str(value or "").strip().strip("\"'“”‘’")).strip()
    return out.rstrip(".").strip()


def _tags(value) -> List[str]:
    """Hashtags without the # sign, without punctuation, unique, and never more than the renderer will post."""
    items = value if isinstance(value, (list, tuple)) else re.split(r"[\s,;]+", str(value or ""))
    seen, out = set(), []
    for item in items:
        tag = re.sub(r"\W", "", str(item or ""))
        if tag and tag.lower() not in seen:
            seen.add(tag.lower())
            out.append(tag)
        if len(out) >= MAX_TAGS:
            break
    return out


def _take(rest: str, pattern) -> Tuple[str, str]:
    """Pull a text field out of the note, and hand back the note without that clause."""
    m = pattern.search(rest)
    if not m:
        return "", rest
    return str(m.groupdict().get("text") or "").strip(), (rest[:m.start()] + " " + rest[m.end():]).strip()


def _move(rest: str, rules) -> Optional[dict]:
    """The first clause that moves this end of the clip, as {"by": seconds} (negative is earlier)."""
    for pattern, default in rules:
        m = pattern.search(rest)
        if not m:
            continue
        amount = _num(m.groupdict().get("n"))
        if not amount:
            continue
        sign = _sign(m.groupdict().get("dir")) or default
        if not sign:
            continue
        return {"by": round(max(-MAX_SHIFT, min(MAX_SHIFT, sign * amount)), 3)}
    return None


def parse(text: str) -> dict:
    """Read a note and return only what it asks to change, plus a plain "note" when part of it was not understood.

    Times come back relative to the clip the note is applied to ("end 2 s earlier" is {"end": {"by": -2.0}}),
    because a note is written against what the user sees, not against the source video. Nothing here touches
    a clip, a file or the network, so it is safe to call on a sentence the user is still typing.
    """
    note = str(text or "").strip()
    if not note:
        return {"note": "Write what to change first."}
    out: dict = {}
    if len(note) > PROMPT_MAX:
        note = note[:PROMPT_MAX]
        out["note"] = f"Only the first {PROMPT_MAX} characters were read."
    rest = note
    # 1. The fields that carry text of their own; they are removed so their words cannot be read as commands.
    for key, pattern in (("hook", _HOOK), ("title", _TITLE), ("description", _DESC), ("hashtags", _TAGS)):
        value, rest = _take(rest, pattern)
        if value:
            out[key] = _tags(value) if key == "hashtags" else _text(value)
    low = rest.lower()
    # 2. Times.
    for key, rules in (("end", _END_RULES), ("start", _START_RULES)):
        moved = _move(rest, rules)
        if moved:
            out[key] = moved
    # 3. A look, by name. A name the renderer does not know is dropped rather than swapped for a default:
    # getting a different look than asked for, silently, is worse than being told the name is unknown.
    known = _styles()
    for name in sorted(known, key=len, reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", low):
            out.setdefault("style", name)
            break
    for name in sorted(_layouts(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", low):
            out.setdefault("layout", name)
            break
    if "layout" not in out:
        for pattern, name in _LAYOUT_WORDS:
            if pattern.search(low):
                out["layout"] = name
                break
    # 4. Captions: one size step, or word by word, or on and off.
    if _CAP_WORD.search(low):
        out["style"] = CAPTION_WORD_STYLE
        out["captions"] = True
    elif _CAP_BIG.search(low):
        out["caption_step"] = 1
    elif _CAP_SMALL.search(low):
        out["caption_step"] = -1
    if _CAP_OFF.search(low):
        out["captions"] = False
    elif _CAP_ON.search(low):
        out.setdefault("captions", True)
    # 5. Say what was not understood, instead of pretending the note worked.
    if not out:
        return {"note": "Nothing in that note is something this editor can change."}
    said = note.lower()
    if re.search(r"\bhook\b", said) and "hook" not in out:
        out["note"] = "A new hook needs the words after a colon, like 'new hook: GOT HIM'."
    elif re.search(r"\bstyle\b", low) and "style" not in out:
        out["note"] = "That look is not one PeakCut knows: " + ", ".join(sorted(known, key=len, reverse=True)[:12]) + "."
    elif re.search(r"\b(?:the\s+)?reaction\b", low):
        out["note"] = "Finding the reaction needs the transcript, so that part of the note was not used."
    return out


# ---------------------------------------------------------------- putting the change on a clip
def _seconds(value, default: float) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def _target(change: dict, key: str, current: float) -> Optional[float]:
    """What the note wants this time to be: a number is a time in the video, {"by": s} moves the current one."""
    if key not in change:
        return None
    value = change.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return _seconds(value, current)
    if isinstance(value, dict):
        if "by" in value:
            return current + _seconds(value.get("by"), 0.0)
        for name in ("at", "to", "value"):
            if name in value:
                return _seconds(value.get(name), current)
        return None
    return None


def _words(clip: dict) -> List[dict]:
    """The clip's own transcript, if it still carries one. [] just means the cut cannot be snapped."""
    for key in ("words", "fixed_words"):
        value = clip.get(key)
        if isinstance(value, list) and value and all(isinstance(w, dict) and "s" in w for w in value):
            return value
    return []


def _sentence_ends(words: List[dict]) -> List[float]:
    """Where a sentence finishes: a word ending in . ? !, or else a pause. Same rule as brain.sentence_ends."""
    drawable = max(2, len(words) // 80)
    punctuated = sum(1 for w in words if str(w.get("w") or "")[-1:] in ".?!") >= drawable
    out = []
    for i, w in enumerate(words):
        gap = (_seconds(words[i + 1].get("s"), 9.0) - _seconds(w.get("e"), 0.0)) if i + 1 < len(words) else 9.0
        if (punctuated and str(w.get("w") or "")[-1:] in ".?!") or gap >= (1.0 if punctuated else 0.5):
            out.append(_seconds(w.get("e"), 0.0))
    return out


def _snap(start: float, end: float, words: List[dict]) -> Tuple[float, float]:
    """Nudge a cut onto a word and the end of a sentence, at most SNAP_S away. Never raises, never moves far."""
    if not words:
        return start, end
    ends = [t for t in _sentence_ends(words) if t > start and abs(t - end) <= SNAP_S]
    if ends:
        end = min(ends, key=lambda t: abs(t - end))
    starts = [_seconds(w.get("s"), -99.0) for w in words if abs(_seconds(w.get("s"), -99.0) - start) <= SNAP_S]
    if starts:
        start = min(starts, key=lambda t: abs(t - start))
    return start, end


def _fit(start: float, end: float, clip: dict) -> Tuple[float, float]:
    """Keep the clip inside the video and inside the 3-180 s the renderer allows, by moving the end, never by failing."""
    top = _seconds(clip.get("duration") or clip.get("src_end") or 0, 0.0)
    if top <= 0:
        top = float("inf")
    start = max(0.0, start)
    end = min(end, top)
    if end - start > MAX_LEN:
        end = start + MAX_LEN
    if end - start < MIN_LEN:
        end = start + MIN_LEN
        if end > top:                     # no room after this start: give the clip its length backwards
            end = top
            start = max(0.0, end - MIN_LEN)
    return start, end


def apply(clip: dict, change: dict) -> dict:
    """Return a NEW clip with the change on it; the clip that was passed in is never written to.

    Unknown fields, look names the renderer does not know, and values that do not change anything are left out.
    The result is always a usable clip: a time change that would break the 3-180 s rule is clamped, never raised.
    """
    out = copy.deepcopy(clip) if isinstance(clip, dict) else {}
    if not isinstance(change, dict) or not change:
        return out
    # Times first: a later caption step or hook does not depend on them, but the clamp needs the new span.
    start, end = _seconds(out.get("start"), 0.0), _seconds(out.get("end"), 0.0)
    want_start, want_end = _target(change, "start", start), _target(change, "end", end)
    if want_start is not None or want_end is not None:
        new_start = start if want_start is None else want_start
        new_end = end if want_end is None else want_end
        new_start, new_end = _fit(new_start, new_end, out)
        new_start, new_end = _snap(new_start, new_end, _words(out))
        new_start, new_end = _fit(new_start, new_end, out)
        if abs(new_start - start) > 1e-6:
            out["start"] = round(new_start, 2)
        if abs(new_end - end) > 1e-6:
            out["end"] = round(new_end, 2)
    # Text fields, capped exactly as jobs.request_render caps them.
    for key in ("hook", "title", "description"):
        if key in change:
            value = str(change.get(key) or "").strip()[:CAPS[key]]
            if value != str(out.get(key) or ""):
                out[key] = value
    if "hashtags" in change:
        value = _tags(change.get("hashtags"))
        if value != list(out.get("hashtags") or []):
            out["hashtags"] = value
    # A known look, by name. An unknown one is dropped, never replaced with a default.
    style = str(change.get("style") or "").strip().lower()
    if style and style in _styles() and style != out.get("style"):
        out["style"] = style
    layout = str(change.get("layout") or "").strip().lower()
    if layout and layout in _layouts() and layout != out.get("layout"):
        out["layout"] = layout
    # "Bigger captions" is one step up the size ladder, from whatever look the clip has now.
    step = change.get("caption_step")
    if isinstance(step, int) and not isinstance(step, bool) and step:
        ladder = [n for n in CAPTION_LADDER if n in _styles()] or sorted(_styles())
        current = str(out.get("style") or "")
        index = ladder.index(current) if current in ladder else min(1, len(ladder) - 1)
        index = max(0, min(len(ladder) - 1, index + (1 if step > 0 else -1)))
        if ladder and ladder[index] != current:
            out["style"] = ladder[index]
    if isinstance(change.get("captions"), bool) and change["captions"] != out.get("captions"):
        out["captions"] = change["captions"]
    return out
