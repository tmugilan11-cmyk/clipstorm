# Insights page audit — /app/analytics (Overview tab) + analytics frame files

Auditor: agent-136 (QA swarm, PeakCut). Scope: the page `/app/analytics` (Overview tab) and the
frame files that draw it. Server: http://127.0.0.1:8798.

## Pages and files owned

- PAGE `/app/analytics` (Overview tab; also `/app/analytics/overview`, verified 200)
- `web/feat/analytics.js` — the page shell: tabs, range picker, Compare toggle, "last updated" stamp
- `web/feat/analytics-kpi.js` — the Overview tab's key-number cards (`#an_kpi`)
- `web/feat/analytics-charts.js` — the daily views / watch-time SVG charts (`#an_charts`)

## Checks run

1. **Full file reads** of all three owned files (220, 181, 257 lines), plus the shared files that
   restyle this page: `web/feat/polish-type.js`, `web/feat/polish-wide.js`,
   `web/feat/polish-contrast.js` (header), `web/feat/analytics-empty.js` (the empty-box fallback),
   `web/plugins.js` (router/helpers), `web/index.html` (palette, shared CSS, `fromPath`),
   `studio/api_analytics.py` (the two endpoints the files call).
2. **HTTP shells** — `curl -s -o /dev/null -w "%{http_code}"`:
   - `http://127.0.0.1:8798/app/analytics` → **200**
   - `http://127.0.0.1:8798/app/analytics/overview` → **200**
   - `http://127.0.0.1:8798/app/apps` → **200** (the "Connected apps" links' target is a real page,
     registered at `web/feat/menu-pages.js:181-185` with `path: "apps"`)
3. **Live API probes**:
   - `GET /api/analytics/summary?days=28` → **200**; body shows `source:"peakcut"`, `compare:null`,
     six not-connected cards (clips/posted/views/queued/failed/creators), the note, and **no**
     `change`/`delta` fields on any card.
   - `GET /api/analytics/timeseries?metric=estimatedMinutesWatched&days=28` → **400**
     `{"detail":"PeakCut does not know that metric. Ask for one of: average_view_duration, average_view_percentage, comments, likes, shares, subscribers, views, watch_time."}`
   - `GET /api/analytics/timeseries?metric=watch_time&days=28` → **200** (rows of `{day,value}` only,
     no compare key).
   - `summary` params: `days=Query(28,ge=0,le=3650)`, `compare=Query(1,ge=0,le=1)` — compare **defaults
     to 1**; `timeseries` accepts only `metric` + `days`, **no compare params at all**
     (`studio/api_analytics.py:176-178, 237-239`).
4. **Contrast measurements** (WCAG relative luminance, `(L1+0.05)/(L2+0.05)`, script run against the
   palette in `web/index.html:16-22`):
   - `--dim #A3A3A3` on `--bg #0A0A0A` → **7.85:1** (labels, hints, legends) — pass
   - `--faint` resolved to `#A0948C` on bg (`polish-contrast.js:29` inside `#main,dialog`) → **6.70:1**
     (units, range line, axis ticks) — pass; raw `#7C7C7C` would be 4.74:1, still pass, override active
   - `--text #F5F5F5` on bg → **18.16:1**; `--brand-deep #FFB27A` on bg → **11.22:1** — pass
   - Change pill default (`--dim` on `--muted #111111`) → **7.49:1**; `.pill.ok` (`--good #34D399` on
     `--good-soft #0B2A1E`) → **8.01:1**; `.pill.bad` (`--bad #F87171` on `--bad-soft #2B1416`) →
     **6.25:1** — all pass
   - **`.ac-comp` dashed comparison line: `#FFB27A` at opacity .36 over bg blends to `#624632` →
     2.30:1 — FAIL** the 3:1 non-text minimum (WCAG 1.4.11). At opacity .5 it is 3.45:1 (pass); at .6,
     4.54:1.
   - **Switch knob (Compare toggle, `web/index.html:226-227`): white knob on the unchecked
     `#DCD2D0` track → 1.48:1 — FAIL** the 3:1 non-text minimum.
   - `.ac-swatch.alt` legend swatch at opacity .5 → 3.45:1 — pass (borderline).
   - `.an-dot` uses `--line-2 #2A2A2A` on bg → 1.38:1, decorative dot only, not information-bearing.
5. **Viewport / layout reasoning from measured CSS** (no browser allowed in this audit): the KPI grid
   is 6 columns ≥1180px, 2 columns ≤640px, 1 column ≤430px (`analytics-kpi.js:19-21`) — at 390px the
   container is ~358px, so the 1-column rule holds and no card is wider than the viewport. Tab row is
   `overflow-x:auto` (`index.html:244`). Chart SVG uses `viewBox w×180` with `width:100%`, so it scales
   down, never overflows. `polish-wide.js` overrides only apply above 1600px.
6. **Parse checks** — `node --check` on all three owned files → all OK.
7. **Code-risk greps** on the three files: no `console.*`, no `debugger`, no `!important`, no em-dash
   in comments. All `innerHTML` writes pass through `esc()`; the tooltip is `aria-live="polite"` and
   clamped to the chart box.
8. **Interplay checks**: `analytics-empty.js` only paints into a box whose text is empty for ≥1300 ms
   (`EMPTY` regex on `box.textContent`); the KPI and chart boxes always carry labels or an error
   sentence, so the two files cannot double-paint or overwrite each other. `put()` dedupes identical
   HTML; `fill()` dedupes by `dataset.sig`.

## Findings

| # | Severity | Where | What | Evidence | Fix |
|---|----------|-------|------|----------|-----|
| 1 | Critical | `web/feat/analytics-charts.js:58` (and the fallback at `:209`) | The watch-time chart asks for a metric the server does not know, so its first request fails with HTTP 400 on every fill — a console error on load — before the fallback succeeds. | `CHARTS` declares `metric:"estimatedMinutesWatched"`; `studio/api_analytics.py` `_METRICS` has no such key. Measured live: `GET /api/analytics/timeseries?metric=estimatedMinutesWatched&days=28` → **400** "PeakCut does not know that metric…"; `metric=watch_time` → **200**. Browsers log the 400 as a failed resource on every page load. | Ask `watch_time` first — it is already declared as the alt key (`charts.js:60`). Swap the primary/alt or drop the YouTube-internal name. |
| 2 | Important | `web/feat/analytics-kpi.js:99` (comment at `:111`) | The Compare toggle cannot turn the comparison off. When off, the client sends no `compare` param; the server defaults `compare=1` (`api_analytics.py:178`), so the request is byte-for-byte the same as with the toggle on. Previous-period cards always come back and change pills are always computed. The comment at `kpi.js:111` states the opposite belief ("With the comparison off the route sends no previous cards"). | Server default measured in `api_analytics.py:178`; `kpi.js:99` `if (c) add("compare", 1)` sends nothing when off. | Send `compare=0` explicitly when the toggle is off (the server's default is the server owner's to change). |
| 3 | Important | `web/feat/analytics-charts.js:74-75, 91` vs `studio/api_analytics.py:238-239` | The comparison is claimed but delivers nothing in the charts. The client sends `compare_start`/`compare_end` and reads `b.compare` for the dashed previous-range line, but the timeseries endpoint accepts only `metric`+`days` and its rows carry no compare key — so the dashed line, the "Previous range" legend (`charts.js:133`) and the tooltip's previous-range row can never render, while the page header promises "compared with the N days before" (`analytics.js:68`). | Endpoint signature `api_analytics.py:237-239` (no compare params); live response rows are `{day,value}` only. | Server: accept and return the compare series (owner's call), or the client fetches the previous window with a second request, or stop claiming the comparison. |
| 4 | Important | `web/feat/analytics-kpi.js:157` → `127-129` | The loading frame claims "Not connected yet" even when a channel is connected. `fill()` paints the frame first with `note(null)`, which renders the not-connected copy, so for the request's whole duration a connected reader sees "Not connected yet. Connect a channel in Connected apps to fill these in." | `paint(box, null, q)` at `kpi.js:157`; `note(null)` at `:129` returns the not-connected sentence. | Paint a loading sentence in the loading frame, like the charts file does (`charts.js:224-225`, "Reading views and watch time for \<label\>.") — pass a loading flag through `note()`. |
| 5 | Important | `web/feat/analytics-charts.js:20` | The dashed comparison line fails WCAG non-text contrast: brand-deep at opacity .36 over the black background blends to `#624632` = **2.30:1**, below the 3:1 minimum (WCAG 1.4.11). The line is information-bearing (the whole point of the Compare toggle). | Measured: blended luminance at opacity .36 → 2.30:1; at .5 → 3.45:1; at .6 → 4.54:1. | Raise the stroke opacity to .5 (measured 3.45:1) or use full `--brand-deep` (11.22:1); re-measure after any palette change. |
| 6 | Minor | `web/index.html:226-227` (shared file; rendered on this page as the Compare switch) | The switch knob fails non-text contrast when off: the white 16px knob on the light `#DCD2D0` track is **1.48:1**, below 3:1. Not an owned file — flagged for its owner; it is the only control on the Overview tab affected. | Measured from `index.html:226-227` (`background:#DCD2D0` unchecked, `::after` white knob). | Darken the unchecked track or outline the knob in ink; measure before changing (per `docs/TEXT-PASS.md`). |
| 7 | Minor | `web/feat/analytics.js:41-45` vs `studio/api_analytics.py:104-109` | "Lifetime" delivers about ten years, not a lifetime. The client sends `days=0` for Lifetime; the server's window for `days<=0` is 3650 days. The range line reads "Lifetime, up to \<date\>", which over-promises. | `analytics.js:41-45` (Lifetime starts 2005-01-01, `days:null`); `api_analytics.py:104-109` (`days<=0 → 3650-day window`); `kpi.js:95` comment acknowledges the cap. | Say the cap in the range line or hint ("Lifetime, up to ten years back") or raise the server ceiling (owner's call). |
| 8 | Minor | `web/feat/analytics.js:96-102, 112-113` | Tab panels carry no `role="tabpanel"`. The tab buttons carry `role="tab"` + `aria-selected`, but the sections only carry `data-an-panel` + `hidden`, so the tab → panel relationship is not exposed to assistive tech. | `analytics.js:96-103` (sections with `data-an-panel`, no role). | Add `role="tabpanel"` and an `aria-labelledby` pointing at the tab button. |
| 9 | Minor | `web/feat/analytics.js:17` vs `web/feat/polish-type.js:48` | Dead mobile heading rule: the page sets `.an-name` to 20px on phones, but `polish-type.js` sets `#view .an-name{font-size:var(--pt-3xl)}` (23px), which wins on specificity. No visible symptom (23px reads fine at 390px); it is dead code and a maintenance trap — a future edit to `analytics.js:17` will do nothing. | Specificity comparison: `#view .an-name` (1,1,0) beats `.an-name` (0,1,0) in any media query. | Drop the override from `analytics.js:17` or scope it the same way `polish-type.js` does. |

## Usability findings

| Where | What | Fix |
|-------|------|-----|
| `analytics-kpi.js:157→129` | During load the key-numbers box says "Not connected yet. Connect a channel in Connected apps to fill these in." even for a connected install — a reader learns the wrong state in the first second of every visit. | Loading copy, not the not-connected copy (finding 4). |
| `analytics.js:68` + `analytics-charts.js:133` | The header promises "compared with the N days before" and the chart's legend is ready to say "Previous range", but the comparison never arrives — a beginner looks for a dashed line that can never be drawn. | Ship the comparison or stop claiming it (finding 3). |
| `analytics-kpi.js:99` | The Compare toggle's two positions produce identical requests and identical numbers — a control that does nothing the reader can see. | Honor the off position (finding 2). |
| `analytics.js:41-45` | "Lifetime" is really the last ten years; a beginner comparing two Lifetime reads a year apart sees no difference. | Label the cap (finding 7). |
| Good, no change needed | "Connect a channel in Connected apps to fill these in." carries a working link to `/app/apps` (verified 200) — one step from the broken state to its fix. "Not in this answer yet: Impressions, Click-through rate." states exactly which numbers are missing instead of blank space. Range labels 7/28/90/365/Lifetime are self-explanatory; the change pills carry arrows plus `title`/`aria-label` explaining direction and the period. | — |

## What passed

- Both page shells 200; `/app/apps` link target 200.
- All text on the Overview tab passes WCAG AA contrast (dim 7.85:1, faint-resolved 6.70:1, pills
  6.25–8.01:1); the two failures are non-text (dashed line, switch knob).
- No element is wider than a 390px viewport at the measured breakpoints; the tab row scrolls instead
  of clipping; the chart SVG scales with its `viewBox`.
- Loading, empty and error states exist in all three files, and the shared `analytics-empty.js`
  fallback cannot conflict with them (it requires an empty-text box for ≥1300 ms).
- All `innerHTML` writes are escaped; no `console.*`/`debugger`/`!important` in the owned files;
  `node --check` passes on all three.
