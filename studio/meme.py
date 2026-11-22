"""One synthesised sound plus one visual gag (freeze, push-in, vignette, shake) baked onto a clip at its payoff."""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import wave
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union

from . import config
from .media import NO_WINDOW, run

try:
    import numpy as np
    AVAILABLE = True           # numpy makes every shipped sound, so without it there is nothing to play
except Exception:              # a machine without numpy still boots; only the gag is unavailable
    np = None                  # type: ignore[assignment]
    AVAILABLE = False

SR = 48000                     # every sound is made and mixed at this rate
HOOK_SAFE = 3.0                # a gag never lands in the first seconds, that is the hook
MAX_EXT = 3.0                  # a meme ending may stretch a clip by at most this many seconds
MIN_CLIP = HOOK_SAFE + 0.4     # shorter than this there is no room for a payoff at all
GAG_SECONDS = 120              # one gag encode; far beyond normal, so a frozen ffmpeg is stopped not waited on

# What the ffmpeg chain understands. A mood carries a list of these.
EFFECTS = ("zoom", "punch", "shake", "flash", "vignette", "desat")
# The four gags named on the page. Each is realised by an effect in the list above, except freeze, which is the
# hold: the frame stops for that many seconds.
TREATMENTS = ("freeze", "push-in", "vignette", "shake")
_TREAT_EFFECT = {"freeze": (), "push-in": ("zoom", "punch"), "vignette": ("vignette",), "shake": ("shake",)}

SOUND_NAME = re.compile(r"^[A-Za-z0-9_./-]{1,60}$")   # a sound is a file under the sounds folder, never a path out
_lock = threading.Lock()       # two picks finishing together must not write the same wav


# ---------------------------------------------------------------- the nine moods
# sound: a name, or a list where the first that exists wins (so your own copy beats the synthesised one).
# effect: what is done to the picture. treatment: the gag that is named and always applied.
# volume: dB on the mix. offset: seconds from the payoff. hold: freeze seconds. tail: "auto" or seconds.
MOODS: Dict[str, dict] = {
    "embarrassing": {"sound": ["mine/hello_darkness", "sad_trombone"], "effect": ["zoom", "vignette", "desat"],
                     "treatment": "freeze", "volume": -3, "offset": 0.0, "hold": 1.2, "tail": "auto"},
    "fail":         {"sound": ["mine/sad_violin", "sad_trombone"], "effect": ["punch", "desat"],
                     "treatment": "push-in", "volume": -2, "offset": 0.1, "hold": 0.0, "tail": "auto"},
    "shock":        {"sound": "vine_boom", "effect": ["punch", "flash"],
                     "treatment": "push-in", "volume": 0, "offset": 0.0, "hold": 0.0, "tail": 0},
    "hype":         {"sound": ["airhorn", "bass_drop"], "effect": ["punch", "shake", "flash"],
                     "treatment": "shake", "volume": -2, "offset": 0.0, "hold": 0.0, "tail": 0},
    "win":          {"sound": "bass_drop", "effect": ["punch", "flash"],
                     "treatment": "push-in", "volume": -2, "offset": -0.15, "hold": 0.0, "tail": 0},
    "awkward":      {"sound": ["mine/curb_enthusiasm", "crickets"], "effect": ["zoom", "desat"],
                     "treatment": "freeze", "volume": -4, "offset": 0.0, "hold": 0.8, "tail": "auto"},
    "cringe":       {"sound": "record_scratch", "effect": ["flash", "desat"],
                     "treatment": "freeze", "volume": -2, "offset": 0.0, "hold": 1.0, "tail": 0.4},
    "funny":        {"sound": ["rimshot", "ding"], "effect": ["punch"],
                     "treatment": "push-in", "volume": -3, "offset": 0.1, "hold": 0.0, "tail": 0.6},
    "suspense":     {"sound": "heartbeat", "effect": ["zoom", "vignette"],
                     "treatment": "vignette", "volume": -3, "offset": -0.3, "hold": 0.0, "tail": 0},
}


def sounds_dir() -> Path:
    """Where the synthesised sounds and moods.json live: the data folder, so a fresh install makes its own."""
    return Path(config.DATA_DIR) / "sounds"


def _need() -> None:
    if not AVAILABLE:
        raise RuntimeError("numpy is needed to make the sounds; install it with: pip install numpy")


def _file() -> Path:
    return sounds_dir() / "moods.json"


def _clean(name: str, spec: object) -> Optional[dict]:
    """One mood, checked field by field. Anything that cannot be read is dropped, never guessed."""
    if not isinstance(spec, dict):
        return None
    sound = spec.get("sound")
    names = [sound] if isinstance(sound, str) else sound
    if not isinstance(names, list) or not names:
        return None
    names = [str(n) for n in names if isinstance(n, str) and SOUND_NAME.match(n)]
    if not names:
        return None
    fx = spec.get("effect")
    fx = [e for e in fx if e in EFFECTS] if isinstance(fx, list) else []
    treat = str(spec.get("treatment") or "")
    if treat not in TREATMENTS:
        treat = "freeze" if float(_num(spec.get("hold"), 0.0)) > 0 else "push-in"
    if not (set(_TREAT_EFFECT[treat]) & set(fx)) and _TREAT_EFFECT[treat]:
        fx.append(_TREAT_EFFECT[treat][0])
    tail = spec.get("tail", 0)
    tail = "auto" if tail == "auto" else _num(tail, 0.0)
    return {"sound": names[0] if len(names) == 1 else names,
            "effect": fx, "treatment": treat,
            "volume": max(-30.0, min(6.0, _num(spec.get("volume"), 0.0))),
            "offset": max(-1.0, min(1.0, _num(spec.get("offset"), 0.0))),
            "hold": max(0.0, min(2.0, _num(spec.get("hold"), 0.0))),
            "tail": tail if tail == "auto" else max(0.0, min(MAX_EXT, float(tail)))}


def _num(v: object, fallback: float) -> float:
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return fallback


def load_moods() -> Dict[str, dict]:
    """The moods in use: what moods.json says, over the defaults, so a half-edited file can never break a render."""
    table = {k: _clean(k, v) for k, v in MOODS.items()}
    table = {k: v for k, v in table.items() if v}
    f = _file()
    try:
        if f.exists():
            saved = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                for name, spec in saved.items():
                    if isinstance(name, str) and name:
                        one = _clean(name, spec)
                        if one:
                            table[name] = one
    except (OSError, ValueError):
        pass                    # an unreadable moods.json is ignored, the defaults still play
    return table


def save_moods(moods: dict) -> Dict[str, dict]:
    """Checks, then writes moods.json in one go, and returns what was saved."""
    if not isinstance(moods, dict):
        raise ValueError("moods must be a dict of mood -> settings")
    table = {}
    for name, spec in moods.items():
        if isinstance(name, str) and name and len(name) <= 40 and re.fullmatch(r"[a-z0-9_-]+", name):
            one = _clean(name, spec)
            if one:
                table[name] = one
    if not table:
        raise ValueError("no usable mood in there")
    f = _file()
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_name(f"{f.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(table, indent=1), encoding="utf-8")
        os.replace(tmp, f)
    except OSError as e:
        raise RuntimeError(f"could not save the moods to {f}: {e}")
    return table


# ---------------------------------------------------------------- synthesis
def _t(d: float) -> "np.ndarray":
    return np.arange(int(d * SR)) / SR


def _env(n: int, a: float = 0.005, r: float = 0.05) -> "np.ndarray":
    e = np.ones(n)
    na, nr = max(int(a * SR), 1), max(int(r * SR), 1)
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] = np.minimum(e[-nr:], np.linspace(1, 0, nr))
    return e


def _lp_fast(x: "np.ndarray", fc: float, n: int = 3) -> "np.ndarray":
    """Low-pass in the frequency domain: a one-pole shape raised to n, which costs one FFT."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / fc) ** (2 * n))
    return np.fft.irfft(X, len(x))


def _bp(x: "np.ndarray", lo: float, hi: float) -> "np.ndarray":
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= (f > lo) & (f < hi)
    return np.fft.irfft(X, len(x))


def _reverb(x: "np.ndarray", tail: float = 0.5, mix: float = 0.25, seed: int = 1) -> "np.ndarray":
    """A short synthetic room: noise decaying away, low-passed, folded back under the dry signal."""
    r = np.random.default_rng(seed)
    n = int(tail * SR)
    ir = r.standard_normal(n) * np.exp(-np.arange(n) / (SR * tail / 5))
    ir = _lp_fast(ir, 3000)
    y = np.fft.irfft(np.fft.rfft(x, len(x) + n) * np.fft.rfft(ir, len(x) + n), len(x) + n)
    y = y / (np.abs(y).max() + 1e-9)
    z = np.zeros(len(y))
    z[: len(x)] = x
    return z * (1 - mix) + y * mix * np.abs(x).max()


def _norm(x: "np.ndarray", peak_db: float = -3.0) -> "np.ndarray":
    return x / (np.abs(x).max() + 1e-9) * 10 ** (peak_db / 20)


def vine_boom() -> "np.ndarray":
    """The sub-bass boom: a falling sine folded over, plus a short thump."""
    t = _t(1.8)
    f = 38 + 120 * np.exp(-t * 14)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.tanh(2.2 * np.sin(ph)) * np.exp(-t * 2.6) + 0.35 * np.sin(2 * ph) * np.exp(-t * 6)
    x += 0.5 * _bp(np.random.default_rng(3).standard_normal(len(t)), 80, 900) * np.exp(-t * 30)
    return _norm(_reverb(x * _env(len(t), 0.002, 0.2), 0.6, 0.18))


def sad_trombone() -> "np.ndarray":
    """Wa-wa-wa-waaah: four muted notes, the last one sagging."""
    notes = [(233.1, .55), (220.0, .55), (207.7, .55), (196.0, 1.5)]
    out: List["np.ndarray"] = []
    for i, (f0, d) in enumerate(notes):
        t = _t(d)
        last = i == 3
        # vibrato and a slow sag on the last note only; the conditional binds to the whole factor, as in the original
        f = f0 * (1 + (0.004 * np.sin(2 * np.pi * 5.5 * t) if last else 0)) * (1 - 0.06 * np.clip((t - 0.5) / 1.0, 0, 1) if last else 1)
        ph = 2 * np.pi * np.cumsum(f) / SR
        wah = 0.25 + 0.75 * np.sin(np.pi * np.clip(t / d, 0, 1)) ** 0.7     # the mute opens, then closes
        x = sum(np.sin(k * ph) * k ** -1.0 * np.exp(-k / (1 + 9 * wah)) for k in range(1, 22))
        x = x + 0.04 * np.random.default_rng(i).standard_normal(len(t))      # breath
        out.append(x * _env(len(t), 0.04, 0.12 if not last else 0.35) * (0.6 + 0.4 * wah))
        out.append(np.zeros(int(0.05 * SR)))
    x = np.concatenate(out)
    return _norm(_reverb(_bp(_lp_fast(x, 2200), 80, 9000), 0.4, 0.15))


def record_scratch() -> "np.ndarray":
    """A needle dragged off the record."""
    t = _t(0.75)
    rng = np.random.default_rng(5)
    f = 900 * np.exp(-t * 2.2) * (1 + 0.5 * np.sin(2 * np.pi * 9 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    saw = 2 * ((ph / (2 * np.pi)) % 1) - 1
    noise = _bp(rng.standard_normal(len(t)), 1500, 9000)
    x = (0.6 * saw + 0.9 * noise) * (0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 14 * t)))
    x += 0.6 * (rng.random(len(t)) > 0.9985) * rng.standard_normal(len(t))   # vinyl crackle, drawn in this order
    return _norm(x * _env(len(t), 0.003, 0.03) * np.exp(-t * 1.5))


def airhorn() -> "np.ndarray":
    """Three short blasts and one long one: the MLG horn chord."""
    out: List["np.ndarray"] = []
    for d in (0.28, 0.28, 0.28, 1.1):
        t = _t(d)
        x = 0
        for f in (415.3, 523.3, 622.3):     # Ab, C, Eb
            ph = 2 * np.pi * np.cumsum(f * (1 + 0.003 * np.sin(2 * np.pi * 7 * t))) / SR
            x = x + sum(np.sin(k * ph) * k ** -0.65 for k in range(1, 16))
        x = np.tanh(0.25 * x) * (1 + 0.15 * np.random.default_rng(1).standard_normal(len(t))) * _env(len(t), 0.012, 0.06 if d < 1 else 0.3)
        out += [x, np.zeros(int(0.07 * SR))]
    return _norm(_reverb(_lp_fast(np.concatenate(out), 5000), 0.5, 0.15))


def bass_drop() -> "np.ndarray":
    """A riser, then the floor falls out."""
    t = _t(2.2)
    f = np.where(t < 0.9, 220 * np.exp(-t * 2.4) + 38, 38 + 0 * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.tanh(1.6 * np.sin(ph)) * np.where(t < 0.9, 0.7, 1.0) * np.exp(-np.maximum(t - 0.9, 0) * 1.4)
    x += 0.5 * _bp(np.random.default_rng(2).standard_normal(len(t)), 2000, 9000) * np.exp(-t * 4) * (t < 0.9)
    return _norm(x * _env(len(t), 0.01, 0.3))


def crickets() -> "np.ndarray":
    """Awkward silence, filled in."""
    t = _t(3.4)
    x = np.zeros(len(t))
    rng = np.random.default_rng(7)
    for f, rate, ph0 in [(4300, 2.6, 0.0), (4750, 2.1, 0.3), (3900, 3.0, 0.6)]:
        gate = (((t * rate + ph0) % 1) < 0.35).astype(float)
        pulse = (np.sin(2 * np.pi * 38 * t) > 0.2).astype(float)             # chirp trains
        x += np.sin(2 * np.pi * f * t) * gate * pulse * 0.4
    x += 0.012 * _lp_fast(rng.standard_normal(len(t)), 1500)                  # night air
    return _norm(x * _env(len(t), 0.2, 0.5), -8)


def heartbeat() -> "np.ndarray":
    """Thump-thump, four times."""
    d = 3.4
    x = np.zeros(int(d * SR))
    for b in np.arange(0.0, d - 0.6, 0.85):
        for off, g, f0 in [(0, 1.0, 62), (0.2, 0.7, 52)]:
            n = int(0.22 * SR)
            t = np.arange(n) / SR
            i = int((b + off) * SR)
            x[i:i + n] += np.sin(2 * np.pi * (f0 + 30 * np.exp(-t * 30)) * t) * np.exp(-t * 18) * g
    return _norm(_reverb(x, 0.3, 0.1), -4)


def whoosh() -> "np.ndarray":
    """A band sweeping up and away."""
    t = _t(0.7)
    n = np.random.default_rng(4).standard_normal(len(t))
    y = np.zeros(len(t))
    fc = 400 + 5500 * np.sin(np.pi * t / 0.7) ** 2
    for lo in range(0, len(t), 480):
        seg = n[lo:lo + 960]
        k = len(seg)
        y[lo:lo + k] += _bp(seg, fc[lo] * .6, fc[lo] * 1.5) * np.hanning(k)
    return _norm(y * np.sin(np.pi * t / 0.7) ** 1.5)


def ding() -> "np.ndarray":
    """A bright bell, three partials."""
    t = _t(1.6)
    x = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, a, d in [(1318.5, 1, 3), (2637, .35, 5), (3951, .15, 8)])
    return _norm(x * _env(len(t), 0.002, 0.05))


def rimshot() -> "np.ndarray":
    """Ba-dum-tss."""
    out = np.zeros(int(1.7 * SR))
    rng = np.random.default_rng(6)

    def drum(at: float, f: float, d: float, noise: float) -> None:
        t = _t(d)
        i = int(at * SR)
        out[i:i + len(t)] += np.sin(2 * np.pi * (f + 90 * np.exp(-t * 40)) * t) * np.exp(-t * 14) \
            + noise * _bp(rng.standard_normal(len(t)), 1500, 9000) * np.exp(-t * 25)

    drum(0.0, 190, 0.25, 0.9)
    drum(0.16, 110, 0.35, 0.1)
    t = _t(1.2)
    i = int(0.42 * SR)
    out[i:i + len(t)] += 0.7 * _bp(rng.standard_normal(len(t)), 5000, 14000) * np.exp(-t * 4)
    return _norm(out)


SOUNDS = {"vine_boom": vine_boom, "sad_trombone": sad_trombone, "record_scratch": record_scratch,
          "airhorn": airhorn, "bass_drop": bass_drop, "crickets": crickets, "heartbeat": heartbeat,
          "whoosh": whoosh, "ding": ding, "rimshot": rimshot}


def _write_wav(path: Path, x: "np.ndarray") -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def make_sounds(out_dir: Optional[Union[str, Path]] = None) -> Dict[str, Path]:
    """Writes every shipped sound into out_dir as a mono wav, and returns name -> file.

    Each file lands through a temporary name, so a server reading the folder at the same moment never opens
    half a wav. A sound that cannot be written is left out; only a run that wrote nothing raises."""
    _need()
    root = Path(out_dir) if out_dir else sounds_dir()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise RuntimeError(f"the sounds folder {root} cannot be written: {e}")
    made: Dict[str, Path] = {}
    trouble: List[str] = []
    with _lock:
        for name, fn in SOUNDS.items():
            dst = root / f"{name}.wav"
            tmp = dst.with_name(f"{dst.name}.{os.getpid()}.tmp")
            try:
                _write_wav(tmp, fn())
                os.replace(tmp, dst)
                made[name] = dst
            except Exception as e:                 # one quiet sound must not cost the other nine
                trouble.append(f"{name}: {e}")
                try:
                    tmp.unlink()
                except OSError:
                    pass
    if not made:
        raise RuntimeError("no sound could be made: " + "; ".join(trouble[-2:] or ["unknown error"]))
    return made


def sound_names(mood: str) -> List[str]:
    """The file names a mood's sound may live under, in order. Never makes anything."""
    m = load_moods().get(mood) or {}
    spec = m.get("sound")
    names = [spec] if isinstance(spec, str) else list(spec or [])
    return [str(n) for n in names if n]


def sound_ready(mood: str) -> bool:
    """Whether one of a mood's sounds is already on disk. A look at the folder, never a build.

    A mood names its sounds (`hype` is airhorn then bass_drop), so asking for `<mood>.wav` would report every gag
    as unbuilt while its files sit right there."""
    root = sounds_dir()
    try:
        names = sound_names(mood)
    except Exception:  # noqa: BLE001 - a broken mood file is simply "not ready"
        return False
    for n in names:
        for ext in ("wav", "m4a", "mp3"):
            try:
                if (root / f"{n}.{ext}").is_file():
                    return True
            except OSError:
                continue
    return False


def _resolve_sound(spec: object, root: Optional[Path] = None) -> Path:
    """The file for a mood's sound: your own copy first, else the synthesised one, made on demand."""
    root = root or sounds_dir()
    names = [spec] if isinstance(spec, str) else list(spec or [])
    for _ in range(2):                            # the second pass runs after the shipped sounds are made
        for n in names:
            for ext in ("wav", "m4a", "mp3"):
                f = root / f"{n}.{ext}"
                if f.is_file():
                    return f
        if not any(root.glob("*.wav")):
            make_sounds(root)
    raise RuntimeError(f"no sound called {spec} in {root}, and it is not one PeakCut can make")


# ---------------------------------------------------------------- the payoff
def _probe(path: Path) -> tuple:
    """Width, height and length of a clip."""
    try:
        out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                   "stream=width,height:format=duration", "-of", "json", str(path)], timeout=120)
        j = json.loads(out)
        st = (j.get("streams") or [{}])[0]
        return int(st["width"]), int(st["height"]), float(j["format"]["duration"])
    except (RuntimeError, KeyError, IndexError, TypeError, ValueError) as e:
        raise RuntimeError(f"could not read {Path(path).name} as a video: {e}")


def _audio_len(path: Path) -> float:
    try:
        out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], timeout=60)
        return float(out.strip().splitlines()[0])
    except (RuntimeError, IndexError, ValueError) as e:
        raise RuntimeError(f"could not read the length of {Path(path).name}: {e}")


def _has_audio(path: Path) -> bool:
    try:
        out = run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=index",
                   "-of", "csv=p=0", str(path)], timeout=60)
        return bool(out.strip())
    except RuntimeError:
        return True                               # if the probe itself fails, let ffmpeg say what is wrong


def find_payoff(short: Union[str, Path], dur: float) -> float:
    """The loudest 100 ms in the back half of the clip, never inside the hook; 70 % in when there is no audio."""
    try:
        p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(short), "-vn", "-ac", "1", "-ar", "16000",
                            "-f", "s16le", "-"], capture_output=True, timeout=120, creationflags=NO_WINDOW)
        x = np.frombuffer(p.stdout, "<i2").astype(float)
        w = 1600                                  # 100 ms at 16 kHz
        n = len(x) // w
        if n < 5:
            return max(HOOK_SAFE, dur * 0.7)
        r = np.sqrt((x[: n * w].reshape(n, w) ** 2).mean(1))
        lo = int(max(dur * 0.4, HOOK_SAFE) * 10)
        hi = max(int((dur - 0.6) * 10), lo + 1)
        return float(np.argmax(r[lo:hi]) + lo) / 10
    except Exception:
        return max(HOOK_SAFE, min(dur * 0.7, dur - 0.4))     # no decode is not a reason to skip the gag


# ---------------------------------------------------------------- the gag
def _filter(W: int, H: int, dur: float, T: float, hold: float, tail: float, total: float,
            S: float, Lm: float, fx: Sequence[str], volume: float, audio: bool) -> str:
    """The ffmpeg graph: picture split around the payoff, and the sound laid under the clip."""
    # transient effects ride the first segment after the payoff (the freeze if there is one, else the live video)
    zt: List[str] = []
    dx = dy = "0"
    if "zoom" in fx:
        zt.append(f"0.14*min(t/{hold if hold else 1.5:.3f},1)")
    if "punch" in fx:
        zt.append("0.12*max(0,1-t/0.35)")
    if "shake" in fx:                             # 0.07 of headroom is what the 20 px knock needs
        zt.append("0.07")
        dx = "20*sin(t*70)*max(0,1-t/0.5)"
        dy = "14*cos(t*83)*max(0,1-t/0.5)"
    Z = "1+" + "+".join(zt) if zt else ""
    trans = (f"scale=w='2*trunc(iw*({Z})/2)':h='2*trunc(ih*({Z})/2)':eval=frame,"
             f"crop={W}:{H}:'max(0,min(iw-{W},(iw-{W})/2+{dx}))':'max(0,min(ih-{H},(ih-{H})*0.4+{dy}))'," if Z else "")
    flash = "fade=t=in:st=0:d=0.22:color=white," if "flash" in fx else ""
    stat = ("eq=saturation=0.25:contrast=1.05," if "desat" in fx else "") + ("vignette=angle=0.95," if "vignette" in fx else "")
    base = "fps=30,setsar=1,format=yuv420p,"

    v = [f"[0:v]split={3 if hold else 2}[a][c]" if not hold else "[0:v]split=3[a][b][c]",
         f"[a]trim=0:{T:.3f},setpts=PTS-STARTPTS,{base}null[pre]"]
    if hold:
        v.append(f"[b]trim=start={T:.3f}:end={T + 0.1:.3f},setpts=PTS-STARTPTS,fps=30,trim=end_frame=1,"
                 f"tpad=stop_mode=clone:stop_duration={hold:.3f},setpts=PTS-STARTPTS,{trans}{flash}{stat}{base}null[hold]")
    postx = ("" if hold else trans + flash) + stat
    v.append(f"[c]trim=start={T:.3f},setpts=PTS-STARTPTS,{postx}{base}"
             + (f"tpad=stop_mode=clone:stop_duration={tail:.3f}," if tail else "") + "null[post]")
    v.append(f"[pre]{'[hold]' if hold else ''}[post]concat=n={3 if hold else 2}:v=1:a=0[vo]")

    # the original sound is fetched back up to full level while the gag plays, and the freeze holds the frame silent
    head = "" if audio else f"anullsrc=r={SR}:cl=stereo,atrim=0:{dur:.3f},"
    aud = [(f"[0:a]" if audio else "") + head + f"aresample={SR},aformat=channel_layouts=stereo,asplit=2[x][y]",
           f"[x]atrim=0:{T:.3f},asetpts=PTS-STARTPTS[ap]",
           f"[y]atrim=start={T:.3f},asetpts=PTS-STARTPTS[aq]"]
    if hold:
        aud += [f"anullsrc=r={SR}:cl=stereo,atrim=0:{hold:.3f},asetpts=PTS-STARTPTS[ah]",
                "[ap][ah][aq]concat=n=3:v=0:a=1[ao]"]
    else:
        aud.append("[ap][aq]concat=n=2:v=0:a=1[ao]")
    aud.append(f"[ao]apad=whole_dur={total:.3f},volume=0.3:enable='between(t,{S:.3f},{S + Lm:.3f})'[ad]")
    aud.append(f"[1:a]aresample={SR},aformat=channel_layouts=stereo,atrim=0:{Lm:.3f},"
               f"afade=t=out:st={max(Lm - 0.25, 0):.3f}:d=0.25,volume={volume}dB,"
               f"adelay={int(S * 1000)}|{int(S * 1000)}[as]")
    aud.append(f"[ad][as]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=9,atrim=0:{total:.3f}[ao2]")
    return ";".join(v + aud)


def apply(short: Union[str, Path], mood: str, at: Optional[float] = None,
          out: Optional[Union[str, Path]] = None) -> Path:
    """Puts one mood's sound and its visual treatment on `short` at the payoff, and returns the new file."""
    _need()
    src = Path(short)
    if not src.is_file():
        raise RuntimeError(f"no such clip: {src}")
    table = load_moods()
    if mood not in table:
        raise ValueError(f"there is no {mood!r} mood; pick one of {', '.join(sorted(table))}")
    m = table[mood]
    W, H, dur = _probe(src)
    if dur < MIN_CLIP:
        raise ValueError(f"the clip is {dur:.2f} s long; a gag needs at least {MIN_CLIP:.1f} s")

    # where the gag lands: given, or the loudest moment, and never in the hook and never under the last frames
    T = float(at) if at is not None else find_payoff(src, dur)
    T = min(max(T, HOOK_SAFE), dur - 0.4)
    hold = float(m.get("hold") or 0.0)
    fx = [e for e in m.get("effect") or () if e in EFFECTS]
    treat = str(m.get("treatment") or "push-in")
    want = _TREAT_EFFECT.get(treat, ())
    if want and not (set(want) & set(fx)):
        fx.append(want[0])                        # the named gag is always in the chain
    if treat == "freeze" and hold <= 0.0:
        hold = 1.0                                # a freeze with no hold would be a lie

    snd = _resolve_sound(m.get("sound"))
    L = _audio_len(snd)
    S = max(HOOK_SAFE, T + float(m.get("offset") or 0.0))
    tail = m.get("tail", 0)
    tail = max(0.0, S + L - (dur + hold)) + 0.3 if tail == "auto" else float(tail or 0.0)
    tail = max(0.0, min(tail, MAX_EXT - hold))
    total = dur + hold + tail
    Lm = min(L, total - S)
    if Lm < 0.05:
        raise RuntimeError("there is no room left for the sound after the payoff; give the clip more seconds")

    dst = Path(out) if out else src.with_name(f"{src.stem}_{mood}.mp4")
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise RuntimeError(f"the folder for {dst} cannot be written: {e}")

    # the graph goes in as one argument, the way the rest of the studio passes it: no script file to leak
    graph = _filter(W, H, dur, T, hold, tail, total, S, Lm, fx, float(m.get("volume") or 0.0), _has_audio(src))
    run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-i", str(snd), "-filter_complex", graph,
         "-map", "[vo]", "-map", "[ao2]", "-t", f"{total:.3f}", "-c:v", "libx264", "-crf", "18",
         "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-movflags", "+faststart", str(dst)], timeout=GAG_SECONDS)
    if not dst.is_file():
        raise RuntimeError(f"ffmpeg wrote no file at {dst}")
    return dst
