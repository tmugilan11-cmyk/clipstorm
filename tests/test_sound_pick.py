"""The sound team: a beat is a real word's time, a sound is placed for real, the critics can say no, and the mix
keeps picture and sound together.

The first picker failed in ways a test can pin, so each one has a check here:

  * the AI never saw a sound, only a mood word, and the catalogue's first row for that word went on the clip;
    now the pickers choose from named sounds with their meaning, and a choice of an id that was never shown is
    ignored;
  * a time was the first word of a three-word group, so every sound began on top of the streamer's voice; now a
    beat hangs on a named word, "after" it means after its last sound, and a sound with words in it is moved past
    the word it answers and cut (or dropped) where the streamer talks again;
  * a sound's own silent start was never known, so the hit landed late; the cue now starts that much earlier;
  * one generous answer was enough; now a proposal needs both critics, or one critic and a high fit;
  * the same sound could go on a clip twice, and two sounds could land on one beat.

The mix is checked on a real file made here: a long sound is pushed under the voice, and a clip whose sound runs
past its picture comes out with the two the same length (render.av_gap under 0.06).

No network and no AI: both are stood in. Run: python tests/test_sound_pick.py
"""
import io
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import wave
from pathlib import Path

FAILED = []
OK = 0


def check(name, fn):
    global OK
    try:
        fn()
    except AssertionError as e:
        FAILED.append((name, str(e) or "failed"))
        print(f"  FAIL {name}\n       {e}")
    except Exception as e:  # noqa: BLE001 - a crash is a failure too
        FAILED.append((name, f"{type(e).__name__}: {e}"))
        print(f"  FAIL {name}\n       {type(e).__name__}: {e}")
    else:
        OK += 1
        print(f"  ok   {name}")


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tests" / "sound-pick-data"
if DATA.exists():
    shutil.rmtree(DATA, ignore_errors=True)
DATA.mkdir(parents=True, exist_ok=True)
os.environ["PEAKCUT_DATA"] = str(DATA)
os.environ["PEAKCUT_SOUND_WEB"] = "0"
os.environ["PEAKCUT_SOUND_VISION"] = "0"
os.environ["PEAKCUT_JUDGE_WEB"] = "0"
os.environ["PEAKCUT_FETCH_MODEL"] = "0"
sys.path.insert(0, str(ROOT))

from studio import memesound, render, sound_kb, sound_moment, sound_pick, sound_web, soundplan  # noqa: E402

print("the sound team")


def tone(seconds=0.6, hz=440, lead=0.0, rate=16000) -> bytes:
    """A real wav: `lead` seconds of silence, then a tone."""
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(rate)
    frames = [0] * int(rate * lead) + [int(14000 * math.sin(2 * math.pi * hz * i / rate)) for i in range(int(rate * seconds))]
    w.writeframes(b"".join(struct.pack("<h", v) for v in frames))
    w.close()
    return buf.getvalue()


# The clip: seconds 100 to 116 of a stream. He hunts for an alien, and it is a deer.
START, END = 100.0, 116.0
WORDS = []
for text, at in (("hey alien come out", 100.2), ("where are you alien", 104.0), ("oh there you go", 110.9),
                 ("that's a damn deer", 112.2)):
    for k, w in enumerate(text.split()):
        WORDS.append({"w": w, "s": round(at + 0.15 * k, 2), "e": round(at + 0.15 * k + 0.14, 2)})
CLIP = {"id": "clip001", "start": START, "end": END, "hook": "ALIEN COME OUT", "reason": "the alien is a deer",
        "rubric": {"kind": "fail"}}


def shelf_sound(slug, seconds, lead=0.0, meaning="", moments=(), voice=False, pop=8.0, place="after_line"):
    """A sound on the shelf and in the knowledge base, measured from its real file."""
    memesound.store(slug, tone(seconds, lead=lead), slug)
    book = sound_kb.load()
    book.setdefault("sounds", {})[slug] = {
        "title": slug.replace("-", " ").upper(), "meaning": meaning or f"the {slug} sound", "moments": list(moments),
        "use_when": "", "never_when": "", "voice": voice, "says": "bruh" if voice else "", "place": place,
        "energy": 3, "pop": pop, "stream_fit": 8, "is_meme": True, "audio": sound_kb.measure(memesound.path_for(slug)),
        "at": 9e9}
    book["at"] = 9e9
    sound_kb._write(book)


shelf_sound("bruh", 0.5, lead=0.12, meaning="a flat 'bruh' for a letdown", moments=("anticlimax", "cringe"), voice=True)
shelf_sound("vine-boom", 0.9, meaning="a deep boom for a shock", moments=("shock", "reveal"))
shelf_sound("sad-violin", 4.0, meaning="sad violin for a fail", moments=("fail", "sad"), place="under_talk")


class Stand:
    """The AI, stood in: canned answers per member of the team, and a record of every prompt."""

    def __init__(self, reader, picks, marks, final=None):
        self.reader, self.picks, self.marks, self.final = reader, picks, marks, final
        self.asked = []

    def __call__(self, prompt, purpose, timeout=None, tally=None):
        self.asked.append((purpose, prompt))
        if tally is not None:
            tally.add(100, calls=0)
        if purpose == "reader":
            return self.reader
        if purpose.startswith("picker"):
            return {"picks": self.picks.get(purpose, [])}
        if purpose.startswith("critic"):
            return {"marks": self.marks(prompt, purpose)}
        if purpose == "sound designer":
            return {"final": self.final if self.final is not None else [], "why": "one is enough"}
        raise AssertionError(f"unexpected purpose {purpose}")


READ = {"what": "He hunts for an alien and finds a deer", "tone": "build-up, letdown",
        "beats": [{"line": 4, "word": "deer", "when": "after", "kind": "anticlimax", "what": "it is a deer",
                   "strength": 9},
                  {"line": 1, "word": "hey", "when": "on", "kind": "shock", "what": "the hook", "strength": 5},
                  {"line": 99, "word": "x", "when": "after", "kind": "fail", "what": "nothing", "strength": 5}],
        "sound_search": ["bruh"]}


def ids_in(prompt):
    """{sound title: id} as the pickers were shown them."""
    out = {}
    for line in prompt.splitlines():
        if line.startswith("S") and " \"" in line:
            sid, rest = line.split(" ", 1)
            out[rest.split("\"")[1]] = sid
    return out


def a_beat_is_a_real_words_time():
    ws = sound_moment.clip_words(WORDS, START, END)
    lines = sound_moment.lines_of(ws, END - START)
    deer = next(w for w in ws if w["w"] == "deer")
    b = sound_pick._beat_time(lines, {"line": 4, "word": "deer", "when": "after", "kind": "anticlimax"})
    assert b and abs(b["t"] - (deer["e"] + 0.05)) < 0.011, f"'after deer' should be just after the word ends: {b}"
    on = sound_pick._beat_time(lines, {"line": 4, "word": "deer", "when": "on", "kind": "shock"})
    assert abs(on["t"] - deer["s"]) < 0.011, f"'on deer' should be the word's start: {on}"
    assert sound_pick._beat_time(lines, {"line": 40, "word": "deer"}) is None, "a line that does not exist made a beat"
    odd = sound_pick._beat_time(lines, {"line": 4, "word": "deer", "kind": "made-up-kind"})
    assert odd["kind"] in sound_kb.MOMENTS, "a kind outside the list was let through"
    assert "quiet" in sound_moment.lines_text(lines), "the transcript does not say where the pauses are"


check("a beat is a real word's time, and an invented line makes none", a_beat_is_a_real_words_time)


def placing_respects_the_words():
    ws = sound_moment.clip_words(WORDS, START, END)
    lines = sound_moment.lines_of(ws, END - START)
    bruh = sound_kb.get("bruh")
    beat = sound_pick._beat_time(lines, {"line": 4, "word": "deer", "when": "after", "kind": "anticlimax"})
    got = sound_pick.place(beat, bruh, ws, END - START, -20.0)
    assert not got.get("no"), got
    assert abs(got["at"] - (beat["t"] - bruh["audio"]["lead"])) < 0.02, \
        f"the sound's silent start was not allowed for, so its hit lands late: {got} lead {bruh['audio']['lead']}"
    assert got["talk"] == 0, "a sound in the quiet after the last word still covers talking"
    # A sound with words, put ON a word, waits for the word to finish.
    on = sound_pick._beat_time(lines, {"line": 3, "word": "oh", "when": "on", "kind": "shock"})
    got = sound_pick.place(on, bruh, ws, END - START, -20.0)
    oh = next(w for w in ws if w["w"] == "oh")
    assert got.get("no") or got["hit"] >= oh["e"], f"a talking sound was put on top of the word it answers: {got}"
    # A long talking sound with no room before the next line is dropped, not laid over the streamer.
    long_voice = dict(bruh, audio=dict(bruh["audio"], seconds=3.0, ring=3.0, lead=0.0))
    tight = sound_pick._beat_time(lines, {"line": 1, "word": "out", "when": "after", "kind": "fail"})
    tight = dict(tight, t=max(tight["t"], 1.05))
    got = sound_pick.place(tight, dict(long_voice), [dict(w) for w in ws] + [{"w": "x", "s": 1.4, "e": 1.6}],
                           END - START, -20.0)
    assert got.get("no"), f"a 3 s talking sound with 0.3 s of room was kept: {got}"
    # Nothing in the hook.
    got = sound_pick.place(dict(beat, t=0.4), sound_kb.get("vine-boom"), ws, END - START, -20.0)
    assert got.get("no"), "a sound was placed in the first second, over the hook"
    # The end of the clip is said, so a critic can judge a sound that would be cut off.
    late = dict(beat, t=END - START - 1.0)
    got = sound_pick.place(late, sound_kb.get("sad-violin"), ws, END - START, -20.0)
    assert "clip ends" in got.get("note", "") and got["end"], f"a cut-off sound did not say so: {got}"


check("a placed sound allows for its silent start, waits for words and never covers the hook", placing_respects_the_words)


def critics_marks():
    m = sound_pick.together([{"fit": 9, "timing": 8, "known": 9, "verdict": "use"},
                             {"fit": 8, "timing": 7, "known": 9, "verdict": "use"}])
    assert m["verdict"] == "use"
    one = sound_pick.together([{"fit": 5, "timing": 8, "known": 9, "verdict": "use"},
                               {"fit": 3, "timing": 3, "known": 9, "verdict": "skip"}])
    assert one["verdict"] == "skip", "one generous critic was enough to put a weak sound on the clip"
    strong = sound_pick.together([{"fit": 9, "timing": 8, "known": 9, "verdict": "use"},
                                  {"fit": 7, "timing": 7, "known": 9, "verdict": "skip"}])
    assert strong["verdict"] == "use", "a high fit with one 'use' should still pass"
    assert sound_pick.score(one, {"votes": 3}) <= 59, "a skipped proposal scored like a good one"
    assert sound_pick.together([None, None]) is None


check("a proposal needs both critics, or one and a high fit", critics_marks)


def the_team_chooses_and_the_critics_can_veto():
    def picks_for(purpose):
        return []
    seen = {}

    def marks(prompt, purpose):
        rows = []
        for block in prompt.split("=== ")[1:]:
            pid = block.split(":")[0].strip()
            good = "BRUH" in block
            rows.append({"id": pid, "fit": 9 if good else 2, "timing": 9 if good else 3, "known": 9,
                         "verdict": "use" if good else "skip", "why": "x"})
        seen[purpose] = prompt
        return rows

    stand = Stand(READ, {}, marks)
    first = {}

    def reader_then_picks(prompt, purpose, timeout=None, tally=None):
        if purpose.startswith("picker"):
            sid = ids_in(prompt)
            first["ids"] = sid
            picks = [{"beat": "B1", "sound": sid["BRUH"], "why": "a letdown", "fit": 9},
                     {"beat": "B1", "sound": sid["SAD VIOLIN"], "why": "sad", "fit": 4},
                     {"beat": "B9", "sound": sid["BRUH"], "why": "no such beat"},
                     {"beat": "B1", "sound": "S999", "why": "no such sound"}]
            stand.asked.append((purpose, prompt))
            return {"picks": picks}
        if purpose == "sound designer":
            ids = [b.split(":")[0].strip() for b in prompt.split("=== ")[1:]]
            stand.asked.append((purpose, prompt))
            return {"final": ids, "why": "it says the letdown"}
        return stand(prompt, purpose, timeout, tally)

    got = sound_pick.choose(CLIP, WORDS, None, ask=reader_then_picks)
    cues = got["cues"]
    assert [c["slug"] for c in cues] == ["bruh"], f"the critics' veto was ignored or bruh lost: {cues}"
    assert len(got["beats"]) == 1, f"the hook beat or the invented line made a beat: {got['beats']}"
    names = {p for p, _ in stand.asked}
    assert {"reader", "sound designer"} <= names and sum(1 for n in names if n.startswith("picker")) == 3 \
        and sum(1 for n in names if n.startswith("critic")) == 2, f"not the whole team was asked: {names}"
    picker_prompt = next(p for n, p in stand.asked if n.startswith("picker"))
    assert "a flat 'bruh' for a letdown" in picker_prompt, "the pickers were not told what the sounds mean"
    assert "B1 at" in picker_prompt, "the pickers were not told where the beats are"
    c = cues[0]
    for k in ("slug", "title", "at", "volume", "end", "why", "mood"):
        assert k in c, f"the cue is missing {k}, which the audio editor reads"
    assert c["mood"] == "anticlimax"
    assert got["cost"]["calls"] >= 7, f"the cost was not counted: {got['cost']}"
    viola = [x for x in got["considered"] if x["slug"] == "sad-violin"]
    assert viola and not viola[0]["chosen"], "the vetoed sound is not listed as considered and turned down"


check("the whole team is asked, ids must be real, and the critics can say no", the_team_chooses_and_the_critics_can_veto)


def none_is_an_answer():
    quiet = dict(READ, beats=[])
    got = sound_pick.choose(CLIP, WORDS, None, ask=Stand(quiet, {}, lambda p, n: []))
    assert got["cues"] == [] and got["source"] == "ai" and "no moment" in got["why"].lower(), got["why"]
    nothing = sound_pick.choose(CLIP, WORDS, None, ask=Stand(READ, {}, lambda p, n: []))
    assert nothing["cues"] == [] and nothing["why"], "no picks must still say why"
    short = sound_pick.choose(dict(CLIP, end=START + 3), WORDS, None, ask=Stand(READ, {}, lambda p, n: []))
    assert short["cues"] == [] and "too short" in short["why"]

    def broken(prompt, purpose, timeout=None, tally=None):
        raise RuntimeError("the service is down")
    down = sound_pick.choose(CLIP, WORDS, None, ask=broken)
    assert down["cues"] == [] and "could not read" in down["why"], down["why"]


check("no sound is a real answer, and a failure is a sentence", none_is_an_answer)


def one_beat_one_sound_and_spacing():
    reader = dict(READ, beats=READ["beats"][:1] + [
        {"line": 4, "word": "damn", "when": "on", "kind": "shock", "what": "he swears", "strength": 6}])

    def ask(prompt, purpose, timeout=None, tally=None):
        if purpose == "reader":
            return reader
        if purpose.startswith("picker"):
            sid = ids_in(prompt)
            return {"picks": [{"beat": "B1", "sound": sid["VINE BOOM"]}, {"beat": "B2", "sound": sid["BRUH"]},
                              {"beat": "B2", "sound": sid["VINE BOOM"]}]}
        if purpose.startswith("critic"):
            return {"marks": [{"id": b.split(":")[0].strip(), "fit": 9, "timing": 9, "known": 9, "verdict": "use"}
                              for b in prompt.split("=== ")[1:]]}
        return {"final": [b.split(":")[0].strip() for b in prompt.split("=== ")[1:]]}

    got = sound_pick.choose(CLIP, WORDS, None, ask=ask)
    hits = [c["hit"] for c in got["cues"]]
    assert len(got["cues"]) == 1, f"two sounds 0.3 s apart both went on: {got['cues']}"
    assert len({c["slug"] for c in got["cues"]}) == len(got["cues"]), "the same sound went on twice"
    assert all(b - a >= sound_pick.SPACING for a, b in zip(hits, hits[1:]))


check("one sound per beat, never twice, never crowded", one_beat_one_sound_and_spacing)


def suggest_keeps_the_page_contract_and_shelves_the_file():
    # A sound the knowledge base has in its own folder, not yet on the shelf.
    sound_kb.kb_dir().mkdir(parents=True, exist_ok=True)
    (sound_kb.kb_dir() / "womp-womp.mp3").write_bytes(tone(1.0))
    book = sound_kb.load()
    book["sounds"]["womp-womp"] = {"title": "Womp Womp", "meaning": "a letdown horn", "moments": ["anticlimax"],
                                   "voice": False, "pop": 9.9, "stream_fit": 9, "is_meme": True, "at": 9e9,
                                   "audio": sound_kb.measure(sound_kb.kb_dir() / "womp-womp.mp3"),
                                   "audio_url": "https://dankmachine.com/media/audio/womp.mp3"}
    sound_kb._write(book)
    assert not memesound.kept("womp-womp")

    def ask(prompt, purpose, timeout=None, tally=None):
        if purpose == "reader":
            return READ
        if purpose.startswith("picker"):
            return {"picks": [{"beat": "B1", "sound": ids_in(prompt)["Womp Womp"], "why": "letdown"}]}
        if purpose.startswith("critic"):
            return {"marks": [{"id": "P1", "fit": 9, "timing": 9, "known": 9, "verdict": "use"}]}
        return {"final": ["P1"]}

    job = {"dir": str(DATA / "job"), "user": "u", "words": WORDS}
    got = soundplan.suggest(job, CLIP, None, ask=ask)
    for k in ("ok", "cues", "why", "source", "seconds", "most", "need"):
        assert k in got, f"the suggest answer lost {k}, which the audio editor reads"
    assert got["cues"] and got["cues"][0]["slug"] == "womp-womp", got
    assert memesound.kept("womp-womp") and got["cues"][0]["kept"] and got["need"] == [], \
        "the chosen sound was not put on the shelf, so the page could not play or mix it"
    index = json.loads((memesound.home() / "index.json").read_text(encoding="utf-8"))
    assert "dankmachine.com" in index["womp-womp"].get("url", ""), "where the sound came from was not written down"
    for slug in ("bruh", "vine-boom", "sad-violin"):
        assert memesound.kept(slug), f"{slug}, a sound already on the shelf, is gone"


check("the suggest answer keeps the page's shape and puts the sound on the shelf",
      suggest_keeps_the_page_contract_and_shelves_the_file)


def the_route_still_asks_the_measured_way():
    src = (ROOT / "studio" / "api_memesound.py").read_text(encoding="utf-8")
    seg = src[src.index("async def clip_sounds_suggest"):src.index("@router.get(\"/api/memesounds/knowledge\")")]
    assert "soundplan.suggest(" in seg, "the button no longer reaches the sound team"
    assert "ask=team" in seg, "the route's own measured ask is not the one the team uses"
    assert "soundplan.plan(" not in seg, "the button still runs the first picker"


check("the suggest route runs the sound team with the measured ask", the_route_still_asks_the_measured_way)


def the_mix_ducks_long_sounds_and_keeps_sync():
    work = DATA / "mix"
    work.mkdir(exist_ok=True)
    clip = work / "clip.mp4"
    # 6 s of picture with 6.5 s of sound, the way some finished clips come out of the renderer.
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x568:rate=30:duration=6",
                    "-f", "lavfi", "-i", "sine=frequency=220:duration=6.5", "-c:v", "libx264", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", "-t", "6.5", str(clip)], check=True,
                   capture_output=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(clip), "-c", "copy", str(work / "clip2.mp4")], check=True)
    src = work / "clip2.mp4"
    out = work / "mixed.mp4"
    memesound.mix(src, [{"slug": "sad-violin", "at": 1.0, "volume": 0}, {"slug": "vine-boom", "at": 4.5}], out)
    gap = render.av_gap(out)
    assert gap < 0.06, f"picture and sound are {gap:.3f} s apart after the mix"
    info = memesound._ffprobe(out)
    assert abs(info["duration"] - info["picture"]) < 0.06, f"the sound runs past the picture: {info}"
    # The long sound goes through the voice ducker; the short one does not.
    import inspect
    body = inspect.getsource(memesound.mix)
    assert "sidechaincompress" in body and "DUCK_LONGER" in body, "long sounds are no longer ducked under the voice"


check("a long sound is ducked under the voice and the mix keeps picture and sound together",
      the_mix_ducks_long_sounds_and_keeps_sync)


def most_sounds_by_length():
    assert sound_pick.most_for(3) == 0 and sound_pick.most_for(8) == 1 and sound_pick.most_for(20) == 2
    assert sound_pick.most_for(60) == 3, "a long clip may earn a third sound, never more"


check("a clip carries few sounds, by its length", most_sounds_by_length)

print()
shutil.rmtree(DATA, ignore_errors=True)
if FAILED:
    print(f"{len(FAILED)} check(s) failed - {', '.join(n for n, _ in FAILED)}")
    sys.exit(1)
print(f"All checks passed. {OK} ok")
