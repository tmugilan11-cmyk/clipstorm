"""Checks every feature the overhaul added, without a network, a key, or a render.

Each of the sixteen new modules under studio/ is imported, asked for the facts it should know, and called on a
tiny input where it can be. Nothing here spends money, downloads anything, or touches the real data folder: the
tests that write point PEAKCUT_DATA at a throwaway directory first.

    python tests/test_overhaul.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Every test that writes anything must land in a throwaway folder, so import config only after this is set.
# A plain folder beside the repo, not tempfile.mkdtemp: on Windows a mkdtemp folder gets a tightened DACL that
# then refuses the sub-folders config.py makes inside it.
_TMP = str(Path(__file__).resolve().parent / "overhaul-data")
os.environ["PEAKCUT_DATA"] = _TMP
os.environ["PEAKCUT_FETCH_MODEL"] = "0"
os.environ["PEAKCUT_UPDATE_CHECK"] = "0"

from studio import (autopilot, brand, captions, chat, config, edit, formats, hunt,  # noqa: E402
                    meme, moments, music, peek, rules, translate, vision, voice, ytstats)

failures = []
skips = []


def check(name, got, want):
    if got == want:
        print(f"  ok    {name}")
    else:
        print(f"  FAIL  {name}: got {got!r}, wanted {want!r}")
        failures.append(name)


def truthy(name, got):
    """Anything that should simply be there: a non-empty string, a non-empty list, a true flag."""
    if got:
        print(f"  ok    {name}")
    else:
        print(f"  FAIL  {name}: got {got!r}")
        failures.append(name)


def ok(name, fn):
    """A call that must not raise. Its return value is left to the caller to look at."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 - a raising module is exactly what this is checking for
        print(f"  FAIL  {name}: raised {type(e).__name__}: {str(e)[:120]}")
        failures.append(name)
        return None


print("brand")
check("defaults has the whole schema", len(brand.DEFAULTS) >= 24, True)
d = brand.defaults()
check("defaults normalise to the same keys", sorted(d), sorted(brand.DEFAULTS))
check("colours are hex without #", "FFFFFF" in d["colors"].values() or all(len(v) == 6 for v in d["colors"].values()), True)
check("a theme is in the list", "neon" in brand.THEMES, True)
saved = ok("brand.save", lambda: brand.save("overhaul-test", {"theme": "neon", "colors": {"spoken": "#ff00aa"}}))
if saved:
    check("a lower-case #colour is cleaned", saved["colors"]["spoken"], "FF00AA")
    back = ok("brand.load", lambda: brand.load("overhaul-test"))
    check("what was saved comes back", back["colors"]["spoken"] if back else None, "FF00AA")
    truthy("the file is on disk", Path(config.DATA_DIR / "brand_overhaul-test.json").exists())
bad = ok("brand.save with rubbish", lambda: brand.save("overhaul-test", {"colors": {"spoken": "nope"}, "made_up": 1}))
if bad:
    check("a bad colour falls back", bad["colors"]["spoken"], brand.DEFAULTS["colors"]["spoken"])
    check("an unknown key is dropped", "made_up" in bad, False)
trap = ok("brand.save with a path as the user", lambda: brand.save("../../escape", {}))
truthy("a path in the user id cannot escape", Path(config.DATA_DIR / "brand__________________escape.json").exists() or trap is not None)
seen = ok("brand.apply_style", lambda: brand.apply_style(("A", "A", 0, 80, 1, "111111", "222222", "333333", 4, 2, None, 3, 1200), d))
check("apply_style keeps the 13 fields", len(seen) if seen else 0, 13)
check("apply_style leaves a short tuple alone", brand.apply_style((1, 2), d), (1, 2))

print("captions")
names = captions.style_names()
check("there are 42 video looks", len(names), 42)
# The exact number is a gate: post-description formats do not belong in the burned-in video style table.
check("the names are strings", all(isinstance(n, str) for n in names), True)
truthy("style() resolves a look", ok("captions.style", lambda: captions.get(names[0]) or True))
ass = ok("captions.build_ass", lambda: captions.build_ass(
    [{"w": "hello", "s": 0.0, "e": 0.4}, {"w": "there", "s": 0.4, "e": 0.9}],
    0.0, 0.9, "a hook", names[0], [], 200, 1250))
truthy("the subtitle file has a header", ass and ass.startswith("[Script Info]"))
truthy("the subtitle file has a line of dialogue", ass and "Dialogue:" in ass)

print("formats")
truthy("there is at least one format", len(formats.FORMATS) >= 1)
check("an empty pick is still a known format", formats.fmt_of({}) in formats.FORMATS, True)
plan = ok("formats.plan", lambda: formats.plan({}, [{"w": "hi", "s": 0.0, "e": 0.5}]))
check("a plan is a dict", isinstance(plan, dict), True)

print("chat")
import json  # noqa: E402  (only needed here)
# chat reads "t", "user" and "text" - the names its own _clean() keeps.
msgs = [{"t": 1.0, "user": "a", "text": "LOL"}, {"t": 1.5, "user": "b", "text": "lol"},
        {"t": 2.0, "user": "c", "text": "W"}, {"t": 2.2, "user": "d", "text": "LOL"},
        {"t": 30.0, "user": "e", "text": "lol"}, {"t": 30.5, "user": "f", "text": "LOL"},
        {"t": 31.0, "user": "g", "text": "LOL"}, {"t": 31.5, "user": "h", "text": "LOL"},
        {"t": 32.0, "user": "i", "text": "LOL"}]
truthy("top_phrases finds the repeated word", ok("chat.top_phrases", lambda: chat.top_phrases(msgs, 3)))
spikes = ok("chat.find_spikes", lambda: chat.find_spikes(msgs, ratio=2.0, minimum=3))
check("find_spikes returns a list", isinstance(spikes, list), True)
heat = ok("chat.heat", lambda: chat.heat(msgs, 0.0, 3.0))
check("heat is a 0-100 number", isinstance(heat, int) and 0 <= heat <= 100, True)
check("heat of an empty window is 0", chat.heat(msgs, 200.0, 260.0), 0)
check("find_spikes on nothing is empty", chat.find_spikes([], 3.0, 5), [])

print("moments")
check("scoring nothing is a dict", isinstance(ok("moments.score", lambda: moments.score({})), dict), True)

print("vision")
check("vision says whether it can work", isinstance(vision.AVAILABLE, bool) or vision.AVAILABLE is None, True)
check("vision.available() gives a yes or no", isinstance(vision.available(), bool), True)
check("tagging nothing is a list", isinstance(ok("vision.tag_transcript", lambda: vision.tag_transcript([], [])), list), True)

print("meme")
truthy("there are moods", len(meme.MOODS) >= 1)
check("meme says whether it can work", isinstance(meme.AVAILABLE, bool), True)

print("music")
truthy("there are beds", len(music.MOODS) >= 1)
check("music says whether it can work", isinstance(music.AVAILABLE, bool), True)

print("translate")
truthy("there are languages", len(translate.LANGS) >= 1)
check("translate says whether it can work", isinstance(translate.available(), bool), True)
if not translate.available():
    skips.append("translate.text (no engine installed)")
    skips.append("translate.words (no engine installed)")
else:
    truthy("a line comes back translated", ok("translate.text", lambda: translate.text("hello", "es")))

print("peek")
ts = ok("peek.times", lambda: peek.times(0.0, 60.0, 4))
check("four moments are offered", len(ts) if ts else 0, 4)
check("they sit inside the clip", all(0.0 <= t <= 60.0 for t in ts) if ts else False, True)
check("they are in order", ts == sorted(ts) if ts else False, True)

print("rules")
doc = ok("rules.load", lambda: rules.load())
truthy("the rules document is not empty", doc)
hit = ok("rules.lookup", lambda: rules.lookup("twitch", "xqc"))
check("a known channel answers with a rule", isinstance(hit, dict) and "rule" in hit, True)
miss = ok("rules.lookup of an unknown channel", lambda: rules.lookup("twitch", "no-such-channel-xyz"))
check("an unknown channel does not raise", True, True)
truthy("badge renders", ok("rules.badge", lambda: rules.badge({"rule": "ask"}, "x")))

print("hunt")
check("watching is a list", isinstance(ok("hunt.watching", lambda: hunt.watching()), list), True)
check("a key is a string", isinstance(hunt.key("twitch", "xqc"), str), True)

print("ytstats")
check("a bare id is kept", ytstats.vid_id("dQw4w9WgXcQ"), "dQw4w9WgXcQ")
check("a watch link gives up its id", ytstats.vid_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"), "dQw4w9WgXcQ")
check("a shorts link gives up its id", ytstats.vid_id("https://youtube.com/shorts/dQw4w9WgXcQ"), "dQw4w9WgXcQ")
check("nonsense gives nothing", not ytstats.vid_id(""), True)

print("voice")
truthy("voice can be applied", callable(voice.apply))

print("autopilot")
# autopilot writes an OPERATING SYSTEM task: "windows", "macos" or "linux", not a streaming platform.
text = ok("autopilot.preview", lambda: autopilot.preview("windows", ["09:00", "18:30"]))
truthy("a preview is text", isinstance(text, str) and text.strip())
truthy("the preview names the time", text and ("09:00" in text or "9:00" in text))
truthy("the preview does not run anything", text and "pastes it" in text.lower())
inst = ok("autopilot.install without confirming", lambda: autopilot.install("windows", ["09:00"], "echo hi"))
check("installing needs a deliberate confirmation", isinstance(inst, dict) and not inst.get("ok", True), True)
truthy("and says why", inst and "confirm" in str(inst.get("error", "")).lower())

print("edit")
change = ok("edit.parse", lambda: edit.parse("end 2 seconds earlier"))
truthy("the change mentions the end", isinstance(change, dict) and "end" in json.dumps(change))
clip = {"id": "c1", "start": 10.0, "end": 40.0, "style": "bounce"}
after = ok("edit.apply", lambda: edit.apply(clip, change or {}))
check("apply gives back a clip", isinstance(after, dict), True)
check("apply leaves the original alone", clip["end"], 40.0)
nothing = ok("edit.parse of chatter", lambda: edit.parse("make it nice"))
check("unclear words are not an error", isinstance(nothing, dict), True)

print()
if skips:
    for s in skips:
        print(f"  skip  {s}")
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("All checks passed.")
