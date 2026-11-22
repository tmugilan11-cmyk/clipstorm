# style-tiles

Skill loaded: **frontend-design**.

One file: `peakcut/web/feat/style-tiles.js` (266 lines). No other file was touched.

## What it does

Settings > Brand used to ask "Caption style" with one `<select>`. You had to pick "hormozi" or "beast"
by reading words that describe nothing. Now the same choice is a grid of real frames, one per look, each
drawn by the server from the real caption renderer. You pick with your eyes.

- The grid is built as a sibling of the select, as one full-width row under the Brand fields.
- Every tile is a real `<button type="button" class="stile" data-act="pickstyle" data-style="NAME">`
  holding `<img loading="lazy" src="/api/style/preview?style=NAME" alt="">` plus the look's label.
- Clicking a tile writes the name into `#br_style`, then fires `new Event("change", {bubbles: true})`
  on it. The page's own listener (`web/index.html:2754`, `if (t.id && t.id.startsWith("br_")) brPreviewSoon();`)
  redraws its big preview, and the page's own save button reads `val("br_style")` as it always did.
  No save call was added.
- The original select stays in the page and keeps its value. It is only hidden with CSS
  (`select.stile-hide{display:none}`), never removed, because the page saves from it.

## The three constraints in the brief, and how each is met

**Slow preview endpoint.** A frame is requested only when its tile comes within 350px of the screen,
through one `IntersectionObserver`, and at most 4 requests are in flight at once (a small pump with a
20s timeout so a stuck ffmpeg call cannot hold a slot for ever). 35 looks are ~17 seconds of server time
if asked all at once; opening the page now asks for the visible ones only, measured at 16 of 35.

**No jumping grid.** Every `<img>` carries `width="270" height="480"` and the frame box is
`aspect-ratio:9/16`, so the space is reserved before any byte arrives. A soft sheen sits in the empty
frame until the image lands, then fades to the picture.

**A failed frame is not a hole.** On `error` the tile gets `data-st="off"` and the frame box is hidden;
the label stays and the tile is still a working picker.

**Keyboard.** Tiles are real buttons, so tab and Enter work with no extra code. `:focus-visible` draws a
2px brand-orange ring. Enter on a focused tile picks the look, confirmed live (see below).

**The style list is cached.** `GET /api/captions/styles` is asked once for the whole page (guarded by an
`asked` flag) and kept in a module variable. The grid is built on first paint from the options the page
already put in the select, so it never waits for the network; if the server's list turns out to differ,
the grid is rebuilt once.

**Idempotent.** The `drawSettings` hook runs on every repaint. It bails out immediately when the select is
absent (every settings tab except Brand), and when a grid is already beside the select it only moves the
`.on` mark. Verified: switching to the AI tab and back leaves exactly one grid with one marked tile.

## The id was checked, and is what the brief said

`web/index.html:2361`, inside `brandPage()`:

```html
<label class="f">Caption style<select id="br_style">${opts(styles, b.style)}</select>...
```

`#br_style` is correct, no fallback lookup was needed.

One layout note: that select sits inside its `<label>`, and a `<label>` may only hold inline content
(a block inside it would also forward every click to the select), so the grid is inserted after the whole
label, with `grid-column:1/-1` to be a full row of the `.fields` grid.

The server's shape differs from the one in the brief. The brief said
`{"styles": {"beast": "Beast", ...}}` (a map). It is actually an object wrapping a list:
`{"default":"bounce","styles":[{"name":"bounce","label":"Bounce","house":true}, ...],"count":35}`.
The code accepts both shapes.

Also worth knowing: `web/index.html:1454-1487` already holds dead helpers `styleTiles()`,
`pickStyleTile()` and `watchStyleTiles()` using `.stiles`/`.stile`. They have no callers anywhere
(grep matched only the definitions), so nothing was wired to them. This file registers its own
`data-act="pickstyle"` handler and does not rely on that dead code. Removing it is a change to a file
I do not own.

## Endpoints used

| Endpoint | Used for |
|---|---|
| `GET /api/captions/styles` | the list of looks, asked once and cached |
| `GET /api/style/preview?style=NAME` | one real rendered frame per tile, on scroll |

## Commands run, with real output

```
$ cd peakcut && node --check web/feat/style-tiles.js; echo "check exit=$?"; wc -l web/feat/style-tiles.js
check exit=0
266 web/feat/style-tiles.js
```

```
$ curl -s http://127.0.0.1:8798/api/captions/styles | head -c 300
{"default":"bounce","styles":[{"name":"bounce","label":"Bounce","house":true},{"name":"hype","label":"Hype","house":true},{"name":"clean","label":"Clean","house":true},{"name":"beast","label":"Beast","house":false},{"name":"bubble","label":"Bubble","house":false},{"name":"classic","label":"Classic",
```

```
$ curl -s -o /dev/null -w "preview http=%{http_code} type=%{content_type} bytes=%{size_download} secs=%{time_total}\n" \
    "http://127.0.0.1:8798/api/style/preview?style=beast"
preview http=200 type=image/jpeg bytes=49109 secs=0.454375
```

```
$ curl -s http://127.0.0.1:8798/assets/feat
{"files":["autopilot.js","filters.js","grid.js","heard.js","log.js","mood.js","peek.js","pill.js","stage.js","stats.js","style-tiles.js"]}

$ curl -s http://127.0.0.1:8798/healthz
{"ok":true}
```

The loader lists the new file, so `plugins.js` injects it on boot.

## Live check in the browser

Opened `http://127.0.0.1:8798/app/settings/brand`, waited for boot, opened the Brand tab.

Loaded plugins and the grid:

```json
{"order":["filters","log","autopilot","grid","heard","mood","stats","peek","pill","stage","style-tiles"],
 "hasGrid":true,"gridTiles":35,"hideSelect":true,"selValue":"hormozi",
 "imgsWithSrc":16,"totalImgs":35,"okTiles":16,
 "firstLabels":["Bounce","Hype","Clean","Beast","Bubble"]}
```

35 tiles, select hidden, and only 16 frames asked for, the ones on screen.

Clicking the "beast" tile:

```json
{"sel":"beast","changeFired":1,"on":true,"pressed":"true","onCount":1,"live":"Beast chosen."}
```

One event, exactly one tile marked, and ~900ms later the page's own preview had redrawn itself:

```
#br_preview src = http://127.0.0.1:8798/api/style/preview?style=beast&font=Anton-Regul...
```

so the page's existing change handler really did notice. The select went `hormozi -> beast`, and the
brand document was never sent: no save was performed by the tile.

Keyboard, on the "neon" tile:

```json
{"focused":"neon","tabIndex":0,"isButton":"BUTTON/button"}
after Enter: {"sel":"neon","on":"neon","pressed":"true","live":"Neon chosen.","outline":"rgb(255, 139, 51)"}
```

Enter picks the look; the focus ring is the brand orange.

Redraw safety, after switching to the AI tab and back to Brand:

```json
{"grids":1,"tiles":35,"on":1,"sel":"hormozi"}
```

Failure path, forcing `data-st="off"` on a tile:

```json
{"offFrameDisplay":"none","onFrameDisplay":"block","selectVisible":"none","selectInDomAndValued":35}
```

A broken frame leaves the label only, and the select is still in the page with its 35 options.

Network, filtered to `style/preview`: exactly one request per look that was on screen (bounce, hype,
clean, beast, bubble, classic, comic, crimson, drop, duo, ember, emoji, glow, hollow, hormozi, karaoke,
minimal, lower, lemon, meme, neon, mozi, pill, pop, punch, retro, slide, shake, stamp, sweep, tiktok,
twotone, typewriter, whisper, word), 466 to 628 ms each, no duplicates, plus the two `&cb=brand`
previews the page itself loads.

Console: `No console lines yet` - the file throws nothing.

A screenshot of the grid was taken and read back: 11 columns of tall dark frames with visible captions,
label under each, orange ring and a tick on the chosen tile.

House rule check: `peakcut/AGENTS.md` says "Keep the existing palette, no shadows, and hover states that
change colour only". Every `box-shadow` was removed; hover changes border colour and background only.
Colours are the existing tokens (`--brand`, `--brand-soft`, `--line`, `--muted`, `--dim`, `--r-sm`).
`prefers-reduced-motion` turns off the sheen and the fade.

## What I could not test

- **The save round trip.** Pressing Save would have written the brand document (`PUT /api/brand`) for the
  real account, so I did not press it. What was proven is the part my file owns: the select's value really
  changes and the page's own change handler really fires. The save reads that same value
  (`web/index.html:2909`, `style: val("br_style")`).
- **Signed out vs signed in.** The live server runs with sign-in off (one local owner). The preview
  endpoint requires a user, and it answered 200 for this session, so the tile images are fine there.
  A multi-user build was not exercised.
- **A genuinely failing preview.** I simulated the failed state with `data-st="off"` rather than making
  the server fail. The markup and CSS path is the one a real error uses, but a real 400/500 was not seen.
- **Very narrow phones.** The 560px breakpoint (76px tiles) was written but not opened on a device.
- **Reduced motion.** The media query is present but not turned on and observed.

## Review notes

- Nothing outside my file was edited; no git command was run; the server was not restarted.
- The hook is cheap: one `querySelector` per draw on other settings tabs, and a single class check when
  the grid already exists.
- All server text goes through `esc()` before it reaches `innerHTML`; the image URL is
  `encodeURIComponent`-ed.
- If a name ever arrives that the select does not list, the tile adds its own `<option>` first, so a save
  can never write an empty string.
- Suggestions for files I do not own: delete the dead `styleTiles()` / `pickStyleTile()` /
  `watchStyleTiles()` helpers and the `.stiles` / `.stile` rules at `web/index.html:1454-1487` and
  `web/index.html:472-479`, so one picker style is not defined twice.
