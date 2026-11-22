# 02 — Clip formats (callback, compilation, escalation, thenvsnow, reveal, chat, waitforit)

Source of the feature: `gta6-clipper-main/formats.py` (283 lines), with helpers from
`gta6-clipper-main/parts.py` and `gta6-clipper-main/clip.py`.
Host: `peakcut/`.

---

## 1. What it does

Today PeakCut can only make one kind of Short: one continuous span with word-by-word captions
and a hook. This feature adds seven `format`s to that same span, so one pick can become a
structured video instead of a plain cut. `callback` plays a claim, hard-cuts to the payoff, and
marks the time jump with an "EARLIER" tag or a full "40 MINUTES LATER" card. `compilation`,
`escalation` and `thenvsnow` stitch 2-6 parts together with a full-screen label card before each
part ("#3", "STRIKE 1", "THEN") plus a small corner badge during it. `reveal` blurs the facecam
for the first second or two and then clears it with a flash. `chat` floats real Twitch chat
bubbles into the top of the frame after the payoff. `waitforit` adds a "WAIT FOR IT" tag and a
yellow bar that fills up to the payoff, then flashes and disappears. Every format is opt-in per
clip; a clip with no format renders exactly as it does today.

---

## 2. Exact mechanics

### 2.1 The pick contract

A pick is a dict. Common keys (`gta6-clipper-main/formats.py:1-11`):

| key | used by | meaning |
| --- | --- | --- |
| `format` | all | one of `moment`, `callback`, `compilation`, `escalation`, `thenvsnow`, `reveal`, `chat`, `waitforit` |
| `start`, `end` | all | seconds in the source; the whole clip for single-span formats |
| `hook` | all | the hook line shown on screen |
| `parts` | callback, compilation, escalation, thenvsnow | list of `{start, end, label?}`; a part may also carry `layout` |
| `tag` | callback, reveal, waitforit | corner tag text |
| `jump_card` / `jump` | callback | `true` = full card instead of the small tag; `jump` = card text (default `"LATER"`) |
| `word` | escalation | badge noun, default `"ATTEMPT"` |
| `labels` | thenvsnow | `["THEN","NOW"]` |
| `reveal` | reveal | blur seconds, default `1.6` |
| `payoff` | chat, waitforit | seconds (relative to the clip) of the payoff moment; if absent it is measured |
| `chat` | chat | optional list of strings used instead of fetching Twitch chat |
| `squeeze` | waitforit | silent-gap cut threshold in seconds, default `1.5`; `0` disables |

Format resolution (`formats.py:216`):

```python
def fmt_of(p): return p.get("format") or ("callback" if p.get("parts") else "moment")
```

Format registry and minimum part counts (`formats.py:213-214`):

```python
FORMATS = dict(moment=f_moment, callback=f_callback, compilation=f_compilation,
               escalation=f_escalation, thenvsnow=f_thenvsnow, reveal=f_reveal,
               chat=f_chat, waitforit=f_waitforit)
NEEDS_PARTS = {"callback": 2, "compilation": 3, "escalation": 3, "thenvsnow": 2}
```

Errors (`formats.py:247-252`), both `RuntimeError`, both surfaced to the user as text:

* `f"unknown format {fmt!r}; formats: {', '.join(FORMATS)}"`
* `f"{fmt} needs at least {NEEDS_PARTS[fmt]} parts"`

### 2.2 Shared constants

```python
YEL, RED, WHITE = "0xFFD400", "0xFF3B30", "white"   # formats.py:19
BADGE_Y = 215   # formats.py:20, under the platform's top UI
```

`BADGE_Y = 215` is the **top** edge of the badge/tag text, `x = 50` px from the left
(`formats.py:101,117,131,207`). There is an unused `CHAT_Y = 1330` at `formats.py:21`; chat rows
actually use `YB = 1440`.

Text size / border / box formulas (`formats.py:38-44`):

* `borderw = int(size) // 14 + 3`
* `boxborderw = int(size) // 4`
* font is chosen per script by `parts.font_for`: Arabic block (U+0600-06FF, 0750-077F,
  FB50-FEFF) → Noto Sans Arabic Bold, Devanagari (U+0900-097F) → Noto Sans Devanagari Bold,
  else Anton Regular (`parts.py:15-19`).
* all on-screen text passes `parts.clean_text`: uppercase, keep only Unicode categories `L`, `N`,
  `M` plus the seven characters `space # / . ! ? -` (`parts.py:11-13`). That is what makes
  `Kai's #3, 2/3!` become `KAIS #3 2/3!` and keeps `Café Ñandú مرحبا` intact.

### 2.3 Timeline of every format

**moment** (`formats.py:96-97`) — one span, no extra graphics. `[clip]`.

**callback** (`formats.py:99-107`) — part 0 gets the hook, parts ≥ 1 get no hook.

1. render part 0, render part 1, …
2. if the part index `k ≥ 1` **and** `p["jump_card"]`: insert a card before that part, built from
   the **last frame of the previous part**, text `p.get("jump", "LATER")`. That is the hard time
   jump: the still is the old scene, then the new scene appears.
3. else if `k == 0` and (`parts[1].start - parts[0].end > 600` **or** `p["tag"]` is set): burn the
   small tag `p.get("tag", "EARLIER")`, font 64, `x=50`, `y=215`, box `black@0.55`.
4. if no part is over 600 s apart and no tag/jump_card is given, the two parts are simply
   butt-joined with no marker at all.

`600` s is the only threshold: `float(sp[1]["start"]) - float(sp[0]["end"]) > 600`
(`formats.py:103`). Order is `[card?, part0, card?, part1, …]`.

**compilation / escalation / thenvsnow** share `numbered()` (`formats.py:109-118`), which yields
`[card0, part0, card1, part1, …]` — the card comes **before** its part:

card lines, in order:

* line 1 (only for `k == 0` and a hook is set): the hook, size 78, colour `YEL`
* line 2 (always): the big label, size `330` when `len(big) < 5` else `190`, colour `col`
* line 3 (only if the part has a `label`): that label, size 80, `WHITE`

card duration: `0.9` s for the first card, `0.6` s for the rest (`formats.py:116`).
badge for part `k`: `badge_of(k, n)`, size 100, `x=50`, `y=215`, colour `col`, box `black@0.55`,
present for the whole part.

Per-format table functions (`formats.py:120-128`):

| format | big label | badge | colour |
| --- | --- | --- | --- |
| compilation | `f"#{n-k}"` | `f"#{n-k}"` | `YEL` |
| escalation | `f"{word} {k+1}"` | `f"{word} {k+1}/{n}"` | heat ramp (below) |
| thenvsnow | `labels[min(k,1)]` | `labels[min(k,1)]` | `YEL` if `k == 0` else `RED` |

`compilation` counts **down** (`#3`, `#2`, `#1`) so the best clip is last. `escalation`'s
`word = clean_text(p.get("word", "ATTEMPT"))` and the heat ramp is exactly:

```python
heat = lambda k, n: ["0xFFFFFF", "0xFFD400", "0xFF9500", "0xFF3B30"][min(3, round(3*k/max(n-1, 1)))]
```

i.e. white → yellow → orange → red, index `round(3k/(n-1))` clamped to 3: for `n=3` the colours
are index 0, 2, 3 (white, orange, red). `thenvsnow` labels default to `["THEN", "NOW"]`
(`formats.py:127`).

**reveal** (`formats.py:130-142`)

* `R = float(p.get("reveal", 1.6))` seconds.
* The part is rendered in the "stack" layout (facecam on top) — required, because the blur box is
  the top of the frame.
* tag `p.get("tag", "WATCH HIS FACE")`, size 90, `y=215`, box `0xE11D48@0.9`, visible only for
  `t < R`.
* face gate: `face = has_face(f, 0)`; any exception means `face = True`. If no face, log
  `"reveal: no facecam found, rendered as a plain moment (nothing blurred)"` and return the plain
  part — the format degrades, it does not fail.
* blur geometry: `h = 620` (the comment at `formats.py:137` is `# blur stops above the hook (y ~ 680)`).
* filter chain, in order:

```
split[a][b];
[a]crop=1080:620:0:0,boxblur=45:3,eq=brightness=-0.35[bl];
[b][bl]overlay=0:0:enable='lt(t,1.600)',
<tag>,
drawbox=x=0:y=0:w=iw:h=ih:color=white@0.45:t=fill:enable='between(t,1.600,1.680)'
```

So the sharp reveal lands at `R` and a 0.08 s white flash covers the cut.

**chat** (`formats.py:189-202`)

* `t0 = float(p.get("payoff") or peak_time(f))` — the payload moment.
* rows come from `chat_rows()` (2.4).
* constants: `LIFE, X, YB, ROW = 2.2, 40, 1440, 112` — each bubble lives 2.2 s, sits 40 px from
  the left, its centre is at `1440 - overlay_h/2 - 112 * (number of newer rows)`, so a new bubble
  pushes the older ones up exactly one 112 px slot.
* pop: three-step scale `0.85` for 0.05 s, `0.93` for the next 0.05 s, `1.0` after — done with
  three `split` branches and three `overlay ... enable='between(t,a,b)'` calls, not with a
  per-frame scale (the source notes this was 10× faster).
* bubble PNG: rounded rect `radius = H//3`, fill `(14, 14, 20, 178)` (≈70 % dark), name in its
  Twitch colour at x 28, message white after it; font `Poppins-Bold.ttf` starting at 56 px,
  shrunk by 4 until `W = name_w + text_w + 56 <= 980` or `size <= 44`; `H = int(size + 40)`.
* no usable lines after filtering → `RuntimeError("no usable chat lines in this span")`.

**waitforit** (`formats.py:204-211`)

* the part is rendered with `squeeze = p.get("squeeze", 1.5)`: silent stretches longer than 1.5 s
  are jump-cut out (already supported by `clip.py`'s `squeeze` option in the source; in PeakCut
  this becomes caption-based gap removal, see 4.6).
* `t0 = float(p.get("payoff") or peak_time(f))`.
* `t0 < 2.5` logs `"payoff in the first 2.5 s, nothing to wait for; use format moment"`.
* graphic, all gated on `t < t0`:
  * tag `p.get("tag", "WAIT FOR IT")`, size 100, `y=215`, box `0xE11D48@0.9`
  * track: `drawbox=x=0:y=170:w=iw:h=18:color=black@0.5:t=fill`
  * fill: `drawbox=x=0:y=170:w='iw*min(t/5.20,1)':h=18:color=0xFFD400:t=fill:replace=0`
  * flash after the bar disappears: `drawbox=...:color=white@0.45:t=fill:enable='between(t,5.20,5.28)'`

    (numbers shown for `t0 = 5.2`; the formula is `t/t0` and `between(t, t0, t0+0.08)`.)

### 2.4 Choosing the payoff moment — `peak_time`

```python
def peak_time(mp4):                      # formats.py:89-93
    db = audio_db(mp4); k = len(db)//3
    return (k + int(np.argmax(db[k:]))) / 20
```

`audio_db` is 50 ms per sample (8 kHz mono, reshaped to `-1, 400`), hence `/20`. Net effect: the
loudest 50 ms window in the **last two thirds** of the part, in seconds. The first third is
ignored so a loud intro cannot win. `payoff` always overrides it.

### 2.5 Choosing chat lines — `chat_rows` / `fetch_chat`

If the pick carries `chat`, use it verbatim: `[(t0 + 0.2 + i*0.55, "", "#FFFFFF", clean_text(x))
for i, x in enumerate(p["chat"][:5])]` — first bubble 0.2 s after the payoff, then one every
0.55 s (`formats.py:161-162`).

Otherwise Twitch VOD chat only: `re.search(r"videos/(\d+)", p["url"])` must match, else
`RuntimeError('chat needs a Twitch VOD link, or give your own lines: "chat": ["KEKW", ...]')`
(`formats.py:165-167`). Query window is `v0-1 .. v0+9` where `v0 = clip.start + t0`
(`formats.py:168`), fetched from `https://gql.twitch.tv/gql` with the persisted query
`VideoCommentsByOffsetOrCursor` and the public web client id (`gta6-clipper-main/chat.py:15-16`;
the hash there carries the comment "persisted-query hash can rotate").

Filter, exactly (`formats.py:169-174`):

* strip every character outside `[A-Za-z0-9 ?!.*'-]`, then `clip.clean` each token
* keep `2 <= len(text) <= 24`
* reject text starting with `!`
* reject a second line that is the same lowercase text
* keep only authors matching `^[A-Za-z0-9_]{2,16}$`
* take the **5 shortest**, then re-sort those by time: `sorted(sorted(good, key=len(g[3]))[:5])`

Row times: `at = max(t0 + 0.2 + (s - v0) * 0.5, last + 0.5)`, `last = at`, keep only `at < d - 1.2`
— the real order and rhythm, squeezed ×0.5 and never closer than 0.5 s, so five fit in ~4 s
(`formats.py:172-174`).

### 2.6 Joining, loudness, and the final pass

Parts are joined by `parts.join` (`parts.py:51-64`), which is the load-bearing part of the whole
feature — a naive concat produces a file whose audio drifts or whose fps differs per segment:

per input:
`[i:v]scale=1080:1920,fps=30,setsar=1,format=yuv420p[v{i}];[i:a]aresample=48000,aformat=channel_layouts=stereo[a{i}]`
then `concat=n={n}:v=1:a=1[v][ac]`, then a **two-pass linear** loudnorm
`loudnorm=I=-14:TP=-1.5:LRA=11` (measure pass into `-f null -`, second pass adds
`:measured_I=…:measured_TP=…:measured_LRA=…:measured_thresh=…:offset=…:linear=true`; if the
measure pass fails it falls back to one-pass), encoded `libx264 -preset medium -crf 18 -c:a aac
-b:a 192k -ar 48000`.

Then one **final pass** over the finished Short (`formats.py:218-242`), so progress bar, end card
and extra aspect ratios are applied once and not per part:

* progress bar: `drawbox=x=0:y=ih-12:w=iw:h=12:color=black@0.35:t=fill` under the bar itself
* end card: an ASS overlay from the end-card text
* extra aspects: base branch 1080×1920 plus one branch per requested aspect, cropped as
  `1080×H` at y-offset `y0` — `ASPECTS = {"1:1": (1080, 1080, 320), "4:5": (1080, 1350, 190)}`
  (`clip.py:228`), where the third element is the crop y and is replaced by `0` when the clip is
  stacked
* encode `libx264 -preset medium -crf 18`, audio copied

Finally `render()` logs `ok … {total:.1f}s` and appends `"  WARN: outside 8-40 s"` when the result
is shorter than 8 s or longer than 40 s (`formats.py:255-256`). It returns a subprocess-like
`SimpleNamespace(returncode=0|1, stdout, stderr)` so the batch driver treats a format failure like
a failed `clip.py` (`formats.py:244-257`).

### 2.7 Card drawing

A card is a still, not a video: the last frame of the previous part (`-sseof -0.15 -frames:v 1`,
`formats.py:57`), blurred and darkened with
`scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:2,eq=brightness=-0.22:saturation=1.2`,
plus text at 30 fps with silent audio (`anoisesrc` pink noise band-passed at 1800 Hz in the source;
a plain `anullsrc` is fine for the port). Card text pops in: each line is drawn at
`size + size*0.35*max(0, 1 - t/0.12)`, i.e. 35 % oversized at t=0 and settled by 0.12 s, and the
lines are stacked with line spacing `size * 1.15`, the block vertically centred
(`formats.py:46-54`).

---

## 3. PeakCut today

What already exists and overlaps:

* `peakcut/studio/render.py:267` `render_clip(src, out_dir, name, clip, words, src_w, src_h) -> dict`
  already turns **one span** into a finished 1080×1920 mp4 + cover. It is the natural "render one
  part" primitive, and it already applies the caption style (`render.py:159` `build_ass`), the
  hook box (`render.py:128` `_hook_events`), the layout geometry (`render.py:112` `geometry`),
  the ffmpeg filter chain (`render.py:235` `_filter`) and the encode with QSV-then-libx264
  fallback (`render.py:289` `_render_in`). It also already normalises loudness once per clip with
  `-af loudnorm=I=-14:TP=-1.5:LRA=11`.
* `peakcut/studio/jobs.py:373` `render_one(job, clip, words)` is the only caller, at
  `jobs.py:386`: `out = render.render_clip(src, d / "clips", clip["id"], local, near, job["width"], job["height"])`.
* `peakcut/studio/jobs.py:345` `request_render(jid, cid, changes)` is the re-make path: it already
  has a per-key allow-list with truncation, clamps `start`/`end`, and validates
  `3 <= end-start <= 180`.
* `peakcut/studio/jobs.py:110` `DEFAULTS` / `jobs.py:114` `LIMITS` / `jobs.py:117` `clean_options`
  are the job-level option whitelist; `jobs.py:756-765` is where a clip dict is created.
* `peakcut/studio/brain.py:15` `SCHEMA` is the pick schema; `brain.py:120` `_tidy` is the only
  sanitiser a pick passes through.
* `peakcut/studio/facecam.py:329` `detect(path, ask=None) -> dict | None` knows where the webcam
  is (source pixels, `x/y/w/h` + `conf`) — that is the reveal/blur input.
* `peakcut/studio/media.py:80` `run(cmd, cwd=None, timeout=3600)`, `media.py:293` `probe`,
  `media.py:310` `extract_audio`, `media.py:317` `load_audio`, `media.py:323`
  `loudness_per_second` are the process/measurement primitives.
* `peakcut/studio/live.py:317` `_chat(channel)` already reads Twitch IRC chat for live jobs, and
  `live.py:355` `_chat_spike` already scores chat rate.
* `peakcut/web/index.html:2154` `drawClipDlg` + `index.html:2513` is the clip editor and its
  re-make POST; `server.py:582` `/api/status` already publishes `styles` and `layouts` for it.

The concrete gap:

1. **No notion of parts.** `render_clip` renders exactly one `[start, end]`; `request_render`
   edits one span; `brain._tidy` returns one span. Nothing in PeakCut can express "these three
   spans, in this order, with a card between them".
2. **No concat / no second encode pass.** `render.py:289` outputs a final file directly. There is
   no join, no per-part normalisation, no post-pass over a finished Short. `_render_in` applies
   `loudnorm` per clip, which is the wrong layer for a multi-part clip: five parts each
   normalised then concatenated pumps audibly.
3. **No static-frame/card builder.** `parts.card` has no equivalent. `render.py` can only burn ASS
   over moving video.
4. **No decoration layer.** There is nothing that draws a 100 px badge at (50, 215) for the whole
   clip, or a fill-to-`t0` bar, or a timed blur box.
5. **No payoff detection.** `peak_time` has no counterpart; PeakCut has per-second loudness for
   the *whole source* (`jobs.py:617`) but not for the part it just rendered.
6. **No chat fetch for VODs.** `live.py` reads live IRC only; a finished-job clip has no chat.
7. **One layout short for `reveal`.** `render.py:81` `LAYOUTS` is blur/zoom/crop/gameplay; the
   source's `stack` (facecam on top, game below, facecam panel exactly 620 px tall) does not exist.

---

## 4. Port plan

### 4.1 New modules

| path | concern |
| --- | --- |
| `peakcut/studio/formats.py` | format table, part planning, decoration plan, per-part render + join + final pass |
| `peakcut/studio/chat.py` | Twitch VOD chat fetch and bubble PNGs (only needed by `format == "chat"`) |

`render.py` gets **one** addition: the `stack` layout (4.7). Everything else is new files, so a
user who never picks a format runs the same code path as today.

### 4.2 Public surface of `peakcut/studio/formats.py`

```python
from pathlib import Path
from typing import Any, Iterable, Sequence

Clip = dict[str, Any]
Word = dict[str, Any]        # {"s": float, "e": float, "w": str, ...}
Span = dict[str, Any]        # {"start", "end", "label"?, "layout"?, "hook"?}
Chip = dict[str, Any]        # one thing drawn on one part

KINDS: tuple[str, ...]       # ("moment", "callback", "compilation", "escalation",
                             #  "thenvsnow", "reveal", "chat", "waitforit")
FORMATS: dict[str, dict]     # kind -> {"label": str, "needs_parts": int, "hint": str}
NEEDS_PARTS: dict[str, int]  # {"callback": 2, "compilation": 3, "escalation": 3, "thenvsnow": 2}

def public() -> list[dict]:
    """UI catalogue: [{"id","label","needs_parts","hint"}], no secrets, safe to send to any user."""

def fmt_of(clip: Clip) -> str:
    """clip['format'], else 'callback' if clip['parts'] else 'moment'. Raises ValueError on unknown."""

def check(clip: Clip) -> None:
    """Raise ValueError with a plain-language message if this clip cannot be rendered as its
    format: unknown format, too few parts, a part shorter than 2 s, a part outside the clip,
    more than 6 parts, a total under 3 s or over 180 s, a label longer than 24 chars."""

def spans(clip: Clip) -> list[Span]:
    """The ordered spans to render. Single-span formats return one span covering the clip.
    callback/compilation/escalation/thenvsnow return clip['parts'] normalised and validated."""

def chips(clip: Clip) -> list[Chip]:
    """The pure decoration plan, one list per span, no ffmpeg. Chip = {
        "kind": "card" | "badge" | "tag" | "bar" | "blur" | "flash" | "chat",
        "span": int,              # index into spans()
        "text": str,              # already clean_text()ed, "" for non-text chips
        "size": int,              # font size in px
        "color": str,             # "RRGGBB"
        "box": str | None,        # "RRGGBB@0.55" or None
        "t0": float | None,       # visible from, seconds in the part; None = whole part
        "t1": float | None,       # visible until
        "dur": float | None,      # card duration
        "lines": list[tuple[str, int, str]],   # card only: (text, size, colour)
    }
    This is the function the unit tests assert on; it must not touch ffmpeg."""

def peak_payoff(part: Path, clip: Clip, dur: float) -> float:
    """Seconds into `part` of the payoff. Order: clip['payoff'] -> loudest 50 ms in the last two
    thirds (media.extract_audio + media.load_audio + media.loudness_per_second) -> 0.6 * dur."""

def render_clip(src: Path, out_dir: Path, name: str, clip: Clip, words: Sequence[Word],
                src_w: int, src_h: int) -> dict:
    """Render a multi-part formatted clip. Same return shape as render.render_clip:
    {"file": f"{name}.mp4", "cover": f"{name}.jpg", "layout": str}. Raises RuntimeError /
    ValueError with user-facing text on failure."""
```

Internal helpers (not exported, but the build agent needs their exact shape):

```python
def _work_dir(out_dir: Path) -> Path
    # tempfile.mkdtemp(prefix="pkfmt") under the job dir, always rmtree'd; short path for Windows

def _render_part(src, work, index, span, clip, words, src_w, src_h) -> Path
    # calls render.render_clip(src, work, f"p{index}", part_clip, words, src_w, src_h)
    # part_clip = dict(clip, start=span["start"], end=span["end"], hook="", layout=span layout)
    # returns work / f"p{index}.mp4"
    # hook="" always: cards carry the hook text, a hook box on every part would repeat it

def _last_frame(part: Path, png: Path) -> Path          # -sseof -0.2 -frames:v 1
def _card(part: Path, chip: Chip, out: Path) -> Path     # still + ASS text + silence (4.4)
def _decorate(part: Path, chips: list[Chip], out: Path, fonts: Path) -> Path   # 4.4
def _concat(parts: list[Path], out: Path) -> Path        # 4.5
def _finish(out: Path, clip: Clip) -> None               # 4.5
def _cover(out: Path, png: Path, total: float) -> Path
```

### 4.3 Wiring into the existing pipeline

**Called by** `peakcut/studio/jobs.py:386`, replacing the single call with a two-way dispatch:

```python
# jobs.py, inside render_one(), replacing the line at jobs.py:386
if formats.fmt_of(clip) == "moment":
    out = render.render_clip(src, d / "clips", clip["id"], local, near, job["width"], job["height"])
else:
    out = formats.render_clip(src, d / "clips", clip["id"], local, near, job["width"], job["height"])
```

Nothing else in `render_one` changes: it still sets `status`, `version`, `error`, still writes
`clips/{id}.json`, still fires `on_clip_ready`. `formats.render_clip` must therefore return the
same dict keys (`file`, `cover`, `layout`) and raise the same kinds of exception that
`safe.friendly(e, 400)` (`safe.py:7`) already turns into user text.

**Must be called by** `jobs.request_render` (`jobs.py:345`) before the clip is queued: the
allow-list at `jobs.py:352-362` gains the format keys, then `formats.check(clip)` is called so a
bad part list is a 400 on the way in, not a failed render later:

```python
FMT_FIELDS = {"format": 20, "tag": 24, "word": 20, "jump": 24, "labels": 40,
              "reveal": 8, "payoff": 8, "squeeze": 8, "chat": 5}
```

* `format` must be in `formats.FORMATS`, else fall back to `DEFAULTS["format"]` (same rule as
  `style`/`layout` at `jobs.py:353-354`).
* `parts` is not a string field: validate it as a list of `{start, end, label?}` dicts, max 6,
  each `start`/`end` rounded to 2 dp and finite, `end > start`, each part inside the clip span.
* `jump_card` is a bool, `chat` a list of ≤5 strings of ≤40 chars each (each goes through
  `clean_text`).
* after merging, call `formats.check(clip)`; let `ValueError` bubble to the existing
  `(ValueError, TypeError) -> HTTPException(400)` at `server.py:950`.

**Must be called by** the job creation path (`jobs.py:756-765`) and option whitelist
(`jobs.py:110` `DEFAULTS`, `jobs.py:117` `clean_options`) if the format is chosen per job rather
than per clip: add `"format": "moment"` to `DEFAULTS`, validate it in `clean_options` against
`formats.FORMATS`, and copy `o["format"]` into the clip dict next to `style`/`layout` at
`jobs.py:757`. **Phase 1 can skip this** — per-clip editing in the clip dialogue is enough to ship
and keeps the AI path untouched.

**Must be called by** `peakcut/studio/server.py:582` `/api/status` so the SPA can offer the list:

```python
"formats": formats.public(),
```

**Must call** `render.render_clip` (per part), `render.install_fonts()`'s destination
`config.FONTS_DIR`, `media.run` (`media.py:80`) for every ffmpeg invocation — never
`subprocess.run` directly, so timeouts and error text stay consistent — and
`media.extract_audio` / `media.load_audio` / `media.loudness_per_second` in `peak_payoff`.

**Must not** be called from `live.py` in phase 1: a live clip has one span and no `parts`; the
format would have to be a per-session option (`live.py:624` calls `jobs.render_one` directly and
would keep working because `fmt_of` returns `"moment"`).

### 4.4 Drawing badges, tags and cards — ASS, not drawtext

The source draws everything with ffmpeg `drawtext`, which needs a bare relative font filename and
a `cwd` set to the font folder on Windows, and which breaks on `\ : ' %` (`formats.py:34-44`).
**Do not port drawtext.** PeakCut already ships an ASS pipeline with a font folder
(`render.py:289-321` copies `config.FONTS_DIR/*.ttf` into the work dir and passes
`ass=…:fontsdir=f`), and ASS gives timing, positioning and the pop animation for free. Write one
small ASS writer in `formats.py`:

```python
def _ass(events: list[Chip], height: int = 1920) -> str
```

* header identical to `build_ass`: `PlayResX 1080`, `PlayResY 1920`, `WrapStyle 2`,
  `ScaledBorderAndShadow yes` (`render.py:159-175`)
* one style `Badge` with `BorderStyle=3` (opaque box), `Shadow=0`, `Outline=<box padding>`,
  `BackColour` = box colour, `PrimaryColour` = text colour
* one style `Card` with `Alignment=5` (centred), used for cards and nothing else
* text escaping: strip `{`, `}` and `\` exactly like `render._clean` (`render.py:91`), and run the
  text through `formats._clean_text` (a PeakCut port of `parts.clean_text`, ASCII-safe superset)
* colour conversion helper, one place only:

```python
def _ass_colour(hex_rgb: str, opacity: float = 1.0) -> str:
    """'FFD400' -> '&H00D4FF&'; alpha byte is inverted: 0x00 opaque, 0xFF invisible,
    so opacity 0.55 -> &H73..." (0x73 == 115 == round(255 * (1 - 0.55)))."""
```

Mapping the source's graphics onto ASS events:

| source graphic | ASS |
| --- | --- |
| badge/tag, `x=50`, `y=215`, size `S`, colour `C`, box `B@o` | one Dialogue, `Badge` style, `{\an7\pos(50,215)\fs{S}\1c<C>\4c<B>\bord{int(S/4)}\t(0,120,\fscx100\fscy100)\fscx85\fscy85}`; start/end = the visible window |
| card line block | one Dialogue per line, `Card` style, `{\an5\pos(540,{y})\fs{S}\1c<C>\bord{int(S/14)+3}\3c&H000000&}`, y computed with the `size*1.15` stack |
| `enable='lt(t,R)'` (reveal tag) | Dialogue end time `R` |
| `enable='between(t,R,R+0.08)'` (flash) | not ASS — a `drawbox` in the filter chain (4.6) |
| `iw*min(t/t0,1)` bar | not ASS — a `drawbox` with an expression (4.6) |

The 0.08 s flash and the filling bar must stay ffmpeg filters: ASS cannot animate a box width
per frame without a `\p` drawing per frame.

### 4.5 Rendering one part, joining, finishing

`render_clip` pipeline, in order:

1. `check(clip)`, `parts = spans(clip)`, `work = _work_dir(out_dir)`.
2. Render each part with `render.render_clip` into `work` (sequentially; jobs already run up to 6
   clips in parallel at `jobs.py:662-663`, so parts must not add another thread pool on top).
3. Insert cards: for every `chip["kind"] == "card"`, `_last_frame(parts[i-1], work/f"f{i}.png")`
   then `_card(...)` → a `work/c{i}.mp4` of `chip["dur"]` seconds (0.9 s for the first card,
   0.6 s otherwise).
4. Decorate: `_decorate(part, chips_for_that_span, out, config.FONTS_DIR)` — one re-encode per
   part that adds the ASS overlay and, for reveal/waitforit, the extra filters (4.6). Parts with
   no chips skip this step entirely.
5. `_concat([...])` → `out_dir/{name}.mp4` (4.5.1).
6. `_finish(out, clip)` → optional progress bar, end card, extra aspect ratios (4.5.2).
7. `_cover(out, png, total)` → `{name}.jpg` at `min(1.2, total/2)`, `-q:v 3`.
8. `rmtree(work)` in a `finally`.
9. Return `{"file": f"{name}.mp4", "cover": f"{name}.jpg", "layout": <layout of span 0>}`.

#### 4.5.1 `_concat`

Port of `parts.join` (`parts.py:51-64`), which must be reproduced exactly:

```
ffmpeg -y -v error
  -i p0.mp4 -i c1.mp4 -i p1.mp4 …            # every segment, in order
  -filter_complex
    "[0:v]scale=1080:1920,fps=30,setsar=1,format=yuv420p[v0];[0:a]aresample=48000,aformat=channel_layouts=stereo[a0];
     … per input … ;
     [v0][a0][v1][a1]…concat=n=N:v=1:a=1[v][ac];
     [v][ac]loudnorm=I=-14:TP=-1.5:LRA=11,format=yuv420p[vo];[ac]anull[ao]"
  -map "[vo]" -map "[ao]"
  -c:v libx264 -preset medium -crf 18 -c:a aac -b:a 192k -ar 48000 -movflags +faststart out.mp4
```

`scale=1080:1920` without `force_original_aspect_ratio` is deliberate: every input is already
1080×1920, this only pins fps and SAR. **Cards must have an audio track** — an `anullsrc=r=48000:cl=stereo`
input mapped through, or `concat` will refuse the file. Two-pass loudnorm is optional in the port;
one-pass `loudnorm=I=-14:TP=-1.5:LRA=11` is acceptable, linear two-pass is better because the six
parts were cut from one source and their loudness differs only slightly.

#### 4.5.2 `_finish`

Only when the clip asks for it (all default off, so today's behaviour is untouched):

* `progress` truthy → `drawbox=x=0:y=ih-12:w=iw:h=12:color=black@0.35:t=fill` plus the yellow bar
  to `ih-12`; the source's `progress_bar` (`clip.py:494`) defaults to `FFE500`, h 12.
* `endcard` text → burn an ASS file with the text centred, for the last 2.5 s.
* `aspects` → re-crop into the extra sizes: `4:5` → `crop=1080:1350:0:190`,
  `1:1` → `crop=1080:1080:0:320`, y replaced by `0` when the clip is stacked.

### 4.6 The two graphical filters that cannot be ASS

**reveal** — applied in `_decorate` for the reveal span, over the part:

```
split[a][b];
[a]crop=1080:620:0:0,boxblur=45:3,eq=brightness=-0.35[bl];
[b][bl]overlay=0:0:enable='lt(t,{R:.2f})',
drawbox=x=0:y=0:w=iw:h=ih:color=white@0.45:t=fill:enable='between(t,{R:.2f},{R+0.08:.2f})'
```

`h = 620` is not arbitrary: it must equal the facecam panel height of the `stack` layout (4.7), so
the blur covers the facecam exactly and stops above the hook at y ≈ 680.

**waitforit** — applied for the waitforit span, `t0 = peak_payoff(...)`:

```
drawbox=x=0:y=170:w=iw:h=18:color=black@0.5:t=fill:enable='lt(t,{t0:.2f})',
drawbox=x=0:y=170:w='iw*min(t/{t0:.2f},1)':h=18:color=0xFFD400:t=fill:enable='lt(t,{t0:.2f})':replace=0,
drawbox=x=0:y=0:w=iw:h=ih:color=white@0.45:t=fill:enable='between(t,{t0:.2f},{t0+0.08:.2f})'
```

Always format these numbers with `:.2f` and a decimal point: `enable='between(t,5,5.08)'` works but
`between(t,5.20,5.28)` is locale-safe and matches the source.

**squeeze** (waitforit only): the source gets it from `clip.py`'s own `squeeze` option. PeakCut has
no equivalent, and adding one to `render.py` would change today's output. Port it as a
**pre-pass on the part's word list**, not on the video: with `squeeze > 0`, remove gaps longer than
`squeeze` from the span by splitting the span into sub-spans at those gaps and concatenating them
in `_concat` (each sub-span is just another `render.render_clip` call). Silence removal by
re-cutting is what the source does; re-timing captions against a squeezed video is not worth the
risk. `squeeze = 0` means "one span, no cuts".

### 4.7 The one change to `render.py` — the `stack` layout

`reveal` needs the facecam on top; PeakCut's `gameplay` layout puts it in the corner. Add a fifth
layout, isolated to three places:

* `render.py:81-82` `LAYOUTS["stack"] = "Facecam on top, gameplay below"`
* `render.py:112-125` `geometry`: `stack` behaves like `crop` for `fg_h` (`fg_h = H`) and returns
  `(layout, fg_h, 300, 1380)` — the hook stays clear of the 620 px panel either way
* `render.py:235-252` `_filter`: when `layout == "stack"` and a 4-tuple facecam is present

```
[0:v]crop={fx}:{fy_w}:{fx_x}:{fy_y},scale=1080:620:force_original_aspect_ratio=increase,crop=1080:620,setsar=1[fc];
[0:v]scale=1080:1300:force_original_aspect_ratio=increase,crop=1080:1300,setsar=1[gm];
[fc][gm]vstack=inputs=2,setsar=1[base]
```

(facecam cropped with the stored box, scaled to fill 1080×620; game cropped to 1080×1300; stacked
top-to-bottom = 1920). With no facecam, `stack` must fall back to `crop` exactly like
`gameplay` does at `render.py:277-278`, so a source without a webcam still renders.

If the build agent prefers to keep `render.py` untouched in phase 1, `reveal` must degrade to a
blur of the whole game area with no facecam promise, and the format must say so in `chips()` —
but the stacked version is the feature as designed.

---

## 5. Data files

### 5.1 Clip data (no new file — it lives in `job.json`)

The format is stored on the clip dict, which `jobs.public` already serialises. New optional keys,
all absent for a plain moment:

```json
{
  "format": "compilation",
  "parts": [
    {"start": 712.4, "end": 723.9, "label": "the 3rd"},
    {"start": 1204.0, "end": 1216.5},
    {"start": 1588.2, "end": 1601.0}
  ],
  "tag": "EARLIER",
  "jump_card": true,
  "jump": "40 MINUTES LATER",
  "word": "STRIKE",
  "labels": ["THEN", "NOW"],
  "reveal": 1.6,
  "payoff": 6.4,
  "squeeze": 1.5,
  "chat": ["KEKW", "no way"]
}
```

Rules the server must enforce on the way in (`formats.check`):

| field | type | limit |
| --- | --- | --- |
| `format` | str | one of `formats.FORMATS`; unknown falls back to `DEFAULTS["format"]` |
| `parts` | list | 2-6 entries for multi-part formats; each `{start, end}` finite, `end > start`, `end - start >= 2`; total 3-180 s (matches `jobs.py:357`) |
| `tag`, `jump`, `word` | str | ≤ 24 chars after `clean_text` |
| `labels` | list[str] | exactly 2 strings ≤ 16 chars |
| `reveal` | float | 0.3-6.0, default 1.6 |
| `payoff` | float | 0.5 ≤ payoff ≤ span duration |
| `squeeze` | float | 0-5, default 1.5 |
| `chat` | list[str] | ≤ 5 × 40 chars |

`jobs.public` needs no change: none of these keys is secret. `HIDDEN` (`jobs.py:145`) already
covers the paths.

### 5.2 Optional site-wide default — `config.DATA_DIR / "formats.json"`

Only if an admin panel is built. Follow `peakcut/studio/ai.py` exactly (`_lock`, `_saved` mtime
cache, `_file()`, `public()`, `save()` with `tmp` + `os.chmod(tmp, 0o600)` + `replace`).

```json
{
  "default": "moment",
  "enabled": ["moment", "callback", "reveal", "waitforit", "chat"],
  "chat": {"allow_network": false, "rows": 5}
}
```

Schema: `default` ∈ `formats.FORMATS`; `enabled` ⊆ `formats.FORMATS` and must contain `default`;
`chat.allow_network` (bool, default **false**) is the only switch that lets a job contact
`gql.twitch.tv`. Routes would follow the transcription block (`server.py:1350-1360`):
`GET /api/formats` with `_admin()` + `formats.public()`, `PUT /api/formats` with `_admin()`,
`_throttle("formats:" + ctx.uid(), 20, 600)` and `HTTPException(400, str(e))` on `ValueError`.
If this file is not built, `formats.FORMATS` in code is the catalogue and `enabled` is everything.

### 5.3 Chat bubble assets

No new font and no new asset: bubbles are drawn with `PIL` using
`config.FONTS_DIR / render.FONT_FILES["Poppins ExtraBold"]` at 56 px shrinking to 44 px, into a
PNG in the part's work dir that is deleted with it. Nothing is cached on disk between clips.

---

## 6. Risks

* **Module globals that assume one user.** The source keeps `_LAST` (thread → last part, so the
  final pass can read the caption y), `_LOCKS` (per-key render locks) and `_SWEPT` (cache sweep
  once per process) at module level. In PeakCut they would be shared across users and across
  parallel jobs, and `_LAST` would leak one user's render metadata into another's clip. Pass state
  explicitly instead; no module-level dict keyed by anything but a path inside the job's own
  folder.
* **Caching across users.** The source's `part_mp4` cache is keyed by an md5 of the arguments and
  lives next to the output. In a server that cache is a privacy hole (two users with the same
  source URL and times share a file) and a correctness hole (different `facecam`, different
  fonts). Phase 1: no cross-clip cache at all; the work dir dies with the render.
* **Per-part loudnorm then concat.** Concatenating five independently normalised parts pumps
  audibly. Normalise once, at `_concat`, and keep `render_clip`'s own `-af loudnorm` (it is
  harmless but redundant per part; do not remove it, other features rely on it).
* **Heterogeneous segments fail concat.** `render.py` does not force fps or SAR; a 25 fps source
  and a 30 fps card will not concat. Every segment must pass through
  `scale=1080:1920,fps=30,setsar=1,format=yuv420p` and
  `aresample=48000,aformat=channel_layouts=stereo`.
* **No `cv2`.** `clip.has_face` uses OpenCV; `requirements.txt` has no opencv. Port the face gate
  onto `facecam.detect` (`facecam.py:329`) with `ask=None` so it never calls the AI. `None` means
  "degrade to a plain moment", which is the source's own behaviour when the detector throws.
* **Drawtext porting.** Escaping (`\ : ' %`), the bare font filename and the Windows `cwd` trick
  are three separate failure modes. Use ASS for all text and `drawbox` for all geometry.
* **Disk and time.** A 5-part compilation is ~7 encodes of the same span (5 parts + 2 cards) plus
  concat, loudnorm and the finish pass. `_wait_for_clips` (`jobs.py:426`) kills a clip after
  `PEAKCUT_CLIP_MINUTES` = 15 min; scale that by part count or the first 5-part compilation on a
  slow box will be reported as failed. `account.delete_clip` (`account.py:27`) must also remove
  any `{cid}.part*`/`{cid}-card*` leftovers.
* **AI schema.** `brain.SCHEMA` (`brain.py:15`) is strict; making `parts` required would break
  every existing pick and every provider that validates the schema. Add `format` and `parts` as
  **optional** properties only, and keep `_tidy` (`brain.py:120`) tolerant: drop `parts` unless it
  validates, and fall back to `moment`.
* **Twitch GQL.** No auth, rotating persisted-query hash, undocumented, and rate limited. Off by
  default (`chat.allow_network` false), and `format == "chat"` must accept user-supplied lines so
  the feature works with no network at all. `chat.py` must use `httpx` (already a dependency) with
  an explicit timeout — never the blocking default.
* **Untrusted text.** Chat lines and part labels come from video/chat, i.e. from strangers:
  `clean_text` on the way in, `_clean` (strip `{}` `\`) before any ASS event, length caps in
  `check()`, and never interpolate a label into an ffmpeg argument.
* **Windows path length.** Every intermediate file is one more path segment; use
  `tempfile.mkdtemp(prefix="pkfmt")` exactly the way `render.py:283` does, and delete it in a
  `finally`.

---

## 7. Verification

```bash
cd peakcut

# 1. Unit level: the decoration plan, no ffmpeg involved.
python tests/test_formats.py

# 2. One real render end to end (4 s of generated pattern, 2 parts + 1 card).
python - <<'PY'
import os, tempfile, json, subprocess
from pathlib import Path
os.environ["PEAKCUT_DATA"] = tempfile.mkdtemp(prefix="pcfmt-")
os.environ["DATABASE_URL"] = ""
os.environ["PEAKCUT_ACCOUNTS"] = "0"
from studio import formats
d = Path(os.environ["PEAKCUT_DATA"]); src = d / "src.mp4"
subprocess.run(["ffmpeg","-y","-v","error","-f","lavfi","-i",
                "testsrc2=size=1280x720:rate=30:duration=12",
                "-f","lavfi","-i","sine=frequency=440:duration=12",
                "-shortest","-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac",str(src)], check=True)
clip = {"id":"t","format":"compilation","hook":"3 TIMES KAI LOST IT","style":"bounce",
        "layout":"blur","captions":True,
        "parts":[{"start":0.5,"end":3.0,"label":"the first"},
                 {"start":4.0,"end":6.5},
                 {"start":7.0,"end":9.5}]}
words = [{"s":i*0.4,"e":i*0.4+0.35,"w":f"w{i}"} for i in range(30)]
out = formats.render_clip(src, d/"clips", "t", clip, words, 1280, 720)
print(json.dumps(out, indent=1))
for f in ("t.mp4","t.jpg"):
    assert (d/"clips"/f).exists(), f
PY

# 3. Structural check on the result: 6 segments joined, one video stream, sane duration.
ffprobe -v error -show_entries format=duration -of csv=p=0 <data>/clips/t.mp4     # ≈ 10.6 s
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,nb_frames \
        -of default=nw=1 <data>/clips/t.mp4                                      # 1080x1920, 30/1
ffprobe -v error -show_entries stream=codec_type -of csv=p=0 <data>/clips/t.mp4  # video + audio

# 4. No regression for a user who never picks a format.
python tests/run.py          # every existing suite must stay green; test_captions is the guard
```

`tests/test_formats.py` must assert, at minimum:

* `fmt_of({}) == "moment"`, `fmt_of({"parts": [1]}) == "callback"`,
  `fmt_of({"format": "chat"}) == "chat"`, and `ValueError` for `{"format": "nope"}`.
* `check()` rejects `{"format": "compilation", "parts": [{}]}` with a message containing
  `"needs at least 3 parts"`, and rejects a part shorter than 2 s.
* `chips()` for `compilation` with 3 parts yields `#3`, `#2`, `#1` in that order, the first card
  `0.9` s and the rest `0.6` s, badge text equal to the card text.
* `chips()` for `escalation` with `word="STRIKE"` and 3 parts yields `STRIKE 3/3` badges with
  colours `FFFFFF`, `FF9500`, `FF3B30`.
* `chips()` for `thenvsnow` yields `THEN` then `NOW`, colours `FFD400` then `FF3B30`.
* `clean_text("Kai's #3, 2/3!") == "KAIS #3 2/3!"` and
  `clean_text("Café Ñandú مرحبا") == "CAFÉ ÑANDÚ مرحبا"`.
* `chips()` for `callback` with an 11-minute gap produces the `EARLIER` tag, with a 9-minute gap
  and no `tag` produces nothing, and with `jump_card` produces a card whose text is
  `"40 MINUTES LATER"`.
* `peak_payoff()` returns `clip["payoff"]` verbatim when given, and otherwise a value strictly
  inside `(dur/3, dur)`.
* `_ass_colour("FFD400", 0.55)` starts with `&H73` and `_ass(...)` output contains no `{` from the
  text and no `drawtext=`.
