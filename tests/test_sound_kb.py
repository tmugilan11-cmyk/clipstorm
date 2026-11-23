"""The sound knowledge base: what every meme sound is for, how popular it is, and where its hit is.

The first picker knew a sound only by its catalogue name. These checks pin what replaced that:

  * a build reads several sources per sound and asks the AI what each one means, and keeps only what it said
    in the closed list of moments, with numbers held to their ranges;
  * popularity comes from measured plays first, so a sound with ten million plays outranks one nobody played;
  * the length, the silent start and the loudness are measured on the file itself;
  * a file is only ever downloaded from the catalogue's own address, and a sound longer than a sting is left out;
  * the owner's own sounds are researched too, and nothing on the shelf is removed or changed by a build;
  * a sound researched this week is not researched again.

No network and no AI: the catalogue, the web readers, the download and the AI are stood in.
Run: python tests/test_sound_kb.py
"""
import io
import json
import math
import os
import re
import shutil
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
        print(f"  ok   {name}")


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tests" / "sound-kb-data"
if DATA.exists():
    shutil.rmtree(DATA, ignore_errors=True)
DATA.mkdir(parents=True, exist_ok=True)
os.environ["PEAKCUT_DATA"] = str(DATA)
os.environ["PEAKCUT_SOUND_WEB"] = "0"
os.environ["PEAKCUT_SOUND_VISION"] = "0"
os.environ["PEAKCUT_JUDGE_WEB"] = "0"
sys.path.insert(0, str(ROOT))

from studio import memesound, sound_kb, sound_web  # noqa: E402

print("the sound knowledge base")


def tone(seconds=0.6, lead=0.0, hz=330, rate=16000) -> bytes:
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(rate)
    w.writeframes(b"".join(struct.pack("<h", v) for v in
                           [0] * int(rate * lead) + [int(12000 * math.sin(2 * math.pi * hz * i / rate))
                                                     for i in range(int(rate * seconds))]))
    w.close()
    return buf.getvalue()


ROWS = {
    "vine-boom": {"slug": "vine-boom", "title": "VINE BOOM SOUND", "about": "a boom for shock",
                  "audio_url": "https://dankmachine.com/media/audio/vine-boom.mp3", "popularity": 7_500_000,
                  "aliases": ["vine thud"]},
    "bruh": {"slug": "bruh", "title": "BRUH", "about": "deadpan letdown",
             "audio_url": "https://dankmachine.com/media/audio/bruh.mp3", "popularity": 4_500_000},
    "obscure-song": {"slug": "obscure-song", "title": "my cousin's song", "about": "a song",
                     "audio_url": "https://dankmachine.com/media/audio/obscure.mp3", "popularity": 12},
    "long-song": {"slug": "long-song", "title": "A whole song", "about": "four minutes",
                  "audio_url": "https://dankmachine.com/media/audio/long.mp3", "popularity": 50_000},
}


class Catalogue:
    def trending(self, window):
        return [ROWS["bruh"]] if window == "24h" else []

    def search(self, name, limit=8):
        return [r for r in ROWS.values() if set(name.lower().split()) & set(r["title"].lower().split())]

    def one(self, slug):
        return ROWS.get(slug)

    def library(self):
        return memesound.library()


class Web:
    def __init__(self):
        self.asked = []

    def ranking(self, kind, pages=1):
        self.asked.append(("ranking", kind))
        return [{"slug": "vine-boom", "title": "VINE BOOM SOUND", "rank": 1},
                {"slug": "obscure-song", "title": "my cousin's song", "rank": 200},
                {"slug": "long-song", "title": "A whole song", "rank": 150}] if kind == "best" else []

    def instant(self, slug):
        self.asked.append(("instant", slug))
        return {"views": 12_000_000, "saves": 590_000} if slug == "vine-boom" else {}

    def variants(self, name):
        self.asked.append(("variants", name))
        return ["VINE BOOM SOUND!!", "vine boom bass boosted"] if "VINE" in name else []

    def find(self, q):
        return []

    def meaning(self, name, tries=None):
        self.asked.append(("meaning", name))
        return {"page": "https://knowyourmeme.com/memes/vine-boom-sound-effect",
                "about": "used to emphasize shock or surprise"} if "VINE" in name.upper() else {}

    def youtube(self, q, n=8):
        self.asked.append(("youtube", q))
        return [{"title": q, "views": 10_000_000, "seconds": 3}] if "VINE" in q.upper() else []

    def save(self):
        pass


def fetch(slug, url):
    """The download, stood in: a real audio file, the long song really long."""
    assert sound_kb._allowed(url), f"a download was attempted from {url}"
    sound_kb.kb_dir().mkdir(parents=True, exist_ok=True)
    p = sound_kb.kb_dir() / f"{slug}.mp3"
    p.write_bytes(tone(40.0 if slug == "long-song" else 0.8, lead=0.25 if slug == "vine-boom" else 0.0))
    return p


ASKED = []


def ask(prompt, purpose, timeout=None, tally=None):
    ASKED.append(prompt)
    out = []
    for i, title in re.findall(r'=== S(\d+): "([^"]*)"', prompt):
        row = {"id": f"S{i}", "meaning": f"what {title} means", "use_when": "u", "never_when": "n",
               "place": "after_line", "energy": 9, "popular_now": 42, "stream_fit": 8, "voice": False, "says": "",
               "crude": False, "is_meme": True, "moments": ["shock", "not-a-moment", "reveal"]}
        if "cousin" in title:
            row.update(is_meme=False, popular_now=1, moments=["sad"])
        if title == "BRUH":
            row.update(moments=["anticlimax", "cringe"], voice=True, says="bruh")
        if title == "my upload":
            row.update(moments=["fail"])
        out.append(row)
    return {"sounds": out}


# the owner's own upload, already on the shelf before any build
memesound.store("mine-my-upload", tone(0.7), "my upload")
BEFORE = (memesound.path_for("mine-my-upload")).read_bytes()


def a_build_researches_and_describes():
    web = Web()
    got = sound_kb.build(ask=ask, catalogue=Catalogue(), web=web, fetch=fetch, workers=2)
    assert got["ok"], got
    book = json.loads((memesound.home() / "knowledge.json").read_text(encoding="utf-8"))
    s = book["sounds"]
    assert "vine-boom" in s and "bruh" in s and "mine-my-upload" in s, f"sounds missing: {sorted(s)}"
    assert "long-song" not in s and "long-song" in got["skipped_long"], "a 40 s song was kept as a meme sound"
    v = s["vine-boom"]
    assert v["moments"] == ["shock", "reveal"], f"a moment outside the list was kept: {v['moments']}"
    assert v["energy"] == 5 and v["popular_now"] == 10, "numbers were not held to their ranges"
    assert v["kym"]["page"].startswith("https://knowyourmeme.com"), "Know Your Meme was not read"
    assert abs(v["audio"]["lead"] - 0.25) < 0.05, f"the silent start was not measured: {v['audio']}"
    assert v["source"].startswith("https://dankmachine.com/"), "where the file came from was not written down"
    kinds = {k for k, _ in web.asked}
    assert {"ranking", "instant", "variants", "meaning", "youtube"} <= kinds, f"not every source was read: {kinds}"
    assert s["obscure-song"]["is_meme"] is False
    assert s["mine-my-upload"].get("mine"), "the owner's own sound was not researched"
    assert memesound.path_for("mine-my-upload").read_bytes() == BEFORE, "a build changed the owner's file"
    assert not memesound.kept("vine-boom"), "a build put a sound on the person's shelf; only a pick may"


check("a build reads every source, describes each sound and keeps the owner's files", a_build_researches_and_describes)


def popular_is_measured():
    hot = sound_kb.get("vine-boom")
    cold = sound_kb.get("obscure-song")
    assert hot["pop"] > 8.5, f"twelve million plays and rank 1 is only {hot['pop']}"
    assert cold["pop"] < hot["pop"] - 3, f"a sound nobody plays ranks near the top: {cold['pop']}"
    assert sound_kb.popularity({"popular_now": 6}) == 6.0, "with no numbers at all the AI's view is the answer"


check("popularity comes from measured plays first", popular_is_measured)


def the_shortlist_follows_the_moment():
    got = sound_kb.shortlist(["anticlimax"], most=10)
    assert got and got[0]["slug"] == "bruh", f"the anticlimax sound is not first: {[g['slug'] for g in got]}"
    assert all(g.get("is_meme", True) for g in got), "a sound that is not a meme was offered"
    assert any(g["slug"] == "vine-boom" for g in got), "the most popular sounds are not added as a fallback"


check("the shortlist puts the sound for the moment first", the_shortlist_follows_the_moment)


def fresh_sounds_are_not_researched_again():
    before = len(ASKED)
    got = sound_kb.build(ask=ask, catalogue=Catalogue(), web=Web(), fetch=fetch)
    assert got["researched"] == 0 and len(ASKED) == before, "a sound researched this week was researched again"


check("a sound researched this week is not researched again", fresh_sounds_are_not_researched_again)


def downloads_only_from_the_catalogue():
    assert sound_kb._allowed("https://dankmachine.com/media/audio/x.mp3")
    assert not sound_kb._allowed("https://www.myinstants.com/media/sounds/x.mp3"), "myinstants files are not ours to take"
    assert not sound_kb._allowed("https://evil.example/dankmachine.com.mp3")
    assert sound_kb.download("x", "https://evil.example/x.mp3") is None


check("a file is only downloaded from the catalogue", downloads_only_from_the_catalogue)


def the_web_can_be_switched_off():
    assert sound_web.on() is False
    assert sound_web.ranking("best") == [] and sound_web.instant("bruh") == {} and sound_web.find("x") == []
    assert sound_web.meaning("vine boom") == {} and sound_web.youtube("x") == []
    assert sound_kb.fresh() is False, "a refresh started with the web switched off"


check("with the web switched off nothing is asked", the_web_can_be_switched_off)


def measuring_a_file():
    p = DATA / "probe.wav"
    p.write_bytes(tone(1.0, lead=0.4))
    got = sound_kb.measure(p)
    assert abs(got["seconds"] - 1.4) < 0.05 and abs(got["lead"] - 0.4) < 0.05, got
    assert got["ring"] > 1.3 and -40 < got["loud_db"] < 0, got


check("length, silent start and loudness are measured on the file", measuring_a_file)

print()
shutil.rmtree(DATA, ignore_errors=True)
if FAILED:
    print(f"{len(FAILED)} check(s) failed - {', '.join(n for n, _ in FAILED)}")
    sys.exit(1)
print(f"All checks passed. {OK} ok")
