"""A name the speech model never heard of is put right in the captions.

Speed said "don't take KSI" and the captions said "don't take care sir" (2026-11-23): the caption tidier was only
shown the video's title, and its guard refused any fix that did not look like the word heard. It is now shown what
the clip is about and the names in the stream, and a fix to one of those names is let through.
No network: the AI is a stand-in."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio import brain

FAILED = []


def check(name, ok, why=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({why})"))
    if not ok:
        FAILED.append(name)


def words(*ws):
    return [{"w": w, "s": float(i), "e": float(i) + 0.5} for i, w in enumerate(ws)]


def main():
    heard = words("hey", "don't", "take", "care", "sir", "no")
    prompts, answer = [], [None]
    real = brain.ask_ai
    brain.ask_ai = lambda prompt, schema=None, purpose="", timeout=None: prompts.append(prompt) or (answer[0], "m", 1)
    try:
        answer[0] = ["Hey,", "don't", "take", "KSI!", "", "No!"]
        got = brain._fix_caption_words(heard, "GTA 6 stream", "en", "He thinks the alien is KSI.", ["KSI", "ET"])
        check("'care sir' becomes KSI", [w["w"] for w in got] == ["Hey,", "don't", "take", "KSI!", "No!"], [w["w"] for w in got])
        check("the name keeps the timing of the first word", got[3]["s"] == 3.0)
        check("the tidier is told what the clip is about", "He thinks the alien is KSI." in prompts[-1])
        check("and the names in the stream", "Names in this stream: KSI, ET" in prompts[-1])

        answer[0] = ["hey", "don't", "take", "pizza", "", "no"]
        got = brain._fix_caption_words(heard, "", "en", "", ["KSI"])
        check("a swap to a word that is not a name is still refused, and its pair is kept",
              [w["w"] for w in got] == ["hey", "don't", "take", "care", "sir", "no"], [w["w"] for w in got])

        answer[0] = ["Hey,", "don't", "take", "KSI", "", "no"]
        got = brain._fix_caption_words(heard, "", "en", "", [])
        check("without being given the name, it is not let through", [w["w"] for w in got][3:5] == ["care", "sir"],
              [w["w"] for w in got])
    finally:
        brain.ask_ai = real

    names = brain.caption_names("Speed finds an alien, thinks it's KSI, then screams 'No, ET'",
                                cast=["IShowSpeed (Speed) - streamer", "Lucia (Lucy/Lucio) - GTA VI protagonist"])
    check("names come from the story's cast and the clip's own words",
          all(n in names for n in ("Speed", "Lucia", "Lucy", "KSI", "ET")), names)
    check("ordinary capitalised words are not names", "The" not in names and "No" not in names, names)
    src = (Path(brain.__file__).parent / "jobs.py").read_text(encoding="utf-8")
    check("a clip's captions are tidied with its story and names", "names=brain.caption_names(about, cast=_cast(job))" in src)
    print()
    if FAILED:
        print(f"{len(FAILED)} failed: " + ", ".join(FAILED))
        raise SystemExit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
