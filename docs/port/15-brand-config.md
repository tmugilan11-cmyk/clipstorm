# 15 — Brand config (one document that dresses every Short)

## 1. What it does

Each person keeps one small brand document — a set of colours, a caption look, a font, a watermark, a progress
bar, a closing card, an optional music bed and a couple of picture switches — and every clip rendered afterwards
comes out in that look without touching the clip editor again. The document is edited once in Settings and is
written to the user's own folder, so two people on the same server can have two completely different channel
identities. A named "theme" can pre-fill the whole document, and the per-clip pick fields (the style dropdown, the
layout) still win, exactly like the last hand-set value winning over a saved default. Everything is off or neutral
until the user saves something, so an untouched account renders exactly the clips PeakCut renders today.

## 2. Exact mechanics

Source: `gta6-clipper-main/brand.example.json`, `app.py` (`brand_norm`), `clip.py` (`opt`, `with_theme`,
`brand_style`, `make_wm`, `wm_xy`, `progress_bar`, `cap_y`, `deco`), `themes.json`, `batch.py` (`bed_cmd`),
`meme.py` (`bed`). Everything needed is below; the source need not be reopened.

### 2.1 The document: 25 keys

`brand.example.json` is the schema *and* the defaults table: `brand_norm` reads that very file from disk and
uses it as the default map (`app.py:75`), so a missing key is filled from these values.

| key | type | default in `brand.example.json` | what it changes |
|---|---|---|---|
| `style` | str | `"hormozi"` | caption look name (looked up in `STYLES`) |
| `font` | str | `"Anton-Regular"` | TTF stem, overrides the look's own font |
| `colors` | obj | `{text, spoken, outline, key, box}` | see 2.5 |
| `hook_text` | hex | `"FFFFFF"` | hook title colour |
| `hook_box` | hex | `"0B3D91"` | hook title box colour |
| `position` | str | `"auto"` | caption height: `auto` / `top` / `middle` / `bottom` |
| `watermark` | str | `"@nocodehack"` | text handle, or a path to a PNG logo, or `""` = none |
| `watermark_color` | hex | `"FFFFFF"` | fill of a *text* watermark |
| `watermark_pos` | str | `"bounce"` | `tl` / `tr` / `bl` / `br` / `bounce` |
| `watermark_opacity` | float | `0.65` | 0–1 alpha |
| `watermark_size` | float | `0.2` | fraction of the 1080 width |
| `progress` | bool | `true` | bottom progress bar |
| `progress_color` | hex | `"00E5FF"` | bar colour |
| `endcard` | str | `"FOLLOW FOR MORE"` | closing card text, `""` = none |
| `aspects` | list | `[]` | extra exports: subset of `1:1`, `4:5` |
| `lang` | str | `""` | `es fr pt de ar hi` — selects a Noto caption face |
| `fillers` | bool | `true` | drops "um/uh/like" (feature 10) |
| `emoji` | bool | `false` | emoji pops over keywords (feature 06) |
| `denoise` | bool | `true` | `afftdn` in front of `loudnorm` |
| `blackfix` | bool | `true` | holds the last frame over a game-over black flash |
| `lift` | bool | `true` | gamma lift on a dark cam panel / dark game panel |
| `flash` | bool | `false` | white flash on the punch-in |
| `theme` | str | `""` | name from `themes.json`; `""` = none |
| `flip` | bool | `false` | stacked layouts put the cam **below** the game |
| `_help` | str | long text | **ignored** — every key starting with `_` is skipped |

`colors` is itself a 5-key map: `text` (unspoken words) `FFFFFF`, `spoken` (the word being said) `00E5FF`,
`outline` `000000`, `key` (keyword colour) `FF3B30`, `box` (pill behind the spoken word) `FF2E93`.

### 2.2 Normalisation — `brand_norm(b)` (`app.py:74-87`)

Runs on read *and* on save, so on-disk JSON is always canonical.

1. `ex = {k: v for k, v in json.loads(brand.example.json).items() if not k.startswith("_")}` — the default map.
2. **Legacy migration** (the old single-user app shape):
   - `colors.primary → colors.spoken`, `colors.accent → colors.text` (only if the new key is absent);
   - `watermark` as a **dict** → `""` when `type == "none"`, else `image` when `type == "image"`, else `handle`;
     and then `watermark_pos` defaults to `BRAND_POS.get(position, position or "tl")` with
     `BRAND_POS = {"top-left":"tl","top-right":"tr","bottom-left":"bl","bottom-right":"br"}` (`app.py:73`), and
     `watermark_opacity` defaults to the dict's `opacity` (`.65` when absent);
   - `default_style → style`.
3. `out = {k: b.get(k, v) for k, v in ex.items()}` — every unknown key is dropped, every missing key filled.
4. Colours: `out["colors"] = {k: str(c.get(k, v)).lstrip("#") for k, v in ex["colors"].items()}` and
   `for k in ("hook_text","hook_box","watermark_color","progress_color"): out[k] = str(out[k]).lstrip("#")`.
   Hash signs are stripped here and never appear downstream; case is not normalised on load.

`BRAND = brand_norm({})` (`app.py:87`) is the module-level "empty document" — **do not port that global**, see §6.

### 2.3 Resolution order — `opt(name, opts, brand, default)` (`clip.py:429-433`)

```
pick field (the per-clip dict)  >  env CLIPPER_<NAME.upper()>  >  brand.json  >  default
```

The env layer is single-user convenience (`CLIPPER_WATERMARK`, `CLIPPER_THEME`, `CLIPPER_STYLE`,
`CLIPPER_LAYOUT`, `CLIPPER_MUSIC`, `CLIPPER_BRAND`, `CLIPPER_CAP_SIZE`, …). The server has no per-request
environment, so **the port keeps only pick > brand > default** and reads nothing from `os.environ`.

Note the two different default sets. Because `brand_norm` guarantees every key exists, the `default` argument at
each call site is dead code for a real document — it only fires for `brand = {}`:

| call site | fallback when brand is empty |
|---|---|
| `opt("watermark", opts, brand, "")` (`clip.py:647`) | `""` |
| `opt("watermark_color", …, "FFFFFF")` (`clip.py:649`) | `FFFFFF` |
| `opt("watermark_size", …, 0.22)` (`clip.py:653`) | `0.22` |
| `opt("watermark_opacity", …, 0.7)` (`clip.py:653`) | `0.7` |
| `opt("watermark_pos", …, "tl")` (`clip.py:653`) | `tl` |
| `opt("progress", …, "")` (`clip.py:654`) | `""` → off |
| `opt("progress_color", …, "FFE500")` (`clip.py:654`) | `FFE500` |
| `opt("endcard", …, "")` (`clip.py:614`) | `""` → off |
| `opt("denoise"/"blackfix"/"lift", …, "1")` (`clip.py:621,631,636,640`) | `"1"` → on |
| `opt("cap_size", …, 1)` (`clip.py:611`) | `1` |

`truthy(v)` (`clip.py:457`) is false for `""`, `"0"`, `"false"`, `"no"`, `"off"`, `"none"` (case-insensitive) and
for `None`; everything else — including `"1"` and `0.65` — is true.

### 2.4 Themes — `with_theme(brand, opts)` (`clip.py:446-456`)

```python
name = opts.get("theme") or os.environ.get("CLIPPER_THEME") or brand.get("theme")
if not name: return {**brand}
th = THEMES[name]["brand"]                    # unknown name -> SystemExit listing the names
pick = {k: opts[k] for k in THEME_KEYS if opts.get(k) not in (None, "")}
return th | brand | pick | {"colors": th.get("colors", {}) | brand.get("colors", {}) | (opts.get("colors") or {})}
```

`THEME_KEYS` (`clip.py:442`) is the eleven keys a theme may set:
`("style", "colors", "hook_text", "hook_box", "progress_color", "watermark_color", "watermark_opacity",
"watermark_size", "watermark_pos", "progress", "font")`.

The merge is `dict | dict` (right wins), and `colors` is merged **key by key**, so a theme that omits `box` keeps
the brand's `box`. Order is `theme < brand.json < pick`, and a theme never sets `watermark` (the text/handle).

`themes.json` sits next to `clip.py` (`THEMES_FILE = Path(__file__).resolve().parent / "themes.json"`,
`clip.py:441`) and is `{"themes": [{"name", "label", "brand": {...}}, ...]}` — reproduce all five:

| name | label | style | colors text / spoken / outline / key / box | hook_text / hook_box | progress | progress_color | wm color / opacity / size / pos |
|---|---|---|---|---|---|---|---|
| `clean` | Clean (neutral default) | classic | FFFFFF / FFE500 / 000000 / 5CFF3D / – | FFFFFF / 000000 | true | FFE500 | FFFFFF / 0.6 / 0.2 / tl |
| `nocodehack` | NoCodeHack (ink, cream, cobalt sticker) | hormozi | FFF6E3 / 2F6BFF / 0B0F1A / 2F6BFF / 2F6BFF | FFF6E3 / 0B0F1A | true | 2F6BFF | FFF6E3 / 0.85 / 0.22 / tr |
| `neon` | Neon (cyan and magenta glow) | neon | FFFFFF / 22D3EE / 164E63 / FF2E93 / – | FFFFFF / 7C1D6F | true | 22D3EE | 22D3EE / 0.8 / 0.2 / bounce |
| `bold-yellow` | Bold yellow (Hormozi punch) | hormozi | FFFFFF / FFE500 / 000000 / FF3B30 / – | 000000 / FFE500 | true | FFE500 | FFE500 / 0.8 / 0.22 / tl |
| `minimal-white` | Minimal white (quiet, thin) | minimal | FFFFFF / FFFFFF / 000000 / FFFFFF / – | FFFFFF / 1A1A1A | false | FFFFFF | FFFFFF / 0.5 / 0.16 / br |

(`–` = the theme omits the key; the brand's value survives.)

### 2.5 Colours and font into the style — `brand_style(st, brand)` (`clip.py:458-470`)

`st` is the style tuple. The mapping is by index, and **only four of the five colours are settable**:

```python
IDX = {"text": 5, "spoken": 6, "outline": 7, "box": 10}
for k, v in IDX.items():
    if c.get(k) and (v != 10 or st[10]):          # box only where the style already has a pill
        st[v] = c[k].lstrip("#").upper()
```

So `colors.text` → index 5, `colors.spoken` → 6, `colors.outline` → 7, `colors.box` → 10. `colors.key` is **not**
a style field: it is the global `KEY` used to paint keywords (2.12). Colour values are upper-cased here (the only
place that happens). The call `brand_style(STYLES["pill"], {"colors": {"box": "FF0000"}})[10] == "FF0000"` but
`brand_style(STYLES["hormozi"], {...})[10] is None` — this asymmetry is asserted in `clip.py:767` and is
deliberate.

Font: `font` names a file. Resolution is `fpath(st) = Path(st[0]) if Path(st[0]).suffix else FONTS / f"{st[0]}.ttf"`
(`clip.py:471`). It then opens the TTF with PIL to read the real family name — `st[1]` **must** be the font's own
name-table family, because that is what ASS's `Fontname` resolves through `fontsdir`:

```python
st[0] = resolved path
st[1] = family          # e.g. "Anton-Regular" -> family "Anton"
st[2] = -1 if "Bold" in family or "Black" in family else 0     # ASS Bold flag
old   = st[3]
st[3] = int(old / font_factor(p) * ???)   # see below
```

The size correction is `st[3] = int(st[3] / old * ...)` in the narrow sense that the *stored* size is multiplied by
`font_factor(p) = (OS/2.usWinAscent + OS/2.usWinDescent) / head.unitsPerEm` (`clip.py:230-235`, `1.5` on any
failure, `fontTools` used when importable). Its effect: a synonym — ASS sizes are em-height, the style table stores
what looks right at that em, so re-measuring a substituted font keeps the visual size constant. PeakCut's
`render._Font` already reads the same two numbers with `struct` (`render.py:28-69`), so the port uses
`render._Font` and needs no `fontTools`.

### 2.6 Caption vertical position — `cap_y(st, pos, stacked)` (`clip.py:266-270`)

```python
POS_Y = {"top": 450, "middle": 960, "bottom": 1440}    # clip.py:227
CAP_Y = 1250                                           # clip.py:58, the classic baseline
def cap_y(st, pos="auto", stacked=None):
    if stacked: return POS_Y[pos] if pos in ("middle", "bottom") else CAP_Y   # the seam, never the cam face
    return POS_Y.get(pos, st[12])                                             # "auto" -> the style's own y
```

`position` is validated to `auto|top|middle|bottom` before use (`clip.py:514`). For a cropped export the value is
then clamped into the window: `my_y(H, y0) = int(min(max(cap_y(st,pos) - y0, 150), H - 170))` when `y0 or
H != 1920`, else the raw value (`clip.py:670`).

### 2.7 Watermark

**The PNG** — `make_wm(spec, path, color="FFFFFF")` (`clip.py:481-487`):

```python
if Path(spec).is_file():                      # a real file: just normalise to RGBA
    Image.open(spec).convert("RGBA").save(path); return
f = ImageFont.truetype(str(FONTS / "Poppins-Bold.ttf"), 64)
w = int(f.getlength(spec)) + 24
im = Image.new("RGBA", (w, 100), (0, 0, 0, 0))
ImageDraw.Draw(im).text((12, 12), spec, font=f, fill="#" + color, stroke_width=4, stroke_fill="#000000")
im.crop(im.getbbox()).save(path)
```

A text watermark is therefore rendered once at 64 px with a 4 px black outline, tightly cropped, and scaled later
by ffmpeg. It is cached per render, not per clip — it is written into the temp work folder.

**Placement** — `wm_xy(pos, W, H, y0=0)` (`clip.py:488-492`):

```python
top = max(160 - y0, 40)
return {"tl": (40, top),
        "tr": ("W-w-40", top),
        "bl": (40, f"H-h-{190 if H > 1500 else 60}"),
        "br": ("W-w-40", f"H-h-{190 if H > 1500 else 60}"),
        "bounce": ("'40+(W-w-80)*abs(mod(t/7,2)-1)'", top)}.get(pos, (40, top))
```

`40` px margin on every edge; `160` px of clearance from the top for the Shorts UI (collapsing to `40` when the
export is cropped, i.e. `y0 > 0`); `190` px from the bottom on a 1920-tall export, `60` on anything shorter (the
1080 and 1350 exports). `bounce` slides the watermark left-to-right across the free width with a 14 s round trip
(`mod(t/7,2)`, triangle wave) — `t` is the filter's timestamp, which starts at 0 because `-ss` precedes `-i`.

**The overlay** — `deco()` (`clip.py:655-669`):

```python
wmw = int(1080 * float(opt("watermark_size", opts, brand, 0.22)))     # clip.py:653
wmo = float(opt("watermark_opacity", opts, brand, 0.7))
ov(wm_png, f"format=rgba,scale={wmw}:-1,colorchannelmixer=aa={wmo}",
   f"overlay=x={x}:y={y}")
```

`scale={wmw}:-1` keeps aspect (the PNG height is ignored), `colorchannelmixer=aa=` is the whole opacity
implementation. The PNG is added as **an extra ffmpeg input of one frame** — `extra.extend(["-i", Path(png).name])`
— and the graph references it as `[{len(extra)//2}:v]` (`clip.py:660`). It is passed as a bare relative filename
with ffmpeg `cwd=work`, because a drive colon breaks the filter syntax on Windows.

### 2.8 Progress bar — `progress_bar(dur, color="FFE500", h=12)` (`clip.py:494-496`)

```python
return (f"color=c=0x{color}:s=1080x{h}:r=30:d={dur:.2f}",
        f"overlay=x='-w+w*t/{dur:.3f}':y=H-{h}")
```

A 12 px, 30 fps, 1080-wide colour generator lasting exactly the clip duration, overlaid so its right edge tracks
`t` — the visible width is `w*t/dur`, i.e. a left-to-right fill. It is composited over a dim track:

```python
f += (f"{src}[bar{k}];"
      f"[{cur}]drawbox=x=0:y=ih-12:w=iw:h=12:color=black@0.35:t=fill[tr{k}];"
      f"[tr{k}][bar{k}]{over}[{dst}];")                            # clip.py:668
```

The bar sits at the very bottom edge (`H-12`, `ih-12`): inside the Shorts UI band, which is intentional — it reads
as the platform's own progress line.

### 2.9 End card — `ass()` (`clip.py:290`, `:296-297`)

A second ASS style and one event, in the same file as the captions:

```python
Style: Cta,{FONT},96,&H00FFFFFF,&H00FFFFFF,&H00{hb},&H00000000,-1,0,0,0,100,100,0,0,3,26,0,5,70,70,0,1
ey = my(y + 230 if y < 1000 else y - 270)     # beside the captions, never on them
if endcard and dur > 2.5:
    Dialogue: 2,{ts(dur-1.0)},{ts(dur)},Cta,,0,0,0,,{\pos(540,{ey})\3c&H{hb}&\fad(150,0)\fscx70\fscy70\t(0,180,\fscx100\fscy100)}{esc(endcard.upper())}
```

`hb` is the `hook_box` colour converted to ASS's `&HBBGGRR` order (`bgr()`), used as the Cta **outline** colour.
`BorderStyle 3` = opaque box, outline 26, shadow 0. The card shows only in the last second, is uppercased, pops from
70 % scale to 100 % over 180 ms, and fades in over 150 ms. Hard requirement: clip length **> 2.5 s** (a shorter
clip silently drops the card).

### 2.10 Aspects and flip — the export branches (`clip.py:615-618`, `:677-682`)

```python
ASPECTS = {"1:1": (1080, 1080, 320), "4:5": (1080, 1350, 190)}     # W, H, where the window starts in the 9:16
asp = [a for a in aspects if a in ASPECTS]                        # list, or a comma string, filtered
branches = [("", 1920, 0)] + [
    ("_" + a.replace(":", "x"), ASPECTS[a][1],
     (1920 - ASPECTS[a][1] if flip else 0) if STACKED else ASPECTS[a][2]) for a in asp]
```

`flip` **only** matters when the layout is stacked: the crop window moves from the value in `ASPECTS` (which keeps
the top) to the top of the frame (`1920 - H`), i.e. the game panel. Non-stacked exports always use the tabulated
`y0`. Each branch gets **its own ASS file** with every y shifted and clamped by `my_y`, and its own
`crop=1080:{H}:0:{y0},` before the `ass=` filter (`clip.py:678`). One branch means one output file; `n` branches
split the video (`[vz]split={nb}`) and the audio (`asplit={nb}`) and are encoded in one ffmpeg call with `-map`
per branch (`clip.py:676-681`).

### 2.11 Music bed — `batch.bed_cmd` (`batch.py:20-24`) + `meme.bed` (`meme.py:247-258`)

The value is one of the four mood names or a file name:

```python
m = pick.get("music") or os.environ.get("CLIPPER_MUSIC") or brand.get("music")     # brand["music"] is not in the 25 keys
if m in ("hype", "chill", "tense", "funny"):
    cmd += ["--mood", m]
else:
    cmd += ["--file", str(m)]
out = <stem>_b.mp4
```

`mood` (default `"chill"`) synthesises a 4-bar loop in numpy when no sample is present (`meme.py:223-233`); the
table is `(bpm, kick steps, hats, bass notes, wave, f0)`:

| mood | bpm | kicks (16ths) | hats | note offsets | wave | f0 Hz |
|---|---|---|---|---|---|---|
| `hype` | 128 | `[0,4,8,12]` | yes | `[0,0,3,5]` | saw | 55.0 |
| `chill` | 80 | `[0,10]` | no | `[0,3,5,3]` | sin | 55.0 |
| `tense` | 90 | `[0,8]` | no | `[0,0,1,0]` | saw | 41.2 |
| `funny` | 110 | `[0,6,8,14]` | yes | `[0,4,7,4]` | sin | 82.4 |

`resolve_bed` (`meme.py:235-245`) prefers `sounds/mine/bed_<mood>.{wav,m4a,mp3}` and otherwise writes
`sounds/bed_<mood>.wav` atomically (`write_wav` to a pid-suffixed temp, then `os.replace`).

The mix is a second pass with the picture **copied** — no re-encode of video:

```
ffmpeg -y -loglevel error -i SHORT.mp4 -stream_loop -1 -i BED
  -filter_complex "
    [0:a]aresample=48000,aformat=channel_layouts=stereo,asplit=3[sp][k][m];
    [1:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{dur:.3f},volume={db}dB,
          afade=t=in:d=0.3,afade=t=out:st={dur-0.5:.3f}:d=0.5[b];
    [b][k]sidechaincompress=threshold=0.05:ratio=6:attack=15:release=350:makeup=1[bd];
    [m][bd]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=9,atrim=0:{dur:.3f}[ao];
    [sp]anullsink"
  -map 0:v -map "[ao]" -t {dur:.3f} -c:v copy -c:a aac -b:a 192k -ar 48000 -movflags +faststart OUT.mp4
```

`db = -14` (the CLI default). The bed is the **sidechain key** too (`[b][k]sidechaincompress`), so it ducks itself
under the speech; `threshold=0.05:ratio=6:attack=15:release=350:makeup=1`. `normalize=0` then `loudnorm` at
`I=-14:TP=-1.5:LRA=9` — note **LRA 9**, not the 11 used elsewhere.

### 2.12 The remaining switches, and where each one acts

| key | acts at | effect |
|---|---|---|
| `lang` | `clip.py:609-610` | `{"ar": "Noto Sans Arabic", "hi": "Noto Sans Devanagari"}` — swaps the caption font and multiplies the size by **1.3** (Noto sets smaller) |
| `denoise` | `clip.py:621` | prefix `afftdn=nr=8:nf=-45,` to `loudnorm=I=-14:TP=-1.5:LRA=11` |
| `blackfix` | `clip.py:631-633` | detects black runs and emits `freezeframes=first=:last=:replace=` |
| `lift` | `clip.py:636-645` | `eq=gamma=…:brightness=0.02` on the cam panel and/or `eq=gamma=…:contrast=1.04` on the game panel, chosen from measured luma |
| `flash` | `clip.py:671` | white flash on the punch-in; **off by default on purpose** |
| `fillers` | transcript step | drops filler words (feature 10) |
| `emoji` | `clip.py:614`, `:650-652` | collects `(t, emoji)` during caption building, draws each as a PNG overlay, min gap **1.4 s** (`EMOJI_GAP`), only after the hook ends |
| `colors.key` | `clip.py:534-536` | `KEY = str(brand["colors"].get("key", "5CFF3D")).lstrip("#")` — the colour every *keyword* word is painted, applied statically |

### 2.13 Saving and reading — `app.py`

- `GET /api/brand` (`app.py:740-741`):
  `{"brand": brand_norm(json.loads(brand.json)) or BRAND, "exists": bool, "fonts": sorted(stem for fonts/*.ttf)}`
- `POST /api/brand` (`app.py:892-894`):
  copies the old file to `brand.json.bak`, then `f.write_text(json.dumps(brand_norm(d["brand"]), indent=1))`,
  answers `{"ok": 1, "file": path}`. The normaliser is applied on save, so the file on disk is always complete.
- `load_brand(out)` (`clip.py:422-428`) searches, in order: `CLIPPER_BRAND`, `Path.cwd()/"brand.json"`,
  `out.parent/"brand.json"`, `out.parent.parent/"brand.json"`; unreadable JSON prints
  `brand.json unreadable ({e}), ignoring it` and returns `{}`.

The search-path cascade is a single-user fossil: it exists because the CLI renderer is launched from a folder, not
from an account. **The port replaces it with one explicit path** (see §4).

### 2.14 Caption size multiplier — `cap_scale(v)` (`clip.py:434-440`)

`"S" → 0.85`, `"M" → 1.0`, `"L" → 1.2`, case-insensitive; any other number is used as-is; anything non-numeric
(the sentinel `None` included) is `1.0`; the result is clamped to **0.7–1.5**. The selftest
(`clip.py:753`) pins it: `[cap_scale(x) for x in ("S","l",1.1,9,"x",None)] == [.85, 1.2, 1.1, 1.5, 1.0, 1.0]`.
When `!= 1` it scales three style fields (`clip.py:612`):
`st[3] *= cs` (size), `st[8] *= cs` (outline), `st[11] = max(1, int(st[11]/cs + .5))` (words per line — inverse,
so a bigger font means fewer words).

### 2.15 Reference ffmpeg shape of one branch

For a clip of `dur` seconds, branch `k` with window `(H, y0)`, watermark + progress on:

```
[s_k] -> crop=1080:{H}:0:{y0}, ass=cap{k}.ass:fontsdir=. -> [c{k}]
      -> [wm_input:v]format=rgba,scale={1080*wmsize}:-1,colorchannelmixer=aa={wmo} -> overlay=x=..:y=..  -> [x{k}_1]
      -> drawbox=x=0:y=ih-12:w=iw:h=12:color=black@0.35:t=fill                                 -> [tr{k}]
      -> [tr{k}][bar{k}]overlay=x='-w+w*t/{dur:.3f}':y=H-12                                     -> [o{k}]
audio: [ac]{dn}loudnorm=I=-14:TP=-1.5:LRA=11[an]; afade=t=out:st={dur-0.08}:d=0.08
encode: -c:v libx264 -preset medium -crf 18 -c:a aac -b:a 192k -ar 48000
```

`GRADE = "eq=saturation=1.3:contrast=1.07"` is applied to `[vz]` before the split, i.e. every branch shares it.

## 3. PeakCut today

Everything the brand document would drive is either hard-coded constants or absent.

- `peakcut/studio/render.py:14-21` — `STYLES` is a dict of **three** looks (`bounce`, `hype`, `clean`), each with
  `label, font, size, base, active, strong, outline, pop, upper, per`. No shadow, no pill colour, no per-style y, no
  keyword colour.
- `render.py:22-23` — `HOOK = {"font":"Poppins ExtraBold","size":96,"ink":"14100E","box":"FFFFFF","pad_x":36,
  "pad_y":22,"radius":26,"max_w":900}`. Hook colours are **constants**; `_hook_events` (`render.py:128-156`) draws
  its own white rounded box. `hook_text`/`hook_box` have nowhere to go.
- `render.py:24` — `FONT_FILES` maps three families to three bundled TTFs; `render.py:73-78` `install_fonts()`
  copies `studio/fonts/*.ttf` into `config.FONTS_DIR` at boot (`server.py:66`). `brand["font"]` has no consumer.
- `render.py:112-125` — `geometry(src_w, src_h, layout)` returns `(layout, fg_h, hook_y, cap_y)`; caption y is
  **layout-derived** (`1380` for `crop`/`gameplay`, up to `1640`), never user-set. `position` has no analogue.
- `render.py:267-286` — `render_clip(src, out_dir, name, clip, words, src_w, src_h)`. Reads only
  `clip["start"|"end"|"layout"|"facecam"|"captions"|"hook"|"style"|"highlight_words"]`.
- `render.py:289-321` — `_render_in(...)` is the single ffmpeg call: `_filter(...) + f"[v0]ass={name}.ass:fontsdir=f[v]"`,
  `-map "[v]" -map "0:a:0" -af loudnorm=I=-14:TP=-1.5:LRA=11`, qsv then x264, one output. **No overlay, no extra
  input, no second output, no grade, no denoise.** Confirmed: `grep -n "watermark|logo|music|bed|endcard|progress_bar"`
  over `peakcut/studio` returns only `mailer.py:24` (`LOGO`, an email header) and `brain.py:419` (prompt text).
- `peakcut/studio/jobs.py:110-111` — `DEFAULTS = {"max_clips":6,"min_len":15,"max_len":60,"style":"bounce",
  "layout":"blur","quality":720,"range_start":None,"range_end":None,"captions":True}`; `LIMITS` (`:114`) covers
  four ints. `clean_options` (`:117-142`) whitelists by `DEFAULTS`, clamps by `LIMITS`, and validates
  `style ∈ render.STYLES` (`:131-132`) / `layout ∈ render.LAYOUTS` (`:133-134`).
- `peakcut/studio/creators.py:17-23` — `creators.DEFAULTS` already carries per-creator `style`, `layout`,
  `captions`, `min_len`, `max_len`, `max_clips`; `_clean` (`:54-86`) validates `style` only by "is a string".
  `jobs.create` (`jobs.py:288-294`) folds six of those into the job's base options. **This is the closest thing to a
  brand today** — six flat fields on the creator, no colours, no watermark, no music.
- `peakcut/studio/accounts.py:38-66` — the per-user file pattern to copy: `_dir()` = `config.user_dir(ctx.uid())/"accounts"`,
  `_read(name, default)` with `ValueError → default`, `_write(name, data)` atomic
  (`tmp.write_text → chmod 0o600 → tmp.replace`) plus `ctx.bump()`. `accounts.py:240-270` is the
  whitelist-and-clamp `save_settings` precedent.
- `peakcut/studio/server.py:1318-1447` — the settings-route precedent: `_tr_file()`, `_tr_lock`, `_tr_saved()`
  (file-over-env merge), `_tr_public()` (never leaks the secret), `GET`/`PUT /api/transcribe`,
  `HTTPException(400)` for user errors, `HTTPException(507)` on `OSError`, `ctx.bump()` after a write.
  `_admin()` is at `server.py:306-315`, `_throttle()` at `:633`.
- `peakcut/web/index.html:2003-2009` — `setTabs()` returns `[key, label, icon, hint]` rows and gates three of them
  on `S.status.user?.is_admin`; `:847-903` is the `I` icon map, `:904` is `ic(n)`; `:1308` is the `ROUTES` map and
  `:1317` the settings-tab router regex `\/app\/settings(?:\/(ai|profile|security|apps|storage|transcribe))?`;
  `:2049` and `:2301-2332` are the load/save handlers to imitate.

**The gap.** PeakCut has no per-account document, no watermark, no progress bar, no end card, no music bed, no
aspect variants, no denoise/grade switch, and no user-supplied colour or font: one constant look table plus a
per-creator `style` string. The brand feature is a new module plus four splice points (render overlays, render audio,
jobs render path, settings route) — it is not an extension of an existing config file.

## 4. Port plan

### 4.1 New module

`peakcut/studio/brand.py` — one concern: the per-user brand document and the filter/PNG builders it implies.

Dependency direction: `config`, `ctx` (read) → `brand` → `render` → `jobs` → `server`. **`brand.py` must not import
`render`**, exactly like the `captions.py` precedent: wherever it needs style metadata, the caller passes it in.
This keeps `render.build_ass`'s documented "no import of render" rule intact and avoids a cycle.

```python
DEFAULTS: dict[str, object]          # the 25 keys of §2.1, exactly the brand.example.json values
THEME_KEYS: tuple[str, ...]          # §2.4
COLOR_KEYS: tuple[str, ...]          # ("text", "spoken", "outline", "key", "box")
POSITIONS: tuple[str, ...]           # ("auto", "top", "middle", "bottom")
WM_POS: tuple[str, ...]              # ("tl", "tr", "bl", "br", "bounce")
ASPECTS: dict[str, tuple[int, int, int]]   # {"1:1": (1080, 1080, 320), "4:5": (1080, 1350, 190)}
POS_Y: dict[str, int]                # {"top": 450, "middle": 960, "bottom": 1440}
LANGS: tuple[str, ...]               # ("", "es", "fr", "pt", "de", "ar", "hi")
LANG_FONT: dict[str, str]            # {"ar": "Noto Sans Arabic", "hi": "Noto Sans Devanagari"}
BED_MOODS: tuple[str, ...]           # ("hype", "chill", "tense", "funny")
THEMES: dict[str, dict]              # §2.4's five rows, loaded once from themes.json


def doc_path() -> Path:
    """config.user_dir(ctx.uid()) / "brand.json" — the one place a user's document can live."""


def themes() -> list[dict]:
    """[{"name", "label"}, ...] for the settings dropdown, in themes.json order."""


def normalise(raw: dict | None) -> dict:
    """brand_norm (§2.2): legacy migration, defaults filled, '#' stripped, unknown keys dropped. Never raises."""


def load() -> dict:
    """The caller's document, normalised. Missing or unreadable file -> normalise({}). Never raises."""


def current() -> dict:
    """load() memoised per user id on (st_mtime_ns, st_size); re-read when the file changes on disk."""


def public() -> dict:
    """{"brand": current(), "exists": bool, "themes": themes(),
        "styles": [names], "fonts": [family names], "layouts": [names]}"""


def save(patch: dict) -> dict:
    """Validate and merge over current(), write atomically, ctx.bump(), return the saved document.
    Raises ValueError with a human message for any invalid field (§5.2). Never raises OSError silently."""


def resolve(brand: dict, pick: dict | None = None) -> dict:
    """with_theme (§2.4) + pick precedence (§2.3), no environment layer. Returns a full 25-key document."""


def style_for(style: dict, brand: dict) -> dict:
    """brand_style (§2.5) for one of render.STYLES' dicts: returns a copy with base/active/outline
    replaced by colors.text/spoken/outline, and font/size re-derived. `style` is passed in, not imported.
    Honours colors.box only when the style dict already has a "box" key."""


def caption_y(brand: dict, style: dict, layout: str, stacked: bool = False) -> int:
    """cap_y (§2.6). `auto` -> the style's own y; stacked -> the seam unless middle/bottom was asked.
    Clamp into the frame the same way render.geometry already does."""


def wm_png(spec: str, color: str, out: Path) -> Path | None:
    """make_wm (§2.7): copy an RGBA logo, or draw the text at 64 px with a 4 px black outline.
    Returns None for an empty spec. `spec` must already be either a hex-free handle or a path inside
    doc_path().parent (checked by the caller, see §4.5)."""


def wm_xy(pos: str, w: int, h: int, y0: int = 0) -> tuple[int | str, int | str]:
    """wm_xy (§2.7), byte-for-byte, including the bounce expression."""


def progress_bar(dur: float, color: str = "FFE500", h: int = 12) -> tuple[str, str]:
    """progress_bar (§2.8): (lavfi source, overlay filter)."""


def endcard_events(text: str, dur: float, cap_y: int, box: str) -> list[str]:
    """The Cta Style row and its one Dialogue line (§2.9), or [] when text is empty or dur <= 2.5."""


def deco(k: int, h: int, y0: int, dur: float, plan: dict, args: list[str], work: Path) -> str:
    """The overlay fragment for branch k (§2.7-2.8). Appends the watermark PNG's -i pair to `args`
    and returns the chain from [c{k}] to [o{k}]. Empty string when the plan has nothing to draw."""


def bed(mp4: Path, music: str, db: float = -14) -> Path | None:
    """The music second pass of §2.11: writes <stem>_bed.mp4 next to mp4, returns it, or None when
    `music` is empty. Picture copied; raises RuntimeError on ffmpeg failure."""
```

### 4.2 How it plugs in

**`jobs.render_one` (`jobs.py:373-402`)** — the only place a brand document meets a clip. Immediately after
`local = dict(...)` (near `jobs.py:379`) and before the `render.render_clip` call at `jobs.py:386`:

```python
from . import brand                                   # module import at the top of jobs.py
...
local = brand.apply_brand(brand.current(), local, style_default=DEFAULTS["style"], layout_default=DEFAULTS["layout"])
out = render.render_clip(src, d / "clips", clip["id"], local, near, job["width"], job["height"])
if local.get("music"):
    moved = brand.bed(d / "clips" / out["file"], local["music"])
    if moved:
        out["file"] = moved.name
```

`brand.current()` is safe on a worker thread: `jobs` dispatches through `ctx.bind` (`jobs.py:317`, `:322`), so
`ctx.uid()` resolves to the job's owner inside the render worker.

**`brand.apply_brand(brand, clip, *, style_default, layout_default) -> dict`** — the one function that is *not* in
the list above because it is the join point; specify it as:

```python
def apply_brand(brand: dict, clip: dict, *, style_default: str = "bounce",
                layout_default: str = "blur") -> dict:
    """A copy of `clip` with the brand's render fields filled in. Per-clip values win — but a clip still
    sitting on the global default counts as 'unset', because jobs.DEFAULTS and creators.DEFAULTS both
    pre-fill 'bounce'/'blur' and would otherwise mask every brand style forever (§6)."""
```

Rules, in this order:

1. `out = dict(clip)`; `b = resolve(brand, {})` (the theme already folded in by `save`).
2. `out["style"] = clip["style"] if clip.get("style") not in (None, "", style_default) else b["style"]`;
   `out["layout"]` the same against `layout_default`. Both are then checked against the caller's name sets by
   `render` itself (`render.STYLES` / `render.LAYOUTS`); an unknown name falls back there, never raises.
3. Copy through every remaining brand key under its own name: `watermark`, `watermark_color`, `watermark_pos`,
   `watermark_opacity`, `watermark_size`, `progress`, `progress_color`, `endcard`, `aspects`, `lang`, `denoise`,
   `fillers`, `emoji`, `blackfix`, `lift`, `flash`, `flip`, `theme`, `colors`, `hook_text`, `hook_box`, `font`,
   `position` — each only when the clip does not already define it.
4. Add `out["brand"] = b` so `render` can read `colors`/`font`/`position` as one object instead of five keys.

**`render.render_clip` (`render.py:267-286`)** — signature unchanged; it reads the new keys off the clip dict it
already receives. Three insertions:

- After `ass = build_ass(...)` (`render.py:276-277`), build the end card and splice it into the same file:

  ```python
  ass = _with_endcard(ass, clip, cap_y)      # new helper: inserts the Cta Style row into [V4+ Styles]
                                             # and the Dialogue line before the first Dialogue of the file
  ```

  `brand.endcard_events(clip.get("endcard", ""), end - start, cap_y, clip.get("hook_box", "000000"))` returns
  `[]` for the default (empty) case, so today's clips are byte-identical.
- Styles: replace the `build_ass` call's `style_name` argument with
  `brand.style_for(render.STYLES.get(name, STYLES["bounce"]), clip["brand"])["name"]`-style resolution — concretely,
  `build_ass` gains one optional keyword, `colors: dict | None = None`, and applies `brand.style_for(st, {"colors": colors, "font": ...})`
  to `st` **after** `STYLES.get(...)` (`render.py:160`) and **before** any measurement. With `colors=None` the body
  is untouched.
- Caption y: `cap_y` from `geometry` stays the default; when the brand sets `position`, use
  `brand.caption_y(clip["brand"], st, layout)` instead. `auto` returns `geometry`'s value, so nothing moves by
  default.

**`render._render_in` (`render.py:289-321`)** — the ffmpeg call becomes a splice, and every piece is skipped when
its key is falsy, so the default command line is unchanged:

```python
extra: list[str] = []                                  # -i pairs for overlay inputs
plan = {"watermark": ..., "progress": ..., "dur": end - start}
fc = _filter(layout, fg_h, face) + f"[v0]ass={name}.ass:fontsdir=f[v]"
if plan_has_deco:
    fc += f"[v]{brand.deco(0, H, 0, end - start, plan, extra, work)}"
af = ("afftdn=nr=8:nf=-45," if clip.get("denoise") else "") + "loudnorm=I=-14:TP=-1.5:LRA=11"
base = ["ffmpeg", "-y", "-v", "error", "-ss", f"{start:.2f}", "-t", f"{end - start:.2f}",
        "-i", str(src), *extra,                        # inputs BEFORE -filter_complex
        "-filter_complex", fc, "-map", "[v]", "-map", "0:a:0", "-af", af, ...]
```

`brand.deco` must copy its watermark PNG into `work/` and reference it by bare filename, mirroring `render.py:293-294`
which already stages the fonts there. Input index arithmetic: the source is input `0`, so the *n*-th pair appended
by `deco` is input `n` and its graph label is `[{n}:v]`.

**`render.install_fonts` (`render.py:73-78`)** — already globs `*.ttf` per file, so any new caption face (the Noto
pair for `lang`, and feature 01's nine faces) needs no code change, only files in `peakcut/studio/fonts/`.

**`jobs.clean_options` (`jobs.py:117-142`)** — three new optional keys so a job can override the brand for one
video: `"watermark": ""`, `"progress": False`, `"endcard": ""`. Add them to `DEFAULTS` with those neutral values
plus a branch each (`str(v)[:80]`, `bool`, `str(v)[:40]`); the whitelist then accepts them and
`jobs.create`'s `{**base, **clean_options(options)}` (`jobs.py:294`) carries them into the job.

**`server.py`** — a new settings block modelled on the transcription block (`server.py:1318-1447`), placed next to
it:

```python
@app.get("/api/brand")
def brand_get(request: Request):
    _me(request)
    return brand.public()

@app.put("/api/brand")
def brand_put(request: Request, body: dict = Body(...)):
    _me(request); _throttle("brandput:" + ctx.uid(), 30, 600)
    try:
        return {"brand": brand.save(body.get("brand") or body)}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except OSError:
        raise HTTPException(507, "Could not write the brand file to disk.")

@app.post("/api/brand/logo")
def brand_logo(request: Request, file: UploadFile = File(...)):
    _me(request); _throttle("brandlogo:" + ctx.uid(), 20, 600)
    # only PNG/JPEG, max 2 MB, stored as config.user_dir(ctx.uid())/brand/logo.png,
    # then brand.save({"watermark": "logo.png"}) and return public()
```

Gate with `_me(request)` (per-user), **not** `_admin()`. `ctx.bump()` happens inside `brand.save`, which is what
makes another open tab refresh (`server.py:665-683` is the version/token check).

**`web/index.html`** — four edits, all additive:

1. `ROUTES` (`:1308`) needs no change (`settings` is already a route).
2. The settings router regex (`:1317`) must accept the new tab:
   `\/app\/settings(?:\/(ai|profile|security|apps|storage|transcribe|brand))?`.
3. `setTabs()` (`:2003-2009`) gains one row, available to everyone (a brand is per-user, not admin-only):
   `["brand", "Brand", "sliders", "Watermark, colours and music for every clip"]`.
   `"sliders"` is a real key in the `I` map (`index.html:872`) — no new icon path needed.
4. `drawSettings` (`:2026+`) gains a branch next to `if (tab === "ai")` / `tab === "transcribe"`:
   `const k = S.brand = await api("/api/brand");` then the form (§4.3), with a delegated handler alongside
   `case "aisave"` / the transcribe save (`:2301-2332`) calling `send("/api/brand", {brand}, "PUT")`.

### 4.3 The settings form (exact fields)

One tab, five groups; every control maps 1:1 to a §2.1 key and nothing else is editable:

| group | controls |
|---|---|
| **Look** | theme `<select>` (from `k.themes`, plus "None"); style `<select>` (from `k.styles`); font `<select>` (from `k.fonts`); 5 colour `<input type="color">` (text, spoken, outline, key, box) |
| **Hook** | hook_text colour, hook_box colour |
| **Captions** | position `<select>` auto/top/middle/bottom |
| **Watermark** | text `<input maxlength="60">` or a logo upload (mutually exclusive: uploading clears the text field and vice versa); colour; pos `<select>` tl/tr/bl/br/bounce; opacity `<input type="range" min="0" max="1" step="0.05">`; size `<input type="range" min="0.05" max="0.5" step="0.01">` |
| **Extras** | progress checkbox + colour; endcard `<input maxlength="40">`; aspects two checkboxes (`1:1`, `4:5`); music `<select>` (None + 4 moods); language `<select>`; then the six boolean switches (denoise, blackfix, lift, fillers, emoji, flash) and flip |

Colours are stored **without** `#` (§2.2) — the `<input type="color">` value must be stripped on save and
re-prefixed with `#` on load. Show a warning line, not an error, when `k.brand.style` is not in `k.styles`
("this look arrives with caption styles; `bounce` is used meanwhile").

### 4.4 Order of operations inside one render (do not reorder)

1. `jobs.render_one` resolves `src`, builds `local`.
2. `brand.apply_brand(brand.current(), local)` — style/layout default substitution, key fill-in, `brand` sub-dict.
3. `render.render_clip` → `geometry()` → `cap_y` (brand `position` when set) → `build_ass` with `colors` (style
   mutation happens inside, before measurement) → `brand.endcard_events` spliced in.
4. `_render_in` → `brand.deco` writes `wm.png` into `work/`, appends `-i` pairs, returns the graph → one ffmpeg pass
   (video + captions + overlays + audio chain) → cover at `min(1.2, dur/2)` → move mp4/jpg/ass out.
5. `brand.bed(...)` — **after** the file is in `out_dir`, because it renames its own output and copies the picture;
   it must be the last step, and `out["file"]` must be updated to the returned name so the SPA plays the right file.

Aspect variants (feature 02) slot between 3 and 4; brand only supplies the branch list and the per-branch `y0`.

### 4.5 Safety rules the port must implement

- `watermark` is either a bare handle/short text **or** a filename inside `config.user_dir(uid)/"brand/"`. Resolve
  with `(config.user_dir(uid) / "brand" / name).resolve()` and require the result to be
  `is_relative_to(user_brand_dir.resolve())`; anything else is rewritten to `""` on save. Never accept a path from
  the request body.
- `endcard` and `watermark` text pass through `render._clean` (`render.py:92`) before they reach ASS — a `{` in
  user text is an override block otherwise.
- Every numeric from the document is clamped in `normalise()` (`watermark_size` 0.05–0.5, `watermark_opacity`
  0–1), so a hostile document cannot produce a 10 000 px watermark.

## 5. Data files

### 5.1 `config.user_dir(uid)/brand.json` — one per user, the whole point of the feature

`config.user_dir` (`config.py:146-149`) already validates the uid against `[A-Za-z0-9_]{6,40}`, so the path is safe.
Layout on disk, written with `indent=1` (matching `accounts._write`), permissions `0o600` (matching `ai.save`):

```json
{
 "style": "bounce",
 "font": "",
 "colors": {"text": "FFFFFF", "spoken": "00E5FF", "outline": "000000", "key": "FF3B30", "box": ""},
 "hook_text": "FFFFFF", "hook_box": "0B3D91",
 "position": "auto",
 "watermark": "", "watermark_color": "FFFFFF", "watermark_pos": "bounce",
 "watermark_opacity": 0.65, "watermark_size": 0.2,
 "progress": false, "progress_color": "00E5FF",
 "endcard": "",
 "aspects": [], "lang": "",
 "fillers": true, "emoji": false, "denoise": true, "blackfix": true, "lift": true, "flash": false,
 "theme": "", "flip": false
}
```

Deliberate differences from `brand.example.json`, and why:

- `style` defaults to `"bounce"`, not `"hormozi"` — `hormozi` does not exist in PeakCut until feature 01 lands, and
  a default that silently falls back would look like a bug.
- `watermark`, `endcard` and `progress` default **off** (`""`/`""`/`false`) where gta6 defaults to
  `"@nocodehack"` / `"FOLLOW FOR MORE"` / `true`. The brief's rule: every feature off by default or degrading to
  today's behaviour. Nobody's existing clips gain a watermark because they opened Settings.
- `font` defaults to `""` (use the look's own font) rather than `"Anton-Regular"`.

Schema rules for `save()`: unknown keys dropped; a missing key filled from `DEFAULTS`; `_`-prefixed keys ignored;
colours are 6 hex chars, case-insensitive, `#` stripped, upper-cased; `position ∈ POSITIONS`;
`watermark_pos ∈ WM_POS`; `aspects ⊆ {"1:1","4:5"}`, at most 2, stored in the canonical order; `lang ∈ LANGS`;
`theme ∈ THEMES or ""`; `style`/`font` stored as given (forward-compatible — an unknown name falls back at render
time, never at save time, so a document written before feature 01 keeps working after it).

### 5.2 `peakcut/studio/themes.json` — bundled, read-only, shared by everyone

Copy `gta6-clipper-main/themes.json` **verbatim** (2293 bytes, the five rows of §2.4). It ships next to the module,
not in `DATA_DIR`: themes are code, not user data, and a per-user copy would be five duplicated tables. Loaded once
at import with `json.loads((Path(__file__).resolve().parent / "themes.json").read_text("utf-8"))`; a malformed file
degrades to `{}` (no themes offered) rather than failing the server.

### 5.3 Assets

| asset | where | note |
|---|---|---|
| watermark logo | `config.user_dir(uid)/brand/logo.png` | written by `POST /api/brand/logo` only, ≤ 2 MB, PNG/JPEG re-encoded to PNG |
| watermark text PNG | `<render work dir>/wm.png` | transient, one per render, deleted with the work folder (`render.py:286`) |
| caption faces | `peakcut/studio/fonts/*.ttf` → `config.FONTS_DIR` | `install_fonts()` already copies them (`render.py:73-78`). Add `NotoSansArabic-Bold.ttf` and `NotoSansDevanagari-Bold.ttf` for `lang`, with their OFL text |
| music beds | `<work>/bed_*.wav` | synthesised on first use per mood, then reused. Do **not** ship four WAVs; `numpy` is already a dependency (`requirements.txt:3`) |

`Poppins-Bold.ttf` is the source's watermark face; PeakCut ships `Poppins-ExtraBold.ttf` only. Use ExtraBold — at
64 px with a 4 px outline the difference is invisible, and it avoids a fifth Poppins weight.

## 6. Risks

- **`brand_norm` reads a file from disk on every call** (`app.py:75`). In a server that is one `read_text` +
  `json.loads` per normalisation. Cache the default map once at import; keep `normalise()` pure.
- **`BRAND = brand_norm({})` (`app.py:87`) is a module global and must not be ported.** PeakCut serves several
  users from one process: a module-level document is exactly how one person's watermark ends up on another's clip.
  Everything arrives as an argument; `current()` is memoised **per user id**, keyed on the file's
  `(st_mtime_ns, st_size)`, and returns a copy.
- **`clip.py` has six module globals** (`STACKED`, `CAP_Y`, `KEY`, `FONT`, `HOOK_Y`, `HOOK_S`). Only `CAP_Y`-style
  constants may be copied; `STACKED`/`KEY`/`FONT` are per-clip state and stay local.
- **The `DEFAULTS["style"] = "bounce"` trap.** Both `jobs.DEFAULTS` (`jobs.py:110`) and `creators.DEFAULTS`
  (`creators.py:17`) pre-fill the style, so `clip["style"]` is *always* set and a naive "per-clip wins" rule means
  the brand's style never applies. §4.2's `style_default` substitution is the fix; test it explicitly (§7, check 3).
- **`position` vs `geometry()`.** PeakCut's caption y is layout-derived (`render.py:112-125`, `1380`/up to `1640`).
  A fixed `1250` from `POS_Y` would put captions across the facecam on `gameplay`. `auto` must return
  `geometry`'s value; only the three explicit positions override it, and they still get clamped to the frame's
  safe band.
- **The env layer must be deleted, not ported** (`clip.py:429-433`). `CLIPPER_*` is process-wide; on a multi-user
  server one operator's environment would restyle everyone. `resolve()` reads pick + document only.
- **`make_wm` accepts any path** (`clip.py:484`). Ported naively that is an arbitrary-file-read on behalf of a
  logged-in user (open a `/etc/passwd`-shaped file as an "image" and see the error text, or worse, read a PNG that
  is not theirs). §4.5's containment check is mandatory, and it must be applied **on save** as well as on use.
- **`SystemExit` on an unknown theme** (`clip.py:452`) would kill a uvicorn worker. Raise `ValueError` →
  `HTTPException(400)` on the save path; on the render path, fall back to "no theme".
- **ASS injection.** `endcard`, `watermark` text and the hook are user data; `{` opens an override block. Route
  every one through `render._clean` (`render.py:92`) and never tag already-tagged output.
- **Overlay input indices are positional.** `[{len(extra)//2}:v]` breaks the moment anyone inserts an input before
  the overlays. Build the whole `extra` list in `deco` and pass it through as one object; never compute an index
  by hand at the call site.
- **Windows path length.** The overlay PNG goes through the ASS/filter parser too: the existing temp-work-dir
  design (`render.py:278-282`) exists for exactly this reason — the PNG must be a bare relative name inside
  `work/`, and the docstring says so.
- **The music pass re-encodes audio only.** `-c:v copy` means it cannot be merged with `_render_in`'s encode, and it
  costs one more full file write per clip. It also cannot share the `loudnorm` measurement (two different targets:
  `LRA=11` for the clip, `LRA=9` for the mix). Accept the second pass; gate it on `music != ""`.
- **`sidechaincompress` needs two audio streams.** A clip whose source audio is missing/`-map 0:a:0` failed will
  fail the music pass, not the render. Catch `RuntimeError` from `brand.bed` and keep the unmixed file so a bad
  music setting never costs the user a clip.
- **The progress bar uses `dur` three times** (lavfi `d=`, overlay `/`, and `-t`). Any rounding difference between
  them shows as a bar that finishes early or late. Compute `dur = round(end - start, 3)` once and use that value.
- **Dependencies: none new.** `PIL` (`pillow==11.3.0`) is already required for `_Font` and for logos; `numpy`
  (`2.2.6`) is already required and is all the bed synthesis needs; ffmpeg is already the renderer.
  **Do not port `fontTools`** — `render._Font` (`render.py:28-69`) reads `OS/2`/`head` with `struct` and is the
  measurement to reuse.
- **`flip` is inert until feature 02.** PeakCut has no stacked layout, so `flip` can only be stored and ignored;
  document that in the tooltip rather than pretending it works.

## 7. Verification

```bash
cd peakcut
python tests/test_brand.py      # new: pure document + filter-string contract, no server, no ffmpeg
python tests/run.py             # full suite; "turning captions off and back on" must still pass
```

`tests/test_brand.py` follows `tests/test_captions.py`'s shape — a self-provisioning tempdir in `__main__`,
`check(name, condition)` printing `PASS`, non-zero exit on failure, `PEAKCUT_DATA` pinned before importing `studio`.
Assert, in this order:

1. `set(brand.DEFAULTS) == set(json.load(open("studio/brand.example.json")) - {"_help"})` **modulo** the three
   deliberate overrides of §5.1, i.e. 25 keys, no `_`-prefixed key present.
2. `brand.normalise({})["style"] == "bounce"`; `brand.normalise({"colors": {"spoken": "#00ff00"}})["colors"]["spoken"] == "00ff00"`;
   `brand.normalise({"watermark": {"type": "image", "image": "l.png"}})["watermark"] == "l.png"`;
   `brand.normalise({"default_style": "hype"})["style"] == "hype"` (legacy migrations of §2.2).
3. `brand.apply_brand({"style": "clean", ...}, {"style": "bounce"})["style"] == "clean"` and
   `brand.apply_brand({"style": "clean", ...}, {"style": "hype"})["style"] == "hype"` — the default-vs-explicit rule.
4. `brand.resolve({"theme": "nocodehack", "hook_box": "123456"}, {"progress_color": "00FF00"})` keeps
   `hook_box == "123456"`, `colors.text == "FFF6E3"` (theme), `style == "hormozi"` (theme), and
   `progress_color == "00FF00"` (pick) — the `theme < brand < pick` order of §2.4, from `clip.py:770`'s own test.
5. `brand.resolve({}, {})["colors"] == {}`-equivalent: with no theme and no pick, the document is unchanged.
6. `brand.style_for(render.STYLES["bounce"], {"colors": {"spoken": "00FF00", "outline": "112233"}})["active"] == "00FF00"`
   and `["outline"] == "112233"`; and the same call leaves `pop` and `per` untouched.
7. `brand.wm_xy("tl", 1080, 1920) == (40, 160)`, `brand.wm_xy("br", 1080, 1920)[0] == "W-w-40"`,
   `"mod(t/7,2)" in brand.wm_xy("bounce", 1080, 1920)[0]`, `brand.wm_xy("tl", 1080, 1350, 190)[1] == 40` —
   all four from `clip.py:770`.
8. `brand.progress_bar(10.0)[1] == "overlay=x='-w+w*t/10.000':y=H-12"` (`clip.py:772`).
9. `brand.ASPECTS["4:5"][:2] == (1080, 1350)`; `brand.endcard_events("FOLLOW FOR MORE", 2.0, 1380, "000000") == []`
   (too short) and `len(brand.endcard_events("FOLLOW FOR MORE", 6.0, 1380, "000000")) == 2` for a 6 s clip.
10. `brand.caption_y({"position": "auto"}, st, "crop") == render.geometry(1920, 1080, "crop")[3]` — i.e. `auto`
    changes nothing.
11. `brand.save({"watermark_size": 99})` stores `0.5`, and `brand.save({"colors": {"text": "red"}})` raises
    `ValueError`; `brand.save({"watermark": "../../etc/passwd"})` stores `""` (§4.5).
12. `brand.current()` for two different `ctx.as_user(...)` ids returns two different documents (§6, the global).

Then prove pixels once, on a real file:

```bash
cd peakcut
python - <<'PY'
from pathlib import Path
from studio import brand, render
# 3 s of black at 1080x1920, one clip, brand with watermark + progress + endcard on
PY
ffmpeg -y -v error -f lavfi -i color=c=black:s=1080x1920:d=3 -f lavfi -i sine=f=330:d=3 \
       -shortest -pix_fmt yuv420p /tmp/pk-src.mp4
# render one clip through the real pipeline, then probe the output:
ffprobe -v error -select_streams v -show_entries stream=width,height,duration -of csv=p=0 <out.mp4>
ffmpeg -y -v error -ss 2.5 -i <out.mp4> -frames:v 1 /tmp/pk-end.png     # the Cta card must be visible
ffmpeg -y -v error -ss 0.5 -i <out.mp4> -frames:v 1 /tmp/pk-mid.png      # watermark + bar left edge
```

`ffmpeg` exiting 0 on the full filter graph is the real gate: a malformed `overlay` expression or a missing input
fails the filter, not merely looks wrong. Then eyeball `/tmp/pk-mid.png` (watermark in the top-left 40/160 corner, a
short bar at the bottom) and `/tmp/pk-end.png` (the card beside the captions). Finally, with the brand document
absent, the same render must produce a clip whose `ffprobe` output is identical to `main`'s — that is the "degrades
to today's behaviour" guarantee.
