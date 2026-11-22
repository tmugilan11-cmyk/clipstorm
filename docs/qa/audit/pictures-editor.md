# Audit: Pictures editor — /app/pictures

Auditor: agent-145 (QA swarm, audit wave). Bug hunting per `systematic-debugging`; every visual
claim measured or line-cited per `docs/qa/CONTRACT.md`.

## Pages and files owned

- Page: `/app/pictures`
- `web/feat/pictures.js` (644 lines, read fully)
- `web/feat/pictures-dialog.js` (62 lines, read fully)

Support files read (read-only, not owned): `web/plugins.js` (page host, feat loader, `runAfter`
hook mechanics), `web/index.html` (palette, `go()`, `openClip()`, globals `S`/`D`, dialog
`#clipdlg` + `#ed_picbox`, the `data-act="openpics"` button), `studio/api_overlay.py` (all
overlay routes), `studio/overlay.py` (`library()`, `clean_items()`).

## Every check run

1. **Page shell** — `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8798/app/pictures` → **200**.
2. **Assets load** — `/assets/feat` → 200; `/assets/feat/pictures.js` → 200;
   `/assets/feat/pictures-dialog.js` → 200. Both files are loaded by the plugins.js loader
   (`web/plugins.js:248`, `s.src = "/assets/feat/" + f`), served from `web/feat/` by
   `studio/server.py:497-501`.
3. **Live API** — `GET /api/overlays` → 200 (3 images, each carrying `name`/`bytes`/`width`/`height`);
   `GET /api/overlays/templates` → 200; `GET /api/overlays/image/no-such-thing.png` → 404
   (correct "not on the shelf" path, `api_overlay.py:104-105`).
4. **All 10 routes the two files call exist** in `studio/api_overlay.py`:
   `GET /api/overlays` (:57), `POST /api/overlays/upload` (:68),
   `GET /api/overlays/image/{name}` (:99), `GET`+`PUT /api/overlays/templates` (:117, :125),
   `DELETE /api/overlays/templates/{tid}` (:141),
   `GET`+`PUT /api/jobs/{jid}/clips/{cid}/overlay` (:152, :169),
   `GET /api/jobs/{jid}/clips/{cid}/overlay/preview` (:273),
   `PUT /api/jobs/{jid}/overlay-template` (:291). No 404 route risk.
5. **Response shapes the page reads all exist server-side**: `clip.line`
   (`api_overlay.py:163`, `overlay.describe(items)`), `clip.template_name` (:162),
   shelf rows with `width`/`height` (`overlay.py:140-141`), `note` fields on every list route.
6. **Entry point reachable** — the page registers `hidden: true` (`web/plugins.js:85` honors it,
   so it stays out of the sidebar by design); the only way in is the clip dialog's
   "Open the picture editor" button, `data-act="openpics"`, which exists at `web/index.html:2779`.
   `openpics` closes the dialog and `go("pictures")` (`pictures.js:555-563`).
7. **Dead-handler sweep** — `wire()` is only registered under `after.drawSettings`
   (`pictures.js:553`), but `plugins.js` `runAfter` (`web/plugins.js:116-130`) deliberately runs
   every plugin's `after.drawSettings` hook against a page view after its `load` finishes, so the
   pointer-drag, slider, align-grid, layer, shelf and template handlers are all live. Every
   `data-*` hook the markup emits (`data-align`, `data-layer`, `data-picadd`, `data-tpluse`,
   `data-tplget`, `data-tpldrop`, `data-dlg-tpl`, `data-transform`) has a handler.
8. **Regex byte-check** — the name-prettifying regexes at `pictures.js:202` and `:293`
   (`/-[a-f0-9]{6}(?=\.)/i`, `/\.[a-z]+$/i`) verified single-backslash at byte level (`od -c`).
   The `\\.` seen in text dumps is display escaping, not file content.
9. **Bare-name globals exist** — `S` (`web/index.html:1145`), `D` (`:1149`),
   `go(v, tab)` (`:1461`; `st.view` is a view-name string because `go` does `S.view = v`),
   `openClip(jid, cid)` (`:2719`). `D`, `go`, `openClip` are `typeof`-guarded in
   `pictures.js:557,563,569`. The `pics_back` fallback `go("library")` targets a real view
   branch in `go()` (`index.html` `else if (v === "library")`).
10. **Contrast (computed `(L1+0.05)/(L2+0.05)`, small text judged at 4.5)** —
    `--dim #A3A3A3` on `--field #141414` = **7.30** (align buttons, range outputs);
    `--dim` on `--card #111111` = **7.49** (field labels, summary, status);
    `--faint #A0948C` on `--card` = **6.39** and on `--field` = **6.24** (notes, thumb labels);
    `--text #F5F5F5` on `--card` = **17.4**. `--faint` resolves to `#A0948C` inside `#main`/`dialog`
    via `web/feat/polish-contrast.js:29`. Every pair passes; **no text below 3:1**.
11. **390px viewport** — `.pics-body` collapses to one column at ≤1000px (`pictures.js:102`);
    `.pics-canvas` is 405px with `max-width:100%` (:48); `.pics-position` becomes 148px at ≤640px
    with 44px align buttons, summary and handles (:78-79). Nothing measured wider than a 390px
    viewport; the canvas is the widest element and is capped.
12. **9:16 mismatch ruled out** — the base preview frame is rendered server-side at 1080x1920
    with `scale=...:force_original_aspect_ratio=increase, crop=..., setsar=1`
    (`api_overlay.py:250-251`), so the client's `aspect-ratio:9/16` canvas matches the frame it
    judges against. Fraction-based placement survives a 405-wide editor into a 1080 render
    (design note, `pictures.js:7-8`).
13. **Save-loop state machine** (`pictures.js:368-405`) — `pending`/`revision`/`dirty` flags
    reviewed line by line: saves coalesce (a `save()` call during flight sets `pending=true`),
    a revision mismatch keeps `dirty`, failures set `failed` + toast + unhide the Retry button
    (:160, :573). No lost-update path found.
14. **Escape sweep** — every interpolated name/message goes through `esc()`
    (`pictures.js:291-293`, `:303-310`; `pictures-dialog.js:33-48`, `:58`); toasts receive raw
    message text (text context, safe). No unescaped server text reaches `innerHTML`.
15. **Loading/empty/error states** — dialog pane ships "Reading this clip…" then content or an
    error line (`pictures-dialog.js:27,58`); page canvas ships an empty state when no clip is
    bound (:327-329); shelf and template lists have empty states (:286-289, :299-301); save has
    status text + Retry. Two gaps found (findings 2 and 3).

## Findings

| severity | where | what | evidence | fix |
|---|---|---|---|---|
| important | `web/feat/pictures.js:48-49,60-61,79` | The rotate and resize handles sit outside the picture bounds (turn handle 36px above the top edge, size handle 14px past the bottom-right corner) while the canvas clips at its box (`.pics-canvas{overflow:hidden}`). Any picture whose top edge is within ~36px of the canvas top — stickers and posters at the top: the common case — silently loses its rotate handle, and items near the bottom-right edge lose the size handle. `overflow:hidden` clips painting **and** pointer hit-testing, so a clipped handle cannot be clicked | Canvas is 405px wide → 720px tall, so the top 36px is the top 5% of the frame. CSS lines cited; rotation remains possible via the slider, position via the inputs | Draw the handles inset within the picture bounds, or set `overflow:visible` on `.pics-canvas` and clip only the frame `img` (wrap the frame, not the handles) |
| important | `web/feat/pictures.js:112-114,332` | Re-opening the editor for the same clip shows stale state: `state()` resets `S` only when the clip id changes, and `load()` skips the overlay refetch when `active.ready` is already true. Leave via "Back to clip", change the layout in the clip dialog's Pictures pane (which PUTs `/api/jobs/{jid}/overlay-template` for all clips), reopen the editor → it draws the old items and the old `tplName` and previews the wrong template | `load()` guard `if (active.jid && active.cid && !active.ready)`; `state()` reset compares only jid/cid; the dialog-pane PUT changes `clip.overlay_template` behind the editor's back | Drop the `!active.ready` guard so every page load refetches the clip overlay — it is one GET, and the base frame is already cached per `previewAt` |
| important | `web/feat/pictures.js:331,286-289` | A failed picture-library fetch is swallowed (`api("/api/overlays").catch(() => null)`) and the shelf then renders the empty-state text "No pictures yet. Add a logo or a poster and it stays here." — a network error is indistinguishable from an empty shelf, with no toast and no retry. The outer try/catch only toasts the clip-overlay await; the shelf promise is nulled on error | `.catch(() => null)` at :331; `drawShelf()` empty branch at :286-289 | Keep the rejection and render "The picture library could not be opened." in the grid with a Retry link (the page already has the retry pattern at :160/:573) |
| minor | `web/feat/pictures-dialog.js:25-26` | The dialog pane caches per clip (`box.dataset.key`) and never refreshes: after changing the layout in that pane, closing and reopening the dialog for the same clip shows the stale select and hint, contradicting what was just saved | The guard `if (box.dataset.key === D.jid + "/" + D.cid) return;` skips the fetch on every later draw for that clip | Refetch on each `drawClipDlg` (one cheap GET) or rewrite `box.innerHTML` in the change handler |
| minor | `web/feat/pictures-dialog.js:46-48,51-55` | After choosing a layout in the pane's select, the hint under it does not update — it still describes the old layout until the dialog is redrawn | The hint is static innerHTML; the change handler only toasts | Update the hint inside the change handler from the response (`out.name`/`out.note` are already sent by `api_overlay.py:309-310`) |
| minor | `web/feat/pictures-dialog.js:51-55` | The select keeps the newly chosen value when the PUT fails, so the control contradicts the toast and the server state | No revert on catch | Revert `sel.value` to the previous template on error |
| minor | `web/feat/pictures.js:210` vs `:132` | Once a picture is selected, the "On this clip" help line is replaced by the bare file name (e.g. "logo"), so the instruction disappears and a beginner may not connect the name to the selection; two different default texts also exist (body() ships "Select a picture to move or resize it.", `syncControls` rewrites it to "Choose or upload a picture from the library below.") | `on.textContent = it ? pictureName(it.name) : ...` — textContent assignment, two literal strings | Keep an instruction with the name: `logo — drag it, or use the sliders below` |
| minor | `web/feat/pictures.js:156,574-579` | Layer ordering is one-way: only "Bring to front" exists, so a picture can never be lowered except by removing and re-adding it | Single splice-to-end handler in `pics_nudgedown`; no send-to-back action anywhere | Add a "Send to back" button (splice to index 0) next to "Bring to front" |
| minor | `web/feat/pictures.js:141,143,152` | The size/rotation/opacity value `<output>`s are `aria-hidden="true"`, so a screen-reader user never hears the actual values, only native range announcements | `aria-hidden="true"` on the three outputs | Drop `aria-hidden` and give each range an `aria-valuetext` (or announce via the output) |
| minor | `web/feat/pictures.js:89` | Thumbnail labels are 10px and clamp to one line — long names truncate to a sliver. Contrast passes (`#A0948C` on `--field` 6.24:1) but 10px is at the edge of legibility | `.pics-thumb b{font-size:10px}` | 11-12px, keep the ellipsis |
| minor | `web/feat/pictures.js:147-148` | "Across (%)" / "Down (%)" are not beginner-obvious (they are the picture's x/y position inside the frame) | Literal labels in the Precision details block | Rename to "Left-right (%)" / "Up-down (%)" |

## Checked and found correct (deliberate non-findings)

- `\\.` in text dumps of `pictures.js:202,293` — byte-checked (`od -c`), the file holds single
  backslashes; both regexes are correct.
- `wire()` hooked only to `after.drawSettings` — `plugins.js:113-130` fires the hook for page
  views after load; handlers are live.
- `hidden: true` page — honored by `web/plugins.js:85`; reachable via the dialog button
  (`web/index.html:2779`).
- 9:16 canvas vs frame — the server renders the base frame at 1080x1920
  (`studio/api_overlay.py:250-251`); no misalignment for non-9:16 sources.
- Save-loop races — coalesce correctly; the failure path shows status, toast, and the Retry
  button.
- Contrast — all resolved pairs computed and passing (see check 10).
- All routes, all response shapes, all entry points verified live against the running server.
