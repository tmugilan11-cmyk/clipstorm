"""The judge picks the moment a stranger would stop for, not the tidy paragraph.

No AI is called here: the two scouts and the critic are stood in for, so what is checked is everything the
judge does around them - what it shows them, how two finds of one moment become one, how the critic's marks
become a score, that a "skip" can never be made into a clip by a generous number, and that a video gives
fewer clips rather than weak ones.
"""
import os as _os; _os.environ.setdefault("PEAKCUT_JUDGE_WEB", "0")
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio import brain, judge, trends

FAILED = []


def check(name, ok, why=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({why})"))
    if not ok:
        FAILED.append(name)


def talk(start, text, gap=0.3):
    """Words spoken one after another from `start`, a sentence per call."""
    out, t = [], start
    for w in text.split():
        out.append({"w": w, "s": round(t, 2), "e": round(t + 0.25, 2)})
        t += gap
    return out


def main():
    words = (talk(0, "okay so today we are going to drive to the shop and buy some clothes.")
             + talk(20, "chat which door do I pick the middle one okay here we go.")
             + talk(31, "oh no it is the wrong one you liars you set me up.")
             + talk(40, "I am never listening to chat again that was crazy.")
             + talk(60, "anyway let me check the map and see where the next mission is."))
    z = np.zeros(80, dtype=np.float32)
    z[31:36] = 3.2                                    # he shouts when the trap springs

    # ---- what the judge is shown
    lines = judge.lines_of(words, z)
    shown = judge.fmt(lines)
    check("a loud line is marked", "(LOUD) oh no" in shown, shown)
    check("silence before a line is marked", "(PAUSE" in shown, shown)
    inside = judge.fmt(lines, (20, 44))
    check("the critic sees which lines are in the clip", ">> [20.0]" in inside and "   [0.0]" in inside, inside)
    check("the taste names trolling and reactions first", "Trolling" in judge.TASTE and "caught off guard" in judge.TASTE)
    check("the taste says what a boring clip is", "If nobody reacts, there is no clip" in judge.TASTE)

    # ---- the score is made from the critic's marks
    great = {"hook_score": 9, "payoff": 10, "emotion": 10, "share": 9, "standalone": 8, "overall": 94, "verdict": "post"}
    dull = {"hook_score": 3, "payoff": 2, "emotion": 1, "share": 1, "standalone": 6, "overall": 30, "verdict": "skip"}
    liar = {"hook_score": 10, "payoff": 10, "emotion": 10, "share": 10, "standalone": 10, "overall": 100, "verdict": "skip"}
    check("a great clip scores high", judge.final_score(great) >= 90, judge.final_score(great))
    check("a dull clip scores low", judge.final_score(dull) <= 35, judge.final_score(dull))
    check("a clip the critic said skip to can never pass", judge.final_score(liar) <= judge.SKIP_CAP, judge.final_score(liar))
    check("junk marks do not crash the score", judge.final_score({"overall": "lots", "verdict": None}) == 0)

    # ---- two finds of one moment are one candidate
    merged = judge._merge([{"start": 20, "end": 44, "score": 80, "hook": "A"}, {"start": 22, "end": 43, "score": 70, "hook": "B"},
                           {"start": 60, "end": 75, "score": 50, "hook": "C"}, {"start": "x", "end": 3}], 15)
    check("the same moment found twice is kept once", len(merged) == 2, merged)
    check("and remembered as found by both", merged[0].get("seen") == 2 and merged[0]["hook"] == "A", merged[0])

    # ---- the whole judge, with the AI stood in for
    asked = []

    def fake(prompt, schema=None, purpose="AI call", timeout=None):
        asked.append((purpose, prompt))
        if "reader" in purpose:
            return [{"who": "Speed, alone, talking to his chat", "situation": "He lets chat choose a door.",
                     "voices": ["[20-30] 'you' is the chat"], "timeline": ["[31] the door is a trap and he blames chat"],
                     "refs": ["the fog"], "look_up": ["the fog is coming meme"]}], "m", 50
        if "scout" in purpose:
            if "the talk" in purpose:
                return [{"start": 0, "end": 18, "score": 85, "hook": "SHOPPING TRIP", "title": "t", "description": "d",
                         "hashtags": [], "reason": "tidy sentences"},
                        {"start": 20, "end": 44, "score": 80, "hook": "WRONG DOOR", "title": "t", "description": "d",
                         "hashtags": [], "reason": "chat tricks him"}], "m", 100
            if "the lines" in purpose:
                return [], "m", 100
            return [{"start": 21, "end": 43, "score": 75, "hook": "HE GOT SET UP", "title": "t", "description": "d",
                     "hashtags": [], "reason": "he shouts"}], "m", 100
        # the critic: the troll is great, the shopping trip is boring
        out = []
        for i in (1, 2):
            block = prompt.split(f"=== candidate {i}")[1].split("=== candidate")[0]
            if "WRONG DOOR" in block or "HE GOT SET UP" in block:
                out.append(dict(great, id=i, start=20.0, end=44.0, kind="troll", hook="CHAT SET HIM UP", title="Chat set him up",
                                why="Chat tricks him and he explodes."))
            else:
                out.append(dict(dull, id=i, start=0.0, end=18.0, kind="other", hook="SHOPPING", title="x", why="Nothing happens."))
        return out, "m", 200

    real = brain.ask_ai
    real_trends = trends.lines
    real_web = (judge.web.search, judge.web.top_clips)
    brain.ask_ai = fake
    trends.lines = lambda: ["The Fog Is Coming"]
    judge.web.search = lambda q, n=4: [{"title": "The Fog", "snippet": "A meme about fog rolling in."}]
    judge.web.top_clips = lambda name, game="", n=12: [{"title": "Speed gets jumpscared", "views": 24_100_000, "seconds": 35}]
    try:
        clips, tokens, model = judge.pick(words, z, 0.0, start=0, end=80, title="GTA", uploader="Speed", n=2)
        purposes = [p for p, _ in asked]
        check("a reader, three scouts and two critics are asked", sorted(purposes) == [
            "Video: critic (the editor)", "Video: critic (the viewer)", "Video: reader", "Video: scout (the lines)",
            "Video: scout (the reactions)", "Video: scout (the talk)"], purposes)
        check("the reader goes first", purposes[0] == "Video: reader", purposes[:2])
        reader = asked[0][1]
        check("the reader is told there are no speaker labels", "NO speaker labels" in reader and "look_up" in reader)
        later = [pr for p, pr in asked if "reader" not in p]
        check("everyone after the reader knows who is talking and what is going on",
              all("WHAT IS GOING ON HERE" in pr and "'you' is the chat" in pr and "the door is a trap" in pr for pr in later))
        check("what could not be placed was looked up on the web", all("A meme about fog rolling in." in pr for pr in later))
        check("real clips of the streamer are shown as taste, with their views",
              all('24.1M views, 35s: "Speed gets jumpscared"' in pr for pr in later))
        check("the two critics are different people", any("You are nineteen" in pr for p, pr in asked if "viewer" in p)
              and any("thousands of streamer clips" in pr for p, pr in asked if "editor" in p))
        check("the scouts are told what is trending", all("The Fog Is Coming" in pr for p, pr in asked if "scout" in p))
        check("every scout and critic is told what the marks mean",
              all("(LOUD) the streamer was far louder" in pr and "(PAUSE n)" in pr for p, pr in asked), [p for p, _ in asked])
        critic = next(pr for p, pr in asked if "critic" in p)
        check("the critic is shown how loud the clip was", "L: " in critic and "+3.2" in critic, critic[-400:])
        check("the critic is told when both scouts agree", "both scouts picked this" in critic)
        check("the best clip comes first", bool(clips) and clips[0]["hook"] == "CHAT SET HIM UP", [c["hook"] for c in clips])
        check("its score is the critic's, not the scout's", clips[0]["score"] >= 90, clips[0]["score"])
        check("its kind is one the app knows", clips[0]["category"] == "funny", clips[0]["category"])
        check("the marks travel with the clip", clips[0].get("rubric", {}).get("emotion") == 10 and clips[0]["rubric"]["scouts"] == 2
              and clips[0]["rubric"]["critics"] == 2, clips[0].get("rubric"))
        check("the boring one is scored as boring", any(c["score"] <= 35 for c in clips), [c["score"] for c in clips])
        check("tokens are added up", tokens == 750, tokens)

        # what the person asked for, in their own words, reaches every scout and critic
        asked.clear()
        judge.pick(words, z, 0.0, start=0, end=80, title="GTA", uploader="Speed", n=2, focus="trolling other streamers")
        check("the person's own request reaches every scout and critic",
              all('"trolling other streamers"' in pr for p, pr in asked if "reader" not in p) and len(asked) == 6, len(asked))

        # two critics as one: the numbers are averaged, and one generous critic alone does not make a clip
        both = judge.together(dict(great, start=1, end=2), dict(dull, start=3, end=4))
        check("two critics' marks are averaged", both["overall"] == 62 and both["critics"] == 2, both)
        check("one yes and one no on a middling clip is a no", both["verdict"] == "skip", both)
        check("the cut comes from the critic who liked it more", both["start"] == 1, both)
        fine = dict(great, overall=78, verdict="skip")
        check("one yes with a strong average is a yes", judge.together(great, fine)["verdict"] == "post")
        check("one critic alone still counts", judge.together(None, great)["critics"] == 1 and judge.together(None, None) is None)

        # a video gives fewer clips rather than weak ones
        db = np.full(80, -30.0, dtype=np.float32)
        db[31:36] = -5.0
        got, info = brain.find_clips(words, db, 80.0, "GTA", "Speed", max_clips=6)
        check("a video keeps the strong clip and drops the weak one", [c["hook"] for c in got] == ["CHAT SET HIM UP"],
              [(c["hook"], c["score"]) for c in got])
        check("and says a weaker moment was left out", "left out" in info.get("note", ""), info)
        got, info = brain.find_clips(words, db, 80.0, "GTA", "Speed", max_clips=6, min_score=0)
        check("a bar of zero keeps everything", len(got) == 2, len(got))

        # a critic that edits the cut outside what it was shown is not believed
        def wild(prompt, schema=None, purpose="AI call", timeout=None):
            if "scout" in purpose:
                return fake(prompt, schema, purpose, timeout)
            return [dict(great, id=1, start=900.0, end=990.0, kind="troll", hook="X", why="y"),
                    dict(great, id=2, start=900.0, end=990.0, kind="troll", hook="X", why="y")], "m", 1
        brain.ask_ai = wild
        clips, _, _ = judge.pick(words, z, 0.0, start=0, end=80, n=2)
        check("a cut outside the transcript is refused", all(c["end"] <= 80.5 for c in clips), [(c["start"], c["end"]) for c in clips])

        # the critic not answering leaves the scouts' finds, marked down
        def deaf(prompt, schema=None, purpose="AI call", timeout=None):
            if "scout" in purpose:
                return fake(prompt, schema, purpose, timeout)
            raise RuntimeError("timed out")
        brain.ask_ai = deaf
        clips, _, _ = judge.pick(words, z, 0.0, start=0, end=80, n=2)
        check("without the critic the scouts' finds stand, marked down", bool(clips) and max(c["score"] for c in clips) <= 70,
              [c["score"] for c in clips])

        # both scouts failing is an error the caller hears about
        def dead(prompt, schema=None, purpose="AI call", timeout=None):
            raise RuntimeError("no AI")
        brain.ask_ai = dead
        try:
            judge.pick(words, z, 0.0, start=0, end=80, n=2)
            check("no AI at all is reported", False, "no error raised")
        except RuntimeError:
            check("no AI at all is reported", True)
    finally:
        brain.ask_ai = real
        trends.lines = real_trends
        judge.web.search, judge.web.top_clips = real_web

    print()
    if FAILED:
        print(f"{len(FAILED)} failed: " + ", ".join(FAILED))
        raise SystemExit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
