"""Meme sounds for a clip: the catalogue, a downloaded shelf of them, and a mixer that puts them on a timeline.

`meme.py` synthesises nine noises with numpy and bakes one gag onto a clip. That is a fixed set: you get an airhorn
and a sad trombone, and nothing else. This module is the other half — it reaches DankMachine's free catalogue (38k
sounds, no key), keeps the ones a person actually picked on this machine, and mixes several of them onto one clip at
exact times so a sound can land on any beat, not only the payoff.

Three separate jobs, kept apart on purpose:

    the catalogue    search, a "describe the moment" lookup, trending, and one sound by slug
    the shelf        the mp3s downloaded from the catalogue, so a render never needs the network
    the mix          several sounds at chosen times, mixed under the clip's own voice

Nothing here is on the render path unless a clip carries cues, so a PeakCut with no internet still makes clips
exactly as before.

The catalogue says plainly that rights are unverified (`rights_status: "unverified"`, `commercial_use: "unknown"`),
so every row keeps those two words and the page shows them. PeakCut never claims a sound is free to use.
"""
from __future__ import annotations

import json
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

import httpx

from . import config, media, safe

BASE = "https://dankmachine.com/api/v1"
UA = "PeakCut/1.0 (+https://github.com/haziqahmedqasmi/peakcut) meme-sounds"
TIMEOUT = 20.0
CACHE_SECONDS = 60.0          # the catalogue caches for 60 s on its side, so matching it here costs nothing
LISTED = 30                   # the most rows one answer ever carries
MIX_SECONDS = 300             # one clip is seconds; a stalled ffmpeg is stopped, not waited on
SR = 48000
MAX_CUES = 12                 # a fifteen second clip with twelve sounds on it is noise, not a joke
MIN_GAP = 0.35                # two sounds closer together than this arrive as one click
SLUG = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")

_lock = threading.Lock()
_cache: Dict[str, tuple] = {}          # key -> (when, answer), only ever in memory: a list is cheap to ask again


# ---------------------------------------------------------------- where the shelf lives

def home() -> Path:
    """The folder the catalogue downloads into. Created on demand, never at import."""
    return config.DATA_DIR / "memesounds"


def shelf() -> Path:
    """The mp3s themselves."""
    return home() / "sounds"


def _made(folder: Path) -> Path:
    """mkdir that says something useful when it cannot."""
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise RuntimeError(f"PeakCut cannot write its meme sound folder {folder}: {safe.friendly(e)}")
    return folder


# ---------------------------------------------------------------- the catalogue

def _get(path: str, params: Optional[dict] = None) -> dict:
    """One read from the catalogue, remembered for a minute.

    A failure is raised as `CatalogueDown` with the words a page can show, because "no sounds found" and "the
    catalogue could not be reached" are different sentences and only one of them is the person's fault."""
    key = path + "?" + "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    try:
        r = httpx.get(BASE + path, params=params or {}, headers={"User-Agent": UA}, timeout=TIMEOUT,
                      follow_redirects=True)
    except httpx.HTTPError as e:
        raise CatalogueDown(f"The meme sound catalogue could not be reached: {str(e)[:120]}") from e
    if r.status_code != 200:
        raise CatalogueDown(f"The meme sound catalogue answered {r.status_code}.")
    try:
        body = r.json()
    except ValueError as e:
        raise CatalogueDown("The meme sound catalogue answered with something that is not JSON.") from e
    if not isinstance(body, dict):
        raise CatalogueDown("The meme sound catalogue answered with something that is not a record.")
    _cache[key] = (time.time(), body)
    return body


class CatalogueDown(RuntimeError):
    """The catalogue could not be read. Says so in words a page can print."""


def clean(row: dict) -> dict:
    """One catalogue row, cut down to the keys this app promises.

    Every field is carried only when the catalogue actually sent it. A missing popularity stays missing rather
    than becoming a zero, because a zero would rank an unknown sound last on invented evidence."""
    row = row if isinstance(row, dict) else {}
    out = {
        "slug": str(row.get("slug") or "")[:80],
        "title": str(row.get("title") or "").strip()[:120],
        "about": str(row.get("about") or "").strip()[:400],
        "category": str(row.get("category") or "").strip()[:40],
        "moods": [str(m)[:24] for m in (row.get("moods") or []) if m][:6],
        "use_cases": [str(u)[:24] for u in (row.get("use_cases") or []) if u][:6],
        "audio_url": str(row.get("audio_url") or "").strip(),
        "page": str(row.get("page_url") or "").strip(),
        "rights": str(row.get("rights_status") or "unverified")[:20],
        "commercial": str(row.get("commercial_use") or "unknown")[:20],
    }
    pop = row.get("popularity")
    if isinstance(pop, (int, float)) and pop >= 0:
        out["popularity"] = int(pop)
    return out


def _rows(body: dict) -> List[dict]:
    rows = body.get("sounds")
    if not isinstance(rows, list):
        return []
    return [c for c in (clean(r) for r in rows if isinstance(r, dict)) if c["slug"] and c["audio_url"]]


def search(text: str, limit: int = 12) -> List[dict]:
    """Sounds by name, alias, tag, mood or use case."""
    word = str(text or "").strip()[:80]
    if not word:
        return []
    return _rows(_get("/search", {"q": word, "limit": str(max(1, min(LISTED, int(limit))))}))


def reaction(situation: str) -> List[dict]:
    """Sounds for a described moment: "he loses the game in the last second"."""
    said = str(situation or "").strip()[:200]
    if not said:
        return []
    return _rows(_get("/reaction", {"situation": said}))


def trending(window: str = "24h") -> List[dict]:
    """What people are playing right now. `window` is rising, 1h, 24h or 7d."""
    win = str(window or "24h").strip()
    if win not in ("rising", "1h", "24h", "7d"):
        win = "24h"
    return _rows(_get("/trending", {"window": win}))


def one(slug: str) -> Optional[dict]:
    """One sound by slug, or None when the catalogue does not have it."""
    name = str(slug or "").strip()
    if not SLUG.match(name):
        return None
    try:
        body = _get(f"/sounds/{name}")
    except CatalogueDown:
        return None
    row = body.get("sound") if isinstance(body.get("sound"), dict) else body
    got = clean(row if isinstance(row, dict) else {})
    return got if got.get("slug") and got.get("audio_url") else None


# ---------------------------------------------------------------- ranking that fixes the catalogue's order
# The catalogue's own "describe a moment" answer comes back with popularity 0 on the top rows and non-English
# titles in front of the obvious pick. Ordering is a judgement this app can make better, so it makes it here,
# using only what the catalogue sent.

_MOOD_HINT = {
    "funny": ("funny", "comedy", "punchline", "joke", "laugh"),
    "fail": ("fail", "failure", "loss", "lose", "lost", "sad", "defeat"),
    "win": ("win", "victory", "won", "success", "champion"),
    "hype": ("hype", "hype", "energy", "loud", "drop", "impact", "epic"),
    "shock": ("surprise", "shock", "twist", "reveal", "gasp"),
    "awkward": ("awkward", "silence", "cringe", "uncomfortable"),
    "sad": ("sad", "emotional", "cry", "tear", "heartbreak"),
    "angry": ("angry", "rage", "mad", "furious"),
    "scary": ("scary", "horror", "fear", "creepy", "jumpscare"),
}


def _ascii_ish(text: str) -> bool:
    """Whether a title can be read at a glance by most people looking at this page."""
    return all(ord(ch) < 0x2E80 for ch in str(text or ""))


def rank(rows: Iterable[dict], want: str = "") -> List[dict]:
    """Order rows by how likely they are to be the sound someone meant.

    Popularity is the strongest signal the catalogue offers, so it leads. A title that cannot be read at a glance
    is pushed down but never dropped, and a row whose title or tags share a word with `want` is lifted."""
    word = str(want or "").lower()
    seed = set(re.findall(r"[a-z]{3,}", word))

    def key(row: dict) -> tuple:
        title = str(row.get("title") or "").lower()
        tags = " ".join(row.get("moods") or []) + " " + " ".join(row.get("use_cases") or [])
        share = len(seed & set(re.findall(r"[a-z]{3,}", title + " " + tags)))
        pop = row.get("popularity")
        pop = int(pop) if isinstance(pop, int) else -1        # unknown popularity sorts under a known zero
        return (-share, -pop, 0 if _ascii_ish(row.get("title")) else 1, str(row.get("title") or ""))

    return sorted(rows, key=key)


def find(situation: str, limit: int = 8) -> List[dict]:
    """The best sounds for a described moment, ranked here rather than taken in the catalogue's order."""
    got = rank(reaction(situation), situation)
    if got:
        return got[:limit]
    # No answer for that sentence: fall back to a plain search of its longest words, so a quiet catalogue still
    # answers with something the person can listen to instead of an empty page.
    words = sorted({w for w in re.findall(r"[a-z]{4,}", str(situation or "").lower())}, key=len, reverse=True)
    for w in words[:3]:
        got = rank(search(w), w)
        if got:
            return got[:limit]
    return []


# ---------------------------------------------------------------- the shelf: downloads, so a render is offline

def path_for(slug: str) -> Path:
    """Where one sound is kept, whether or not it exists yet."""
    name = str(slug or "").strip()
    if not SLUG.match(name):
        raise ValueError("That is not a sound name PeakCut can keep.")
    return shelf() / f"{name}.mp3"


def kept(slug: str) -> bool:
    """Whether a sound is already on this machine."""
    try:
        p = path_for(slug)
        return p.is_file() and p.stat().st_size > 512
    except (ValueError, OSError):
        return False


def take(slug: str, audio_url: str = "", title: str = "") -> Path:
    """Download one sound to the shelf, or answer with the copy already there.

    The file is written to a temporary name and moved, so a half-downloaded mp3 is never left where a render
    would find it and mix a broken half second of audio into a clip."""
    dst = path_for(slug)
    if kept(slug):
        return dst
    url = str(audio_url or "").strip()
    if not url:
        # The catalogue is asked whenever there is no direct address, whatever the title — a page that
        # passes a display name but no URL is the normal case, and the slug is what finds the file.
        row = one(slug)
        url = (row or {}).get("audio_url", "")
    if not url:
        raise RuntimeError(f"PeakCut does not know where to get the sound {slug}.")
    _made(shelf())
    tmp = dst.with_suffix(".part")
    try:
        with httpx.stream("GET", url, headers={"User-Agent": UA}, timeout=60.0, follow_redirects=True) as r:
            if r.status_code != 200:
                raise RuntimeError(f"The sound {slug} answered {r.status_code}, so it was not kept.")
            with tmp.open("wb") as fh:
                for chunk in r.iter_bytes(65536):
                    fh.write(chunk)
    except httpx.HTTPError as e:
        _drop(tmp)
        raise RuntimeError(f"The sound {slug} could not be downloaded: {str(e)[:120]}")
    except OSError as e:
        _drop(tmp)
        raise RuntimeError(f"PeakCut could not save {slug}: {safe.friendly(e)}")
    if not tmp.is_file() or tmp.stat().st_size <= 512:
        _drop(tmp)
        raise RuntimeError(f"The sound {slug} downloaded empty, so it was not kept.")
    try:
        tmp.replace(dst)
    except OSError as e:
        _drop(tmp)
        raise RuntimeError(f"PeakCut could not keep {slug}: {safe.friendly(e)}")
    remember(slug, title)
    return dst


MAX_UPLOAD = 8 * 1024 * 1024      # a sound effect over 8 MB is not a sound effect


def store(slug: str, data: bytes, title: str = "") -> Path:
    """Put bytes the person uploaded on the shelf, with the same care `take` uses for a download.

    The bytes are written to a temporary name and moved, and the caller is expected to prove with ffprobe
    that they are really audio BEFORE calling this — a shelf entry that will not decode is worse than a
    missing one, because a render would find it."""
    dst = path_for(slug)
    if not isinstance(data, (bytes, bytearray)) or len(data) < 512:
        raise ValueError("That file is too small to be a sound.")
    if len(data) > MAX_UPLOAD:
        raise ValueError("That file is over 8 MB. A sound effect does not need to be.")
    _made(shelf())
    tmp = dst.with_suffix(".part")
    try:
        tmp.write_bytes(bytes(data))
        tmp.replace(dst)
    except OSError as e:
        _drop(tmp)
        raise RuntimeError(f"PeakCut could not keep {slug}: {safe.friendly(e)}")
    remember(slug, title, {"source": "uploaded"})
    return dst


def make_slug(title: str) -> str:
    """A shelf name from a file name: mine- + the letters that survive, so uploads cannot collide with
    catalogue slugs and two uploads of the same name still land as two sounds."""
    raw = "".join(ch if (ch.isascii() and (ch.isalnum() or ch in "._-")) else "-" for ch in str(title or "").lower())
    name = re.sub(r"-{2,}", "-", raw.strip("-."))[:48].strip("-.")
    name = name or "sound"
    slug = f"mine-{name}"
    n = 2
    while path_for(slug).exists():
        slug = f"mine-{name}-{n}"
        n += 1
    return slug


def _drop(path: Path):
    try:
        path.unlink()
    except OSError:
        pass


def _index_file() -> Path:
    return home() / "index.json"


def _index() -> dict:
    """The small record of what each kept sound is, so the shelf can be drawn without the catalogue."""
    try:
        got = json.loads(_index_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return got if isinstance(got, dict) else {}


def remember(slug: str, title: str = "", extra: Optional[dict] = None):
    """Note what a kept sound is called, so the shelf has labels without asking the catalogue again."""
    with _lock:
        got = _index()
        row = got.get(slug) if isinstance(got.get(slug), dict) else {}
        row["title"] = str(title or row.get("title") or slug)[:120]
        row["at"] = time.time()
        for k, v in (extra or {}).items():
            if v not in (None, ""):
                row[k] = v
        got[slug] = row
        try:
            _made(home())
            tmp = _index_file().with_suffix(".part")
            tmp.write_text(json.dumps(got, ensure_ascii=False, indent=1), encoding="utf-8")
            tmp.replace(_index_file())
        except OSError:
            pass                      # a missing label is a small loss; a failed render is a big one


def library() -> List[dict]:
    """Every sound kept on this machine, newest first, with its length when PeakCut knows it."""
    got = _index()
    out = []
    try:
        files = sorted(shelf().glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        files = []
    for p in files:
        slug = p.stem
        row = got.get(slug) if isinstance(got.get(slug), dict) else {}
        out.append({"slug": slug, "title": str(row.get("title") or slug)[:120],
                    "seconds": round(length(p), 2), "bytes": p.stat().st_size})
    return out


def forget(slug: str) -> bool:
    """Remove one sound from the shelf. Answers whether anything was removed."""
    try:
        p = path_for(slug)
    except ValueError:
        return False
    gone = False
    try:
        p.unlink()
        gone = True
    except OSError:
        pass
    with _lock:
        got = _index()
        if slug in got:
            got.pop(slug, None)
            gone = True
            try:
                _index_file().write_text(json.dumps(got, ensure_ascii=False, indent=1), encoding="utf-8")
            except OSError:
                pass
    return gone


_lengths: Dict[str, float] = {}


def _ffprobe(path: Union[str, Path]) -> dict:
    """What ffprobe says about a file: its length and which kinds of track it has.

    `media.probe` is not usable here on purpose — it is a video prober and refuses a file with no picture, which
    every sound on the shelf is. This one asks the same tool the plain question and never raises on a good file."""
    try:
        p = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams",
                            str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           creationflags=media.NO_WINDOW, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise RuntimeError(f"ffprobe could not read {Path(path).name}: {safe.friendly(e)}")
    if p.returncode != 0:
        raise RuntimeError(f"ffprobe could not read {Path(path).name}: {(p.stderr or '').strip()[-160:]}")
    try:
        data = json.loads(p.stdout or "{}")
    except ValueError as e:
        raise RuntimeError(f"ffprobe answered with something that is not JSON for {Path(path).name}") from e
    streams = data.get("streams") or []
    fmt = data.get("format") or {}
    try:
        dur = float(fmt.get("duration") or 0.0)
    except (TypeError, ValueError):
        dur = 0.0
    if dur <= 0:                                  # some containers leave it off the format and put it on a stream
        for s in streams:
            try:
                dur = max(dur, float(s.get("duration") or 0.0))
            except (TypeError, ValueError):
                continue
    return {"duration": dur,
            "video": any(s.get("codec_type") == "video" for s in streams),
            "audio": any(s.get("codec_type") == "audio" for s in streams)}


def length(path: Union[str, Path]) -> float:
    """How long a sound is, in seconds. One ffprobe per file, remembered."""
    key = str(path)
    if key in _lengths:
        return _lengths[key]
    try:
        secs = float(_ffprobe(path)["duration"] or 0.0)
    except Exception:                 # noqa: BLE001 - an unknown length is 0 and the caller decides what to do
        secs = 0.0
    _lengths[key] = secs
    return secs


# ---------------------------------------------------------------- the mix

def cue_ok(cue: dict) -> Optional[str]:
    """Check one cue, answering `None` when it is usable and a sentence when it is not.

    A cue is `{"slug", "at", "volume", "end"}`. Times are seconds from the start of the clip. `end` is where the
    sound is cut, which is how a long sound is trimmed to a punch instead of running over the next line."""
    if not isinstance(cue, dict):
        return "That sound cue is not a record."
    slug = str(cue.get("slug") or "").strip()
    if not slug:
        return "A sound cue needs a sound."
    if not SLUG.match(slug):
        return f"{slug!r} is not a sound name PeakCut can mix."
    if not kept(slug):
        return f"The sound {slug} is not on this machine yet. Add it from the meme sounds page first."
    try:
        at = float(cue.get("at"))
    except (TypeError, ValueError):
        return f"The cue for {slug} has no time on the timeline."
    if at < -0.5:
        return f"The cue for {slug} starts before the clip does."
    end = cue.get("end")
    # Zero means "play the whole sound", the same as leaving it out. The editor sends 0 for its "Whole sound"
    # choice, and reading that as a real end time refused every cue the page sent with "ends before it starts",
    # so nothing could be saved at all and the Save button looked broken.
    if end not in (None, ""):
        try:
            when = float(end)
        except (TypeError, ValueError):
            return f"The cue for {slug} has an end time that is not a number."
        if when and when <= at:
            return f"The cue for {slug} ends before it starts."
    return None


def tidy(cues: Sequence[dict], limit: int = MAX_CUES) -> List[dict]:
    """Keep the cues that can be mixed, in time order, with sane numbers.

    Two cues closer than `MIN_GAP` would be heard as one click, so the later one is moved later rather than
    dropped: the person asked for two sounds and should get two."""
    out: List[dict] = []
    for cue in list(cues or [])[: limit * 2]:
        if cue_ok(cue):
            continue
        got = {"slug": str(cue["slug"]).strip(), "at": max(0.0, float(cue["at"]))}
        try:
            got["volume"] = max(-30.0, min(12.0, float(cue.get("volume") or 0.0)))
        except (TypeError, ValueError):
            got["volume"] = 0.0
        end = cue.get("end")
        # Zero is "play the whole sound", so it is stored as no end at all. Storing it as a real number
        # capped every such cue at a twentieth of a second, which is a click rather than a sound.
        if end not in (None, ""):
            try:
                when = float(end)
            except (TypeError, ValueError):
                when = 0.0
            if when:
                got["end"] = max(got["at"] + 0.05, when)
        if str(cue.get("title") or "").strip():
            got["title"] = str(cue["title"])[:120]
        out.append(got)
    out.sort(key=lambda c: c["at"])
    spaced: List[dict] = []
    for cue in out:
        if spaced and cue["at"] - spaced[-1]["at"] < MIN_GAP:
            cue = dict(cue, at=round(spaced[-1]["at"] + MIN_GAP, 3))
        spaced.append(cue)
    return spaced[:limit]


def mix(short: Union[str, Path], cues: Sequence[dict], out: Union[str, Path],
        voice: float = 0.0) -> Path:
    """Mix several sounds onto a clip at their times, keeping the clip's own audio underneath.

    The picture is copied rather than re-encoded: only the sound changes, so this costs a second and cannot change
    a single frame. Returns `out` on success and raises with a plain sentence when the mix cannot be made.

    `voice` is dB applied to the clip's own audio (0 leaves it alone), which is how the whole track can be pushed
    down a little to make room without touching each cue."""
    src, dst = Path(short), Path(out)
    if not src.is_file():
        raise RuntimeError(f"no such clip: {src.name}")
    plan = tidy(cues)
    if not plan:
        raise ValueError("There is nothing to mix: no cue on this clip survived a look at its numbers.")
    info = _ffprobe(src)
    dur = float(info.get("duration") or 0.0)
    if dur <= 0:
        raise RuntimeError(f"{src.name} reports no length, so no sound can be placed on it.")
    has_audio = bool(info.get("audio"))
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise RuntimeError(f"the folder for {dst.name} cannot be written: {safe.friendly(e)}")

    # Only sounds that start inside the clip can be heard. One that starts after the end is a mistake in the plan,
    # not a reason to fail a render, so it is left out and the rest still land.
    heard = [c for c in plan if c["at"] < dur]
    if not heard:
        raise ValueError(f"Every sound on this clip starts after it ends ({dur:.1f} s).")
    missing = [c["slug"] for c in heard if not kept(c["slug"])]
    if missing:
        raise RuntimeError("These sounds are not on this machine: " + ", ".join(sorted(set(missing))))

    parts: List[str] = []
    if has_audio:
        # The clip's own audio is padded to its full length first, so it is never the short side of the mix: a
        # sound that starts at 9 s on an 11 s clip must not decide how long the result is.
        parts.append(f"[0:a]volume={voice:.1f}dB,apad,atrim=0:{dur:.3f}[base]" if voice
                     else f"[0:a]apad,atrim=0:{dur:.3f}[base]")
    labels: List[str] = ["base"] if has_audio else []
    args: List[str] = ["ffmpeg", "-y", "-v", "error", "-i", str(src)]
    # Counted by hand, not derived from `len(args)`: those flags are not inputs, and a filter graph that names the
    # wrong stream index fails with nothing but "Invalid argument" to go on.
    feeds = 1

    for i, cue in enumerate(heard):
        sound = path_for(cue["slug"])
        length_s = length(sound)
        if length_s <= 0:
            continue
        span = length_s
        if cue.get("end"):
            span = min(span, max(0.05, float(cue["end"]) - cue["at"]))
        span = min(span, max(0.05, dur - cue["at"]))
        if span < 0.05:
            continue
        ms = int(round(cue["at"] * 1000))
        vol = float(cue.get("volume") or 0.0)
        args += ["-i", str(sound)]
        parts.append(f"[{feeds}:a]atrim=0:{span:.3f},asetpts=PTS-STARTPTS,"
                     f"volume={vol:.1f}dB,adelay={ms}|{ms}[s{i}]")
        labels.append(f"s{i}")
        feeds += 1

    if not labels:
        raise RuntimeError("None of the sounds on this clip could be placed.")
    if len(labels) == 1:
        # One input and nothing to mix with: the clip simply keeps its own audio.
        parts.append("[base]alimiter=limit=0.95[aout]") if has_audio else parts.append("[base]anull[aout]")
    else:
        # Every part is already padded to the clip's own length or shorter, so `longest` cannot outrun the clip;
        # the `-t` on the output is the belt to this braces.
        parts.append("".join(f"[{n}]" for n in labels) +
                     f"amix=inputs={len(labels)}:duration=longest:dropout_transition=0:normalize=0[mixed]")
        parts.append("[mixed]alimiter=limit=0.95,loudnorm=I=-14:TP=-1.5:LRA=11[aout]")

    cmd = args + ["-filter_complex", ";".join(parts), "-map", "0:v", "-map", "[aout]",
                  "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", str(SR),
                  "-movflags", "+faststart", "-t", f"{dur:.3f}", str(dst)]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           creationflags=media.NO_WINDOW, timeout=MIX_SECONDS)
    except (OSError, subprocess.TimeoutExpired) as e:
        _drop(dst)
        raise RuntimeError(f"ffmpeg could not mix the sounds: {safe.friendly(e)}")
    if p.returncode != 0 or not dst.is_file() or dst.stat().st_size == 0:
        _drop(dst)
        raise RuntimeError("ffmpeg could not mix the sounds: " + ((p.stderr or "").strip()[-300:] or "no reason given"))
    return dst


def describe(plan: Sequence[dict]) -> str:
    """One line about what is on a clip, for a card or a log."""
    got = tidy(plan)
    if not got:
        return "No meme sounds on this clip."
    bits = [f"{c['slug']} at {c['at']:.1f}s" for c in got]
    return f"{len(got)} meme sound{'s' if len(got) != 1 else ''}: " + ", ".join(bits)
