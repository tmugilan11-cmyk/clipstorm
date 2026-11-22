# 04 - Moment types without AI

## 1. What it does

Watches a video once, cheaply, and labels the stretches where something is happening: a chase, a crash, a fight, a stunt, a reaction, or something funny. It never calls a model - it reads motion, camera flow and audio bands out of ffmpeg pipes and thresholds them into spans with a confidence score. Cost is roughly 85x realtime, so a 40-minute stream is labelled in about half a minute on a laptop. The output is a list of `{t0, t1, type, score}` spans that can tag transcript lines, sort or gate clips, and give a clip a human-readable "this is a crash" label even when no AI key is configured.

## 2. Exact mechanics

Source: `gta6-clipper-main/moments.py` (297 lines). Everything below is the real algorithm; after reading it a build agent should not need the file open.

### 2.1 Global constants (moments.py:15-21)

```python
FPS, W, H = 2, 160, 90          # video sampling: 2 frames/s, 160x90 gray
AR = 16000; FR = 20             # audio rate, envelope frames/s
MIN_LEN = {"chase": 5, "crash": 1.0, "fight": 4, "stunt": 3, "reaction": 2, "funny": 2}   # seconds
THR = {"chase": .5, "crash": .7, "fight": .6, "stunt": .7, "reaction": .55, "funny": .5}
HYPE = re.compile(r"\b(oh my (god|gosh)|no way|what the|holy|bruh|let'?s go+|are you kidding|crazy|insane|dude+|bro+)\b|!", re.I)
LAUGH = re.compile(r"\b(ha(ha)+|haha\w*|lol|lmao|lmfao|laugh\w*|dying|dead|cry(ing)?)\b", re.I)
CHATLOL = re.compile(r"LUL|KEKW|OMEGALUL|LMAO|ICANT", re.I)
```

`FR // FPS = 10` audio frames per video bin. One video bin = 0.5 s. Every feature array is indexed at 2 Hz.

### 2.2 Helpers (moments.py:24-36)

- `pct(x, lo=50, hi=98)`: `np.clip((x - p50) / (p98 - p50 + 1e-6), 0, 1)`. Scale-free, so a quiet stream and a loud one rank alike.
- `sm(x, n)`: centred moving average of `n` bins, `np.convolve` with `mode="edge"` padding `(n//2, n-1-n//2)`.
- `prev_med(x, n=6)`: causal baseline - median of the **n bins before** each bin (`x[max(0,i-n):i]`, `x[0]` at i=0). 6 bins = 3 s. Used for "spike above the last 3 s".

### 2.3 Audio features (moments.py:39-44)

```python
k = AR // FR                       # 800 samples per frame
n = len(pcm) // k
f = pcm[: n * k].reshape(n, k) * np.hanning(k)
S = np.abs(np.fft.rfft(f, axis=1)) ** 2
fr = np.fft.rfftfreq(k, 1 / AR)
band = lambda a, b: 10 * np.log10(S[:, (fr >= a) & (fr < b)].sum(1) + 1e-9)
return {"low": band(60, 400), "voice": band(300, 3000), "high": band(3000, 8000), "all": band(60, 8000)}
```

Bands: **low 60-400 Hz** (engine/tyres), **voice 300-3000 Hz**, **high 3000-8000 Hz** (crashes, impacts), **all 60-8000 Hz**. Output is dB per 20 Hz frame.

### 2.4 Laughter periodicity (moments.py:47-55)

```python
e = np.asarray(env, float); out = np.zeros(len(e)); d = e - sm(e, 20); st = FR // FPS   # st = 10
for i in range(0, len(e), st):
    w = d[max(0, i - win // 2): i + win // 2]        # win = 60 -> 3 s window
    if len(w) < 20: continue
    v = (w * w).sum() + 1e-9
    out[i: i + st] = max((w[:-l] * w[l:]).sum() / v for l in range(2, 6))
```

Normalised autocorrelation at lags 2-5 frames of the detrended voice envelope, written across each 10-frame block. At 20 Hz, lags 2-5 are periods of 0.10-0.25 s, i.e. 4-10 Hz (the docstring says "3.5-8 Hz" - the code is the truth). Input is the amplitude envelope reconstructed from voice dB: `10 ** (A["voice"] / 20)` (moments.py:244).

### 2.5 Binning (moments.py:58-60)

`to_bins(a, n, fn=np.mean)`: fold 10 audio frames per video bin with `fn`, then `np.pad(..., (0, max(0, n - len(b))), mode="edge")[:n]`. Laughter modulation is binned with `np.max`, not mean (moments.py:244).

### 2.6 Scoring (moments.py:63-89) - the core

Inputs: per-bin (2 Hz) arrays `m` motion, `out` radial outflow, `rot` rotation, `cam` cam-tile motion, `low/voice/high/all` (dB), `mod` laughter periodicity, `txt_laugh`, `txt_hype`, `chat_lol` (0/1).

```python
n = len(F["voice"]); z = np.zeros(n); k = lambda s: int(s * FPS)          # k(6) = 12 bins = 6 s
L, V, A = pct(sm(F["low"], k(6))), pct(F["voice"]), pct(F["all"])
tr = lambda x: pct(np.maximum(0, x - prev_med(x)), 75, 99)                # positive jump above the last 3 s
Ta, Tv, flux = tr(F["all"]), tr(F["voice"]), tr(F["high"])
dens = np.minimum(1, sm((Ta > .45).astype(float), k(8)) * k(8) / 4)       # >= 4 transients in 8 s -> 1.0
```

Video branch (`has_video=True`):

```python
m   = pct(F["m"])
ms  = pct(sm(F["m"], k(6)))                          # sustained motion, 6 s
out = pct(sm(F["out"], k(6)), 50, 97)
rot = pct(sm(np.abs(F["rot"]), k(4)), 50, 97)
mj  = pct(np.maximum(0, F["m"] - prev_med(F["m"])), 75, 99)   # motion spike
cap = 1
```

Audio-only branch (`has_video=False`), all motion proxies capped at 0.7 because motion is unknown:

```python
m = ms = A * .8;  out = L;  rot = z;  mj = Tv;  cap = .7
```

The six type scores:

| type | formula (moments.py line) |
|---|---|
| chase | `cap * min(sm(min(ms, max(out, L)), k(2)), sm(max(L, A*.8), k(4)))` (78) |
| crash | `where(Ta > .35, cap * min(max(mj, Ta*.8), max(Ta, flux)) * min(1, .4 + Ta), 0)` (79) |
| fight | `cap * where(dens > .3, (dens + sm(m, k(3)) + sm(V, k(3))) / 3 * 1.25, 0)` (80) |
| stunt | `min(rot, max(ms, .5)) * where(L < .85, 1, .8)` if `has_video` else `z` (81) |
| reaction | see below (82-84) |
| funny | see below (85-88) |

`reaction` uses the cam tile when one exists:

```python
camm = pct(sm(F["cam"], k(2))) if (has_video and has_cam) else sm(Tv, k(2))
r = np.minimum(1, (camm * .45 + sm(V, k(2)) * .55) * 1.2) * (.5 + .5 * np.maximum(Tv, V)) * (V > .5)
S["reaction"] = np.minimum(1, r + .2 * sm(F["txt_hype"], k(3)).clip(0, 1) * (V > .4))
```

`funny` fuses periodicity and text, and is damped when only audio says so:

```python
mod = np.clip((sm(F["mod"], k(2)) - .35) / .35, 0, 1) * (V > .4)      # periodic voice bursts
txt = np.minimum(1, sm(F["txt_laugh"], k(4)) * 2.8 + sm(F["chat_lol"], k(4)) * 2)
f   = np.minimum(1, mod * .55 + txt * .6 + np.minimum(mod, txt) * .3)
S["funny"] = np.where((mod > .3) | (txt > .3), f, 0) * np.where(txt > .3, 1, .75)
```

Everything is returned as `np.clip(np.nan_to_num(s), 0, 1)`.

### 2.7 Spans (moments.py:92-104)

```python
on = s >= THR[t]; i = 0; n = len(s)
while i < n:
    if not on[i]: i += 1; continue
    j = i
    while j < n and (on[j] or on[j + 1: j + 1 + gap * FPS].any()): j += 1     # gap = 3 -> 6 bins lookahead
    a, b = i / FPS, j / FPS
    if b - a >= MIN_LEN[t]: out.append({"t0": round(t0 + a, 1), "t1": round(t0 + b, 1),
                                       "type": t, "score": round(float(np.percentile(s[i:j], 90)), 2)})
    i = j + 1
return sorted(out, key=lambda r: (r["t0"], r["type"]))
```

Rule: threshold, **bridge gaps of up to 3 s**, drop anything shorter than the type's `MIN_LEN`, and report the **90th percentile** of the score inside the span (not the mean, not the max). Types may overlap; output is sorted by `t0`.

### 2.8 Video features (moments.py:149-168)

```python
p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-an",
                      "-vf", f"fps={FPS},scale={W}:{H}", "-pix_fmt", "gray", "-f", "rawvideo", "-"],
                     stdout=subprocess.PIPE)
```

Frames are read one at a time (160*90 bytes); the file is never loaded whole. Per frame pair:

```python
fl = cv2.calcOpticalFlowFarneback(prev, f, None, .5, 2, 9, 2, 5, 1.1, 0)   # dense flow, 160x90
vx, vy = fl[..., 0], fl[..., 1]
cm = mean(|f[cam] - prev[cam]|) if cam else 0                                # cam-tile motion, int16 abs
v = (mean(hypot(vx, vy)[mask]),                                            # m  : motion
     mean(((xc * vx + yc * vy) / r)[mask]),                                # out: radial outflow = speed
     mean(((xc * vy - yc * vx) / r)[mask]),                                # rot: tangential = rotation = stunt
     cm)                                                                    # cam
```

with `yy, xx = np.mgrid[0:H, 0:W]`, `xc, yc = xx - W/2, yy - H/2`, `r = hypot(xc, yc) + 1`, and `mask` = all ones except the cam rectangle (`mask[cam[1]:cam[3], cam[0]:cam[2]] = False`, moments.py:154-155). The first frame yields `(0, 0, 0, 0)`.

### 2.9 Camera box (moments.py:132-146)

`find_cam` runs YuNet (`models/yunet.onnx`, 640x360, confidence 0.6) on 12 frames spread through the video and keeps face centres that are in a **corner**: `(cx < 160 or cx > 480) and (cy < 90 or cy > 270)` at 640x360. Fewer than 4 hits means no cam. The box is `median(cx, cy, w)` with `r = w * 1.6`, clamped to the frame, then divided by 4 into 160x90 units. This exists only to (a) exclude the cam from the game-motion mask and (b) give `cam` a meaning. **It is replaceable and must be replaced in PeakCut - see section 4.6.**

### 2.10 Text features (moments.py:171-185)

Reads the transcript file's `[start-end] body` lines. Per line, `plain = re.sub(r"\[[^\]]*\]", "", body)`; `LAUGH` sets `txt_laugh[i:j] = 1`, `HYPE` sets `txt_hype`, and a `[CHAT ...]` tag matching `CHATLOL` sets `chat_lol`, where `i, j = int((start - t0) * FPS), int((end - t0) * FPS) + 1`. Bins are 0/1.

### 2.11 Banner events (moments.py:188-192)

Merged from a separate `vision.py` event file, not from audio/video: `{"t0": e["t"], "t1": max(e["t_end"], e["t"] + 3), "type": "banner", "label": e["label"], "score": round(e["weight"], 2)}` for `e["kind"] == "word"` or (`"text"` and `e.get("hits", 0) >= 3`). Out of scope for this port (that is feature 05); the module must simply tolerate a 7th type.

### 2.12 Full run (moments.py:237-254)

```python
dur, v, has_a = probe(src); has_v = v is not None
if not dur or not has_a: raise SystemExit("need a readable file with audio: " + src)
A = read_audio(src); n = int(dur * FPS)
if has_v:
    cam_box = tuple(int(int(x) / 4) for x in cam.split(",")) if cam else find_cam(src, dur)
    Vd = read_video(src, cam_box)
F = {k: to_bins(a, n) for k, a in A.items()}
F["mod"] = to_bins(laugh_mod(10 ** (A["voice"] / 20)), n, np.max)
for k in ("m", "out", "rot", "cam"):
    F[k] = np.pad(Vd[k], (0, max(0, n - len(Vd[k]))), mode="edge")[:n] if has_v else np.zeros(n)
F.update(text_feats(txt, n, t0))
mo = segments(score(F, has_v, bool(cam_box)), t0) + banner_moments(events)
mo.sort(key=lambda r: (r["t0"], r["type"]))
```

Output file next to the source, `<src>.moments.json`:

```json
{"src": "...", "t0": 0.0, "dur": 1234.5, "has_video": true, "cam": [10, 60, 40, 82],
 "scan_s": 14.2, "x_realtime": 86.9,
 "moments": [{"t0": 12.5, "t1": 31.0, "type": "chase", "score": 0.83}]}
```

`t0` is the absolute time of the file's first second (same base as the transcript); `dur` rounds to 0.1; `x_realtime = dur / max(scan_s, .01)`.

### 2.13 Transcript tagging (moments.py:195-216)

`tag_transcript(txt_path, moments, write=True, min_score=.55, slack=2)`: for each non-banner moment with `score >= .55`, every line whose span overlaps (`s.end + slack >= mo.t0 and s.start - slack <= mo.t1`) collects `type -> max score`; the top **2** types are appended as ` [MOMENT chase 0.8]` **before** any trailing `[HEAT n]`. It is idempotent (skips a type already present) and writes one `.bak` on first use. This file mutation is single-user behaviour and must not be ported as-is.

### 2.14 Reference selftest (moments.py:257-289)

Synthetic 600-bin (5 min) feature dict with planted events: chase at bins 100-160 (m=1.5, out=1.0, low=+14 dB, all=+10 dB), crash at 250-253 (m=3.5, all=+22, high=+18, voice=+10), fight at 330-370 (hits every 4 bins: all=+18, high=+14, voice=+14, m=+2), stunt at 440-456 (rot=3.0, m=2.0), reaction at 520-540 (voice=+14, all=+8, cam=3.0), funny at 570-590 (voice=+8, mod=.9, txt_laugh=1, chat_lol=1). Asserts each type is found in its stretch, asserts nothing is found before bin 45 ("false hit in the quiet start"), and asserts audio-only finds crash but never stunt.

## 3. PeakCut today

There is no per-type labelling and no audio-band or flow analysis anywhere in `peakcut/studio/`.

- **`peakcut/studio/brain.py:273` `find_clips(words, db, duration, title, uploader, max_clips, min_len, max_len, log, game)`** is the only moment picker. It asks a model per window (`brain.py:294`), and its "type" is a *post-hoc category string*, not a measured stretch: `CATEGORIES = {"funny", "fail", "clutch", "rage", "shock", "take", "story", "other"}` (`brain.py:81`). `funny` there is a model's opinion, not a label derived from audio.
- **`peakcut/studio/brain.py:245` `fallback_by_loudness(db, words, n, max_len, duration)`** is what runs when no AI key is set: "take the loudest stretches that contain speech", every pick stamped `"category": "other"`, `"reason": "Picked by loudness because the AI was unavailable."`. This is exactly the gap this feature closes - a crash, a chase and a rant are indistinguishable to it.
- **`peakcut/studio/brain.py:177` `loud_zscore(db)`** and **`peakcut/studio/media.py:323` `loudness_per_second(audio)`** give **one RMS dB value per second**, broadband. No 60-400 / 300-3000 / 3000-8000 split, so no engine-vs-impact discrimination, and no transient count.
- **`peakcut/studio/quality.py:32` `motion_map(path, bucket=2.0)`** already extracts a scalar per 2 s bucket via `tblend=all_mode=difference,signalstats,metadata=print` - the same *kind* of signal as `m` - but it is used only to find static ranges (`quality.py:69` `static_ranges`), and it is thrown away: `jobs.py:712` computes it once, `jobs.py:744-755` uses it only to drop ad-break clips. No direction, no radial outflow, no rotation, so `stunt` is undetectable from it.
- **`peakcut/studio/facecam.py:329` `detect(path, ask=None)`** already finds the webcam box in source pixels with numpy + ffmpeg only, and its docstring states the house rule at `facecam.py:24`: *"Only numpy and ffmpeg, which are already here."* It replaces `find_cam`/YuNet entirely; nothing in PeakCut ships `models/yunet.onnx`.
- **`peakcut/studio/media.py:317` `load_audio(wav)`** already returns int16 16 kHz mono in memory (`sf.read`, `assert sr == 16000`), loaded once at `jobs.py:608`. `moments.py`'s own `read_audio` (a second ffmpeg decode) is therefore redundant.
- **`peakcut/studio/jobs.py:738`** is the call site (`brain.find_clips(bw, db[s0:s0+...], (b-a)/16000, ...)`), and **`jobs.py:756-767`** builds the clip dict: `id, start, end, style, layout, captions, status, version`, plus `facecam`. There is no `moment` key, and nothing in `job.json` records a type.
- **`peakcut/studio/jobs.py:514` `BLOCK = 10*60`** means the pipeline already works in 10-minute blocks with `audio[a:b]` in hand (`jobs.py:713`), which is the natural granularity for this analysis.
- **No module has** `pct`/`sm`/`prev_med`, band features, or per-type thresholds. `render.py:14 STYLES` today holds three caption looks (`bounce`, `hype`, `clean`), unrelated to moment types.

Summary of the gap: PeakCut can say *how loud* a second was, and whether a whole video was static; it cannot say *what kind of moment* a stretch is, and with no AI key it says nothing at all beyond loudness.

## 4. Port plan

New module: **`peakcut/studio/moments.py`**. numpy + ffmpeg subprocess only, no new dependency. Docstring style follows `facecam.py` / `quality.py` (explain the metric, then the numbers).

### 4.1 Module constants

Copy verbatim: `FPS = 2`, `W, H = 160, 90`, `AR = 16000`, `FR = 20`, `MIN_LEN`, `THR`, `HYPE`, `LAUGH`, `CHATLOL` (section 2.1). Do **not** add a `HERE`-relative model path; there is no YuNet here.

### 4.2 Public API

```python
from __future__ import annotations

import numpy as np
from pathlib import Path


def pct(x, lo: float = 50, hi: float = 98) -> np.ndarray: ...
def sm(x, n: int) -> np.ndarray: ...
def prev_med(x, n: int = 6) -> np.ndarray: ...
def audio_feats(pcm: np.ndarray) -> dict[str, np.ndarray]: ...
def laugh_mod(env: np.ndarray, win: int = 60) -> np.ndarray: ...
def to_bins(a, n: int, fn=np.mean) -> np.ndarray: ...
def text_feats(words: list[dict], n: int, t0: float) -> dict[str, np.ndarray]: ...
def score(F: dict[str, np.ndarray], has_video: bool = True, has_cam: bool = False) -> dict[str, np.ndarray]: ...
def segments(S: dict[str, np.ndarray], t0: float = 0.0, gap: int = 3,
             thr: dict[str, float] | None = None, min_len: dict[str, float] | None = None) -> list[dict]: ...
def read_video(path: str | Path, cam: tuple[int, int, int, int] | None = None,
               duration: float = 0.0) -> dict[str, np.ndarray]: ...
def frame_flow(prev: np.ndarray, cur: np.ndarray, cam=None,
               block: int = 8, reach: int = 2) -> tuple[float, float, float, float]: ...
def analyse(path: str | Path, audio: np.ndarray | None = None, duration: float = 0.0,
            t0: float = 0.0, cam: tuple[int, int, int, int] | None = None,
            video: bool = True) -> dict: ...
def label(words: list[dict], moments: list[dict], min_score: float = .55,
          slack: float = 2.0, top: int = 2) -> list[dict]: ...
def best(moments: list[dict], kind: str) -> dict | None: ...
def overlap(start: float, end: float, moments: list[dict], kind: str | None = None) -> float: ...
def fallback(words: list[dict], moments: list[dict], n: int, min_len: int, max_len: int,
             duration: float) -> list[dict]: ...
def public(moments: list[dict]) -> list[dict]: ...
def settings() -> dict: ...
def save(changes: dict) -> dict: ...
def selftest() -> int: ...
```

### 4.3 What each returns

- `audio_feats(pcm)` - `{"low","voice","high","all"}`, each `float64` dB array at 20 Hz. `pcm` is **float32 in -1..1**; PeakCut holds int16, so callers pass `audio[a:b].astype(np.float32) / 32768`.
- `score(F, has_video, has_cam)` - `{type: np.ndarray}`, six `float64` arrays in 0..1 at 2 Hz, same length as `F["voice"]`. Never raises; `np.nan_to_num` inside.
- `segments(S, t0, gap, thr, min_len)` - `list[dict]`, each `{"t0": float, "t1": float, "type": str, "score": float}`. `t0`/`t1` rounded to 0.1 s and offset by `t0`; `score` = 90th percentile rounded to 2 dp. Defaults `thr=THR`, `min_len=MIN_LEN` so the tuning table can be overridden from `moments.json`.
- `analyse(...)` - the whole pipeline for one file, returning
  `{"t0": float, "dur": float, "has_video": bool, "cam": list[int] | None, "scan_s": float, "x_realtime": float, "moments": list[dict]}`.
  It must **not** write anything to disk and must **not** raise on a missing video track: fall back to `has_video=False` (scores capped at 0.7) and return the audio-only labelling. Return `{"moments": [], ...}` when there is no audio.
- `label(words, moments, min_score=.55, slack=2.0, top=2)` - pure re-implementation of `tag_transcript`: returns a **new** list of word dicts, each optionally carrying `"moment"` (best type) and `"moment_score"` (float). Sort the overlapping types by score descending, keep `top`. No file I/O, no `.bak`, idempotent by construction.
- `best(moments, kind)` - highest-scoring moment of that type, or `None`.
- `overlap(start, end, moments, kind=None)` - seconds of `[start, end)` covered by matching moments (mirrors `quality.static_overlap`'s shape, `quality.py:91`).
- `fallback(words, moments, n, min_len, max_len, duration)` - the no-AI picker: convert each moment to a clip `{start, end, score, category, hook, title, description, hashtags, highlight_words, reason}`, clipping `min_len`/`max_len`, deduplicating overlaps, `category` mapped to the existing `brain.CATEGORIES` vocabulary so the SPA keeps working: `chase -> clutcho?` **no** - use `{"chase": "clutch", "crash": "fail", "fight": "rage", "stunt": "clutch", "reaction": "shock", "funny": "funny"}`. `reason` = `"Picked from the sound and motion of the game, because the AI was unavailable."`
- `public(moments)` - the list minus any internal keys, floats rounded to 0.1/2 dp, safe for `job.json` and the browser.

### 4.4 Wiring into `_run_job` - exact call sites

1. **Where to analyse.** Inside the block loop in `_run_job`, after the transcript for the block exists (`peakcut/studio/jobs.py:728-730`), the block's own audio is `audio[a:b]` (int16, 16 kHz, `jobs.py:713`). Call:

   ```python
   mo = moments.analyse(job.get("source_path") or "", audio=audio[a:b], duration=(b - a) / 16000,
                        t0=a / 16000, cam=..., video=bool(job.get("source_path")))
   ```
   `job["source_path"]` is set at `jobs.py:603` (file uploads) and `jobs.py:636` (whole-video downloads); for long videos streamed as pieces it is absent, so the call degrades to audio-only - correct, and it must not trigger a download just to look at motion.

2. **Camera box.** When `layout == "gameplay"`, `jobs.py:762-765` already calls `_facecam(job)` -> `facecam.detect(...)` -> `{"x","y","w","h"}` in **source pixels**. Convert to 160x90 units before passing:
   `cam = (int(x * W / src_w), int(y * H / src_h), int((x + w) * W / src_w), int((y + h) * H / src_h))`, using `job["width"]` / `job["height"]`. Do not port `find_cam`; do not add YuNet.

3. **Feed the picker.** Extend `peakcut/studio/brain.py:273` `find_clips(...)` with a keyword-only `hints: list[dict] | None = None`. When present, append one line per hint to the prompt (`brain.py:290-292` block, next to `_game_rules(game)`): `"Measured events in this stretch: chase 12.5-31.0s, crash 41.0-44.2s, ..."`. This is a hint, not a filter - the model still picks, so clip quality cannot regress.

4. **No-AI path.** In `find_clips`, replace the `if not used_model:` branch (`brain.py:300-302`) so it calls `moments.fallback(...)` when moments are supplied, else keeps `fallback_by_loudness` unchanged. `peakcut/studio/brain.py:245` stays as the last resort.

5. **Stamp the clip.** At `jobs.py:757`, add `moment=` to the `c.update(...)` dict: the type of the highest-overlap moment (`moments.best` / `overlap`), or `None`. `render_one` (`jobs.py:373`) and `render.render_clip` need **no change** - this is metadata, and per brief ground rule 4 a user who never enables it gets byte-identical clips.

6. **Persist.** `job["moments"] = moments.public(mo_list)` after the loop; `job.json` is already the store (`jobs.save`, `jobs.py:169`). The `public(job)` filter at `jobs.py:152` passes unknown keys straight through, so no change is needed there - but per-clip `moment` must be a plain string, because `jobs.public` only strips `("src", "fixed_words", "fixed_for")` from clips.

7. **Never** call this from `render.py` or from a request handler: it is a job-stage function, run on the worker thread, under the existing queue fairness (`_FairQueue`, `jobs.py:16`) and load limiter.

### 4.5 The numpy-only flow substitute (this is the one real porting decision)

`moments.py:163` needs `cv2.calcOpticalFlowFarneback`, and **opencv is not in `peakcut/requirements.txt`** (numpy 2.2.6, soundfile, sherpa-onnx, pillow, httpx, fastapi, SQLAlchemy, psycopg, python-multipart, uvicorn, yt-dlp - and nothing else). Adding `opencv-python-headless` is ~40 MB and violates brief ground rule 3.

`frame_flow` replaces it with block matching at 160x90, and the three metrics that leave it keep the **exact** formulas of `moments.py:165`:

```python
def frame_flow(prev, cur, cam=None, block=8, reach=2):
    """(m, out, rot, cam_motion) for one frame pair at 160x90. numpy only."""
    a = prev.astype(np.float32); b = cur.astype(np.float32)
    mask = np.ones((H, W), bool)
    if cam:
        mask[cam[1]:cam[3], cam[0]:cam[2]] = False
    m = float(np.abs(b - a)[mask].mean()) / 255.0          # same quantity as mean|flow|, 0..1
    # per 8x8 block: pick the (dx, dy) in -2..2 with the lowest SSD, on a 3-level pyramid if you want speed
    # dx, dy grids for all blocks at once, shape (by, bx)
    xc = block_x + block / 2 - W / 2      # block centre minus frame centre, float32
    yc = block_y + block / 2 - H / 2
    r  = np.hypot(xc, yc) + 1
    out = float(((xc * dx + yc * dy) / r)[valid].mean())
    rot = float(((xc * dy - yc * dx) / r)[valid].mean())
    cm  = float(np.abs(b[cam[1]:cam[3], cam[0]:cam[2]] - a[cam[1]:cam[3], cam[0]:cam[2]]).mean()) if cam else 0.0
    return m, out, rot, cm
```

Cost at 2 fps: 220 blocks x 25 candidate offsets x 64 px = ~350k multiply-adds per frame pair, vectorised as 25 shifted whole-frame differences plus a block-sum. That is cheaper than Farneback, and the downstream `pct()` normalisation is scale-free, so the shift from dense per-pixel flow to block-mean flow barely moves the scores.

**Fidelity caveat for the build agent:** `m` becomes a normalised mean absolute difference (0..1) rather than a pixel displacement. `pct()` (percentile normalisation) absorbs the change of units, so every downstream threshold still holds - but `score()` must be re-run against the reference selftest (section 7) and, if `chase`/`stunt` come out weak, the fix is the block search range (`reach`), not the constants. If opencv is ever approved, keep the signature and drop in `cv2.calcOpticalFlowFarneback(prev, f, None, .5, 2, 9, 2, 5, 1.1, 0)` unchanged.

### 4.6 Things that must be renamed or dropped

| source | PeakCut |
|---|---|
| `read_audio` (moments.py:120, second ffmpeg decode) | drop - use `media.load_audio` (`media.py:317`) and slice `audio[a:b]` |
| `find_cam` (moments.py:132, YuNet) | drop - use `facecam.detect` (`facecam.py:329`), convert units |
| `probe` (moments.py:113) | drop - `media.probe` (`media.py:293`) already returns width/height/duration and raises a friendly error for no-audio |
| `tag_transcript` (moments.py:195, writes file + `.bak`) | `label()` - pure, returns new word dicts |
| `banner_moments` (moments.py:188) | out of scope (feature 05); tolerate `"banner"` in a `TYPE` tuple |
| `sheet` (moments.py:219, contact sheet, cv2) | out of scope; if wanted later, ffmpeg `select`+`tile` |
| `run` (moments.py:237, CLI + file writes) | `analyse()` - no disk writes, no `SystemExit` |
| `--selftest` CLI | `selftest()` callable, plus `tests/test_moments.py` |

### 4.7 Optional routes (only if the UI is wanted; admin-gated, mirrors transcription)

Follow `peakcut/studio/server.py:1313-1430` exactly: `_admin(request)` (`server.py:310`), `_throttle(...)` (`server.py:633`), `HTTPException(400)` for user error.

```python
def _mo_file(): return config.DATA_DIR / "moments.json"      # same shape as _tr_file, server.py:1317
@app.get("/api/moments")   def moments_get(request: Request): _admin(request); return moments.settings()
@app.put("/api/moments")   def moments_put(request: Request, body: dict = Body(...)): ...
@app.post("/api/moments/test") def moments_test(request: Request): ...   # analyse a 20 s slice of any finished job
```

`moments_test` should run `analyse` over one already-finished job's `source_path` first 20 s and return the spans, so the admin can see it work without waiting for a render.

## 5. Data files

One new file: **`<DATA_DIR>/moments.json`** (i.e. `config.DATA_DIR / "moments.json"`), created lazily on first save, never required to exist. Read it the way `ai.py:43-60` reads `ai.json` (`_file()` + mtime-keyed cache); write it the way `server.py:1377-1387` writes `tr.json` (tmp file, lock, `tmp.replace(f)`).

Schema - every key optional, missing means default:

```json
{
  "enabled": false,
  "min_score": 0.55,
  "tag_words": true,
  "hint_ai": true,
  "use_when_no_ai": true,
  "types": {
    "chase":    {"thr": 0.5,  "min_len": 5,   "on": true},
    "crash":    {"thr": 0.7,  "min_len": 1.0, "on": true},
    "fight":    {"thr": 0.6,  "min_len": 4,   "on": true},
    "stunt":    {"thr": 0.7,  "min_len": 3,   "on": true},
    "reaction": {"thr": 0.55, "min_len": 2,   "on": true},
    "funny":    {"thr": 0.5,  "min_len": 2,   "on": true}
  }
}
```

- `enabled` defaults to **false** (brief ground rule 4: degrade to today's behaviour).
- `types[*].thr` and `types[*].min_len` override `THR` / `MIN_LEN` in `segments(thr=..., min_len=...)`; `on: false` removes the type from `score()`'s returned dict and therefore from `segments`.
- Validation: clamp `thr` to 0..1, `min_len` to 0.5..60, `min_score` to 0..1; unknown types dropped. `save()` raises `ValueError` with a user-readable message (the route converts it to `HTTPException(400)`).

Per-job output, in the existing `job.json` (no new file): `job["moments"]` = the `public()` list, and `job["clips"][i]["moment"]` = a type string or absent. Nothing is written into the user's source folder - `moments.py`'s `<src>.moments.json` side-file must not be reproduced, because PeakCut's source path can be a shared download or a read-only upload.

No model file, no font, no static asset.

## 6. Risks

- **No opencv.** The naive paste dies at `import cv2`. Use section 4.5, or get explicit approval for `opencv-python-headless` - do not silently add it.
- **CPU on a shared box.** 85x realtime is one job on an idle laptop. With `JOB_WORKERS` (`config.py:183`) jobs running, a full-length video decode at 2 fps competes with the renders. Run only inside `_run_job`, cap with `config.MAX_VIDEO_HOURS` (`config.py:187`), and skip entirely for pieces-only jobs (`jobs.py:594`).
- **Single-user assumptions that break.** The source writes `<src>.moments.json`, a `.bak` next to the transcript, and uses `SystemExit` and a global `HERE`. None of that survives: no writes outside `job["dir"]`, no exceptions that kill a worker, no module-level mutable state (threads and `ctx` - see `ctx.py:43 bind`). Two users analysing at once must not share any buffer.
- **`tag_transcript` is a destructive edit.** Porting it as-is would rewrite a file that a user may be reading; `label()` returning new dicts is the only safe form.
- **Silent unit change in `m`.** See 4.5 - every `m`-derived score (`chase`, `fight`, `stunt`, `reaction`) shifts if the block matcher returns a different scale. Re-run the selftest after swapping the flow.
- **`funny` depends on chat and laughter text.** PeakCut has no `[CHAT ...]` tags in transcripts, so `chat_lol` is always 0 in VOD; `txt_laugh` from word regexes still works, and the `np.where(txt > .3, 1, .75)` damping already accounts for audio-only. Chat counts exist only for live recordings (`live.py:133 chat`, Twitch only) - wire them if cheap, otherwise accept weaker `funny`.
- **Over-trust.** A moment type is a hint, not a verdict. Never let it *remove* a clip the AI chose; only annotate, hint, or supply a fallback.
- **numpy 2.2.6.** `np.hanning`, `np.percentile`, `np.pad(mode="edge")` are all fine; avoid `np.float_`/`np.int0` and any removed alias.

## 7. Verification

1. **Unit, no media needed** - port the reference selftest as `selftest()` and as `peakcut/tests/test_moments.py` (same `PASS <name>` / `raise AssertionError` style as `tests/test_captions.py:16-19`, driven by `tests/run.py`):

   ```bash
   cd peakcut && python -c "from studio import moments; assert moments.selftest() > 0"
   python tests/test_moments.py
   ```

   It must assert: all six types found in their planted stretches, nothing before bin 45, `stunt` absent and `crash` present when `has_video=False`, and that `label()` is idempotent (`label(label(w, m), m) == label(w, m)`) and never exceeds 2 types per word.

2. **Real file, one command** - build a 40 s fixture with two halves (still + a fast pan with a bang) and check the labelling end to end:

   ```bash
   cd peakcut && ffmpeg -y -v error -f lavfi -i "testsrc2=size=1280x720:rate=30:duration=20" \
     -f lavfi -i "sine=frequency=120:duration=20" -shortest /tmp/mo_a.mp4 && \
   ffmpeg -y -v error -i /tmp/mo_a.mp4 -filter_complex "[0:v]hue=s=0,noise=alls=40:allf=t+u[v]" \
     -map "[v]" -map 0:a -t 20 /tmp/mo_b.mp4 && \
   python -c "
   import time; from studio import moments
   t=time.time(); r=moments.analyse('/tmp/mo_b.mp4'); print(r['moments'], r['x_realtime'], 'x realtime')
   assert r['dur'] > 19 and isinstance(r['moments'], list); assert time.time()-t < 60"
   ```

3. **In the app** - with `enabled: true` in `moments.json`, run one video with no AI key set: `job["moments"]` is non-empty, `job["clips"][0]["moment"]` names a type, and `job["ai"]["note"]` no longer says the picks came from loudness alone. Then set `enabled: false` and confirm the same video produces byte-identical `job.json` clip dicts to a run before the change (ground rule 4).
4. **Full suite, nothing regressed**: `python tests/run.py` - in particular `tests/test_captions.py` and `tests/test_static.py`, which both exercise `render`/`quality` paths this feature sits next to.
