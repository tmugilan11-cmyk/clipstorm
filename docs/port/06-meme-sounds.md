# 06 — Meme sounds (9 moods) with per-mood visual treatment

Source: `C:\Users\Asus\Documents\deepseek-harness\default-workspace\gta6-clipper-main\meme.py` (305 lines).
Host: `peakcut/`. Everything below is derived from the two codebases as they stand; no new dependency is needed
(`numpy` 2.2.6 and `soundfile` 0.14.0 are already in `peakcut/requirements.txt`).

---

## 1. What it does

At one chosen beat of a finished clip — the payoff — the clip plays a short synthesised comedy sound and
simultaneously applies a matching visual gag: a slow push-in, a quick punch-in, a shake, a white flash, a dark
vignette, or desaturation. Nine named moods (`embarrassing`, `fail`, `shock`, `hype`, `win`, `awkward`, `cringe`,
`funny`, `suspense`) each fix a sound choice, an effect set, a volume, a start offset, an optional freeze-frame
and an optional tail extension. The sound is faded in over the clip's own ducked audio and the result is
re-normalised to −14 LUFS. The gag may freeze the picture for up to ~1.2 s and may extend the clip by at most
3 s, and it never lands in the first 3 s.

---

## 2. Exact mechanics

All references are to `gta6-clipper-main/meme.py` (absolute path above). Audio source of truth is
`gta6-clipper-main/sounds/` (10 rendered `.wav` files plus `moods.json` exist on disk and can be copied as
fixtures).

### 2.1 Constants

```python
SR = 48000          # meme.py:15  every sound is mono 48 kHz
HOOK_SAFE = 3.0     # meme.py:16  a gag never lands before this second
MAX_EXT = 3.0       # meme.py:17  a gag may lengthen the clip by at most this
SND = HERE / "sounds"   # meme.py:14
```

`run(cmd, timeout=900, **k)` (`meme.py:19`) is a subprocess wrapper that returns a `CompletedProcess` with
returncode `124` and stderr `f"timeout after {timeout} s"` instead of raising. `probe(f)` (`meme.py:24`) returns
`(width, height, duration)` via `ffprobe -show_entries stream=width,height:format=duration -of json`.

### 2.2 Synthesis primitives (`meme.py:29-40`)

| helper | exact behaviour |
|---|---|
| `_t(d)` | `np.arange(int(d * SR)) / SR` — `meme.py:29` |
| `_env(n, a=0.005, r=0.05)` | ones of length `n`; `na=max(int(a*SR),1)`, `nr=max(int(r*SR),1)`; first `na` = `linspace(0,1,na)`; last `nr` = `minimum(e[-nr:], linspace(1,0,nr))` — `meme.py:30-31` |
| `_lp_fast(x, fc, n=3)` | FFT low-pass: `X *= 1 / (1 + (f/fc) ** (2*n))` on the rfft, then `irfft(X, len(x))` — `meme.py:32-33` |
| `_bp(x, lo, hi)` | FFT brick-wall band-pass: `X *= ((f > lo) & (f < hi))` — `meme.py:34-35` |
| `_reverb(x, tail=0.5, mix=0.25, seed=1)` | `ir = rng(seed).standard_normal(int(tail*SR)) * exp(-arange(n)/(SR*tail/5))`, `_lp_fast(ir, 3000)`; convolve with `np.fft.rfft` at length `len(x)+n`; normalise `y /= max(|y|)`; `z[:len(x)] = x`; return `z*(1-mix) + y*mix*max(|x|)` — `meme.py:36-39` |
| `_norm(x, peak_db=-3.0)` | `x / (max(|x|)+1e-9) * 10**(peak_db/20)` — `meme.py:40` |

### 2.3 The ten sounds (`meme.py:42-106`)

Every one of these must be reproduced sample-exactly; the `rng` seeds are part of the recipe.

**`vine_boom()` — 1.8 s, `meme.py:42-46`**
```python
t = _t(1.8); f = 38 + 120 * np.exp(-t * 14); ph = 2 * np.pi * np.cumsum(f) / SR
x = np.tanh(2.2 * np.sin(ph)) * np.exp(-t * 2.6) + 0.35 * np.sin(2 * ph) * np.exp(-t * 6)
x += 0.5 * _bp(np.random.default_rng(3).standard_normal(len(t)), 80, 900) * np.exp(-t * 30)
return _norm(_reverb(x * _env(len(t), 0.002, 0.2), 0.6, 0.18))
```
Spectral peak must be **< 150 Hz** (`meme.py:271`).

**`sad_trombone()` — 3.35 s, `meme.py:47-56`**
```python
notes = [(233.1, .55), (220.0, .55), (207.7, .55), (196.0, 1.5)]
for i, (f0, d) in enumerate(notes):
    t = _t(d); last = i == 3
    f = f0 * (1 + (0.004 * np.sin(2 * np.pi * 5.5 * t) if last else 0)) * (1 - 0.06 * np.clip((t - 0.5) / 1.0, 0, 1) if last else 1)
    ph = 2 * np.pi * np.cumsum(f) / SR; wah = 0.25 + 0.75 * np.sin(np.pi * np.clip(t / d, 0, 1)) ** 0.7
    x = sum(np.sin(k * ph) * k ** -1.0 * np.exp(-k / (1 + 9 * wah)) for k in range(1, 22))
    x = x + 0.04 * np.random.default_rng(i).standard_normal(len(t))
    out.append(x * _env(len(t), 0.04, 0.12 if not last else 0.35) * (0.6 + 0.4 * wah)); out.append(np.zeros(int(0.05 * SR)))
x = np.concatenate(out); return _norm(_reverb(_bp(_lp_fast(x, 2200), 80, 9000), 0.4, 0.15))
```
21 harmonics with `k**-1.0`, a mute "wah" that opens then closes, 50 ms of silence between notes.
Note the source quirk at `meme.py:51`: the `if last else 1` binds to the whole second factor, so only the last
note gets the 6 % pitch fall and the 5.5 Hz vibrato.

**`record_scratch()` — 0.75 s, `meme.py:57-62`**
```python
f = 900 * np.exp(-t * 2.2) * (1 + 0.5 * np.sin(2 * np.pi * 9 * t)); ph = 2 * np.pi * np.cumsum(f) / SR
saw = 2 * ((ph / (2 * np.pi)) % 1) - 1; noise = _bp(rng.standard_normal(len(t)), 1500, 9000)
x = (0.6 * saw + 0.9 * noise) * (0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 14 * t)))
x += 0.6 * (rng.random(len(t)) > 0.9985) * rng.standard_normal(len(t))      # vinyl crackle
return _norm(x * _env(len(t), 0.003, 0.03) * np.exp(-t * 1.5))
```
`rng = np.random.default_rng(5)`; the crackle draw happens **after** the noise draw, so the stream order matters.

**`airhorn()` — 2.22 s, `meme.py:63-72`**
```python
for d in (0.28, 0.28, 0.28, 1.1):
    t = _t(d); x = 0
    for f in (415.3, 523.3, 622.3):                     # Ab, C, Eb  (MLG chord)
        ph = 2 * np.pi * np.cumsum(f * (1 + 0.003 * np.sin(2 * np.pi * 7 * t))) / SR
        x = x + sum(np.sin(k * ph) * k ** -0.65 for k in range(1, 16))
    x = np.tanh(0.25 * x) * (1 + 0.15 * np.random.default_rng(1).standard_normal(len(t))) * _env(len(t), 0.012, 0.06 if d < 1 else 0.3)
    out += [x, np.zeros(int(0.07 * SR))]
return _norm(_reverb(_lp_fast(np.concatenate(out), 5000), 0.5, 0.15))
```
15 harmonics, `k**-0.65`; 70 ms of silence after each of the four bursts.

**`bass_drop()` — 2.2 s, `meme.py:73-77`**
```python
f = np.where(t < 0.9, 220 * np.exp(-t * 2.4) + 38, 38 + 0 * t)
x = np.tanh(1.6 * np.sin(ph)) * np.where(t < 0.9, 0.7, 1.0) * np.exp(-np.maximum(t - 0.9, 0) * 1.4)
x += 0.5 * _bp(np.random.default_rng(2).standard_normal(len(t)), 2000, 9000) * np.exp(-t * 4) * (t < 0.9)
return _norm(x * _env(len(t), 0.01, 0.3))
```

**`crickets()` — 3.4 s, `meme.py:78-84`**
```python
for f, rate, ph0 in [(4300, 2.6, 0.0), (4750, 2.1, 0.3), (3900, 3.0, 0.6)]:
    gate = (((t * rate + ph0) % 1) < 0.35).astype(float)
    pulse = (np.sin(2 * np.pi * 38 * t) > 0.2).astype(float)
    x += np.sin(2 * np.pi * f * t) * gate * pulse * 0.4
x += 0.012 * _lp_fast(rng.standard_normal(len(t)), 1500)      # night air, rng seed 7
return _norm(x * _env(len(t), 0.2, 0.5), -8)
```
Normalised to **−8 dB** peak (not −3). Spectral peak must be **between 3500 and 5200 Hz** (`meme.py:272`).

**`heartbeat()` — 3.4 s, `meme.py:85-91`**
```python
d = 3.4; x = np.zeros(int(d * SR))
for b in np.arange(0.0, d - 0.6, 0.85):                  # beats at 0, 0.85, 1.70, 2.55
    for off, g, f0 in [(0, 1.0, 62), (0.2, 0.7, 52)]:
        n = int(0.22 * SR); t = np.arange(n) / SR; i = int((b + off) * SR)
        x[i:i + n] += np.sin(2 * np.pi * (f0 + 30 * np.exp(-t * 30)) * t) * np.exp(-t * 18) * g
return _norm(_reverb(x, 0.3, 0.1), -4)                   # −4 dB peak
```

**`whoosh()` — 0.7 s, `meme.py:92-96`**
```python
fc = 400 + 5500 * np.sin(np.pi * t / 0.7) ** 2
for lo in range(0, len(t), 480):                         # 10 ms hop, 20 ms window
    seg = n[lo:lo + 960]; k = len(seg); y[lo:lo + k] += _bp(seg, fc[lo] * .6, fc[lo] * 1.5) * np.hanning(k)
return _norm(y * np.sin(np.pi * t / 0.7) ** 1.5)         # rng seed 4
```

**`ding()` — 1.6 s, `meme.py:97-99`**
```python
x = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, a, d in [(1318.5, 1, 3), (2637, .35, 5), (3951, .15, 8)])
return _norm(x * _env(len(t), 0.002, 0.05))
```

**`rimshot()` — 1.7 s buffer, `meme.py:100-106`**
```python
out = np.zeros(int(1.7 * SR)); rng = np.random.default_rng(6)
def drum(at, f, d, noise):
    t = _t(d); i = int(at * SR)
    out[i:i + len(t)] += np.sin(2 * np.pi * (f + 90 * np.exp(-t * 40)) * t) * np.exp(-t * 14) \
                       + noise * _bp(rng.standard_normal(len(t)), 1500, 9000) * np.exp(-t * 25)
drum(0.0, 190, 0.25, 0.9); drum(0.16, 110, 0.35, 0.1)
t = _t(1.2); i = int(0.42 * SR)
out[i:i + len(t)] += 0.7 * _bp(rng.standard_normal(len(t)), 5000, 14000) * np.exp(-t * 4)   # cymbal
return _norm(out)
```
The `drum` closure draws from the shared `rng` in call order — call `drum(0.0, …)` before `drum(0.16, …)`,
then the cymbal.

**Registry / writer (`meme.py:107-116`)**
```python
SOUNDS = dict(vine_boom=vine_boom, sad_trombone=sad_trombone, record_scratch=record_scratch, airhorn=airhorn,
              bass_drop=bass_drop, crickets=crickets, heartbeat=heartbeat, whoosh=whoosh, ding=ding, rimshot=rimshot)

def write_wav(path, x):     # mono, 16-bit, SR
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())

def make_sounds(d=None):
    d = Path(d or SND); d.mkdir(parents=True, exist_ok=True)
    for n, f in SOUNDS.items(): write_wav(d / f"{n}.wav", f())
    return sorted(SOUNDS)
```

### 2.4 The mood table — reproduce verbatim (`meme.py:119-129`, also on disk as `sounds/moods.json`)

| mood | sound (str, or list → first existing wins) | effect | volume dB | offset s | hold s | tail |
|---|---|---|---|---|---|---|
| `embarrassing` | `["mine/hello_darkness", "sad_trombone"]` | `["zoom","vignette","desat"]` | −3 | 0.0 | 1.2 | `"auto"` |
| `fail` | `["mine/sad_violin", "sad_trombone"]` | `["punch","desat"]` | −2 | 0.1 | 0.0 | `"auto"` |
| `shock` | `"vine_boom"` | `["punch","flash"]` | 0 | 0.0 | 0.0 | 0 |
| `hype` | `["airhorn","bass_drop"]` | `["punch","shake","flash"]` | −2 | 0.0 | 0.0 | 0 |
| `win` | `"bass_drop"` | `["punch","flash"]` | −2 | −0.15 | 0.0 | 0 |
| `awkward` | `["mine/curb_enthusiasm","crickets"]` | `["zoom","desat"]` | −4 | 0.0 | 0.8 | `"auto"` |
| `cringe` | `"record_scratch"` | `["flash","desat"]` | −2 | 0.0 | 1.0 | 0.4 |
| `funny` | `["rimshot","ding"]` | `["punch"]` | −3 | 0.1 | 0.0 | 0.6 |
| `suspense` | `"heartbeat"` | `["zoom","vignette"]` | −3 | −0.3 | 0.0 | 0 |

Effect vocabulary is closed: `zoom`, `punch`, `shake`, `flash`, `vignette`, `desat` (`meme.py:8`).

### 2.5 Resolution and defaults

```python
def load_moods():          # meme.py:130-133
    p = SND / "moods.json"
    if not p.exists(): p.write_text(json.dumps(DEFAULT_MOODS, indent=1)); return DEFAULT_MOODS
    return json.loads(p.read_text())

def resolve_sound(spec):   # meme.py:134-141
    names = [spec] if isinstance(spec, str) else spec
    for _ in range(2):                                   # second pass after synthesising
        for n in names:
            for ext in ("wav", "m4a", "mp3"):
                if (SND / f"{n}.{ext}").exists(): return SND / f"{n}.{ext}"
        if not any(SND.glob("*.wav")): make_sounds()
    raise SystemExit(f"no sound found for {spec} in {SND}")
```
So `mine/hello_darkness` and `mine/sad_violin` and `mine/curb_enthusiasm` fall through to the shipped sound
unless the user dropped a file into `sounds/mine/`.

### 2.6 Payoff detection (`meme.py:144-150`)

```python
o = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-vn", "-ac", "1", "-ar", "16000",
                    "-f", "s16le", "-"], capture_output=True, timeout=300).stdout
x = np.frombuffer(o, "<i2").astype(float); w = 1600; n = len(x) // w     # 100 ms windows at 16 kHz
if n < 5: return max(HOOK_SAFE, dur * 0.7)                                # under 0.5 s of audio
r = np.sqrt((x[: n * w].reshape(n, w) ** 2).mean(1))
lo = int(max(dur * 0.4, HOOK_SAFE) * 10); hi = max(int((dur - 0.6) * 10), lo + 1)   # in tenths
return float(np.argmax(r[lo:hi]) + lo) / 10
```
"Loudest 100 ms in the last 60 % of the clip, never inside the hook." Search range starts at
`max(0.4*dur, 3.0) s` and ends at `dur − 0.6 s`; the result is rounded to 0.1 s.

### 2.7 Timing (`meme.py:153-160`)

```python
W, H, dur = probe(src)
T = float(at) if at is not None else find_payoff(src, dur)
T = min(max(T, HOOK_SAFE), dur - 0.4)                      # clamp; may silently land below HOOK_SAFE
L = duration of the resolved sound (ffprobe, seconds)
hold = float(m.get("hold", 0))
S    = max(HOOK_SAFE, T + float(m.get("offset", 0)))       # sound start, never before 3 s
tail = m.get("tail", 0)
tail = max(0.0, S + L - (dur + hold)) + 0.3 if tail == "auto" else float(tail)
tail = max(0.0, min(tail, MAX_EXT - hold))                 # hold + tail <= 3 s
total = dur + hold + tail
```

### 2.8 Video chain (`meme.py:161-175`)

Transient displacement, applied to the first segment after `T` (the freeze if there is one, else the live video):

```python
zt = []
if "zoom"  in fx: zt.append(f"0.14*min(t/{hold if hold else 1.5:.3f},1)")
if "punch" in fx: zt.append("0.12*max(0,1-t/0.35)")
if "shake" in fx: zt.append("0.05"); dx = "20*sin(t*70)*max(0,1-t/0.5)"; dy = "14*cos(t*83)*max(0,1-t/0.5)"
Z = "1+" + "+".join(zt) if zt else None
trans = (f"scale=w='2*trunc(iw*({Z})/2)':h='2*trunc(ih*({Z})/2)':eval=frame,"
         f"crop={W}:{H}:'(iw-{W})/2+{dx}':'(ih-{H})*0.4+{dy}'," if Z else "")
flash = "fade=t=in:st=0:d=0.22:color=white," if "flash" in fx else ""
stat  = ("eq=saturation=0.25:contrast=1.05," if "desat" in fx else "") + ("vignette=angle=0.95," if "vignette" in fx else "")
base  = "fps=30,setsar=1,format=yuv420p,"
```

Filtergraph (three waypoints `[pre]`, `[hold]`, `[post]` concatenated; `[hold]` only when `hold > 0`):

```
[0:v]split=3[a][b][c]
[a]trim=0:{T},setpts=PTS-STARTPTS,{base}null[pre]
[b]trim=start={T}:end={T+0.1},setpts=PTS-STARTPTS,fps=30,trim=end_frame=1,tpad=stop_mode=clone:stop_duration={hold},setpts=PTS-STARTPTS,{trans}{flash}{stat}{base}null[hold]
[c]trim=start={T},setpts=PTS-STARTPTS,{ "" if hold else trans+flash }{stat}{base} [tpad=stop_mode=clone:stop_duration={tail},] null[post]
[pre][hold][post]concat=n=3:v=1:a=0[vo]
```
Without a hold it is `split=2[a][c]`, `[pre][post]concat=n=2`, and `[c]` carries `trans` + `flash`.
Numbers are formatted `:.3f` (time) and the zoom denominator `:.3f`. The crop y origin is
`(ih - H) * 0.4` — the frame is biased upward, keeping the face.

### 2.9 Audio chain (`meme.py:177-183`)

```
[0:a]aresample=48000,aformat=channel_layouts=stereo,asplit=2[x][y]
[x]atrim=0:{T},asetpts=PTS-STARTPTS[ap]
[y]atrim=start={T},asetpts=PTS-STARTPTS[aq]
(hold) anullsrc=r=48000:cl=stereo,atrim=0:{hold},asetpts=PTS-STARTPTS[ah] ; [ap][ah][aq]concat=n=3:v=0:a=1[ao]
(!hold) [ap][aq]concat=n=2:v=0:a=1[ao]
[ao]apad=whole_dur={total},volume=0.3:enable='between(t,{S},{S+Lm})'[ad]
[1:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{Lm},afade=t=out:st={max(Lm-0.25,0)}:d=0.25,volume={mood volume}dB,adelay={int(S*1000)}|{int(S*1000)}[as]
[ad][as]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=9,atrim=0:{total}[ao2]
```
with `Lm = min(L, total - S)`. The clip's own audio is **ducked to 30 % (−10.5 dB) while the sound plays** and is
silent during a freeze (`anullsrc`), because the concat replaces time rather than extending it.

### 2.10 Encode (`meme.py:184-187`)

The whole graph is written to a temp file (`Path(tempfile.mkdtemp(prefix="meme_")) / "g.txt"`, joined with `;`)
and passed as `-filter_complex_script`:

```
ffmpeg -y -loglevel error -i {src} -i {sound} -filter_complex_script {g.txt}
       -map [vo] -map [ao2] -t {total}
       -c:v libx264 -crf 18 -preset fast -c:a aac -b:a 192k -ar 48000 -movflags +faststart {out}
```
Returns `dict(out=str(out), at=round(T,2), sound=snd.name, hold=hold, tail=round(tail,2), duration=round(total,2))`.

### 2.11 Contact sheet (`meme.py:191-196`)

Five frames at `[T-0.8, T+0.02, T+0.3, T+hold*0.9+0.3, total-0.1]`, each `scale=216:-2`, `hstack=inputs=5`,
`-frames:v 1 -q:v 3`. Optional (`sheet=` argument); useful for reviewing a mood without watching the clip.

### 2.12 Loudness measurement (`meme.py:198-200`)

`ffmpeg -nostats -i F -af ebur128=peak=true -f null -`, parse the **last** `I: x LUFS` and `Peak: x dBFS`
from stderr. Used only by the selftest.

### 2.13 Self-test assertions (`meme.py:265-292`) — the acceptance criteria

* every sound: `0.3 < len/SR < 4`, `0.3 < max|x| <= 1`, no NaN;
* `vine_boom` spectral peak `< 150 Hz`; `crickets` peak in `(3500, 5200)` Hz;
* fixture: `testsrc2=s=360x640:r=30:d=10` + `sine=f=300` at `volume=0.3`, `-shortest -pix_fmt yuv420p`;
* `3.0 <= find_payoff(fixture, 10) <= 9.4`;
* every mood at `at=5.0`: output `(w,h) == (360,640)`, `abs(d - res["duration"]) < 0.15`,
  `10 <= d <= 10 + MAX_EXT + 0.1`, integral loudness `-17 < i < -11`;
* `meme(fixture, "shock", at=0.5)["at"] >= HOOK_SAFE` (hook protection);
* a stalled tool returns rc 124 rather than blocking.

---

## 3. PeakCut today

What already exists, and how far it is from the above.

| Area | Today | Gap |
|---|---|---|
| Clip rendering | `peakcut/studio/render.py:267` `render_clip(src, out_dir, name, clip, words, src_w, src_h) -> dict` writes `<name>.mp4/.jpg/.ass`; the ffmpeg call is `peakcut/studio/render.py:289-315` `_render_in` — `-ss start -t (end-start) -i src -filter_complex fc -map [v] -map 0:a:0 -af loudnorm=I=-14:TP=-1.5:LRA=11`, qsv `global_quality 23` falling back to `libx264 -crf 21 -preset veryfast` | No second audio input, no freeze, no appended tail, no per-clip effect pass. `-t` is fixed to `end - start`, so the renderer cannot lengthen a clip at all. |
| Effect vocabulary | `peakcut/studio/render.py:235-252` `_filter` — only layout composition (blur / zoom / crop / gameplay PIP) | Nothing in common with `zoom/punch/shake/flash/vignette/desat`. |
| Captions | `peakcut/studio/render.py:159` `build_ass(...)`; styles at `peakcut/studio/render.py:14-21` (`bounce`, `hype`, `clean`) | Unrelated, but it is the model for "a named look selected per clip". |
| Settings persistence | `peakcut/studio/ai.py:39` `_lock`, `:43` `_file()` → `config.DATA_DIR/"ai.json"`, `:47` `_from_dashboard()` (mtime cache), `:99` `public()`, `:110` `save()` | The pattern to copy for a mood table. Nothing mood-related exists. |
| Admin gate / throttle | `peakcut/studio/server.py:310` `_admin` (404), `peakcut/studio/server.py:633` `_throttle(key, limit, window, msg)` (429) | Ready to reuse. |
| Settings routes | `peakcut/studio/server.py:1324` `_tr_saved()` (file-over-env merge, tolerates junk JSON, `.with_suffix(".tmp")` then `replace`), `:1343` `_tr_public()`, `:1350/1356/1399/1418` GET/PUT/models/test | The template for a `/api/meme` block. |
| Per-clip re-render | `peakcut/studio/server.py:939` `rerender` → `jobs.request_render` (`peakcut/studio/jobs.py:345`), 409 when busy, `_throttle("render:"+uid,20,600)`, `ValueError/TypeError` → `HTTPException(400)` | Accepts only `captions`, `start`, `end`, `hook`, `title`, `description`, `style`, `layout` (`peakcut/studio/jobs.py:349-367`). No meme key. |
| Job options | `peakcut/studio/jobs.py:110` `DEFAULTS`, `:114` `LIMITS`, `:117-142` `clean_options` (bool `captions` special-cased; unknown keys silently dropped; every other non-`style`/`layout` key falls to `float(v)` and raises on nonsense) | A new `meme` key **must** get its own branch, or `float("shock")` raises `ValueError`. |
| Clip construction | `peakcut/studio/jobs.py:756-766` `c.update(id=…, style=o["style"], layout=o["layout"], captions=o.get("captions", True), …)`; creator defaults `peakcut/studio/creators.py:17-23` | No meme field on the clip, no creator default. |
| Render entry | `peakcut/studio/jobs.py:373` `render_one(job, clip, words)` — builds `local = dict(clip, start=…, end=…, hook=…)` at `:384`, calls `render.render_clip` at `:386`, then `clip.update(out, status="done", …)` at `:387`; failures funnel to `safe.friendly` at `:399-401` | Exactly one place to hook the post-pass; nothing there today. |
| Audio helpers | `peakcut/studio/media.py:80-88` `run()` (raises `RuntimeError("<tool> failed: …")` / `"… took too long and was stopped."`), `:293` `probe`, `:310` `extract_audio` (16 kHz mono, `first_pts=0`), `:317` `load_audio`, `:323` `loudness_per_second` | `run()` is stricter than `meme.py:19` `run()` (raises instead of returning rc 124) — a good thing, but it means a stalled encoder becomes a clip error, not a silent pass-through. |
| Fonts / assets | `peakcut/studio/render.py:73-78` `install_fonts()` copies bundled `.ttf` into `config.FONTS_DIR` (`config.py:123` = `DATA_DIR/"fonts"`), called once at boot from `peakcut/studio/server.py:66` | The exact pattern for "generate the sounds into `DATA_DIR` at boot". |
| Front end | `peakcut/web/index.html:1862` and `:2169` per-clip `Caption style` / `Layout` selects; `:2003` `setTabs()` (tuple `[id,label,icon,hint]`, admin-gated entries); `:1317` settings route regex; `:847` icon map `I`, `:904` `const ic = n =>` | Needs a mood select in both editor panels, a settings tab, and the regex/icon additions. |
| Status payload | `peakcut/studio/server.py:581-589` `/api/status` publishes `"styles"` and `"layouts"` | Needs `"moods"` so the SPA can populate a select without a second call. |
| Tests | `peakcut/tests/run.py:48-68` — 20 suites, each a standalone script with `check(name, cond)` printing `PASS <name>`; `peakcut/tests/test_captions.py:35-103` shows the pattern (patch `render._render_in`, `ctx.as_user`, `jobs.create(..., enqueue=False)`) | No meme suite. |

**The gap in one sentence:** PeakCut can build a clip with a fixed duration and exactly one audio input, so the
whole of section 2 — a second audio track, a frozen segment, a tail extension, and the transient effect chain —
has no place to live yet.

---

## 4. Port plan

### 4.1 New module: `peakcut/studio/meme.py`

One concern, one file. Audio synthesis and the ffmpeg post-pass both live here, mirroring `render.py`'s role.
It imports **only** `numpy`, `pathlib`, `json`, `tempfile`, `shutil`, `threading`, and
`from . import config` / `from .media import run` — never `jobs` or `server` (no import cycles).

Module constants:

```python
SR: int = 48_000
HOOK_SAFE: float = 3.0
MAX_EXT: float = 3.0
EFFECTS = ("zoom", "punch", "shake", "flash", "vignette", "desat")
DEFAULT_MOODS: dict[str, dict] = { ... }        # the table in §2.4, verbatim
```

### 4.2 Public signatures

```python
# ---- synthesis (deterministic; no I/O beyond writing files) -------------------
def vine_boom() -> "np.ndarray": ...
def sad_trombone() -> "np.ndarray": ...
def record_scratch() -> "np.ndarray": ...
def airhorn() -> "np.ndarray": ...
def bass_drop() -> "np.ndarray": ...
def crickets() -> "np.ndarray": ...
def heartbeat() -> "np.ndarray": ...
def whoosh() -> "np.ndarray": ...
def ding() -> "np.ndarray": ...
def rimshot() -> "np.ndarray": ...
SOUNDS: dict[str, Callable[[], "np.ndarray"]] = {...}

def write_wav(path: Path, x: "np.ndarray") -> None
def make_sounds(dest: Path | None = None) -> list[str]
    # writes the 10 wavs; returns sorted names. Must be atomic: write to
    # "<name>.<pid>.tmp" then os.replace() (the source already does this for beds, meme.py:243-244),
    # and must be guarded by a module-level threading.Lock so two jobs cannot synthesise at once.

def sounds_dir() -> Path
    # config.DATA_DIR / "meme"      (created on demand)
def ensure_sounds() -> Path
    # synthesise any missing wav into sounds_dir() under the lock; return the dir. Idempotent, cheap after the
    # first call (builds a set of existing names). Never re-synthesises an existing file.

# ---- mood table --------------------------------------------------------------
def _file() -> Path                       # config.DATA_DIR / "meme.json"
def load_moods() -> dict[str, dict]       # saved moods merged over DEFAULT_MOODS, always including all 9 keys
def save_moods(data: dict) -> dict[str, dict]
    # validates and writes atomically (.with_suffix(".tmp") then replace) under a threading.Lock;
    # raises ValueError on nonsense so the route can answer 400.
def public() -> dict                      # never leaks a path: {"moods": {name: {sound: [names], effect: [...],
                                          #   volume, offset, hold, tail}}, "effects": [...], "sounds": [names
                                          #   present on disk], "ready": bool}
def labels() -> dict[str, str]            # {"shock": "Shock", ...} for /api/status and the SPA select

# ---- the gag ----------------------------------------------------------------
@dataclass(frozen=True)
class Plan:
    mood: str
    at: float          # T, seconds into the input
    sound: Path
    sound_len: float   # L
    hold: float
    tail: float
    total: float       # dur + hold + tail
    video: str         # filter_complex fragment, ends in the label [vo]
    audio: str         # filter_complex fragment, ends in the label [ao2]
    volume_db: float

def find_payoff(src: Path, dur: float) -> float
def resolve_sound(spec: str | list[str], root: Path | None = None) -> Path
    # raises ValueError("no sound found for ...") instead of SystemExit
def plan(src: Path, dur: float, mood: str, at: float | None = None,
         moods: dict[str, dict] | None = None) -> Plan
    # pure apart from ffprobe on the sound; builds both filter strings from §2.8/§2.9
def apply(src: Path, out: Path, mood: str, at: float | None = None,
          moods: dict[str, dict] | None = None, work: Path | None = None) -> dict
    # runs ffmpeg, returns {"at": float, "sound": str, "hold": float, "tail": float, "duration": float}
def cover(src: Path, at: float, out: Path) -> None
    # one-frame jpg at `at` (the existing render.py:316-318 cover call, re-shot after the gag)
```

`plan()` and `apply()` must both refuse, with `ValueError`, when `dur < HOOK_SAFE + 0.4` (see §6.1). `apply()`
writes into `work` (default: a `tempfile.mkdtemp(prefix="meme")` that it deletes in a `finally`), never into
`src`, and `os.replace`s onto `out` only after ffmpeg succeeded. All ffmpeg calls go through
`peakcut/studio/media.py:80` `run(cmd, cwd=work, timeout=...)` so a frozen encoder raises
`RuntimeError("ffmpeg took too long and was stopped.")` and the clip lands in `status="error"` like any other
render failure.

### 4.3 Pipeline wiring — exact call sites

1. **`peakcut/studio/jobs.py:110` `DEFAULTS`** — add `"meme": ""`.
2. **`peakcut/studio/jobs.py:117-142` `clean_options`** — add a branch **before** the `else`:
   ```python
   elif k == "meme":
       v = v if v in meme.DEFAULT_MOODS else ""
   ```
   (`meme_at` is not a job option; it is per clip, see 4.) Without this branch `float("shock")` raises
   `ValueError: could not convert string to float`, which would reject every job that sets a mood.
3. **`peakcut/studio/jobs.py:756-766`** — in the `c.update(...)`, add `meme=o.get("meme", "")`. No `meme_at`
   at creation: it is chosen at render time by `find_payoff`.
4. **`peakcut/studio/jobs.py:373` `render_one`** — between the `render.render_clip(...)` call at `:386` and the
   `clip.update(out, status="done", ...)` at `:387`:
   ```python
   if clip.get("meme"):
       title = Path(out["file"])
       gag = meme.apply(d / "clips" / title, d / "clips" / title, clip["meme"],
                        at=clip.get("meme_at"), work=...)
       clip["meme_result"] = gag                       # at / hold / tail / duration
       meme.cover(d / "clips" / title, min(1.2, (clip["end"] - clip["start"]) / 2), d / "clips" / Path(out["cover"]))
   ```
   If `meme.apply` raises, **keep the ungagged clip**: catch, record `clip["meme_error"] = safe.friendly(e, 200)`
   and carry on to `status="done"`. A comedy sound is never worth losing a clip over (this is the "degrade to
   today's behaviour" rule from `peakcut/docs/GTA6-PORT-BRIEF.md`).
5. **`peakcut/studio/jobs.py:345` `request_render`** — add `"meme"` to the string loop at `:361`
   (`for k in ("hook", "title", "description", "style", "layout", "meme")`) and validate
   `if new.get("meme") not in meme.DEFAULT_MOODS: new["meme"] = ""` next to the `style`/`layout` checks at
   `:364-367`. Also accept `meme_at`: `if "meme_at" in changes: new["meme_at"] = float(changes["meme_at"]) | None`.
6. **`peakcut/studio/creators.py:17-23` `DEFAULTS`** — add `"meme": ""` so a creator can pick a house mood.
   `_clean` (`peakcut/studio/creators.py:56`) already iterates the `DEFAULTS` keys; `meme` needs the same
   `if k == "meme"` guard as `captions` because the generic path calls `float`-ish coercion.
7. **`peakcut/studio/server.py:589` `/api/status`** — add `"moods": meme.labels()`.
8. **New routes**, immediately after the transcription block (`peakcut/studio/server.py:1440`), following
   `peakcut/studio/server.py:1324-1347` for the file-over-default merge and `:1356` for the PUT shape:
   ```python
   @app.get("/api/meme")          # _admin(request) -> meme.public()
   @app.put("/api/meme")          # _admin, body: {"moods": {name: {...}}}; ValueError/TypeError -> HTTPException(400);
                                  # ctx.bump(); return meme.public()
   @app.post("/api/meme/sounds")  # _admin, _throttle("memesounds:"+ctx.uid(), 6, 600);
                                  # meme.ensure_sounds() with force=False -> {"sounds": [...], "dir_hint": n}
   @app.post("/api/meme/preview") # _admin, _throttle("memepreview:"+ctx.uid(), 10, 600);
                                  # body {"mood": str}; renders a 3 s 360x640 testsrc2 fixture through meme.apply
                                  # and returns it as FileResponse("video/mp4") so a mood can be auditioned.
                                  # 502 + safe.friendly on RuntimeError, 400 on unknown mood.
   ```
   `/api/meme/preview` is the multi-user analogue of `meme.py`'s contact sheet: it lets the admin hear a mood
   without making a clip. It must write into `config.TMP_DIR` and delete afterwards.
9. **`peakcut/studio/server.py:66`** — call `meme.ensure_sounds()` next to `render.install_fonts()`, wrapped in
   `try/except Exception` with a printed warning: a missing sound set must not stop the server booting.

### 4.4 Front end (`peakcut/web/index.html`)

* `:1317` route regex → `(ai|profile|security|apps|storage|transcribe|meme)`.
* `:2003` `setTabs()` → add `["meme", "Meme sounds", "bell", "Comedy sounds and their visual gag"]` inside the
  existing `S.status.user?.is_admin` spread. The `bell` icon already exists in `I` at `:893`; `ic("bell")`
  will resolve without touching the icon map.
* `:2026` `drawSettings()` → a `case "meme"` panel: one row per mood (name, sound select limited to the ten
  names, effect checkboxes for the six effects, volume/offset/hold/tail number inputs), a **Preview** button
  posting to `/api/meme/preview` and playing the response in an `<audio>`/`<video>`, and a **Save** button
  PUTting the whole table. Follow the existing `trHints()` (`:2019`) shape for the live-update helper.
* `:1862` and `:2169` → a `Mood` select next to `Caption style`:
  `<label class="f">Meme<select data-k="meme">${opts(S.status.moods, c.meme || "", "None")}</select></label>`
  (the second, in the clip editor, uses `data-f="meme"`). It must **not** carry `data-caption-style` — a mood
  works with captions off, which is why it is a separate control.
* Playing back a gagged clip: the mp4 is now up to 3 s longer than `end - start`. Where the SPA prints a
  duration, prefer `c.meme_result?.duration ?? (c.end - c.start)`.

### 4.5 Order of work

1. `peakcut/studio/meme.py` synthesis half (`SOUNDS`, `make_sounds`, `ensure_sounds`) + its unit test.
2. `find_payoff`, `plan`, `apply`, `cover` + the render test on a synthetic fixture.
3. `jobs.py` wiring (steps 1-5) and creator default (6).
4. `server.py` settings + status + preview (7-9).
5. SPA (4.4).
6. `peakcut/tests/test_meme.py` registered in `peakcut/tests/run.py:48-68`.

---

## 5. Data files

### 5.1 `DATA_DIR/meme.json` — the mood table (optional; created on first Save)

`config.DATA_DIR` (`peakcut/studio/config.py:119`) — the same folder as `ai.json`, so it follows
`PEAKCUT_DATA` and is never inside the install tree.

```json
{
  "moods": {
    "<mood>": {
      "sound":   ["sad_trombone"] | "sad_trombone",
      "effect":  ["zoom", "vignette", "desat"],
      "volume":  -3,
      "offset":  0.0,
      "hold":    1.2,
      "tail":    "auto" | 0.4
    }
  }
}
```

Validation rules for `save_moods` (raise `ValueError`, message shown to the admin as a 400):

| field | rule |
|---|---|
| key | must be one of the nine names; unknown keys are ignored, the nine are always present (defaults fill gaps) |
| `sound` | str or list of str; each `^[A-Za-z0-9_./-]{1,60}$`; a name may resolve to nothing, then the mood is silent-but-visual (do not raise) |
| `effect` | list, filtered to `EFFECTS`; unknowns dropped, order preserved |
| `volume` | float, clamped `[-30, 6]` |
| `offset` | float, clamped `[-1.0, 1.0]` |
| `hold` | float, clamped `[0.0, 2.0]` |
| `tail` | `"auto"` or float clamped `[0.0, 3.0]`; effective tail is additionally capped by `MAX_EXT - hold` |

The file is read on every `load_moods()` call (cheap JSON), with an `st_mtime_ns` cache exactly as
`peakcut/studio/ai.py:47-60` does, so a hand-edited file is picked up without a restart. Writes happen under
`threading.Lock` to `.with_suffix(".tmp")` then `replace` (`peakcut/studio/server.py:1378-1386` pattern), so a
crash mid-write cannot leave a half-written table.

### 5.2 `DATA_DIR/meme/` — the generated sounds

```
DATA_DIR/meme/vine_boom.wav  sad_trombone.wav  record_scratch.wav  airhorn.wav  bass_drop.wav
              crickets.wav   heartbeat.wav     whoosh.wav          ding.wav     rimshot.wav
DATA_DIR/meme/mine/<name>.<wav|m4a|mp3>        # optional, admin-supplied
```

* Generated by `ensure_sounds()` on first boot; each file is mono 16-bit 48 kHz (`meme.py:110-112`), about
  1.6 MB for the set. Regeneration is deterministic, so a corrupt file can simply be deleted.
* `DATA_DIR` rather than `peakcut/studio/fonts/` because the data folder is writable and survives a reinstall —
  the same argument that put fonts in `config.FONTS_DIR` (`peakcut/studio/config.py:123`).
* `mine/` is looked up first (`resolve_sound`, §2.5) but **is not populated by the port**: `meme.py:205-214`
  `add()` downloads from a URL with `yt_dlp`, which a multi-user server must not do on demand (SSRF and
  copyright). An admin may drop files into `mine/` by hand; the UI only lists what is on disk.
* The ten `gta6-clipper-main/sounds/*.wav` files may be copied in as a fixture for tests, but production must
  synthesise them — a repo file is not guaranteed to match the code after an edit.

### 5.3 No other asset

No fonts, no JSON on the render path, no changes to `peakcut/requirements.txt` (`numpy`, `soundfile` are already
dependencies; `wave` is stdlib).

---

## 6. Risks

**6.1 The hook clamp can invert on short clips.** `peakcut/studio/jobs.py:359` allows clips from 3 s
(`request_render`) and `LIMITS["min_len"]` is `(5, 120)` at `peakcut/studio/jobs.py:114`, so `dur` can be 5 s.
`meme.py:155` does `T = min(max(T, HOOK_SAFE), dur - 0.4)` — for `dur = 3.0` that yields **2.6 s, inside the
hook**, and for `dur < 3.4` the two clamps fight. A naive port therefore breaks the source's own promise
("never touches the first 3 s") on exactly the clips PeakCut is most likely to cut. **Fix:** refuse when
`dur < HOOK_SAFE + 0.4` (3.4 s) with a clear `ValueError`, and treat a clip that is too short as "no gag"
rather than an error (§4.3 step 4 keeps the clip).

**6.2 `SystemExit` in a worker thread.** `meme.py:141`, `:187`, `:256` raise `SystemExit`. In the source that
ends one CLI run; inside `ThreadPoolExecutor` (`peakcut/studio/jobs.py:663`) it escapes `render_one`'s
`except Exception` (`peakcut/studio/jobs.py:399` — `SystemExit` is a `BaseException`) and kills the worker
silently, leaving the clip stuck at `status="rendering"` forever. Every failure path must raise
`ValueError`/`RuntimeError`.

**6.3 Temp-dir leak.** `meme.py:184` `Path(tempfile.mkdtemp(prefix="meme_")) / "g.txt"` is never removed. On a
multi-user server with thousands of clips that is an unbounded directory pile in `%TEMP%`. Use the existing
`render.py:282-286` pattern: `mkdtemp` + `try/finally: shutil.rmtree(work, ignore_errors=True)`, or
`config.TMP_DIR`.

**6.4 Global `SND` monkeypatch is not thread-safe.** `meme.py:266-267` reassigns the module-global `SND` in
`selftest`. Two bits of it must not survive: pass `root=` through `resolve_sound`/`ensure_sounds` instead of
mutating state, and put a lock around `make_sounds()` — two clips rendering at once on a fresh install would
otherwise both write `vine_boom.wav` and one could read a truncated file.

**6.5 Double loudness normalisation.** `render.py:297` already applies `loudnorm=I=-14:TP=-1.5:LRA=11`; the gag
pass applies `loudnorm=I=-14:TP=-1.5:LRA=9` (`meme.py:183`). Chaining them is safe (the second pass mostly
no-ops) but the LRA target differs; use `LRA=9` on the gag pass to match the source, and accept that the
integral loudness of a gagged clip can drift up to ±0.5 LU from a plain one. The `-17 < i < -11` assertion in
§7 covers it.

**6.6 Generation loss and duration drift.** The gag is a second encode (`crf 18 fast` on top of `crf 21
veryfast`), and the clip becomes `+hold+tail` seconds longer (≤ 3 s). Consequences: (a) `clip["end"] -
clip["start"]` no longer equals the file duration, which the SPA and any posting code may assume — store
`clip["meme_result"]["duration"]` and prefer it; (b) disk usage per clip rises ~5 %; (c) a clip that already sat
close to `CLIP_MINUTES` (`peakcut/studio/jobs.py:423`) now needs the extra encode, so a slow machine can newly
time out — `meme.apply` should use a `timeout` of ~120 s, not `media.run`'s default 3600.

**6.7 Frame geometry.** `scale` + `crop` with `eval=frame` at 1080×1920: with `zoom` (1.14) or `punch` (1.12)
there is margin for `dx`/`dy`, but with `shake` alone `Z = 1.05` gives only ±27 px of margin against
`dx = 20`, leaving a visible edge for a couple of frames if the input is exactly 1080 wide and anything else
scales slightly differently. The source tolerates this because gameplay footage is 360 wide and the flash
covers it. **Fix in the port:** clamp the crop offset,
`crop=1080:1920:'max(0,min(iw-1080,(iw-1080)/2+dx))':'max(0,min(ih-1920,(ih-1920)*0.4+dy))'`, and bump the
`shake` zoom to `0.07` so the margin is at least 37 px.

**6.8 Freeze silences speech.** `anullsrc` during `hold` (`meme.py:178`) cuts the clip's own audio dead for up
to 1.2 s. On a gaming clip that is the joke; on an interview-style clip it sounds like a broken file. Ship the
mood defaults as in §2.4 but leave `hold` editable in the settings table (§5.1) and default the feature to
**no mood** on every clip, so existing behaviour is untouched.

**6.9 Re-decoding for `find_payoff`.** `meme.py:146` decodes the whole file to 16 kHz PCM just to find the
loudest 100 ms. PeakCut already has the loudness profile of the source in memory at pick time
(`peakcut/studio/media.py:323` `loudness_per_second`) and the job keeps `words`. The first version may port
`find_payoff` verbatim (it is only ~0.1 s of CPU for a 60 s clip); if compile time matters later, compute `at`
in `render_one` from that array instead and pass it as `meme_at`. Do not block the port on this.

**6.10 Multi-user specifics.** The mood table is global (one admin, one house style) — that is correct for this
feature and mirrors how `render.STYLES` is global. The sounds are global and synthesis is deterministic, so
there is nothing per-user to isolate. The one thing that must **not** be ported is `meme.py:205-214` `add()`
(URL download) and `meme.py:247-258` `bed()` (music beds are feature 07, and `-stream_loop -1` on a
user-supplied file is a separate licence question). Files written by `apply` must stay inside
`job["dir"]/"clips"` (`peakcut/studio/jobs.py:386`), which is already per-user.

---

## 7. Verification

**Unit — synthesis and planning, no server needed:**

```bash
cd peakcut && python -c "
import numpy as np, tempfile, pathlib
from studio import meme
d = pathlib.Path(tempfile.mkdtemp()); meme.make_sounds(d)
for n, f in meme.SOUNDS.items():
    x = f(); assert 0.3 < len(x)/meme.SR < 4, n; assert 0.3 < np.abs(x).max() <= 1, n; assert not np.isnan(x).any(), n
f = meme.vine_boom(); sp = np.fft.rfftfreq(len(f), 1/meme.SR)[np.abs(np.fft.rfft(f)).argmax()]; assert sp < 150, sp
f = meme.crickets(); sp = np.fft.rfftfreq(len(f), 1/meme.SR)[np.abs(np.fft.rfft(f)).argmax()]; assert 3500 < sp < 5200, sp
p = meme.plan(pathlib.Path('x.mp4'), 20.0, 'cringe'); assert abs(p.total - (20 + 1.0 + 0.4)) < 1e-6
print('meme synthesis ok')
"
```

**Render — the nine moods end to end (this is the test to add as `peakcut/tests/test_meme.py`, modelled on
`peakcut/tests/test_captions.py:35-103`, using `check(name, condition)`):**

```bash
cd peakcut && python tests/test_meme.py
```

which must assert, on a fixture built with
`ffmpeg -f lavfi -i testsrc2=s=360x640:r=30:d=10 -f lavfi -i sine=f=300:d=10 -af volume=0.3 -shortest -pix_fmt yuv420p`:

* for each of the nine moods at `at=5.0`: `media.probe(out)` returns `(360, 640)` and
  `abs(duration - plan.total) < 0.15`, and `10 <= duration <= 13.1`;
* integral loudness (`ffmpeg -af ebur128`) is in `(-17, -11)` for every mood;
* `meme.plan(fixture, 10.0, "shock", at=0.5).at >= 3.0` — the hook is protected;
* `hold + tail <= 3.0` for all nine;
* a 3 s fixture raises `ValueError` (not `SystemExit`) and `jobs.render_one` still finishes the clip with
  `status="done"` and `clip["meme_error"]` set (§4.3 step 4);
* the filter strings for `cringe` contain `fade=t=in:st=0:d=0.22:color=white`, `eq=saturation=0.25`,
  `tpad=stop_mode=clone:stop_duration=1.000` and `adelay=5000|5000` — a cheap regression guard on §2.8/§2.9;
* picture is otherwise untouched: with `moods={"<none>": ...}`/no mood, the output md5 equals the ungagged
  render, proving the feature is off by default.

**Settings round-trip (in the same suite):** PUT `/api/meme` with `{"moods": {"cringe": {"volume": -99}}}`
returns `volume == -30` (clamped), a non-admin gets 404, an unknown mood name is ignored, and
`DATA_DIR/meme.json` exists afterwards.

**Whole suite, unchanged behaviour:**

```bash
cd peakcut && python tests/run.py
```
must stay green — in particular `tests/test_transcribe_logfare.py`, the 20 existing suites, and a job submitted
with no `meme` option must render byte-identical to today.
