# Audit: Insights — Audience + Traffic (agent-138)

Audit of the `/app/analytics` page's **Audience** and **Traffic** tabs and the four feature files behind them, run for the 40-agent PeakCut QA swarm. All work was static (grep / file reads / curl against `http://127.0.0.1:8798`); no browser was used, per `docs/qa/CONTRACT.md`.

## Pages and files owned

| What | Where |
|---|---|
| Page | `/app/analytics` — Audience tab, Traffic tab (served at 200; same shell as `/app/insights`) |
| File | `web/feat/analytics-audience.js` (240 lines — Audience tab body) |
| File | `web/feat/analytics-retention.js` (446 lines — "How far people watched" card on the Content tab) |
| File | `web/feat/analytics-realtime.js` (200 lines — "Right now" card on the Overview tab) |
| File | `web/feat/analytics-traffic.js` (185 lines — Traffic tab body) |

Cross-reads used as evidence (owned by others, not modified): `web/index.html` (palette :17-21, route map :1419, `#main` wrapper :907,912), `web/plugins.js` (282 lines), `web/feat/analytics.js` (shell, 220 lines), `web/feat/analytics-table.js` (`.ant-name` :31,152), `web/feat/analytics-empty.js` (126 lines), `web/feat/polish-contrast.js` (48 lines), `studio/api_analytics.py` (handlers :176-424).

## Findings

| Severity | Where | What | Evidence | Fix |
|---|---|---|---|---|
| Important | `web/feat/analytics-audience.js:20-21` | The "New viewers" bar and its legend dot are invisible on the dark page: `.aa-dot.new` and `.aa-fill.new` use `background:var(--brand-ink)`, which is `#160D05` (near-black) in the signed-in dark theme (`web/index.html:17`), drawn on the `.aa-track` background `var(--muted)` = `#111111` (:21) | Measured (WCAG (L1+0.05)/(L2+0.05)): #160D05 vs #111111 = **0.98:1**; vs #0A0A0A = 1.03:1 — far below the 3:1 non-text bar. The sibling "Returning" bar uses `--brand` #FF8B33 on the same track = 8.09:1, so the New series was clearly meant to be a visible second hue. The sheet assumes the light palette, where `--brand-ink` is `#2A1A12` and does read on white | Give the New series a visible hue that measures ≥3:1 on `#111111` (e.g. `--brand-deep` #FFB27A, which measures 11.2:1 on `--bg`), and change it by measuring, per the repo's own rule |
| Important | `web/feat/analytics-traffic.js:14` | Every traffic-source bar is barely visible: `.atf-bar{...background:var(--brand-line)}` is `#4A2E18` (dark brown border colour) drawn on the `.atf-track` background `var(--muted)` = `#111111` (:13) | Measured: #4A2E18 vs #111111 = **1.52:1**, below WCAG 1.4.11's 3:1 for meaningful graphics. `--brand-line` is the palette's border tint (`#FFD9BC` in light themes — a border colour, not a fill). The percentage text still carries the number, but the bar is the tab's main visual comparison | Fill the bars with `--brand` (#FF8B33, 8.09:1 on the track) and measure |
| Minor | `web/feat/analytics-traffic.js:133` | Dead class: `.atf-bar.top` is applied to the biggest source's bar, but no `.atf-bar.top` rule exists anywhere (the `.top` rules in `web/index.html` are scoped to `.sinfo .top` and `.hbar-row .top`, neither of which matches) | Grep: no `atf-bar.top` selector in any file; :133 applies `top` to the first bar. The "biggest source stands out" intent never shows — same pattern as the audience sheet's light-palette assumption | Add `.atf-bar.top{background:var(--brand)}` (also fixes the top bar's visibility), or drop the class |
| Minor | `web/feat/analytics-realtime.js:122` | Misleading fail copy: "Reload the page to try again" — but the card re-checks by itself every 61 s (`TICK = GAP + 1000`, :36-40), so a reload is never needed | :122 `"Today's views could not be read." + (state.why ? ... : " Reload the page to try again.")` vs the stale branch :120 which already says "This card fills in on its next check." | Use the same next-check wording as :120 ("This card fills in on its next check.") |
| Minor | `web/feat/analytics-retention.js:24` | Weak keyboard focus ring on the curve's focusable group: `.rwrap:focus-visible{outline:2px solid var(--brand-line)}` — a border colour against the page | Measured: #4A2E18 on `--bg` #0A0A0A = **1.60:1** (1.52:1 vs `--card` #111111), below the 3:1 focus-indicator bar. Keyboard users can tab to the curve but can hardly see where focus is | Outline with `--brand` and measure |

## Usability findings

| Severity | Where | What | Evidence | Fix |
|---|---|---|---|---|
| Minor | `web/feat/analytics-audience.js` (no-token note) | With no channel connected, the Audience tab tells the user to connect but gives no way there: the note text renders as plain copy, so `analytics-empty.js` (which links empty boxes) deliberately stays out, and this file contains no link. Every sibling surface on the same page links: traffic :141, KPI :128, realtime :130, empty-boxes :61 | Grep for `/app/apps` across all analytics files: present in 5 files, absent in `analytics-audience.js` and `analytics-retention.js`. `analytics-empty.js:86` returns early on real content, so the note text suppresses the link | Append a "Connected apps" link to the no-token note, the way `analytics-traffic.js:141` does |
| Minor | `web/feat/analytics-audience.js:25,155` | The 7×24 hours heatmap (`min-width:520px`) sits in an `overflow-x:auto` scroll region with no hint; on a 390 px phone roughly 130 px (about hours 18-24) hides off-screen, and on overlay-scrollbar platforms there is no visible scrollbar and no copy saying more is there | :25 `.aa-scroll{overflow-x:auto;padding-bottom:2px}.aa-map{min-width:520px}`; :155 renders it; grep for "scroll/swipe/drag" copy in the file: none | One faint line under the map: "Swipe to see the whole day" (or a right-edge fade) |
| Minor | `web/feat/analytics-retention.js` (fail state) | The curve's error shows the server's "Retention comes from YouTube. Connect a channel under Connected apps." with retry buttons but no link, so the user must find the nav row themselves | Server body verified: `{"detail":"Retention comes from YouTube. Connect a channel under Connected apps."}` (`studio/api_analytics.py:411`); grep: no `/app/apps` in this file | Link the words "Connected apps" to `/app/apps`, the way the other cards do |

## Checks run

- **Full reads** of all four owned files, plus cross-reads of the shell (`analytics.js`), `plugins.js`, `analytics-table.js`, `analytics-empty.js`, `polish-contrast.js`, the palette and route map in `index.html`, and all six route handlers in `studio/api_analytics.py:176-424`.
- **HTTP status** via curl: `/app/analytics` **200**, `/app/insights` **200**, `/api/analytics/summary?days=7` **200**, `/api/analytics/timeseries?metric=views&days=7` **200**, `/api/analytics/videos?days=7` **200**, `/api/analytics/audience?days=7` **200**, `/api/analytics/traffic?days=7` **200**, `/api/analytics/retention?video=…` **400** and `/api/analytics/retention` **400** — both 400s are the documented no-token / no-id paths, not defects.
- **Response bodies** vs UI contracts: audience no-token JSON (`returning:null`, countries/hours `[]`, note "Viewer types, countries and hours come from YouTube. Connect a channel to see them.") matches the block's empty-state copy; traffic no-token (`sources:[]` + note) matches; retention 400 detail strings match what the card surfaces; timeseries unknown metric → 400 listing the eight valid metrics.
- **Route/param agreement**: every UI-capped `days` (3650) matches the server's `le=3650`; `videos` `limit` is `Query(100, ge=1, le=200)` and retention's `limit=200` is inside it; `metric` max_length 40; `video` max_length 200; audience/traffic/summary/timeseries field shapes match what the four files read (`rows[].day/value`, `points[].at/watching`, `cards[]`, `sources[]`).
- **Contrast sweep** (my own WCAG math, (L1+0.05)/(L2+0.05)): 12 pairs — `.aa-note` #A3A3A3/#111111 7.49:1 ✓, `.aa-legend`/`.aa-h`/`.aa-d` ✓, `.aa-val` ✓, `.rerr` #F87171/#2B1416 6.25:1 ✓, `.rnote`/`.rt` #A0948C 7.24:1 ✓ (polish-contrast.js lifts `--faint` for `#main`, which wraps every view), `.annow-*` ✓ (18.16 / 7.85 / 7.24), `.rtip` ✓, `.atf-say a` #FFB27A 11.2:1 ✓. Only the two pairs in the findings table fail.
- **Structure checks**: `plugins.js P.css` injects an unprefixed `pcss_<id>` style tag (retention's `analytics-retention` id is correct); after-hooks fire only for `#jobs,#ov,#cbody,#clipdlg,#sform,.topbar` — the audience tab instead draws from its own `documentElement` MutationObserver (debounced 120 ms), which works; `peakcut:render` is a real event (dispatched by the shell's `ask()`); the shell's `switchTab` deletes `body.dataset.aa` and empties `#an_body`, so there is no stale-content bug on tab switches; the shell's `reload()` deletes both skip-redraw signatures on range changes.
- **Console-risk scan**: every fetch is wrapped, every interpolated string goes through `esc()`/`text()`, globals (`P`, `ic`, `put`) are guarded with `typeof` at load; no unescaped `innerHTML` interpolation found. No dead `[data-act]` handlers; retention's retry buttons and curve keyboard support (arrow/Home/End/Escape) are wired.
- **Mobile geometry**: `.aa-split` 104px + minmax(0,1fr) + 92px columns fit 390 px (no overflow); `.atf-row` collapses to `repeat(3,auto)` under 700 px with name/track full-width; `.annow` mobile sizes under 640 px; retention picker goes full-width under 700 px. The only mobile gap is the heatmap scroll hint above.

## Observations for other owners (not mine to fix)

- `web/feat/analytics-table.js` clamps `.ant-name` to `max-width:340px` with a 2-line clamp — on very narrow screens the title column may feel tight, but it ellipsises rather than overflows.
- The shell's "Last updated" stamp and panel painting are the shell agent's file; no defect observed in how it interacts with these four cards.

**Bottom line**: every route is green and every state (loading, empty, error, stale) is present and truthful; the real work is two invisible data series on the dark page (audience "New", traffic bars), one dead class, one misleading sentence, one weak focus ring, and three places where the page tells you to connect a channel without a link to do it.
