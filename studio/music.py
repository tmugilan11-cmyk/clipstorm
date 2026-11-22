"""Music beds for a finished clip: four synthesised moods, ducked under the speech and normalised to about -14 LUFS."""
from __future__ import annotations

import json
import os
import subprocess
import wave
from pathlib import Path
from typing import Optional, Union

from . import config, safe

try:
    import numpy as np
    AVAILABLE = True
except Exception:  # noqa: BLE001 - a broken install is the same as no install
    np = None                 # type: ignore[assignment]
    AVAILABLE = False

Pathish = Union[str, os.PathLike]

SR = 48000                # every bed is written at this rate, and the mix runs at it
LOOP_BARS = 4             # a bed is four bars: the loop length is exact, so it repeats without a gap
TARGET_LUFS = -14.0       # what the finished mix is brought to, the same target render.py uses
BED_DB = -14.0            # the bed starts this far down, before the voice pushes it further under
FADE_IN, FADE_OUT = 0.3, 0.5
DUCK = "threshold=0.05:ratio=6:attack=15:release=350:makeup=1"   # the voice key, as in gta6-clipper's meme.py
PROBE_SECONDS = 60
MIX_SECONDS = 900         # one clip is seconds, never hours; a stalled ffmpeg is stopped, not waited on

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# label and hint are the page's words; the numbers are what bed_loop() plays. Nothing is sampled: every sound is
# built from a sine, a saw and a noise burst, so the beds ship with PeakCut and belong to nobody else.
MOODS: dict = {
    "hype": {"label": "Hype", "hint": "fast and loud: a big play, a win, a run",
             "bpm": 128, "kick": (0, 4, 8, 12), "hat": True, "notes": (0, 0, 3, 5), "shape": "saw",
             "root": 55.0, "lowpass": 5000},
    "chill": {"label": "Chill", "hint": "slow and warm: a talk, a story, a drive",
              "bpm": 80, "kick": (0, 10), "hat": False, "notes": (0, 3, 5, 3), "shape": "sin",
              "root": 55.0, "lowpass": 2500},
    "tense": {"label": "Tense", "hint": "a held breath: a chase, a near miss, a wait",
              "bpm": 90, "kick": (0, 8), "hat": False, "notes": (0, 0, 1, 0), "shape": "saw",
              "root": 41.2, "lowpass": 2500},
    "funny": {"label": "Funny", "hint": "bouncy and light: a fail, a joke, a reaction",
              "bpm": 110, "kick": (0, 6, 8, 14), "hat": True, "notes": (0, 4, 7, 4), "shape": "sin",
              "root": 82.4, "lowpass": 2500},
}


# ---------------------------------------------------------------- where beds live
def bed_path(mood: str, out_dir: Optional[Pathish] = None) -> Path:
    """The wav one mood's bed is kept in: `<out_dir>/bed_<mood>.wav`, or PeakCut's data folder when none is given."""
    return Path(out_dir or (config.DATA_DIR / "music")) / f"bed_{_mood(mood)}.wav"


def _mood(mood: str) -> str:
    """A known mood, or "chill" for anything else, so one bad word in a request cannot fail a render."""
    key = str(mood or "").strip().lower()
    if key in MOODS:
        return key
    print(f"Music: no mood called {key or '(none)'}, using chill. The moods are {', '.join(MOODS)}.", flush=True)
    return "chill"


# ---------------------------------------------------------------- synthesis
def _t(d: float):
    return np.arange(int(d * SR)) / SR


def _env(n: int, attack: float = 0.005, release: float = 0.05):
    """A flat shape with a short fade at each end, so a note starts and stops without a click."""
    e = np.ones(n)
    na, nr = max(int(attack * SR), 1), max(int(release * SR), 1)
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] = np.minimum(e[-nr:], np.linspace(1, 0, nr))
    return e


def _lowpass(x, cutoff: float, n: int = 3):
    """A gentle low-pass, done in the frequency domain: a bed has no reason to hiss."""
    x = np.asarray(x)
    spectrum = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    spectrum *= 1 / (1 + (f / cutoff) ** (2 * n))
    return np.fft.irfft(spectrum, len(x))


def _normalise(x, peak_db: float = -3.0):
    """Scale a bed to one peak level, so every mood arrives at the mixer equally loud."""
    return np.asarray(x) / (np.abs(x).max() + 1e-9) * 10 ** (peak_db / 20)


def _kick(d: float = 0.25):
    t = _t(d)
    return np.sin(2 * np.pi * (45 * t + 90 * (1 - np.exp(-t * 30)) / 30)) * np.exp(-t * 14)


def _hat(d: float = 0.06, seed: int = 3):
    return np.random.RandomState(seed).randn(int(d * SR)) * np.exp(-_t(d) * 60)


def _note(f: float, d: float, shape: str = "saw"):
    """One held note: a saw for anything that should bite, a sine for anything that should sit back."""
    t = _t(d)
    w = (2 * ((t * f) % 1) - 1) if shape == "saw" else np.sin(2 * np.pi * f * t)
    return w * _env(len(t), 0.01, 0.06)


def bed_loop(mood: str) -> "np.ndarray":
    """One four-bar loop of the mood, mono float samples at 48 kHz, peaking at -3 dB.

    The kick, the optional hats and a four-note figure are placed on a sixteenth grid; the whole loop is then
    low-passed, which is what turns a row of beeps into something that sits under a voice."""
    key = _mood(mood)
    m = MOODS[key]
    step = 60 / m["bpm"] / 4                       # one sixteenth, in seconds
    n = int(LOOP_BARS * 16 * step * SR)
    x = np.zeros(n + SR)                           # room for the last note's tail, cut off below
    bars = LOOP_BARS

    def put(y, at: float, gain: float = 1.0):
        i = int(at * step * SR)
        x[i:i + len(y)] += y * gain

    for bar in range(bars):
        for k in m["kick"]:
            put(_kick(), bar * 16 + k)
        if m["hat"]:
            for k in range(2, 16, 4):
                put(_hat(), bar * 16 + k, 0.35)
        for q in range(4):
            f = m["root"] * 2 ** (m["notes"][(bar + q) % 4] / 12)
            put(_note(f, step * 3.5, m["shape"]), bar * 16 + q * 4, 0.7 if key == "tense" else 0.45)
    return _normalise(_lowpass(x[:n], m["lowpass"]), -3)


def _write_wav(path: Path, x) -> Path:
    """Write mono 16-bit PCM through a temporary file: a render reading this name never sees half a bed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{os.getpid()}.tmp")
    try:
        with wave.open(str(tmp), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((np.clip(x, -1.0, 1.0) * 32767).astype("<i2").tobytes())
        os.replace(tmp, path)
    except Exception:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    return path


def make_beds(out_dir: Pathish) -> dict:
    """Synthesise one wav per mood into `out_dir` and return {mood: path} for the ones that were written.

    A mood that could not be made is reported on one line and simply left out of the result; this never raises."""
    made: dict = {}
    out = Path(out_dir)
    if not AVAILABLE:
        print("Music beds need numpy, which is not installed here. Clips still render, without music.", flush=True)
        return made
    try:
        out.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Music beds: could not use {safe.friendly(e)}. Clips still render, without music.", flush=True)
        return made
    for mood in MOODS:
        try:
            made[mood] = _write_wav(bed_path(mood, out), bed_loop(mood))
        except Exception as e:  # noqa: BLE001 - one bed failing is not a failed render
            print(f"Music bed {mood}: {safe.friendly(e)}", flush=True)
    return made


# ---------------------------------------------------------------- mixing a bed under a clip
def _info(src: Path) -> tuple:
    """(seconds, has_video, has_audio) for a clip, read with ffprobe. Raises when it cannot be read."""
    p = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(src)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       creationflags=NO_WINDOW, timeout=PROBE_SECONDS)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or "ffprobe could not read the clip").strip()[-300:])
    data = json.loads(p.stdout or "{}")
    duration = float((data.get("format") or {}).get("duration") or 0.0)
    kinds = {s.get("codec_type") for s in data.get("streams") or []}
    return duration, "video" in kinds, "audio" in kinds


def _filter(duration: float) -> str:
    """The graph: the clip's own sound is split three ways - one copy to keep, one to key the ducker with, one to
    mix - and the bed, faded in and out, is turned down whenever that key is loud."""
    bed = (f"[1:a]aresample={SR},aformat=channel_layouts=stereo,atrim=0:{duration:.3f},volume={BED_DB}dB,"
           f"afade=t=in:d={FADE_IN},afade=t=out:st={max(duration - FADE_OUT, 0):.3f}:d={FADE_OUT}[bk]")
    duck = f"[bk][k]sidechaincompress={DUCK}[bdk]"
    mix = (f"[m][bdk]amix=inputs=2:normalize=0:duration=first,"
           f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=9,atrim=0:{duration:.3f}[ao]")
    return (f"[0:a]aresample={SR},aformat=channel_layouts=stereo,asplit=3[sp][k][m];"
            f"{bed};{duck};{mix};[sp]anullsink")


def apply(short: Pathish, mood: str, out: Pathish) -> Path:
    """Put one mood's bed under a finished clip, ducked by the clip's own voice and brought to about -14 LUFS.

    The picture is copied, never re-encoded. Returns `out` on success, and `short` untouched on any failure with
    one line saying why, so a render that asks for music can never fail because of the music."""
    src, dst = Path(short), Path(out)
    key = _mood(mood)
    backup = src                                          # what the caller keeps if anything goes wrong
    if not AVAILABLE:
        print("Music needs numpy, which is not installed here. The clip is unchanged.", flush=True)
        return backup
    if not src.is_file():
        print(f"Music: {src.name} is not there. The clip is unchanged.", flush=True)
        return backup

    bed = bed_path(key)
    if not bed.is_file():
        made = make_beds(bed.parent)
        bed = made.get(key, bed)
    if not bed.is_file():
        print(f"Music: the {key} bed could not be made. The clip is unchanged.", flush=True)
        return backup

    try:
        duration, has_video, has_audio = _info(src)
    except Exception as e:  # noqa: BLE001 - no probe, no music
        print(f"Music: {safe.friendly(e)} The clip is unchanged.", flush=True)
        return backup
    if not has_audio:
        print("Music: this clip has no sound to duck under, so it is left as it is.", flush=True)
        return backup
    if duration <= 0:
        print("Music: this clip reports no length, so it is left as it is.", flush=True)
        return backup

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Music: could not use {safe.friendly(e)}. The clip is unchanged.", flush=True)
        return backup

    # A bed is written at 48 kHz; the codec follows the file the caller asked for, so a .wav test stays a wav.
    audio = ["-c:a", "pcm_s16le"] if dst.suffix.lower() in (".wav", ".flac") else ["-c:a", "aac", "-b:a", "192k"]
    video = ["-map", "0:v", "-c:v", "copy"] if has_video else []
    faststart = ["-movflags", "+faststart"] if dst.suffix.lower() in (".mp4", ".mov", ".m4v") else []
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-stream_loop", "-1", "-i", str(bed),
           "-filter_complex", _filter(duration), *video, "-map", "[ao]", "-t", f"{duration:.3f}",
           *audio, "-ar", str(SR), *faststart, str(dst)]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           creationflags=NO_WINDOW, timeout=MIX_SECONDS)
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"Music: {safe.friendly(e)} The clip is unchanged.", flush=True)
        _discard(dst)
        return backup
    if p.returncode != 0 or not dst.is_file() or dst.stat().st_size == 0:
        print(f"Music: ffmpeg could not mix the {key} bed: {(p.stderr or '').strip()[-400:]}", flush=True)
        _discard(dst)
        return backup
    return dst


def _discard(path: Path):
    """A half-written mix is worse than no mix: remove it so the next run starts clean."""
    try:
        path.unlink()
    except OSError:
        pass
