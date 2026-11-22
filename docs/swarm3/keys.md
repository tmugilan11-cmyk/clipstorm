# keys — keyboard shortcuts for the clip dialog and the review page

Slug: `keys`. One file owned and written: `web/feat/keys.js` (173 lines). No other file was touched.

## What I built

A plug-in that answers keys in two places, and a small hint line that says which keys work.

**Clip dialog (`#clipdlg[open]`)**

| Key | What it does | What it clicks |
|---|---|---|
| `Escape` | closes the dialog | `[data-act="closedlg"]` inside the dialog; falls back to `dlg.close()` if that button is missing |

That is the whole list, on purpose. I read `drawClipDlg` (index.html:2590-2638) and the dialog markup has no
previous/next clip control of any kind: no stepper, no `D.next`/`D.prev`, nothing to click. ArrowLeft/ArrowRight
here could only be invented, and an invented arrow would either do nothing or drift from the page's own logic, so
I did not bind them. The brief says to say so, so: **arrows are not bound in the clip dialog.**

Letters do nothing in the dialog. `a` and `x` only mean approve/reject on the Review view, and there the page's own
`rvKeys` already owns them (see below).

**Review view (`#rvroot` present and visible)**

| Key | What it does | What it clicks |
|---|---|---|
| `Enter` | approves the clip at the cursor | `[data-act="rvapprove"]` on that card (index.html:2128) |
| `Backspace` | rejects it | `[data-act="rvreject"]` (index.html:2129) |
| `ArrowRight` | skips ahead | `[data-act="rvskip"]` (index.html:2130) |

All three click the real buttons, so the shortcut runs the page's own `rvReview` / `rvSkip` code and cannot drift
from it. The cursor is the first `.rv-card[data-cid]` whose pills are not already `.pill.ok`/`.pill.bad`, which is
the same clip `rvCursor()` picks (index.html:2100).

`a` / `x` / `s` are deliberately **not** bound here. index.html:1529 runs `rvKeys(e)` before plug-ins load and
already approves, rejects and skips. Binding them again would fire a second PATCH for one key press, so I left
them to the page and the hint line points at them.

Held keys do not repeat: `reviewKey` returns early on `e.repeat`, so leaning on Enter cannot decide clip after clip.

**Guards — `keys(e)` returns `false` (and so does nothing) when**

- `e.ctrlKey`, `e.metaKey` or `e.altKey` is set;
- the target is an INPUT, TEXTAREA or SELECT, or is contenteditable (the loader checks this too, I check again);
- the target is a focused `button`/`a`/`[role=button]`/`summary` **and** the key is Enter or Space, so the browser's
  own button activation still wins;
- `#formdlg` is open;
- any `dialog[open]` exists that is not `#clipdlg` (this also catches the ad-hoc dialogs index.html creates at
  :969, :1274, :1886 and :2967);
- the guided tour is running (`#tour` present) — the tour reads keys in the capture phase.

**Hint line**

A `<p class="pckeys">` with `<kbd>` keys: on the review page right under `.rv-list`, and in the clip dialog at the
bottom of `.panel`. Text is mine, no server strings, nothing escaped. The review hint stays visible once every clip
is decided, because that is exactly when someone wonders whether keys exist — I checked the real page and an earlier
version that hid itself was undiscoverable.

CSS is registered with `PeakCut.css("keys", ...)` (so it lands as `#pcss_keys`), styles only `.pckeys` and its
children, uses the theme's own variables (`--faint`, `--dim`, `--muted`, `--line-2`), and adds no shadows. Hover
states are not used. The line is 12px and quiet.

## Endpoints used

None. This plug-in never calls the API: every action is a `.click()` on a button the page already rendered, and
the page does the request. That keeps the permission, toast and refresh behaviour in one place.

## Commands run and their output

```
$ cd peakcut && node --check web/feat/keys.js && echo "JS OK"
JS OK

$ cd peakcut && node --check web/feat/keys.js && echo "JS OK" && wc -l web/feat/keys.js
JS OK
173 web/feat/keys.js
```

Served-file check:

```
$ python -c "import httpx,json;print(json.dumps(httpx.get('http://127.0.0.1:8798/assets/feat').json(),indent=1))"
{"files": ["autopilot.js", "day.js", "filters.js", "grid.js", "heard.js", "keys.js", "log.js",
           "mood.js", "peek.js", "pill.js", "stage.js", "stats.js", "style-tiles.js"]}
keys.js listed: True
```

Live page checks (browser tools, `http://127.0.0.1:8798/app`):

```
PeakCut._order = ["autopilot","day","filters","keys","grid","heard","log","peek","mood","pill","stage","stats","style-tiles"]
typeof PeakCut.keys.keys                      -> "function"
document.getElementById("pcss_keys")          -> present
```

Real Review page, real buttons, clicks intercepted in the capture phase on `#rvroot` so nothing was saved:

```
Enter        -> ["c0:rvapprove"]
Backspace    -> ["c0:rvreject"]
ArrowRight   -> ["c0:rvskip"]
a            -> []            x -> []            s -> []        (page's rvKeys owns these)
ArrowLeft    -> []            ArrowDown -> []
ctrl+Enter   -> []            meta+x -> []       alt+Enter -> []
repeat Enter -> []
keydown in a fresh <input>              -> []
#formdlg opened with showModal(), Enter  -> []
  ... after f.close(), Enter             -> ["c0:rvapprove"]
```

Clip dialog on the real page (a real clip opened with `openClip`):

```
open                  -> true
.panel .pckeys        -> present, text "Keys Esc close", 1 <kbd>
[data-act="closedlg"] -> present
Escape                -> ["closedlg"], dialog closed
a / x / Enter / ArrowRight in the dialog -> []
with an unrelated <dialog open> also up, Escape -> []
```

The hint on the real review page:

```
<p class="pckeys"> present immediately after .rv-list
text  "Keys Enter approve Backspace reject Right next clip"
12px, rgb(160,148,140) (theme --faint), 3 <kbd> elements, on screen
```

## What I could not test

- **Screenshots.** `dsh_browser_screenshot` timed out on every attempt in this session, so the visual check is
  computed styles and geometry (`getBoundingClientRect`) rather than an image. Everything above is DOM-level
  evidence; nothing is a guess about pixels.
- **A clip dialog for a clip that is still undecided.** This workspace has exactly one clip and it is already
  approved, so on the Review page there is no undecided card to click. I tested the review keys against the real
  page by temporarily removing the pill class from the rendered card (restoring it afterwards, and clicking
  nothing that reaches the API), and against synthetic cards for the two-card cursor case.
- **`close` events on `<dialog>`.** In this browser session the `close` event never fires, even for a dialog I
  created myself and closed directly — the dialog does report `open === false`. That is the environment (the tab
  is hidden), not the page, and index.html's own `#clipdlg` close handler depends on that same event. It does not
  affect this plug-in, which checks `dlg.open` rather than listening for the event, but a reviewer re-checking the
  dialog cleanup in a hidden tab should know that `innerHTML` is not cleared there.
- **Touch and mobile.** The hint wraps (`flex-wrap`) and the dialog is single-column below the mobile breakpoint,
  but I did not test on a phone-sized viewport.

## Notes for a reviewer

- **The one real decision:** I did not bind `a`/`x` on the Review page even though the brief mentions them,
  because index.html:1529 already handles them and a plug-in binding would send two decisions per key press. The
  keys I do bind (`Enter`, `Backspace`, `ArrowRight`) all click real `[data-act]` buttons, which is what the brief
  asks for, and they do not collide with anything the page owns. If you would rather have `a`/`x` come from the
  plug-in, the page's `rvKeys` would have to stop handling them first — that is a change in `web/index.html`, which
  I do not own.
- **Arrows in the clip dialog** are unbound because there is no control to click. To get them, `drawClipDlg` would
  need a previous/next control (again `web/index.html`, not mine). The hint says only what works, so it will stay
  honest if that control is added later only after this plug-in is taught to use it.
- **Ordering.** `keys` sits at index 3 in `PeakCut._order` on this load, after `filters` and before `grid`. The
  loader order depends on the `/assets/feat` listing; nothing in this file assumes a position. It returns `true`
  only when it acted, which stops later plug-ins from also acting on the same press.
- **Background tabs.** `syncReview`/`syncDlg` are driven by a `setTimeout` debounce plus a `MutationObserver`, not
  by `requestAnimationFrame`, because frames do not run in a hidden tab and the hint never appeared there.
- No new dependencies, no `innerHTML` with server text, no emoji, no em dash, comments in plain language.
