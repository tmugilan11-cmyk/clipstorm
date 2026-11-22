"""The meme-sound timeline: what the page draws, what the server keeps, and what a render hears.

The timeline was built against the routes in `studio/api_memesound.py`, and three of its behaviours
quietly depended on details nobody had written down. Each check here pins one of them:

  * the jobs lookup used `jobs.find`, which does not exist - the real one is `jobs.get`, and the timeline
    answered 500 on its very first load;
  * `take` only asked the catalogue when BOTH the url and the title were missing, so the page's normal
    call (title, no url) failed on every Keep;
  * the clip PUT stores only cues whose sound is on the shelf, so a kept sound can never make a render
    fail later, and a removed one cannot stay on a clip.

The upload path is checked with a real tone, because proving "the bytes are audio" is the point of the
ffprobe step: a renamed picture must never reach the shelf.

Run: python tests/test_meme_timeline.py
"""
import io
import os
import re
import struct
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


# The studio writes into PEAKCUT_DATA, so the run gets a folder of its own and can never touch a real install.
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tests" / "meme-tl-data"
DATA.mkdir(parents=True, exist_ok=True)
os.environ["PEAKCUT_DATA"] = str(DATA)

sys.path.insert(0, str(ROOT))

from studio import api_memesound, jobs, memesound  # noqa: E402


FEAT = (ROOT / "web" / "feat" / "meme-timeline.js").read_text(encoding="utf-8")
# Placing a sound moved out of the clip dialog and onto its own wide page, so the routes that place and mix
# are called from there now. Checking both files keeps the promise ("the page speaks to routes that exist")
# without pinning it to a file that no longer does that job.
EDIT = (ROOT / "web" / "feat" / "audio-edit.js").read_text(encoding="utf-8")
ROUTES = (ROOT / "studio" / "api_memesound.py").read_text(encoding="utf-8")

# A real half-second tone, so the upload check exercises ffprobe rather than a stub.
def _tone_wav(seconds: float = 0.5, hz: int = 220) -> bytes:
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(16000)
    w.writeframes(b"".join(
        struct.pack("<h", int(12000 * ((i * hz / 16000) % 1.0 * 2.0 - 1.0))) for i in range(int(16000 * seconds))
    ))
    w.close()
    return buf.getvalue()


def test_jobs_lookup_is_the_real_one():
    """The timeline loads a clip through _job_or_404; it must use jobs.get, not the jobs.find that never existed."""
    src = Path(api_memesound.__file__).read_text(encoding="utf-8")
    assert "jobs.find(" not in src, "the route still calls jobs.find(), which does not exist"
    assert "jobs.get(" in src, "the route does not use jobs.get()"


def test_take_asks_the_catalogue_without_a_url():
    """The page calls take(slug, title) with no url; the catalogue must be asked, not skipped."""
    src = Path(memesound.__file__).read_text(encoding="utf-8")
    m = re.search(r"def take\(.*?\n(.*?)\n    if not url:", src, re.S)
    assert m, "could not find the guard in take()"
    body = m.group(1)
    assert "if not url and not title" not in body, \
        "take() still skips the catalogue when a title was given but no url - every Keep from the page fails"


def test_slug_and_store():
    """Uploaded sounds land under mine- names, with dots and dashes cleaned from both ends.

    The route strips the file extension before naming, so the checks here use titles the way the route sends them."""
    assert memesound.make_slug("my vine boom") == "mine-my-vine-boom"
    assert memesound.make_slug("...") == "mine-sound", "a name of dots must not survive as an empty stem"
    assert memesound.make_slug("звук") == "mine-sound", "non-ascii titles still need a usable shelf name"
    assert memesound.make_slug("").startswith("mine-")
    slug = memesound.make_slug("tone test")
    path = memesound.store(slug, _tone_wav(), "tone test")
    assert path.is_file() and path.stat().st_size > 512
    assert memesound.kept(slug)
    assert memesound.forget(slug) is True
    assert not memesound.kept(slug)


def test_store_refuses_oversize():
    try:
        memesound.store("mine-big", b"x" * (memesound.MAX_UPLOAD + 1), "big")
        raise AssertionError("a file over MAX_UPLOAD was accepted")
    except (ValueError, RuntimeError):
        pass


def test_upload_route_proves_the_bytes_are_audio():
    """The route runs ffprobe before storing; a fake wav must be refused and a real one kept."""
    import asyncio

    class _Req:
        class state:
            user = type("U", (), {"id": "test_user_01", "is_admin": True})()

    async def run():
        class _F:
            filename = "tone test.wav"
            async def read(self):
                return _tone_wav()
        return await api_memesound.memesounds_upload(_Req(), file=_F())

    got = asyncio.run(run())
    assert got["ok"] is True and got["sound"]["source"] == "uploaded"
    assert got["sound"]["slug"].startswith("mine-")
    assert 0.1 <= got["sound"]["seconds"] <= memesound.MIX_SECONDS
    memesound.forget(got["sound"]["slug"])

    async def run_bad():
        class _F:
            filename = "not audio.wav"
            async def read(self):
                return b"RIFFxxxxWAVEjunkjunk" + b"\x00" * 600
        return await api_memesound.memesounds_upload(_Req(), file=_F())

    try:
        asyncio.run(run_bad())
        raise AssertionError("a fake wav was accepted")
    except Exception as e:  # the route answers with HTTPException(400)
        assert "audio" in str(getattr(e, "detail", e)), str(e)


def test_cue_validation_uses_the_shelf():
    """A cue for a sound that is not on this machine is refused, so a render can never fail on a missing file."""
    why = memesound.cue_ok({"slug": "definitely-not-kept-xyz", "at": 1.0, "volume": 0})
    assert why, "a cue for a sound that is not kept was accepted"
    slug = memesound.make_slug("kept probe")
    memesound.store(slug, _tone_wav(), "kept probe")
    assert memesound.cue_ok({"slug": slug, "at": 1.0, "volume": 0}) is None
    assert memesound.cue_ok({"slug": slug, "at": -1.0, "volume": 0})
    assert memesound.cue_ok({"slug": slug, "at": 1.0, "end": 0.5, "volume": 0}) is not None, "end before start must be refused"
    assert memesound.tidy([{"slug": slug, "at": 1.0, "volume": 99}])[0]["volume"] == 12.0, "tidy clamps loudness"
    memesound.forget(slug)


def test_whole_sound_is_not_a_zero_length_cue():
    """Zero end means "play the whole sound", the way the editor's "Whole sound" choice sends it.

    Reading 0 as a real end time refused every cue the page ever saved with "ends before it starts", and
    `tidy` turned 0 into a twentieth of a second, which is a click rather than a sound.
    """
    slug = memesound.make_slug("whole probe")
    memesound.store(slug, _tone_wav(), "whole probe")
    assert memesound.cue_ok({"slug": slug, "at": 1.0, "volume": 0, "end": 0}) is None, \
        "end 0 is the whole sound, not a cue that ends before it starts"
    assert memesound.cue_ok({"slug": slug, "at": 1.0, "volume": 0, "end": ""}) is None, "an empty end is the whole sound"
    kept = memesound.tidy([{"slug": slug, "at": 1.0, "volume": 0, "end": 0}])[0]
    assert "end" not in kept, "tidy stored a zero end, which caps the sound at a click: %r" % kept
    real = memesound.tidy([{"slug": slug, "at": 1.0, "volume": 0, "end": 2.0}])[0]
    assert real.get("end") == 2.0, "a real end time must survive: %r" % real
    memesound.forget(slug)


def test_the_page_and_the_routes_agree():
    """The pages speak to routes that exist, and none they invented.

    A sound is kept or searched from the library page ("From the web" lives in meme-timeline.js), and it is
    placed, saved, suggested and mixed from the audio editor (audio-edit.js). Both are checked here.
    """
    for needle in ("/api/memesounds/library", "/api/memesounds/keep", "/api/memesounds/upload",
                   "/api/memesounds/search", "/api/memesounds/for"):
        assert needle in FEAT, f"the library page never calls {needle}"
        assert needle.strip("/api/") in ROUTES or needle in ROUTES, f"the route file has no {needle}"
    for needle in ("/sounds", "/sounds/suggest", "/sounds/hear", "/api/memesounds/keep",
                   "/api/memesounds/library"):
        assert needle in EDIT, f"the audio editor never calls {needle}"
        assert needle.strip("/api/") in ROUTES or needle in ROUTES, f"the route file has no {needle}"
    for needle in ("pointerdown", "pointermove", "pointerup"):
        assert needle in EDIT, f"the audio editor does not {needle} - drag would not work"
    assert "MutationObserver" in FEAT or "drawSettings" in FEAT, "the library page hooks nothing"
    assert "decodeAudioData" in FEAT or "wave" not in FEAT.lower(), "a waveform was promised but never drawn"
    # The dialog must offer ONE way in, not a panel of its own.
    index = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert 'data-act="openaudio"' in index, "the clip editor has no Edit audio button"
    assert "class=\"mtl\"" not in FEAT, "the old in-dialog track is still being injected"


check("the jobs lookup is the real one", test_jobs_lookup_is_the_real_one)
check("take asks the catalogue without a url", test_take_asks_the_catalogue_without_a_url)
check("slugs and shelf storage behave", test_slug_and_store)
check("store refuses oversize", test_store_refuses_oversize)
check("the upload route proves the bytes are audio", test_upload_route_proves_the_bytes_are_audio)
check("cue validation uses the shelf", test_cue_validation_uses_the_shelf)
check("a whole sound is not a zero-length cue", test_whole_sound_is_not_a_zero_length_cue)
check("the page and the routes agree", test_the_page_and_the_routes_agree)

print()
if FAILED:
    print(f"{len(FAILED)} check(s) failed - {', '.join(n for n, _ in FAILED)}")
    sys.exit(1)
print(f"All checks passed. {OK} ok")
