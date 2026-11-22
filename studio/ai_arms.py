"""Two-arm trials: try one setting at a time, so a round can say which change moved the numbers.

`studio/learn.py` asks the AI for up to two changes and applies them together. That is the confound: if
views move, nobody can say which of the two did it, and the next round builds on a guess. A trial gives
each setting its own window instead. Arm a applies the first setting. When that window has been
measured, `turn()` moves to arm b, which applies the second setting. Each arm keeps its own reading, so
`read()` can name the arm that came out ahead instead of guessing.

    trial = ai_arms.start("hook_words", "wait for it", "clip_len", "45")
    ai_arms.applied(trial)                      # [{"setting": "hook_words", "value": "wait for it"}]
    trial = ai_arms.turn(trial)                 # arm a has run, arm b is next
    ai_arms.applied(trial)                      # [{"setting": "clip_len", "value": "45"}]
    trial = ai_arms.turn(trial)                 # arm b has run, so the trial is done
    ai_arms.done(trial)                         # True
    ai_arms.read(trial, reading_a, reading_b)   # one sentence naming the better arm

The caller applies the one item `applied()` returns and puts the other setting back to what it was, so
exactly one change is in effect during an arm. A caller that leaves the first change in place while
running the second arm has rebuilt the confound this file exists to remove.

Nothing is written to disk here. `studio/learn.py` already keeps the rounds in one small file, and a
second copy of the same facts would drift away from it. This file also does not import `server.py` or
any api module, so it is safe to import from a route, a test or a background thread.
"""
from __future__ import annotations

import time

try:  # the improvement engine owns the setting names and the sample limit
    from . import learn
except Exception:  # noqa: BLE001 - a broken engine must not stop a trial being written down
    try:  # a caller that put studio/ straight on the path instead of importing it as a package
        import learn  # type: ignore[no-redef]
    except Exception:  # noqa: BLE001
        learn = None

# The setting names this file will accept when the engine cannot be read. These are the words the
# tool already uses everywhere, so a trial written down during a broken import is still meaningful.
_PLAIN_NAMES = ("style", "hook_words", "clip_len", "sound", "captions_always")

# How a setting name reads in a sentence. A name that is not here falls back to spaces for underscores.
_READS = {"style": "style", "hook_words": "hook words", "clip_len": "clip length",
          "sound": "sound", "captions_always": "captions always"}


def _five() -> tuple[str, ...]:
    """The five setting names the improvement engine allows, read from its own constants."""
    if learn is not None:
        out = []
        for const in ("STYLE", "HOOK", "LENGTH", "MOOD", "COUNTER"):
            pair = getattr(learn, const, None)
            if isinstance(pair, (tuple, list)) and pair and isinstance(pair[0], str) and pair[0]:
                out.append(pair[0])
        if out:
            return tuple(out)
    return _PLAIN_NAMES


def _name_of(const: str, fallback: str) -> str:
    """One setting name from the engine's constant, with the plain word kept as a last resort."""
    pair = getattr(learn, const, None) if learn is not None else None
    if isinstance(pair, (tuple, list)) and pair and isinstance(pair[0], str) and pair[0]:
        return pair[0]
    return fallback


def _two_arms() -> tuple[str, str]:
    """The pair this wave trials against each other: the hook words and the clip length.

    Both are per clip values with no file behind them, so a trial cannot fail because a look the machine
    cannot draw or a sound it does not have was picked. They also change different parts of a clip, so a
    move in the numbers can be read as coming from one of them. The retention work in this wave points
    at the same two: where people stop watching becomes advice about the hook and the length.
    """
    return _name_of("HOOK", "hook_words"), _name_of("LENGTH", "clip_len")


ARMS = _two_arms()


# ---------------------------------------------------------------- the trial record


def start(target: str, value: str, other: str, other_value: str) -> dict:
    """Open a trial: name two settings and the value each one should try.

    Arm a applies `target` with `value`. Arm b applies `other` with `other_value`. Nothing is applied
    here, because the caller decides when an arm runs and what the channel looked like before it did.
    A setting PeakCut does not change is refused with a plain sentence, rather than kept in a record
    that could never be applied.
    """
    known = _five()
    first, second = str(target or "").strip(), str(other or "").strip()
    for name in (first, second):
        if name not in known:
            raise ValueError(f"PeakCut does not change a setting called {name or 'nothing'}. The settings "
                             f"it can try are: {', '.join(known)}.")
    if first == second:
        raise ValueError("A trial needs two different settings. The same setting twice cannot say which "
                         "change did it.")
    return {"at": time.time(), "target": first, "value": _text(value),
            "other": second, "other_value": _text(other_value), "arm": "a", "runs": []}


def turn(trial: dict) -> dict:
    """Finish the arm now in effect and hand back the record with the other arm next.

    The record handed in is copied, never changed, so a caller can keep the old one. The arm that was in
    effect is written into "runs", because that list is how `done()` knows an arm really ran and not
    only that a trial was created.
    """
    if not isinstance(trial, dict):
        return {}
    out = dict(trial)
    now = _arm(out)
    ran = _ran(out)
    if now not in ran:
        ran.append(now)
    out["runs"] = ran
    out["arm"] = "b" if now == "a" else "a"
    return out


def applied(trial: dict) -> list[dict]:
    """The setting and value this arm actually applies, as a one item list.

    Arm a applies `target` and arm b applies `other`. A list is returned because that is the shape a
    round already uses for the changes it applies, so the caller can hand it straight on.
    """
    got = trial if isinstance(trial, dict) else {}
    if _arm(got) == "b":
        return [{"setting": str(got.get("other") or ""), "value": _text(got.get("other_value"))}]
    return [{"setting": str(got.get("target") or ""), "value": _text(got.get("value"))}]


def done(trial: dict) -> bool:
    """Whether both arms have run.

    A trial is done after `turn()` has been called at the end of each arm: the first call records arm a
    and moves to arm b, the second records arm b. A record that never went through `turn()` carries no
    record of a finished arm, so it cannot claim both arms ran.
    """
    ran = _ran(trial)
    return "a" in ran and "b" in ran


# ---------------------------------------------------------------- reading the two arms


def read(trial: dict, before: dict, after: dict) -> str:
    """One sentence saying which arm did better, quoting both numbers it was given.

    `before` is the reading taken while arm a was in effect and `after` is the reading taken while arm b
    was in effect. The sentence always starts with a capital letter and ends in one full stop, so a page
    can print it as it is. A missing reading, a reading with no view count and a sample too small to read
    are each said in words rather than turned into a number that pretends to be measured.
    """
    return _saying(_read_line(trial, before, after))


def _saying(sentence: str) -> str:
    """A sentence ready to print: first letter capital, exactly one full stop at the end."""
    got = str(sentence or "").strip()
    while got.endswith(".."):
        got = got[:-1]
    return (got[0].upper() + got[1:]) if got else got


def _read_line(trial: dict, before: dict, after: dict) -> str:
    """The sentence itself, written without a capital so `read()` can put one in one place."""
    arms_a = _arm_text(trial, "a")
    arms_b = _arm_text(trial, "b")
    if not isinstance(before, dict) or not isinstance(after, dict) or not before or not after:
        return (f"Only one arm of this trial has a reading, so PeakCut cannot yet say whether {arms_a} "
                f"or {arms_b} did better.")
    was, now = _views(before), _views(after)
    if was is None or now is None:
        return (f"One of the two readings has no view count, so PeakCut cannot say whether {arms_a} or "
                f"{arms_b} did better.")
    said = _compare(before, after)
    if said is None:
        return ("PeakCut could not compare these readings because the improvement engine is not "
                "available, so this trial says nothing about either arm.")
    if now > was:
        better, worse = arms_b, arms_a
    elif was > now:
        better, worse = arms_a, arms_b
    else:
        better, worse = "", arms_b
    if not better:
        return _level_sentence(said, arms_a, arms_b, was)
    quoted = _views_quote(said)
    line = f"{better} did better than {worse}: {quoted}" if quoted else f"{better} did better than {worse}"
    limit = _min_views()
    if limit is None:
        return f"{line}, and PeakCut could not read its own sample limit, so treat that as a hint."
    thin = [v for v in (was, now) if v < limit]
    if thin:
        both = "both readings are" if len(thin) == 2 else "one reading is"
        return f"{line}, but {both} under {limit} views, so that difference is inside the noise."
    return f"{line}."


def _level_sentence(said: list[str], arms_a: str, arms_b: str, views: float) -> str:
    """The sentence for two arms that ended level on views, with any other move kept as a clause."""
    rest = [s for s in said if not s.startswith("Views ")]
    extra = _clause(rest[0]) if rest else ""
    line = (f"{arms_a} and {arms_b} ended level on views at {_num(views)} each, so this trial does not "
            f"say which setting is better")
    return f"{line}, even though {extra}." if extra else f"{line}."


# ---------------------------------------------------------------- small helpers


def _arm(trial: dict) -> str:
    """Which arm is in effect now. A record that says nothing is read as arm a."""
    got = trial if isinstance(trial, dict) else {}
    said = str(got.get("arm") or "a").strip().lower()
    return "b" if said == "b" else "a"


def _ran(trial: dict) -> list[str]:
    """The arms that have finished, in a fresh list so the caller's record is never changed."""
    got = trial.get("runs") if isinstance(trial, dict) else None
    if not isinstance(got, list):
        return []
    return [a for a in ("a", "b") if a in got]


def _arm_text(trial: dict, which: str) -> str:
    """How one arm reads in a sentence: arm a, which set hook words to wait for it."""
    got = trial if isinstance(trial, dict) else {}
    if which == "b":
        name, value = got.get("other"), got.get("other_value")
    else:
        name, value = got.get("target"), got.get("value")
    return f"arm {which}, which set {_setting(name)} to {_value(value)}"


def _setting(name) -> str:
    """A setting name as a person reads it."""
    got = str(name or "").strip()
    return _READS.get(got, got.replace("_", " ") or "an unnamed setting")


def _value(value) -> str:
    """A setting value as a person reads it, in quotes only when it holds a space."""
    got = _text(value)
    if not got:
        return "an empty value"
    return f'"{got}"' if " " in got else got


def _text(value) -> str:
    """Any value as a short plain string, so a length of 45 and the word 45 read the same."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()[:120]


def _views(reading: dict):
    """The view count from one reading, or None when the reading does not carry one."""
    got = reading.get("views") if isinstance(reading, dict) else None
    if got is None or isinstance(got, bool):
        return None
    try:
        return float(got)
    except (TypeError, ValueError):
        return None


def _compare(before: dict, after: dict):
    """The engine's own comparison, or None when it cannot be asked.

    `studio/learn.py` already says what moved and in which direction, so the sentence here quotes that
    work instead of growing a second opinion that could disagree with the Improve page.
    """
    if learn is None:
        return None
    try:
        got = learn.compare(before, after)
    except Exception:  # noqa: BLE001 - a bad reading must not stop the sentence being written
        return None
    return [str(s).strip() for s in (got or []) if str(s).strip()]


def _min_views():
    """The view count under which the engine calls a move noise, or None when it cannot be read."""
    limit = getattr(learn, "MIN_SAMPLE_VIEWS", None) if learn is not None else None
    try:
        return int(limit) if limit is not None else None
    except (TypeError, ValueError):
        return None


def _views_quote(said: list[str]) -> str:
    """The views sentence from the engine, without its full stop, so one sentence can hold it."""
    for s in said:
        if s.startswith("Views "):
            return s.rstrip(".")
    return ""


def _clause(sentence: str) -> str:
    """A sentence made to sit after a comma: no capital letter and no full stop."""
    got = sentence.strip().rstrip(".")
    return (got[0].lower() + got[1:]) if got else ""


def _num(v: float) -> str:
    """A number for a sentence: no trailing .0 on a whole one."""
    return str(int(round(v))) if abs(v - round(v)) < 0.05 else f"{v:.1f}"
