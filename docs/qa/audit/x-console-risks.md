# Cross-cutting console-risks audit — web/feat/*.js

Auditor: agent-157 (cross-cutting, 40-agent QA swarm) · Repo: peakcut · Server: http://127.0.0.1:8798 (curl only; no browser used — lead owns the browser during this audit).

**Scope owned:** every feature file under `web/feat/` — 76 files scanned (75 feature files + `_example.js`). No single page owned; this is the static console-risk sweep across all of them, against `web/plugins.js`, `web/index.html` helpers and the server route table in `studio/`.

**Method:** ops_grep / ops_glob / ops_inspect_local_file for static work; curl against http://127.0.0.1:8798 for live checks. Skill loaded: systematic-debugging (root cause before fixes; every finding verified to its source line before reporting; one false positive retracted — see "Retracted finding").

---

## Checks run

| # | Check | Result |
|---|---|---|
| 1 | Feature inventory (`ops_glob web/feat/*.js`) | 76 files: 75 feature files + `_example.js` template |
| 2 | Framework reading — `web/plugins.js` in full | `P.add/P.css/P.page/P.toast/P.send/P.api` etc. (24 members); `wireActs` = one click listener on `[data-act]`, silently ignores unknown acts (plugins.js:151-167); `drawPage` catches page-load errors → toast "That page could not finish loading." + console.warn (plugins.js:133-134); feat files load as **classic scripts** (plugins.js:246-251), so `index.html` globals resolve |
| 3 | `index.html` helper reading | `esc` :930, `ic` :992, `api` :999-1004, `send` :1005, `toast` :1006-1011, `S` :1145, shared ACTS switch :3196-3465 |
| 4 | Server route table | 195 routes total: 193 `@app/@router` `.get/.post/.put/.patch/.delete` decorators across `studio/server.py` + `studio/api_*.py`, plus 2 `api_route` (`studio/api_memesound.py:198`, `studio/api_sound.py:121`, both GET,HEAD); `/assets/feat` listing handled inside `@app.get("/assets/{name}")` `studio/server.py:465-467` |
| 5 | **Route diff: every fetch/send path vs studio routes** | Every `/api/` literal in `web/feat/*.js` (128 hits) resolves to a server route. **0 missing, 0 404s.** `pictures.js` defines its own send wrapper defaulting to PUT (pictures.js:106) — its `PUT /api/overlays/templates` matches. `peek.js:57-60` builds `"/api/jobs/"+jid+"/peek/"+cid` unencoded, but both ids pass the allowlist `/^[A-Za-z0-9_-]+$/` (`okId`, peek.js:53) at :148/:154 before use — safe |
| 6 | **innerHTML without esc — XSS scan** | 130 `innerHTML` sites in 49 files. **All verified escaped or in-file constant** (no untrusted interpolation). Details per file below |
| 7 | **Undefined global refs** | Clean. All `P.*` references defined (plugins.js 24 members + helpers registered by feat files: `P.icon`/`P.iconHtml` menu-icons.js:37/55, `P.menuGroup`/`P.menuGroups`/`P.pageRows`/`groupFor` menu.js:74-77, `P.empty` polish-empty.js:39, `P.loading` polish-loading.js:54). Zero module-scope cross-file calls (grep `^(const|let|var) \w+ = (P|window\.PeakCut|PeakCut)\.\w+\(` → 0 hits), so load order cannot throw today |
| 8 | **`$` vs `document.querySelector` misuse** | Clean. Every `$`/`$$` call site is in a file defining the helper locally (keys.js:32-33 = querySelector wrappers; audio-edit.js:139 and audio-page.js:112 = getElementById wrappers used consistently with in-file element ids). No file relies on an undefined global `$` |
| 9 | Icon names used by feat files | All 12 `ic()` names exist in `index.html`'s `I` map: caret :938, chart :940, film :941, cog :942, plus :943, copy :948, trash :950, x :951, check :960, clock :961, plusc :978, arrowr :975 |
| 10 | **Dead `[data-act]` handlers** (wireActs silently ignores unknown acts → a button with no handler does nothing) | All 54 distinct literal act names used in `web/feat` have handlers: feat `act:{}` blocks, the shared ACTS switch in `index.html` (collapse :3196, toggleopts :3197, closedlg :3209, openaudio :3210, openclip :3226, newcreator :3227, remake :3421, rvapprove/rvreject :3443, rvskip :3444), and `pcpage` in plugins.js:156. Dynamic acts from keys.js:91 (`rvapprove`/`rvreject`/`rvskip`) render from index.html:2176-2178 pills and are handled — plus keys.js falls back gracefully (`if (!btn) return false`, keys.js:92) |
| 11 | Live curl checks vs http://127.0.0.1:8798 | All HTTP 200: `/app`, `/app/analytics`, `/app/sounds`, `/assets/feat` (75 files + `_example.js`), `/assets/feat/pill.js`, `/assets/feat/history.js`, `/api/status`, `/api/analytics/summary`, `/api/overview`, `/api/usage`, `/api/moods`, `/api/captions/styles`, `/api/formats`, `/api/hunt/watching`, `/api/creators`, `/api/trends/saved` |
| 12 | Loading / empty / error states | Present where they matter: `P.loading` (polish-loading.js:54), `P.empty` (polish-empty.js:39), tool-draw errors escaped inline in `P.toolsHtml` (plugins.js:216-218), page-load errors toasted (plugins.js:133-134), per-builder fail/empty lines esc'd (e.g. analytics-trends.js:78-81, analytics-table.js:203-212) |

### innerHTML scan details (check 6)

Every `innerHTML` target was read at its source line. Representative verification:

- **analytics-trends.js** — every `r.term`/`r.url`/`r.title`/`r.channel`/`interest` through `esc` (:185-237); bar width numeric (:189); `chip()` :235-238; `failLine`/`noteLine`/loading :78-81; `section()` :167-171.
- **meme-timeline.js** — `esc` on title/slug/about/`e.message`.
- **creators.js** — face/chips/accountLine/trackLine/clipsLine/card all esc'd; `sentence()` defined locally (:80).
- **live.js** — `row`/`said` esc'd (:108-150); summary counts computed client-side; `sentence()` local (:187).
- **peek.js** — local `esc` :43-44; strip/take nodes esc'd (:73-83); node() :62-66 template uses only allowlisted ids.
- **formats.js** — `esc` everywhere (:208-209, :223, :301-307, :404); `tileHtml` uses `encodeURIComponent` for `/api/style/preview?style=` (:303).
- **pictures.js** — all esc'd or `encodeURIComponent` (:189-196, :216-217, :246, :276, :291-309, :333-633); in-file constant labels only.
- **log.js** — `escHtml` :26/:37 (lines.map(esc), errorText esc'd); `CSS.escape` for querySelector.
- **style-tiles.js** — `label = esc(x.label)` :184; `data-style` esc'd :186; `encodeURIComponent` for preview img :188.
- **grid.js** — `esc` :123; paint() :130-133; remount() :139-149 via `P.toolsHtml()` (escapes internally).
- **history.js** — block() :117-136: `esc` jid/cid/tip/t; numeric counts.
- **keys.js** — `innerHTML` = fixed in-file markup only (:24-30, :38), comment documents why no escaping needed (keys.js:22).
- **mood.js** — optionHtml: `esc(m.name)` both value+label (:78-81); group label esc'd (:85); say() textContent (:92-100).
- **analytics-table.js** — head()/cell()/row() esc'd (:136-157); `<option value="${d}">` numeric only (DAYS array, :169-179); input value esc'd (:179).
- **usage.js** — all esc'd (:116-121, :158-186 numeric SVG + esc titles, :196-248, :258-265).
- **audio-edit.js** — no template literals; string-concat builders all esc'd (:254-257, :442-443); in-file constants elsewhere.
- **audio-page.js** — no template literals; card() fully esc'd (:307-330); `icon()` has `paths[name] || ""` fallback (:341).
- **learn-report.js** — `esc` :31; host.innerHTML fixed markup only.
- **polish-errors.js** — own `escHtml` (:18). **polish-loading.js** — ${text} built in-file (:105).

---

## Findings

| Severity | Where | What | Evidence | Fix |
|---|---|---|---|---|
| minor | `web/feat/audio-page.js:321` | Dead ternary — both branches identical, so the "like" icon never changes with state | `(liked ? icon("heart") : icon("heart"))` on line 321 | Replace the ternary with `icon("heart")`. Not user-facing: state is still visible via `aria-pressed` + CSS `.alb-mini[aria-pressed="true"]` — but the code misleads readers into thinking the icon is state-driven |
| minor | `web/feat/audio-page.js:313` | The globe icon shown instead of a duration carries no explanation — a beginner cannot tell it means "in the catalogue, not on this machine yet" | `known(r.seconds) ? esc(secsBare(r.seconds)) : icon("web")` — icon rendered with no `title` and no text, while every neighbouring button has a `title` (:318, :321, :323, :327, :328) | Add `title="In the catalogue, not on this machine yet"` to the `.alb-ico` span (or a short text hint) |
| minor | `web/feat/menu-pages.js` + `menu.js:74-77` + `menu-icons.js:37/55` + `polish-empty.js:39` + `polish-loading.js:54` | Cross-file helper load-order fragility (convention note, no runtime error today): helpers defined in one feat file are called from another; safety depends on alphabetical `/assets/feat` load order staying favourable | menu-pages.js calls `P.menuGroup`/`P.icon` defined in menu.js and menu-icons.js, which sort earlier (menu-icons.js < menu-pages.js < menu.js). Verified safe today: helpers are only called at boot, never at module scope (grep of module-scope cross-file calls → 0 hits) | Keep the convention: cross-file helpers may only be called at boot/load, never at module scope; or move the shared helpers (`P.icon`, `P.menuGroup`, `P.empty`, `P.loading`) into `web/plugins.js` so order stops mattering |

### Observation outside owned scope (for the index.html owner to triage)

- `web/index.html:992` — `const ic = n => \`${I[n]}\`` has no `||""` fallback (compare `admin.html:198` which has `${I[n]||""}`), so an unknown icon name renders the literal text "undefined" inside the `<svg>`. No current `web/feat` caller passes an unknown name (check 9), so this is latent. `web/feat/polish-icons.js:10` documents the quirk. Not counted as a finding of this audit because `web/index.html` is not in this auditor's scope.

---

## Retracted finding (transparency)

An earlier pass reported "undefined global `sentence()`". That was a **false positive caused by the auditor's own tooling**: the first grep used `path=web` with glob `["*.html","*.js"]`, which matches the top level only and never descended into `web/feat/*`. Every file that calls `sentence()` defines it locally: creators.js:80, streamer-mode.js:96, live.js:187, audio-edit.js:142, audio-page.js:118, formats.js:86, learn-signals.js:65. Lesson recorded: globs do not descend — verify a global is truly undefined across `web/feat/*` before reporting.

---

## Usability notes (static scan)

The sweep did not surface any beginner-hostile copy in the 49 files with `innerHTML` builders: copy is consistently plain language with next-step guidance (e.g. peek.js "Not checked yet. Press Look again and this fills in."; formats.js:480 "Customize text and colors" opens the brand page in one step; keys.js hints "Enter approve / Backspace reject / Right next clip"). One usability gap found is in the findings table (the unexplained globe at audio-page.js:313). A full visual/contrast pass was not in this auditor's scope — the lead's browser pass should cover it.

## Verdict

No critical or important findings. The feature-file surface is clean on all four assigned checks: every fetch path maps to a live server route, no unescaped `innerHTML`, no undefined globals, no `$` misuse, and every rendered button has a handler. Three minor polish items, all in `web/feat/audio-page.js` plus one convention note.
