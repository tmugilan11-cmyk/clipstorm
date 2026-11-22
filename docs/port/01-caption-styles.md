# 01 — Caption styles (32 named looks)

## 1. What it does

The user picks one caption "look" by name when creating a video, a live job, or a creator, and every clip
rendered afterwards is captioned in that look instead of PeakCut's single bouncy one. Each look is a complete
typographic package: font, size, colour of the unspoken words, colour of the word being spoken, outline width
and colour, shadow, an optional coloured pill behind the spoken word, how many words share a line, and how high
the captions sit in the 1080×1920 frame. Some looks add motion — a word that pops, stamps, falls in, types itself
out character by character, shakes, sweeps a coloured bar behind itself, or is drawn in two colours split across
its middle — and three of them change the whole layout (two-line karaoke sweep, one word at a time, or the top
half of a line at the top of the frame and the bottom half at the bottom, meme-style). The 32 names are stable
IDs saved with the clip, so a clip re-rendered later comes back in the look it was made with.

## 2. Exact mechanics

Source: `gta6-clipper-main/clip.py`. Everything below is self-contained; no need to reopen the file.

### 2.1 The style table

`STYLES` (`clip.py:18-51`) is a dict of **32** entries, keyed by the style name, each a **13-tuple**:

| # | field | meaning |
|---|---|---|
| 0 | `font_file` | TTF stem in `fonts/` |
| 1 | `family` | ASS `Fontname` — must match the installed family name |
| 2 | `bold` | ASS Bold flag: `-1` = bold (true), `0` = regular |
| 3 | `size` | ASS font size (line height units), 1:1 at PlayResY 1920 |
| 4 | `caps` | `1` = uppercase the caption text, `0` = leave as spoken |
| 5 | `text` | `RRGGBB` of the unspoken words |
| 6 | `spoken` | `RRGGBB` of the word being spoken |
| 7 | `outline` | `RRGGBB` of the outline |
| 8 | `outline_px` | outline width, float |
| 9 | `shadow` | shadow depth, float |
| 10 | `pill` | `RRGGBB` of the pill behind the spoken word, or `None` |
| 11 | `wpl` | words per caption line |
| 12 | `y` | caption anchor, px from the top of 1920 |

> **The brief's field list is wrong on two indices.** It calls index 2 `y_hint` and index 4 `spacing`. The code
> disagrees, and the code is what runs: `style_line()` (`clip.py:262`) writes `st[2]` into the ASS **Bold** field,
> and `word()` (`clip.py:243`) uses `st[4]` as the **uppercase** flag. Index 12 is the y. Use the table above.

`bgr(h)` (`clip.py:52`) converts `RRGGBB` to ASS's `&HBBGGRR` ordering: `h[4:6] + h[2:4] + h[0:2]`.

The full table, verbatim (`clip.py:19-50`):

| name | font file | family | bold | size | caps | text | spoken | outline | ol px | shadow | pill | wpl | y |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| classic | Montserrat-ExtraBold | Montserrat ExtraBold | -1 | 84 | 1 | FFFFFF | FFE500 | 000000 | 7 | 3 | – | 3 | 1250 |
| beast | Anton-Regular | Anton | 0 | 173 | 1 | FFFFFF | FFD400 | 000000 | 3.2 | 1 | – | 3 | 1382 |
| hormozi | Anton-Regular | Anton | 0 | 166 | 1 | FFFFFF | F7C204 | 000000 | 5 | 2 | – | 3 | 1344 |
| mozi | Anton-Regular | Anton | 0 | 166 | 1 | FFFFFF | FFFFFF | 000000 | 2.8 | 1 | 16A34A | 3 | 1344 |
| karaoke | Poppins-Bold | Poppins | -1 | 155 | 0 | A3A3A3 | F7C204 | 000000 | 2.6 | 1 | – | 4 | 1421 |
| pill | Anton-Regular | Anton | 0 | 146 | 1 | FFFFFF | FFFFFF | 000000 | 2 | 0 | 7C3AED | 3 | 1421 |
| lemon | Anton-Regular | Anton | 0 | 152 | 1 | FFFFFF | 111111 | 000000 | 1.8 | 0 | FACC15 | 3 | 1421 |
| neon | Poppins-Bold | Poppins | -1 | 155 | 0 | FFFFFF | 22D3EE | 164E63 | 3 | 2 | – | 4 | 1421 |
| ember | Anton-Regular | Anton | 0 | 173 | 1 | FFF7ED | FB923C | 431407 | 3.2 | 1 | – | 3 | 1382 |
| bubble | Poppins-Bold | Poppins | -1 | 143 | 0 | FFFFFF | FFFFFF | 000000 | 2 | 0 | 2563EB | 4 | 1440 |
| retro | Anton-Regular | Anton | 0 | 166 | 1 | FDE68A | F472B6 | 3B0764 | 3 | 2 | – | 3 | 1382 |
| crimson | Poppins-Bold | Poppins | -1 | 162 | 1 | FFFFFF | EF4444 | 000000 | 3 | 1 | – | 3 | 1382 |
| minimal | Poppins-Medium | Poppins Medium | 0 | 129 | 0 | FFFFFF | FFFFFF | 000000 | 1.6 | 0 | – | 5 | 1440 |
| word | Anton-Regular | Anton | 0 | 210 | 1 | FFFFFF | FFE500 | 000000 | 6 | 3 | – | 1 | 1250 |
| pop | LilitaOne-Regular | Lilita One | 0 | 106 | 1 | FFFFFF | FFD60A | 000000 | 6 | 2 | – | 3 | 1340 |
| typewriter | CourierPrime-Bold | Courier Prime | -1 | 108 | 0 | F8F8F2 | 4ADE80 | 000000 | 5 | 2 | – | 3 | 1400 |
| slide | ArchivoBlack-Regular | Archivo Black | 0 | 104 | 1 | FFFFFF | FF4D6D | 000000 | 6 | 2 | – | 3 | 1360 |
| shake | Anton-Regular | Anton | 0 | 173 | 1 | FFFFFF | FF3B30 | 000000 | 5 | 2 | – | 3 | 1382 |
| sweep | BowlbyOne-Regular | Bowlby One | 0 | 116 | 1 | FFFFFF | FFFFFF | 000000 | 4 | 1 | FF2E93 | 3 | 1382 |
| twotone | ArchivoBlack-Regular | Archivo Black | 0 | 103 | 1 | FFF200 | FF3D00 | 000000 | 6 | 2 | – | 3 | 1382 |
| emoji | LilitaOne-Regular | Lilita One | 0 | 113 | 1 | FFFFFF | FFD60A | 000000 | 6 | 2 | – | 3 | 1380 |
| lower | Poppins-Medium | Poppins Medium | 0 | 100 | 0 | FFFFFF | FFFFFF | 000000 | 14 | 0 | – | 6 | 1480 |
| duo | Poppins-Bold | Poppins | -1 | 123 | 1 | 9CA3AF | FFFFFF | 000000 | 4 | 1 | – | 6 | 1380 |
| meme | Anton-Regular | Anton | 0 | 200 | 1 | FFFFFF | FFFFFF | 000000 | 9 | 0 | – | 6 | 1380 |
| glow | Righteous-Regular | Righteous | 0 | 124 | 0 | FFFFFF | FF4FD8 | FF00C8 | 3 | 0 | – | 3 | 1380 |
| comic | Bangers-Regular | Bangers | 0 | 211 | 1 | FFE600 | FFFFFF | 000000 | 9 | 5 | – | 3 | 1380 |
| whisper | Poppins-Medium | Poppins Medium | 0 | 106 | 0 | FFFFFF | FFFFFF | 000000 | 1.4 | 3 | – | 5 | 1420 |
| punch | BowlbyOne-Regular | Bowlby One | 0 | 196 | 1 | FFFFFF | FFE500 | 000000 | 8 | 4 | – | 1 | 1150 |
| tiktok | Poppins-Bold | Poppins | -1 | 113 | 0 | FFFFFF | FFFFFF | 000000 | 4.5 | 2 | – | 4 | 1380 |
| drop | Montserrat-ExtraBold | Montserrat ExtraBold | -1 | 107 | 1 | FFFFFF | A78BFA | 000000 | 6 | 2 | – | 3 | 1360 |
| hollow | BebasNeue-Regular | Bebas Neue | 0 | 184 | 1 | FFFFFF | FFE500 | 000000 | 5 | 3 | – | 3 | 1380 |
| stamp | ArchivoBlack-Regular | Archivo Black | 0 | 103 | 1 | FFFFFF | FFFFFF | 000000 | 2 | 0 | E11D48 | 3 | 1400 |

Distinct font files required (9): `Montserrat-ExtraBold`, `Poppins-Bold`, `Poppins-Medium`, `LilitaOne-Regular`,
`CourierPrime-Bold`, `BowlbyOne-Regular`, `Righteous-Regular`, `Bangers-Regular`, `BebasNeue-Regular`.
`Anton-Regular`, `ArchivoBlack-Regular` and `Poppins-ExtraBold` already ship in `peakcut/studio/fonts/`.

### 2.2 The animation table

`ANIM` (`clip.py:213-214`) maps a style name to a motion kind. **A style absent from `ANIM` gets `kind = None`,
the plain per-word highlight.** Values:

```
pop → bounce      typewriter → type    slide → slide     shake → shake
sweep → sweep     twotone → twotone    emoji → None      lower → box
duo → duo         meme → meme          glow → glow       comic → comic
whisper → whisper punch → punch         tiktok → phrase   drop → drop
hollow → hollow   stamp → stamp
```

The remaining **14** styles (`classic, beast, hormozi, mozi, karaoke, pill, lemon, neon, ember, bubble, retro,
crimson, minimal, word`) have no `ANIM` entry and use the default branch.

### 2.3 The style line

`style_line(name, st, kind, box=False)` (`clip.py:256-264`) produces one ASS `Style:` line:

```
c1 = c2 = bgr(st[5])
if kind == "duo":     c1 = bgr(st[6])
if kind == "twotone": c1 = c2 = bgr(st[6])
a1 = {"hollow": "FF", "whisper": "8C"}.get(kind, "00")   # primary alpha: hollow fully transparent, whisper ~45% opaque
ang = {"comic": 3, "stamp": 3}.get(kind, 0)              # italic angle in degrees
ol = bgr(st[5]) if kind == "hollow" else bgr(st[7])      # hollow outlines in the fill colour
f"Style: {name},{st[1]},{st[3]},&H{a1}{c1},&H00{c2},&H00{ol},&H64000000,"
f"{st[2]},0,0,0,100,100,0,{ang},{3 if box else 1},{st[8]},{st[9]},5,60,60,0,1"
```

Field-by-field against the `Format:` line: Fontname `st[1]`, Fontsize `st[3]`, Primary `&H{a1}{c1}`,
Secondary `&H00{c2}`, Outline `&H00{ol}`, Back `&H64000000`, Bold `st[2]`, Italic/Underline/StrikeOut `0`,
ScaleX/ScaleY `100`, Spacing `0`, Angle `ang`, BorderStyle `3 if box else 1`, Outline `st[8]`, Shadow `st[9]`,
Alignment `5` (middle-centre — every event also carries an explicit `\pos`), MarginL/MarginR/MarginV `60,60,0`,
Encoding `1`.

Two styles are emitted: `Cap` (`box=False`) and `Box` (`box=True`, the opaque-box variant used by `lower`/`tiktok`).

`whisper` and `hollow` implement their whole look through `a1`; `duo` and `twotone` through `c1`/`c2`.

### 2.4 Grouping words into lines

`groups(words, size=3, gap=0.6)` (`clip.py:199-208`). `ass()` calls it as `groups(words, st[11])`, so **gap is
always the 0.6 s default**:

```
g = []
for w in words:
    full = len(g[-1]) >= size and not (w.get("end") and len(g[-1]) == size) if g else False
    if g and (full or g[-1][-1].get("end") or w["s"] - g[-1][-1]["e"] > gap): g.append([w])
    elif g: g[-1].append(w)
    else: g.append([w])
```

Three break conditions: the line is full (`>= size` words), the previous word ended a sentence
(`g[-1][-1].get("end")`), or a pause longer than 0.6 s. The `full` test is deliberately weakened for the
incoming word: if `w` is itself sentence-ending, a line holding exactly `size` words may absorb it, so a line is
`size` words, or `size + 1` when the extra word closes the sentence. `w.get("end")` is a **flag the caller must
supply** — `clip.py` sets it upstream; PeakCut's word dicts do not have it, so the port must synthesise it
(see §4.4).

### 2.5 The spoken-word tag

`word(x, now, keys, st, kind=None, idx=0)` (`clip.py:241-249`) returns one word with its override block:

```
w   = esc(x["w"].upper() if st[4] else x["w"])
key = re.sub(r"\W", "", w.upper()) in keys
if not (now or key): return w                    # unspoken, non-keyword: bare text, no tags at all

tag = r"\c&H" + (bgr(KEY) if key else bgr(PUNCH_COL[idx % 4] if kind == "punch" and now else st[6])) + "&"
if kind == "shake" and key: tag += SHAKE
if now and kind in NOW:
    tag += NOW[kind] + (rf"\bord12\3c&H{bgr(st[10])}&" if kind == "stamp" else "")
elif now:
    tag += (r"\fscx112\fscy112" if st[:2] == STYLES["classic"][:2] and st[3] == 84
            else r"\fscx100\fscy100\t(0,70,\fscx109\fscy109)"
                 + (rf"\bord10\3c&H{bgr(st[10])}&" if st[10] else ""))
return "{" + tag + "}" + w + r"{\r}"
```

Constants and tables it reads (`clip.py:210-227`):

```
KEY        = "5CFF3D"                      # keyword colour, green, in every style
SHAKE      = r"\frz-4\t(0,45,\frz4)\t(45,90,\frz-4)\t(90,135,\frz4)\t(135,180,\frz0)"
PUNCH_COL  = ["FFFFFF", "FFE500", "22D3EE", "F472B6"]     # punch: each word its own colour
NOW = {
  "bounce": r"\fscx72\fscy72\t(0,100,\fscx117\fscy117)\t(100,200,\fscx100\fscy100)",
  "punch":  r"\fscx170\fscy170\t(0,110,\fscx100\fscy100)",
  "comic":  r"\fscx70\fscy70\t(0,90,\fscx115\fscy115)\t(90,180,\fscx100\fscy100)",
  "stamp":  r"\fscx165\fscy165\t(0,100,\fscx100\fscy100)",
  "hollow": r"\1a&H00&", "whisper": r"\1a&H00&",
  "shake":  r"\fscx108\fscy108",
  "twotone": "", "sweep": "",
}
```

Behaviour worth stating plainly, because it drives the look:

- Unspoken, non-keyword words carry **no** override block — they inherit the style line exactly.
- The `classic` identity test `st[:2] == STYLES["classic"][:2] and st[3] == 84` matches only `classic`: it gets a
  flat `\fscx112\fscy112` with no animation; **every other style** gets `\fscx100\fscy100\t(0,70,109%,109%)`, a
  9 % swell over 70 ms.
- `pill` is not a drawn box. For a style with `st[10]` set, the *spoken word* gets `\bord10` in the pill colour —
  a thick coloured halo. (`BorderStyle: 3` on the `Box` style is separate; only `lower`/`tiktok` use it.)
- `hollow`/`whisper` restore `\1a&H00&` on the spoken word, so the dimmed/vanished fill comes back as it is said.
- Keywords (`keys`, a set of `\W`-stripped uppercase words) are green in **every** style, spoken or not; the
  `shake` kind additionally wobbles them.

`plain(g, st, keys, top=None)` (`clip.py:251-254`) is the same idea for a whole line with **no** highlight: words
joined by spaces, keywords wrapped in `{\c&H{KEY}&}…{\r}` (or back to `top`'s colour), else bare.

`esc(s)` (`clip.py:64`) — sanitisation, not optional: `{`→`(`, `}`→`)`, `\n`→` `.

### 2.6 Event emission per kind

`ass(...)` builds `gs = groups(words, st[11])` and walks them (`clip.py:298-340`). Per group:

```
nxt  = gs[gi+1][0]["s"] if gi+1 < len(gs) else dur
gend = min(g[-1]["e"] + 0.15, nxt)          # never overlap the next line
half = (len(g) + 1) // 2                    # used by duo, meme, and the \N breaker
```

`E(a, b, layer, tags, txt, sty="Cap")` appends
`Dialogue: {layer},{ts(a)},{ts(b)},{sty},,0,0,0,,{{{tags}}}{txt}`. `ts(t)` (`clip.py:63`) is `h:mm:ss.ss`
with two decimals.

**`box` (`lower`) and `phrase` (`tiktok`)** — one event per line, no per-word highlight:

```
per = 3 if box else 2
txt = r"\N".join(plain(g[k:k+per], st, keys) for k in range(0, len(g), per))
tags = rf"\pos(540,{y})" + (r"\fad(70,0)" if phrase else "") + (r"\3c&H000000&\3a&H5A&" if box else "")
E(g[0]["s"], gend, 0, tags, txt, "Box" if box else "Cap")
```

**`duo`** — two lines, each word sweeping grey→white over its own duration via `\kf` (centiseconds):

```
cs = [max(int(round(((g[i+1]["s"] if i+1 < len(g) else min(w["e"] + .1, gend)) - w["s"]) * 100)), 1)
      for i, w in enumerate(g)]
parts = [f"{{\\kf{c}}}" + esc(w["w"].upper() if st[4] else w["w"]) for w, c in zip(g, cs)]
E(g[0]["s"], gend, 0, rf"\pos(540,{y})",
  " ".join(parts[:half]) + (r"\N" + " ".join(parts[half:]) if g[half:] else ""))
```

**`meme`** — unstacked: the first half of the line at y 520, the rest at y 1380, as two events, second half
starting on its own first word. Stacked layouts: one event, the line broken at `half` with `\N`.

**Everything else** — one event per spoken word, the whole line visible, only the current word tagged. End of a
word's event is the next word's start, or `gend` for the last:

```
for i, w in enumerate(g):
    end = g[i+1]["s"] if i+1 < len(g) else gend
    pre = rf"\move(540,{y+70},540,{y},0,140)\fad(90,0)" if kind == "slide" and i == 0 else rf"\pos(540,{y})"
    if kind == "type":     # typed char by char; the rest of the line is invisible so the line never reflows
        n = len(w["w"]); step = max(min((end - w["s"]) * 1000 * .6 / max(n, 1), 60), 15)
        cur  = "".join(rf"{{\alpha&HFF&\t({int(k*step)},{int(k*step)+1},\alpha&H00&)}}{esc(c)}"
                       for k, c in enumerate(w["w"].upper() if st[4] else w["w"])) + r"{\r}"
        line = " ".join([word(x, False, keys, st) for x in g[:i]] + [cur]
                        + [r"{\alpha&HFF&}" + word(x, False, keys, st) + r"{\r}" for x in g[i+1:]])
    elif kind == "drop":   # words fall in as they are spoken
        cur  = r"{\alpha&HFF&\fscy150\t(0,110,\alpha&H00&\fscy100)}" + word(w, False, keys, st) + r"{\r}"
        line = " ".join([word(x, False, keys, st) for x in g[:i]] + [cur]
                        + [r"{\alpha&HFF&}" + word(x, False, keys, st) + r"{\r}" for x in g[i+1:]])
    else: line = " ".join(word(x, j == i, keys, st, kind, j) for j, x in enumerate(g))
```

Three kinds then emit a **second** event from the same loop. `text_w(st, text)` (`clip.py:236-239`, PIL) gives the
drawn width in px so the sweep bar can be positioned:

```
sweep:    sp = text_w(st, " "); ws = [text_w(st, cap(x["w"])) for x in g]
          tot = sum(ws) + sp * (len(g) - 1)
          a = 540 - tot/2 + sum(ws[:i]) + sp*i;  b = a + ws[i];  pad = 22
          tags = rf"\pos(540,{y})\1a&HFF&\bord22\3c&H{bgr(st[10])}&\shad0"
                 rf"\clip({a-pad:.0f},0,{a-pad:.0f},{H})\t(0,140,\clip({a-pad:.0f},0,{b+pad:.0f},{H}))"
          text = plain(g, st, ())             # no keyword colour on this underlay
glow:     tags = rf"\pos(540,{y})\1a&H40&\1c&H{bgr(st[7])}&\3c&H{bgr(st[7])}&\bord16\blur14\shad0"
twotone:  layer 2, tags = rf"\pos(540,{y})\1c&H{bgr(st[5])}&\bord0\shad0"
                          rf"\clip(0,{y-fs},1080,{y-int(fs*.02)})"   # top slice only
          text = plain(g, st, keys, st[5])    # base layer in the *second* colour shows below the slice
```

Layer of the primary event: `1 if kind in ("sweep","glow") else (0 if kind != "twotone" else 1)`.

**Emoji overlay** (`clip.py:221-226, 305-308`) is *not* a look: any caller that passes an `emoji` list gets
`(time, glyph)` pairs appended — for each word whose `\W`-stripped lowercase form is a key of the 50-entry `EMOJI`
map (`fire/hot/burn→🔥`, `money/cash/…→💰`, `crazy/insane/wild/mind→🤯`, `dead/die/died/kill→💀`, `win/won/…→🏆`,
…), spaced at least `EMOJI_GAP = 1.4` s apart, only when `HOOK_S <= s < dur - 0.4`. The `emoji` *style*'s `ANIM`
is `None` on purpose — it is the plain look plus the overlay.

### 2.7 Document skeleton

`ass()` (`clip.py:272-341`) writes `PlayResX: 1080`, `PlayResY: {H}` (1920), the `Format:` line, `Cap`, `Box`,
then two fixed styles with `FONT = "Montserrat ExtraBold"` (`clip.py:12`):

```
Style: Hook,{FONT},76,&H00{hf},&H00{hf},&H00{hb},&H00000000,-1,0,0,0,100,100,0,0,3,22,0,5,70,70,0,1
Style: Cta,{FONT},96,&H00FFFFFF,&H00FFFFFF,&H00{hb},&H00000000,-1,0,0,0,100,100,0,0,3,26,0,5,70,70,0,1
```

Hook event: layer 1, `0 → min(HOOK_S, dur)` where `HOOK_S = 3.0` (`clip.py:57`), tags
`\pos(540,{HOOK_Y})\3c&H{hb}&\fad(0,250)`, text `esc(hook.upper())`, `HOOK_Y = 330` (`clip.py:59`).
End card: layer 2, `dur-1.0 → dur`, only when `dur > 2.5`, tags
`\pos(540,{ey})\3c&H{hb}&\fad(150,0)\fscx70\fscy70\t(0,180,\fscx100\fscy100)` with
`ey = y + 230 if y < 1000 else y - 270`.

Return value: `head + "\n".join(events) + "\n"` — real newlines.

## 3. PeakCut today

`peakcut/studio/render.py` is the whole caption system today.

- `STYLES` (`render.py:14-21`) — **3** looks, each a dict of 8 flat keys: `label, font, size, base, active,
  strong, outline, pop, upper, per`. Keys `bounce`, `hype`, `clean`.
- `FONT_FILES` (`render.py:24`) — maps family → TTF: `Poppins ExtraBold`, `Anton`, `Archivo Black`. Anything else
  silently measures with Poppins ExtraBold.
- `_Font` (`render.py:28-69`) — reads `head`/`OS/2`/`post` straight out of the TTF with `struct`, gives
  `em()`, `width()`, `cap_shift()`. `width()` is the only honest text measurement available.
- `_groups` (`render.py:99-109`) — PeakCut's own grouping: `per` from the style, plus a 16-character cap and a
  0.45 s pause. **Not** the same rule as `clip.py`'s `groups()`.
- `build_ass` (`render.py:159-228`) — the caption builder. Filters words to the clip window (`:181`), re-bases
  times by `CAPTION_LEAD = 0.0` (`:161`, `:72`), clamps each word's end to the next word's start (`:183-184`),
  groups (`:185`), then for every word emits **three** events — waiting (`:220-221`), being said
  (`:222-224`, `\fscx94\fscy94\t(0,90,{pop})\t(90,200,{pop-5})`), said (`:225-227`) — each at its own
  `\an5\pos(x, cy)` with manually accumulated `x`, because `_Font.width()` lets it reserve space so a growing word
  never pushes its neighbours.
- Long-line safety (`:203-208`) — a line wider than `CAP_MAX_W = 960` (`render.py:25`) is shrunk to fit; a script
  the font cannot draw falls back to one whole centred line via `roman.drawable()` (`:195-201`).
- `geometry()` (`render.py:112-125`) returns `(layout, fg_h, hook_y, cap_y)`; caption y is layout-dependent
  (`1380` for `crop`/`gameplay`, up to `1640`).
- Call site: `render_clip` (`render.py:267`) → `build_ass(...)` (`:276-277`) → `_render_in` (`:289`) writes the
  `.ass`, copies `config.FONTS_DIR/*.ttf` into the work dir and runs
  `ass={name}.ass:fontsdir=f` (`:293-295`).
- `install_fonts()` (`render.py:73-78`) copies `studio/fonts/*.ttf` into `config.FONTS_DIR` at boot
  (`server.py:66`), per-file, only when absent.
- Style choice is already plumbed end to end: `jobs.DEFAULTS["style"] = "bounce"` (`jobs.py:110`), validated
  against `render.STYLES` in `clean_options` (`jobs.py:131-132`) and `rerender` (`jobs.py:364-365`),
  defaulted per creator (`creators.py:17`), copied per live clip (`live.py:574`), published to the SPA as
  `{k: v["label"]}` with layouts in `/api/status` (`server.py:589`), drawn as a 3-tile picker in the new-video
  form (`web/index.html:1380-1382`) using `CAP_LOOK` / `capPrev()` (`index.html:1394-1399`).

**The gap.** Three looks, all one shape: a single hard-coded animation (pop + colour swap) with no per-style
typography beyond font/size/colour/outline. Missing entirely: 29 named looks; per-style shadow, pill, and
words-per-line; per-style caption height; the whole transform vocabulary (`\t` scale/stamp/comic, `\move` slide,
typewriter alpha reveal, drop-in, `\kf` karaoke, `\clip` sweep/glow/twotone layers, top/bottom meme split,
opaque-box lines); keyword colouring (PeakCut only recolours words the AI happened to highlight); fonts beyond 3.

## 4. Port plan

### 4.1 New module

`peakcut/studio/captions.py` — pure ASS generation, no I/O, no `config`, **no import of `render`** (render
imports it, not the other way round, to avoid a cycle).

```python
from collections.abc import Callable, Sequence
Measures = Callable[[str, str, float], float]     # (family, text, size_px) -> drawn width in px

Style = tuple[str, str, int, float, int, str, str, str, float, float, str | None, int, int]

STYLES: dict[str, Style]        # the 32 rows of §2.1, key order = insertion order of clip.py:19-50
ANIM:   dict[str, str | None]   # §2.2
LABELS: dict[str, str]          # name -> human label for the UI, e.g. {"word": "One word",
                                #   "hormozi": "Hormozi", "typewriter": "Typewriter", ...}
KEY:      str = "5CFF3D"
Y_REF:    int = 1250            # STYLES["classic"][12]: the y every style's height is relative to
PLAYRES_Y: int = 1920
HOOK_STYLE: str = ("Style: Hook,Poppins ExtraBold,96,&H0014100E,&H0014100E,&H00FFFFFF,&H00000000,"
                   "-1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1")


def has(name: str) -> bool: ...
def label(name: str) -> str: ...
def style(name: str) -> Style:
    """The 13-tuple for `name`, or STYLES["classic"] when unknown."""


def build(words: list[dict], start: float, end: float, style_name: str, highlight: list[str],
          cap_y: int, hook_events: Sequence[str] = (), measures: Measures | None = None) -> str:
    """A complete ASS document for one clip in one look. Real newlines. Nothing else.

    words        [{"w": str, "s": float, "e": float}] — absolute source seconds, already ordered
    start, end   the clip window in the same seconds
    style_name   a key of STYLES; anything else falls back to "classic" (never raises)
    highlight    words the AI called out; compared case- and punctuation-insensitively
    cap_y        caption anchor in the 1080x1920 frame, from render.geometry()
    hook_events  already-built Dialogue lines for the hook; emitted verbatim before the captions
    measures     text measurement; when None, widths fall back to len(text) * size * 0.42
    """
```

`build` must not mutate `words`, must not read module globals other than the tables, and must be safe to call
from several job threads at once (today's pipeline renders clips on worker threads).

### 4.2 How it plugs in

**`render.build_ass` (`render.py:159`)** keeps its exact signature and gains a dispatch as its **first statement** —
before `STYLES.get(...)`, because the 32 new names are not in that dict:

```python
def build_ass(words, start, end, hook, style_name, highlight, hook_y, cap_y) -> str:
    if captions.has(style_name):
        return captions.build(_clip_words(words, start, end), start, end, style_name, highlight, cap_y,
                             hook_events=_hook_events(_clean(hook), max(0.0, end - start), hook_y),
                             measures=lambda fam, t, size: _Font.get(fam).width(t, size))
    st = STYLES.get(style_name, STYLES["bounce"])
    ...                                            # the existing body, untouched
```

Consequences, all of them intentional:

- `bounce`, `hype`, `clean` take the old path and produce **byte-identical** ASS. Every existing clip, creator,
  default and test keeps its current output.
- The hook stays PeakCut's white rounded box: `hook_events` is `_hook_events(...)`'s own return value, so the 32
  looks change captions only. `Style: Hook` and `Dialogue: … ,Hook,` continue to exist for
  `tests/test_captions.py:86` and `:96`.
- `captions.build` re-emits the `Hook` style line and the `[Events]` header so the document is complete on its own.

**`render.py` module top** — import and merge, so every existing consumer sees the new names without changes:

```python
from . import captions
STYLES.update({name: {"label": captions.LABELS.get(name, name.title()), "engine": "captions"}
               for name in captions.STYLES})
```

That single line makes these already-written code paths correct with **no edit**:

- `jobs.clean_options` (`jobs.py:131-132`) accepts a new style instead of resetting to `bounce`.
- `jobs.rerender` (`jobs.py:364-365`) does the same for the clip editor.
- `server.py:589` publishes `{k: v["label"]}` — the SPA tile list grows automatically.
- `creators.py:17` and `jobs.py:110` keep `"bounce"` as the default. Do not change them.

**New helper in `render.py`** — extract the filtering that is currently inline at `render.py:181-184`, and reuse it
from both paths so the two engines see identical words:

```python
def _clip_words(words: list[dict], start: float, end: float) -> list[dict]:
    """Words starting inside the clip, cleaned, re-based to the clip, ends clamped, sentence-end flags set."""
```

It must (a) copy each dict, (b) keep `w["s"] >= start - 0.05 and w["s"] < end`, (c) subtract `start` from `s` and
`e` so the clip starts at 0 — `clip.py` is handed an already-cut word list and works in clip time, so this is the
one translation the port cannot skip — (d) clamp each word's `e` to the next word's `s`, (e) set
`w["end"] = bool(re.search(r"[.?!]\s*$", w["w"]))` because `groups()` reads that flag and PeakCut's transcript
words do not carry it, (f) drop empty words. Return the list sorted by `s`.

**`render.FONT_FILES` (`render.py:24`)** must gain the 9 families of §2.1 → file name. Without it `_Font.get()`
falls back to Poppins ExtraBold and the measured widths disagree with what libass draws — the sweep bar and the
`type`/`drop` line pacing visibly drift.

**Nothing else changes.** `render.install_fonts()` (`render.py:73`) already globs `*.ttf` and copies per file, and
`_render_in` (`render.py:293-295`) already stages `config.FONTS_DIR/*.ttf` into the work dir and points
`fontsdir=f` at it. Adding the font files and restarting is sufficient; an existing deployment picks up only the
new files because the existence check is per file.

### 4.3 Ordering inside `captions.build`

1. Resolve `st = STYLES.get(name, STYLES["classic"])`, `kind = ANIM.get(name)`.
2. `keys = {re.sub(r"\W", "", h.upper()) for h in highlight if h}`.
3. `y = cap_y + (st[12] - Y_REF)` — the style supplies its *relative* height, `render.geometry()` supplies the
   layout-correct absolute anchor. Do not use `st[12]` directly: `crop`/`gameplay` want 1380, the blurred layouts
   want up to 1640, and a fixed 1250 would put captions under the UI or across the facecam.
4. Emit the head: `ScriptType`, `PlayResX 1080`, `PlayResY 1920`, `WrapStyle: 2`, `ScaledBorderAndShadow: yes`
   (keep both — `\N` and long lines depend on them, and `clip.py`'s own head omits them), the `Format:` line,
   `style_line("Cap", …)`, `style_line("Box", …)`, `HOOK_STYLE`.
5. Emit `hook_events` verbatim, then the caption events per §2.6.
6. Return `head + "\n".join(events) + "\n"`.

### 4.4 Sequence of the group loop

Reproduce `ass()`'s loop exactly as written in §2.6, with the port's two substitutions: `dur = end - start` and
every time already relative to `start` (from `_clip_words`). `meme`'s unstacked split is the one kind that needs a
layout decision — PeakCut has no `STACKED`; treat every layout as unstacked **except** `gameplay`, where the
facecam occupies the top corner, so use the stacked single-event form there.

## 5. Data files

**No new JSON.** The style ID is already persisted per creator (`creators.py:17`), per job option
(`jobs.py:110`), per clip (`jobs.py:361-365`) and per live clip (`live.py:574`); adding the 32 names requires no
schema change because the field is a free string validated against `render.STYLES`. Do not introduce a
`captions.json` — there is nothing per-user to store, and a settings file would make the look depend on server
state instead of the clip's own saved field.

New assets, all in `peakcut/studio/fonts/` (copied to `config.FONTS_DIR` at boot):

| file | used by |
|---|---|
| `Montserrat-ExtraBold.ttf` + `OFL-montserrat.txt` | classic, drop |
| `Poppins-Bold.ttf` | karaoke, neon, bubble, crimson, duo, tiktok |
| `Poppins-Medium.ttf` | minimal, lower, whisper |
| `LilitaOne-Regular.ttf` + `OFL-lilitaone.txt` | pop, emoji |
| `CourierPrime-Bold.ttf` + `OFL-courierprime.txt` | typewriter |
| `BowlbyOne-Regular.ttf` + `OFL-bowlbyone.txt` | sweep, punch |
| `Righteous-Regular.ttf` + `OFL-righteous.txt` | glow |
| `Bangers-Regular.ttf` + `OFL-bangers.txt` | comic |
| `BebasNeue-Regular.ttf` + `OFL-bebasneue.txt` | hollow |

All ten files exist in `gta6-clipper-main/fonts/` together with their OFL licence text; copy them verbatim. The
licence files are not optional — PeakCut ships `OFL-anton.txt` etc. alongside its current fonts and must keep
doing so.

`render.FONT_FILES` is the one config map to extend (`render.py:24`), family → file name:

```
"Montserrat ExtraBold": "Montserrat-ExtraBold.ttf", "Poppins Bold": "Poppins-Bold.ttf",
"Poppins Medium": "Poppins-Medium.ttf", "Lilita One": "LilitaOne-Regular.ttf",
"Courier Prime": "CourierPrime-Bold.ttf", "Bowlby One": "BowlbyOne-Regular.ttf",
"Righteous": "Righteous-Regular.ttf", "Bangers": "Bangers-Regular.ttf",
"Bebas Neue": "BebasNeue-Regular.ttf"
```

The key must be exactly the ASS `Fontname` in `STYLES[n][1]`, including the space in `Poppins Medium` — that is a
distinct family from `Poppins`.

## 6. Risks

- **Font identity, not font file, is what ASS uses.** `style_line` writes `st[1]` as `Fontname`; libass resolves it
  through `fontsdir`/fontconfig. If the family string does not match the TTF's name table, libass silently
  substitutes a system font and every measured x-offset is wrong. Verify one rendered frame per font.
- **`Poppins` vs `Poppins ExtraBold` vs `Poppins Medium` are three families.** PeakCut ships only ExtraBold today.
  Copying `Poppins-ExtraBold.ttf` under a bold filename would make `duo`/`karaoke` look identical to `hype` — a
  silent quality bug, not an error.
- **Multi-user concurrency.** `clip.py` is single-user and leans on module globals (`STACKED`, `CAP_Y`, `HOOK_Y`,
  `FONT`). None of those may be ported: PeakCut renders clips from several job threads and a global would leak one
  user's layout into another's clip. Every input arrives as an argument; no module-level mutable state.
- **`\t` animation volume.** `sweep`, `glow` and `twotone` emit 2–3 events per word against the default's 1. On a
  180 s clip that is a few thousand `Dialogue` lines. libass copes, but the `.ass` is also written into the job
  folder and served (`.ass` is moved out at `render.py:319`), so file size and per-frame CPU both grow. Cap the
  kind per clip, not per word.
- **Non-Latin scripts.** PeakCut supports Hindi/Urdu-in-Roman (`tests/test_roman.py`) and has an explicit fallback
  at `render.py:195-201` for scripts its caption font cannot draw. The gta6 path has no such fallback — porting it
  naively replaces real Japanese/Thai/Arabic output with tofu. Keep a `roman.drawable()` check in the new path and
  drop to the existing whole-line centred fallback when it fails.
- **ASS injection from user text.** Hooks and transcripts are user data; `{` starts an override block. PeakCut's
  `_clean` (`render.py:92`) strips `{ } \`; `clip.py`'s `esc` maps them to parens. Run one of them once, before
  tagging, and never on already-tagged output.
- **Colour choice changes.** gta6 paints *keywords* green (`KEY = 5CFF3D`) in all 32 styles statically; PeakCut
  colours the AI's `highlight_words` per style via `st["strong"]`. Keep PeakCut's `highlight` as the driver and
  use `KEY` as the colour for the new looks only, so existing `bounce`/`hype`/`clean` clips do not shift colour.
- **Style IDs are durable.** Users' saved clips hold the string. Never rename or remove a key; unknown names must
  fall back (`bounce` on the legacy path, `classic` inside `captions.build`) rather than raise — a job that throws
  in `build_ass` fails the whole render (`jobs.render_one`).
- **Emoji glyphs come from the OS.** `fontsdir` carries only the caption fonts, so `emoji`'s 🔥 renders as tofu in
  a slim container. Either skip the overlay when no colour-emoji font is present or document the dependency; do
  not add a font package to `requirements.txt` for it.
- **Dependencies: none needed.** Everything is ASS text plus the already-present `PIL`/`ffmpeg`. `clip.py`'s
  `font_factor`/`text_w` use `fontTools` and `PIL`; do not port `fontTools` — `render._Font` already reads the
  same metrics with `struct` and is the measurement to reuse via the `measures` callback.

## 7. Verification

```bash
cd peakcut
python tests/test_caption_styles.py     # new: the 32-look contract, no server needed
python tests/run.py                     # full suite; "turning captions off and back on" must still pass
```

`tests/test_caption_styles.py` follows `tests/test_captions.py`'s shape (self-provisioning tempdir in
`__main__`, `check(name, condition)` printing `PASS`, exit non-zero on failure) and asserts:

1. `len(captions.STYLES) == 32` and every name in §2.1's first column is present.
2. `render.STYLES` contains all 32 plus `bounce/hype/clean`, and `jobs.clean_options({"style": "word"})["style"]
   == "word"` — the validator accepts a new name and still rejects `"nope"` to `"bounce"`.
3. For each of the 32: `captions.build(WORDS, 1.0, 3.0, name, [], 1380)` returns a string containing
   `Style: Cap,` and at least one `Dialogue:` line ending in `,Cap,,0,0,0,,`.
4. `twotone` emits `Dialogue: 2,` lines; `sweep` and `glow` emit `Dialogue: 1,` caption lines; `lower` emits
   `,Box,`; `duo` emits `\kf`; `typewriter` emits `\alpha&HFF&`; `slide` emits `\move(`; `meme` emits two y
   positions (`\pos(540,520)`-equivalent and the lower one).
5. No returned document contains a doubled backslash: `assert "\\\\" not in ass`.
6. Legacy regression: `render.build_ass(WORDS, 1.0, 3.0, "HOOK", "bounce", [], 300, 1380)` equals a checked-in
   golden string byte for byte, and still contains `,Hook,` and `POLISHED`-style `,Cap,` lines — i.e. §3's
   behaviour is untouched.
7. `render.build_ass(..., "not_a_style", ...)` returns the `bounce` output (fallback, no exception).

Then prove pixels, once per style, not just the ASS text:

```bash
cd peakcut
python - <<'PY'
from studio import captions
W = [{"w": "this", "s": 0.2, "e": 0.6}, {"w": "is", "s": 0.7, "e": 0.9}, {"w": "the", "s": 1.0, "e": 1.2},
     {"w": "style", "s": 1.3, "e": 1.8}]
for name in captions.STYLES:
    open(f"/tmp/{name}.ass", "w", encoding="utf-8").write(captions.build(W, 0.0, 2.0, name, [], 1380))
PY
for f in /tmp/*.ass; do
  ffmpeg -y -v error -f lavfi -i color=c=black:s=1080x1920:d=1 -vf "ass=$f:fontsdir=studio/fonts" \
         -frames:v 1 "${f%.ass}.png"
done
```

`ffmpeg` exiting 0 on all 32 is the real gate: a missing family or a malformed style line makes libass fail the
filter, not merely look wrong. Spot-check `classic`, `word`, `twotone`, `lower` and `punch` visually against
`gta6-clipper-main` output for the same words.
