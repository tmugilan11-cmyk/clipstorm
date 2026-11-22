"""What kind of thing is happening, without asking a model.

A stream is long and most of it is not worth clipping. Before any AI is asked, this reads the file once
and labels the stretches where something actually happens: a chase, a crash, a fight, a stunt, a reaction,
or something funny. No key, no model, no network - ffmpeg pipes 2 frames a second at 160x90 and 16 kHz mono
sound, and the numbers below do the rest. About 85x realtime, so a 40 minute stream is labelled in half a
minute on a laptop.

How a stretch is judged, per half second:

    motion      how much the picture changes in the game area
    outflow     how fast the picture moves away from the centre - speed, so a chase
    rotation    how much it turns around the centre - a stunt spins, a chase does not
    cam         how much the facecam tile itself moves - a person reacting, not the game
    low         sound at 60-400 Hz - an engine, tyres
    voice       sound at 300-3000 Hz - someone talking, shouting
    high        sound at 3000-8000 Hz - a bang, an impact
    mod         a 4-10 Hz wobble in the voice band - the "ha-ha-ha" of laughing

Every band is scaled by its own quiet and loud points (pct), so a quiet stream and a loud one rank alike.
A type is a formula over those numbers, not a guess: crash needs an impact above the last 3 seconds of
its own sound, fight needs repeating hits, stunt needs rotation, funny needs laughter-shaped sound or
laughing words. A stretch only becomes a moment when it holds above its threshold for its own minimum
length, gaps under 3 seconds are bridged, and the score reported is the 90th percentile inside it.

Only numpy and ffmpeg, which are already here.
"""

from __future__ import annotations

import json
import re
import subprocess
import threading
import time
from pathlib import Path

import numpy as np

from . import config

FPS, W, H = 2, 160, 90          # video sampling: 2 frames a second, 160x90 grey
AR, FR = 16000, 20             # audio rate, envelope frames a second
MIN_LEN = {"chase": 5, "crash": 1.0, "fight": 4, "stunt": 3, "reaction": 2, "funny": 2}   # seconds
THR = {"chase": .5, "crash": .7, "fight": .6, "stunt": .7, "reaction": .55, "funny": .5}
HYPE = re.compile(r"\b(oh my (god|gosh)|no way|what the|holy|bruh|let'?s go+|are you kidding|crazy|insane|dude+|bro+)\b|!", re.I)
LAUGH = re.compile(r"\b(ha(ha)+|haha\w*|lol|lmao|lmfao|laugh\w*|dying|dead|cry(ing)?)\b", re.I)
CHATLOL = re.compile(r"LUL|KEKW|OMEGALUL|LMAO|ICANT", re.I)

TYPES = ("chase", "crash", "fight", "stunt", "reaction", "funny")
BANNER = "banner"                        # game events arrive from feature 05, this module only tolerates them
CATEGORY = {"chase": "clutch", "crash": "fail", "fight": "rage", "stunt": "clutch", "reaction": "shock", "funny": "funny"}
TITLE = {"chase": "The chase", "crash": "The crash", "fight": "The fight", "stunt": "The stunt",
         "reaction": "The reaction", "funny": "The funny bit"}
REASON = "Picked from the sound and motion of the game, because the AI was unavailable."

BLOCK, REACH = 8, 2             # block matching at 160x90: 8 px blocks, +-2 px of travel between frames
FLAT = 6.0                      # a block with less contrast than this (0-255) has no picture to follow
CHUNK = 60                      # seconds of sound read at a time, so a long stream is never held whole
MAX_FRAMES = FPS * 4 * 3600     # hard stop on the frame walk: four hours is longer than any job
RAW = ("pcm", "path", "audio", "file", "video")   # keys that mean "measure this", not "here are the numbers"

_DEFAULTS = {"enabled": False, "min_score": .55, "tag_words": True, "hint_ai": True, "use_when_no_ai": True}


# ---------------------------------------------------------------- small maths


def pct(x, lo: float = 50, hi: float = 98) -> np.ndarray:
    """Scale-free 0..1: the median is 0 and the 98th percentile is 1, so a quiet stream and a loud one rank alike."""
    x = np.asarray(x, float)
    if not len(x):
        return np.zeros(0)
    a, b = np.percentile(x, [lo, hi])
    return np.clip((x - a) / (b - a + 1e-6), 0, 1)


def sm(x, n: int) -> np.ndarray:
    """Centred moving average of n bins."""
    x = np.asarray(x, float)
    n = max(1, int(n))
    if not len(x):
        return x
    return np.convolve(np.pad(x, (n // 2, n - 1 - n // 2), mode="edge"), np.ones(n) / n, "valid")


def prev_med(x, n: int = 6) -> np.ndarray:
    """Median of the n bins before each bin: the baseline a spike has to beat. 6 bins is 3 seconds."""
    x = np.asarray(x, float)
    out = np.zeros_like(x)
    for i in range(len(x)):
        out[i] = np.median(x[max(0, i - n):i]) if i else (x[0] if len(x) else 0.0)
    return out


def _num(v, default: float = 0.0) -> float:
    """A number from an outside source, or the default when it is missing, a string, or not finite."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    return f if np.isfinite(f) else default


def _clamp(v, lo: float, hi: float) -> float:
    return max(lo, min(hi, _num(v, lo)))


def _flag(v, default: bool) -> bool:
    return bool(v) if isinstance(v, (bool, int)) else default


def _fit(a, n: int) -> np.ndarray:
    """Pad with the last value or cut, so every feature is exactly n bins long."""
    a = np.asarray(a, float).ravel()
    if not len(a):
        return np.zeros(n)
    if len(a) < n:
        return np.pad(a, (0, n - len(a)), mode="edge")
    return a[:n]


# ---------------------------------------------------------------- sound


def _bands(pcm) -> dict:
    """Four dB arrays at 20 Hz: low 60-400, voice 300-3000, high 3000-8000, all 60-8000. pcm is -1..1."""
    x = np.asarray(pcm, np.float32).ravel()
    k = AR // FR                                  # 800 samples a frame
    n = len(x) // k
    if n < 1:
        return {b: np.zeros(0) for b in ("low", "voice", "high", "all")}
    f = x[: n * k].reshape(n, k) * np.hanning(k).astype(np.float32)
    S = np.abs(np.fft.rfft(f, axis=1)) ** 2
    fr = np.fft.rfftfreq(k, 1 / AR)

    def band(a, b):
        return 10 * np.log10(S[:, (fr >= a) & (fr < b)].sum(1) + 1e-9)

    return {"low": band(60, 400), "voice": band(300, 3000), "high": band(3000, 8000), "all": band(60, 8000)}


def audio_feats(pcm) -> dict:
    """Band levels for a stretch of samples (-1..1, or int16), as `{"low","voice","high","all"}` dB arrays."""
    x = np.asarray(pcm)
    if np.issubdtype(x.dtype, np.integer):
        x = x.astype(np.float32) / 32768.0
    return _bands(x)


def audio_features(source) -> dict:
    """Band levels for a file (any path ffmpeg can read) or for a stretch of samples.

    A file is read once in 60 second chunks, so a long stream never sits in memory. Nothing raises: a file
    that cannot be read comes back as empty bands."""
    if isinstance(source, (str, Path)):
        return _bands_from_path(str(source))
    return audio_feats(source)


def _bands_from_path(path: str, seek: float = 0.0, duration: float = 0.0) -> dict:
    """Stream 16 kHz mono through ffmpeg and keep only the bands, never the sound itself."""
    cmd = ["ffmpeg", "-v", "error", "-nostdin"]
    if seek > 0:
        cmd += ["-ss", f"{float(seek):.3f}"]      # before -i: ffmpeg decodes and throws away what comes before
    cmd += ["-i", path]
    if duration and duration > 0:
        cmd += ["-t", f"{float(duration):.3f}"]
    cmd += ["-vn", "-ac", "1", "-ar", str(AR), "-f", "s16le", "-"]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except Exception:  # noqa: BLE001 - no ffmpeg must not stop a job
        return {}
    acc: dict = {}
    step = CHUNK * AR * 2
    try:
        while True:
            raw = _read_exact(proc.stdout, step)
            if not raw:
                break
            a = np.frombuffer(raw[: len(raw) // 2 * 2], np.int16).astype(np.float32) / 32768.0
            for k, v in _bands(a).items():
                acc.setdefault(k, []).append(v)
    except Exception:  # noqa: BLE001
        pass
    finally:
        _close(proc)
    return {k: np.concatenate(v) for k, v in acc.items() if len(v)} if acc else {}


def laugh_mod(env, win: int = 60) -> np.ndarray:
    """How periodic the voice envelope is: the "ha-ha-ha" of laughing.

    Normalised autocorrelation at lags 2-5 frames (0.10-0.25 s, so 4-10 Hz) of a detrended 3 second window,
    written across each half second. Steady fast speech rings a little too, which is why the text and the
    sound have to agree before anything scores as funny."""
    e = np.asarray(env, float)
    out = np.zeros(len(e))
    if not len(e):
        return out
    d = e - sm(e, 20)
    st = FR // FPS
    for i in range(0, len(e), st):
        w = d[max(0, i - win // 2): i + win // 2]
        if len(w) < 20:
            continue
        v = (w * w).sum() + 1e-9
        out[i: i + st] = max((w[:-l] * w[l:]).sum() / v for l in range(2, 6))
    return out


def to_bins(a, n: int, fn=np.mean) -> np.ndarray:
    """Fold 20 frames a second down to 2 a second, then pad to exactly n bins."""
    a = np.asarray(a, float).ravel()
    k = FR // FPS
    m = len(a) // k
    if m < 1:
        return np.zeros(n)
    b = fn(a[: m * k].reshape(m, k), axis=1)
    return np.pad(b, (0, max(0, n - len(b))), mode="edge")[:n]


def text_feats(words, n: int, t0: float = 0.0) -> dict:
    """Per-bin 0/1 arrays from what was said: laughing words, excited words, laughing chat.

    `words` are `{"w","s","e"}` in seconds on the same clock as t0. A block's words sometimes arrive already
    relative to that block, in which case they all sit before t0 and are shifted here rather than dropped."""
    a = {k: np.zeros(n) for k in ("txt_laugh", "txt_hype", "chat_lol")}
    words = [w for w in (words or []) if isinstance(w, dict)]
    if not words or n < 1:
        return a
    times = [(_num(w.get("s")), _num(w.get("e"), _num(w.get("s")))) for w in words]
    if t0 > 0 and max(e for _, e in times) < t0:
        times = [(s + t0, e + t0) for s, e in times]
    for (s, e), w in zip(times, words):
        i, j = max(0, int((s - t0) * FPS)), min(n, int((e - t0) * FPS) + 1)
        if j <= i:
            continue
        body = str(w.get("w") or "")
        if LAUGH.search(body):
            a["txt_laugh"][i:j] = 1
        if HYPE.search(body):
            a["txt_hype"][i:j] = 1
        chat = w.get("chat")
        if chat and CHATLOL.search(str(chat)):
            a["chat_lol"][i:j] = 1
    return a


# ---------------------------------------------------------------- picture


def _read_exact(stream, n: int) -> bytes:
    """n bytes from a pipe, or fewer only at the end of the stream."""
    buf = bytearray()
    while len(buf) < n:
        try:
            chunk = stream.read(n - len(buf))
        except Exception:  # noqa: BLE001
            break
        if not chunk:
            break
        buf += chunk
    return bytes(buf)


def _close(proc) -> None:
    """Stop an ffmpeg we started, whatever state it is in. It must never outlive the call."""
    try:
        if proc.stdout:
            proc.stdout.close()
    except Exception:  # noqa: BLE001
        pass
    try:
        proc.wait(timeout=15)
    except Exception:  # noqa: BLE001
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:  # noqa: BLE001
            pass


def _cam_box(cam):
    """The facecam rectangle in 160x90 units, or None when there is nothing usable."""
    if not cam:
        return None
    try:
        x0, y0, x1, y1 = (int(round(float(v))) for v in cam)
    except (TypeError, ValueError):
        return None
    x0, x1 = max(0, min(x0, W)), max(0, min(x1, W))
    y0, y1 = max(0, min(y0, H)), max(0, min(y1, H))
    return (x0, y0, x1, y1) if x1 - x0 >= 4 and y1 - y0 >= 4 else None


def frame_flow(prev, cur, cam=None, block: int = BLOCK, reach: int = REACH):
    """(motion, outflow, rotation, cam motion) for one pair of 160x90 grey frames, numpy only.

    The reference reads this with OpenCV's dense optical flow. PeakCut has no OpenCV, so each 8x8 block
    picks the +-2 px shift with the lowest squared difference instead, and the three numbers coming out keep
    the same formulas: motion is how much the game area changed, outflow is displacement pointing away from
    the centre (speed), rotation is displacement around the centre (a stunt spins). Motion is a 0..1 change
    rather than a pixel distance, which pct() absorbs because it only ever looks at ranks."""
    a = np.asarray(prev, np.float32)
    b = np.asarray(cur, np.float32)
    mask = np.ones((H, W), bool)
    box = _cam_box(cam)
    if box:
        mask[box[1]:box[3], box[0]:box[2]] = False
    diff = np.abs(b - a)
    m = round(float(diff[mask].mean()) / 255.0, 6) if mask.any() else 0.0

    by, bx = H // block, W // block
    if by < 1 or bx < 1:
        return m, 0.0, 0.0, 0.0
    hh, ww = by * block, bx * block
    A = a[:hh, :ww]
    pad = np.pad(b, reach, mode="edge")
    best = np.full((by, bx), np.inf, np.float32)
    dxs, dys = np.zeros((by, bx), np.float32), np.zeros((by, bx), np.float32)
    for dy in range(-reach, reach + 1):
        for dx in range(-reach, reach + 1):
            B = pad[reach + dy: reach + dy + hh, reach + dx: reach + dx + ww]
            d = A - B
            s = (d * d).reshape(by, block, bx, block).sum(axis=(1, 3))
            hit = s < best
            if hit.any():
                best = np.where(hit, s, best)
                dxs[hit], dys[hit] = float(dx), float(dy)
    flat = A.reshape(by, block, bx, block).var(axis=(1, 3)) < FLAT   # no picture in the block: no travel
    dxs[flat] = 0.0
    dys[flat] = 0.0

    xc = (np.arange(bx, dtype=np.float32) * block + block / 2 - W / 2)[None, :].repeat(by, 0)
    yc = (np.arange(by, dtype=np.float32) * block + block / 2 - H / 2)[:, None].repeat(bx, 1)
    r = np.hypot(xc, yc) + 1
    ok = np.ones((by, bx), bool)
    if box:
        cx, cy = xc + W / 2, yc + H / 2
        ok = ~((cx >= box[0]) & (cx < box[2]) & (cy >= box[1]) & (cy < box[3]))
        if not ok.any():                       # a box that swallowed the frame tells us nothing
            ok = np.ones((by, bx), bool)
    out = float(((xc * dxs + yc * dys) / r)[ok].mean())
    rot = float(((xc * dys - yc * dxs) / r)[ok].mean())
    cm = 0.0
    if box:
        cm = float(np.abs(b[box[1]:box[3], box[0]:box[2]] - a[box[1]:box[3], box[0]:box[2]]).mean())
    return m, out, rot, cm


def read_video(path, cam=None, duration: float = 0.0, seek: float = 0.0) -> dict:
    """Motion numbers per half second, read from the file two frames at a time.

    Nothing is loaded whole and nothing raises: an unreadable file, a file with no video track and a machine
    without ffmpeg all come back as empty arrays, which the caller reads as "no video"."""
    empty = {k: np.zeros(0) for k in ("m", "out", "rot", "cam")}
    box = _cam_box(cam)
    cmd = ["ffmpeg", "-v", "error", "-nostdin"]
    if seek > 0:
        cmd += ["-ss", f"{float(seek):.3f}"]
    cmd += ["-i", str(path), "-an", "-vf", f"fps={FPS},scale={W}:{H}", "-pix_fmt", "gray"]
    if duration and duration > 0:
        cmd += ["-t", f"{float(duration):.3f}"]
    cmd += ["-f", "rawvideo", "-"]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except Exception:  # noqa: BLE001 - no ffmpeg: no motion, not a failure
        return empty
    R = {k: [] for k in ("m", "out", "rot", "cam")}
    size = W * H
    prev = None
    try:
        while len(R["m"]) < MAX_FRAMES:
            raw = _read_exact(proc.stdout, size)
            if len(raw) < size:
                break
            cur = np.frombuffer(raw, np.uint8).reshape(H, W)
            v = frame_flow(prev, cur, box) if prev is not None else (0.0, 0.0, 0.0, 0.0)
            for k, x in zip(R, v):
                R[k].append(x)
            prev = cur
    except Exception:  # noqa: BLE001
        pass
    finally:
        _close(proc)
    return {k: np.asarray(v, dtype=float) for k, v in R.items()}


# ---------------------------------------------------------------- the six scores


def _feature(F, key: str, n: int) -> np.ndarray:
    return _fit(F.get(key, np.zeros(n)), n)


def _scores(F, has_video: bool = True, has_cam: bool = False, allow=None) -> dict:
    """The six formulas, exactly as the single-user clipper had them. Never raises."""
    n = len(np.asarray(F.get("voice", []), float).ravel()) if isinstance(F, dict) else 0
    if n < 1:
        return {}
    z = np.zeros(n)

    def k(seconds):
        return max(1, int(seconds * FPS))

    def tr(x):
        return pct(np.maximum(0, x - prev_med(x)), 75, 99)

    L = pct(sm(_feature(F, "low", n), k(6)))
    V = pct(_feature(F, "voice", n))
    A = pct(_feature(F, "all", n))
    Ta, Tv, flux = tr(_feature(F, "all", n)), tr(_feature(F, "voice", n)), tr(_feature(F, "high", n))
    dens = np.minimum(1, sm((Ta > .45).astype(float), k(8)) * k(8) / 4)      # 4+ transients in 8 s

    mf = _feature(F, "m", n)
    if has_video:
        m = pct(mf)
        ms = pct(sm(mf, k(6)))                                               # sustained movement
        out = pct(sm(_feature(F, "out", n), k(6)), 50, 97)
        rot = pct(sm(np.abs(_feature(F, "rot", n)), k(4)), 50, 97)
        mj = pct(np.maximum(0, mf - prev_med(mf)), 75, 99)                   # a jump in movement
        cap = 1.0
    else:                                                                    # audio only: movement unknown
        m = ms = A * .8
        out = L
        rot = z
        mj = Tv
        cap = .7

    S = {}
    S["chase"] = cap * np.minimum(sm(np.minimum(ms, np.maximum(out, L)), k(2)), sm(np.maximum(L, A * .8), k(4)))
    S["crash"] = np.where(Ta > .35, cap * np.minimum(np.maximum(mj, Ta * .8), np.maximum(Ta, flux)) * np.minimum(1, .4 + Ta), 0)
    S["fight"] = cap * np.where(dens > .3, (dens + sm(m, k(3)) + sm(V, k(3))) / 3 * 1.25, 0)
    S["stunt"] = np.minimum(rot, np.maximum(ms, .5)) * np.where(L < .85, 1, .8) if has_video else z
    camm = pct(sm(_feature(F, "cam", n), k(2))) if (has_video and has_cam) else sm(Tv, k(2))
    r = np.minimum(1, (camm * .45 + sm(V, k(2)) * .55) * 1.2) * (.5 + .5 * np.maximum(Tv, V)) * (V > .5)
    S["reaction"] = np.minimum(1, r + .2 * sm(_feature(F, "txt_hype", n), k(3)).clip(0, 1) * (V > .4))
    mod = np.clip((sm(_feature(F, "mod", n), k(2)) - .35) / .35, 0, 1) * (V > .4)   # periodic voice bursts
    txt = np.minimum(1, sm(_feature(F, "txt_laugh", n), k(4)) * 2.8 + sm(_feature(F, "chat_lol", n), k(4)) * 2)
    f = np.minimum(1, mod * .55 + txt * .6 + np.minimum(mod, txt) * .3)
    S["funny"] = np.where((mod > .3) | (txt > .3), f, 0) * np.where(txt > .3, 1, .75)

    if allow is not None:
        S = {t: s for t, s in S.items() if t in allow}
    return {t: np.clip(np.nan_to_num(s), 0, 1) for t, s in S.items()}


def score(feats, has_video: bool = True, has_cam: bool = False):
    """What each half second looks like.

    `feats` is the per-bin feature dict built by `features()` (or handed to it): the motion and band arrays at
    2 Hz. The answer is `{type: 0..1 array}`, one array per moment type that is switched on in the settings.

    Given something raw instead (`{"path": ...}`, `{"pcm": ...}`) it measures the file and thresholds it in
    one call, and the answer is the list of moments - the same list `segments` returns. Either way this only
    reads; it writes nothing and never raises: features that do not line up are padded, and NaN comes out 0."""
    if not isinstance(feats, dict):
        return {}
    if any(key in feats for key in RAW):
        got = _measure(feats, words=feats.get("words") if isinstance(feats.get("words"), list) else None)
        return _spans(got["scores"], got["t0"], 3, *_tables())
    return _scores(feats, bool(has_video), bool(has_cam), allow=_allowed())


# ---------------------------------------------------------------- spans


def _spans(S, t0: float = 0.0, gap: int = 3, thr=None, min_len=None) -> list:
    """Threshold a type's score into stretches: bridge gaps, drop short ones, report the 90th percentile."""
    thr = {**THR, **(thr or {})}
    min_len = {**MIN_LEN, **(min_len or {})}
    out = []
    for t, s in (S or {}).items():
        if t not in thr or t not in min_len:
            continue
        s = np.asarray(s, float).ravel()
        n = len(s)
        if not n:
            continue
        on = s >= thr[t]
        i = 0
        while i < n:
            if not on[i]:
                i += 1
                continue
            j = i
            while j < n and (on[j] or on[j + 1: j + 1 + int(gap * FPS)].any()):
                j += 1
            a, b = i / FPS, j / FPS
            if b - a >= min_len[t]:
                out.append({"t0": round(t0 + a, 1), "t1": round(t0 + b, 1), "type": t,
                            "score": round(float(np.percentile(s[i:j], 90)), 2)})
            i = j + 1
    return sorted(out, key=lambda r: (r["t0"], r["type"]))


def _clip(span: dict, start: float, end: float):
    """The part of a moment inside a window, or None when none of it is."""
    a, b = max(float(span["t0"]), start), min(float(span["t1"]), end)
    if b - a < 0.3:
        return None
    return {**span, "t0": round(a, 1), "t1": round(b, 1)}


def segments(source, start: float = 0.0, end=None, gap: int = 3, thr=None, min_len=None) -> list:
    """The stretches worth looking at: `[{t0, t1, type, score}]`, sorted, types may overlap.

    `source` may be a file (measured right here), a per-bin feature dict, or a scored dict from `score()`.
    `start`/`end` select a window: with a file only that part is read, with scores it is only filtered.
    Thresholds and minimum lengths default to the tuning table, and the saved settings override them."""
    s_thr, s_len = _tables()
    thr = {**s_thr, **(thr or {})}
    min_len = {**s_len, **(min_len or {})}
    if isinstance(source, (str, Path)):
        if not str(source).strip():
            return []
        window = max(0.0, float(end) - float(start)) if end is not None else 0.0
        got = analyse(str(source), duration=window, t0=float(start), seek=float(start), words=None)
        spans = got["moments"]
    elif isinstance(source, dict):
        if any(t in source for t in TYPES):
            spans = _spans(source, float(start), gap, thr, min_len)
        else:
            spans = _spans(_scores(source, True, False, allow=_allowed()), float(start), gap, thr, min_len)
    else:
        return []
    if end is not None:
        spans = [m for m in (_clip(m, float(start), float(end)) for m in spans) if m]
    return spans


# ---------------------------------------------------------------- the whole pipeline


def _duration(path: str) -> float:
    try:
        p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", str(path)],
                           capture_output=True, text=True, timeout=60)
        return float((p.stdout or "").strip() or 0)
    except Exception:  # noqa: BLE001 - no ffprobe, no duration: the caller can still pass one
        return 0.0


def _empty(t0: float = 0.0, dur: float = 0.0, has_video: bool = False, note: str = "") -> dict:
    out = {"t0": float(t0), "dur": round(float(dur), 1), "has_video": bool(has_video), "cam": None,
           "scan_s": 0.0, "x_realtime": 0.0, "moments": []}
    if note:
        out["note"] = note
    return out


def features(path=None, audio=None, duration: float = 0.0, t0: float = 0.0, cam=None,
             video: bool = True, words=None, seek: float = 0.0) -> dict:
    """Every per-bin number one stretch is scored from, at 2 a second.

    Sound is taken from `audio` when the caller already holds it (the job pipeline has the block in memory),
    and only read from the file otherwise. Vision needs the file; when there is no usable video track the
    result says so and the scores are capped at 0.7, because movement is then unknown."""
    pcm = None
    if audio is not None:
        a = np.asarray(audio)
        pcm = a.astype(np.float32) / 32768.0 if np.issubdtype(a.dtype, np.integer) else a.astype(np.float32)
    src = str(path) if path else ""
    dur = float(duration or 0.0)
    if dur <= 0 and pcm is not None:
        dur = len(pcm) / AR
    if dur <= 0 and src:
        dur = max(0.0, _duration(src) - float(seek))
    if dur <= 0:
        return {"n": 0, "dur": 0.0, "has_video": False, "cam": None, "F": {}, "t0": float(t0)}
    n = max(1, int(dur * FPS))

    bands = _bands(pcm) if pcm is not None else _bands_from_path(src, float(seek), dur)
    if not bands or not len(bands.get("voice", [])):
        return {"n": 0, "dur": dur, "has_video": False, "cam": None, "F": {}, "t0": float(t0)}

    box = _cam_box(cam)
    V = read_video(src, box, dur, float(seek)) if (video and src) else {}
    has_v = bool(len(V.get("m", [])))

    F = {k: to_bins(v, n) for k, v in bands.items()}
    F["mod"] = to_bins(laugh_mod(10 ** (bands["voice"] / 20)), n, np.max)
    for key in ("m", "out", "rot", "cam"):
        F[key] = _fit(V.get(key), n) if has_v else np.zeros(n)
    F.update(text_feats(words, n, float(t0)))
    return {"n": n, "dur": dur, "has_video": has_v, "cam": box, "F": F, "t0": float(t0)}


def _measure(raw: dict, words=None) -> dict:
    """features() plus the six scores, from a dict of raw media keys. Used by score() and segments()."""
    path = raw.get("path") or raw.get("file") or raw.get("video")
    audio = raw.get("pcm") if raw.get("pcm") is not None else raw.get("audio")
    got = features(path=path, audio=audio, duration=_num(raw.get("duration")), t0=_num(raw.get("t0")),
                   cam=raw.get("box") or raw.get("cam_box"), words=words, seek=_num(raw.get("seek")))
    allow = _allowed()
    return {"n": got["n"], "dur": got["dur"], "has_video": got["has_video"], "cam": got["cam"],
            "t0": got["t0"], "scores": _scores(got["F"], got["has_video"], bool(got["cam"]), allow=allow)}


def analyse(path=None, audio=None, duration: float = 0.0, t0: float = 0.0, cam=None,
            video: bool = True, words=None, seek: float = 0.0) -> dict:
    """Label one file (or one stretch of one) without any AI.

    `t0` is the absolute time of the file's first second, so the moments come back on the same clock as the
    transcript. `seek` says how far into the file to start reading, which is what a short preview of a long
    stream needs. `words` are optional: laughing and excited words sharpen `funny` and `reaction`.

    Writes nothing. A missing video track, a missing ffmpeg, an unreadable file and a file with no sound all
    come back as an answer with `moments: []` and a note, never as an exception."""
    began = time.time()
    try:
        got = features(path=path, audio=audio, duration=duration, t0=t0, cam=cam,
                       video=video, words=words, seek=seek)
    except Exception as e:  # noqa: BLE001 - a job must never die on a measurement
        return _empty(t0, duration, False, "Moments could not be measured: " + str(e)[:120])
    if not got["n"]:
        note = "" if got["dur"] else "This file could not be read for moments."
        return _empty(t0, got["dur"], False, note)

    st = settings()
    S = _scores(got["F"], got["has_video"], bool(got["cam"]), allow=_allowed(st))
    thr, min_len = _tables(st)
    moments = _spans(S, float(t0), 3, thr, min_len)
    took = time.time() - began
    return {"t0": float(t0), "dur": round(got["dur"], 1), "has_video": bool(got["has_video"]),
            "cam": list(got["cam"]) if got["cam"] else None, "scan_s": round(took, 1),
            "x_realtime": round(got["dur"] / max(took, .01), 1), "moments": moments}


# ---------------------------------------------------------------- what to do with the moments


def label(words, moments, min_score: float = .55, slack: float = 2.0, top: int = 2) -> list:
    """The same words, each tagged with the moment it falls in: a new list, never an edit in place.

    A word gets `moment` (the best type) and `moment_score`, plus `moment_types` when more than one type
    covers it. Running this twice changes nothing the second time, because everything is worked out from
    `moments` again and a stale tag is dropped rather than kept."""
    live = []
    for m in moments or []:
        if not isinstance(m, dict) or m.get("type") == BANNER:
            continue
        if _num(m.get("score")) < min_score:
            continue
        live.append((str(m.get("type")), _num(m.get("t0")), _num(m.get("t1")), _num(m.get("score"))))
    out = []
    for w in words or []:
        if not isinstance(w, dict):
            continue
        d = {k: v for k, v in w.items() if k not in ("moment", "moment_score", "moment_types")}
        s, e = _num(w.get("s"), None), _num(w.get("e"), None)
        if s is None or e is None:
            out.append(d)
            continue
        hits: dict = {}
        for kind, a, b, sc in live:
            if b + slack >= s and a - slack <= e:
                hits[kind] = max(hits.get(kind, 0.0), sc)
        if hits:
            ranked = sorted(hits.items(), key=lambda kv: (-kv[1], kv[0]))[:max(1, int(top))]
            d["moment"] = ranked[0][0]
            d["moment_score"] = round(float(ranked[0][1]), 2)
            if len(ranked) > 1:
                d["moment_types"] = [{"type": t, "score": round(float(sc), 2)} for t, sc in ranked]
        out.append(d)
    return out


def best(moments, kind: str):
    """The highest scoring moment of one type, or None."""
    found = [m for m in moments or [] if isinstance(m, dict) and m.get("type") == kind]
    return max(found, key=lambda m: _num(m.get("score"))) if found else None


def overlap(start: float, end: float, moments, kind=None) -> float:
    """How many seconds of [start, end) a moment covers. Overlapping moments are not counted twice."""
    spans = []
    for m in moments or []:
        if not isinstance(m, dict) or (kind is not None and m.get("type") != kind):
            continue
        lo, hi = max(_num(m.get("t0")), float(start)), min(_num(m.get("t1")), float(end))
        if hi > lo:
            spans.append((lo, hi))
    spans.sort()
    total, last = 0.0, None
    for lo, hi in spans:
        lo = last if last is not None and lo < last else lo
        if hi > lo:
            total += hi - lo
            last = hi
    return round(total, 3)


def _words_in(words, start: float, end: float, limit: int = 8) -> list:
    out = []
    for w in words or []:
        if not isinstance(w, dict):
            continue
        s = _num(w.get("s"), -1.0)
        if start - 0.3 <= s <= end and str(w.get("w") or "").strip():
            out.append(str(w["w"]).strip())
        if len(out) >= limit:
            break
    return out


def fallback(words, moments, n: int, min_len: int, max_len: int, duration: float) -> list:
    """Clips picked without any AI: one per measured moment, best first.

    The shape is exactly what `brain.find_clips` hands to `jobs.py`, and `category` stays inside
    `brain.CATEGORIES` so the page needs no change. This is a hint-sized, honest pick - it knows a crash
    from a chase, not which crash is worth posting."""
    n = max(0, int(n))
    if n < 1:
        return []
    duration = max(0.0, _num(duration))
    min_len = max(0.5, _num(min_len, 15.0))
    max_len = max(min_len, _num(max_len, 60.0))
    picks: list = []
    order = sorted((m for m in moments or [] if isinstance(m, dict) and m.get("type") in TYPES),
                   key=lambda m: -_num(m.get("score")))
    for mo in order:
        kind = str(mo["type"])
        s, e = _num(mo.get("t0")), _num(mo.get("t1"))
        if duration:
            s, e = max(0.0, min(s, duration)), min(duration, e)
        if e - s < min_len:                        # too short to post: let it grow around what happened
            mid = (s + e) / 2
            s, e = max(0.0, mid - min_len / 2), mid + min_len / 2
            if duration:
                s, e = max(0.0, min(s, duration - min_len)), min(duration, s + min_len)
        e = min(e, s + max_len)
        if e - s < 0.5:
            continue
        if any(min(e, k["end"]) - max(s, k["start"]) > 0.3 * (e - s) for k in picks):
            continue
        inside = _words_in(words, s, e)
        hook = " ".join(inside[:4]).upper() or kind.upper()
        picks.append({"start": round(s, 2), "end": round(e, 2), "score": int(round(_num(mo.get("score")) * 100)),
                      "category": CATEGORY.get(kind, "other"), "hook": hook[:60], "title": TITLE.get(kind, kind.title()),
                      "description": "", "hashtags": [], "highlight_words": inside,
                      "reason": REASON, "moment": kind})
        if len(picks) >= n:
            break
    return picks


def public(moments) -> list:
    """The moments as they may be written to job.json and read by the page: plain numbers, nothing internal."""
    out = []
    for m in moments or []:
        if not isinstance(m, dict) or not m.get("type"):
            continue
        row = {"t0": round(_num(m.get("t0")), 1), "t1": round(_num(m.get("t1")), 1),
               "type": str(m["type"])[:20], "score": round(_num(m.get("score")), 2)}
        if m.get("label"):
            row["label"] = str(m["label"])[:40]
        out.append(row)
    return out


# ---------------------------------------------------------------- settings (DATA_DIR/moments.json)
_lock = threading.Lock()
_saved = {"at": None, "data": {}}


def _file():
    return config.DATA_DIR / "moments.json"


def _from_file() -> dict:
    """What was saved from the dashboard, read again only when the file changes."""
    f = _file()
    try:
        at = f.stat().st_mtime_ns
    except OSError:
        at = 0
    if _saved["at"] != at:
        try:
            data = json.loads(f.read_text(encoding="utf-8")) if at else {}
        except (OSError, ValueError):
            data = {}
        _saved.update(at=at, data=data if isinstance(data, dict) else {})
    return _saved["data"]


def _merge(d: dict) -> dict:
    """Every key optional: what is missing or unusable falls back to the default."""
    t = d.get("types") if isinstance(d.get("types"), dict) else {}
    out = {"enabled": _flag(d.get("enabled"), _DEFAULTS["enabled"]),
           "min_score": round(_clamp(d.get("min_score", _DEFAULTS["min_score"]), 0, 1), 2),
           "tag_words": _flag(d.get("tag_words"), _DEFAULTS["tag_words"]),
           "hint_ai": _flag(d.get("hint_ai"), _DEFAULTS["hint_ai"]),
           "use_when_no_ai": _flag(d.get("use_when_no_ai"), _DEFAULTS["use_when_no_ai"]),
           "types": {}}
    for name in TYPES:
        e = t.get(name) if isinstance(t.get(name), dict) else {}
        on = e.get("on", True)                 # a type is on unless it was switched off by hand
        out["types"][name] = {"thr": round(_clamp(e.get("thr", THR[name]), 0, 1), 2),
                              "min_len": round(_clamp(e.get("min_len", MIN_LEN[name]), .5, 60), 1),
                              "on": on if isinstance(on, bool) else bool(on)}
    return out


def settings() -> dict:
    """The moment settings in use. Off by default, so a user who never opens this gets today's clips."""
    return _merge(_from_file())


def save(changes: dict) -> dict:
    """Save the settings made in the dashboard, and return what is now in use.

    Bad numbers are clamped, unknown types are dropped, and anything that cannot be saved raises ValueError
    with something a person can read - the route turns that into a 400."""
    if not isinstance(changes, dict):
        raise ValueError("The moment settings must be an object.")
    if "types" in changes and not isinstance(changes["types"], dict):
        raise ValueError("The moment types must be an object.")
    cur = settings()
    raw = {k: changes[k] for k in ("enabled", "min_score", "tag_words", "hint_ai", "use_when_no_ai") if k in changes}
    types = {name: dict(v) for name, v in cur["types"].items()}
    for name, patch in (changes.get("types") or {}).items():
        if name not in TYPES or not isinstance(patch, dict):
            continue                            # a type we do not have is not an error, it is not ours
        types[name].update({k: patch[k] for k in ("thr", "min_len", "on") if k in patch})
    new = _merge({**cur, **raw, "types": types})
    f = _file()
    tmp = f.with_suffix(".tmp")
    try:
        tmp.parent.mkdir(parents=True, exist_ok=True)
        with _lock:
            tmp.write_text(json.dumps(new, indent=1), encoding="utf-8")
            tmp.replace(f)
    except OSError as e:
        raise ValueError("Could not save the moment settings: " + str(e)[:120])
    _saved.update(at=None, data={})            # the next read picks the new file up
    return new


def _allowed(st: dict = None) -> list:
    """The types that are switched on, in the table's order."""
    st = settings() if st is None else st
    return [t for t in TYPES if (st["types"].get(t) or {}).get("on", True)]


def _tables(st: dict = None):
    """(thresholds, minimum lengths) with the saved settings laid over the tuning table."""
    st = settings() if st is None else st
    thr = {t: float((st["types"].get(t) or {}).get("thr", THR[t])) for t in TYPES}
    min_len = {t: float((st["types"].get(t) or {}).get("min_len", MIN_LEN[t])) for t in TYPES}
    return thr, min_len


# ---------------------------------------------------------------- selftest


def selftest() -> int:
    """Build five minutes of made-up features with planted events and check every type is found.

    Also checks the quiet start stays quiet, that sound alone still finds a crash but never a stunt (there
    is no picture to see a spin in), and that tagging words twice gives the same words back."""
    rng = np.random.default_rng(1)
    n = 600                                     # bins: five minutes at 2 a second

    t = np.arange(AR * 20) / AR
    noise = rng.normal(0, .02, len(t)).astype(np.float32)
    steady = noise + .2 * np.sin(2 * np.pi * 800 * t)
    laugh = noise + .4 * np.sin(2 * np.pi * 800 * t) * (np.sin(2 * np.pi * 5.5 * t) > 0)

    def mod(x):
        return laugh_mod(10 ** (_bands(x)["voice"] / 20))[100:300].max()

    assert mod(laugh) > .6 > mod(steady) + .1, (mod(laugh), mod(steady))

    F = {k: np.abs(rng.normal(0, .1, n)) for k in ("m", "out", "rot", "cam", "mod")}
    for k in ("low", "voice", "high", "all"):
        F[k] = -50 + rng.normal(0, .4, n)
    F["mod"] *= .3
    for k in ("txt_laugh", "txt_hype", "chat_lol"):
        F[k] = np.zeros(n)

    def put(a, b, **kw):
        for k, v in kw.items():
            F[k][a:b] += v

    put(100, 160, m=1.5, out=1.0, low=14, all=10)                             # chase
    put(250, 253, m=3.5, all=22, high=18, voice=10)                           # crash
    for a in range(330, 370, 4):
        put(a, a + 1, all=18, high=14, voice=14, m=2)                         # fight: repeated hits
    put(330, 370, m=1.2)
    put(440, 456, rot=3.0, m=2.0)                                             # stunt
    put(520, 540, voice=14, all=8, cam=3.0)                                   # reaction
    put(570, 590, voice=8, mod=.9, txt_laugh=1, chat_lol=1)                   # funny

    ms = _spans(_scores(F, True, True, allow=TYPES), 0.0, 3, THR, MIN_LEN)
    for kind, a, b in (("chase", 100, 160), ("crash", 250, 253), ("fight", 330, 370),
                       ("stunt", 440, 456), ("reaction", 520, 540), ("funny", 570, 590)):
        assert any(m["type"] == kind and m["t0"] < b / 2 and m["t1"] > a / 2 for m in ms), (kind, ms)
    assert not any(m["t1"] < 45 for m in ms), "false hit in the quiet start: " + str([m for m in ms if m["t1"] < 45])

    sound_only = _spans(_scores(F, False, False, allow=TYPES), 0.0, 3, THR, MIN_LEN)
    assert any(m["type"] == "crash" for m in sound_only), sound_only
    assert not any(m["type"] == "stunt" for m in sound_only), sound_only

    words = [{"w": "haha", "s": 286.0, "e": 286.6}, {"w": "no", "s": 1.0, "e": 1.2},
             {"w": "way", "s": 1.2, "e": 1.4}, {"w": "go", "s": 500.0, "e": 500.3}]
    tagged = label(words, ms)
    assert label(tagged, ms) == tagged, "label() is not idempotent"
    assert tagged[0].get("moment") == "funny", tagged[0]
    assert all(len(w.get("moment_types") or []) <= 2 for w in tagged)
    assert words[0] == {"w": "haha", "s": 286.0, "e": 286.6}, "label() changed the words it was given"

    assert len(public(ms)) == len(ms) and all(isinstance(m["score"], float) for m in public(ms))
    assert best(ms, "crash") and best(ms, "nothing") is None
    assert overlap(0.0, 1000.0, ms) > 0 and overlap(ms[0]["t0"], ms[0]["t1"], ms) >= 1.0
    clips = fallback(words, ms, 3, 15, 60, 600.0)
    assert clips and all(15 - .01 <= c["end"] - c["start"] <= 60.01 for c in clips), clips
    assert all(c["category"] in {"funny", "fail", "clutch", "rage", "shock", "take", "story", "other"} for c in clips)
    print("moments selftest ok", len(ms), "moments")
    return len(ms)
