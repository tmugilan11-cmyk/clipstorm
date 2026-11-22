"""The settings the Brand page saves must reach the work, not sit in a file.

`learn.py` changes five settings and claims the next clips will be different. That claim is only true if the
pipeline reads those five. This test follows each one from the saved document to the thing that uses it:
the caption look and the sound and the length land on the job, the hook words reach the prompt the AI is asked,
and the brand's colours reach the renderer. Run directly:

    cd peakcut && python tests/test_brand_reaches_work.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["PEAKCUT_DATA"] = str(Path(tempfile.mkdtemp(prefix="brand-work-")) / "data")
os.environ["PEAKCUT_ACCOUNTS"] = "0"
os.environ["PEAKCUT_FETCH_MODEL"] = "0"

from studio import brand, config, ctx, db, jobs, meme, music, render, captions  # noqa: E402

ok, bad = 0, 0


def check(name, cond, got=""):
    global ok, bad
    if cond:
        ok += 1
        print(f"  ok   {name}")
    else:
        bad += 1
        print(f"  FAIL {name}   {got if got != '' else ''}")


def fresh():
    for f in config.DATA_DIR.glob("brand_*.json"):
        f.unlink()
    for f in config.DATA_DIR.glob("jobs/*/job.json"):
        f.unlink()


db.init()
config.DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- the document says one thing, and the job must say the same -------------
print("a brand that names a look, a length and a sound")
fresh()
brand.save("u_local", {"style": "beast", "clip_len": 45, "sound": "hype", "captions": False,
                       "hook_words": "start with a question"})
prefs = jobs._brand_prefs("u_local")
check("it names the caption look", prefs.get("style") == "beast", prefs)
check("it names the length", prefs.get("max_len") == 45, prefs)
check("it names the sound", prefs.get("sound") == "hype", prefs)
check("it carries captions off", prefs.get("captions") is False, prefs)

with ctx.as_user("u_local"):
    job = jobs.create({"type": "file", "path": "/nowhere.mp4", "name": "brand test"}, {}, enqueue=False)
opts = job["options"]
check("the job took the look", opts.get("style") == "beast", opts.get("style"))
check("the job took the length", opts.get("max_len") == 45, opts.get("max_len"))
check("the job took the sound", opts.get("sound") == "hype", opts.get("sound"))
check("the job took captions off", opts.get("captions") is False, opts.get("captions"))
check("the job still has a sane short length", opts["min_len"] < opts["max_len"],
      (opts["min_len"], opts["max_len"]))

# --- a value typed on the form still wins over the saved one ----------------
print("a form that names something else than the brand")
with ctx.as_user("u_local"):
    typed = jobs.create({"type": "file", "path": "/nowhere.mp4", "name": "typed"},
                        {"style": "hormozi", "max_len": 30}, enqueue=False)
check("the typed look wins", typed["options"]["style"] == "hormozi", typed["options"]["style"])
check("the typed length wins", typed["options"]["max_len"] == 30, typed["options"]["max_len"])
check("the saved sound still applies", typed["options"].get("sound") == "hype", typed["options"].get("sound"))

# --- nothing saved means the old defaults, exactly -------------------------
print("a person who never saved a brand")
fresh()
with ctx.as_user("u_local"):
    plain = jobs.create({"type": "file", "path": "/nowhere.mp4", "name": "plain"}, {}, enqueue=False)
check("the look is PeakCut's own", plain["options"]["style"] == jobs.DEFAULTS["style"], plain["options"]["style"])
check("the length is PeakCut's own", plain["options"]["max_len"] == jobs.DEFAULTS["max_len"],
      plain["options"]["max_len"])
check("no sound is invented", plain["options"].get("sound") == "", plain["options"].get("sound"))
check("captions stay on", plain["options"]["captions"] is True, plain["options"]["captions"])

# --- a brand from an older build cannot break a job -----------------------
print("a brand holding values this build does not know")
fresh()
brand.save("u_local", {"style": "not-a-look", "clip_len": 99999, "sound": "not-a-sound"})
survived = jobs._brand_prefs("u_local")
check("an unknown look is not passed on", "style" not in survived, survived)
check("an over-long length is pulled back into range",
      survived.get("max_len") == jobs.LIMITS["max_len"][1], survived.get("max_len"))
check("an unknown sound is not passed on", "sound" not in survived, survived)
with ctx.as_user("u_local"):
    guarded = jobs.create({"type": "file", "path": "/nowhere.mp4", "name": "guarded"}, {}, enqueue=False)
check("the job still has a real look", guarded["options"]["style"] in render.STYLES
      or guarded["options"]["style"] in captions.style_names(), guarded["options"]["style"])
check("the job still has a real length", jobs.LIMITS["max_len"][0] <= guarded["options"]["max_len"]
      <= jobs.LIMITS["max_len"][1], guarded["options"]["max_len"])

# --- the sound asked for is one that really exists ------------------------
print("a sound named on a job")
check("a mood that exists is kept", jobs.clean_options({"sound": "funny"}).get("sound") == "funny", "funny")
check("a mood PeakCut cannot play becomes no sound", jobs.clean_options({"sound": "nope"}).get("sound") == "", "nope")
check("an empty word is no sound", jobs.clean_options({"sound": ""}).get("sound") == "", "")
check("a music bed is accepted too", jobs.clean_options({"sound": "chill"}).get("sound") == "chill", "chill")

# --- the hook words reach the prompt the AI is asked ----------------------
print("the hook note in the prompt")
fresh()
brand.save("u_local", {"hook_words": "start with a question"})
with ctx.as_user("u_local"):
    hooked = jobs.create({"type": "file", "path": "/nowhere.mp4", "name": "hooked"}, {}, enqueue=False)
said = jobs._hook_words(hooked)
check("the job can read the hook words", said == "start with a question", said)
from studio import brain  # noqa: E402

rules = brain._rules(15, 60, "<transcript>hello</transcript>", said)
check("the rules carry the note", "start with a question" in rules, rules[-400:])
check("the note calls itself style, not an instruction", "never an instruction" in rules, "")
check("a job with no note gets no extra line",
      "The person asked for the hooks" not in brain._rules(15, 60, "x", ""), "")
check("the note cannot close the tag", "<" not in brain._hook_note("<script>"), brain._hook_note("<script>"))

# --- the brand's colours reach the renderer ------------------------------
print("the brand document handed to the renderer")
kwargs = jobs._brand_kwargs(hooked)
check("the renderer is given a brand", isinstance(kwargs.get("brand"), dict), type(kwargs.get("brand")))
check("it is this person's brand", kwargs.get("brand", {}).get("hook_words") == "start with a question",
      kwargs.get("brand", {}).get("hook_words"))
check("a job with no owner still gets a document", isinstance(jobs._brand_kwargs({"user": ""}).get("brand"), dict), "")

# --- the face reaches the caption file, for a house look too -------------
# The three house looks (bounce/hype/clean) used to ignore the brand's font entirely: the picker changed, the
# preview changed, and every bounce clip kept its own face. That is the "font controls are not reliable" complaint,
# so this section builds a real caption file and reads the face out of it.
print("the face the person picked reaches the caption file")
from studio import render  # noqa: E402

WORDS = [{"w": w, "s": 0.4 * i, "e": 0.3 + 0.4 * i} for i, w in enumerate("one two three four".split())]


def face_of(doc, look="clean"):
    """The font name inside the built .ass for a house look, which is what ffmpeg will actually draw with."""
    text = render.build_ass(WORDS, 0.0, 2.0, "", look, [], 300, 1380, brand=doc)
    line = [x for x in text.splitlines() if x.startswith("Style: Cap")]
    return line[0].split(",")[1] if line else ""


untouched = brand.normalise({})
check("an untouched brand keeps the look's own face", face_of(untouched) == render.STYLES["clean"]["font"],
      face_of(untouched))
by_family = brand.normalise({"font": "Bangers"})
check("a family name reaches the caption file", face_of(by_family) == "Bangers", face_of(by_family))
by_stem = brand.normalise({"font": "Bangers-Regular"})
check("a file name reaches the same face", face_of(by_stem) == "Bangers", face_of(by_stem))
with_look = brand.normalise({"style": "hormozi", "font": "Montserrat ExtraBold"})
check("a look plus a font keeps the font", face_of(with_look) == "Montserrat ExtraBold", face_of(with_look))
check("a newer look still takes the font too",
      render.build_ass(WORDS, 0.0, 2.0, "", "beast", [], 300, 1380, brand=with_look).count("Montserrat ExtraBold") > 0, "")

print()
print(f"All checks passed. {ok} ok" if not bad else f"{bad} check(s) failed, {ok} ok")
sys.exit(1 if bad else 0)
