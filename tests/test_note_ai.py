"""The "Change it in words" box is read by the AI, and every new title is written in one style.

"new title" (no words after it) used to come back "Nothing in that note is something this editor can change": the
rules only knew a few sentence shapes. No network: the AI is a stand-in that checks what it was shown."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio import ai, brain, config, edit, edit_ai, usage

FAILED = []


def check(name, ok, why=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({why})"))
    if not ok:
        FAILED.append(name)


CLIP = {"start": 100.0, "end": 130.0, "hook": "IT WAS KSI", "title": "Speed Finds the GTA Alien and It's KSI",
        "style": "bounce", "layout": "crop", "captions": True, "description": "d", "hashtags": ["GTA6"]}
WORDS = [{"w": "Oh", "s": 99.0, "e": 99.4}, {"w": "KSI.", "s": 110.0, "e": 110.6},
         {"w": "forehead.", "s": 125.0, "e": 125.8}, {"w": "picture.", "s": 140.0, "e": 140.9}]


def main():
    seen = []
    answer = [{}]
    real = (ai.call, ai.models, config.ai_ready, usage.record)
    ai.models, config.ai_ready, usage.record = (lambda: ["m"]), (lambda: True), (lambda *a, **k: None)
    ai.call = lambda model, prompt, schema, timeout=None: seen.append((prompt, schema)) or (answer[0], 1, 1)
    try:
        answer[0] = {"title": "Speed finds an alien, thinks it's KSI, and roasts its forehead! \U0001F62D",
                     "said": "Wrote a new title."}
        got = edit_ai.understand("new title", CLIP, WORDS)
        prompt, schema = seen[-1]
        check("a note with no words after 'new title' gets a title", got["change"].get("title", "").startswith("Speed finds"), got)
        check("the AI is told the title style", brain.TITLE_STYLE in prompt)
        check("the AI is shown the talk around the clip with its times", "[110.00]" in prompt and "[140.00]" in prompt, prompt[-800:])
        check("the clip's own stretch is marked", prompt.split("<talk>")[1].count(">>>") == 2)
        check("no schema is sent (the prompt names its object)", schema is None)
        check("the emoji is kept", got["change"]["title"].endswith("\U0001F62D"), got["change"]["title"])
        new = edit.apply(CLIP, got["change"])
        check("what changed is said from the clip itself", edit_ai.describe(CLIP, new).startswith("new title:"), edit_ai.describe(CLIP, new))
        check("a new title does not need a re-make", not edit_ai.needs_render(CLIP, new))

        answer[0] = {"end": "125.8", "layout": "stack", "style": "neon-made-up", "said": "x"}
        got = edit_ai.understand("end after forehead, facecam on top, neon captions", CLIP, WORDS)
        new = edit.apply(CLIP, got["change"])
        check("a time in words moves the cut", abs(new["end"] - 125.8) < 1.0, new.get("end"))
        check("a layout in words is put on", new["layout"] == "stack", new.get("layout"))
        check("a look the renderer does not have is dropped", new["style"] == "bounce", new.get("style"))
        check("a moved cut needs a re-make", edit_ai.needs_render(CLIP, new))

        answer[0] = {"said": "This editor cannot add explosion effects."}
        got = edit_ai.understand("add explosion effects", CLIP, WORDS)
        check("a note it cannot do changes nothing and says why", got["change"] == {} and "cannot" in got["said"], got)

        answer[0] = {"start": None, "hook": "kSi it was", "said": "x"}
        got = edit_ai.understand("hook: ksi it was", CLIP, WORDS)
        check("the hook is capitals and a null field is ignored", got["change"] == {"hook": "KSI IT WAS"}, got)

        config.ai_ready = lambda: False
        try:
            edit_ai.understand("new title", CLIP, WORDS)
            check("with no AI set up the rules take over", False)
        except RuntimeError:
            check("with no AI set up the rules take over", True)
    finally:
        ai.call, ai.models, config.ai_ready, usage.record = real

    r = brain._rules(15, 60, "x", None)
    check("the judge writes every new title in that style", brain.TITLE_STYLE in r)
    from studio import judge
    check("so does the critic who writes the posted title",
          any(isinstance(v, str) and brain.TITLE_STYLE in v for v in vars(judge).values()))
    src = (Path(edit_ai.__file__).parent / "api_text.py").read_text(encoding="utf-8")
    check("the note route asks the AI first and keeps the rules as fallback",
          "edit_ai.understand" in src and "edit.parse(note)" in src)
    page = (Path(edit_ai.__file__).parent.parent / "web" / "index.html").read_text(encoding="utf-8")
    check("the page says what changed and whether to re-make", "got.done" in page and "got.render" in page)
    print()
    if FAILED:
        print(f"{len(FAILED)} failed: " + ", ".join(FAILED))
        raise SystemExit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
