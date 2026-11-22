# QA audit — All videos page (`/app/videos`), overview + library views, and `web/feat/filters.js`, `heard.js`, `pill.js`, `log.js`, `keys.js`

Audit wave, 2026-11-22. One auditor's report per the contract in `docs/qa/CONTRACT.md`.

## Files and pages owned

- PAGE: `/app/videos` (the library view; audited with `/app/overview`, which draws the same shell)
- FILE: `web/index.html` — the overview and library views only (`#ov` at `web/index.html:1472`, `#add`/`#jobs` at `:1473`, plus the shared shell CSS those views use)
- FILE: `web/feat/filters.js` (212 lines, read in full)
- FILE: `web/feat/heard.js` (73 lines, read in full)
- FILE: `web/feat/pill.js` (173 lines, read in full)
- FILE: `web/feat/log.js` (116 lines, read in full)
- FILE: `web/feat/keys.js` (173 lines, read in full)

## Checks run

1. **Page shells over HTTP** — `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8798/app/videos` → **200**; `/app/overview` → **200**.
2. **Full reads** of all five feature files and the owned `index.html` regions (CSS `17-22`, `78`, `125-223`, `238-262`, `300-318`, `425-466`, `523-598`, `828-882`, JS `930`, `1037`, `1341-1501`, `1890-2203`).
3. **Syntax** — `node --check` on all five files → **OK** ×5.
4. **Every route the pages call exists in `studio/`**:
   - `GET /api/clips.zip` — `studio/server.py:1134`
   - `POST /api/live/{jid}/clip` — `studio/server.py:1382` (the "Clip last 30s/60s" buttons)
   - `POST /api/live/{jid}/stop` — `studio/server.py:1373` (Stop recording/Stop)
   - `POST /api/posts/{pid}/{action}` — `studio/server.py:1820` (Cancel/Retry in the Post queue)
   - `GET /api/jobs/{jid}/review` — `studio/api_review.py:89`, `PATCH /api/jobs/{jid}/clips/{cid}` — `studio/api_review.py:98` (review page, context for keys.js)
5. **Handlers for every `data-act` the views paint** (dispatch is an if/else chain on `a === "..."` in the document click listener, `web/index.html:3113-3410`): `go` `:3113`, `step` `:3199`, `copyall` `:3258`, `seldl` `:3283`, `selclear` `:3284`, `selall` `:3285`, `seldel` `:3290`, `deljob` `:3313`, `stoplive` `:3341`, `clipnow` `:3348`, `report` `:3403`, `pause` `:3409`, `pcancel`/`pretry` `:3410`. No dead handlers found.
6. **Feature-file plumbing** — `web/plugins.js` hook signatures match all five files: act handlers called `await fn(b, e)` (`plugins.js:165`); `watch()` maps `#jobs`→`drawJobs`, `#ov`→`drawOverview`, `#clipdlg`→`drawClipDlg`, `.topbar`→`drawShell` (`plugins.js:187-194`); `wireKeys` calls `await fn(e) === true` → `preventDefault` (`plugins.js:204`); boot repaint 250 ms + rAF (`plugins.js:266-268`); files loaded from `/assets/feat` (`plugins.js:245`).
7. **`pill.js` targets exist** — `toLibrary()` clicks `#nav [data-act="go"][data-v="library"]`; that row is painted by `nav("library", …)` at `web/index.html:1343` through the `drawShell` template `:1341`. The `pcrungo` fallback `location.href = "/app/videos"` also resolves.
8. **Escaping** — `const esc = s => String(s ?? "").replace(/[&<>"']/g, …)` is defined globally at `web/index.html:930`; every untrusted interpolation in the owned regions (`jobHtml` meta/title, `liveHtml` stats/lines, `log.js` box lines, clip titles) goes through `esc()`.
9. **Contrast, measured** (WCAG 2.2 `(L1+0.05)/(L2+0.05)`; `--faint` resolves to `#A0948C` inside `#main`/`dialog` per `web/feat/polish-contrast.js`):
   - pass: `.pill` `--dim #A3A3A3` on `--muted #111111` → 7.54; `.pill.ok` `#34D399` on `#0B2A1E` → 8.01; `.pill.bad` `#F87171` on `#2B1416` → 6.25; `.pill.warn` `--brand-deep` on `--brand-soft` → 9.43; `.btn.primary` `#160D05` on `#FF8B33` → 8.22; `.btn.danger` `--bad` on `--bad-soft` → 6.25; `.btn.ghost` `--dim` on `--bg` → 7.84; `.kpi b/span` 18.16 / 7.85; `.tile b/span/i` ≥ 7.85; `.step b/.d/.n` (`web/index.html:531-533`) 19.6 / 7.54 / 16.6; `.chart text` `#A0948C` on `#0A0A0A` → 6.70; `.chart .none` → 7.84; `#selbar` (`:580-588`) text 16.65, danger 8.82, primary 7.72; `.heard .rail` fill `--brand` on `--line #1E1E1E` → 7.14
   - **fail: `.pcrun-2` `--dim #A3A3A3` on `#FFF7F0` → 2.38, on `#FFF3F3` → 2.33 (finding 1)**
   - **fail: `.pcrun.is-wait:hover` `--dim` on `#F1ECE7` → 2.15 (finding 2)**
   - **fail: `.chart .b2` `--brand-ink #160D05` on `#0A0A0A` → 1.03 (finding 3)**
   - **fail: `.pill.live` `#fff` on `--live #EF4444` → 3.76 at 12px/600 (finding 4; same finding as `docs/qa/audit/creators.md` finding 1, which measured the proposed fix `#160D05` on `#EF4444` → 5.10, pass)**
10. **390px viewport** — `.home-grid` collapses to `1fr` at ≤1100px (`web/index.html:817`), `.two` at ≤560px (`:836`); `.shot{width:100%}` (`:562`); `main#main{overflow-x:hidden}` (`:873`); `#selbar{max-width:calc(100vw - 24px)}` (`:580`); the Creators table sits in `.scroll{overflow-x:auto}` (`:619`). No element wider than the viewport.
11. **States** — filters.js: search-empty line "Nothing matches that." + "Clear the search, or pick All." (`filters.js:143-155`), idempotent counts, hides the card empty-state only while a filter/search is active (`:157-193`); log.js: loading "Reading the log..." / error / empty "This video has no log written for it." / lines, all escaped (`:31-38`); heard.js returns `""` when the job carries no duration or parts (`:31-51`); `drawJobs` empty states with guidance (`index.html:1990-1993`); `drawOverview` creators-empty with guidance (`:2126`); `drawReview` empty (`:2193`). The Post queue empty state is the one bare one (finding 9).
12. **Motion** — heard.js shimmer has `prefers-reduced-motion` (`heard.js:11-12,18`); pill.js/keys.js intervals repaint only, no animation.
13. **Key-hijack guards** — keys.js checks `typing()`, `formOpen()`, `#formdlg`, other dialogs, and the tour (`keys.js:44-71`), guards `e.repeat` (`:83`), and clicks the real `[data-act]` buttons so its logic cannot drift from the page's (`:86-94`).
14. **Hypothesis disproven** — `log.js:27` box-id regex: raw bytes are `/[^\w-]/g` (single backslash `5c 77`), correct; the same precedent clears `log.js:37` `join("\n")` as a real newline. Not bugs.

## Findings

| severity | where | what | evidence | fix |
|---|---|---|---|---|
| critical | `web/feat/pill.js:20` | The pill's secondary clause ("· N videos running") is near-unreadable: `--dim #A3A3A3` text on the light pill backgrounds | 2.38:1 on run-kind `#FFF7F0` (pill.js:7), 2.33:1 on rec-kind `#FFF3F3` (pill.js:10); 13px text needs 4.5. Shown whenever kind=rec and running>0 (words() pill.js:60-65 sets it, paint() :138 toggles `.pcrun-2` on) | Give `.pcrun-2` a dark per-kind colour (e.g. `#8A3C08` on `#FFF7F0`, `#9E121B` on `#FFF3F3`) instead of `var(--dim)` |
| critical | `web/feat/pill.js:13` | Hovering the wait-state pill flips it light while the text stays light grey: the label vanishes exactly when the user points at it | `.pcrun.is-wait:hover{background:#F1ECE7}` with text still `var(--dim) #A3A3A3` = 2.15:1 during hover (resting 7.54:1 is fine) | Keep the hover dark (e.g. `background:var(--line)`) or set a dark ink colour for the hover state |
| critical | `web/index.html:445` + `:2125` | The overview Activity chart's "Posted" bar series and its legend swatch are near-black on the near-black card: the whole second series is invisible | `.chart .b2{fill:var(--brand-ink)}` `#160D05` on card bg `--bg #0A0A0A` (`.card{background:var(--bg)}` `:238`) = 1.03:1; bars drawn at `:2094`, legend `<i style="background:var(--brand-ink)">Posted</i>` at `:2125` | Fill `.b2` with a visible second colour (e.g. `--brand-deep #FFB27A` → 8.9:1, or `--dim #A3A3A3` → 6.7:1) and match the legend swatch |
| important | `web/index.html:258` | `.pill.live` (the "Live"/"Recording" chips) is below WCAG AA for its 12px/600 text | `#fff` on `--live #EF4444` = 3.76:1, needs 4.5. Painted at `:1901` (livecard head) and `:2113` (overview Creators state()) | Swap to dark ink `--brand-ink #160D05` on `#EF4444` → 5.10 (measured in `docs/qa/audit/creators.md`), or darken the bg to `#DC2626` (4.54) |
| important (usability) | `web/index.html:2194` vs `web/feat/keys.js:23-27` | Two contradictory keyboard legends on the review page: the help text says "A says yes to the next clip, X says no, S skips ahead"; the keys.js hint says "Enter approve / Backspace reject / Right next clip". Both sets work (keys.js:6-8 deliberately leaves a/x/s alone) but neither mentions the other, so a beginner cannot tell which legend is real | `index.html:2194` help copy; `keys.js:23-27` `HINT_REVIEW`; `keys.js:6-8` leaves a/x/s to the page handler; both fire (`:86-94` clicks real buttons) | One legend that names both sets (e.g. "Enter or A — approve · Backspace or X — reject · Right or S — next"), or align the two texts |
| minor | `web/feat/pill.js:12` | The wait-state pill is a dark rectangle on the dark topbar: weakly visible until read | bg `--muted #111111` on topbar `--bg #0A0A0A` with border `--line-2 #2A2A2A` → boundary ≈ 1.33:1 (the text itself passes at 7.54:1) | Slightly lighter pill bg (`--line #1E1E1E`) or a stronger border |
| minor | `web/feat/filters.js:17-18` | Same weak-boundary pattern on the filter pills | `.pcf-pill` bg `--bg` on the page bg with border `--line #1E1E1E` → boundary 1.33:1 | Same: lighter bg or stronger border |
| minor | `web/index.html:2132` vs `:2124` | Copy inconsistency: the KPI card says "Est. earnings", the Creators table header says "Est. $" | Both strings in `drawOverview` | Pick one label ("Est. earnings") for both |
| minor (usability) | `web/index.html:2140` | The Post queue empty state gives no next action, unlike every other empty state on the page | Bare `<p class="help">Nothing queued or posted yet.</p>`; compare `:1990-1993` and `:2126` which tell the person what to do | Add one line: what queues a post (approved clips + autopost on) and a link to All videos or Settings |
| minor | `web/feat/filters.js:33` | `display:none!important` — `!important` is on the fix-wave ban list | `[data-pcfilter="out"]{display:none!important}` | Works today; replace with a higher-specificity selector in the fix wave |

## Cleared

- Both pages 200; all five files parse; no dead handlers (16/16 verified); no missing backend routes.
- All contrast pairs not listed above pass WCAG AA for their size (measured values in check 9).
- `log.js` regex and `join("\n")` byte-verified correct; `heard.js` respects `prefers-reduced-motion`; `keys.js` guards every hijack path; `filters.js` owns its strings via `textContent` and has search/empty/escape states.
- No element overflows a 390px viewport; the Creators table scrolls inside its card like every other wide table in the app.
