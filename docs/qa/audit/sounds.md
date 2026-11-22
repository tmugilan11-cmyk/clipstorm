# Audit: Sounds page (/app/sounds) and its two feature files

Auditor: agent-134, QA swarm audit wave. Skill loaded first: systematic-debugging.
Rules followed: docs/qa/CONTRACT.md (measured findings only, no browser, one owner per file).

## Files and pages owned

- Page: `/app/sounds`
- File: `web/feat/sounds.js` (403 lines) - the Sounds page itself: the meme noise list, the music bed list, Play, and "Build the missing sounds"
- File: `web/feat/meme-timeline.js` (161 lines) - the "From the web" section the Sounds page gains after its own load (DankMachine catalogue search, keep, upload, remove)

## Every check run

1. Read `docs/qa/CONTRACT.md`; loaded the `systematic-debugging` skill before starting.
2. Read `web/feat/sounds.js` and `web/feat/meme-timeline.js` in full.
3. Page shell: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8798/app/sounds` - **200**, checked twice.
4. Byte-level check of both owned files (python count of backslash runs) to confirm the escape sequences the file inspector renders ambiguously: `meme-timeline.js` contains `/\s+/`, `"\u00b7"`, `"\u2026"` as single-backslash escapes (correct JS, renders "·" and "…"); `sounds.js` contains the correct `CSS.escape` fallback `/["\\]/g, "\\$&"`. No literal escape-code text is drawn on the page.
5. Harness trace: `web/plugins.js` (`P.add`, `P.page`, `P.drawPage`, `runAfter`, `repaint`, `boot`) and `web/index.html` (`api()` at 999, `send()` at 1005, `go()` at 1461, `remember()` at 1442, `pathFor()` at 1405, `fromPath()` at 1426). Confirmed:
   - `P.drawPage` runs the `after.drawSettings` hook after the page's own `load()` resolves, so the From-the-web section is appended on the Sounds page (not dead).
   - `api(path, opt)` passes `opt` straight to `fetch`, so meme-timeline's POST/DELETE/FormData calls are wired; non-OK answers throw with the server's `detail` in `.message`, which both files surface.
   - `pathFor()` maps the registered page to `/app/sounds`, so the address bar follows `go("sounds")`.
6. Routes: grepped every `/api/...` address the two files call against `studio/*.py`. All 10 exist:
   - `GET /api/moods` (api_sound.py:58), `GET/HEAD /api/sounds/{kind}/{mood}` (api_sound.py:121, HEAD listed explicitly), `POST /api/moods/prime` (api_sound.py:155)
   - `GET /api/memesounds/search` (api_memesound.py:81), `GET /api/memesounds/for` (96), `GET /api/memesounds/library` (130), `POST /api/memesounds/keep` (138), `DELETE /api/memesounds/library/{slug}` (154), `POST /api/memesounds/upload` (162), `GET/HEAD /api/memesounds/play/{slug}` (198)
   No 404/500 route from either file.
7. Live read-only curl against 127.0.0.1:8798:
   - `/api/moods` - `{moods, count, meme, music}`, 13 rows (9 meme, 4 music), all `ready: true` on this install. Notes are the finding below.
   - `HEAD /api/sounds/meme/shock` - 200. `HEAD /api/sounds/music/chill` - 200. `HEAD /api/memesounds/play/vine-boom-longer-22911` - 200.
   - `/api/memesounds/library` - 200, `{sounds:[{slug,title,seconds,bytes}], folder, note}`, 4 rows.
   - `/api/memesounds/search?q=boom` - 200, `{query, sounds, kept}`, 12 rows with slug/title/about.
   - `/assets/feat` - lists both owned files, so both load at boot.
8. Contrast, computed as `(L1+0.05)/(L2+0.05)` for the resolved pairs the two files draw (12px-13px text, so 4.5 applies):
   - `--dim` #A3A3A3 on `--bg` #0A0A0A (`.snd-note`, `.mtlweb .help`, `.help`): **7.85:1** - pass
   - `--dim` #A3A3A3 on `--muted` #111111 (`.pill` "Not built" / "N of M built"): **7.49:1** - pass
   - `--good` #34D399 on `--good-soft` #0B2A1E (`.pill.ok` "Ready"): **8.01:1** - pass
   - `--bad` #F87171 on `--bg` (`.err`): **7.16:1** - pass
   - `--faint` on `--bg` (`.snd-say`, `.hint`): the index.html base #7C7C7C computes **4.74:1** - pass; `web/feat/polish-contrast.js` raises it to #A0948C (**7.24:1** per its header) at boot. No contrast finding.
9. Escape audit of every `innerHTML` interpolation in both files: row labels, notes, titles, slugs, error messages all go through `esc(...)` or `textContent`. No untrusted text reaches markup unescaped.
10. Narrow-viewport walk (390px): `.snd-row` uses `flex-wrap:wrap` with name/note going full-width at the 560px breakpoint (sounds.js:33-37); `.mtlweb` result rows use `minmax(0,1fr)` for the name column with ellipsis, so buttons never push the row wider than the screen; the library grid falls to one column at 190px. No overflow found.
11. Loading/empty/error states: Sounds list has loading (sounds.js:362), empty (296), error (290); From-the-web search has searching/empty/error (67, 78, 79); upload has a progress note (142). One gap found (kept-sounds grid, below).

## Findings

| severity | where | what | evidence | fix |
|---|---|---|---|---|
| important | web/feat/meme-timeline.js:108-112 | Every "Listen" press builds a **new** `Audio` and never pauses the previous one, and the panel has no Stop control: pressing Listen on two rows (or twice on one row) plays both copies at once, overlapping, until each file ends. | meme-timeline.js:110 `const a = new Audio("/api/memesounds/play/" + enc(play)); a.play()` - no pause, no tracking of the previous element; the Sounds list 20 lines up in sounds.js:77,106-117 already does this correctly with one shared player. | Reuse one shared `Audio` for the whole section (copy the sounds.js pattern): pause it before each play, remember which row is sounding, and toggle the pressed button between "Listen" and "Stop". |
| important | web/feat/sounds.js:247 | The description under every Meme noises row is a bare visual-gag keyword, not a sound description: all 9 meme rows show "freeze", "push-in", "shake" or "vignette", and the page's own curated sound descriptions (`BY_NAME`, "A trombone, or someone saying hello into a dark room." etc.) are unreachable. A beginner cannot tell what the sound is like from the page. | sounds.js:247 `if (row.note) return row.note;` prefers the server note; studio/api_sound.py:51 `_note` reads keys `("hint","note","label","effect","treatment")` and the mood documents only carry `"treatment"` (studio/meme.py:33,46-62), which is the visual gag applied to the clip (meme.py:1); live `/api/moods` confirms: 9 meme rows with keyword notes, 4 music rows with real sentences. | In `about(row)`, only prefer `row.note` when it reads like a sentence (e.g. contains a space); otherwise fall through to `BY_NAME`. The root cause is `_note()` treating the clip's visual treatment as a mood description - that key list fix belongs to the fix wave (api_sound.py is not this auditor's file). |
| important | web/feat/sounds.js:394-400 | The "stop the sound when you leave the page" listener listens for `hashchange`, but the app navigates with `history.pushState` and never changes the hash, so the listener is dead code: a sound left playing keeps sounding under every page you switch to, with no Stop control there. The page's own comment claims this case is handled. | sounds.js:396 `String(location.hash || "").indexOf("/app/sounds")` on a `hashchange` event; index.html:1444 `remember()` navigates via `history.pushState({v, tab}, "", url)`, and no code in index.html sets `location.hash` (grep found none). `go()` stops the live stream (`window._gaStop`, index.html:1469) but has no hook a feature page can use. | Check the state the app actually changes: pause when `PeakCut.state().view !== "sounds"` (a small interval or a `popstate` listener plus a view-change event from `go()`), or simplest, keep a 250 ms check like plugins.js's own repaint loop. |
| important (usability) | web/feat/sounds.js:69,280,369 with web/index.html:836 | On a phone (viewport 560px or less) every explanatory hint on the Sounds page is hidden by the global mobile rule `.hint{display:none}`: both section subtitles ("A short gag laid over the clip: a horn, a rimshot, a room going quiet." / "A looped bed mixed under the voice, one for each mood.") and the Build button's "pressing it twice costs nothing" reassurance vanish, leaving a bare "Build the missing sounds" button with no explanation of what it builds or that it is safe to press. | sounds.js:69 `const hint = (line) => \`<p class="hint">\``; index.html:836 `@media (max-width:560px){... .hint{display:none} ...}`; the From-the-web section keeps its help visible because it uses `.help` (meme-timeline.js:25), so the two halves of the same page behave differently on a phone. | Add to the sounds CSS block: `@media (max-width:560px){.snd .hint{display:block}}`. Specificity (`.snd .hint`, 0-2-0) outranks the global rule (`.hint`, 0-1-0), so no `!important` is needed and no other page is touched. |
| minor (bug) | web/feat/meme-timeline.js:62-80 | Two quick searches run in parallel and the later-arriving response wins even if it answers the older query, so results can appear for words that are no longer in the box. | `search()` never sequences or aborts the previous request; each response writes `res.innerHTML` unconditionally. sounds.js guards the same shape with the `nowPlaying` check (sounds.js:165,178). | Keep a per-section request token: `const mine = ++reqSeq` before the ask, and inside `then`, `if (mine !== reqSeq) return;`. |
| minor (bug) | web/feat/meme-timeline.js:50-59 | The kept-sounds grid has no loading state: while `/api/memesounds/library` is in flight the area is blank, then rows pop in - the search box directly above it does show "Searching.", so the page is inconsistent about it. | `libList()` writes nothing to `host.innerHTML` until the response (or the catch). | Write `'Reading the shelf...'` into the host before the request, mirroring search() line 67. |
| minor (bug) | web/feat/meme-timeline.js:54 | Dangling separator on a kept sound that has no duration but is uploaded: the small line reads " · your file" with the dot before nothing, because the separator is appended unconditionally when a duration was never drawn. | `` `${r.seconds ? Number(r.seconds).toFixed(1) + "s" : ""}${r.source === "uploaded" ? " · your file" : ""}` `` - with `seconds` missing and `source === "uploaded"` the line starts with the separator. | Add the separator only when a duration was drawn: build the duration string first, then `dur ? dur + " · your file" : "your file"`. |
| minor (usability) | web/feat/sounds.js:254-265 | The quiet line under every row repeats the pill beside it: on this install all 13 rows render "Ready to play." under a green "Ready" pill (on a fresh install, "Not built yet. Use the button below this list to make it." would stack once per not-built row), so the same sentence runs 13 times down the page. | `rowHtml` always renders the `snd-say` span with static copy: sounds.js:256-257, 265 (`aria-live="polite"`). | Start the say-line empty - the pill already carries the state, and `aria-live="polite"` still announces the line when Play or an error fills it later. Keep the per-row guidance only where it teaches something the pill cannot (e.g. only while nothing is built at all). |
| minor (usability) | web/feat/meme-timeline.js:59 | The kept-sounds error says "The shelf could not be read." - the section never calls the kept list a shelf, so a beginner has no word to attach it to. | drawWeb's own copy says "keep a sound here" (line 92); only the error and the server docstrings say "shelf". | "The kept sounds could not be read. Reload the page; if it stays empty, the server log says why." |

## What passed and is worth recording

- Page shell 200; all 10 routes the two files call exist, and both byte routes answer HEAD (sounds.js's play probe relies on it).
- All resolved colour pairs on this page pass WCAG at their sizes (numbers above); no clipped or overlapping text found at 390px or on desktop; no unescaped interpolation; no console-risky pattern (every `play()` rejection is caught, `CSS.escape` is guarded).
- The From-the-web section is correctly appended once per page draw (`drawWeb` bails when `.mtlweb` or `.snd` is missing), and the `after.drawSettings` hook really is run for feature pages (plugins.js:116-141).
- The Sounds page keeps loading, empty and error states, and leaves-the-page audio state is intended to be handled - it just listens for the wrong event.
