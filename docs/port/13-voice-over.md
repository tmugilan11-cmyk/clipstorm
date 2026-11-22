# 13 — Voice-over (the user's own line, game ducked under it)

Source: `gta6-clipper-main/voice.py` (18 lines). Everything below is self-contained; there is no need to reopen the file.

## 1. What it does

The user records one short line about the moment, on a phone or a mic, in any audio format. They hand PeakCut that file plus the second in the clip where the line should start, and the clip is made again with the voice sitting on top of the game audio. While the user is talking the game audio automatically drops out of the way and then swells back, so the line is always intelligible without the user mixing anything. The video image is not touched by this feature at all — only the audio bed changes.

This is a *transformation* in the platform sense: the user's own commentary is what makes the clip theirs.

## 2. Exact mechanics

### 2.1 The whole feature is one ffmpeg filter graph

`voice.py` does no analysis, no probing, no normalisation pass of its own. It converts the start time to milliseconds, builds one `filter_complex` string, and calls ffmpeg once.

`voice.py:7`:

```python
ms = int(float(at) * 1000)
```

`at` is a decimal string from argv; `float()` then `int()` **truncates** toward zero. `"2.94"` becomes `2940` ms; `"2.999"` becomes `2999` ms (not 3000). The original never validates `at`, so `at="-3"` produces `adelay=-3000|‑3000` and ffmpeg fails. The port must validate (see §4.4).

### 2.2 The filter graph, verbatim

`voice.py:8-12` is a single f-string. Reproduced exactly, split into its five chained fragments for readability — the real string is these joined by `;` with no newlines:

```
[1:a]loudnorm=I=-16:TP=-1.5,aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms},apad,asplit=2[v][sc];
[0:a]aresample=48000,aformat=channel_layouts=stereo[g];
[g][sc]sidechaincompress=threshold=0.015:ratio=20:attack=15:release=400:makeup=1[duck];
[duck][v]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]
```

Input index `0` is the finished clip, index `1` is the user's recorded line.

Fragment by fragment:

| # | Line | What it does |
|---|---|---|
| 1 | `[1:a]loudnorm=I=-16:TP=-1.5` | Brings the user's line to −16 LUFS, true peak −1.5 dBTP. Single pass (not `loudnorm` two-pass), so it is approximate. **Load-bearing**: the sidechain detector in fragment 3 is level-dependent, and an un-normalised phone recording can be 20 dB too quiet to trigger any duck at all (see §2.5). |
| 2 | `,aresample=48000,aformat=channel_layouts=stereo` | Up/down-samples to 48 kHz and forces stereo, so `adelay`'s per-channel syntax is well-defined and the two streams can be mixed. |
| 3 | `,adelay={ms}\|{ms}` | Delays **each channel** by the same `ms`. The `\|` form takes one value per channel; `{ms}\|{ms}` is the two-channel spelling. Equivalent after fragment 2 to `adelay=delays={ms}:all=1`. |
| 4 | `,apad` | Pads the voice with silence **forever**. Not cosmetic — see §2.3. |
| 5 | `,asplit=2[v][sc]` | The same normalised, delayed, padded voice is used twice: once as programme material (`[v]`) and once as the compressor's key input (`[sc]`). |
| 6 | `[0:a]aresample=48000,aformat=channel_layouts=stereo[g]` | The game audio, resampled and stereo-ised, **not** normalised here. |
| 7 | `[g][sc]sidechaincompress=threshold=0.015:ratio=20:attack=15:release=400:makeup=1[duck]` | Game in, voice as key. The game is reduced whenever the key is above `threshold`. Full parameter table in §2.4. |
| 8 | `[duck][v]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]` | Sums ducked game + voice at unity (`normalize=0` — without it ffmpeg halves both). `duration=first` = the ducked game's length. Then a hard limiter at 0.95 linear = **−0.45 dBFS**. |

`voice.py:10` carries the only explanatory comment in the file:

```python
# sidechain: the game drops about 15 dB only while you talk, returns over 0.4 s
```

**Discrepancy to preserve in the port:** the comment says *15 dB*, `SKILL-REFERENCE.md:78-83` and `docs/GTA6-PORT-BRIEF.md:69` both say *18 dB*, and the code contains **no 15 and no 18 anywhere** — the depth is an emergent property of a compressor. See §2.5 for what it actually measures.

### 2.3 `apad` is mandatory, and why

`sidechaincompress` ends when its **key** input ends. The user's line is always shorter than the clip, so without `apad` the whole mix is truncated at the end of the voice.

Measured on ffmpeg 9.0.2 with a 6.0 s game bed and a 2.0 s voice started at 2.0 s:

| Graph | Output duration |
|---|---|
| with `apad` | **6.000000 s** |
| without `apad` | **4.000000 s** |

4.0 s = voice end (2.0 s delay + 2.0 s tone) — the game bed is simply gone after that. A port that drops `apad` to "clean up" the graph ships clips with chopped audio.

### 2.4 `sidechaincompress` parameter table

| Parameter | Value | Meaning |
|---|---|---|
| `threshold` | `0.015` linear | `20*log10(0.015)` = **−36.478 dBFS**. The key must exceed this before any reduction happens. |
| `ratio` | `20` | Slope above threshold = `1 − 1/20` = **0.95**. So reduction ≈ `0.95 × (key_dB − (−36.478))`. |
| `attack` | `15` ms | Reduction onset. Measured: 0 dB at t−0.01 s, −8.9 dB at voice onset, −15.6 dB 20 ms later, settled by ~40 ms. Effectively click-free and immediate. |
| `release` | `400` ms | Recovery. Measured at voice-off: −16.0 dB → −13.7 (50 ms) → −11.7 (100 ms) → −9.6 (150 ms) → −7.6 (200 ms) → −5.5 (250 ms) → −3.5 (300 ms) → −1.9 (350 ms) → −0.75 (400 ms) → −0.14 (450 ms) → **0 dB at 500 ms**. The real recovery is ~0.45–0.50 s, slightly longer than the nominal 400 ms. |
| `makeup` | `1` | Unity makeup gain — no post-reduction boost. Changing this to `0` or `2` silently changes the whole balance. |
| `level_sc` | *(absent)* | Defaults to 1. If set, the key is attenuated before detection and the duck depth collapses. Do not add it. |

### 2.5 How deep the duck actually goes (measured, not documented)

Depth is **not** a constant. It is `0.95 × (key level above −36.478 dBFS)`, and the key is the loudnorm'd voice. Sweep of a steady 3 kHz probe as the key, measuring the drop in the game bed's own band:

| Voice (key) RMS | Measured game drop |
|---|---|
| −24.0 dBFS | 0.00 dB |
| −20.0 dBFS | 0.00 dB |
| −17.0 dBFS | 0.29 dB |
| −14.0 dBFS | 1.52 dB |
| −10.0 dBFS | 4.62 dB |
| −6.0 dBFS | 8.41 dB |
| −3.0 dBFS | 11.26 dB |

With a proper `loudnorm=I=-16` voice, the same graph measures:

| Voice | Measured steady duck |
|---|---|
| `loudnorm=I=-16` steady tone | **16.01 dB** (game −37.64 → −53.65 dBFS) |
| `loudnorm=I=-16` speech-like, level-modulated | uneven per-frame, peaks ~16 dB, dips to ~1 dB on syllable gaps |

So: **the shipped graph gives ~16 dB, the comment says 15, the docs say 18.** Calibration formula the port should use, derived from the same measurement and validated against it:

```
slope      = 1 - 1/ratio                       # 0.95 at ratio 20
excess     = duck_db / slope                   # dB the key must sit above threshold
threshold  = 10 ** ((voice_db - excess) / 20)  # linear, matches sidechaincompress
```

Check: `voice_db = −19.6`, `duck_db = 18` → `excess = 18.95` → `threshold = 10^(−1.9275) = 0.01184`. Predicted depth `0.95 × 18.95 = 18.0` ✓. And the shipped `0.015` with that same voice predicts `0.95 × (−19.6 + 36.478) = 16.03 dB` — exactly the 16.01 dB measured. The formula is trustworthy; use it, clamp the result (see §4.3).

### 2.6 The ffmpeg invocation

`voice.py:13-14`, verbatim:

```python
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", clip, "-i", line,
                "-filter_complex", graph, "-map", "0:v", "-map", "[a]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", out], check=True)
print("ok", out)
```

Load-bearing details:

- **`-i clip` before `-i line`.** The graph hardcodes index 0 = clip, index 1 = voice. Reordering the arguments silently swaps game and commentary.
- **`-c:v copy`** — the video bitstream is not re-encoded. This only works because the input is an already-finished encode. It is why the feature is described as "over a finished Short".
- **`-map 0:v -map [a]`** — the original audio track is *not* mapped; only the mixed output is. There is exactly one audio stream in the result.
- **no `-shortest`** — length comes from `apad` + `duration=first`.
- **`-y`** — always overwrites. In a server this is a bug, not a feature (§6).
- **`-loglevel error`** plus `check=True`: failure surfaces as `CalledProcessError`, and because `-loglevel error` suppresses everything else, the message is usually just the exit code — no diagnosis.
- **`print("ok", out)`** is the entire user feedback.

`voice.py:17-18` is `main(*sys.argv[1:5])` — exactly four positional arguments, no flags, no `--help`, no defaults.

## 3. PeakCut today

### 3.1 What exists that this feature touches

| Where | What it is | Overlap |
|---|---|---|
| `peakcut/studio/render.py:289-321` (`_render_in`) | the single ffmpeg invocation that produces a clip | this is where the mix must happen |
| `peakcut/studio/render.py:296-298` | the argv `base` list | already maps one audio stream and applies one audio filter |
| `peakcut/studio/render.py:235-252` (`_filter`) | `[0:v]` → `[v0]` visual chain | untouched by voice-over; it establishes that the code composes filter fragments by string concatenation |
| `peakcut/studio/render.py:267-286` (`render_clip`) | writes `<name>.mp4`, `<name>.jpg`, `<name>.ass` | its return dict (`{"file","cover","layout"}`) is what `jobs.render_one` merges into the clip |
| `peakcut/studio/jobs.py:345-371` (`request_render`) | the re-make parameter validator | the natural home for `at` / `duck` / `off` |
| `peakcut/studio/jobs.py:373-402` (`render_one`) | builds `local = dict(clip, ...)` and calls `render_clip` | the clip dict already carries every render parameter, so a `voice` key flows through for free |
| `peakcut/studio/jobs.py:149` / `:152-167` (`HIDDEN`, `public`) | strips private keys from the API view | a new clip key must be checked against this |
| `peakcut/studio/server.py:939-950` | `POST /api/jobs/{jid}/clips/{cid}/render` | guards + throttle the port should reuse |
| `peakcut/studio/server.py:749` (`POST /api/upload`) | multipart streaming upload, 4 MB chunks into `config.TMP_DIR/"uploads"`, then `shutil.move` | the template for accepting the voice file |
| `peakcut/studio/media.py:80-90` (`run`) | subprocess wrapper with `NO_WINDOW`, timeout, `RuntimeError("<binary> failed: <stderr tail>")` | the voice probe must use this, not bare `subprocess` |
| `peakcut/studio/media.py:293-318` (`probe`) | ffprobe wrapper returning `{"width","height","duration"}` | reference for how a probe parses ffmpeg output |
| `peakcut/studio/config.py:119-123` | `DATA_DIR`, `TMP_DIR`, `USERS_DIR`, `MODELS_DIR`, `FONTS_DIR` | `TMP_DIR` for the upload staging file |
| `peakcut/studio/account.py:35-40` | `delete_clip` unlinks `clips/<file>`, `clips/<cover>` and the `{stem}.ass` / `{stem}.json` sidecars | **must learn about the voice file or it is orphaned** |

### 3.2 The gap, concretely

1. **No mixing code exists.** A grep of `peakcut/studio/*.py` for `amix|sidechaincompress|adelay|apad` returns one unrelated hit: `peakcut/studio/brain.py:419`, prompt prose ("Ignore steady background noise or music that is loud the whole time."). There is no filter-graph mixing anywhere in the server.
2. **The render takes exactly one audio input.** `peakcut/studio/render.py:297` is `"-map", "0:a:0", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11"`. One stream in, one filter, one stream out. A second input and a graph are structurally impossible without editing that argv.
3. **`-af` and `-filter_complex` cannot both own the audio.** `-af` is a shorthand for a filter chain on the mapped stream; once the audio is produced by `[a]` from `filter_complex`, the `-af` pair must be deleted, and the game's `loudnorm=I=-14` moves into the graph.
4. **The upload route is video-only.** `server.py:749` validates against `VIDEO_TYPES` (`server.py:42` = `.mp4 .mov .mkv .webm .m4v .ts .flv`) and rejects everything else with 400. A `.wav` or a phone `.m4a` cannot get in.
5. **Nothing is clip-timed.** `start`/`end` are *source* times; `render_clip` is handed `local = dict(clip, start=…, end=…)` already rebased by `off` (`jobs.py:373-402`). There is no field anywhere for "an event at second 12 of the finished clip".
6. **No per-clip audio state.** `jobs.HIDDEN` and the `public()` clip-key strip list (`jobs.py:152-167`) know `src`, `fixed_words`, `fixed_for` — a voice attachment has no representation and no cleanup.

## 4. Port plan

### 4.1 New module: `peakcut/studio/voice.py`

Pure and importable without a database. Imports: `math`, `re`, `subprocess`, `pathlib.Path`, `from . import config, media`. It must **not** import `jobs` or `render` (both import `voice`; importing back creates a cycle).

```python
# ---- constants (all from voice.py unless marked "port") -------------------
VOICE_LUFS: float = -16.0          # voice.py:9  loudnorm=I
VOICE_TP: float = -1.5             # voice.py:9  loudnorm=TP
MIX_RATE: int = 48000              # voice.py:9,11
DUCK_THRESHOLD: float = 0.015      # voice.py:11 shipped default (=-36.478 dBFS)
DUCK_RATIO: float = 20.0           # voice.py:11
DUCK_ATTACK_MS: int = 15           # voice.py:11
DUCK_RELEASE_MS: int = 400         # voice.py:11
DUCK_DEFAULT_DB: float = 18.0      # port: the documented depth (SKILL-REFERENCE.md:78-83)
LIMIT: float = 0.95               # voice.py:12
GAME_LUFS: float = -14.0           # port: render.py:297's existing loudnorm
GAME_TP: float = -1.5              # port: render.py:297
GAME_LRA: float = 11.0             # port: render.py:297
THRESHOLD_MIN: float = 0.0005      # port: -66 dBFS floor for the computed threshold
THRESHOLD_MAX: float = 0.20        # port: -14 dBFS ceiling
MAX_AT_PAST_END: float = 0.20      # port: `at` must leave this much clip after it
VOICE_EXTS: tuple[str, ...] = (".wav", ".mp3", ".m4a", ".aac", ".ogg", ".opus",
                               ".flac", ".aiff", ".mp4", ".mov", ".m4v", ".webm")
VOICE_MAX_MB: int = 25             # port
```

```python
def db_to_linear(db: float) -> float: ...
```
Returns `10 ** (db / 20.0)`.

```python
def linear_to_db(x: float) -> float: ...
```
Returns `20.0 * log10(max(x, 1e-12))`. Needed to turn a `sidechaincompress` threshold into a reportable dB value.

```python
def threshold_for(duck_db: float, voice_db: float, ratio: float = DUCK_RATIO) -> float: ...
```
Returns the linear `sidechaincompress` threshold that produces `duck_db` of reduction for a key measured at `voice_db` dBFS:

```python
slope  = 1.0 - 1.0 / ratio            # 0.95
excess = duck_db / slope
return min(THRESHOLD_MAX, max(THRESHOLD_MIN, 10.0 ** ((voice_db - excess) / 20.0)))
```

Raises `ValueError("The duck has to be between 0 and 30 dB.")` when `duck_db` is outside `[0, 30]`, and `ValueError("I couldn't measure how loud your line is.")` when `voice_db` is not finite. Validated against the measured table in §2.5.

```python
def probe_db(path: Path, timeout: int = 120) -> float: ...
```
Runs

```
ffmpeg -hide_banner -nostats -v info -i <path> -map 0:a:0 -af volumedetect -f null -
```

via `subprocess.run(..., capture_output=True, text=True, encoding="utf-8",
errors="replace", creationflags=media.NO_WINDOW, timeout=timeout)`, parses `stderr` with
`re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?) dB", err)`. Returns the float. Raises
`ValueError("That file has no sound in it.")` if the regex misses, or if stderr contains
`"Output file #0 does not contain any stream"` / `"matches no streams"`. Raises
`RuntimeError` with `f"ffmpeg failed: {err[-1500:]}"` on a non-zero exit — mirror
`media.run` (`media.py:80-90`) so error text looks the same everywhere.
Note: `media.run` returns **stdout only**; `volumedetect` writes to stderr, which is why this is
a separate function rather than a `media.run` call.

```python
def clean_spec(raw: object, duration: float, *, default_duck: float = DUCK_DEFAULT_DB) -> dict | None: ...
```
Validates a client-supplied voice spec for a clip of `duration` seconds. Returns `None` when the feature is being switched off (`raw is None`, `raw == {}`, or `raw.get("off")`), otherwise a normalised dict:

```python
{"file": str, "at": float, "duck": float, "db": float}
```

Rules, each with the exact `ValueError` message (the route turns these into 400 via `HTTPException(400, str(e))`):

| Input | Rule | Message |
|---|---|---|
| `raw` not a dict | reject | `"The voice setting is not valid."` |
| `raw["at"]` missing / not a number / `NaN` / `inf` | reject | `"Say what second your line should start on."` |
| `at < 0` | reject | `"Your line can't start before the clip does."` |
| `at > duration - MAX_AT_PAST_END` | reject | `"Your line starts after the clip ends. Pick an earlier second."` |
| `raw["duck"]` missing | `default_duck` | — |
| `duck` outside `[0, 30]` | reject | `"The duck has to be between 0 and 30 dB."` |
| `raw["db"]` (`voice_db`) missing / not finite | reject | `"I couldn't measure how loud your line is."` |
| `raw["file"]` missing / not a bare filename | reject | `"The voice file is missing."` |

The `file` check is `re.fullmatch(r"[\w.\-]{1,120}", name)` and must not contain `/`, `\` or `..` — it is the value that later becomes `out_dir / name`.

```python
def mix_chain(at: float, duck_db: float, voice_db: float, *,
              loudness: float = VOICE_LUFS, true_peak: float = VOICE_TP,
              ratio: float = DUCK_RATIO, attack_ms: int = DUCK_ATTACK_MS,
              release_ms: int = DUCK_RELEASE_MS, limit: float = LIMIT,
              rate: int = MIX_RATE) -> str: ...
```
Returns a filter-graph fragment that takes the game from input `[0:a]`, the voice from input `[1:a]`, and produces `[a]`. **It starts with a leading `;`** — see §4.5. Verbatim shape:

```python
ms = int(at * 1000)
thr = threshold_for(duck_db, voice_db, ratio)
return (
    f";[0:a]aresample={rate},aformat=channel_layouts=stereo,"
    f"loudnorm=I={GAME_LUFS}:TP={GAME_TP}:LRA={GAME_LRA}[gm];"
    f"[1:a]loudnorm=I={loudness}:TP={true_peak},aresample={rate},"
    f"aformat=channel_layouts=stereo,adelay=delays={ms}:all=1,apad,asplit=2[vo][sc];"
    f"[gm][sc]sidechaincompress=threshold={thr:.6f}:ratio={ratio}:"
    f"attack={attack_ms}:release={release_ms}:makeup=1[duck];"
    f"[duck][vo]amix=inputs=2:duration=first:normalize=0,"
    f"alimiter=limit={limit}[a]"
)
```

Differences from `voice.py:8-12` and why:

- `adelay=delays={ms}:all=1` instead of `{ms}|{ms}` — `all=1` cannot under-specify channels if `aformat` ever stops guaranteeing two.
- `threshold={thr:.6f}` instead of the literal `0.015` — so `duck_db` is honoured (`0.015` is what `threshold_for(18, -19.6)` returns to within 25 %, so the default behaves like the original).
- The game's `loudnorm=I=-14:TP=-1.5:LRA=11` moved out of `-af` and into the graph, **before** the ducker. Order matters: normalise, then duck, then mix. Ducking before normalisation lets the normaliser undo the duck.
- Everything else is byte-for-byte the original.

```python
def remove(path: Path) -> None: ...
```
`path.unlink(missing_ok=True)` wrapped in `try/except OSError` — used by the delete paths, mirrors the tolerance in `account.py:35-40`.

### 4.2 `peakcut/studio/render.py` — fuse the mix into the single render pass

**Decision: mix inside `_render_in`, not in a second pass over the finished mp4.** The gta6 version can `-c:v copy` because it post-processes a finished file; PeakCut's clip is produced by a filter graph in one shot, and a second file-writing pass would (a) decode+re-encode video needlessly under `RENDER_SECONDS = 600`, (b) create an intermediate file to clean up per clip, (c) re-run the audio encoder on already-lossy AAC. Fusing costs nothing extra and keeps `render_clip`'s return contract intact.

`render_clip` signature is unchanged:

```python
def render_clip(src: Path, out_dir: Path, name: str, clip: dict, words: list,
                src_w: int, src_h: int) -> dict
```

Inside it, after `geometry` / `_hook_y` / `build_ass` (render.py:267-286), add:

```python
voice_spec = clip.get("voice")
voice_path = None
if isinstance(voice_spec, dict) and voice_spec.get("file"):
    voice_path = Path(out_dir) / str(voice_spec["file"])
    if not voice_path.is_file():
        raise RuntimeError("The voice line for this clip is missing. Record it again.")
```

and pass it as a new keyword-only argument:

```python
def _render_in(work: Path, src: Path, out_dir: Path, name: str, start: float,
               end: float, layout: str, fg_h: int, ass: str,
               face=None, voice: dict | None = None, voice_path: Path | None = None) -> dict
```

Inside `_render_in`, the two changes to `render.py:296-298`:

1. Append the second input **after** the first, keeping the source at index 0:

```python
base = ["ffmpeg", "-y", "-v", "error",
        "-ss", f"{start:.2f}", "-t", f"{end - start:.2f}", "-i", str(src)]
if voice_path is not None:
    base += ["-i", str(voice_path)]
```

2. Move the audio out of `-af` and into the graph, and map `[a]`:

```python
fc = _filter(layout, fg_h, face) + f"[v0]ass={name}.ass:fontsdir=f[v]"
if voice_path is not None:
    fc += voice.mix_chain(float(voice["at"]), float(voice["duck"]), float(voice["db"]))
    base += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]"]
else:
    base += ["-filter_complex", fc, "-map", "[v]", "-map", "0:a:0",
             "-af", "loudnorm=I=-14:TP=-1.5:LRA=11"]
base += ["-c:a", "aac", "-b:a", "160k", "-ar", "48000",
         "-movflags", "+faststart", "-pix_fmt"]
```

The encoder ladder, the `_qsv_ok` memo, the `err = p.stderr[-1200:]` →
`RuntimeError(f"Render failed: {err}")` path, the cover grab at
`cover_t = min(1.2, (end - start) / 2)`, the move of `mp4`/`jpg`/`ass` into `out_dir`,
and the return value `{"file": f"{name}.mp4", "cover": f"{name}.jpg", "layout": layout}`
all stay exactly as they are. **Do not** add `voice` to the returned dict — the clip already
holds it, and `jobs.render_one` merges the dict with `clip.update(out, ...)`.

Keep `-b:a 160k` (not the source's `192k`) so voice clips and normal clips are encoded
identically; the graph already ends in a −0.45 dBFS limiter, so no headroom is lost.

### 4.3 `peakcut/studio/jobs.py` — per-clip state and validation

Add to the top-level imports: `from . import voice`.

New function, placed next to `request_render` (`jobs.py:345`):

```python
def set_voice(jid: str, cid: str, spec: dict) -> dict:
    """Attach a voice line to one clip. The files are already on disk; this only records them."""
```

- `job = get(jid)`; `raise ValueError("No such video")` when `None`.
- `clip = next((c for c in job["clips"] if c["id"] == cid), None)`; `raise ValueError("No such clip")` when `None`.
- `raise Busy("This clip is still being made. Wait for it to finish first.")` when `clip.get("status") in ("queued", "rendering")` — same message and same class as `account.py:30-31`.
- Stores `clip["voice"] = spec` and calls `save(job)` (`jobs.py:169-184`), then returns `public(job)`.
  `save()` already calls `ctx.bump(job.get("user"))`, which is what makes the change appear on the
  user's next `/api/sync` poll — do not add a second bump.

```python
def clear_voice(jid: str, cid: str) -> dict:
    """Take the voice line off a clip and delete its file."""
```

- Same lookup and same `Busy` guard.
- Pops `clip["voice"]`, calls `voice.remove(job_dir(jid) / "clips" / spec["file"])`, `save(job)`, returns `public(job)`.

Extend `request_render` (`jobs.py:345-371`) so a re-make can change the voice in the same
call as the captions. The function in the host builds a working copy `new = dict(clip)`, so the
branch goes **after** the length validation and **before** `clip.update(new, status="queued")`
(`jobs.py:367`), and it must mutate `new`, not `clip`:

```python
    # ... after: if not 3 <= new["end"] - new["start"] <= 180: raise ValueError(...)
    if "voice" in changes:
        span = float(new["end"]) - float(new["start"])          # clip-local seconds
        spec = voice.clean_spec(changes["voice"], span)
        old = (clip.get("voice") or {}).get("file")
        if spec is None:                                        # switched off
            new.pop("voice", None)
        else:                                                   # keep the measured level
            spec["db"] = float((clip.get("voice") or {}).get("db", spec["db"]))
            new["voice"] = spec
        if old and (spec is None or spec["file"] != old):
            voice.remove(Path(job["dir"]) / "clips" / Path(old).name)
```

`new["start"]` / `new["end"]` are the *validated* clip-local values already computed above
(`3 <= end - start <= 180`), so the duration is available without another probe. `Path` is
already imported in `jobs.py`; `job["dir"]` is the job's own folder, the same one
`render_one` uses as `d`.

`render_one` (`jobs.py:373-402`) needs **no change**: `local = dict(clip, start=…, end=…)`
already copies `voice` through to `render_clip`, and `voice["file"]` is a bare filename inside
the same `d/"clips"` directory that `render_clip` receives as `out_dir`, so the path resolves
without any new absolute-path field. That matters because `public()` would otherwise have to
learn about another private key.

`public()` (`jobs.py:152-167`) needs **no change**: `{"file", "at", "duck", "db"}` is all
client-safe (a bare filename, three numbers). Do not put an absolute path in it.
`HIDDEN` (`jobs.py:149`) is unchanged for the same reason.

### 4.4 `peakcut/studio/server.py` — two routes

Placed immediately after the render route (`server.py:939-950`).

```python
@app.post("/api/jobs/{jid}/clips/{cid}/voice")
async def add_voice(request: Request, jid: str, cid: str,
                    file: UploadFile = File(...), at: str = Form(""),
                    duck: str = Form("")) -> dict:
    """Store the user's own line for one clip. The line is mixed in on the next make."""
```

Order of operations — each step mirrors an existing route so behaviour is consistent:

1. `_need_verified()` (`server.py:318-320`) — the same gate `/api/upload` uses.
2. `job = _job_or_404(jid)` (`server.py:593`).
3. `clip` lookup; `raise HTTPException(404, "No such clip")`.
4. `if job["status"] in ("queued", "running") or clip.get("status") in ("queued", "rendering"): raise HTTPException(409, "This clip is still being made. Try again when it has finished.")` — same copy as `server.py:939-950`.
5. `_throttle("voice:" + ctx.uid(), 20, 600, "That's a lot of voice lines in a short time. Wait a few minutes.")` (`server.py:633`).
6. Extension check: `ext = Path(file.filename or "line.wav").suffix.lower()`; `if ext not in voice.VOICE_EXTS: raise HTTPException(400, "Record your line as a wav, mp3 or m4a file.")`.
7. Stream into `config.TMP_DIR / "uploads" / f"{os.urandom(8).hex()}{ext}"` in 4 MB chunks exactly like `server.py:749`, enforcing `voice.VOICE_MAX_MB` → `raise HTTPException(413, f"That recording is bigger than {voice.VOICE_MAX_MB} MB. Record a shorter line.")`. Do not reuse the request-body middleware's limit as the only check — it is `MAX_UPLOAD_MB` scale.
8. Probe before accepting: `db = await run_in_threadpool(voice.probe_db, tmp)`; `ValueError` → `raise HTTPException(400, str(e))`.
9. `dest = Path(job["dir"]) / "clips" / f"{cid}.voice{ext}"`; `if clip.get("voice", {}).get("file") and … != dest.name: voice.remove(old path)`; `shutil.move(str(tmp), dest)`.
10. Build the spec and store it:
    ```python
    dur = float(clip["end"]) - float(clip["start"])
    try:
        spec = voice.clean_spec({"file": dest.name, "at": at or 0.0,
                                 "duck": duck or voice.DUCK_DEFAULT_DB, "db": db}, dur)
        return await run_in_threadpool(jobs.set_voice, jid, cid, spec)
    except (ValueError, TypeError) as e:
        voice.remove(dest)
        raise HTTPException(400, str(e))
    finally:
        Path(tmp).unlink(missing_ok=True)
    ```
    Note `dur` is in **clip-local seconds**, which is exactly the timeline `at` refers to, because the render graph's clock starts at 0 at the first frame (`-ss`/`-t` are input options).

```python
@app.delete("/api/jobs/{jid}/clips/{cid}/voice")
async def drop_voice(request: Request, jid: str, cid: str) -> dict:
    """Take the user's line off a clip."""
```
Same `_need_verified` / `_job_or_404` / 409 guard, then `jobs.clear_voice(jid, cid)`; wrap
`Busy` → `HTTPException(409, str(e))` and `ValueError` → `HTTPException(400, str(e))`.

Nothing else in `server.py` changes. The existing
`POST /api/jobs/{jid}/clips/{cid}/render` route keeps working unmodified: `at`/`duck` are sent
as `{"voice": {...}}` inside the existing `body: dict = Body(...)` and reach
`jobs.request_render` (`server.py:939-950`) without a new parameter.

### 4.5 The one concatenation footgun

`_filter()` (`render.py:235-252`) returns a chain that **ends with the label `[v0]` and no
trailing semicolon**, because `_render_in` appends `f"[v0]ass=…"` directly to it. Therefore
`voice.mix_chain()` must return a fragment that **starts with `;`**. Getting this wrong produces
`[v0]ass=clip.ass:fontsdir=f[v];[0:a]…` (correct) versus
`[v0]ass=clip.ass:fontsdir=f[v][0:a]…` (an unreadable label concatenation and an ffmpeg
"Invalid filterchain" error that surfaces only as `RuntimeError("Render failed: …")`).

### 4.6 `peakcut/studio/account.py` — cleanup

In `delete_clip` (`account.py:22-50`), beside the existing sidecar loop:

```python
v = clip.get("voice") or {}
if v.get("file"):
    (d / "clips" / Path(str(v["file"])).name).unlink(missing_ok=True)
```

Without this, every deleted voice clip leaves a stray upload in the job directory forever —
and `Path(...).name` is not decorative: it makes the unlink impossible to point outside
`clips/` via a crafted filename, the same defensive shape as `account.py:45-46`.

### 4.7 `peakcut/web/index.html` — clip card controls

- In the clip action row (where the existing re-make / delete buttons live) add an
  "Add your voice" button rendering `ic("microphone")` — the icon **already exists** in
  `const I` (`index.html:847-903`), so no new SVG is needed; just confirm the key before use.
- Clicking it opens a small inline panel with `<input type="file" accept="audio/*,video/mp4">`,
  a seconds field pre-filled with `1` (a hook lands inside the first ~2 s; `render.py:112-125`
  puts the hook box at y≈300), and a "Game drops" range slider 6–24 dB defaulting to 18.
- Submits `FormData{file, at, duck}` to `POST /api/jobs/{jid}/clips/{cid}/voice`, then re-renders
  from the returned `jobs.public(job)` payload (same pattern as the existing re-make call).
- The upload stores the spec but does not render. The card then offers "Make it again", which
  calls the **existing** `POST /api/jobs/{jid}/clips/{cid}/render` with an empty body `{}` — no
  `voice` key is needed, because `render_one` copies the whole clip dict into `local`, so the
  stored `voice` reaches `render_clip` on its own.
- Once attached, the card shows "Your line at 1.0 s · game −18 dB" with a remove button that
  calls `DELETE …/voice`.

### 4.8 Call graph, complete

```
POST /api/jobs/{jid}/clips/{cid}/voice
  -> server._need_verified()            (server.py:318)
  -> server._job_or_404()               (server.py:593)
  -> server._throttle()                 (server.py:633)
  -> voice.probe_db()                   (§4.1, subprocess + volumedetect)
  -> voice.clean_spec()                 (§4.1)
  -> jobs.set_voice()                   (§4.3)
       -> jobs.get(), jobs.save()       (jobs.py:169)
       -> jobs.public()                 (jobs.py:152)

POST /api/jobs/{jid}/clips/{cid}/render   (unchanged route)
  -> jobs.request_render()              (jobs.py:345)  [+ voice branch]
  -> jobs._q.put(("clip", jid, cid))    (jobs.py:371)
  -> jobs._worker() -> jobs.render_one() (jobs.py:373)
       -> render.render_clip()          (render.py:267)  [+ reads clip["voice"]]
            -> render._render_in()      (render.py:289)  [+ 2nd -i, -map [a]]
                 -> voice.mix_chain()   (§4.1)
       -> jobs.save()

DELETE /api/jobs/{jid}/clips/{cid}/voice
  -> jobs.clear_voice() -> voice.remove()

account.delete_clip()                   (account.py:22)  [+ unlink voice file]
```

## 5. Data files

### 5.1 Per-clip state — inside `job.json`, no new file

The clip dict (written by `jobs.save`, `jobs.py:169-184`) gains one optional key:

```json
"voice": {
  "file": "a1b2c3d4e5f6.voice.wav",
  "at": 1.0,
  "duck": 18.0,
  "db": -19.6
}
```

| Field | Type | Meaning |
|---|---|---|
| `file` | `str` | bare filename inside `<job dir>/clips/`; `^[\w.\-]{1,120}$`, no path separators. Encoded on disk as `{cid}.voice{ext}` so a re-record replaces rather than accumulates. |
| `at` | `float` | seconds **from the first frame of the finished clip**, `0 <= at <= (end - start) - 0.2`. |
| `duck` | `float` | target reduction in dB, `0 <= duck <= 30`, default `18.0`. |
| `db` | `float` | the measured `mean_volume` of the line in dBFS, captured once at upload by `voice.probe_db`. Stored so a re-render never re-probes and so the graph is deterministic. |

All four values are client-safe, so `jobs.public` (`jobs.py:152-167`) and `jobs.HIDDEN`
(`jobs.py:149`) need no edit.

### 5.2 Audio on disk

`<DATA_DIR>/users/<uid>/<jid>/clips/<cid>.voice.<ext>` — next to `<cid>.mp4`, `<cid>.jpg`,
`<cid>.ass`, `<cid>.json`, and cleaned up by `account.delete_clip` (§4.6). Staged during upload
in `config.TMP_DIR / "uploads"` (`config.py:122`), the same place `server.py:749` stages video.

### 5.3 Server defaults — `voice.json` in `config.DATA_DIR`

Optional but recommended, so an admin can retune the default depth without a deploy. Follows
`ai.py` exactly (module docstring documents the env fallbacks, dashboard file wins):

`<DATA_DIR>/voice.json`, mode `0600`, written `tmp` then `Path.replace` under a `threading.Lock`:

```json
{
  "duck": 18.0,
  "loudness": -16.0,
  "max_mb": 25
}
```

| Field | Type | Bounds | Default | Env fallback |
|---|---|---|---|---|
| `duck` | float | 0–30 | 18.0 | `PEAKCUT_VOICE_DUCK` |
| `loudness` | float | −30 – −8 | −16.0 | `PEAKCUT_VOICE_LUFS` |
| `max_mb` | int | 1–200 | 25 | `PEAKCUT_VOICE_MAX_MB` |

Read through a `current() -> dict` that merges file over env and tolerates a hand-edited file
containing `null`, `[]`, `3` or `"text"` (the defensive shape of `server._tr_saved`,
`server.py:1324-1341`). Exposed read-only at `GET /api/voice` behind `_admin()` with the same
shape as `_tr_public()` (`server.py:1343-1349`) — the settings page needs it, and it contains no
secrets, so `public()` can just return the three numbers plus a computed
`"threshold"` in dBFS for transparency.

If the settings tab is built, add `["voice", "Voice", "microphone", "Your own line over a clip"]`
to `setTabs()` (`index.html:2003-2007`) — admin-only, next to Transcription, using the existing
`microphone` icon. The tab is optional; the JSON file is what the build agent must not skip,
because §2.5 shows the default depth is a real tuning decision.

## 6. Risks

1. **`-af` and `-filter_complex` both claiming the audio.** The single most likely naive-port
   failure: adding the graph while leaving `render.py:297`'s `"-af", "loudnorm=…"` in place.
   ffmpeg rejects it (`Filtergraph 'loudnorm' was specified through the -vf/-af/-filter option
   and the filtergraph options`), and the error arrives as `RuntimeError("Render failed: …")`
   only after the whole clip has been decoded. Delete the `-af` pair, always.
2. **Dropping `apad`.** Measured in §2.3: output truncates to the length of the voice
   (6.0 s → 4.0 s). A reviewer "simplifying" the graph will silently ship clipped audio, and
   nothing in the render asserts the output duration.
3. **Swapping the input order.** The graph hardcodes `[0:a]` = game, `[1:a]` = voice. If the
   voice is added before the `-ss`/`-t`-trimmed source, `-ss` starts applying to the voice
   instead and the whole clip shifts. The second `-i` must come *after* the source's
   `-t … -i src` pair.
4. **Assuming 18 dB happens.** It does not; §2.5 measures 16 dB for the shipped constants. Use
   `voice.threshold_for` and keep the clamp, or the feature quietly under-duck quiet phone
   recordings — where the push-to-talk moment the user cares about has the game at *full*
   volume, which is the exact complaint that made this feature worth porting.
5. **`at` beyond the clip.** `adelay` past the end produces silence and no duck, and the user
   sees "nothing happened". `clean_spec` rejects it, and the route must surface that 400 rather
   than swallowing it.
6. **Single-user assumptions that do not survive PeakCut.**
   - `-y` overwrites whatever is at `out` (`voice.py:13`). In the port the output name is
     `<cid>.mp4` and the previous good clip is moved aside by `render.py:316-320` — but a
     crashed render must not leave a half-written file in place of a good clip. Rely on the
     existing work-dir + move pattern; do **not** write ffmpeg output directly to the final path.
   - `main(*sys.argv[1:5])` trusts four positional strings. In the server every one of them is
     user input: `at` is `NaN`/`inf`/negative, `duck` is huge, `file` is `../../etc/passwd`.
     `clean_spec` covers all three; the filename regex is the one that matters most because it
     becomes a filesystem path.
   - The file is an upload: unbounded size, arbitrary container, possibly no audio stream at
     all. `VOICE_MAX_MB` + `probe_db`'s "no sound in it" check are mandatory, not polish.
   - Content addressing: `{cid}.voice{ext}` is per-clip, so two users can never collide (the job
     dir is per-user). Do not hoist it to `DATA_DIR` or to a shared tmp name — `os.urandom` is
     only for the staging file.
   - Nothing here may touch another user's job: every lookup goes through `_job_or_404`
     (`server.py:593`), which resolves within the caller's own job list. With sign-in off
     (`config.ACCOUNTS` unset) every request belongs to the one built-in owner
     (`auth.local_user()`, reached through `ctx.uid()`), so the same code path serves both
     single-user and multi-user installs — that is the one place the original's single-user
     assumption happens to be safe, as long as the identity keeps coming from the session and
     never from the request body.
7. **Dependency concerns.** None new: ffmpeg/ffprobe are already required by `media.py`, and the
   filters used (`loudnorm`, `sidechaincompress`, `adelay`, `apad`, `asplit`, `amix`,
   `alimiter`) are all in the essential build. `sidechaincompress` needs the `swresample`/`af`
   filter set but no extra library. Two real portability notes: (a) `adelay`'s `all=1` option
   exists since ffmpeg 4.2, so pin nothing new but do not lower a documented minimum below that;
   (b) `alimiter` is CPU, not lookahead-free — it adds latency compensation internally, so do
   not try to "fix" the output length with `-shortest`.
8. **Loudness drift.** A voice clip measures hotter than a plain clip, because the game is
   normalised to −14 LUFS *then* mixed with a −16 LUFS voice and only limited at −0.45 dBFS.
   Do not add a second `loudnorm` after the limiter to "fix" it: a dynamic normaliser chasing a
   sidechain ducker pumps audibly. Accept the drift, and compare a voice clip against a plain
   clip by ear before shipping.

## 7. Verification

### 7.1 The graph, headless (fastest proof)

```bash
cd peakcut && python - <<'PY'
from pathlib import Path
from studio import voice
import subprocess, random
d = Path("/tmp/votest"); d.mkdir(exist_ok=True)
subprocess.run(["ffmpeg","-y","-v","error","-f","lavfi","-i",
    "sine=frequency=200:sample_rate=48000:duration=6","-af","volume=-14dB",
    "-c:a","pcm_s16le",str(d/"game.wav")], check=True)
subprocess.run(["ffmpeg","-y","-v","error","-f","lavfi","-i",
    "sine=frequency=3000:sample_rate=48000:duration=2","-c:a","pcm_s16le",
    str(d/"line.wav")], check=True)
db = voice.probe_db(d/"line.wav")
chain = voice.mix_chain(2.0, 18.0, db)
subprocess.run(["ffmpeg","-y","-v","error","-i",str(d/"game.wav"),"-i",
    str(d/"line.wav"),"-filter_complex",chain.lstrip(";"),"-map","[a]",
    "-c:a","pcm_s16le",str(d/"mix.wav")], check=True)
print("voice_db", round(db,2), "chain", chain[:60], "...")
PY
```

Then assert the three numbers that matter, with a tiny Goertzel in the same script:

- output duration is **6.00 s** (±0.02) — proves `apad` is doing its job;
- the 200 Hz game bed drops by **18 dB ± 2** between 2.5 s and 3.5 s relative to 0.5–1.5 s;
- the bed is back within **0.5 dB** of its original level by 4.6 s (voice ends at 4.0 s, release
  is 400 ms).

### 7.2 Permanent regression test — `peakcut/tests/test_voice.py`

Model it on the existing `peakcut/tests/test_captions.py` (same directory, same style).

```python
from studio import voice

def test_duck_depth_matches_the_request(tmp_path):
    game = _tone(tmp_path / "game.wav", 200, 6.0, -14)
    line = _tone(tmp_path / "line.wav", 3000, 2.0, -20)
    db = voice.probe_db(line)
    chain = voice.mix_chain(2.0, 18.0, db).lstrip(";")
    mix = _run_chain(tmp_path / "mix.wav", game, line, chain)
    assert abs(_duration(mix) - 6.0) < 0.02
    before = _level_at(mix, 200, 0.5, 1.5)
    under  = _level_at(mix, 200, 2.5, 3.5)
    assert 16.0 <= before - under <= 20.0          # 18 dB target
    assert abs(_level_at(mix, 200, 5.0, 5.9) - before) < 0.5   # released

def test_apad_keeps_full_length(tmp_path):
    ...  # same graph with "apad" stripped must measure ~4.0 s, guarding the invariant

def test_clean_spec_rejects_bad_at():
    for bad in (-1, "x", float("nan"), 99):
        with pytest.raises(ValueError):
            voice.clean_spec({"file": "a.voice.wav", "at": bad, "db": -20}, 10.0)

def test_clean_spec_rejects_path_traversal():
    with pytest.raises(ValueError):
        voice.clean_spec({"file": "../job.json", "at": 1, "db": -20}, 10.0)

def test_threshold_for_matches_measurement():
    assert voice.threshold_for(18.0, -19.6) == pytest.approx(0.0118, abs=0.001)
    assert voice.threshold_for(16.0, -19.6) == pytest.approx(0.015, abs=0.002)
```

Run it with:

```bash
cd peakcut && python -m pytest tests/test_voice.py -q
# or the suite's own runner:
cd peakcut && python tests/run.py
```

### 7.3 End to end, through the server

```bash
# 1. attach a line to a finished clip, 1.0 s in, 18 dB duck
curl -b cookies.txt -F "file=@line.wav" -F "at=1.0" -F "duck=18" \
     http://127.0.0.1:8000/api/jobs/<JID>/clips/<CID>/voice
#    -> 200, and the clip payload now carries "voice": {"file", "at", "duck", "db"}

# 2. re-make it; the mix happens on this call
curl -b cookies.txt -H 'content-type: application/json' -d '{}' \
     http://127.0.0.1:8000/api/jobs/<JID>/clips/<CID>/render

# 3. the finished file must be the full clip length and carry both signals
ffprobe -v error -show_entries format=duration -of csv=p=0 data/users/*/<JID>/clips/<CID>.mp4
ffmpeg -v error -i data/users/*/<JID>/clips/<CID>.mp4 -map 0:a:0 -af volumedetect -f null -
#    -> mean_volume within ~1 dB of a version rendered without the voice
```

Then the acceptance check a human can do in ten seconds: play the clip, and at the stated
second the game must audibly step back for the length of the line and swell back within about
half a second, and the line must be clearly on top of the game the whole time it plays.

Failures must be visible: upload a `.txt` (→ 400 "Record your line as a wav, mp3 or m4a file."),
a silent wav (→ 400 "That file has no sound in it."), and `at=999` (→ 400 "Your line starts
after the clip ends. Pick an earlier second."). A missing voice file at render time must surface
as `clip["error"] == "The voice line for this clip is missing. Record it again."`, not a silent
no-voice render.
