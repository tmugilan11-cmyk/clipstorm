"""The judge picks the moment a stranger would stop for, not the tidy paragraph.

No AI is called here: the reader, the scouts, the critics, the story keeper and the showrunner are stood in
for, so what is checked is everything the judge does around them - what it shows them, how two finds of one
moment become one, how the critics' marks become a score, that a "skip" can never be made into a clip by a
generous number, that a video gives fewer clips rather than weak ones, that the story of the stream reaches
every read, that the setup before a clip is shown and may be pulled in, that the picture is looked at only
when it can be, that the third critic sees only what is still in the running, and that the showrunner drops
a repeat and keeps the scores' meaning.
"""
import os as _os
import tempfile as _tempfile
_os.environ.setdefault("PEAKCUT_JUDGE_WEB", "0")
_os.environ.setdefault("PEAKCUT_JUDGE_VISION", "0")
_os.environ.setdefault("PEAKCUT_DATA", _tempfile.mkdtemp(prefix="pc-judge-"))   # nothing is written to real data
import sys
import threading
import types
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio import ai, brain, config, judge, judge_look, judge_show, judge_story, trends  # noqa: E402

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


def blocks_of(prompt):
    """candidate number -> its block, from a critic's prompt."""
    out = {}
    for part in prompt.split("=== candidate ")[1:]:
        head = part.split(":", 1)[0].split(" ")[0]
        if head.isdigit():
            out[int(head)] = part
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
    check("the taste asks for a hook a stranger understands", "A stranger must" in judge.TASTE)

    # ---- the score is made from the critic's marks
    great = {"hook_score": 9, "payoff": 10, "emotion": 10, "share": 9, "standalone": 8, "overall": 94, "verdict": "post"}
    dull = {"hook_score": 3, "payoff": 2, "emotion": 1, "share": 1, "standalone": 6, "overall": 30, "verdict": "skip"}
    liar = {"hook_score": 10, "payoff": 10, "emotion": 10, "share": 10, "standalone": 10, "overall": 100, "verdict": "skip"}
    check("a great clip scores high", judge.final_score(great) >= 90, judge.final_score(great))
    check("a dull clip scores low", judge.final_score(dull) <= 35, judge.final_score(dull))
    check("a clip the critic said skip to can never pass", judge.final_score(liar) <= judge.SKIP_CAP, judge.final_score(liar))
    check("junk marks do not crash the score", judge.final_score({"overall": "lots", "verdict": None}) == 0)

    # ---- two finds of one moment are one candidate
    merged = judge._merge([{"start": 20, "end": 44, "score": 80, "hook": "A"}, {"start": 22, "end": 43, "score": 70, "hook": "B",
                                                                                  "setup_from": 14},
                           {"start": 60, "end": 75, "score": 50, "hook": "C"}, {"start": "x", "end": 3}], 15)
    check("the same moment found twice is kept once", len(merged) == 2, merged)
    check("and remembered as found by both", merged[0].get("seen") == 2 and merged[0]["hook"] == "A", merged[0])
    check("the earliest setup a scout asked for is kept", merged[0].get("setup_from") == 14, merged[0])

    # ---- the whole judge, with the AI stood in for
    asked = []
    lock = threading.Lock()

    def fake(prompt, schema=None, purpose="AI call", timeout=None):
        with lock:
            asked.append((purpose, prompt))
        if "reader" in purpose:
            return [{"who": "Speed, alone, talking to his chat", "situation": "He lets chat choose a door.",
                     "voices": ["[20-30] 'you' is the chat"], "timeline": ["[31] the door is a trap and he blames chat"],
                     "refs": ["the fog"], "look_up": ["the fog is coming meme"]}], "m", 50
        if "scout" in purpose:
            if "the talk" in purpose:
                return [{"start": 0, "end": 18, "score": 85, "hook": "SHOPPING TRIP", "title": "t", "description": "d",
                         "hashtags": [], "reason": "tidy sentences", "what_happens": "he plans a shopping trip"},
                        {"start": 20, "end": 44, "score": 80, "hook": "WRONG DOOR", "title": "t", "description": "d",
                         "hashtags": [], "reason": "chat tricks him", "what_happens": "chat tricks Speed into the wrong door"}], "m", 100
            if "the lines" in purpose:
                return [], "m", 100
            return [{"start": 21, "end": 43, "score": 75, "hook": "HE GOT SET UP", "title": "t", "description": "d",
                     "hashtags": [], "reason": "he shouts"}], "m", 100
        if "showrunner" in purpose:
            return [], "m", 10
        if "story" in purpose:
            return [{"cast": ["Speed - the streamer"], "jokes": [], "setups": [], "beats": ["[20] he asks chat"],
                     "doing": "picking a door", "earlier": ""}], "m", 30
        # the critics: the troll is great, the shopping trip is boring
        out = []
        for i, block in blocks_of(prompt).items():
            if "WRONG DOOR" in block or "HE GOT SET UP" in block:
                hook = "CHAT SET SPEED UP" if "admin" in purpose else "CHAT SET HIM UP"
                out.append(dict(great, id=i, start=20.0, end=44.0, kind="troll", hook=hook, title="Chat set him up",
                                why="Chat tricks him and he explodes.", what_happens="chat lies to Speed about the door",
                                first_seconds="Speed asks chat which door"))
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
        info = {}
        clips, tokens, model = judge.pick(words, z, 0.0, start=0, end=80, title="GTA", uploader="Speed", n=2, info=info)
        purposes = [p for p, _ in asked]
        check("a reader, three scouts, two critics and the final desk are asked", sorted(purposes) == [
            "Video: critic (the clip-page admin)", "Video: critic (the editor)", "Video: critic (the viewer)",
            "Video: reader", "Video: scout (the lines)", "Video: scout (the reactions)", "Video: scout (the talk)"], purposes)
        check("the calls are counted", info.get("calls") == 7, info)
        check("the reader goes first", purposes[0] == "Video: reader", purposes[:2])
        check("the final desk goes last", purposes[-1] == "Video: critic (the clip-page admin)", purposes[-2:])
        reader = asked[0][1]
        check("the reader is told there are no speaker labels", "NO speaker labels" in reader and "look_up" in reader)
        later = [pr for p, pr in asked if "reader" not in p]
        check("everyone after the reader knows who is talking and what is going on",
              all("WHAT IS GOING ON HERE" in pr and "'you' is the chat" in pr and "the door is a trap" in pr for pr in later))
        check("what could not be placed was looked up on the web", all("A meme about fog rolling in." in pr for pr in later))
        check("real clips of the streamer are shown as taste, with their views",
              all('24.1M views, 35s: "Speed gets jumpscared"' in pr for pr in later))
        check("the critics are different people", any("You are nineteen" in pr for p, pr in asked if "viewer" in p)
              and any("thousands of streamer clips" in pr for p, pr in asked if "editor" in p)
              and any("You run a clip page" in pr for p, pr in asked if "admin" in p))
        check("the scouts are told what is trending", all("The Fog Is Coming" in pr for p, pr in asked if "scout" in p))
        check("the scouts say who does what to whom", all("what_happens" in pr and "setup_from" in pr
                                                          for p, pr in asked if "scout" in p))
        check("every scout and critic is told what the marks mean",
              all("(LOUD) the streamer was far louder" in pr and "(PAUSE n)" in pr for p, pr in asked), [p for p, _ in asked])
        critic = next(pr for p, pr in asked if "editor" in p)
        check("the critic is shown how loud the clip was", "L: " in critic and "+3.2" in critic, critic[-400:])
        check("the critic is told when both scouts agree", "more than one scout picked this" in critic)
        check("the critic thinks before it marks", "first_seconds" in critic and "stranger_needs" in critic)
        check("the critic is told what the scout thinks happens", "chat tricks Speed into the wrong door" in critic)
        viewer = next(pr for p, pr in asked if "viewer" in p)
        e_order = [int(x.split(":")[0].split(" ")[0]) for x in critic.split("=== candidate ")[1:]]
        v_order = [int(x.split(":")[0].split(" ")[0]) for x in viewer.split("=== candidate ")[1:]]
        check("the two critics read the candidates in different orders", e_order == list(reversed(v_order)) and len(e_order) > 1,
              (e_order, v_order))
        admin = next(pr for p, pr in asked if "admin" in p)
        check("the final desk sees only what is still in the running", "SHOPPING TRIP" not in admin and "WRONG DOOR" in admin,
              admin[-600:])
        check("the best clip comes first", bool(clips) and clips[0]["hook"] == "CHAT SET SPEED UP", [c["hook"] for c in clips])
        check("the final desk writes the hook", clips[0]["hook"] == "CHAT SET SPEED UP")
        check("its score is the critics', not the scout's", clips[0]["score"] >= 90, clips[0]["score"])
        check("its kind is one the app knows", clips[0]["category"] == "funny", clips[0]["category"])
        check("the marks travel with the clip", clips[0].get("rubric", {}).get("emotion") == 10 and clips[0]["rubric"]["scouts"] == 2
              and clips[0]["rubric"]["critics"] == 3, clips[0].get("rubric"))
        check("what happens travels with the clip", "chat lies to Speed" in clips[0].get("context", ""), clips[0].get("context"))
        check("the boring one is scored as boring", any(c["score"] <= 35 for c in clips), [c["score"] for c in clips])
        check("tokens are added up", tokens == 950, tokens)

        # what the person asked for, in their own words, reaches every scout and critic
        asked.clear()
        judge.pick(words, z, 0.0, start=0, end=80, title="GTA", uploader="Speed", n=2, focus="trolling other streamers")
        check("the person's own request reaches every scout and critic",
              all('"trolling other streamers"' in pr for p, pr in asked if "reader" not in p) and len(asked) == 7, len(asked))

        # ---- the story of the stream reaches every read
        asked.clear()
        story = judge_story.empty()
        story.update(cast=["Kai - his friend on the call, the quiet voice"], jokes=["[100] chat always lies about doors"],
                     setups=["[200] he swears he will never trust chat -> open"],
                     beats=[{"t": 300.0, "text": "chat sent him into a lake"}, {"t": 2000.0, "text": "he finally trusts chat and wins"}])
        brief = judge_story.brief(story, 1000, 1080)
        check("the story names who is who", "Kai - his friend on the call" in brief and "chat always lies" in brief, brief)
        check("the story says what came just before, in minutes", "min before) chat sent him into a lake" in brief, brief)
        check("a finished video's story says what happens later", "WHAT HAPPENS LATER" in brief and "trusts chat and wins" in brief)
        check("a live stream's story does not", "WHAT HAPPENS LATER" not in judge_story.brief(story, 1000, 1080, later=False))
        check("an empty story adds nothing", judge_story.brief(judge_story.empty(), 0, 10) == "")
        judge.pick(words, z, 0.0, start=0, end=80, title="GTA", uploader="Speed", n=2, story=brief)
        check("the reader, every scout and every critic are told the story",
              all("Kai - his friend on the call" in pr for p, pr in asked) and len(asked) == 7, len(asked))

        # rolling story: a stretch read into it
        asked.clear()

        def keeper(prompt, schema=None, purpose="AI call", timeout=None):
            asked.append((purpose, prompt))
            return [{"cast": ["Speed - the streamer", "Kai - friend on the call"], "jokes": ["[31] chat lies about doors"],
                     "setups": ["[20] chat picks a door -> [31] it is a trap"],
                     "beats": ["[31] chat tricks Speed", "[999] something outside the part", "no second here"],
                     "doing": "choosing doors", "earlier": "He started the stream shopping."}], "m", 40
        brain.ask_ai = keeper
        new, spent = judge_story.advance(story, words, 0, 80, "GTA", "Speed", live=True)
        check("the story keeper is shown the story so far and the new part",
              "THE STORY SO FAR" in asked[0][1] and "chat sent him into a lake" in asked[0][1] and "[31.0]" in asked[0][1])
        check("the story moves on", new["upto"] == 80 and "Kai - friend on the call" in new["cast"] and spent == 40, new)
        check("a beat's second stays inside the part it was written about", all(0 <= b["t"] <= 2000 for b in new["beats"])
              and any(b["t"] == 80 and "outside" in b["text"] for b in new["beats"]), new["beats"])
        many = dict(new, beats=[{"t": float(i), "text": f"beat {i}"} for i in range(40)], whole=False)
        new2, _ = judge_story.advance(many, words, 0, 80, live=True)
        check("a live story is kept short", len(new2["beats"]) <= judge_story.MOST["beats"], len(new2["beats"]))
        check("and saved short", len(judge_story.short(many)["beats"]) <= judge_story.MOST["beats"])
        moved = judge_story.carried(new)
        check("a story carried over a restart keeps no seconds from the old clock",
              moved["beats"] == [] and moved["upto"] == 0.0 and "[31]" not in " ".join(moved["setups"] + moved["jokes"])
              and "chat tricks Speed" in moved["earlier"], moved)

        def broken(prompt, schema=None, purpose="AI call", timeout=None):
            raise RuntimeError("timed out")
        brain.ask_ai = broken
        same, spent = judge_story.advance(new, words, 0, 80)
        check("a story keeper that does not answer leaves the story as it was", same == new and spent == 0)

        # the whole story of a finished video: parts read at once, then joined
        asked.clear()
        long_words = [dict(w, s=w["s"] + k * 700, e=w["e"] + k * 700) for k in range(3) for w in words]

        def parts(prompt, schema=None, purpose="AI call", timeout=None):
            with lock:
                asked.append((purpose, prompt))
            if "joined" in purpose:
                return [{"cast": ["Speed - streamer"], "jokes": ["doors"], "setups": ["[20] the bet -> [1431] he wins it"],
                         "arc": "He loses to chat all night, then wins."}], "m", 70
            a = float(prompt.split("covers seconds ")[1].split(" ")[0])
            return [{"cast": ["Speed"], "jokes": [], "setups": [], "beats": [f"[{a + 31:.0f}] part at {a:.0f}"],
                     "doing": "x", "earlier": ""}], "m", 20
        brain.ask_ai = parts
        whole, spent = judge_story.build(long_words, "GTA", "Speed", chunk=700)
        names = sorted(p for p, _ in asked)
        check("a whole video is read in parts and joined", names.count("Video: story (a part)") == 3
              and names.count("Video: story (joined)") == 1 and spent == 3 * 20 + 70, names)
        check("the joined story links a setup to its payoff", "he wins it" in " ".join(whole["setups"]) and whole["whole"])
        mid = judge_story.brief(whole, 700, 780)
        check("a stretch of it knows what came before and what comes later",
              "part at 0" in mid and "WHAT HAPPENS LATER" in mid and "part at 1400" in mid, mid)

        # find_clips keeps the story in the job's folder between blocks
        brain.ask_ai = fake
        asked.clear()
        memory = Path(_os.environ["PEAKCUT_DATA"]) / "story.json"
        db = np.full(80, -30.0, dtype=np.float32)
        db[31:36] = -5.0
        brain.find_clips(words, db, 80.0, "GTA", "Speed", max_clips=6, memory=memory, at=600.0)
        kept = judge_story.load(memory)
        check("a block's story is read once and kept in the job's folder", kept is not None and kept["upto"] >= 660
              and [p for p, _ in asked].count("Video: story") == 1, ([p for p, _ in asked], kept))
        stories = sum(1 for p, pr in asked if "story" not in p and "THE STORY SO FAR" in pr and "Speed - the streamer" in pr)
        check("and every read of the block is told it", stories >= 7, stories)
        asked.clear()
        brain.find_clips(words, db, 80.0, "GTA", "Speed", max_clips=6, memory=memory, at=600.0)
        check("a block already in the story is not read again", "Video: story" not in [p for p, _ in asked])

        # ---- setup and payoff: the critic sees what came before, and may pull it in
        brain.ask_ai = fake
        setup_words = (talk(0, "chat I bet you ten dollars the middle door is safe I promise you.")
                       + talk(50, "okay here we go the middle door.")
                       + talk(70, "oh no it is the wrong one you liars you set me up.")
                       + talk(80, "I lost the bet chat that was crazy."))
        zz = np.zeros(120, dtype=np.float32)
        zz[70:76] = 3.0

        def pulled(prompt, schema=None, purpose="AI call", timeout=None):
            with lock:
                asked.append((purpose, prompt))
            if "scout" in purpose:
                return [{"start": 50, "end": 85, "score": 80, "hook": "WRONG DOOR", "title": "t", "description": "d",
                         "hashtags": [], "reason": "trap"}], "m", 1
            if "reader" in purpose:
                return [], "m", 1
            return [dict(great, id=1, start=0.0, end=85.0, kind="troll", hook="HE LOST THE BET", why="the bet pays off")], "m", 1
        asked.clear()
        brain.ask_ai = pulled
        got, _, _ = judge.pick(setup_words, zz, 0.0, start=0, end=120, n=1, min_len=15, max_len=60)
        crit = next(pr for p, pr in asked if "editor" in p)
        check("the critic is shown the setup a minute before the clip", "[0.0] chat I bet you ten dollars" in crit
              and "EARLIER into the lines shown before" in crit.replace("\n  ", " "), crit[:200])
        check("a setup pulled in keeps the payoff: the clip is cut from the front", bool(got) and got[0]["end"] >= 82
              and got[0]["end"] - got[0]["start"] <= 61, [(c["start"], c["end"]) for c in got])

        # ---- the third critic: a repeat of a clip already made is held back
        brain.ask_ai = fake
        asked.clear()

        def repeat(prompt, schema=None, purpose="AI call", timeout=None):
            out, m, t = fake(prompt, schema, purpose, timeout)
            if "admin" in purpose:
                out = [dict(r, same_as_made="Chat set him up!") for r in out]
            return out, m, t
        brain.ask_ai = repeat
        got, _, _ = judge.pick(words, z, 0.0, start=0, end=80, title="GTA", uploader="Speed", n=2,
                               made=[{"hook": "CHAT SET HIM UP", "title": "Chat lies about the door and he falls for it"}])
        admin = next(pr for p, pr in asked if "admin" in p)
        check("the final desk is shown the clips already made", "CLIPS ALREADY MADE" in admin and '"CHAT SET HIM UP"' in admin)
        check("the editor and the viewer are not", all("CLIPS ALREADY MADE" not in pr for p, pr in asked if "admin" not in p))
        best = max(got, key=lambda c: c["score"])
        check("a repeat of a made clip cannot pass", best["score"] <= judge.SKIP_CAP and "Repeats a clip" in best["reason"],
              (best["score"], best["reason"]))

        asked.clear()
        got, _, _ = judge.pick(words, z, 0.0, start=0, end=80, title="GTA", uploader="Speed", n=2,
                               made=[{"hook": "CHAT SET HIM UP", "title": "Bigfoot chases him through the woods"}])
        best = max(got, key=lambda c: c["score"])
        check("a repeat the two clips do not bear out is not believed", best["score"] >= 90 and "Repeats" not in best["reason"],
              (best["score"], best["reason"]))

        # three critics as one: most of them saying post is enough when the average is decent
        mid_yes = dict(great, overall=70)
        check("two of three critics saying post with a decent average is a post",
              judge.together(mid_yes, mid_yes, dict(dull, overall=60))["verdict"] == "post")
        check("one of three is not", judge.together(mid_yes, dict(dull, overall=60), dict(dull, overall=60))["verdict"] == "skip")

        # ---- your own results: what worked on this channel
        brain.ask_ai = fake
        real_own = judge.own_results
        try:
            judge.own_results = types.SimpleNamespace(taste_lines=lambda creator=None, n=12: [
                f'Your clip "Chat lied" (troll, 34 s) got 120k views, 81% watched - did well (for {creator})'])
            asked.clear()
            judge.pick(words, z, 0.0, start=0, end=80, title="GTA", uploader="Speed", n=2, creator="c1")
            check("the channel's own results reach the scouts and critics",
                  all("WHAT WORKED ON THIS CHANNEL" in pr and "120k views" in pr and "(for c1)" in pr
                      for p, pr in asked if "reader" not in p))
            check("but not the reader", all("WHAT WORKED" not in pr for p, pr in asked if "reader" in p))
            judge.own_results = types.SimpleNamespace(taste_lines=lambda creator=None, n=12: [])
            asked.clear()
            judge.pick(words, z, 0.0, start=0, end=80, n=2)
            check("no results add nothing", all("WHAT WORKED" not in pr for p, pr in asked))

            def boom(creator=None, n=12):
                raise ValueError("broken")
            judge.own_results = types.SimpleNamespace(taste_lines=boom)
            asked.clear()
            clips_b, _, _ = judge.pick(words, z, 0.0, start=0, end=80, n=2)
            check("broken results never stop the judge", bool(clips_b) and all("WHAT WORKED" not in pr for p, pr in asked))
        finally:
            judge.own_results = real_own

        # ---- the picture: frames are looked at only when there is somewhere to take them from
        brain.ask_ai = fake
        real_look = judge_look.look
        seen_cands = []

        def fake_look(cands, where, z=None, z_base=0.0, timeout=None, log=None, names=()):
            seen_cands.append(len(cands))
            return {1: '[31] bottom-centre: "You will never find the alien"'}, 0, "text"
        judge_look.look = fake_look
        try:
            asked.clear()
            info = {}
            got, _, _ = judge.pick(words, z, 0.0, start=0, end=80, uploader="Speed", n=2, frames=lambda t: ("x.ts", t), info=info)
            crit = next(pr for p, pr in asked if "editor" in p)
            check("the critics are told what was on screen", "ON SCREEN:" in crit and "never find the alien" in crit
                  and "game's" in crit, crit[-500:])
            check("how the picture was looked at is said", info.get("look") == "text", info)
            asked.clear()
            judge.pick(words, z, 0.0, start=0, end=80, n=2)
            check("no frames, no look", len(seen_cands) == 1 and all("ON SCREEN:" not in pr for p, pr in asked))
        finally:
            judge_look.look = real_look
        check("the look is off in the tests", not judge_look.enabled()
              and judge_look.look([{"start": 0, "end": 10}], lambda t: ("x", t)) == ({}, 0, ""))
        rows = [(31.0, [(0.3, 0.9, 0.7, 0.95, "You will never find the alien, Speed"),
                        (0.8, 0.05, 0.99, 0.1, "chat says W SPEED"), (0.0, 0.9, 0.2, 0.95, "@someone donated $5"),
                        (0.3, 0.92, 0.7, 0.98, "ISHOWSPEEDSUI ISHOWSPEED"), (0.1, 0.1, 0.2, 0.15, "12,345")])]
        said = judge_look.screen_text(rows, names=("IShowSpeed",))
        check("subtitles come first, then other text, then chat", said.index("never find the alien") < said.index("donated")
              < said.index("W SPEED"), said)
        check("the channel's own overlay and bare numbers are left out", "ISHOWSPEEDSUI" not in said and "12,345" not in said, said)
        check("frames are taken at the start, the loud moments and the end",
              judge_look.moments({"start": 20.0, "end": 44.0}, z) [:1] == [20.8]
              and any(31 <= t <= 36 for t in judge_look.moments({"start": 20.0, "end": 44.0}, z))
              and judge_look.moments({"start": 20.0, "end": 44.0}, z)[-1] == 43.0, judge_look.moments({"start": 20.0, "end": 44.0}, z))

        # asked once whether the AI can see pictures, and remembered
        real_see = (judge_look.enabled, ai.ready, ai.see, ai.models, ai.base_url, config.DATA_DIR)
        looks = []
        try:
            judge_look.enabled = lambda: True
            ai.ready = lambda: True
            ai.models = lambda: ["text-only-model"]
            ai.base_url = lambda: "http://127.0.0.1:9/v1"
            config.DATA_DIR = Path(_tempfile.mkdtemp(prefix="pc-look-"))

            def blind(prompt, image, timeout=None):
                looks.append(1)
                raise RuntimeError('HTTP 503 {"error": "model_unavailable"}')
            ai.see = blind
            first, second = judge_look.can_see(), judge_look.can_see()
            check("a model that refuses pictures is asked once and remembered", first is False and second is False
                  and len(looks) == 1 and (config.DATA_DIR / judge_look.PROBE_FILE).exists(), looks)

            def offline(prompt, image, timeout=None):
                looks.append(1)
                raise RuntimeError("connection timed out")
            ai.models = lambda: ["another-model"]
            ai.see = offline
            judge_look.can_see()
            judge_look.can_see()
            check("a service that cannot be reached is not remembered as blind", len(looks) == 3, len(looks))
            ai.models = lambda: ["seeing-model"]
            ai.see = lambda prompt, image, timeout=None: ("Red.", 0, 0)
            check("a model that sees pictures is remembered as one", judge_look.can_see() is True)
        finally:
            judge_look.enabled, ai.ready, ai.see, ai.models, ai.base_url, config.DATA_DIR = real_see

        # ---- the showrunner: finalists of a whole video side by side
        def show(prompt, schema=None, purpose="AI call", timeout=None):
            asked.append((purpose, prompt))
            return [{"id": "F1", "same_as": "", "rank": 2, "score": 70, "why": "fine"},
                    {"id": "F2", "same_as": "", "rank": 1, "score": 99, "why": "the best of the night"},
                    {"id": "F3", "same_as": "F2", "rank": 3, "score": 80, "why": "the same lie again"},
                    {"id": "F4", "same_as": "M1", "rank": 4, "score": 75, "why": "already made"}], "m", 33
        brain.ask_ai = show
        asked.clear()
        fins = [{"start": 0, "end": 20, "score": 88, "hook": "A", "rubric": {"verdict": "post"}, "context": "he sings badly"},
                {"start": 30, "end": 50, "score": 84, "hook": "B", "rubric": {"verdict": "post"},
                 "context": "chat lies about the door trap"},
                {"start": 60, "end": 80, "score": 82, "hook": "C", "rubric": {"verdict": "post"},
                 "context": "chat lies about the door again"},
                {"start": 90, "end": 110, "score": 58, "hook": "D", "rubric": {"verdict": "skip"},
                 "context": "the bigfoot chase in the woods"}]
        kept, dropped, spent = judge_show.rank(fins, made=[{"hook": "OLD", "title": "Bigfoot chase through the woods", "score": 90}],
                                               title="GTA")
        check("the showrunner sees every finalist and the clips already made", "F4" in asked[0][1] and "M1: score 90" in asked[0][1])
        check("a finalist that repeats a better one or a made clip is dropped",
              [c["hook"] for c in dropped] == ["C", "D"] and spent == 33, [c["hook"] for c in dropped])
        check("the rest are in the showrunner's order", [c["hook"] for c in kept] == ["B", "A"], [c["hook"] for c in kept])
        check("a score moves only a little, and the order is the order of the scores",
              kept[0]["score"] == 84 + judge_show.UP and kept[1]["score"] <= kept[0]["score"] and kept[1]["score"] >= 88 - judge_show.DOWN,
              [c["score"] for c in kept])
        unlike = [dict(c, context=t) for c, t in zip(fins, ("he sings", "a car flips", "the police arrive", "a dog barks"))]
        kept2, dropped2, _ = judge_show.rank(unlike, made=[{"hook": "OLD", "title": "Bigfoot chase", "score": 90}])
        check("a repeat the clips do not bear out is not dropped", not dropped2 and len(kept2) == 4, [c["hook"] for c in dropped2])
        one_kept, _, spent = judge_show.rank(fins[:1])
        check("one finalist and nothing made: nothing to compare", spent == 0 and len(one_kept) == 1)
        skip_up, _, _ = judge_show.rank([dict(fins[3], hook="E"), dict(fins[0], hook="F")])
        check("a skip stays under the cap whatever the showrunner says",
              all(c["score"] <= judge.SKIP_CAP for c in skip_up if c["rubric"].get("verdict") == "skip"), skip_up)
        brain.ask_ai = broken
        same_fins, dropped, spent = judge_show.rank(fins)
        check("a showrunner that does not answer leaves the finalists", len(same_fins) == 4 and not dropped and spent == 0)

        # ---- a video gives fewer clips rather than weak ones
        brain.ask_ai = fake
        db = np.full(80, -30.0, dtype=np.float32)
        db[31:36] = -5.0
        got, info = brain.find_clips(words, db, 80.0, "GTA", "Speed", max_clips=6)
        check("a video keeps the strong clip and drops the weak one", [c["hook"] for c in got] == ["CHAT SET SPEED UP"],
              [(c["hook"], c["score"]) for c in got])
        check("and says a weaker moment was left out", "left out" in info.get("note", ""), info)
        asked.clear()
        got, info = brain.find_clips(words, db, 80.0, "GTA", "Speed", max_clips=6, min_score=0)
        check("a bar of zero keeps everything", len(got) == 2, len(got))
        check("and the finalists are compared by the showrunner", "Video: showrunner" in [p for p, _ in asked])

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

        # ---- a live recording: frames come from its buffer pieces, and a restart keeps the story
        from studio import live
        tmp = Path(_tempfile.mkdtemp(prefix="pc-live-"))
        (tmp / "seg_000001.ts").write_bytes(b"x")
        fake_session = types.SimpleNamespace(lock=threading.RLock(), segments=[(tmp / "seg_000000.ts", 0.0, 6.0),
                                                                              (tmp / "seg_000001.ts", 6.0, 12.0)])
        hit = live.Session._frame_at(fake_session, 8.5)
        check("a second of the recording is found in its piece, by absolute path",
              hit is not None and Path(hit[0]).is_absolute() and abs(hit[1] - 2.5) < 1e-6, hit)
        check("a piece that is gone gives no frame", live.Session._frame_at(fake_session, 3.0) is None)
        check("a restarted recording gets the story without the old clock",
              live._restarted(dict(new, beats=[{"t": 5.0, "text": "x"}]))["beats"] == [] and live._restarted(None) is None)
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
