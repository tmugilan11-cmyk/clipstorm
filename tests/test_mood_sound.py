"""The sound a person picks on a clip reaches the file that is rendered - or says why it did not.

Three things used to be quietly wrong, and each one looked fine from the page:

  * the clip dialog posted `mood`, and the render route dropped it, so every choice was lost;
  * the mood list asked for `<mood>.wav` while a mood names its sounds (`hype` is airhorn then bass_drop), so every
    noise was reported "not built yet" while its files sat on disk;
  * nothing failed loudly, so a clip with a gag that could not be applied still claimed to carry it.

Two more were found by proving the pages afterwards, and both were the same shape - a page asking a question the
server did not answer:

  * the Sounds page probes each sound with HEAD before playing it, and the route only answered GET, so a sound that
    was sitting on disk was reported as unreachable (405);
  * the Schedule page's "An Improve round on a timer" card read autopilot's preview, so it printed a PeakCutAutopilot
    command under a heading that promised an Improve round.

Run: python tests/test_mood_sound.py
"""
import os
import sys
import tempfile
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


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

# The studio writes into PEAKCUT_DATA, so the run gets a folder of its own and can never touch a real install.
DATA = HERE / "mood-data"
if not DATA.is_dir():
    DATA.mkdir()
os.environ["PEAKCUT_DATA"] = str(DATA)
os.environ["PEAKCUT_FETCH_MODEL"] = "0"

from studio import config, jobs, meme, music  # noqa: E402

print("the sound a clip can be given")


def a_mood_is_a_word_or_nothing():
    """The coercion the render route does, checked on its own: a name is lowercased and trimmed, and nothing is empty."""
    for body, want in (({"mood": "  HYPE  "}, "hype"), ({"mood": ""}, None), ({"mood": None}, None),
                       ({"mood": "Funny "}, "funny"), ({"mood": "x" * 40}, "x" * 20)):
        have = str(body.get("mood") or "").strip().lower()[:20] or None
        assert have == want, f"{body!r} became {have!r}, wanted {want!r}"


check("a mood is a lowercase word, and empty means none", a_mood_is_a_word_or_nothing)


def every_meme_mood_names_its_own_sound():
    moods = meme.load_moods()
    assert moods, "no meme moods at all"
    for name, row in moods.items():
        names = meme.sound_names(name)
        assert names, f"{name} names no sound, so nothing can ever be ready for it"
        want = row.get("sound")
        first = want if isinstance(want, str) else (want or [None])[0]
        assert first is None or names[0] == first, f"{name} starts with {names[0]!r}, its mood file says {first!r}"


check("every meme mood names the sound its own mood file names", every_meme_mood_names_its_own_sound)


def readiness_follows_the_files():
    """`sound_ready` must be true for the shipped sounds and false for a name nothing writes."""
    made = meme.make_sounds(meme.sounds_dir())
    assert made, "no shipped sound could be written"
    wanted = {"hype": ["airhorn", "bass_drop"], "funny": ["rimshot", "ding"], "win": ["bass_drop"]}
    for mood, files in wanted.items():
        have = [f for f in files if (meme.sounds_dir() / f"{f}.wav").is_file()]
        assert have, f"none of {files} is on disk, so {mood} cannot be checked"
        assert meme.sound_ready(mood) is True, f"{mood} has {have[0]}.wav and still reports not ready"
    assert meme.sound_ready("no-such-mood") is False, "a mood that does not exist reported ready"


check("a mood is ready when one of its named sounds is on disk", readiness_follows_the_files)


def ready_never_builds_anything():
    """The page asks about readiness on every open; that must be a directory listing, not a few seconds of numpy."""
    before = sorted(p.name for p in meme.sounds_dir().glob("*.wav"))
    for _ in range(3):
        for name in meme.load_moods():
            meme.sound_ready(name)
    after = sorted(p.name for p in meme.sounds_dir().glob("*.wav"))
    assert before == after, f"asking about readiness wrote files: {set(after) - set(before)}"


check("asking whether a sound is ready builds nothing", ready_never_builds_anything)


def music_knows_its_beds():
    assert music.AVAILABLE, "music needs numpy, which this run does not have"
    # A fresh data folder has no beds: they are made on demand, exactly as a first render would make them.
    made = music.make_beds(music.bed_path("chill").parent)
    assert made, "no music bed could be written"
    for name in music.MOODS:
        bed = music.bed_path(name)
        assert bed.is_file(), f"the {name} bed was not made at {bed}"
        assert music._mood(name) == name, f"music does not recognise its own mood {name!r}"
    assert music._mood("nonsense") == "chill", "an unknown mood must fall back, never fail a render"


check("every music bed can be made, and an unknown mood falls back", music_knows_its_beds)


def a_silent_clip_is_left_alone():
    """A clip whose sound cannot be applied keeps the picture it was rendered with, and the clip does not claim it."""
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        made = folder / "clip.mp4"
        made.write_bytes(b"not really a video")      # every mixer will refuse this
        out = {"file": "clip.mp4", "cover": "clip.jpg", "layout": "crop"}
        (folder / "clip.jpg").write_bytes(b"jpg")
        before = made.read_bytes()
        jobs._add_sound({"mood": "funny", "start": 0.0, "end": 10.0}, out, folder)
        assert made.read_bytes() == before, "the clip file was changed even though the sound could not be applied"
        assert "mood" not in out, f"the clip claims the {out.get('mood')!r} sound it does not carry"
        assert not list(folder.glob(".*sound*")), f"a half-written file was left behind: {list(folder.glob('*'))}"


check("a sound that cannot be applied leaves the clip alone and claims nothing", a_silent_clip_is_left_alone)


def no_mood_means_no_work():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        made = folder / "clip.mp4"
        made.write_bytes(b"x")
        out = {"file": "clip.mp4", "cover": "clip.jpg"}
        for mood in (None, "", "   "):
            jobs._add_sound({"mood": mood, "start": 0.0, "end": 10.0}, out, folder)
            assert "mood" not in out, f"mood {mood!r} was written on a clip that asked for nothing"
        assert made.read_bytes() == b"x", "the clip was touched with no sound asked for"


check("no sound asked for means the file is not touched at all", no_mood_means_no_work)


def a_meme_beats_a_bed_when_the_name_is_both():
    """`funny` and `hype` are a meme noise and a music bed. A gag is what a person picked the sound for."""
    both = [n for n in meme.load_moods() if n in music.MOODS]
    assert both, "this check is pointless if no name is both"
    src = (ROOT / "studio" / "jobs.py").read_text(encoding="utf-8")
    body = src[src.index("def _add_sound"):src.index("def _caption_words")]
    i_meme = body.index("meme.apply")
    i_music = body.index("music.apply")
    assert i_meme < i_music, "music is tried before the meme table, so a gag would silently become a bed"
    assert "got is None and" in body, "the bed is tried even when the meme already worked"


check("a name that is both a gag and a bed is treated as the gag", a_meme_beats_a_bed_when_the_name_is_both)


def the_route_keeps_the_word():
    src = (ROOT / "studio" / "jobs.py").read_text(encoding="utf-8")
    body = src[src.index("def request_render"):src.index("def _brand_kwargs")]
    assert '"mood"' in body, "request_render does not read `mood`, so the page's choice is dropped again"
    assert 'new["mood"]' in body, "request_render reads `mood` but never stores it on the clip"
    hook = src[src.index("def render_one"):]
    hook = hook[:hook.index("def _caption_words")]
    assert "_add_sound(" in hook, "the clip worker never applies the sound"
    assert hook.index("render.render_clip") < hook.index("_add_sound("), "the sound is added before there is a file"


check("the render route stores the word and the worker applies it", the_route_keeps_the_word)


def the_page_sends_the_word():
    js = (ROOT / "web" / "feat" / "mood.js").read_text(encoding="utf-8")
    assert 'data-f="mood"' in js, "the clip dialog has no mood field"
    assert "mood" in js and "/api/moods" in js, "the field is not filled from the mood list"


check("the clip dialog has a mood field filled from the server", the_page_sends_the_word)


def the_route_answers_the_question_the_page_asks():
    """The Sounds page asks with HEAD before it plays, so the route must answer HEAD as well as GET.

    It did not, and the page's own probe is why: a missing sound and a sound this browser cannot decode arrive at
    an <audio> element as the same error event, so the page asks the address first to tell them apart. A 405 there
    meant every Play press on a sound that was sitting on disk said "the server could not hand over the sound".
    Measured directly: `curl -I /api/sounds/meme/embarrassing` was 405 while `curl` was 200.
    """
    src = (ROOT / "studio" / "api_sound.py").read_text(encoding="utf-8")
    tail = src[src.index("/api/sounds/{kind}/{mood}"):]
    marker = "@router.post(" + repr("/api/moods/prime") + ")"
    route = tail[: tail.index(marker)] if marker in tail else tail
    assert '"HEAD"' in route, (
        "the sound route does not answer HEAD, so the page's probe gets 405 and a sound that exists looks missing"
    )
    assert '"GET"' in route, "the sound route no longer answers GET, so nothing can be downloaded"
    page = (ROOT / "web" / "feat" / "sounds.js").read_text(encoding="utf-8")
    assert 'method: "HEAD"' in page, "the page no longer probes with HEAD; this check has outlived its reason"


check("the sound route answers the HEAD the page probes with", the_route_answers_the_question_the_page_asks)


def the_improve_round_has_its_own_command():
    """The Schedule page's "Improve round" card must show the round's own command, not the clips tick.

    It used to read /api/schedule/preview, which is autopilot's scheduler text, so the card headed "An Improve round
    on a timer" printed a PeakCutAutopilot task. `schedule_ai.spec` already built the right command and no route
    served it. Measured after the fix: the Improve card names PeakCutRound and not PeakCutAutopilot, and the clips
    card names PeakCutAutopilot and not PeakCutRound.
    """
    api = (ROOT / "studio" / "api_preview.py").read_text(encoding="utf-8")
    assert "/api/schedule/round" in api, "no route serves the Improve round schedule"
    assert "schedule_ai.spec(" in api, "the round route does not build its command from schedule_ai.spec"
    page = (ROOT / "web" / "feat" / "schedule.js").read_text(encoding="utf-8")
    assert "/api/schedule/round" in page, "the Schedule page still asks autopilot for the Improve round"


check("the Improve round card shows the round's own command", the_improve_round_has_its_own_command)


print()
if FAILED:
    print(f"{len(FAILED)} check(s) failed - {', '.join(n for n, _ in FAILED)}")
    sys.exit(1)
print(f"All checks passed. {OK} ok")
