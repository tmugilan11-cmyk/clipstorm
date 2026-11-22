# 09 — Peek: preview frames of a pick before rendering it

Source: `gta6-clipper-main/peek.py` (51 lines).
Host: `peakcut/studio/peek.py` (new), plugged into `peakcut/studio/jobs.py`.

---

## 1. What it does

Before PeakCut spends a render on a moment, it can show what that moment actually looks like on screen: four frames taken inside the clip's own window — one second in, a third through, two thirds through, one second from the end — stitched left-to-right into a single wide JPEG. The strip is written next to the finished clips and shown in the library card, so a person can see "wrong game on screen", "menu", "ad break", "score screen" without paying for a 40-second vertical render. Each strip is built from the smallest video the moment can be cut from — the already-fetched per-clip piece when one exists, otherwise a throwaway 240p slice of just those seconds. The whole feature is opt-in and non-fatal: if the preview fails, the clip still renders exactly as it does today.

---

## 2. Exact mechanics

### 2.1 One durable artefact, not four

The feature brief says "4 frames … into clips/peek/". Correct it: **the four frames are scratch files in a temporary directory and are deleted.** The only thing that survives is one horizontally-stacked strip JPEG per clip. `peek.py:1` states it — "4 frames of each picked moment … as one strip" — and `peek.py:17` opens with `tempfile.TemporaryDirectory(...)`, with the frames written into `tmp` at `peek.py:32` and only the `hstack` output (`peek.py:37`) written to the real output directory.

```
clips/<cid>_peek.jpg     # one strip per clip: 240 px tall, four frames wide
```

Concretely, for a 30 s clip at 1280×720 source: each frame is `scale=-2:240` → 426×240, and the strip is 1704×240.

### 2.2 The four sample times

```python
def times(a, b):
    return [a + 1, a + (b - a) / 3, a + 2 * (b - a) / 3, b - 1]
```
`peek.py:9`. The comment on that line is the contract: *"inside the window: the cut snaps to sentences, never past it"* — i.e. never sample outside `[a, b]`, because the renderer's own sentence-snap may move the cut, and a frame from outside the window would be a lie about what the clip shows.

Why 1 s of inset rather than 0: the first and last quarter-second of a cut are the fade/keyframe junk; `a+1` and `b-1` land on real picture.

The source ships its own proof — `peek.py:49`:

```python
assert [round(x) for x in times(100, 130)] == [101, 110, 120, 129]
```

**`times()` is not safe for short windows.** For `b - a = 3` (PeakCut's minimum clip, `jobs.py:359-360`) it returns `[a+1, a+1, a+2, a+2]` — two duplicate pairs, and two `ffmpeg` seeks producing identical frames. For `b - a < 2` it returns times *before* `a` and *after* `b`. The port must clamp and de-duplicate (§4.2); the source never hits this because its own picks are 20–60 s.

### 2.3 The frame seek

```python
["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{max(t - off, 0):.2f}", "-i", src,
 "-frames:v", "1", "-vf", "scale=-2:240", f"f{i}.jpg"]
```
`peek.py:32`, `check=True`, `timeout=60`.

Five load-bearing details:

| detail | why |
|---|---|
| `-ss` **before** `-i` | input seek: ffmpeg jumps instead of decoding from zero. This is the whole reason 4 frames cost ~0.3 s. |
| `-ss … {:.2f}` | two decimals, always. Sub-second precision matters when the window is 3 s. |
| `max(t - off, 0)` | `off` is the file-time of the video's second zero (see 2.4). Never seek negative. |
| `scale=-2:240` | `-2` = "compute the width, keep it **even**". Odd width is what makes `hstack` fail with *"Input 0 width … is not divisible by 2"*. |
| `-frames:v 1` | stop after one frame; without it ffmpeg decodes the remainder of the file. |

`check=True` catches a hard error, but a seek past EOF is **not** an error to ffmpeg — it exits 0 and writes nothing. So the real guard is the existence check, `peek.py:33-34`:

```python
if f.exists():
    frames += ["-i", str(f)]
```

The port must keep that guard: a frame that is missing is dropped, not an error.

### 2.4 `off` — the offset that decides whether the frames are of the right moment

`peek.py:23-27` branches on whether the source is already a local file:

```python
if Path(p["url"]).is_file():
    src, off = p["url"], 0.0
else:
    src, off = str(Path(tmp) / "m.mp4"), a        # downloaded slice starts at a
```

When the video is downloaded as a slice starting at `a`, file-time 0 **is** video-time `a`, so every sample time must be shifted down by `a`. When the source is the original file, file-time 0 is video-time 0 and `off` is 0.

This is the single most breakable part of the port. PeakCut has *three* possible sources with three different `off` values (§4.4). Getting it wrong produces a strip that looks plausible and is of a completely different moment — it fails silently, which is the worst failure mode for a preview feature.

### 2.5 The download (240p, one window only)

```python
[sys.executable, "-m", "yt_dlp", *CK, "-q",
 "-S", "res:240",
 "--download-sections", f"*{a:.2f}-{b:.2f}",
 "--merge-output-format", "mp4",
 "-o", src, p["url"]]
```
`peek.py:26`. `-S res:240` sorts formats preferring 240p — a preview needs no more. `--download-sections *a-b` fetches only that window. `CK` (`peek.py:7`) is the source's only cookie story:

```python
CK = ["--cookies-from-browser", os.environ["CLIPPER_BROWSER"]] if os.environ.get("CLIPPER_BROWSER") else []
```

**This does not port.** PeakCut has no browser cookie import (see §6.6) and never downloads as a subprocess.

### 2.6 Timeouts, and why the source does not use `subprocess.run(timeout=)`

`peek.py:11-15`:

```python
pr = subprocess.Popen(cmd)
try:
    pr.wait(timeout)
except subprocess.TimeoutExpired:
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pr.pid)] if os.name == "nt"
                   else ["pkill", "-P", str(pr.pid)], capture_output=True)
    pr.wait()
    raise
```

The comment is the finding: *"subprocess.run(timeout) kills only yt_dlp; its ffmpeg child kept streaming and stalled the next picks"*. yt-dlp spawns ffmpeg to merge, and killing the parent orphans that child, which keeps writing to the same file while the next pick starts. Hence `kill the whole tree` (`/T` on Windows, `-P` — children of PID — elsewhere).

Retry policy, `peek.py:29-30`: **two attempts, 90 s each.**

```python
for retry in range(2):
    if run_tree(cmd, 90) == 0:
        break
    ...
    raise RuntimeError("yt_dlp failed")
except subprocess.TimeoutExpired:
    if retry:
        raise RuntimeError(f"download stalled twice (90 s each) for {a:.0f}-{b:.0f}s; "
                           "peek skipped, render is unaffected")
```

Note the message: **`render is unaffected`** — the feature is explicitly allowed to fail. That is the contract the port must preserve.

### 2.7 The stack

`peek.py:35-37`:

```python
if not frames:
    raise RuntimeError("no frames")
n = len(frames) // 2                     # frames is ["-i", path, "-i", path, ...]
ffmpeg -y -loglevel error <frames...> -filter_complex (f"hstack=inputs={n}" if n > 1 else "null") <jpg>
```

- `n` is derived as `len(frames) // 2` because the list is interleaved argv pairs — not `len(frames)`.
- `hstack` requires **equal height on all inputs and even widths**; `scale=-2:240` (2.3) guarantees both, and is why every frame must go through the identical filter.
- The `n == 1` case cannot use `hstack` (it needs ≥ 2 inputs), hence the `"null"` filtergraph. If the port ever emits `hstack=inputs=1` ffmpeg errors out.
- Default `q`/pix_fmt: no `-q:v` is passed, so ffmpeg uses mjpeg's default (`-q:v 2`-ish for a `.jpg` output) — roughly 60–120 KB for a 1704×240 strip. Fine to leave alone; do not "improve" it to `-q:v 3` without checking text legibility, since the strip is meant to be *read* (HUD, score, menu names).

### 2.8 The driver, and the two behaviours worth keeping

`peek.py:40-46`:

```python
out.mkdir(parents=True, exist_ok=True)
def one(p):
    try:    print("ok", strip(p, out), "|", p.get("hook", ""))
    except Exception as e:  print("failed", p["name"], str(e)[:120])   # never re-raises
with ThreadPoolExecutor(4) as ex:
    list(ex.map(one, picks))
```

1. **One failure never stops the run** — `one()` swallows everything and prints. (`ex.map` would otherwise surface the exception on `.result()`, which `list()` calls.)
2. **Four at a time** — `ThreadPoolExecutor(4)` (`peek.py:46`). Appropriate for a single-user desktop tool with the GPU idle; wrong for a server (§6.4).

And the parts expansion at `peek.py:43`, for clips that are callback halves:

```python
picks = [x for p in picks
         for x in ([p | q | dict(name=f"{p['name']}_part{k}") for k, q in enumerate(p["parts"], 1)]
                   if p.get("parts") else [p])]
```

PeakCut has no `parts` concept — its clips are flat dicts with `start`/`end`. Drop this; do not port a `parts` key that nothing produces.

### 2.9 Full constant table

| constant | value | source |
|---|---|---|
| frame count | 4 | `peek.py:9` |
| inset from either end | 1.0 s | `peek.py:9` |
| intermediate fractions | 1/3, 2/3 | `peek.py:9` |
| frame height | 240 px | `peek.py:32` |
| download format sort | `res:240` | `peek.py:26` |
| download attempts | 2 | `peek.py:29` |
| download timeout | 90 s per attempt | `peek.py:29` |
| per-frame ffmpeg timeout | 60 s | `peek.py:32` |
| stack filter | `hstack=inputs=n` / `null` | `peek.py:36` |
| workers | 4 | `peek.py:46` |
| output | one `.jpg` per pick | `peek.py:19` |
| jpeg quality | ffmpeg default (none passed) | `peek.py:37` |

---

## 3. PeakCut today

Nothing in PeakCut samples more than one frame of anything, and nothing previews a pick at all.

**The overlap — single-frame extraction, three existing implementations:**

| what | where | how |
|---|---|---|
| clip cover | `render.py:316-318` | `cover_t = min(1.2, (end - start) / 2)`; `ffmpeg -y -v error -ss {cover_t:.2f} -i <name>.mp4 -frames:v 1 -q:v 3 <name>.jpg` — of the **rendered** mp4, i.e. after the render is already paid for |
| source thumbnail | `media.py:223-242` `save_thumb(job_dir, url="", video=None)` | link thumbnail bytes, or `ffmpeg -ss {min(3.0, d/3):.2f} -frames:v 1 -vf scale=480:-2 -q:v 4` — one frame of the **whole video**, not of a pick |
| frame for a model | `facecam.py:284-293` `_frame_jpeg(path, width=768)` | `-ss mid -frames:v 1 -vf scale=768:-2 -pix_fmt yuvj420p -q:v 4 -f image2pipe -vcodec mjpeg -` → bytes. **The best precedent in the codebase** for "ffmpeg gives you a JPEG"; note it already uses `scale=…:-2` and takes a timeout. |

**The gap, precisely:**

1. There is no multi-seek sampler and no `hstack` anywhere in `peakcut/studio/`.
2. The library card shows one frame of the finished clip — `web/index.html:1681` `<img src="${m}${esc(c.cover)}?v=${c.version}">` — so a user sees the picture only *after* the render, which is the exact problem Peek exists to solve.
3. The downloadable-slice primitive already exists and only needs a smaller height: `media.py:266-277` `download_section(url, out_dir, stem, start, end, height=720, exact=False)`, whose `download_ranges=download_range_func(None, [(max(0.0, start), end)])` (`media.py:272`) is PeakCut's form of `--download-sections`, and whose `height` maps to `_video_format(height)` (`media.py:106`). `height=240` reproduces `-S res:240`.
4. For URL videos PeakCut **already holds the moment on disk**: `jobs.py:471` `_piece_again` / `jobs.py:492` `_fetch_piece` download the piece and record `clip["src"]`, `clip["src_offset"]`, `clip["src_end"]`. A peek on such a clip needs no download at all — the source always re-downloads, which is pure waste in the host.
5. The seam where a peek is cheap and correctly "before rendering" is `jobs.py:644-660`, the `make()` closure: `_fetch_piece` has just run (`:646-647`), `render_one` has not (`:660`).
6. `jobs.py:108` `on_clip_ready` / `jobs.py:394` fires **after** `render_one` returns and only when `version == 1` — right for posting, too late for peeking.
7. Serving and cleanup gaps: `server.py:1034-1041` `media_file` serves `<job dir>/clips/<name>` matching `[\w\-]+\.(mp4|jpg)` — a strip named `<cid>_peek.jpg` is served **with no route change**; but `account.py:35-40` unlinks only `clip["file"]`, `clip["cover"]`, and `{cid,file_stem}.{ass,json}`, so a strip would be orphaned on clip deletion.
8. Options plumbing that must learn one new key: `jobs.py:110-111` `DEFAULTS`, `jobs.py:114` `LIMITS`, `jobs.py:117-142` `clean_options` (which already has a `bool` precedent at `captions`), and `jobs.py:149-166` `public(job)` (which strips `src`/`fixed_words`/`fixed_for` per clip but would pass a bare filename through happily).

---

## 4. Port plan

### 4.1 New module: `peakcut/studio/peek.py`

One concern: turn one clip window into one strip JPEG. **It must not import `jobs`** — `jobs.py:14` will import `peek`, so a back-import is a cycle. Everything that needs `jobs.save()` happens in the caller.

Imports it may use: `config`, `media`, `safe` — that is all. No `numpy`, no `PIL`, no new dependency.

```python
"""Frames of a pick before it is rendered: four moments of one clip as a single strip."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from . import config, media, safe
```

Module constants (all module-level, **never mutated** — see §6.3):

```python
FRAMES = 4          # samples per clip
FRAME_H = 240       # px, the same 240p the source downloads
INSET = 1.0         # seconds trimmed off each end before sampling
SEEK_TIMEOUT = 60   # seconds, per frame
STACK_TIMEOUT = 120 # seconds, for the hstack
DL_TIMEOUT = 90     # seconds, per download attempt
DL_TRIES = 2

def frame_count() -> int:
    """FRAMES, or PEAKCUT_PEEK_FRAMES. Read per call, never cached at import."""
    return max(2, int(config.env("PEAKCUT_PEEK_FRAMES", str(FRAMES)) or FRAMES))

def frame_height() -> int:
    return max(120, int(config.env("PEAKCUT_PEEK_HEIGHT", str(FRAME_H)) or FRAME_H))
```

`frame_count()`/`frame_height()` as functions rather than constants follow `config.py:135-136` (`SKIP_STATIC`, `STATIC_THRESHOLD`) — the host's existing style for "operator may override via env". Minimum 2 because `hstack` needs two inputs; if that is violated the `n == 1` path (4.3) covers it anyway.

### 4.2 `times()` — the sampler, fixed for short windows

```python
def times(a: float, b: float, count: int | None = None) -> list[float]:
    """Where to look inside [a, b]: one second in, then even thirds, one second from the end.

    Always inside the window and always ascending. A short window (a 3 s clip) gives fewer,
    deduplicated times rather than repeated ones.
    """
```

Behaviour, exactly:

```python
n = max(2, count or frame_count())
a, b = float(a), float(b)
if b <= a:
    return [a]
span = b - a
if span <= 2 * INSET:                      # a 3 s clip: no room for insets, spread evenly instead
    pts = [a + span * (k + 1) / (n + 1) for k in range(n)]
elif n == 4:
    pts = [a + INSET, a + span / 3, a + span * 2 / 3, b - INSET]      # peek.py:9, unchanged
else:                                      # operator overrode the count: same insets, even steps
    lo, hi2 = a + INSET, b - INSET
    pts = [lo + (hi2 - lo) * k / (n - 1) for k in range(n)]
hi = b - 0.05                              # never seek onto the very last frame
out = sorted({round(min(max(t, a), hi), 3) for t in pts})
return out or [a]
```

The `elif n == 4` branch **must reproduce the source bit for bit** for a normal window: `times(100, 130)` → `[101.0, 110.0, 120.0, 129.0]`, and `[round(x) for x in ...] == [101, 110, 120, 129]` must hold, because §7 asserts it. The `set` de-duplication plus `sorted` is order-preserving for any span > 2 s, because the source's own four times are already ascending there. `- 0.05` matters only for the last sample: seeking exactly onto the final frame of a file returns nothing on some builds, and a missing frame is silently dropped (4.3), so the strip would come out with three tiles.

### 4.3 `frames()`, `stack()`, `strip()`

```python
def frames(src: Path, start: float, end: float, out_dir: Path,
           off: float = 0.0, height: int | None = None) -> list[Path]:
    """Fetch up to N frames of [start, end] out of `src` as small JPEGs. `off` is the
    video-time of the file's second zero. Frames that ffmpeg refuses to produce are skipped."""
    h = height or frame_height()
    out_dir.mkdir(parents=True, exist_ok=True)
    got: list[Path] = []
    for i, t in enumerate(times(start, end)):
        f = out_dir / f"f{i}.jpg"
        cmd = ["ffmpeg", "-y", "-loglevel", "error",
               "-ss", f"{max(t - off, 0.0):.2f}", "-i", str(src),
               "-frames:v", "1", "-vf", f"scale=-2:{h}", str(f)]
        try:
            media.run(cmd, timeout=SEEK_TIMEOUT)
        except Exception:                      # noqa: BLE001 - one bad seek is not a failed peek
            continue
        if f.exists() and f.stat().st_size > 0:
            got.append(f)
    return got
```

Note `media.run` (`media.py:80`) is the host's ffmpeg runner: it already sets `creationflags=NO_WINDOW`, captures output, and converts a non-zero exit into `RuntimeError(f"{cmd[0]} failed: {stderr[-1500:]}")` — so the source's `check=True` is already in place, and the console-window flash that `NO_WINDOW` (`media.py:14`) exists to prevent is already handled.

One deliberate divergence from `peek.py:33-34`. The source treats "ffmpeg exited 0 but wrote no file" as normal and skips the frame. Under `media.run`, an ffmpeg that exits non-zero **raises**; we swallow it with `continue` for the same reason — a missed frame is not a missed peek — but the `st_size > 0` check is what catches the other case, because on several ffmpeg builds a seek past EOF exits 0 and writes a 0-byte file. Both guards are needed; neither alone is sufficient.

```python
def stack(jpgs: list[Path], out: Path) -> Path:
    """Left-to-right strip of the frames. One frame passes through untouched (hstack needs ≥2)."""
    if not jpgs:
        raise RuntimeError("no frames")
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for f in jpgs:
        cmd += ["-i", str(f)]
    cmd += ["-filter_complex", f"hstack=inputs={len(jpgs)}" if len(jpgs) > 1 else "null", str(out)]
    media.run(cmd, timeout=STACK_TIMEOUT)
    return out
```

The `n == 1` branch is not decorative: `hstack=inputs=1` is an ffmpeg error, and a 3 s clip whose two bad seeks got dropped can legitimately reach `n == 1`.

```python
def strip(src: Path, start: float, end: float, out: Path, off: float = 0.0) -> Path:
    """The whole feature: 4 frames of one window, stacked into one JPEG at `out`."""
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pkpeek", ignore_cleanup_errors=True) as tmp:
        return stack(frames(src, start, end, Path(tmp), off), out)
```

`ignore_cleanup_errors=True` is load-bearing and comes straight from `peek.py:19`: on Windows ffmpeg can still hold a handle when the context exits, and a failed cleanup must not fail a preview that already succeeded. It requires **Python ≥ 3.10**; PeakCut already uses `X | None` annotations and `list[str]`, so this is safe — but see §6.5.

### 4.4 `source()` — the three-way `off` decision

This is where the port diverges most from the source, and where a naive port breaks silently.

```python
def source(job: dict, clip: dict, work: Path) -> tuple[Path, float]:
    """The video to sample from, and the video-time of its second zero.

    Clip piece first (free), then the job's own upload, then a throwaway 240p slice.
    """
```

| case | condition | returns `(src, off)` | why |
|---|---|---|---|
| per-clip piece (URL jobs, long videos) | `clip.get("src")` | `(Path(clip["src"]), float(clip.get("src_offset", 0.0)))` | `_fetch_piece` (`jobs.py:492`) set both; the piece begins at video-time `src_offset`, exactly the source's `off = a` case at `peek.py:25`. **Zero download.** |
| uploaded file | `job.get("source_path")` | `(Path(job["source_path"]), 0.0)` | file starts at video-time 0 — the source's `Path(p["url"]).is_file()` branch, `peek.py:23-24`. |
| URL, no piece yet | `job["source"]["url"]` | `(piece, float(clip["start"]))` | mirrors `peek.py:25`: the slice's file-time 0 is video-time `start`. |

Body:

```python
    p = clip.get("src")
    if p:
        return Path(p), float(clip.get("src_offset", 0.0))
    sp = job.get("source_path")
    if sp:
        return Path(sp), 0.0
    url = (job.get("source") or {}).get("url") or ""
    if url and media.site_allowed(url):
        work.mkdir(parents=True, exist_ok=True)
        for attempt in range(DL_TRIES):
            try:
                piece = media.download_section(url, work, "peek",
                                               float(clip["start"]), float(clip["end"]),
                                               height=frame_height(), exact=True)
                return piece, float(clip["start"])
            except media.YouTubeBlocked:
                raise                                  # a refusal: retrying is what causes it
            except Exception:                          # noqa: BLE001 - second try, then give up
                if attempt == DL_TRIES - 1:
                    raise
        raise RuntimeError("no piece")                 # unreachable
    raise RuntimeError("There is no video to take frames from yet.")
```

Notes for the build agent:

- `exact=True` (`media.py:273-274`, sets `force_keyframes_at_cuts`) is **mandatory** here. The default `exact=False` cuts on the nearest keyframe, so the file would not begin at `clip["start"]` and `off = clip["start"]` would be wrong by up to a keyframe interval (seconds). This is the one place where reusing `download_section` with its defaults silently corrupts the result.
- `media.YouTubeBlocked` (`media.py:27`) must be re-raised, not retried — `check_youtube`/`note_refusal` (`media.py:41-54`) put YouTube on a 600 s (`YT_PAUSE`, `media.py:20`) pause for the whole process, and a second attempt is what trips the bot check.
- `media.site_allowed(url)` (`media.py:69`) is not decoration: it rejects anything whose host is not in `config.ALLOWED_SITES`, and `download_section` does **not** check it itself. Skipping this check would let a crafted job payload point yt-dlp at an arbitrary host.
- `DL_TIMEOUT` is declared for documentation parity with `peek.py:29`'s 90 s, but `media.download_section` takes no timeout — yt-dlp runs in-process (`media.py:275-277`). See §6.4; do not invent a wrapper to use it.
- `config` is used for the env helpers in `frame_count()`/`frame_height()`; `safe` is not needed inside `source()` — `journal`-style error text is added by the caller (§4.7b) so the wording lives in one place.

### 4.5 `make()` — one clip, one strip

```python
def make(job: dict, clip: dict) -> dict:
    """Frames for one clip, written beside its siblings. Returns the clip keys to set.

    Raises on failure; the caller decides whether that is fatal (it never is).
    """
    d = Path(job["dir"]) / "clips"
    name = f'{clip["id"]}_peek.jpg'
    start, end = float(clip["start"]), float(clip["end"])
    with tempfile.TemporaryDirectory(prefix="pkpeek", ignore_cleanup_errors=True) as tmp:
        src, off = source(job, clip, Path(tmp))
        strip(src, start, end, d / name, off)
    return {"peek": name,
            "peek_at": [round(t, 2) for t in times(start, end)],
            "peek_version": int(clip.get("peek_version", 0)) + 1}
```

The download work directory must be a `TemporaryDirectory`, not `mkdtemp`: a peek of a URL clip that has no `src` yet downloads a slice, and leaving it behind would accumulate junk in `config.TMP_DIR` that nothing ever deletes. `strip()` opens its own inner temporary directory for the four frames, so the two nest and both go.

Contract:

- **Writes exactly one file**: `<job dir>/clips/<cid>_peek.jpg`. `<cid>` is `clip01`… (`jobs.py:756`), so the name is `clip01_peek.jpg` — this matches `server.py:1035`'s `re.fullmatch(r"[\w\-]+\.(mp4|jpg)", name)` **with no route change**, because `_` is inside `\w`.
- `peek` is a **bare filename**, never a path. `jobs.public` (`jobs.py:152-166`) passes clip keys through except `src`/`fixed_words`/`fixed_for`, and `server.py:1038` resolves the name against `job["dir"]/clips`. Handing out an absolute path would leak the server's storage layout to the browser — the same reason `_job_or_404` and `media_file` never expose `dir`.
- `peek_version` exists for the same reason `version` does on the cover (`web/index.html:1681` `?v=${c.version}`): the strip is cached for 300 s (`server.py:1040`), so re-peeking must change the URL.
- Returns rather than saves, so `peek.py` never needs `jobs` and the import stays one-way (§4.1). The callers (§4.7b, §4.7c) do `clip.update(peek.make(job, clip))` and their own `save(job)`, keeping `_lock`/`ctx.bump` semantics in `jobs` where they live.

### 4.6 Optional: bytes for a model

```python
def strip_bytes(job: dict, clip: dict) -> bytes:
    """The strip as JPEG bytes, for showing to a model. b"" when there is none."""
    name = clip.get("peek")
    if not name:
        return b""
    p = Path(job["dir"]) / "clips" / Path(str(name)).name
    return p.read_bytes() if p.is_file() else b""
```

That is the entire extension point for "let the AI sanity-check the picture" (source `SKILL.md:45`: drop the pick if the wrong game / a menu / an ad / a logo card fills more than a couple of seconds, or the face never changes). `brain.look_for_facecam` (`brain.py:393`) and `ai.see(prompt, image)` (`ai.py:304`) are the existing consumers of image bytes. **Do not implement the review in this feature** — that is a separate spec; this function only makes the bytes reachable.

### 4.7 `jobs.py` — three small additions

**(a) Queue API, next to `request_render` (`jobs.py:345`):**

```python
def peek_clip(jid: str, cid: str) -> dict:
    """Queue a frame strip for one clip: the same picture the render will be made of."""
    job = _jobs.get(jid)
    if not job:
        raise ValueError("No such video")
    clip = next((c for c in job["clips"] if c["id"] == cid), None)
    if not clip:
        raise ValueError("No such clip")
    if clip.get("status") == "rendering":
        raise ValueError("This clip is being made right now. Try again when it has finished.")
    clip["peek_status"] = "queued"
    save(job)
    _q.put(("peek", jid, cid))          # no user= : the quick line, exactly like jobs.py:370
    return clip
```

`ValueError` because `server.py:939-952` already turns `ValueError`/`TypeError` from `request_render` into a 400, and the new route does the same (§4.8) — one error convention, no new exception type.

**`no user=` is not a style choice, it is the only correct call.** `_FairQueue.put(item, user=None)` (`jobs.py:43-53`) has two destinations: with `user`, the item joins that person's line and `get()` (`jobs.py:55-81`) increments `self.running`; with `user=None`, the item joins `self.quick` and `running` is untouched. Only `kind == "job"` ever calls `_q.done()` (`jobs.py:810` and `:833`) to decrement it. A peek queued with `user=` would therefore leave `running` permanently higher, and `_room()` (`jobs.py:31-36`) — `if self.running == 0: return True` — would eventually return False forever, stopping **every user's** videos. This is why the existing re-make path is `_q.put(("clip", jid, cid))` with no user (`jobs.py:370`). Copy that exactly.

The cost of the quick line is that a peek is served before queued videos. That is the right trade: a strip takes well under a second, and the alternative is a preview arriving minutes after the clip it describes.

**(b) Worker kind, inside `_worker` (`jobs.py:798-833`).** The existing dispatch is `if kind == "job": _run_job(job)` / `else: <render one clip>`. Make it three-way — insert a new `elif` between them and leave the `else` branch untouched:

```python
            if kind == "job":
                _run_job(job)
            elif kind == "peek":                       # NEW
                clip = next((c for c in job["clips"] if c["id"] == cid), None)
                if clip:
                    try:
                        clip.update(peek.make(job, clip))
                        clip["peek_status"] = "done"
                        clip.pop("peek_error", None)
                    except Exception as e:             # noqa: BLE001 - a peek never blocks anything
                        clip["peek_status"] = "error"
                        clip["peek_error"] = safe.friendly(e, 300)
                    save(job)
            else:
                <existing clip branch, unchanged>
```

Three details that are load-bearing:

- **Do not touch `ctx`.** `_worker` already does `token = ctx._uid.set(job["user"])` at `:812` before the dispatch and `ctx._uid.reset(token)` in the `finally` at `:831`, for every kind. Setting it again inside the branch would leak an extra token.
- **Do not call `_q.done()`.** See (a): a quick-line item never incremented `running`. Adding a `done()` there would let the queue start more concurrent videos than `JOB_WORKERS` permits.
- **Catch the exception in the branch, not outside it.** The outer `except` at `:822-829` writes `error.log`, marks queued/rendering clips as failed, and sets the *job* to `status="error"` — catastrophic for a preview that was never meant to be able to fail anything.

**(c) Automatic-before-render hook, inside `make()` (`jobs.py:644-660`), between `_fetch_piece` (`:647`) and the transcribe step (`:648`):**

```python
        if o.get("peek") and clip.get("status") != "error":
            try:
                clip.update(peek.make(job, clip))
            except Exception:                       # noqa: BLE001 - the render is what matters
                pass
            save(job)
```

This is the literal port of the source's workflow ("look before rendering"), and it is cheap: for URL jobs `_fetch_piece` has just downloaded `clip["src"]`, so the peek re-reads a file already on disk and performs no network work at all. It runs on the render pool thread (`jobs.py:663`), which is already an ffmpeg thread, so it adds no new concurrency shape.

**(d) Options plumbing** — three edits in `jobs.py`:

| file:line | change |
|---|---|
| `jobs.py:110-111` | add `"peek": False` to `DEFAULTS`, so `clean_options` will not silently drop the key and the SPA can read the default |
| `jobs.py:121-125` `clean_options` | add a branch beside `captions`: `if k == "peek": out[k] = bool(v); continue` |
| `jobs.py:114` | no `LIMITS` entry — it is a bool, and `LIMITS` is `(lo, hi)` integer ranges |
| `jobs.py:152-166` `public` | **no change** — `options` is returned whole and `peek` is a bool, so nothing leaks |

Why an explicit branch instead of relying on `DEFAULTS`: `clean_options` (`jobs.py:117-142`) ends with a catch-all `else: v = float(v)`. A string like `"off"` — which a browser form can easily send — would raise `ValueError("could not convert string to float")`, surfacing to the user as a 400 on job creation. The `captions` branch at `:121-125` exists precisely to avoid that; `peek` needs the same treatment.

### 4.8 `server.py` — one route, following the transcription block's gating

Insert beside `rerender` (`server.py:939`):

```python
@app.post("/api/jobs/{jid}/clips/{cid}/peek")
def peek_clip(jid: str, cid: str):
    job = _job_or_404(jid)
    _throttle("peek:" + ctx.uid(), 60, 600, "That's a lot of previews in a short time. Wait a moment.")
    try:
        jobs.peek_clip(jid, cid)
    except (ValueError, TypeError) as e:
        raise HTTPException(400, str(e))
    return jobs.public(_job_or_404(jid))
```

- `_job_or_404(jid)` (`server.py:593-597`) is the authorisation: it can only resolve a job the caller owns, so there is no cross-tenant path. Keep it as the **first** statement, before the throttle, exactly as `rerender` does.
- `_throttle` (`server.py:633-637`) takes `(key, limit, window, msg)`. 60 in 600 s is deliberately loose: a user legitimately peeks every pick of a 6-clip job. The render route uses 20/600 because renders cost minutes; a strip costs ~0.5 s.
- No `_quota()` call: a strip is ≤ ~150 KB and lives inside the job directory that `jobs.delete` (`jobs.py:334-342`) already `rmtree`s. If the operator wants it counted, `_quota` (`server.py:613`) measures the whole user tree anyway.
- **No change to `media_file`** (`server.py:1034-1041`): `<cid>_peek.jpg` satisfies `[\w\-]+\.(mp4|jpg)` and the path `<job dir>/clips/<name>` is where §4.5 writes it.

### 4.9 `account.py` — one line, so strips are not orphaned

`account.py:35-40` currently unlinks `clip["file"]`, `clip["cover"]`, and `{cid, file-stem}.{ass,json}`. Change the tuple at `:35` to include the strip:

```python
    for name in (clip.get("file"), clip.get("cover"), clip.get("peek")):
```

Without this, deleting a clip leaves its `_peek.jpg` on disk forever and the file silently counts against `MAX_USER_GB` (`config.py`). Deleting a whole video is already covered by `shutil.rmtree`.

### 4.10 `web/index.html` — show it, and mark the button

In `clipHtml(j, c)` (`index.html:1681-1703`), inside the `<article class="clip">`, after the cover `<img>` block:

```js
${c.peek ? `<button class="peek" data-act="peekpic" data-id="${esc(j.id)}" data-cid="${esc(c.id)}"
   title="Four frames of this moment">${ic("eye")}</button>
 <img class="peekstrip" src="/media/${esc(j.id)}/${esc(c.peek)}?v=${c.peek_version||1}"
   alt="Four frames of this moment" loading="lazy">` : ""}
```

- `ic("eye")` — `"eye"` already exists in the `I` map (`index.html:847-903`), so no new icon is needed. **Never reference an icon key that is absent** — `ic()` (`index.html:904`) interpolates `I[n]` and a missing key renders the literal string `undefined` as the SVG body.
- `peek_version` in the query string is required, not decorative: `server.py:1040` sets `Cache-Control: private, max-age=300`, so a re-peek with an unchanged URL would show the old strip for five minutes.
- `esc()` the filename, as `c.cover` is escaped at `:1681`.
- A `data-act="peekpic"` handler posts the route from §4.8 and, on success, re-renders that card. Follow the existing `data-act` switch rather than adding a new listener.
- Optional, and the only place a settings tab would ever be needed: surface the `peek` job option as a checkbox beside the captions toggle (`index.html:1381`, `#o_captions`). Do **not** add a `peek` settings tab to `setTabs()` (`index.html:2003-2009`) or to the router alternation (`index.html:1317`) — this feature has nothing per-account to store.

### 4.11 Call graph, complete

```
POST /api/jobs/{jid}/clips/{cid}/peek   server.py (new, §4.8)
  └─ jobs.peek_clip(jid, cid)            jobs.py (new, §4.7a)
       └─ _q.put(("peek", jid, cid))    jobs.py:103  _FairQueue.put
            └─ _worker(quick_only=False) jobs.py:798  kind == "peek"  (new, §4.7b)
                 └─ peek.make(job, clip) peek.py §4.5
                      ├─ peek.source(job, clip, work)  §4.4
                      │    └─ media.download_section(url, work, "peek", start, end,
                      │                               height=240, exact=True)   media.py:266
                      │       └─ media._ydl / _youtube_guard                       media.py:56,98
                      ├─ peek.strip(src, start, end, out, off)   §4.3
                      │    ├─ peek.times(start, end)             §4.2
                      │    ├─ peek.frames(...) -> media.run(["ffmpeg", ...])      media.py:80
                      │    └─ peek.stack(...)  -> media.run(["ffmpeg", ...])      media.py:80
                      └─ returns {"peek", "peek_at", "peek_version"}
                 └─ jobs.save(job)        jobs.py:169  (tmp+replace, ctx.bump)

automatic path (job option peek=True), off by default:
_run_job(job)  jobs.py:546
  └─ block loop  jobs.py:736-779
       └─ renders.submit(ctx.bind(make), c, list(words))   jobs.py:767
            └─ make(clip, words_now)                        jobs.py:644
                 ├─ _fetch_piece(job, clip, audio)          jobs.py:492  -> clip["src"], src_offset
                 ├─ peek.make(job, clip)   <-- NEW, §4.7c
                 └─ render_one(job, clip, words_now)        jobs.py:373
                      └─ render.render_clip(...)            render.py:267
```

The peek writes its own clip keys (`peek`, `peek_at`, `peek_version`, `peek_status`, `peek_error`) and touches nothing `render_one` reads, so the two can interleave without a lock. `jobs.save` is already atomic and serialised (`jobs.py:169-185`).

---

## 5. Data files

**None.** No new JSON asset, no new directory in `config.DATA_DIR`, nothing to migrate, nothing to lock.

Why, concretely:

1. **Nothing secret.** Unlike `tr.json`/`ai.json` there is no key, model, or credential — so the `_tr_public()` "never leak the key" machinery (`server.py:1343`) has no work to do.
2. **Nothing global to persist.** Every knob is either a job option (`peek: bool`, stored in `job["options"]` inside the job's own `job.json`) or an operator env override (`PEAKCUT_PEEK_FRAMES`, `PEAKCUT_PEEK_HEIGHT`, read through `config.env` exactly as `SKIP_STATIC`/`STATIC_THRESHOLD` are at `config.py:135-136`).
3. **Nothing per-user.** A strip is a file in the job directory; the job directory *is* the per-user namespace (`config.user_dir(uid)/jobs/<jid>`, `config.py:146`).

The only schema that changes is the clip dict inside the existing `job.json`:

| key | type | written by | meaning |
|---|---|---|---|
| `peek` | `str` | `peek.make` | bare filename, `clip01_peek.jpg`. Absent when there is no strip. |
| `peek_at` | `list[float]` | `peek.make` | the video-time of each frame, left to right. Debugging + lets the AI review say "the menu is the third frame". |
| `peek_version` | `int` | `peek.make` | 1, 2, 3… Only used as a cache-buster in the URL. |
| `peek_status` | `str` | `jobs.peek_clip` / `_worker` | `"queued"`, `"done"`, `"error"`. |
| `peek_error` | `str` | `jobs._worker` | `safe.friendly(e, 300)`, shown like any clip error. |

**Files on disk**, all inside the job directory that already owns everything else:

```
<user>/jobs/<jid>/clips/<cid>.mp4        existing render
<user>/jobs/<jid>/clips/<cid>.jpg        existing cover  (render.py:316)
<user>/jobs/<jid>/clips/<cid>_peek.jpg   NEW: the strip
```

---

## 6. Risks

### 6.1 `times()` on a short window (silent wrongness)

`peek.py:9` assumes a 20–60 s pick. PeakCut's minimum clip is 3 s (`jobs.py:359-360`), where the formula returns two duplicated pairs, and below 2 s it returns times outside the window. A naive copy therefore emits four frames of two moments, or frames of the *previous* clip. Fixed by §4.2; the fix must not change the output for normal windows — assert `times(100, 130)` in §7.

### 6.2 `off` — the silent-corruption bug

Wrong `off` ⇒ a beautiful strip of the wrong moment, no error anywhere. Three code paths, three offsets (§4.4). The one that bites: calling `media.download_section` **without `exact=True`** (`media.py:273-274`). With keyframe cuts the file does not start at `clip["start"]`, so `off = clip["start"]` is off by up to a GOP — 2–6 s of GTA 6 footage, i.e. a completely different scene. Note also that `_fetch_piece` (`jobs.py:492`) already sets `src_offset` correctly by FFT-matching the audio (`media.find_offset`, `media.py:280`); trusting it is right, recomputing it is not.

### 6.3 Multi-user assumptions that do not hold

| single-user source assumption | what it becomes on the server |
|---|---|
| `ThreadPoolExecutor(4)` per `main()` run (`peek.py:46`) | Up to 4 decodes × every concurrent user. On a 4-core box that is the whole machine. **Never** spawn a private pool; go through `_q`/`_FairQueue` (`jobs.py:16-101`), which is per-user fair. |
| module-level state is fine (one process, one user) | `FRAMES`/`FRAME_H` must be read-only module constants or function reads. The source has no state to leak, but a tempting "cache the last strip path" optimisation would become a cross-user data leak. Do not add one. |
| `print("ok"/"failed")` (`peek.py:41-44`) | Nothing prints on the server. Failure text goes to `clip["peek_error"]` via `safe.friendly` and to nothing else — never to stdout, which is the server log every user shares. |
| `os.environ["CLIPPER_BROWSER"]` cookies (`peek.py:7`) | Does not exist in PeakCut, and must not be invented: a server cannot control a user's browser, and bundled cookies would be a credential-sharing hole. `_youtube_guard` (`media.py:56`) is the host's answer — refusals are surfaced, not worked around. |
| one job at a time, one directory | `<jid>_peek.jpg` is inside that user's job dir, so no collision. But `peek.py`'s `tempfile.TemporaryDirectory` must stay per call; reusing one temp dir across users is a same-name clobber. |
| disk is the user's own | §4.9: an uncompiled `account.delete_clip` orphans strips into a quota measured by `MAX_USER_GB`. |

### 6.4 The `subprocess.run(timeout)` leak — and where it actually now applies

The source's `run_tree` (`peek.py:11-15`) exists because `subprocess.run(timeout=)` kills only yt-dlp and orphans its ffmpeg child. In the port:

- **The four seeks and the stack are safe**: `media.run` runs `ffmpeg` directly, no grandchildren, and a timeout kills the process that matters.
- **The download is not**: `media.download_section` calls `ydl.download([url])` **in-process** (`media.py:275-277`), so yt-dlp's own ffmpeg merge child belongs to the *worker* process, not to a subprocess that can be timed out. There is no hard timeout on that call — only `socket_timeout=20` inside `_ydl` (`media.py:98`). Consequence: a wedged merge hangs one render pool thread, not the request. Mitigation, in order: prefer `clip["src"]`; keep `exact=True` so the slice is small; accept the hang (it is one pool thread); do **not** add a `taskkill /T` of your own — it would kill the whole server on Windows if the PID were ever wrong.

### 6.5 Windows and Python

- `TemporaryDirectory(ignore_cleanup_errors=True)` needs **Python ≥ 3.10** (also for `X | None` annotations). Check `python -V` before assuming; the host already uses `list[float]` and `X | None` elsewhere, so this is a confirmation, not a discovery.
- The delete-while-held problem is real on Windows (`peek.py:19`'s comment) — never `unlink` the strip while a `FileResponse` is streaming it. `server.py:1034-1041` streams; the `_version` bump in §4.5 changes the URL, so an old stream finishes against an old inode; nothing writes in place.
- Long paths: `<user>/jobs/<jid>/clips/clip01_peek.jpg` is well inside 260 chars, unlike the ASS file that forced `render.py:267`'s short-path `mkdtemp`. No action needed — but do not extend the name with the hook text.

### 6.6 Dependencies

**None added.** `ffmpeg` is already mandatory (`tools.py:68` `missing()`, `server.py` reports `no_ffmpeg`); `yt-dlp` is pinned at `2026.10.21` (`requirements.txt`); `Pillow` is present but **not needed and must not be used** — the strip is composed by ffmpeg's `hstack`, and pulling a 1704×240 JPEG through PIL on the server buys nothing. Note that `--download-sections`/`-S res:240` are yt-dlp CLI spellings; the port uses `download_range_func` + `_video_format(240)` instead, so no CLI is spawned.

---

## 7. Verification

### 7.1 New test file: `peakcut/tests/test_peek.py`

Same shape as `tests/test_facecam.py`: set `PEAKCUT_DATA` to a temp dir **before** importing `studio`, print `PASS `/`FAIL ` per check, `sys.exit(1)` on any failure, and register the suite in `tests/run.py:48`'s `runs` list as:

```python
("seeing a moment before rendering it", ["tests/test_peek.py"]),
```

The test builds its own 30 s video, so it needs no assets:

```bash
ffmpeg -f lavfi -i "testsrc=size=1280x720:rate=25:duration=30" \
       -c:v libx264 -preset ultrafast -pix_fmt yuv420p clip.mp4
```

(`testsrc` cycles colour and draws a counter, so four frames from four moments are *provably* different images — that is what makes the checks below meaningful rather than tautological.)

Checks, in order:

1. **The source's own arithmetic still holds** —
   `[round(x) for x in peek.times(100, 130)] == [101, 110, 120, 129]`.
2. **A short window degrades instead of duplicating** —
   `t = peek.times(0, 3)`; assert `len(set(t)) == len(t)`, `len(t) >= 2`, and `all(0 <= x <= 3 for x in t)`. (A naive copy returns `[1, 1, 2, 2]` and fails this.)
3. **The strip exists and is a JPEG** — `p = peek.strip(src, 5, 25, out / "s.jpg")`; `p.stat().st_size > 1000`; `p.read_bytes()[:2] == b"\xff\xd8"`.
4. **Geometry proves four frames of 240 px** — with `PIL.Image` (present in `requirements.txt`): `im.height == 240`; `im.width % 4 == 0`; and `im.width / 4 == round(im.width / 4)`. Then crop the four tiles and assert each has `mean() > 0` and that not all four tiles are identical (`tiles[0].tobytes() != tiles[1].tobytes()`) — categorical proof that four *different* moments were sampled.
5. **`off` is honoured** — `a = peek.strip(src, 0, 10, out / "a.jpg", off=0.0)` and `b = peek.strip(src, 0, 10, out / "b.jpg", off=5.0)`; assert `a.read_bytes() != b.read_bytes()`. Also assert `peek.frames(src, 100, 130, tmp)` returns **fewer than 4** paths on a 30 s file (every seek past EOF must be skipped silently, not raise) — this is the `peek.py:33-34` existence guard, and it is the check that catches "seek past EOF raised and killed the peek".
6. **Failure is contained** — `peek.strip(Path("nope.mp4"), 0, 10, out / "x.jpg")` raises `RuntimeError`, and `(out / "x.jpg").exists()` is `False` (no half-written artefact).
7. **One frame is not `hstack=inputs=1`** — call `peek.stack([one_jpg], out / "one.jpg")` and assert it returns without raising.

### 7.2 Run it

```bash
cd peakcut
python tests/test_peek.py          # PASS/FAIL lines, exit code 1 on any failure
python tests/run.py                # the whole suite, including the new entry
```

### 7.3 Prove the route end to end

With `python tests/run.py`'s throwaway server (or any local `python -m studio.server`), against a job that has clips:

```bash
curl -s -X POST -b cookies.txt \
  http://127.0.0.1:8799/api/jobs/<jid>/clips/clip01/peek | head -c 300
# expect: the public job JSON, clip01 carrying "peek_status": "queued"

curl -s -b cookies.txt -o /tmp/s.jpg \
  http://127.0.0.1:8799/media/<jid>/clip01_peek.jpg
python -c "from PIL import Image; im=Image.open('/tmp/s.jpg'); print(im.size, im.format)"
# expect: (1704, 240) JPEG   <- 4 x 426 wide, 240 tall
```

Negative checks worth one command each: an unauthenticated POST returns 404 (not 403 — `_job_or_404` deliberately reports "No such video", `server.py:593-597`), and `POST …/peek` on a clip whose status is `rendering` returns **400** with "This clip is being made right now."

### 7.4 The pixel proof (the check that catches a wrong `off`)

The geometry test in 7.1.4 catches "no frames"; only this catches "frames of the wrong moment". With `clip["src"]` present, the strip built by `peek.make` must match a strip built directly from the original file:

```bash
# take clip01's own numbers straight out of job.json
ffmpeg -y -loglevel error -ss 12.00 -i <job>/source.mp4 -frames:v 1 -vf scale=-2:240 man0.jpg
ffmpeg -y -loglevel error -ss 12.00 -i <job>/clips/clip01_piece.mp4 -frames:v 1 -vf scale=-2:240 got0.jpg
python -c "import sys;from PIL import Image,ImageChops as C; \
  d=C.difference(Image.open('man0.jpg').convert('L'),Image.open('got0.jpg').convert('L')); \
  print('same moment' if d.getextrema()[1] < 12 else 'WRONG MOMENT', d.getextrema())"
```

`< 12` rather than `0` because the piece was re-encoded. Anything larger means `off` (or `exact=True`) is wrong — §6.2.
