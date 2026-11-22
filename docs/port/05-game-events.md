# 05 — Game event OCR (WASTED, BUSTED, MISSION PASSED, wanted stars, hard cuts)

Source: `gta6-clipper-main/vision.py` (224 lines). Host: `peakcut/`.

---

## 1. What it does

While a gameplay video is being read, PeakCut also watches the picture: roughly once a second it OCRs the
centre band of the frame and looks for the big centred banners games put on screen when something decisive
happens — WASTED, BUSTED, MISSION PASSED, MISSION FAILED, HEIST PASSED/FAILED, VICTORY ROYALE, ELIMINATED,
GAME OVER, YOU DIED, VICTORY, DEFEAT, CHAMPION — fuzzily, so an OCR slip like `BUSTEO` still counts. Any
large, centred, all-caps text it does not recognise is recorded as generic `TEXT …` at lower weight, which is
how a brand-new game with no table entry still produces events. It can additionally count GTA-5 wanted stars
and record hard scene cuts.

Repeated sightings of the same label inside 15 seconds collapse into one event with a start, an end and a hit
count, so a banner held on screen for four seconds is one event, not four. Those events are then attached to
the transcript lines that fall under them, which is the whole point: the AI clip picker reads a transcript
where the line under a death now carries `(GAME WASTED)`, and it stops needing to be told that dying is
interesting.

The feature is off by default, wanted stars are off even when it is on, and if the OCR engine is not installed
the job runs exactly as it does today.

---

## 2. Exact mechanics

### 2.1 The label table

`gta6-clipper-main/vision.py:11-18`. Label → (accepted phrases, heat weight 0–1). Phrases are matched
fuzzily, so the list is the set of spellings the game actually draws, not a strict enum.

| label | phrases | weight |
|---|---|---|
| `WASTED` | `WASTED` | 0.8 |
| `BUSTED` | `BUSTED` | 0.7 |
| `MISSION PASSED` | `MISSION PASSED`, `MISSION COMPLETE` | 0.7 |
| `MISSION FAILED` | `MISSION FAILED` | 0.7 |
| `HEIST PASSED` | `HEIST PASSED`, `HEIST COMPLETE` | 0.8 |
| `HEIST FAILED` | `HEIST FAILED` | 0.7 |
| `VICTORY ROYALE` | `VICTORY ROYALE` | 0.8 |
| `ELIMINATED` | `ELIMINATED`, `YOU ELIMINATED` | 0.5 |
| `GAME OVER` | `GAME OVER` | 0.6 |
| `YOU DIED` | `YOU DIED` | 0.7 |
| `VICTORY` | `VICTORY` | 0.6 |
| `DEFEAT` | `DEFEAT` | 0.5 |
| `CHAMPION` | `CHAMPION`, `YOU ARE THE CHAMPION` | 0.6 |

Weights for the three non-word event kinds, `gta6-clipper-main/vision.py:19`:

```python
W_STARS, W_CUT, W_TEXT = .5, .3, .35   # wanted-star rise, hard scene cut, unknown big centre text
```

Dict order is load-bearing: `match_word` returns the **first** label that matches, so `VICTORY ROYALE` must be
tested before `VICTORY` and `MISSION PASSED` before any hypothetical bare `PASSED`. The table above is in
source order; keep it.

### 2.2 Normalising and fuzzy matching

`gta6-clipper-main/vision.py:32`:

```python
def norm(s): return re.sub(r"[^A-Z ]", "", s.upper()).strip()
```

Uppercase, then delete everything that is not `A-Z` or space, then strip. Digits, punctuation, newlines and
accented letters all disappear; internal runs of spaces are **not** collapsed, so `"A  B"` stays two spaces.

`gta6-clipper-main/vision.py:35-44`:

```python
t = norm(txt)
if len(t) < 4: return None
for lab, (phr, _) in WORDS.items():
    for p in phr:
        n = len(p.split()); tk = t.split()
        cands = [t] + [" ".join(tk[i:i + n]) for i in range(max(1, len(tk) - n + 1))]
        if any(difflib.SequenceMatcher(None, c, p).ratio() >= .8 for c in cands): return lab
```

- Strings shorter than 4 characters after `norm` are never matched (kills stray glyphs).
- Two candidate shapes: the whole normalised string, and every **same-word-count** window of it. For a
  two-word phrase like `MISSION PASSED` (n=2) against OCR text of five tokens, windows `[0:2] [1:3] [2:4] [3:5]`
  are tried — this is what lets a banner be found inside a line that also OCR'd a HUD element.
- `difflib.SequenceMatcher(None, c, p).ratio() >= .8` — a plain character-level similarity, no token order
  awareness. `BUSTEO` vs `BUSTED` = 5/6 ≈ 0.83 → match. `MISSION PASSEO!` normalises to `MISSION PASSEO`
  vs `MISSION PASSED` = 13/14 ≈ 0.93 → match. `hello world` normalises to `HELLO WORLD`, best ratio against
  any phrase is far below .8 → `None`.
- Note the comparison is case-sensitive against the already-uppercased candidates, and the phrases in the
  table are stored uppercase. Do not lowercase the table.

### 2.3 Colour cues

`gta6-clipper-main/vision.py:47-54`. Cheap, no OCR, used both to gate OCR and to enrich an event.

```python
h, w = bgr.shape[:2]; band = bgr[int(h * .25):int(h * .75)]
hsv = cv2.cvtColor(band, cv2.COLOR_BGR2HSV); H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
full = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
return {"sat": float(full[..., 1].mean()) / 255,
        "gold": float(((H > 15) & (H < 35) & (S > 110) & (V > 170)).mean()),
        "red": float((((H < 8) | (H > 172)) & (S > 140) & (V > 120)).mean())}
```

- `sat` is the **mean saturation of the whole frame** divided by 255, in 0–1. A normal gameplay frame sits
  around 0.4–0.7; a desaturated/death-grey frame drops well under that.
- `gold` and `red` are **fractions of pixels in the centre band** (0–1), using OpenCV's 8-bit HSV ranges:
  H 0–180, S 0–255, V 0–255. Gold = H 16–34, S ≥ 111, V ≥ 171. Red = H ≤ 7 or H ≥ 173, S ≥ 141, V ≥ 121.
- The `sat` value is computed from `full` while `gold`/`red` come from `band` — an inconsistency in the
  source, harmless, but reproduce it exactly or the cue thresholds below will not line up.

### 2.4 Finding banners in one frame

`gta6-clipper-main/vision.py:57-65`:

```python
h, w = bgr.shape[:2]; y0, x0 = int(h * .2), int(w * .08)
for box, txt, sc in ocr(bgr[y0:int(h * .8), x0:int(w * .92)]):
    ys = [p[1] for p in box]; xs = [p[0] for p in box]
    rh = (max(ys) - min(ys)) / h; cx = (np.mean(xs) + x0) / w
    out.append((match_word(txt) if float(sc) > .6 else None, txt, float(sc), rh, cx))
```

- OCR is run on the crop `y ∈ [0.20h, 0.80h)`, `x ∈ [0.08w, 0.92w)` — the middle 60 % × 84 % of the frame.
  HUD at the edges and the very top/bottom are excluded on purpose.
- `rh` is the detected text box height **as a fraction of the full frame height** (not of the crop).
- `cx` is the box's mean x, converted back to full-frame coordinates and divided by width.
- Confidence gate `> .6`: below that the text is returned with `label=None` and can never be a word event.
- The function's docstring says it returns 4-tuples; it actually returns 5 (it also yields `cx`).
  `detect_frame` unpacks five.

`ocr()` — `gta6-clipper-main/vision.py:23-29`:

```python
global _ocr
if _ocr is None:
    from rapidocr_onnxruntime import RapidOCR
    _ocr = RapidOCR()
n_ocr[0] += 1; r, _ = _ocr(img, use_cls=False)
return r or []
```

A process-wide lazy singleton, `use_cls=False` (no text-direction classifier — banners are horizontal), and
`None` coerced to `[]`. Each element is `(box, text, score)` with `box` a list of four `(x, y)` points.
`n_ocr[0]` is only a debug counter.

### 2.5 Deciding what a frame contains

`gta6-clipper-main/vision.py:68-76`:

```python
ev = []; cc = colour_cues(bgr)
for lab, txt, sc, rh, cx in banners(bgr):
    if lab: ev.append(("word", lab, {"text": txt, "conf": round(sc, 2), "cues": cc}))
    elif rh >= .06 and sc > .85 and .3 < cx < .7 and len(norm(txt).replace(" ", "")) >= 4 \
            and sum(c.isupper() for c in txt) >= .8 * sum(c.isalpha() for c in txt):
        ev.append(("text", "TEXT " + norm(txt), {"text": txt, "conf": round(sc, 2), "cues": cc}))
```

The generic-text gate, every clause required:

| clause | value | meaning |
|---|---|---|
| `rh >= .06` | 6 % of frame height | big text, not a caption |
| `sc > .85` | OCR confidence | stricter than the .6 used for known words |
| `.3 < cx < .7` | horizontal centre | banner is centred |
| `len(norm(txt).replace(" ", "")) >= 4` | 4 characters | reject glyph noise |
| `sum(c.isupper() for c in txt) >= .8 * sum(c.isalpha() for c in txt)` | ≥ 80 % caps | all-caps banner, not a sentence |

Note the uppercase test runs on the **raw** `txt`, not on `norm(txt)`; a banner in a script without case
(`MISSION PASSED` in Japanese, or digits) has `sum(isalpha)==0` and would divide into a vacuous `0 >= 0`.
Guard the denominator in the port (see §6).

### 2.6 Wanted stars (off by default)

`gta6-clipper-main/vision.py:79-86`:

```python
h, w = bgr.shape[:2]; roi = bgr[int(h * .1):int(h * .24), int(w * .72):]
hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
m = ((hsv[..., 0] > 15) & (hsv[..., 0] < 32) & (hsv[..., 1] > 120) & (hsv[..., 2] > 190)).astype(np.uint8)
n, _, st, _ = cv2.connectedComponentsWithStats(m)
a = [s for s in st[1:] if .0004 * h * w < s[4] < .004 * h * w and .6 < s[2] / max(s[3], 1) < 1.5]
return len(a) if len(a) <= 5 else 0
```

- ROI: top 10 %–24 % of height, right 28 % of width — the GTA-5 HUD strip.
- Mask: H 16–31, S ≥ 121, V ≥ 191 (bright yellow).
- Keep connected components whose **area** is between 0.04 % and 0.4 % of the whole frame, and whose
  bounding-box aspect `w/h` is between 0.6 and 1.5 (star-shaped, not a bar).
- More than 5 survivors is treated as a HUD it does not understand → `0`, not a count.

`gta6-clipper-main/vision.py:130` records why it is off:

```python
n = stars(f) if STARS else 0   # off by default: test showed 6/7 false hits (stream chat/overlay in the corner)
```

Six of seven detections on real VODs were a chat overlay or a stream graphic sitting in that corner. Keep it
off by default and expose it only as an explicit opt-in.

Rise-only recording, `gta6-clipper-main/vision.py:131-134`: an event is emitted only when the count
**increases** (`if n != last_n and n: if n > last_n: …`), and `last_n` resets to 0 when the count reaches zero.

### 2.7 The scan loop

`gta6-clipper-main/vision.py:109-136`. Signature:

```python
def scan(path, t0=0.0, fps=1.0, grabs=None, sweep=4):
```

1. **Sampling.** `vf = cap.get(cv2.CAP_PROP_FPS) or 30`; `step = max(1, round(vf / fps))`. At the default
   `fps=1.0` and 30 fps source this is every 30th frame. Frames are consumed with `cap.grab()` and only
   decoded (`cap.retrieve()`) on sampled indices.
2. **Timestamp.** `t = t0 + i / vf`, absolute seconds in the source's own time base. `t0` is the window start,
   so events come out in absolute video time and line up with transcript seconds.
3. **Downscale.** `gta6-clipper-main/vision.py:117`:
   `f = cv2.resize(f, (640, int(f.shape[0] * 640 / f.shape[1]))) if f.shape[1] > 640 else f`
   Width capped at 640, aspect preserved, never upscaled. Nothing downstream assumes a height.
4. **Hard cut.** `gta6-clipper-main/vision.py:120-121`:

   ```python
   hist = cv2.calcHist([cv2.cvtColor(f, cv2.COLOR_BGR2HSV)], [0, 1], None, [16, 8], [0, 180, 0, 256])
   hist = cv2.normalize(hist, hist).flatten()
   if prev_h is not None and cv2.compareHist(prev_h, hist, cv2.HISTCMP_BHATTACHARYYA) > .55:
       raw.append((t, "cut", "CUT", {}, f))
   ```

   A 2-D histogram over **H (16 bins, 0–180) × S (8 bins, 0–256)**, L1-normalised, compared with the
   Bhattacharyya distance. Threshold **0.55**. V is deliberately ignored so a fade-to-black or a brightness
   pump does not read as a cut. One cut at most per sampled frame, and the cut is recorded even if OCR is
   skipped this frame.
5. **Motion band.** `gta6-clipper-main/vision.py:123`:
   `band = cv2.resize(f[int(f.shape[0] * .2):int(f.shape[0] * .8)], (80, 40)).astype(np.int16)`
   The centre 60 % of height, squashed to 80×40, kept as int16 so the later difference does not wrap.
6. **Rolling saturation baseline.** `sats.append(cc["sat"]); sats[:] = sats[-40:]` — the last **40** sampled
   frames, i.e. ~40 s at 1 fps.
7. **The OCR gate.** `gta6-clipper-main/vision.py:125`:

   ```python
   cue = cc["gold"] > .006 or cc["red"] > .004 or cc["sat"] < .6 * float(np.median(sats))
   ```

   | threshold | value | what it catches |
   |---|---|---|
   | `gold > .006` | 0.6 % of centre-band pixels | gold mission text |
   | `red > .004` | 0.4 % of centre-band pixels | red WASTED text |
   | `sat < 0.6 × median(sats)` | 40 % desaturation | the grey-out of a death screen |

   Then `gta6-clipper-main/vision.py:127`:

   ```python
   if (cue or n_s % sweep == 0) and (prev_band is None or np.abs(band - prev_band).mean() > 6):
       for k, lab, ex in detect_frame(f): raw.append((t, k, lab, ex, f))
       prev_band = band
   ```

   OCR runs when a colour cue fired **or** every 4th sampled frame (`sweep=4`), **and** the 80×40 centre band
   moved by a mean absolute difference greater than **6** (on 0–255 channel values) since the last OCR.
   The motion test is what keeps a static banner from being OCR'd 60 times; `prev_band` is only updated on
   the frames that actually OCR, so slow drift accumulates until it crosses 6.
   `gta6-clipper-main/vision.py:126` documents the cost: *"OCR is slow (~1 s/frame loaded)"*.
8. **Stars**, per §2.6.
9. **Progress.** Every 60 sampled frames, one stderr line with `t`, `ocr_frames` and `raw` count.

`scan` returns `raw`, a list of `(t, kind, label, extra, frame)` tuples. The frame is carried so `merge` can
write a JPEG grab; it is the last element and is not part of the event.

### 2.8 Merging

`gta6-clipper-main/vision.py:139-152`. Signature `merge(raw, gap=15, grabs=None)`, docstring:

> same label within `gap` s = one event (first time); a word seen once at conf<.8 is dropped unless a colour
> cue agrees

```python
for t, k, lab, ex, f in sorted(raw, key=lambda r: r[0]):
    if lab in last and t - last[lab]["t_end"] <= gap:
        last[lab]["t_end"] = t; last[lab]["hits"] += 1; continue
    e = {"t": round(t, 1), "t_end": round(t, 1), "kind": k, "label": lab, "hits": 1, **{a: b for a, b in ex.items()}}
    if k == "word": e["weight"] = WORDS[lab][1]
    else: e["weight"] = {"stars": W_STARS, "cut": W_CUT, "text": W_TEXT}[k]
```

- Sorted by time first; the list is then walked once.
- `gap = 15` seconds. A sighting at `t` extends the open event if `t - t_end <= 15`; otherwise it opens a new
  one. So a WASTED at 10 s and another at 22 s are one event `t=10.0, t_end=22.0, hits=2`; at 26 s it would
  be two.
- Dedupe key is the **label string alone**, shared across kinds. Consequence: every `CUT` within 15 s of the
  previous `CUT` merges, which is why the transcript tagger skips cuts. `TEXT …` labels differ by content so
  they do not collide, and `STARS 2` / `STARS 3` are distinct labels.
- Event fields: `t` (first sighting, 1 decimal), `t_end` (last sighting, 1 decimal — re-rounded in a final
  pass at `gta6-clipper-main/vision.py:151`), `kind` ∈ `word|text|cut|stars`, `label`, `hits`, `weight`,
  plus whatever `extra` carried: `text`, `conf`, `cues` for word/text, `stars` for stars.
- `grabs` writes one JPEG per event named `{int(t)}_{re.sub(r'[^A-Za-z0-9]+', '_', lab)}.jpg` and stores the
  filename under `e["grab"]`. This is a debugging aid; the PeakCut port should use the job directory, not a
  module-relative folder.

### 2.9 Tagging the transcript

`gta6-clipper-main/vision.py:155-184`. Docstring:

> add ` [GAME WASTED]` to the transcript line at each event's time (nearest line start within `slack` s) and
> bump `[HEAT]`. Lines look like `[36001.3-36010.9] text [LOUD +17dB] [HEAT 40]`. Idempotent. Keeps a `.bak`
> of the original.

1. **Parse the lines.** `re.match(r"\[([\d.]+)-([\d.]+)\]", l)` on each line of the transcript file; every
   match yields a span `(start, end, line_index)`.
2. **Which events are allowed into the text.** `gta6-clipper-main/vision.py:166`:

   ```python
   if e["kind"] == "cut" or (e["kind"] == "text" and e["hits"] < 3) or (e["kind"] == "stars" and e["stars"] < 3): continue
   ```

   Cuts never tag. Generic text must have been seen at least **3** times (a real banner persists; a passing
   sign does not). Stars must have reached at least **3** at some point. Word events always tag.
3. **Which line.** `slack = 8` seconds. Candidates are spans with `s[0] - slack <= e["t"] <= s[1] + slack`.
   If none, the event is dropped. The chosen line minimises
   `0 if s[0] <= e["t"] <= s[1] else min(abs(e["t"] - s[0]), abs(e["t"] - s[1]))` — containment wins, then
   the nearest edge. Ties resolve to the earlier span because `min` keeps the first.
4. **Writing the tag.** For each chosen line, per event in list order:
   `tag = f"[GAME {e['label']}]"`; skip if already present (this is the idempotence); otherwise
   `l = re.sub(r" \[HEAT \d+\]", "", l) + " " + tag` — the old `[HEAT n]` is **stripped** and the tag appended
   at the very end of the line.
5. **Recomputing heat.** `gta6-clipper-main/vision.py:177`:

   ```python
   if l != n0: l += f" [HEAT {chat.heat(l)}]"
   ```

   If the line changed, `[HEAT {chat.heat(l)}]` is appended; if it did not, the original line is restored
   byte for byte. The comment on that line: *"one formula (chat.heat, noisy-or over every tag on the line): a
   banner line never ranks below its LOUD-only neighbour"*.

`chat.heat` — `gta6-clipper-main/chat.py:190-203`. A 0–100 noisy-or over tags already on the line:

```python
if m := re.search(r"\[LOUD \+(\d+)dB", line): P.append(min(1, int(m[1]) / 15) * .6)
if m := re.search(r"\[CHAT x([\d.]+)", line): P.append(min(1, float(m[1]) / 6) * .8 + (.1 if '"' in line else 0))
if m := re.search(r"\[CLIPPED x(\d+) ([\d.]+)(k?) views", line):
    v = float(m[2]) * (1000 if m[3] else 1); P.append(min(1, .35 + .15 * math.log10(max(v, 1) / 100) + .05 * (int(m[1]) - 1)) * .9)
if m := re.search(r"\[REPLAYED x(\d+)", line): P.append(min(1, int(m[1]) / 8) * .8)
if re.search(r"\[GAME (WASTED|BUSTED|MISSION FAILED|MISSION PASSED|HEIST PASSED|HEIST FAILED|VICTORY|ELIMINATED|GAME OVER|YOU DIED|DEFEAT|CHAMPION)", line): P.append(.6)
elif "[GAME " in line: P.append(.2)
q = 1
for x in P: q *= 1 - max(0, min(x, .95))
return round(100 * (1 - q))
```

Two things a port must not miss: the `GAME` contribution is a flat **0.6** for the twelve labels in that
regex and only **0.2** for anything else — `VICTORY ROYALE` and every `TEXT …` label fall into the 0.2 branch
because they are not listed. And each probability is clamped to 0.95 before the product, so the result never
reaches 100.

6. **Persistence.** The `.bak` is written once, only if absent; the file is then overwritten and the new text
   returned. `write=False` returns without touching disk.

### 2.10 Frame extraction and the cost budget

The source decodes with OpenCV. In PeakCut the convention is ffmpeg (`peakcut/studio/facecam.py:48`), which
already works everywhere PeakCut works:

```
ffmpeg -v error -i <path> -vf fps=<rate>,scale=640:-2 -frames:v <count> -f rawvideo -
```

`-f rawvideo -` writes packed BGR24 frames to stdout with no container; slice at `h*w*3` bytes per frame.
`facecam._frames` shows the read pattern (`np.frombuffer(...).reshape(n, h, w)`) and — importantly — returns
an empty array instead of raising when ffmpeg is missing, so the caller degrades.

Measured cost, from the source: **"7-20 minutes per hour of stream"** (`SKILL-REFERENCE.md:31`) and
**"~1 s/frame loaded"** for OCR (`gta6-clipper-main/vision.py:126`). Budget accordingly: the cue gate plus the
motion gate are what hold that to 7–20 minutes rather than 60 × 60 OCR calls.

### 2.11 Command-line shape (for parity testing only)

`gta6-clipper-main/vision.py:217-224`: `vision.py <file|url> [START-END] [--fps 1] [--grabs DIR] [--stars]
[--tag clips/src/<id>.txt] [--selftest]`. `parse_win` (`vision.py:89-94`) accepts `h:mm:ss-h:mm:ss` or plain
seconds by summing `s = s*60 + v` over `:`-split parts. `run` (`vision.py:187-194`) writes
`{"src", "window", "fps", "events", "scan_s"}` to `clips/src/<vid>.events.json`. The PeakCut port needs none
of the CLI or the yt-dlp fetch (§2.12) — PeakCut already has the file on disk.

### 2.12 The yt-dlp section is not ported

`gta6-clipper-main/vision.py:97-106` downloads only the requested window at `best[height<=360]/worst` with
`--force-keyframes-at-cuts` and `--download-sections *%d-%d`. PeakCut already has `media.download_section`
(`peakcut/studio/media.py:266`) and `jobs._fetch_piece` (`peakcut/studio/jobs.py:492`), which download a padded
per-clip section and recover the exact offset with `media.find_offset`. Do not port `fetch`.

The 360p point still matters: OCR accuracy and time both scale with resolution, so the port must downscale to
640 wide before the colour maths and before OCR, exactly as the source does at `vision.py:117`.

---

## 3. PeakCut today

### 3.1 There is no OCR and no computer vision at all

`grep -rn "cv2\|opencv\|rapidocr\|pytesseract\|ocr" --include=*.py .` over `peakcut/` returns **zero hits**.
`peakcut/requirements.txt` does not list opencv, onnxruntime or any OCR engine:

```
fastapi==0.162.5  httpx==0.28.1  numpy==2.2.6  psycopg==3.3.9  psycopg-binary==3.3.9
python-multipart==0.0.32  sherpa-onnx==2.0.1  soundfile==0.14.0  SQLAlchemy==2.0.57
uvicorn==0.54.0  yt-dlp==2026.10.21  pillow==11.3.0
```

The one place PeakCut looks at pixels is `peakcut/studio/facecam.py`, and it does so with ffmpeg + numpy
only: `_frames` at `peakcut/studio/facecam.py:48` pulls up to `MAX_FRAMES = 24` grey 320×180 frames through
`-f rawvideo -`. `peakcut/studio/render.py:60` imports `PIL.ImageFont` only to measure text. Nothing reads a
frame's colours.

### 3.2 The closest existing thing is the static/ad-break detector, and it is a different metric

`peakcut/studio/quality.py:32` `motion_map(path, bucket=2.0)` runs
`ffmpeg -vf tblend=all_mode=difference,signalstats,metadata=print:file=-` and buckets the mean luma
difference between consecutive frames. Its docstring records measured values: *"ad slate ~0.19, gameplay clip
~1.6 - 2.5"*. `static_ranges` (`peakcut/studio/quality.py:69`) turns those buckets into ranges and
`static_overlap` (`peakcut/studio/quality.py:91`) measures how much of a clip sits inside one.

This overlaps the *hard cut* idea but is not the same detector: it is a per-2-second-bucket motion average,
not a per-frame HSV histogram Bhattacharyya jump. It is also **off by default** —
`peakcut/studio/config.py:135` `SKIP_STATIC = env("PEAKCUT_SKIP_STATIC", "0") == "1"`, and it is only invoked
at `peakcut/studio/jobs.py:712`. A cut detector ported separately would cost a second full decode of the
video. The port should compute cuts inside the same frame stream that feeds OCR (see §4.3).

### 3.3 The transcript has no place for a game signal

PeakCut never writes a transcript *file*. It holds words as
`[{"w": str, "s": float, "e": float}]` (`peakcut/studio/transcribe.py`) and groups them per AI window in
`brain.make_lines` (`peakcut/studio/brain.py:153`), producing
`{"s", "e", "text", "loud", "chat"}`. `loud` is a bool set when `seg.max() > 1.5` on the loudness z-score;
`chat` is a bool from the live-chat callback.

The prompt is built by `brain._fmt` (`peakcut/studio/brain.py:116`):

```python
return "\n".join(f"[{l['s']:.1f}] {'(LOUD) ' if l['loud'] else ''}{'(CHAT) ' if l.get('chat') else ''}{_safe(l['text'], 2000)}"
                 for l in lines)
```

So a third flag slots in with no format change: `(GAME WASTED)`. What is missing is (a) anything that
produces the events and (b) the two lines in `_fmt` and `make_lines` that would print them.

### 3.4 The pipeline has a clean insertion point

`peakcut/studio/jobs.py:546` `_run_job` runs: download/probe → `media.extract_audio` → block loop
(`peakcut/studio/jobs.py:514` `BLOCK = 600`, `PROGRESSIVE_FROM = 1200`) → per block
`brain.find_clips(...)` at `peakcut/studio/jobs.py:738` → clip dicts built at `peakcut/studio/jobs.py:757`
and appended at `peakcut/studio/jobs.py:766` → `render_one` per clip.

By the time the block loop starts, `job["source_path"]` is a real file for short videos and a full download
that is still in flight for long ones. `peakcut/studio/jobs.py:492` `_fetch_piece` gives long videos a
per-clip section instead, with `clip["src"]` and `clip["src_offset"]`. **The source path is therefore not
guaranteed to cover the whole timeline** — that is the single most important integration fact for this
feature (§6).

### 3.5 Job options are a closed set

`peakcut/studio/jobs.py:110`:

```python
DEFAULTS = {"max_clips": 6, "min_len": 15, "max_len": 60, "style": "bounce", "layout": "blur", "quality": 720,
            "range_start": None, "range_end": None, "captions": True}
```

`clean_options` at `peakcut/studio/jobs.py:117` drops every key not in `DEFAULTS`, and handles booleans with a
single special case (`if k == "captions": if not isinstance(v, bool): raise ValueError(...)`). Adding a
boolean option means editing that branch — a new key is otherwise silently discarded, which is exactly the
kind of failure that ships as "the toggle does nothing".

`peakcut/studio/jobs.py:149` `HIDDEN = ("dir", "user", "source_path", "recover")` and
`public` at `peakcut/studio/jobs.py:152` pass every other job key to the browser, so any new job key is
browser-visible by default.

### 3.6 No settings surface, no UI

`peakcut/studio/config.py` has an env-flag idiom already used for a comparable feature
(`SKIP_STATIC`/`STATIC_THRESHOLD`/`STATIC_MIN_SECONDS` at lines 135–137). There is no OCR settings module, no
`/api/vision` route, and no settings tab: `setTabs()` at `peakcut/web/index.html:2003` lists ai, transcribe,
profile, security, apps, storage, and the `I` icon map at `peakcut/web/index.html:847` has 55 keys
(`bolt`, `microphone`, `film`, `video`, `eye`, `chart`, …) with no OCR-ish glyph. `ic()` at
`peakcut/web/index.html:904` renders `${I[n]}` directly, so a name that is not in the map yields an invisible
icon rather than an error.

---

## 4. Port plan

New module: **`peakcut/studio/vision.py`** (the name is already reserved in
`peakcut/docs/GTA6-PORT-BRIEF.md:76-77`).

### 4.1 Module contract

```python
"""Game event detection: big centred banners (WASTED, BUSTED, MISSION PASSED...), wanted stars, hard cuts.

Watches a video at about one frame a second, reads the centre band with OCR, and turns what it finds into
timestamped events that the AI is told about as "(GAME WASTED)" on the transcript line under the banner.
Everything here is optional: no opencv, no OCR engine or no time budget means no events, never a failed job.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

Event = dict
# {"t": float, "t_end": float, "kind": "word"|"text"|"cut"|"stars", "label": str,
#  "hits": int, "weight": float, "text": str|None, "conf": float|None,
#  "cues": dict[str, float]|None, "stars": int|None}
Line = dict
# brain.make_lines() output, extended with "game": str|None and "games": list[str]
```

### 4.2 Every public function

```python
def available() -> bool:
    """Can this server detect anything? True when the OCR engine imports and its models are present.

    Cached after the first call. Never raises: a missing package is a False, not an error, which is what
    lets the feature be off on a server that never installed it."""

def words_table() -> dict[str, tuple[list[str], float]]:
    """label -> (phrases, weight), bundled table overridden by DATA_DIR/vision_words.json when present."""

def norm(s: str) -> str:
    """Uppercase, drop everything that is not A-Z or space, strip. Exactly vision.py:32."""

def match_word(txt: str, table: dict[str, tuple[list[str], float]] | None = None) -> str | None:
    """The label this OCR string is, or None. Whole string or any same-word-count window, ratio >= .8."""

def colour_cues(frame) -> dict[str, float]:
    """{"sat": 0-1 mean saturation of the frame, "gold": 0-1 gold fraction of the centre band,
    "red": 0-1 red fraction of the centre band}. Takes a BGR uint8 ndarray, vision.py:47."""

def banners(frame) -> list[tuple[str | None, str, float, float, float]]:
    """(label_or_None, text, confidence, relative height, relative centre x) for the centre band."""

def detect_frame(frame) -> list[tuple[str, str, dict]]:
    """(kind, label, extra) for one frame: kind is "word" or "text"."""

def stars(frame) -> int:
    """How many GTA-5 wanted stars are in the top-right HUD strip, 0-5, or 0 when the HUD is unknown."""

def merge(raw: list[tuple], gap: float = 15.0) -> list[Event]:
    """Collapse sightings: same label within `gap` seconds is one event with a start, an end and a hit count."""

def detect(source: str | Path, start: float = 0.0, end: float | None = None, *,
           fps: float = 1.0, want_stars: bool = False, budget_s: float | None = None,
           max_frames: int | None = None,
           on_progress: Callable[[float], None] | None = None) -> list[Event]:
    """Every game event between `start` and `end` seconds of `source`, in absolute source time.

    `start`/`end` narrow the scan but never shift the timestamps: an event at 3600.0 s is reported as 3600.0
    whatever window was scanned, because that is the base the transcript uses.
    `budget_s` stops the scan early (returning what it has) and `max_frames` caps the sampled frames; both
    default to None meaning unbounded, and the caller (jobs.py) always passes a budget.
    `on_progress` receives 0-1 as the file is consumed.
    Returns [] when the feature is unavailable, the source is unreadable, or nothing was found. Never raises."""

def apply(lines: list[Line], events: list[Event], slack: float = 8.0) -> list[Line]:
    """Attach events to transcript lines: the best label becomes line["game"], all of them line["games"].

    The same rules as vision.py:155-184, minus the text rewriting: cut events never attach, a "text" event
    needs hits >= 3, a "stars" event needs stars >= 3, a word event always attaches. A line is eligible when
    event.t is within `slack` seconds of the line's [s, e]; containment beats edge distance.
    Returns new dicts; the input is not mutated."""

def summary(events: list[Event]) -> dict:
    """What the job may show the browser: {"count": int, "labels": {"WASTED": 3, ...}, "stars_max": int}."""

def save(job_dir: Path, events: list[Event], meta: dict) -> Path:
    """Write <job_dir>/events.json and return its path. meta carries src/window/fps/scan_s."""

def load(job_dir: Path) -> list[Event]:
    """The events saved for this job, or [] when there is no file or it is unreadable."""
```

Two deliberate departures from the source:

- **`STARS` stops being module state.** `gta6-clipper-main/vision.py:20` is
  `_ocr = None; n_ocr = [0]; STARS = '--stars' in sys.argv` — a module that reads `sys.argv` at import. In a
  server that breaks immediately (uvicorn's argv is its own) and it is not per-user anyway. It becomes the
  `want_stars` parameter.
- **`apply` produces fields, not `[GAME …]` text.** PeakCut never has a transcript file; its lines are dicts
  built per AI window. Rewriting a file would mean inventing one.

### 4.3 Wiring into the pipeline

The feature is one extra pass in `_run_job`, one extra keyword through `find_clips`, and one extra field in
`_fmt`. In order:

**(1) Config flag** — `peakcut/studio/config.py`, beside `SKIP_STATIC` at line 135:

```python
OCR_EVENTS = env("PEAKCUT_OCR_EVENTS", "0") == "1"      # game banners (WASTED, MISSION PASSED) from the picture
OCR_BUDGET_S = float(env("PEAKCUT_OCR_BUDGET", "240"))  # wall clock for one job's scan, at most
```

Both off/cheap by default, matching the brief's rule 4 and the `SKIP_STATIC` precedent.

**(2) Job option** — `peakcut/studio/jobs.py:110` add `"game_events": False` to `DEFAULTS`; at
`peakcut/studio/jobs.py:117` widen the boolean branch from `if k == "captions":` to
`if k in ("captions", "game_events"):`. That is the whole option plumbing, because `clean_options` already
copies the value into `out`.

**(3) Detect, once, before the block loop.** Immediately after `job["source_path"]` is known and before the
`static_ranges` call at `peakcut/studio/jobs.py:712`:

```python
events = []
if (o.get("game_events") or config.OCR_EVENTS) and vision.available():
    _set(job, stage="Reading the screen for game banners")
    try:
        events = vision.detect(job.get("source_path") or "", lo / 16000, hi / 16000,
                               budget_s=config.OCR_BUDGET_S,
                               on_progress=lambda p: _set(job, progress=max(job["progress"], 0.13 + 0.01 * p)))
    except Exception:  # noqa: BLE001 - a picture pass that fails must not cost the clips
        events = []
    if events:
        vision.save(d, events, {"src": job.get("source_path"), "fps": 1.0, "events": len(events)})
        job["game_events"] = vision.summary(events)
        save(job)
```

Run it in the `fetch` `ThreadPoolExecutor` that `_run_job` already creates (`peakcut/studio/jobs.py:582`), or
a dedicated one-thread executor, so the audio and the first transcript block are not delayed by it. Do not put
it on the render pool.

**(4) Hand the events to the picker.** `brain.find_clips` gains a keyword and marks the lines:

```python
def find_clips(words, db, duration, title="", uploader="", max_clips=6, min_len=15, max_len=60,
               log=print, game=None, events: list[dict] | None = None):
    z = loud_zscore(db)
    lines = vision.apply(make_lines(words, z), events or [])
```

and `_fmt` at `peakcut/studio/brain.py:116` becomes:

```python
def _fmt(lines):
    return "\n".join(
        f"[{l['s']:.1f}] {'(LOUD) ' if l['loud'] else ''}{'(CHAT) ' if l.get('chat') else ''}"
        f"{'(GAME ' + l['game'] + ') ' if l.get('game') else ''}{_safe(l['text'], 2000)}"
        for l in lines)
```

`brain` importing `vision` is fine (no cycle: `vision` imports only `config`, `media`, `ai`). If you would
rather keep `brain` dependency-free, do the `apply` in `jobs.py` before the call — but then `find_clips` still
needs the keyword, because it builds `lines` internally.

**(5) Spend the signal in the prompt.** Add to `RULES` (`peakcut/studio/brain.py:52`), so the AI knows what
the marker means:

```
- A line marked (GAME WASTED), (GAME BUSTED), (GAME MISSION PASSED) or another (GAME ...) label is a moment
  the game itself announced on screen: a death, a failure, a win, an elimination. Take the reaction around it.
```

and to `_game_rules` (`peakcut/studio/brain.py:264`) when the game is one of the GTA titles — the banner
vocabulary is GTA's, and telling the AI "this stream is Grand Theft Auto VI" plus "WASTED is a death" is what
makes the label useful.

**(6) Long videos, where `source_path` is only a piece.** For `pieces=True` the whole-file scan is wrong. Two
acceptable behaviours, pick one and say which in the code:

- *Preferred:* scan only when `src["type"] != "url"` or `not pieces` — i.e. only when `job["source_path"]`
  really covers `lo..hi`. For long videos, attach no game events and let the AI use words and loudness as
  today. This is honest and costs nothing.
- *Alternative:* after `_fetch_piece` (`peakcut/studio/jobs.py:492`) has produced `clip["src"]`, scan that
  piece and add `clip["src_offset"]` back onto every `t`. Costs one scan per clip and only covers what will
  be rendered, which is actually the *better* coverage — but it is a second decode of the same footage the
  renderer is about to read.

Do not silently scan a piece and report its timestamps as absolute: every event would land under the wrong
transcript line.

**(7) Show it.** `job["game_events"] = vision.summary(events)` survives `public()`
(`peakcut/studio/jobs.py:152`) untouched because it is a small dict of counts. The SPA can print
"3 game banners found" in the job row. Full events stay in `events.json`, reachable via
`GET /api/jobs/{jid}/events` added next to `@app.get("/api/jobs/{jid}")` (`peakcut/studio/server.py:692`),
gated by the same owner check that route already uses and reading the file with `vision.load(Path(job["dir"]))`.

**(8) Route block, if a settings surface is wanted.** Optional; the feature works entirely off the env flag
and the per-job toggle. If added, copy `peakcut/studio/server.py:1324-1400` (`_tr_saved`/`_tr_public`/
`transcribe_get`/`transcribe_put`) with `_admin(request)`, `_throttle("vision:" + ctx.uid(), 30, 600)`,
`HTTPException(400)` for a bad value, and `ctx.bump()` on success. There is no secret, so `public()` returns
the effective settings only.

**(9) UI, if a tab is added.** `setTabs()` at `peakcut/web/index.html:2003` gets
`["vision", "Game events", "eye", "Banners such as WASTED from the picture"]` — `"eye"` is already in the
`I` map at `peakcut/web/index.html:847`. Any new icon name must be added there or `ic()` renders an empty svg.

### 4.4 What the renderer needs

Nothing. This feature changes *which* moments are picked, not how they look. `render.build_ass`
(`peakcut/studio/render.py:159`) and `render.render_clip` (`peakcut/studio/render.py:267`) are untouched; a
banner-shaped overlay would be a separate feature and is not in scope.

### 4.5 Order of work

1. `peakcut/studio/vision.py` — `norm`, `match_word`, `merge`, `apply`, `summary`: pure functions, no
   dependencies, testable first (§7.1).
2. `colour_cues` + `detect_frame` + the scan loop with ffmpeg frame extraction, behind `available()`.
3. `config` flags + `jobs` option + the `_run_job` call.
4. `brain.find_clips(events=...)` + `_fmt` + the `RULES` sentence.
5. Route and UI last, and only if wanted.

---

## 5. Data files

### 5.1 Label table — `peakcut/studio/vision_words.json`

Lives next to the fonts, in `peakcut/studio/`, so it ships with the code and needs no data-folder step.
Loaded once at import; a user-editable copy at `config.DATA_DIR / "vision_words.json"` wins when it exists
and parses, which is how a new game gets added without a release.

```json
{
  "version": 1,
  "weights": {"stars": 0.5, "cut": 0.3, "text": 0.35},
  "match_ratio": 0.8,
  "min_chars": 4,
  "words": [
    {"label": "WASTED",         "phrases": ["WASTED"],                          "weight": 0.8},
    {"label": "BUSTED",         "phrases": ["BUSTED"],                          "weight": 0.7},
    {"label": "MISSION PASSED", "phrases": ["MISSION PASSED", "MISSION COMPLETE"], "weight": 0.7},
    {"label": "MISSION FAILED", "phrases": ["MISSION FAILED"],                  "weight": 0.7},
    {"label": "HEIST PASSED",   "phrases": ["HEIST PASSED", "HEIST COMPLETE"],  "weight": 0.8},
    {"label": "HEIST FAILED",   "phrases": ["HEIST FAILED"],                    "weight": 0.7},
    {"label": "VICTORY ROYALE", "phrases": ["VICTORY ROYALE"],                  "weight": 0.8},
    {"label": "ELIMINATED",     "phrases": ["ELIMINATED", "YOU ELIMINATED"],    "weight": 0.5},
    {"label": "GAME OVER",      "phrases": ["GAME OVER"],                       "weight": 0.6},
    {"label": "YOU DIED",       "phrases": ["YOU DIED"],                        "weight": 0.7},
    {"label": "VICTORY",        "phrases": ["VICTORY"],                         "weight": 0.6},
    {"label": "DEFEAT",         "phrases": ["DEFEAT"],                          "weight": 0.5},
    {"label": "CHAMPION",       "phrases": ["CHAMPION", "YOU ARE THE CHAMPION"], "weight": 0.6}
  ]
}
```

Rules for loading: `words` is an ordered list — match order is list order and must stay as above (longest
first). `phrases` must already be uppercase and norm-safe (`[^A-Z ]` removed); reject any phrase that would
change under `norm()`. A malformed or unreadable override is ignored in favour of the bundled file and a note
is logged once — a hand-edited JSON must never stop a job, the same defence `_tr_saved` uses at
`peakcut/studio/server.py:1324` ("a hand-edited tr.json holding null, [], 3 or "text" must not stop the server
booting").

### 5.2 Per-job events — `<job_dir>/events.json`

`jobs.job_dir(jid)` (`peakcut/studio/jobs.py:145`) is the job's own folder; writing there keeps a
multi-user server from sharing state.

```json
{
  "version": 1,
  "src": "/data/users/u1/jobs/job01/source.mp4",
  "fps": 1.0,
  "scan_s": 41.3,
  "window": [0.0, 812.4],
  "budget_hit": false,
  "events": [
    {"t": 118.0, "t_end": 121.0, "kind": "word", "label": "WASTED", "hits": 4, "weight": 0.8,
     "text": "WASTED", "conf": 0.94, "cues": {"sat": 0.11, "gold": 0.0, "red": 0.02}},
    {"t": 402.0, "t_end": 402.0, "kind": "cut", "label": "CUT", "hits": 1, "weight": 0.3},
    {"t": 655.0, "t_end": 660.0, "kind": "text", "label": "TEXT YOU WIN", "hits": 5, "weight": 0.35,
     "text": "YOU WIN", "conf": 0.91, "cues": {"sat": 0.44, "gold": 0.01, "red": 0.0}}
  ]
}
```

`budget_hit: true` means the scan was stopped by `budget_s` and the event list covers only the early part of
the video — the caller must not treat silence after that point as "nothing happened". Events are in time
order; `t_end >= t` always.

### 5.3 Nothing else

No new database table, no migration, no cache directory. The OCR engine's own model files are whatever
`rapidocr_onnxruntime` ships inside its wheel — PeakCut never downloads them, so there is no model-fetch step
to mirror `fetch_model.ensure()`.

---

## 6. Risks

**The dependency is the whole risk.** `opencv` and an OCR engine are not in `peakcut/requirements.txt`, and the
brief forbids heavyweight additions without saying so explicitly. This feature cannot work without them:
`opencv-python-headless` (resize, `cvtColor`, `calcHist`, `compareHist`, `connectedComponentsWithStats`) and
`rapidocr-onnxruntime==1.4.4` (which pulls `onnxruntime`, tens of MB, plus bundled PP-OCR models). That is a
several-hundred-MB Docker image increase and a cold-start import of a second inference runtime on a box that
already runs `sherpa-onnx`. Mitigations, all three of which the port should have: the import is lazy and
inside `available()`; `available()` is called **once** and the answer cached; and every failure path returns
`[]` rather than raising. If a deployer refuses the dependency, the feature is simply absent — which is the
correct behaviour, not a broken job. Do not pretend a colour-cue-only mode is equivalent: without OCR it can
tell you "the frame went grey", and nothing more.

**`sys.argv` at import.** `gta6-clipper-main/vision.py:20` evaluates `'--stars' in sys.argv` at module import.
Pasted into a server this either always reads uvicorn's flags or crashes on an unusual argv. It must become
the `want_stars` parameter, and the module must have no import-time side effects beyond reading its JSON.

**The singleton OCR engine is not obviously thread-safe.** `gta6-clipper-main/vision.py:25-27` builds one
`RapidOCR()` for the process. With several jobs scanning at once (PeakCut renders up to 6 clips in parallel and
runs several jobs), that is concurrent inference on one object and, worse, N concurrent full-video decodes.
Guard with a module-level `threading.Lock` around `_ocr(...)` **and** a process-wide `threading.BoundedSemaphore`
around `detect()` (PeakCut already uses this pattern: `REMOTE_SLOTS` in `peakcut/studio/transcribe.py`, and
`_lookups` in `peakcut/studio/server.py:640`). Without the semaphore, one user's hour-long VOD starves every
other user's render.

**Cost is unbounded without a budget.** The source measures 7–20 minutes per hour of stream on one machine,
with OCR at about a second per frame. Three concurrent 3-hour VODs is over an hour of CPU. `budget_s` must
default to something finite from `config`, `budget_hit` must be reported, and the job must never wait on this
pass: fire it on a worker, attach the events if they arrive, and let clips be picked without them otherwise.
A scan that finishes after the picking is wasted — which is why the budget should be smaller than the time the
first blocks take to transcribe.

**`source_path` may cover only a piece of the video.** For inputs over `LONG_VIDEO = 40 * 60`
(`peakcut/studio/jobs.py:467`) PeakCut downloads per-clip sections into `clip["src"]` via `_fetch_piece`
(`peakcut/studio/jobs.py:492`) and never has a whole file. Scanning that section and reporting its raw
timestamps would put every event at the wrong second and tag the wrong transcript line. Either skip the
feature for that path or add `clip["src_offset"]` — see §4.3(6). This is the single easiest way to ship a
silently-wrong port.

**The label table is GTA-shaped.** A Valorant or Fortnite stream will match nothing; `VICTORY ROYALE` covers
one battle royale and nothing else. The generic `TEXT …` path is the only thing that generalises, and it is
also the noisiest: any big centred all-caps overlay — a sponsor slate, `SUBSCRIBE`, a stream's own alert — is
a candidate. That is why text events need `hits >= 3` before they may tag a line
(`gta6-clipper-main/vision.py:166`), and why the confidence bar for generic text is 0.85 rather than 0.6.

**Division by zero in the uppercase test.** `sum(c.isupper() for c in txt) >= .8 * sum(c.isalpha() for c in txt)`
(`gta6-clipper-main/vision.py:74`) is vacuously true when the text has no cased letters (all digits, or a
script without case). Guard it: require `sum(c.isalpha() for c in txt) >= 4` before the ratio. Pure fidelity
here buys false events.

**A 15-second merge gap merges distinct deaths.** Two WASTEDs 14 s apart (a quick retry) become one event with
`hits=2` spanning both, and the tag lands on whichever line is nearest the *first* sighting. Acceptable; do not
"fix" it by keying on kind, because `apply` and the weight table are written against the source behaviour.
Note also that all `CUT` events share the label `"CUT"` and therefore merge with each other — the source skips
cuts in `apply` anyway, so this is harmless, but it is why the cut list is nearly useless for anything else.

**Wanted stars are a trap.** `gta6-clipper-main/vision.py:130` records that six of seven detections were a
chat overlay in that corner. Keep `want_stars=False`, keep the GTA-5 HUD geometry
(top 10–24 % of height, right 28 % of width), and do not advertise the feature in the UI.

**Region assumptions.** The centre-band crop (`y 20–80 %`, `x 8–92 %`) and the `rh >= .06` bar assume a
full-frame game capture. PeakCut also renders facecam layouts, but detection runs on the **source**, so that
is only a problem if someone later feeds a pre-composed clip back in. Leave it; document it.

**Resolution.** Thresholds are fractions of frame size, so they scale, but OCR time and error rate do not.
Always downscale to 640 wide first (`gta6-clipper-main/vision.py:117`); a 4K source without that is minutes
per minute of video.

**Multi-user isolation.** Nothing here is global except the OCR engine and the table. Events live in the job
folder, the summary in the job dict, and the route must go through the same owner check as
`GET /api/jobs/{jid}`. Do not add a module-level `_events` dict keyed by path — two users uploading the same
file would share it.

**Licence.** `rapidocr-onnxruntime` is Apache-2.0 and bundles Apache-2.0 PP-OCR models; `onnxruntime` is MIT;
`opencv-python-headless` is Apache-2.0. All compatible with PeakCut's existing stack. State it in the
requirements comment so a deployer does not have to go looking.

---

## 7. Verification

### 7.1 Unit tests, no video, no OCR — `peakcut/tests/test_vision.py`

Follow the house style (`tests/test_games.py`: `os.environ["PEAKCUT_DATA"] = tempfile.mkdtemp(...)`,
`sys.path.insert(0, ".")`, a local `check(name, got, want)` printing `PASS`/`FAIL`). Cover, at minimum:

```python
from studio import vision

check("BUSTEO is BUSTED", vision.match_word("BUSTEO"), "BUSTED")
check("MISSION PASSEO! is MISSION PASSED", vision.match_word("MISSION PASSEO!"), "MISSION PASSED")
check("hello world is nothing", vision.match_word("hello world"), None)
check("three chars is nothing", vision.match_word("GG"), None)
check("VICTORY ROYALE does not become VICTORY", vision.match_word("VICTORY ROYALE"), "VICTORY ROYALE")
check("a banner inside a HUD line is found", vision.match_word("WASTED 2 450"), "WASTED")
```

and for the merge and the tagger, with hand-built events:

```python
raw = [(10.0, "word", "WASTED", {}, None), (22.0, "word", "WASTED", {}, None),
       (26.0, "word", "WASTED", {}, None)]
ev = vision.merge(raw)
check("14 s apart is one event", (len(ev), ev[0]["hits"]), (2, 2))
check("the second run starts a new one", ev[1]["t"], 26.0)

lines = [{"s": 10.0, "e": 14.0, "text": "oh no", "loud": True},
         {"s": 30.0, "e": 31.0, "text": "fine", "loud": False}]
out = vision.apply(lines, [{"t": 12.0, "kind": "word", "label": "WASTED", "weight": .8, "hits": 1}])
check("the banner line is tagged", out[0]["game"], "WASTED")
check("its neighbour is not", out[1]["game"], None)
check("apply does not mutate its input", "game" in lines[0], False)
```

Plus: a `text` event with `hits == 2` does not attach while `hits == 3` does; a `cut` never attaches; a
`stars` event needs `stars >= 3`; a malformed `DATA_DIR/vision_words.json` falls back to the bundled table;
`vision.available()` returns `False` (not an exception) when the engine is missing.

### 7.2 Frame-level test against a generated slate

No real footage needed — ffmpeg can draw the banner. Build a 6-second grey card with WASTED on it and assert
the detector finds exactly that:

```bash
ffmpeg -y -f lavfi -i "color=c=0x5a5a5a:s=640x360:d=6,format=rgb24" \
  -vf "drawtext=text='WASTED':fontfile=peakcut/studio/fonts/Anton-Regular.ttf:fontsize=104:fontcolor=0x1e1edc:x=(w-text_w)/2:y=(h-text_h)/2" \
  -r 10 /tmp/slate_wasted.mp4

python -c "
from studio import vision
ev = vision.detect('/tmp/slate_wasted.mp4')
w = [e for e in ev if e['kind'] == 'word']
assert len(w) == 1, ev
assert w[0]['label'] == 'WASTED' and w[0]['hits'] >= 3, ev
print('OK', ev)
"
```

Two more slates prove the two negative cases: the same card with `hue=s=0` before the text (a grey frame) and
with a sentence-case line instead of caps must produce **no** word event. Guard the whole file with
`if not vision.available(): print("skipped: no OCR engine"); raise SystemExit(0)` so the suite still runs on a
machine that never installed it — that is the same degradation rule the feature itself follows.

### 7.3 Prompt-level test

```bash
python -c "
from studio import brain
lines = [{'s': 10.0, 'e': 12.0, 'text': 'no no no', 'loud': True, 'game': 'WASTED'}]
print(brain._fmt(lines))
assert '(GAME WASTED) ' in brain._fmt(lines)
"
```

### 7.4 End to end

Create a job with `game_events: true` on a short source that contains a banner, then confirm the three facts
that matter: the option survives `clean_options`, the event list lands on disk, and the AI saw the marker.

```bash
python -c "
from studio import jobs
print(jobs.clean_options({'game_events': True}))     # must contain game_events, not drop it
"
python tests/run.py                                   # the whole suite, on a throwaway data folder
```

The second command is the regression gate named in `peakcut/docs/GTA6-PORT-BRIEF.md:31-32`; it must stay green,
in particular `tests/test_transcribe_logfare.py`. With the flag off (the default) `tests/run.py` must behave
exactly as before — that is the "off by default" check.

In a real job, `job.json` should carry
`"game_events": {"count": N, "labels": {"WASTED": 1}, "stars_max": 0}` and `<job_dir>/events.json` should
exist with `budget_hit` set to a truthful value.
