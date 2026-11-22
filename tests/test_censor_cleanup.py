"""Taking the swearing out, and taking the dead air out.

Both were asked for in the same breath, and both are checked here the same way: a word list goes in, and the answer is
read back. The render is checked too, because a plan that never reaches ffmpeg is a plan that does nothing.

The two jobs are deliberately different. Censoring must NOT change the length: a silence sits where the word was, so
the caption stays on the mouth. Cleanup must change the length, and everything after a cut must move earlier with it -
including the captions and, when both are on, the silences.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from studio import clean          # noqa: E402

FAILED = []


def check(name, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + name + (("   " + str(detail)) if detail and not ok else ""))
    if not ok:
        FAILED.append(name)


# A sentence with a swear in the middle, a filler at the start and a long dead patch at the end.
WORDS = [
    {"w": "Um,", "s": 0.10, "e": 0.40},
    {"w": "so", "s": 0.45, "e": 0.70},
    {"w": "this", "s": 0.70, "e": 0.95},
    {"w": "is", "s": 0.95, "e": 1.10},
    {"w": "fucking", "s": 1.10, "e": 1.60},
    {"w": "great", "s": 1.60, "e": 1.95},
    {"w": "uh", "s": 2.10, "e": 2.30},
    {"w": "yeah", "s": 2.30, "e": 2.70},
    # ...then nothing is said for four seconds.
]
START, END = 0.0, 6.70

print("what each switch does")
none = clean.plan(WORDS, START, END, clean.Rules())
check("with both switches off nothing is touched", none["mute"] == [] and none["cut"] == [], str(none))
check("and the length is untouched", none["kept_seconds"] == round(END - START, 3), none["kept_seconds"])
check("and it says so plainly", none["why"] == "Nothing was censored and nothing was cut.", none["why"])

censor = clean.plan(WORDS, START, END, clean.Rules(censor=True))
check("bleeping finds the one swear word", len(censor["mute"]) == 1, censor["mute"])
check("the silence covers it", censor["mute"] and abs(censor["mute"][0][0] - 1.06) < 0.06, censor["mute"])
check("bleeping does not cut any time", censor["cut"] == [] and censor["kept_seconds"] == round(END - START, 3),
      censor["kept_seconds"])

cut = clean.plan(WORDS, START, END, clean.Rules(cleanup=True))
check("cleanup cuts something", len(cut["cut"]) >= 1, cut["cut"])
check("the clip gets shorter", cut["kept_seconds"] < END - START, (cut["kept_seconds"], END - START))
check("the filler is named as dropped", cut["dropped"] > 0.5, cut["dropped"])

both = clean.plan(WORDS, START, END, clean.Rules(censor=True, cleanup=True))
check("with both on, the silence is moved onto the cut timeline", both["mute"] != censor["mute"], both["mute"])
check("and it sits earlier, because time was removed before it",
      both["mute"] and both["mute"][0][0] < censor["mute"][0][0], (both["mute"], censor["mute"]))

print()
print("the words a person will read")
bleeped = clean.bleep(WORDS, clean.CURSE)
check("the swear keeps its place but not its letters", bleeped[4]["w"] == "F...", bleeped[4]["w"])
check("the other words are untouched", [w["w"] for w in bleeped if w["w"] != "F..."] ==
      [w["w"] for i, w in enumerate(WORDS) if i != 4], [w["w"] for w in bleeped])
check("and its timing is unchanged, so the caption stays on the mouth",
      (bleeped[4]["s"], bleeped[4]["e"]) == (WORDS[4]["s"], WORDS[4]["e"]), bleeped[4])

moved = clean.retime(WORDS, START, cut["keep"])
check("re-timed words all fit inside the shorter clip",
      moved and max(w["e"] for w in moved) <= cut["kept_seconds"] + 0.01, max(w["e"] for w in moved))
check("and no word is left with a negative start", moved and min(w["s"] for w in moved) >= 0, min(w["s"] for w in moved))
check("re-timing keeps every word that survives", len(moved) >= 4, len(moved))

print()
print("words that look like swearing and are not")
check("class is not ass", clean._plain("class") == "class", clean._plain("class"))
check("Scunthorpe survives", clean._plain("Scunthorpe") == "scunthorpe", clean._plain("Scunthorpe"))
check("a swear with punctuation is still caught", clean._plain("Fuck!") == "fuck", clean._plain("Fuck!"))
check("the same swear in caps is caught", clean._plain("FUCKING,") == "fucking", clean._plain("FUCKING,"))

custom = clean.plan(WORDS, START, END, clean.Rules(censor=True, extra=["great"]))
# "great" sits right after "fucking", so the two silences touch and become one longer silence. That is the right
# answer: two separate one-word gaps would leave the half-second between them audible.
check("a word a person adds is silenced too", custom["mute"] and custom["mute"][0][1] > censor["mute"][0][1],
      (custom["mute"], censor["mute"]))
check("a silence long enough to cover both words is made", custom["mute"] == [(1.06, 2.01)], custom["mute"])

print()
print("edges that must not break a clip")
check("no words means no plan", clean.plan([], 0.0, 10.0, clean.Rules(True, True))["cut"] == [])
check("a zero-length clip is left alone",
      clean.plan(WORDS, 5.0, 5.0, clean.Rules(True, True))["keep"] == [])
short = clean.plan([{"w": "Um,", "s": 0.10, "e": 0.40}, {"w": "so", "s": 0.45, "e": 0.70}], 0.0, 0.5,
                    clean.Rules(cleanup=True))
check("a clip too short to cut is left whole", short["kept_seconds"] == 0.5, short["kept_seconds"])
check("and it says why rather than doing nothing quietly",
      "too short to cut" in short["why"], short["why"])
check("a swear with no timing is skipped rather than crashing",
      clean.plan([{"w": "shit", "s": "x", "e": None}], 0.0, 2.0, clean.Rules(censor=True))["mute"] == [])

print()
print("what ffmpeg is told")
spans = cut["keep"]
expr = clean.keep_expression(spans)
check("the keep expression names every piece", expr.count("between") == len(spans), expr)
check("every piece is a positive window", all(a < b for a, b in spans), spans)
check("the pieces never overlap", all(spans[i][1] <= spans[i + 1][0] for i in range(len(spans) - 1)), spans)
mute_chain = clean.mute_filter(both["mute"])
check("a silence becomes a volume filter", "volume=volume=0" in mute_chain, mute_chain)
check("it is limited to its own window", "enable='between(t," in mute_chain, mute_chain)
check("nothing to silence means no filter at all", clean.mute_filter([]) == "", clean.mute_filter([]))

print()
print("the switches reach a job")
JOBS = (ROOT / "studio" / "jobs.py").read_text(encoding="utf-8")
check("the two flags are known settings", '"censor": False, "cleanup": False' in JOBS, "defaults")
check("a page sending the word false turns it off", 'in ("1", "true", "on", "yes")' in JOBS, "coercion")
check("the render route reads them", 'for flag in ("censor", "cleanup")' in JOBS, "request_render")
check("a new clip carries them", 'censor=o.get("censor", False)' in JOBS, "create")

RENDER = (ROOT / "studio" / "render.py").read_text(encoding="utf-8")
check("the renderer plans the cleanup", "clean.plan(words, start, end" in RENDER, "render_clip")
check("the picture is re-timed with select", "select=" in RENDER and "setpts=N/" in RENDER, "filter")
check("the sound is cut the same way", "aselect=" in RENDER and "asetpts=N/SR/TB" in RENDER, "audio chain")
check("the captions are re-timed", "clean.retime(said, start, plan" in RENDER, "retime")
check("the swear is bleeped in the caption too", "clean.bleep(said" in RENDER, "bleep")

PAGE = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
check("the clip dialog has both switches", 'data-f="censor"' in PAGE and 'data-f="cleanup"' in PAGE, "dialog")
check("and a line that explains them", 'id="ed_clean"' in PAGE, "ed_clean")

FEAT = (ROOT / "web" / "feat" / "clean-forecast.js")
check("the forecast is a page file", FEAT.exists(), str(FEAT))
if FEAT.exists():
    src = FEAT.read_text(encoding="utf-8")
    check("it reads the switches on screen, not the saved clip", "function live(" in src, "live")
    check("and it escapes what it prints", "textContent" in src, "textContent")

print()
if FAILED:
    print("%d check(s) failed:" % len(FAILED))
    for name in FAILED:
        print("  - " + name)
    sys.exit(1)
print("All checks passed.")
