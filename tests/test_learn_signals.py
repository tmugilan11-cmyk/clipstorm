"""The four new pieces of wave 3, checked without a network and without an AI.

These modules only turn numbers and words into sentences, so the tests here are about the promises a
page depends on: a curve with real points says something and a curve without points says nothing (and
never invents a number), a blank hook scores zero instead of raising, a trial cannot claim an arm that
never ran, a day at the spending cap is refused in words, and an empty round still draws as a row.

Every import is guarded: a module this wave did not get to is printed as SKIP, and the rest still run.

Run: python tests/test_learn_signals.py
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

# A data folder of this test's own, made the plain way (a temp dir on this host gets a tightened ACL).
_DATA = HERE / "learn-signals-data"
_DATA.mkdir(exist_ok=True)
os.environ["PEAKCUT_DATA"] = str(_DATA)
os.environ.setdefault("PEAKCUT_ACCOUNTS", "0")

from studio import learn  # noqa: E402

# The modules this wave adds. Each one is optional here on purpose: a test file that cannot be run
# because a sibling module is missing would hide the modules that do exist.
try:
    from studio import learn_signals
except ImportError:
    learn_signals = None

try:
    from studio import hookscore
except ImportError:
    hookscore = None

try:
    from studio import ai_arms
except ImportError:
    ai_arms = None

try:
    from studio import learn_guard
except ImportError:
    learn_guard = None

try:
    from studio import learn_report
except ImportError:
    learn_report = None

ok = 0
bad = []


def check(name: str, got, want=True) -> None:
    global ok
    if got == want:
        ok += 1
    else:
        bad.append(f"{name}   got {got!r}  wanted {want!r}")


def section(name: str, module, run) -> None:
    """Run one group of checks, or say the module is not here and keep going."""
    if module is None:
        print(f"SKIP {name}")
        return
    try:
        run()
    except Exception as e:  # noqa: BLE001 - a section that raises is a failure, not an end of the run
        bad.append(f"{name} raised {type(e).__name__}: {e}")


# ---------------------------------------------------------------- learn_signals
# A curve with something to say: the audience is still there at 5 percent in, falls past half by a
# quarter of the way, and loses more at the very end. Percentages, as the module speaks them.
_CURVE = [{"at": 0, "kept": 100}, {"at": 5, "kept": 52}, {"at": 10, "kept": 51},
          {"at": 25, "kept": 48}, {"at": 50, "kept": 44}, {"at": 75, "kept": 38},
          {"at": 90, "kept": 30}, {"at": 100, "kept": 12}]
_TWO = [{"at": 0, "kept": 100}, {"at": 100, "kept": 20}]


def _signals() -> None:
    said = learn_signals.hook_signal(_CURVE)
    check("a curve with real points writes a hook sentence", bool(said.strip()))
    check("the hook sentence names the 5 percent mark", "5 percent" in said)
    check("the hook sentence carries the share still watching", "52 percent" in said)
    check("the hook sentence never prints a missing value", "None" not in said)
    check("an empty curve writes no hook sentence", learn_signals.hook_signal([]), "")
    check("an empty curve writes no length sentence", learn_signals.length_signal([]), "")
    check("an empty curve writes no number at all",
          (learn_signals.hook_signal([]), learn_signals.length_signal([])), ("", ""))

    # The crossing is where the share first falls to half of the 100 it started at.
    half = learn_signals.drop_off(_CURVE, 0.5)
    check("drop_off finds the crossing at a quarter of the way", half["at"], 25.0)
    check("drop_off reports the share still watching there", half["kept"], 48.0)
    check("two points cannot show a crossing", learn_signals.drop_off(_TWO, 0.5),
          {"at": None, "kept": None})
    check("no points cannot show a crossing", learn_signals.drop_off([], 0.5),
          {"at": None, "kept": None})

    check("two points are too few for a hook sentence", learn_signals.hook_signal(_TWO), "")
    check("two points are too few for a length sentence", learn_signals.length_signal(_TWO, 42), "")

    length = learn_signals.length_signal(_CURVE, 42)
    check("a real curve writes a length sentence", bool(length.strip()))
    check("the length sentence names the clip length it was given", "42 second" in length)

    whole = learn_signals.signals("no-such-video", 28, 42)
    check("a video with no curve gives empty sentences", (whole["hook"], whole["length"]), ("", ""))
    check("a video with no curve reports no points", whole["points"], 0)
    check("lines() has nothing to add without a curve", learn_signals.lines("no-such-video", 28, 42), [])


# ---------------------------------------------------------------- hookscore
_SHORT = "you lose the rent money"
_FILLER = "so and well just okay hey and then this stuff was a thing that happened"


def _hooks() -> None:
    short = hookscore.score(_SHORT)
    long = hookscore.score(_FILLER)
    check("a short concrete hook scores above a long filler one", short["score"] > long["score"])
    check("the short hook is called strong", short["verdict"], "strong")
    check("the short hook breaks no rule", short["reasons"],
          ["It breaks none of the rules this check knows."])
    check("a long filler hook loses a word-count point", any("words long" in r for r in long["reasons"]))
    check("a long filler hook loses a filler point", any('opens with "so"' in r for r in long["reasons"]))

    blank = hookscore.score("")
    check("an empty phrase scores 0", blank["score"], 0)
    check("an empty phrase is weak", blank["verdict"], "weak")
    check("an empty phrase says there is nothing to score", len(blank["reasons"]), 1)

    picked = hookscore.compare(_SHORT, _FILLER)
    check("compare names the stronger phrase", picked["better"], "a")
    check("compare states both scores", (picked["a"]["score"], picked["b"]["score"]),
          (short["score"], long["score"]))
    check("compare quotes the winning score", f"A scores {short['score']}" in picked["why"])
    check("compare of two blanks is a tie", hookscore.compare("", "")["better"], "same")

    given = [_FILLER, _SHORT, "the rent", "   "]
    got = hookscore.suggest(given, 3)
    check("suggest returns nothing not given", [p for p in got if p not in given], [])
    check("suggest keeps the strongest first", got[0] if got else "", _SHORT)
    check("suggest drops a blank phrase", all(p.strip() for p in got))
    check("suggest asks for none and gets none", hookscore.suggest(given, 0), [])


# ---------------------------------------------------------------- ai_arms
def _arms() -> None:
    trial = ai_arms.start("hook_words", "wait for it", "clip_len", 45)
    check("a trial opens on arm a", trial["arm"], "a")
    check("arm a applies the first setting",
          ai_arms.applied(trial), [{"setting": "hook_words", "value": "wait for it"}])
    check("a fresh trial has not run both arms", ai_arms.done(trial), False)

    turned = ai_arms.turn(trial)
    check("turning moves to arm b", turned["arm"], "b")
    check("turning records that arm a ran", turned["runs"], ["a"])
    check("the record handed in is not changed", trial["arm"], "a")
    check("arm b applies the second setting",
          ai_arms.applied(turned), [{"setting": "clip_len", "value": "45"}])
    check("one arm is not both arms", ai_arms.done(turned), False)

    ended = ai_arms.turn(turned)
    check("after the second turn both arms have run", ended["runs"], ["a", "b"])
    check("the trial is done", ai_arms.done(ended), True)

    thin = learn.MIN_SAMPLE_VIEWS - 1
    narrow = ai_arms.read(ended, {"views": max(1, thin // 4)}, {"views": thin})
    check("a move under the sample limit is called noise", "inside the noise" in narrow)
    check("the noise sentence names the limit", str(learn.MIN_SAMPLE_VIEWS) in narrow)
    check("the noise sentence is still readable prose",
          narrow[:1].isupper() and narrow.endswith("."))

    big = learn.MIN_SAMPLE_VIEWS * 20
    wide = ai_arms.read(ended, {"views": big}, {"views": big * 2})
    check("a move above the limit is not called noise", "noise" in wide, False)
    check("the better arm is the one named first", wide.startswith("Arm b"))

    check("a trial with no reading cannot pick an arm",
          "cannot yet say" in ai_arms.read(ended, {}, {"views": big}), True)
    check("a reading with no view count is refused in words",
          "no view count" in ai_arms.read(ended, {"views": None}, {"views": big}), True)

    for name in ("style", "hook_words", "clip_len", "sound", "captions_always"):
        check(f"{name} is a setting a trial accepts", name in ai_arms._five())
    try:
        ai_arms.start("watermark_size", "big", "clip_len", 45)
    except ValueError as e:
        check("a setting PeakCut cannot change is refused", "watermark_size" in str(e))
    else:
        check("a setting PeakCut cannot change is refused", "no error raised", "a ValueError")


# ---------------------------------------------------------------- learn_guard
_UID = "learn_signals_test_user"
_GUARD_FILE = None
_REAL_ROWS = None


def _guard_rows(calls: int, tokens: int) -> list:
    """A day of spending as a full record: this many rounds, this many tokens each, all just now."""
    now = time.time() - 60
    return [{"at": now, "tokens": tokens} for _ in range(calls)]


def _guard() -> None:
    global _GUARD_FILE, _REAL_ROWS
    _GUARD_FILE = learn_guard._file(_UID)
    _REAL_ROWS = learn_guard._rows
    if _GUARD_FILE.exists():
        _GUARD_FILE.unlink()

    check("a person who never ran a round spent nothing", learn_guard.spent(_UID),
          {"calls": 0, "tokens": 0, "at": 0.0})
    check("an empty day may start a round", learn_guard.allow(_UID), {"ok": True, "why": ""})

    # The brief says stub spent() here, but allow() reads its own rows rather than spent(). The record
    # itself is stubbed with the rows spent() would have counted, so the promise under test is the same:
    # a day at the ceiling is refused, in a sentence, instead of raising.
    full = _guard_rows(learn_guard.MAX_CALLS_PER_DAY, 1200)
    learn_guard._rows = lambda uid: list(full)
    try:
        said = learn_guard.allow(_UID)
    finally:
        learn_guard._rows = _REAL_ROWS

    check("a day at the call cap is refused", said["ok"], False)
    check("the refusal is a sentence naming the cap", str(learn_guard.MAX_CALLS_PER_DAY) in said["why"])
    check("the refusal says when it frees", "can start in" in said["why"])
    check("the refusal ends as a sentence", said["why"].rstrip().endswith("."))
    check("the refusal prints no missing value", "None" not in said["why"])

    learn_guard._rows = lambda uid: list(full)
    try:
        spent = learn_guard.spent(_UID)
        words = learn_guard.report(_UID)
    finally:
        learn_guard._rows = _REAL_ROWS

    check("spent counts the rounds at the cap", spent["calls"], learn_guard.MAX_CALLS_PER_DAY)
    check("the report at the cap says no rounds are left", words.startswith("No rounds left today."))
    check("the report never says None", "None" in words, False)
    check("the report has no fraction of a round", re.findall(r"\d+\.\d+", words), [])

    learn_guard._rows = lambda uid: []
    try:
        open_words = learn_guard.report(_UID)
    finally:
        learn_guard._rows = _REAL_ROWS
    check("an unused day reports every round left",
          f"{learn_guard.MAX_CALLS_PER_DAY} of {learn_guard.MAX_CALLS_PER_DAY} rounds" in open_words)
    check("an unused day reports every token left",
          f"{learn_guard.MAX_TOKENS_PER_DAY:,}" in open_words)
    check("the open report never says None", "None" in open_words, False)
    check("the open report has no fraction of a round", re.findall(r"\d+\.\d+", open_words), [])

    # One real round, written the way a round writes itself, so note() is exercised too.
    if _GUARD_FILE.exists():
        _GUARD_FILE.unlink()
    learn_guard.note(_UID, 1500)
    after = learn_guard.spent(_UID)
    check("a written round is counted", after["calls"], 1)
    check("a written round keeps its tokens", after["tokens"], 1500)
    check("a written round records a real time", after["at"] > 0)
    if _GUARD_FILE.exists():
        _GUARD_FILE.unlink()


# ---------------------------------------------------------------- learn_report
_KEYS = ("at", "when", "days", "source", "facts", "changes", "dropped", "applied",
         "saying", "effect", "moved", "reading", "undone")


def _report() -> None:
    row = learn_report.shape({})
    missing = [k for k in _KEYS if k not in row]
    check("an empty round has every key", missing, [])
    check("no key of an empty round is None", [k for k in _KEYS if row[k] is None], [])
    check("an empty round has no time", row["at"], 0.0)
    check("an empty round says when in words", row["when"], "at an unknown time")

    said = learn_report.story({})
    check("the story of an empty round is a sentence", said, "Nothing has run yet.")
    check("the story of an empty round never says None", "None" in said, False)

    for value in (0, None, "", "not a time", -5):
        when = learn_report.when(value)
        check(f"when({value!r}) is not None", when is None, False)
        check(f"when({value!r}) is not empty", when == "", False)

    now = learn_report.when(time.time())
    check("a real moment reads as words", isinstance(now, str) and bool(now.strip()), True)
    check("a real moment does not say None", "None" in now, False)

    # A round with a fact and no change still has to read as prose, not as a broken template.
    real = learn_report.shape({"at": time.time(), "days": 28, "source": "youtube",
                               "facts": ["1200 views, up from 900."]})
    check("a shaped round keeps its fact", real["facts"], ["1200 views, up from 900."])
    check("a shaped round saying is not None", real["saying"], "")
    told = learn_report.story(real)
    check("a round with one change says it changed nothing", "It changed nothing." in told)
    check("the story of a real round never says None", "None" in told, False)


section("learn_signals", learn_signals, _signals)
section("hookscore", hookscore, _hooks)
section("ai_arms", ai_arms, _arms)
section("learn_guard", learn_guard, _guard)
section("learn_report", learn_report, _report)

print()
if bad:
    print(f"{len(bad)} check(s) failed")
    for line in bad:
        print("  " + line)
    sys.exit(1)
print(f"All checks passed. {ok} ok")
