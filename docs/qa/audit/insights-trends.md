# QA Audit — Insights (Trends tab) and analytics-* feature files

Auditor: agent-139 (40-agent swarm). Scope: PAGE `/app/analytics` Trends tab; FILES
`web/feat/analytics-trends.js`, `web/feat/analytics-shorts.js`, `web/feat/analytics-revenue.js`,
`web/feat/analytics-export.js`, `web/feat/analytics-empty.js`. Rule set: `docs/qa/CONTRACT.md`.
Skill loaded: systematic-debugging. No browser tools used (lead owns the browser); all checks ran
via file reads, greps, and curl against http://127.0.0.1:8798.

## Files and pages owned

| What | Path | Lines | Status |
|---|---|---|---|
| Trends tab block | web/feat/analytics-trends.js | 393 | read fully |
| Shorts (Content tab) block | web/feat/analytics-shorts.js | 272 | read fully |
| Revenue card (Overview tab) | web/feat/analytics-revenue.js | 229 | read fully |
| Export button (Insights header) | web/feat/analytics-export.js | 252 | read fully |
| Empty-box filler | web/feat/analytics-empty.js | 126 | read fully |
| Page shell (read-only context) | web/feat/analytics.js | — | read (tabs, ranges, hintFor) |
| Page (read-only context) | web/index.html | — | read (globals, palette, handlers) |
| Server routes (read-only context) | studio/api_trends.py, studio/api_analytics.py, studio/server.py | — | read (route + shape verification) |

## Every check run

1. **Contract** — read `docs/qa/CONTRACT.md`; severity and evidence rules applied below.
2. **Page shells** — `curl -s -o /dev/null -w "%{http_code}"`:
   `/app/analytics` → **200**; `/app/apps` → **200** (empty-box link target); `/` → **303**
   (login redirect, expected with accounts off this is the signed-in path check).
3. **Static serving** — real serve path is `/assets/feat/<name>.js` (studio/server.py:497-504,
   FileResponse with `Cache-Control: no-cache`); all five owned files → **200**.
   (`/web/feat/…` → 404 by design; that is the repo path, not the URL.)
4. **Route existence** — `/api/trends/searches`, `/api/trends/videos`, `/api/trends/saved`
   (GET/POST/DELETE), `/api/trends/status` in studio/api_trends.py:218,265,320,328,364;
   `/api/analytics/summary` (api_analytics.py:176), `/api/analytics/videos` (:271). All present.
5. **Response schemas vs page parsers** — live `curl` of all three GET routes; keys
   (`rows`, `days`, `start`, `end`, `note`, `source`, `cards`, `compare`, `total`) match what
   `analytics-trends.js` / `analytics-shorts.js` / `analytics-revenue.js` read. Empty `rows`
   land in the blocks' empty states, verified in code.
6. **Saved-list contract** — server `MAX_SAVED=50`/`MAX_TERM=120` (api_trends.py) vs page cap
   copy "You can keep 50 search terms" (analytics-trends.js); DELETE accepts `term`
   `max_length=200`, page sends `encodeURIComponent` of a ≤120-char term — fits.
7. **Handler wiring** — every control in the owned files resolves: `data-atr-save`/
   `data-atr-drop` (delegation at analytics-trends.js:374-381, scoped to `#an_body`),
   `data-act="go"` (index.html:3110 big listener → `go(d.v, d.tab)`), export click, drop
   through `P.send`/`P.api` (plugins.js:258-259) with `api()` forwarding `opt.method` to fetch,
   so the DELETE works. No dead handlers found.
8. **Icon names** — every `ic("…")` name used by the owned files (`check`, `plus`, `x`,
   `arrowr`, `money`, `warn`, `bulb`, `up`, `down`, `minus`) exists in the `I` map
   (web/index.html:931+); a missing name would render an empty `<svg>`, not text — none missing.
9. **Contrast (WCAG)** — computed every ink/background pair the owned files draw:
   `--dim #A3A3A3` on `--bg` 7.85:1 and on `--muted` 7.48:1; `--text` on `--bad-soft` 15.87:1;
   `--good` on `--bg` 10.3:1; `--bad` on `--bad-soft` 6.25:1; base `--faint #7C7C7C` on
   `--bg` 4.74:1 / on `--muted` 4.52:1, and `web/feat/polish-contrast.js` lifts `--faint` to
   `#A0948C` (7.24:1) inside `#main`/`dialog` where these pages live. All ≥ 4.5:1 → no finding.
10. **390px viewport** — the owned CSS uses block-level rows, `max-width:100%` chips
    (`.atr-chip`), and no fixed width over 390px; text truncates via `title` + ellipsis
    rather than overflowing. No overflow finding.
11. **States** — loading (`set-load`, aria-busy), fail (`atr-fail`, `arv-quiet`),
    and empty (`atr-empty`, `an-empty`) exist for all three Trends blocks; shorts has an
    explicit "server sent N videos but not how long they run" state; revenue has a
    why-explained quiet state; export disables itself when there is nothing to export.
12. **Console-risky code** — no `eval`, no unescaped `innerHTML` of server text (`esc()` on
    every interpolation of server strings; `toast()` uses `textContent`); the only
    `console.warn` is inside export's catch. No finding.
13. **CSV safety** — export's `cell()` prefixes `'` on cells matching `/^[=+\-@]/` (formula
    injection), output carries a BOM, filename is a slug `peakcut-insights-<range>.csv`.

## Findings

| # | Severity | Where | What | Evidence | Fix |
|---|---|---|---|---|---|
| 1 | important | web/feat/analytics-revenue.js:161 (with studio/api_analytics.py:48) | The Revenue card can never show a number, and its permanent fallback sentence asserts a cause the page cannot verify — "Revenue needs a YouTube Partner Program channel" — which is misleading for a connected YPP channel, whose revenue YouTube does expose but PeakCut never requests. | api_analytics.py:48 `_SUMMARY = "views,estimatedMinutesWatched,…,shares"` contains no revenue metric; live `GET /api/analytics/summary?days=28` returns cards keyed clips/posted/views/queued/failed/creators only; `harvest()` (analytics-revenue.js:153,155) therefore always finds nothing → `have=[]` → line 161 text. | Page-side (this file): make the sentence say only what the page knows, e.g. "The summary for this range carries no revenue figures." Server-side: add `estimatedRevenue` (+ RPM/CPM) to `_SUMMARY` so the card shows real numbers and the fallback becomes true for non-YPP channels. |
| 2 | important | web/feat/analytics.js:76 (shell — labels this page; fix owned by the analytics.js agent) | The Trends tab hint says "How these numbers moved over the range on screen." but the tab holds ranked lists — Top searches, Breakout videos, Saved searches — no movement over time. A beginner reading the hint cannot connect it to what appears. | analytics.js:76 `hintFor` returns that string for `trends`; analytics-trends.js draws three ranked blocks (h3 "Top searches" / "Breakout videos" / "Saved searches"). | Reword the hint to describe the tab, e.g. "What people searched for and which videos broke out over the range on screen." |
| 3 | minor | web/feat/analytics-trends.js:191 | The Interest value ("Very high", "High", …) is explained only by a hover tooltip whose copy is developer-speak — "The words the server used for this term's share of search views" — and the column has no visible header or label. | Line 191: `<span class="atr-interest" title="The words the server used for this term's share of search views">`. | Shorten the title to plain language, e.g. "How often people searched for this, compared with all searches"; optionally add a visible word for the column. |
| 4 | minor | web/feat/analytics-export.js:4-6 (comment) and `OWN` list | Export never appears on the Trends tab, and the file's own comment claims "Trends holds none" — no longer accurate: the tab holds `.atr-list`/`.atr-vlist` rows of searches and videos that could be exported. | analytics-export.js `OWN=["overview","content"]`; `allowed()` returns false for `/trend/`; owned rows live in `.atr-list`/`.atr-vlist` (analytics-trends.js), which `hasRows()`/the CSV builder do not read. | Either add `"trends"` to `OWN` and teach the builder the two row classes, or at minimum correct the stale comment. |
| 5 | minor | web/feat/analytics-trends.js:325 (with analytics.js switchTab) | Leaving Trends and returning while a request for the same range is still in flight leaves `#an_body` blank — the shell clears it and `load()` early-returns, so no loading line repaints for up to a few seconds. | analytics.js switchTab clears `#an_body` for body-panel tabs; analytics-trends.js:325 `if (busy.has(q.sig)) return;` skips the `paint(loading)` for an in-flight sig. | When `busy.has(q.sig)`, still paint the loading line (or have the shell not clear the panel when the same request is in flight). |

No critical findings: every page shell is 200, every control resolves, every owned ink pair
meets WCAG AA (≥ 4.5:1), all three blocks carry loading/fail/empty states, and no
console-risky pattern was found in the owned files.

## Notes for the fix wave

- Finding 1's cleanest fix is one sentence in this file (analytics-revenue.js:159-161); the
  data-level fix (real revenue figures) belongs to the api_analytics.py owner and is optional
  for closing this finding.
- Finding 2's fix lives in web/feat/analytics.js, which this auditor does not own; the
  analytics.js agent should pick it up.
