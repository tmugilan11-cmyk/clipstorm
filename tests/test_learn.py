"""What the improvement engine promises, checked without a network and without an AI.

The engine in `studio/learn.py` changes a real person's settings, so the tests here are about the
promises that make that safe rather than about the AI's opinion:

* only a listed setting can ever change, and a value outside its range is refused;
* a broken or hand-edited log reads as "nothing has happened", never as a traceback;
* the facts are sentences with the number in them, and too few views refuses to change anything;
* a round records the settings from before it ran, so undo is a restore;
* undo without a recorded before-state says so instead of guessing.

Run: python tests/test_learn.py
"""
from __future__ import annotations

import json
import time
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

# A data folder of this test's own, made the plain way (a temp dir on this host gets a tightened ACL).
_DATA = HERE / "learn-data"
_DATA.mkdir(exist_ok=True)
os.environ["PEAKCUT_DATA"] = str(_DATA)
os.environ.setdefault("PEAKCUT_ACCOUNTS", "0")

from studio import accounts, ai, api_analytics, brand, brain, config, ctx, learn  # noqa: E402

ok = 0
bad = []


def check(name: str, got, want=True) -> None:
    global ok
    if got == want:
        ok += 1
    else:
        bad.append(f"{name}   got {got!r}  wanted {want!r}")


UID = "learn_test_user"

# ---------------------------------------------------------------- what may change
check("a listed setting is allowed", learn._allowed("style", "beast"))
check("a style PeakCut cannot draw is refused", learn._allowed("style", "made-up-look"), False)
check("a hook of plain words is allowed", learn._allowed("hook_words", "wait for it"))
check("an empty hook is refused", learn._allowed("hook_words", ""), False)
check("a hook longer than a caption is refused", learn._allowed("hook_words", "x" * 200), False)
check("a length inside the range is allowed", learn._allowed("clip_len", 45))
check("a length of zero is refused", learn._allowed("clip_len", 0), False)
check("a length that is not a number is refused", learn._allowed("clip_len", "as long as it takes"), False)
check("a length longer than the form allows is refused", learn._allowed("clip_len", 9999), False)
check("yes and no work for a switch",
      (learn._allowed("captions_always", "yes"), learn._allowed("captions_always", "false")), (True, True))
check("a switch will not take a random word", learn._allowed("captions_always", "maybe"), False)
check("a setting that is not on the list is refused", learn._allowed("watermark_size", 0.3), False)
check("no silence is a real choice for the sound", learn._allowed("sound", ""))

# ---------------------------------------------------------------- the facts
_FULL = [{"views": 1200.0, "estimatedMinutesWatched": 4800.0, "averageViewDuration": 24.0,
          "averageViewPercentage": 41.0, "subscribersGained": 18.0, "subscribersLost": 3.0}]
_THIN = [{"views": 3.0, "estimatedMinutesWatched": 1.0, "averageViewDuration": 4.0,
          "averageViewPercentage": 20.0, "subscribersGained": 0.0, "subscribersLost": 0.0}]


def stub(rows, token="fake-token"):
    """Answer the Analytics question with one fixed row, and pretend a channel is connected.

    `learn.facts` asks `accounts.youtube_token` and `api_analytics._ask`; both are replaced here so the
    test never touches the network and never needs a real key."""
    api_analytics._ask = lambda token, start, end, metrics, **kw: rows
    accounts.youtube_token = lambda: token


_REAL_ASK = api_analytics._ask
_REAL_TOKEN = accounts.youtube_token

stub(_FULL)
try:
    with ctx.as_user(UID):
        got = learn.facts(28)
finally:
    api_analytics._ask = _REAL_ASK
    accounts.youtube_token = _REAL_TOKEN

check("the facts come from YouTube when a channel is connected", got["source"], "youtube")
check("enough views means it may change something", got["enough"])
check("the sample is the view count", got["sample"], 1200)
check("the first line carries the view count", "1200 views" in got["lines"][0])
check("the second line carries the seconds", "24 seconds" in got["lines"][1])
check("the third line carries the subscriber count", "15 subscribers" in got["lines"][2])
check("a fourth line says how long the video was", "seconds is what those two numbers describe"
      in got["lines"][3])

stub(_THIN)
try:
    with ctx.as_user(UID):
        thin = learn.facts(7)
finally:
    api_analytics._ask = _REAL_ASK
    accounts.youtube_token = _REAL_TOKEN

check("three views is not enough to change anything", thin["enough"], False)
check("the last line says why nothing will change", "at least" in thin["lines"][-1])

stub([], token="")
try:
    with ctx.as_user(UID):
        none = learn.facts(28)
finally:
    api_analytics._ask = _REAL_ASK
    accounts.youtube_token = _REAL_TOKEN

check("no channel reads as no channel", none["source"], "peakcut")
check("and says so in a sentence", "No YouTube channel is connected" in none["lines"][0])


# ---------------------------------------------------------------- a broken log
def write_log(payload: str) -> None:
    f = config.user_dir(UID) / "learn.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(payload, encoding="utf-8")


for payload in ("", "not json at all", "null", "[]", '"text"', "3", '{"rounds": "nope"}'):
    write_log(payload)
    with ctx.as_user(UID):
        readback = learn.log()
    check(f"a log holding {payload[:12] or 'nothing'!r} reads as empty", readback["rounds"], [])

# ---------------------------------------------------------------- a round that cannot run
write_log('{"rounds": []}')
_REAL_READY = ai.ready
ai.ready = lambda: False
try:
    with ctx.as_user(UID):
        blocked = learn.log()
        said = ""
        try:
            learn.run(28)
        except ValueError as e:
            said = str(e)
finally:
    ai.ready = _REAL_READY

check("with no AI set up a round is refused", blocked["can_run"], False)
check("and the reason names Settings, AI", "Settings, AI" in blocked["why_not"])
check("running it says the same thing", "Settings, AI" in said)


# ---------------------------------------------------------------- the version log and undo
def fake_ai(prompt, schema=None, purpose="AI call", timeout=None):
    """An answer with one allowed change, one allowed second change, and two that must be refused.

    The fourth is allowed on its own but beyond the limit of two per round, so it must not land."""
    return ({"changes": [
        {"setting": "style", "value": "beast", "why": "24 seconds is short, so a bigger look holds them.",
         "expect": "averageViewPercentage up"},
        {"setting": "watermark_size", "value": 0.4, "why": "guessing"},
        {"setting": "hook_words", "value": "wait for it", "why": "the first second decides it."},
        {"setting": "clip_len", "value": 41, "why": "one more change than allowed"},
    ], "saying": "Two changes, both supported by the numbers."}, "test-model", 900)


write_log('{"rounds": []}')
with ctx.as_user(UID):
    doc = brand.defaults()
    doc["style"] = "bounce"
    brand.save(UID, doc)

ai.ready = lambda: True
_REAL_BRAIN = brain.ask_ai
brain.ask_ai = fake_ai
stub(_FULL)
try:
    with ctx.as_user(UID):
        report = learn.run(28)
finally:
    ai.ready = _REAL_READY
    brain.ask_ai = _REAL_BRAIN
    api_analytics._ask = _REAL_ASK
    accounts.youtube_token = _REAL_TOKEN

check("at most two changes are kept", len(report["changes"]), 2)
check("the first kept change is the style", report["changes"][0]["setting"], "style")
check("the second kept change is the hook", report["changes"][1]["setting"], "hook_words")
check("the settings that cannot land are all reported", [d["setting"] for d in report["dropped"]],
      ["watermark_size", "clip_len"])
check("a third change waits for the next round",
      "At most two settings change" in report["dropped"][1]["reason"])
check("the dropped one says why", "does not change that setting" in report["dropped"][0]["reason"])
check("the effect is not claimed", "Not known yet" in report["effect"])
check("the round recorded what the settings were before", report["before"]["style"], "bounce")

with ctx.as_user(UID):
    after = brand.load(UID)
check("the style really changed on disk", after["style"], "beast")
check("the hook really changed on disk", after["hook_words"], "wait for it")
check("a setting the AI invented did not land", after.get("watermark_size"),
      brand.DEFAULTS["watermark_size"])

ai.ready = lambda: True
try:
    with ctx.as_user(UID):
        said_again = learn.log()
finally:
    ai.ready = _REAL_READY
check("the round is in the log", len(said_again["rounds"]), 1)
check("the newest round is first", said_again["rounds"][0]["changes"][0]["setting"], "style")
check("a second round is refused straight after", said_again["can_run"], False)
check("and says when the next round can start", "next round can start" in said_again["why_not"])

with ctx.as_user(UID):
    undone = learn.undo()
    back = brand.load(UID)
check("undo reports success", undone["ok"])
check("undo put the style back", back["style"], "bounce")
check("undo put the hook back", back["hook_words"], brand.DEFAULTS["hook_words"])
check("undo says what the settings are now", undone["settings"]["style"], "bounce")

# An answer the AI could not give must be a sentence, not a traceback.
write_log('{"rounds": []}')


def saying_nothing(prompt, schema=None, purpose="AI call", timeout=None):
    return ({"changes": [], "saying": "There are not enough views to say anything yet."},
            "test-model", 40)


with ctx.as_user(UID):
    doc = brand.defaults()
    brand.save(UID, doc)
ai.ready = lambda: True
brain.ask_ai = saying_nothing
stub(_FULL)
try:
    with ctx.as_user(UID):
        quiet = learn.run(7)
finally:
    ai.ready = _REAL_READY
    brain.ask_ai = _REAL_BRAIN
    api_analytics._ask = _REAL_ASK
    accounts.youtube_token = _REAL_TOKEN

check("an answer with no changes applies nothing", quiet["applied"], [])
check("and still records what the numbers said", len(quiet["facts"]) >= 3)
check("and repeats the AI's own sentence", "not enough views" in quiet["saying"])


# ---------------------------------------------------------------- undo that cannot be honest
write_log(json.dumps({"rounds": [{"at": 1.0, "changes": [{"setting": "style", "value": "beast"}],
                                 "applied": [{"setting": "style", "ok": True}]}], "current": None}))
with ctx.as_user(UID):
    refused = ""
    try:
        learn.undo()
    except ValueError as e:
        refused = str(e)
check("undo without a recorded before says so", "were not kept" in refused)

write_log('{"rounds": []}')
with ctx.as_user(UID):
    empty = ""
    try:
        learn.undo()
    except ValueError as e:
        empty = str(e)
check("undo with no rounds says there is nothing to undo", "nothing to undo" in empty)

write_log(json.dumps({"rounds": [{"at": 500.0, "before": {"style": "bounce"}}], "current": None}))
with ctx.as_user(UID):
    wrong = ""
    try:
        learn.undo(at=12345.0)
    except ValueError as e:
        wrong = str(e)
check("undo with a time no round has says so", "no round from that time" in wrong)

# ---------------------------------------------------------------- the settings a round reads
with ctx.as_user(UID):
    brand.save(UID, brand.defaults())
    now = learn._current_settings(UID)
check("the current settings are read from the brand",
      (now["style"], now["hook_words"], now["captions_always"]),
      (brand.DEFAULTS["style"], brand.DEFAULTS["hook_words"], True))

# ---------------------------------------------------------------- the shape the AI answers in
check("the answer schema asks for changes", "changes" in learn._SCHEMA["properties"])
check("and a change needs a setting",
      "setting" in learn._SCHEMA["properties"]["changes"]["items"]["properties"])
check("a change must name a setting and a value",
      learn._SCHEMA["properties"]["changes"]["items"]["required"], ["setting", "value", "why"])
check("the prompt lists the settings",
      "style" in learn._settings_text() and "sound" in learn._settings_text())
check("the prompt says what the AI cannot change", "You cannot change anything else" in
      learn._PROMPT.format(facts="x", settings="y", limits=learn._WHAT_CANNOT_BE_DONE))

# ---------------------------------------------------------------- the brand now holds the keys
d = brand.defaults()
check("the brand knows about captions", d["captions"], True)
check("the brand knows about a clip length", d["clip_len"], 30)
check("the brand knows about a sound, empty by default", d["sound"], "")
check("a clip length is held inside the range the form accepts",
      brand.normalise({"clip_len": 9999})["clip_len"], 600)
check("a sound name is made lower case and short", brand.normalise({"sound": "HY" + "P" * 40})["sound"],
      ("hyp" + "p" * 40)[:20])
check("a switch reads as a switch", brand.normalise({"captions": "no"})["captions"], False)

# ---------------------------------------------------------------- did the change do anything
# measure() is the reading a round keeps; compare() is the only place a round says what moved. Both are
# arithmetic on the same analytics report, so they are tested with fixed numbers and no network.
m = learn.measure(28)
check("a reading with no channel is empty, not zeros", m, {})

b = {"views": 1000, "hours": 12.0, "seconds": 8, "percent": 40.0}
a = {"views": 1500, "hours": 18.0, "seconds": 9, "percent": 45.0}
moved = learn.compare(b, a)
check("a rise is named as a rise with both numbers",
      any("Views up 50 percent, from 1000 to 1500." == line for line in moved), True)
check("every reading that moved is reported once", len(moved), 4)
check("a fall says down", learn.compare(a, b)[0], "Views down 33 percent, from 1500 to 1000.")

check("two empty readings compare to nothing", learn.compare({}, a), [])
check("a reading with no previous one compares to nothing", learn.compare(b, {}), [])
check("nothing moving says nothing", learn.compare({"views": 0, "hours": 0}, {"views": 0, "hours": 0}), [])

small = learn.compare({"views": 40, "hours": 1.0}, {"views": 44, "hours": 1.2})
check("a move on a tiny sample is called too small to read",
      any("too small to read" in line for line in small), True)
big = learn.compare({"views": 4000, "hours": 100.0}, {"views": 4400, "hours": 120.0})
check("a move on a real sample is not called too small",
      any("too small to read" in line for line in big), False)
check("a first reading from nothing is said plainly",
      learn.compare({"views": 0, "hours": 0}, {"views": 30, "hours": 2.0})[0],
      "Views went from nothing to 30.")
check("a whole number has no trailing point oh", learn._tidy(1500.0), "1500")
check("a part of a number keeps one decimal", learn._tidy(12.34), "12.3")

# A round records the reading it started from, and the next round reads it back.
write_log('{"rounds": [{"at": 900.0, "reading": {"views": 4000, "hours": 100.0}}], "current": null}')
check("the newest reading is found again", learn._last_reading(learn._read(UID)).get("views"), 4000)
write_log('{"rounds": [{"at": 900.0, "reading": null}], "current": null}')
check("a round with no reading does not break the next one", learn._last_reading(learn._read(UID)), {})

# ---------------------------------------------------------------- the clips as evidence
# content() reads PeakCut's own records, so it works with no YouTube connection at all. These checks use
# a fake job list: the shapes are what matter, not the numbers.
_REAL_JOBS = learn.jobs if hasattr(learn, "jobs") else None
from studio import jobs as _jobs


class _FakeJob(dict):
    pass


def _fake_jobs(rows):
    """Stand in for jobs.list_jobs with a fixed list, and put the real one back afterwards."""
    _jobs.list_jobs = lambda: [_FakeJob(r) for r in rows]
    return _jobs.list_jobs


_REAL_LIST = _jobs.list_jobs
try:
    now = time.time()
    _fake_jobs([
        {"created": now - 100, "options": {"style": "beast"}, "clips": [
            {"status": "done", "start": 0, "end": 20, "style": "beast", "views": 900, "hook": "wait"},
            {"status": "done", "start": 0, "end": 20, "style": "beast", "views": 700, "hook": "look"},
            {"status": "queued", "start": 0, "end": 20, "style": "beast"},
        ]},
        {"created": now - 200, "options": {"style": "hormozi"}, "clips": [
            {"status": "done", "start": 0, "end": 40, "style": "hormozi", "views": 100, "hook": "wait",
             "mood": "hype"},
            {"status": "done", "start": 0, "end": 40, "style": "hormozi", "views": 120},
        ]},
        {"created": 10.0, "options": {}, "clips": [{"status": "done", "start": 0, "end": 20, "views": 10}]},
    ])
    with ctx.as_user(UID):
        got = learn.content(3650)
    check("only finished clips are counted", got["clips"], 4)
    check("every clip with a number is counted", got["posted"], 4)
    check("the best look is the one with the higher average",
          max(got["per_style"].items(), key=lambda kv: kv[1]["avg"] or 0)[0], "beast")
    # The third job was made in 1970, so its clip is outside every window a person can pick and must not
    # be counted, while the two recent jobs (4 finished clips) must be.
    with ctx.as_user(UID):
        check("an old job is left out of the window", learn.content(3650)["clips"], 4)
    check("the look that won is named in a sentence",
          any("beast" in line and "views a clip" in line for line in got["lines"]), True)
    check("the length that won is named in a sentence",
          any("20 seconds did best" in line for line in got["lines"]), True)
    check("a hook used twice is said once",
          sum(line.count("wait") for line in got["lines"] if line.startswith("Hooks used")), 1)
    check("the sound used is counted", any("hype on 1" in line for line in got["lines"]), True)
    check("a look with one clip is not called the winner",
          got["per_len"][40]["seen"], 2)

    _fake_jobs([{"created": now, "options": {}, "clips": [
        {"status": "done", "start": 0, "end": 10, "views": None}]}])
    with ctx.as_user(UID):
        blind = learn.content(3650)
    check("clips with no number do not invent a winner", blind["per_style"]["unknown"]["avg"], None)
    check("and the page is told the numbers are missing",
          any("says which look or length works" in line for line in blind["lines"]), True)

    _fake_jobs([])
    with ctx.as_user(UID):
        none = learn.content(3650)
    check("no clips at all says so", none["lines"], ["No clips have been made yet, so there is no content to compare."])
finally:
    _jobs.list_jobs = _REAL_LIST

check("a length is rounded to the nearest five seconds", learn._length_bucket(22.4), 20)
check("a very short clip still has a bucket", learn._length_bucket(1.2), 5)
check("a clip with no length has its own bucket", learn._length_bucket(0), 0)
check("the same hook twice is kept once", learn._dedupe(["a", "b", "a", "c"]), ["a", "b", "c"])
check("a group with one clip is never the winner",
      learn._best({"a": {"avg": 999.0, "seen": 1}, "b": {"avg": 1.0, "seen": 3}})[0], "b")
check("nothing to compare means no winner", learn._best({"a": {"avg": None, "seen": 0}}), None)

print()
if bad:
    print(f"{len(bad)} check(s) failed")
    for line in bad:
        print("  " + line)
    sys.exit(1)
print(f"All checks passed. {ok} ok")
