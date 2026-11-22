"""The part that reads the numbers and improves the settings, with a way back.

The idea, in one line: a person presses one button, PeakCut looks at what their channel actually
did, asks the AI which of a small set of settings should change, applies at most one round of
changes, records what changed and why, and can undo it.

Three rules make that safe, and they are the whole design:

1. **Only settings on a list can change.** The AI is asked for changes to a fixed set of words
   (`STYLE`, `HOOK`, `LENGTH`, `MOOD`, `COUNTER` below). A word the list does not hold is dropped.
   An AI cannot invent a setting into this file.
2. **Every change is a version with its before and after.** `state.json` holds the current round and
   the ones before it, so undo is a copy, not a guess.
3. **Nothing is claimed without a number.** A round records the measurements it started from and
   says straight out that the effect is not known yet. It cannot claim an improvement it has not
   seen; a later round is what compares.

It deliberately does not import `server.py`. `studio/api_learn.py` is the doorway.

    studio/learn.py      this file: the facts, the prompt, the applying, the version log
    studio/api_learn.py  POST /api/learn/run, GET /api/learn/state, POST /api/learn/undo
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from . import ai, brand, config, ctx

# ---------------------------------------------------------------- what may change
# Each entry: the setting's name as the AI sees it, where it lands, and the values it may take.
STYLE = ("style", "The caption look. One of the looks PeakCut can draw.")
HOOK = ("hook_words", "How the few words at the top of a clip should be written.")
LENGTH = ("clip_len", "How long a clip may be, in seconds.")
MOOD = ("sound", "A sound added under a clip.")
COUNTER = ("captions_always", "Whether captions are burned in on every clip.")

KINDS = {STYLE[0]: "text", HOOK[0]: "text", LENGTH[0]: "number", MOOD[0]: "text", COUNTER[0]: "bool"}

# The setting name as the AI sees it, and the key it is stored under in the brand document. They differ
# for the one setting whose sensible word is not the document's own key, so undo reads this and never
# has to guess where a value came from.
_BRAND_KEY = {STYLE[0]: "style", HOOK[0]: "hook_words", LENGTH[0]: "clip_len",
              MOOD[0]: "sound", COUNTER[0]: "captions"}

MIN_ROUND_SECONDS = 60 * 60 * 6        # one round per six hours: a change needs time to show anything
MAX_ROUNDS = 20                        # keep the last 20 rounds in the log, then drop the oldest
MIN_SAMPLE_VIEWS = 50                  # below this, the numbers are noise and the advice says so

_WHAT_CANNOT_BE_DONE = (
    "You cannot change anything else. You cannot change how PeakCut transcribes, how it uploads, "
    "the AI key, the accounts, or any file on the machine."
)


def _file(user_id: str) -> Path:
    """Where this person's rounds live: one small file next to their other settings."""
    return config.user_dir(user_id) / "learn.json"


def _read(user_id: str) -> dict:
    """The saved rounds, or an empty log when there is none or the file is not readable.

    A hand-edited or broken file must never stop the page: it reads as "nothing has been done yet"."""
    try:
        got = json.loads(_file(user_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"rounds": [], "current": None}
    if not isinstance(got, dict):
        return {"rounds": [], "current": None}
    rounds = [r for r in (got.get("rounds") or []) if isinstance(r, dict)]
    return {"rounds": rounds[-MAX_ROUNDS:], "current": got.get("current") if isinstance(got.get("current"), dict) else None}


def _write(user_id: str, data: dict) -> None:
    """Save the log in one move, so a crash cannot leave half a round behind."""
    f = _file(user_id)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(f)


def log() -> dict:
    """Every round for the person asking, newest first, plus what the settings are now."""
    uid = ctx.uid()
    data = _read(uid)
    # What PeakCut already knows about this person's own clips, so the page has something true to show
    # before the first round has ever run.
    try:
        said = content()
    except Exception as e:  # noqa: BLE001  - a content read must never stop the page drawing
        said = {"clips": 0, "lines": ["PeakCut could not read its own clips: " + str(e)[:160]]}
    return {"rounds": list(reversed(data["rounds"])), "current": data["current"],
            "can_run": _may_run(data), "why_not": _why_not(data),
            "content": {"clips": said.get("clips", 0), "lines": said.get("lines") or [],
                        "per_style": said.get("per_style") or {}, "per_len": said.get("per_len") or {}}}


def _may_run(data: dict) -> bool:
    """Whether a new round may start now. Time is the only moving part, so this is re-read each time."""
    if not ai.ready():
        return False
    last = data["rounds"][-1] if data["rounds"] else None
    if not last:
        return True
    return (time.time() - float(last.get("at") or 0)) >= MIN_ROUND_SECONDS


def _why_not(data: dict) -> str:
    """The reason a round cannot start, in a sentence a person can act on."""
    if not ai.ready():
        return ("The AI is not set up, so PeakCut cannot read the numbers for you yet. Add a key under "
                "Settings, AI.")
    last = data["rounds"][-1] if data["rounds"] else None
    if last:
        wait = MIN_ROUND_SECONDS - (time.time() - float(last.get("at") or 0))
        if wait > 0:
            when = _ago(time.time() - float(last.get("at") or 0))
            return ("Your settings were changed " + when + ". A change needs time to show anything, "
                    f"so the next round can start in {_wait_text(wait)}.")
    return ""


def _wait_text(seconds: float) -> str:
    """A stretch of time the way a person says it, "2 h 14 min", rounded up so it never promises a moment
    that is still refused, and never says "0 h 0 min" for a wait that is under two minutes."""
    mins = int(max(0.0, float(seconds) + 59) // 60)
    hours, mins = divmod(mins, 60)
    if hours and mins:
        return f"{hours} h {mins} min"
    if hours:
        return f"{hours} h"
    return f"{mins} min" if mins else "less than a minute"


def _ago(seconds: float) -> str:
    """A stretch of time the way a person says it: "just now", "12 minutes ago", "3 h 5 min ago"."""
    seconds = max(0.0, float(seconds))
    if seconds < 90:
        return "just now"
    mins = int(seconds // 60)
    if mins < 60:
        return f"{mins} minutes ago"
    hours, mins = divmod(mins, 60)
    if hours < 24:
        return f"{hours} h {mins} min ago" if mins else f"{hours} h ago"
    days, hours = divmod(hours, 24)
    return f"{days} days ago" if not hours else f"{days} days {hours} h ago"


# ---------------------------------------------------------------- the facts
def facts(days: int = 28) -> dict:
    """What the numbers say, as plain sentences with the figure that made them.

    This is deliberately not "the AI decides what matters". The sentences here are fixed, so the same
    numbers always read the same way, and a person can check one against the Analytics page."""
    from . import api_analytics

    start_end = api_analytics._window(days)
    token = ""
    try:
        from . import accounts
        token = accounts.youtube_token() or ""
    except Exception:  # noqa: BLE001
        token = ""

    got = {"source": "peakcut", "days": days, "start": start_end[0], "end": start_end[1],
           "lines": [], "sample": 0, "enough": False}

    if not token:
        got["lines"] = [
            "No YouTube channel is connected, so PeakCut has no views, watch time or retention to read.",
            "What PeakCut does know is in the pipeline card: clips made, posts sent, and the queue.",
        ]
        got["content"] = _content_lines(days)
        got["lines"] = got["lines"] + got["content"]
        return got

    try:
        rows = api_analytics._ask(token, start_end[0], start_end[1],
                                  "views,estimatedMinutesWatched,averageViewDuration,"
                                  "averageViewPercentage,subscribersGained,subscribersLost")
    except Exception as e:  # noqa: BLE001
        got["lines"] = ["YouTube would not answer: " + str(e)[:200]]
        return got

    r = rows[0] if rows else {}
    views = api_analytics._num(r.get("views"))
    minutes = api_analytics._num(r.get("estimatedMinutesWatched"))
    avg = api_analytics._num(r.get("averageViewDuration"))
    pct = api_analytics._num(r.get("averageViewPercentage"))
    subs = api_analytics._num(r.get("subscribersGained")) - api_analytics._num(r.get("subscribersLost"))

    got["sample"] = int(views)
    got["enough"] = views >= MIN_SAMPLE_VIEWS
    got["source"] = "youtube"

    got["lines"] = [
        f"{int(views)} views in the last {days} days, which is {round(minutes / 60, 1)} hours watched.",
        f"People watched {int(avg)} seconds on average, which is {round(pct, 1)} percent of a video.",
        f"{int(subs)} subscribers gained, after losses.",
    ]
    if avg > 0 and pct > 0:
        got["lines"].append(
            f"A video of {int(round(avg / max(pct, 1) * 100))} seconds is what those two numbers describe.")
    # The clips are evidence too, and a channel with too few views may still have a hundred clips whose own
    # numbers point at a look. Both are handed to the AI; neither is invented.
    got["content"] = _content_lines(days)
    got["lines"] = got["lines"] + got["content"]
    # Where people stop watching is the strongest hint about length and hooks, so it is read here rather
    # than left to the AI to guess. A person with no posted clip has no curve to read, and that is silent.
    got["lines"] = got["lines"] + _retention_lines(_posted_video(), days, int(avg))
    if not got["enough"]:
        # Kept last on purpose: it is the answer, and a reader should not have to hunt for it.
        got["lines"].append(
            f"Only {int(views)} views so far. PeakCut needs at least {MIN_SAMPLE_VIEWS} before a change "
            f"means anything, so nothing will be changed this time.")
    return got


def _content_lines(days: int) -> list:
    """The clip-level sentences from `content()`, kept separate so both branches of `facts` share them."""
    try:
        got = content(days)
    except Exception as e:  # noqa: BLE001  - a content read must never stop the channel facts
        return ["PeakCut could not read its own clips: " + str(e)[:160]]
    return list(got.get("lines") or [])


def _posted_video() -> str:
    """The YouTube id of the newest clip this person posted, or "" when there is none.

    The retention curve belongs to one video, so PeakCut reads the most recent clip that actually reached
    YouTube. Every step is guarded and a missing record is a missing curve, not a failed round: a person
    with no posts yet simply gets no retention sentence."""
    try:
        from . import accounts, posting
        youtube = {a.get("id") for a in accounts._all() if a.get("platform") == "youtube"}
        if not youtube:
            return ""
        posts = [p for p in posting._mine()
                 if p.get("remote_id") and p.get("account") in youtube]
        if not posts:
            return ""
        posts.sort(key=lambda p: float(p.get("posted_at") or p.get("due_at") or 0), reverse=True)
        return str(posts[0].get("remote_id") or "")[:200]
    except Exception:  # noqa: BLE001  - no post record is no curve, and never a stopped round
        return ""


def _retention_lines(video_id: str, days: int, seconds: int) -> list:
    """The retention sentences for one video, or one sentence saying why they are missing.

    A module that is not installed is skipped without a word: the Improve page must not look broken
    because one optional reader has not shipped yet. Any other failure is said out loud, with the
    reason, because a sentence about where people stop watching is evidence and silence would look
    like good news."""
    if not video_id:
        return []
    try:
        from . import learn_signals
    except ImportError:
        return []
    try:
        return list(learn_signals.lines(video_id, days, seconds) or [])
    except Exception as e:  # noqa: BLE001  - see the docstring: name the failure, do not stop the round
        return ["The retention curve could not be read: " + str(e)[:160]]


# ---------------------------------------------------------------- what the clips themselves say
def content(days: int = 3650, limit: int = 60) -> dict:
    """What PeakCut's own clips look like, and how the ones that were posted did.

    The channel totals say whether the audience grew. This says which of this person's own clips the
    audience actually watched, and what those clips had in common: their look, their length, their
    hook. That pairing is the only evidence here that can point at a SETTING rather than at a number.

    It reads PeakCut's own records, so it works with no YouTube connection at all."""
    from . import jobs

    uid = ctx.uid()
    cutoff = time.time() - days * 86400
    got = {"clips": 0, "posted": 0, "lines": [], "per_style": {}, "per_len": {}, "with_views": 0}
    by_style, by_len = {}, {}
    rows = []
    for job in jobs.list_jobs():
        if float(job.get("created") or 0) < cutoff:
            continue
        for c in job.get("clips") or []:
            if c.get("status") != "done":
                continue
            got["clips"] += 1
            length = max(0.0, float(c.get("end") or 0) - float(c.get("start") or 0))
            style = str(c.get("style") or job.get("options", {}).get("style") or "") or "unknown"
            views = c.get("views")
            rows.append({"style": style, "length": length, "views": views,
                         "hook": str(c.get("hook") or "")[:60],
                         "title": str(c.get("title") or "")[:60],
                         "mood": str(c.get("mood") or "")})
            seen = by_style.setdefault(style, {"n": 0, "views": 0, "seen": 0})
            seen["n"] += 1
            if isinstance(views, (int, float)) and views:
                seen["views"] += float(views)
                seen["seen"] += 1
                got["with_views"] += 1
            bucket = _length_bucket(length)
            seen2 = by_len.setdefault(bucket, {"n": 0, "views": 0, "seen": 0})
            seen2["n"] += 1
            if isinstance(views, (int, float)) and views:
                seen2["views"] += float(views)
                seen2["seen"] += 1

    got["per_style"] = {k: _average(v) for k, v in by_style.items()}
    got["per_len"] = {k: _average(v) for k, v in by_len.items()}
    got["posted"] = sum(1 for r in rows if isinstance(r["views"], (int, float)) and r["views"])

    if not got["clips"]:
        got["lines"] = ["No clips have been made yet, so there is no content to compare."]
        return got

    got["lines"].append(f"{got['clips']} clips have been made, and {got['posted']} of them have a view count.")
    best_style = _best(got["per_style"])
    if best_style:
        name, avg, n = best_style
        got["lines"].append(
            f"The look that did best is {name}, at {_tidy(avg)} views a clip over {n} clip"
            f"{'' if n == 1 else 's'} with a number.")
    best_len = _best(got["per_len"])
    if best_len:
        name, avg, n = best_len
        got["lines"].append(
            f"Clips of {name} seconds did best, at {_tidy(avg)} views a clip over {n} clip"
            f"{'' if n == 1 else 's'} with a number.")
    hooks = [r["hook"] for r in rows if r["hook"]]
    if hooks:
        got["lines"].append("Hooks used so far: " + "; ".join(_dedupe(hooks)[:6]) + ".")
    moods = [r["mood"] for r in rows if r["mood"]]
    if moods:
        counted = {}
        for m in moods:
            counted[m] = counted.get(m, 0) + 1
        top = sorted(counted.items(), key=lambda kv: -kv[1])[:3]
        got["lines"].append("Sounds used: " + ", ".join(f"{k} on {v}" for k, v in top) + ".")
    if got["with_views"] == 0:
        got["lines"].append(
            "None of the clips carry a view count yet, so nothing above says which look or length works.")
    return got


def _length_bucket(seconds: float) -> int:
    """A clip length rounded to the nearest 5 seconds, so lengths can be compared in groups."""
    if seconds <= 0:
        return 0
    return max(5, int(round(seconds / 5.0)) * 5)


def _average(seen: dict) -> dict:
    """The mean views of the clips that have a number, plus how many that is."""
    if not seen["seen"]:
        return {"n": seen["n"], "avg": None, "seen": 0}
    return {"n": seen["n"], "avg": seen["views"] / seen["seen"], "seen": seen["seen"]}


def _best(per: dict):
    """The group with the highest mean views, ignoring groups too small to mean anything."""
    usable = [(k, v["avg"], v["seen"]) for k, v in per.items()
              if v.get("avg") is not None and v.get("seen", 0) >= 2]
    if not usable:
        return None
    return max(usable, key=lambda t: t[1])


def _dedupe(items: list) -> list:
    """The items in order, each kept once."""
    out, seen = [], set()
    for x in items:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


# ---------------------------------------------------------------- did it work
_MEASURED = ("views", "hours", "seconds", "percent", "subscribers")


def measure(days: int = 28) -> dict:
    """One small reading of the numbers, kept on a round so a later round can compare against it.

    It is the same report `facts()` reads, reduced to five numbers, so a comparison is arithmetic and
    not a second opinion. Without a channel it returns an empty dict, and the page says so rather than
    printing zeros."""
    from . import api_analytics

    try:
        from . import accounts
        token = accounts.youtube_token() or ""
    except Exception:  # noqa: BLE001
        token = ""
    if not token:
        return {}
    start, end = api_analytics._window(days)
    try:
        rows = api_analytics._ask(token, start, end,
                                  "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage")
    except Exception:  # noqa: BLE001
        return {}
    r = rows[0] if rows else {}
    minutes = api_analytics._num(r.get("estimatedMinutesWatched"))
    return {"days": days, "at": time.time(),
            "views": int(api_analytics._num(r.get("views"))),
            "hours": round(minutes / 60.0, 1),
            "seconds": int(api_analytics._num(r.get("averageViewDuration"))),
            "percent": round(api_analytics._num(r.get("averageViewPercentage")), 1)}


def compare(before: dict, after: dict) -> list:
    """What moved between two readings, in plain sentences. A move inside the noise is said to be noise.

    Nothing here claims cause. It reports the difference and, when the sample is too small, says that
    the difference is too small to read."""
    out = []
    if not before or not after:
        return out
    names = {"views": ("views", "a view"), "hours": ("hours watched", "an hour"),
             "seconds": ("seconds watched on average", "a second"),
             "percent": ("percent of a video watched", "a point")}
    for key, (label, one) in names.items():
        was, now = before.get(key), after.get(key)
        if was is None or now is None:
            continue
        was, now = float(was), float(now)
        if was == 0 and now == 0:
            continue
        if was == 0:
            out.append(f"{label.capitalize()} went from nothing to {_tidy(now)}.")
            continue
        move = (now - was) / was * 100.0
        word = "up" if move > 0 else "down"
        out.append(f"{label.capitalize()} {word} {abs(move):.0f} percent, from {_tidy(was)} to {_tidy(now)}.")
    views = min(float(before.get("views") or 0), float(after.get("views") or 0))
    if out and views < MIN_SAMPLE_VIEWS:
        out.append(f"Both readings are under {MIN_SAMPLE_VIEWS} views, so that move is too small to read.")
    return out


def _tidy(v: float) -> str:
    """A number for a sentence: no trailing .0 on a whole one."""
    return str(int(round(v))) if abs(v - round(v)) < 0.05 else f"{v:.1f}"


# ---------------------------------------------------------------- the prompt
_PROMPT = """You are improving a short-video clipping tool called PeakCut, for one person's channel.

Here is what their channel actually did:
{facts}

Here are the settings you may change:
{settings}

Give at most two changes. For each, answer with:
- "setting": exactly one of the setting names above
- "value": the new value
- "why": one sentence, quoting the number from above that made you choose it
- "expect": what should improve, and which of the numbers above it should move

Rules you must follow:
{limits}

If the numbers do not support any change, answer with an empty list of changes and one sentence
saying what is missing. A wrong change costs this person real audience. Saying "not yet" is a good
answer.
"""


def _settings_text() -> str:
    """The list the AI is given, written from the same constants the applying code checks against."""
    lines = []
    for name, what in (STYLE, HOOK, LENGTH, MOOD, COUNTER):
        lines.append(f"- {name}: {what}")
    return "\n".join(lines)


_SCHEMA = {
    "type": "object",
    "properties": {
        "changes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "setting": {"type": "string"},
                    "value": {"type": "string"},
                    "why": {"type": "string"},
                    "expect": {"type": "string"},
                },
                "required": ["setting", "value", "why"],
            },
        },
        "saying": {"type": "string"},
    },
    "required": ["changes"],
}


def _allowed(name: str, value) -> bool:
    """Whether a proposed change is one PeakCut will accept, checked here and not taken on trust."""
    if name not in KINDS:
        return False
    kind = KINDS[name]
    if kind == "bool":
        return str(value).lower() in ("true", "false", "1", "0", "yes", "no")
    if kind == "number":
        try:
            n = float(value)
        except (TypeError, ValueError):
            return False
        return 5.0 <= n <= 600.0
    if name == STYLE[0]:
        from . import captions, render
        return str(value) in set(render.STYLES) | set(captions.style_names())
    if name == MOOD[0]:
        from . import meme, music
        return str(value) in set(meme.load_moods()) | set(music.MOODS) or str(value) == ""
    return 0 < len(str(value)) <= 120


def run(days: int = 28, dry: bool = False) -> dict:
    """One round: read the numbers, ask the AI, apply what is allowed, record it, hand back the report.

    `dry` answers what it would do without changing anything, which is what the button shows first."""
    uid = ctx.uid()
    data = _read(uid)
    # A preview changes nothing, so the wait between rounds does not apply to it. Asking "what would
    # you change?" and being told to come back in five hours is a refusal of a question that costs
    # nothing to answer, and it made the button look broken on a fresh install.
    if not dry and not _may_run(data):
        raise ValueError(_why_not(data) or "PeakCut cannot run a round just now.")

    got = facts(days)
    # The reading this round starts from. Kept on the round so the NEXT round can compare, which is the
    # only honest way to say whether a change did anything.
    reading = measure(days)
    if not got["enough"]:
        # Not a failure: it is the honest answer. Nothing is asked of the AI, and nothing changes.
        out = {"at": time.time(), "days": days, "source": got["source"], "facts": got["lines"],
               "sample": got["sample"], "model": None, "changes": [], "dropped": [], "applied": [],
               "before": _current_settings(uid), "reading": reading,
               "saying": got["lines"][-1], "effect": "Nothing was changed, so there is no effect to look for."}
        if not dry:
            data["rounds"].append(out)
            _write(uid, data)
        return out

    from . import brain
    prompt = _PROMPT.format(facts="\n".join("- " + s for s in got["lines"]),
                            settings=_settings_text(), limits=_WHAT_CANNOT_BE_DONE)
    answer, model, tokens = brain.ask_ai(prompt, _SCHEMA, "Improving the settings from the numbers")

    proposed = [c for c in (answer.get("changes") or []) if isinstance(c, dict)]
    kept, dropped = [], []
    for c in proposed:
        name = str(c.get("setting") or "").strip()
        value = c.get("value")
        if not _allowed(name, value):
            dropped.append({"setting": name, "value": value,
                            "reason": "PeakCut does not change that setting." if name not in KINDS
                                      else "That was not a value this setting accepts."})
        elif len(kept) >= 2:
            # Two at a time, so the next round can tell which one moved a number.
            dropped.append({"setting": name, "value": value,
                            "reason": "At most two settings change in one round, so this one waits."})
        else:
            kept.append({"setting": name, "value": value, "why": str(c.get("why") or "")[:400],
                         "expect": str(c.get("expect") or "")[:400]})

    applied = []
    before = _current_settings(uid)
    if kept and not dry:
        applied = _apply(uid, kept)

    # What the round before this one started from, measured against where the numbers are now. This is
    # the only place PeakCut says whether a past change did anything, and it says it with a number.
    moved = compare(_last_reading(data), reading) if reading else []
    out = {"at": time.time(), "days": days, "source": got["source"], "facts": got["lines"],
           "sample": got["sample"], "model": model, "tokens": tokens,
           "changes": kept, "dropped": dropped, "applied": applied, "before": before,
           "reading": reading, "moved": moved,
           "saying": str(answer.get("saying") or "")[:400],
           "effect": ("What changed since the last round: " + " ".join(moved)) if moved
                     else "Not known yet. The next round compares these numbers against the ones above."}
    if not dry:
        data["rounds"].append(out)
        data["current"] = {"at": out["at"], "settings": _current_settings(uid)}
        _write(uid, data)
    return out


def _last_reading(data: dict) -> dict:
    """The reading the newest round recorded, so this round can say what moved since it."""
    for r in data.get("rounds") or []:
        got = r.get("reading")
        if isinstance(got, dict) and got:
            return got
    return {}


def _current_settings(user_id: str) -> dict:
    """The settings a round may touch, as they stand right now. Read from where they really live."""
    b = brand.load(user_id)
    return {"style": b.get("style") or "", "hook_words": b.get("hook_words") or "",
            "captions_always": bool(b.get("captions", True)),
            "clip_len": b.get("clip_len"), "sound": b.get("sound") or ""}


def _apply(uid: str, changes: list) -> list:
    """Put the accepted changes where they belong and say what actually moved.

    A change that cannot be written is reported, not swallowed: the report says which ones landed."""
    done = []
    doc = brand.load(uid)
    before = dict(doc)
    for c in changes:
        name, value = c["setting"], c["value"]
        key = _BRAND_KEY.get(name)
        if not key:
            continue
        if name == LENGTH[0]:
            doc[key] = float(value)
        elif name == COUNTER[0]:
            doc[key] = str(value).lower() in ("true", "1", "yes")
        else:
            doc[key] = str(value)[:120]
    try:
        got = brand.save(uid, doc)
    except (OSError, ValueError) as e:
        return [{"setting": c["setting"], "ok": False, "why": str(e)[:200]} for c in changes]
    for c in changes:
        name = c["setting"]
        key = _BRAND_KEY.get(name)
        done.append({"setting": name, "value": c["value"], "ok": True,
                     "from": _short(before.get(key)), "to": _short(got.get(key))})
    return done


def _short(v):
    """A value small enough to show beside another one, with None kept as None so the page can say so."""
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return v
    s = str(v)
    return s[:80]


def undo(at: float | None = None) -> dict:
    """Put the settings back to what they were before one round.

    `at` names the round to undo; without it, the newest round is undone. The brand is written back to
    the values the round recorded, which were read from the brand itself, so this is a restore and
    not a second guess."""
    uid = ctx.uid()
    data = _read(uid)
    if not data["rounds"]:
        raise ValueError("Nothing has been changed yet, so there is nothing to undo.")
    target, idx = None, -1
    for i in range(len(data["rounds"]) - 1, -1, -1):
        r = data["rounds"][i]
        if at is None or abs(float(r.get("at") or 0) - float(at)) < 1:
            target, idx = r, i
            break
    if not target:
        raise ValueError("There is no round from that time.")

    # The settings as they stood before this round, which the round itself recorded. Older rounds did
    # not keep that, so they are refused with a sentence rather than a guess.
    before = target.get("before")
    if not isinstance(before, dict):
        raise ValueError("The settings from before that round were not kept, so PeakCut cannot put them "
                         "back on its own. Set them by hand under Settings, Brand.")

    doc = brand.load(uid)
    for name, value in before.items():
        key = _BRAND_KEY.get(name)
        if key:
            doc[key] = value
    brand.save(uid, doc)
    data["rounds"][idx] = {**target, "undone": time.time()}
    _write(uid, data)
    return {"ok": True, "undone": data["rounds"][idx].get("at"), "settings": _current_settings(uid)}
