# Insights Content audit — /app/analytics (Content tab + compare)

Auditor: agent-137 (QA swarm; audit by file reading + curl only, no browser used — the lead owns the browser).
Server: http://127.0.0.1:8798. Contract: `docs/qa/CONTRACT.md`. Skill loaded: `systematic-debugging` (root cause traced for every finding).

## Pages / files owned

- Page `/app/analytics` — the **Content** tab (video table, sort, filter, date-range picker) and the **compare** block (change-lines under the six KPI cards).
- `web/feat/analytics-table.js` (319 lines) — read fully.
- `web/feat/analytics-compare.js` (246 lines) — read fully.
- Cross-checked (not owned, read for interplay): `web/feat/analytics.js` (page shell, range/compare getters), `web/feat/analytics-kpi.js` (KPI cards the compare sits under), `web/feat/analytics-empty.js`, `web/feat/analytics-shorts.js` (block after the table), `web/plugins.js` (`P.api`), `web/index.html` (globals, `.scroll` containers, icon map), `studio/api_analytics.py` (routes + row keys).

## Checks run

1. `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8798/app/analytics` → **200**. No 404/500 on the owned page.
2. Read both owned feature files end to end (every line), traced `asked() → get() → paint()` (table) and `fill() → asked() → draw()` (compare).
3. Route existence and response shape: `ops_grep` on `studio/api_analytics.py` — `/api/analytics/summary` (:176, `days` 0–3650, `compare` 0–1), `/api/analytics/videos` (:271, `days` 0–3650, `limit` 1–200). Summary cards vs client labels: all six server cards match `analytics-kpi.js:28-33` lowercased; `compare.cards` is a plain-number object (:223-229) and the compare file's `was` extraction reads it correctly.
4. Byte-level regex check on `web/feat`: `ops_grep` pattern `\\\\d` (literal doubled backslash-d) → **0 matches**; pattern `\\d` → 18 matches in 15 files. All regex literals in both owned files are correct single-backslash JS. (Lesson: `ops_inspect_local_file` doubles backslashes in its content output — never count escapes from it.)
5. Globals the owned files depend on: `esc` (`web/index.html:930`), `ic` (:992), `api` (:999), `P.api` (`web/plugins.js:259`), `.scroll{overflow-x:auto}` (:619), `#view` (:912). All exist before the feat files load — the compare's "page is still starting" fallback never trips.
6. Icon keys used by the owned files all exist in the `I` map: `caret` (:938), `film` (:941), `minus` (:939), `down` (:947), `up` (:954) — no empty SVGs.
7. Contrast measured with the WCAG relative-luminance formula (never by eye):
   - `--faint #7C7C7C` on `--bg #0A0A0A` (12px th sort buttons, 12–13px hints): **4.74:1** — ≥ 4.5 pass (shell comment claims 4.6; recomputed 0.2516/0.0530).
   - `--faint` on `--muted #111111` (hovered rows, `.ant-ph` placeholder icon): **4.53:1** — pass (icon also clears the 3:1 non-text rule).
   - `.ant-err #F87171` on `#2B1416`: **6.32:1** — pass.
   - `.akcmp` up `--good #34D399`: **10.3:1**; down `--bad #F87171`: **7.16:1**; `.akcmp-note --dim #A3A3A3`: **7.85:1** on `--bg` — all pass.
   - Nothing in either owned file renders below 4.5:1 → **no contrast findings**.
8. Escaping: every interpolated server string goes through `esc()` — table `:136,137,145,150,152,174,179,203,209,211`; compare `:171,178`. No untrusted `innerHTML` interpolation, no console-risky code found in either file.
9. Mobile containers: `.scroll table:not(.stack){min-width:560px}` (`web/index.html:883`, inside `@media (max-width:640px)`), `table.stack` card layout (:884-891); the owned table's `.ant-t{min-width:960px}` sits inside `.scroll` — measured against a 390px viewport.
10. Cross-file interplay: `analytics-empty.js` only fills boxes whose content is empty — the table's loading/empty/error states all carry text, so no duplicate line and no stuck state; `analytics-shorts.js:153-164` `seat()` creates its own `<section class="set-sec ast">` and inserts it with `insertAdjacentElement("afterend")` — it never rewrites `#an_table`; `analytics.js` `reload()` (:164-174) wipes the box and re-runs `load()` handlers.
11. Handlers: sort buttons (`[data-sort]`), range select, search input, error "Try again" — all bound and live; `aria-sort` per th and `role="status"` "Sorted by …" present.

## Findings

| Severity | Where | What | Evidence | Fix |
|---|---|---|---|---|
| important | `web/feat/analytics-table.js:76` | The Content tab **never inherits the page's date range**. `const g = r.range || r` grabs `window.PeakCutAnalytics.range`, which is a *function* (`web/feat/analytics.js:79-87`); a truthy function passes `\|\|`, so `g.start/g.end/g.days` are undefined → span 0, `Number(g.days)` = NaN → `asked()` always returns the module default 28. The sibling files call the getter (`analytics-compare.js:95`, `analytics-kpi.js:94`); the table never does, so the inheritance code and its comments (`:71-73`, `:165-172`, `:283-284`) are dead. `pick=true` after any table pick (`:264-265`) then disables the (already dead) path forever. | Page range 90 → header says "Last 90 days", table picker says "Last 28 days", fetch is `?days=28`. | `const g = (typeof r.range === "function" ? r.range() : r.range) || r;` (mirror `val()`), or read the plain values `head()`→`agree()` already publishes on the shell object; optionally map Lifetime → `days=0` (server: 0 = the 3650-day lifetime span, `studio/api_analytics.py:37`) instead of capping at `MOST`. |
| important | `web/feat/analytics-table.js:111-112`, `:144` | The **Impressions and Click-through columns can never show a number**: `normalize()` maps `imp`/`ctr` from keys the server never sends (`studio/api_analytics.py:309-320` row keys; `_VIDEO_COLS :50-51` never asks YouTube for them). Every row renders "–" in both columns with tooltip "This video did not report this number." — wrong copy: it blames the video when the app never asks for the metrics. 2 of 11 columns are permanent dead weight. Related dead code: `r.short` reads `is_short/short/format` (`:152`) — none sent → the "Short" badge (`.ant-short :32`) never renders and the short-specific tooltip (`:142-143`) is unreachable; the server does send `seconds` (`:313`), so a Short is detectable by duration. | `ops_grep` row keys vs `normalize()` key lists — zero overlap for imp/ctr/short. | Drop the two columns (or fetch the metrics server-side); rewrite the tooltip ("PeakCut does not fetch impressions for videos"); wire the Short badge from `seconds <= 60` or remove it. |
| minor | `web/feat/analytics-table.js:41`, `:238` | **Stale cache after publishing**: `CACHE` is a Map keyed by `days` with no TTL or invalidation; `mount()` early-returns when the frame exists (`:277`), and `analytics.js` `reload()` (:164-174) wipes the box then `ask()` hits the cache and repaints old rows without any request. The Content tab keeps the old count until a full reload or a picker change. | Cache key set at `:238`, only deleted by the error retry. | Delete the days-key on `peakcut:render`, give the cache a short TTL, or have `reload()` force a re-ask. |
| minor | `web/feat/analytics-table.js:238` | **Silently truncated list**: the table fetches only `?days=N`, the route's `limit` defaults to 100 (`studio/api_analytics.py:273`, cap 200), and the table ignores `data.total`, labelling `list.length` as the full count. A channel with >100 videos in the window sees "100 videos" with no truncation notice. (Server `total` is itself unreliable: own-case pre-limit `len(rows)` :291, YouTube-case post-limit `len(out)` :322.) | Fetch string `:238`; count built from `list.length` in `paint()`. | Request `limit=200` and print "X of Y videos" when `total` exceeds the rows. |
| minor | `web/feat/analytics-compare.js:212` | **Duplicate summary request**: the compare asks `/api/analytics/summary?days=N&compare=1` while the KPI row asks the same route with `start&end&days&compare` (`analytics-kpi.js:96-100`) — two client requests for one server-cached answer (same key `sum:{uid}:{days}:{compare}:{token}`, `studio/api_analytics.py:234`). No quota cost, redundant network. | Two query strings in `web/feat/analytics-*.js`. | Share one query-string builder or one in-flight request between KPI and compare. |

## Usability

| Severity | Where | What | Fix |
|---|---|---|---|
| important | `web/feat/analytics-table.js:76` + `web/feat/analytics.js:79-87,140` | **Two date-range controls can disagree**: the page header says one range (e.g. "Last 90 days, ending …") while the table picker and its numbers say another ("Last 28 days"). A beginner cannot tell which control is in charge, and the hint under the picker does not mention that the page-level range exists. | The bug-1 fix (inherit the page range into the picker), or hide the table picker while it disagrees with the header. |
| important | `web/feat/analytics-table.js:111-112,144` | **Two columns of dashes that blame the video**: beginners read the permanent "–" in Impressions / Click-through, with the tooltip "This video did not report this number", as broken data on their channel. | Drop the columns, or re-copy the tooltip so it says the app does not fetch these numbers. |
| minor | `web/feat/analytics-table.js:18` + `web/index.html:619,883` | **No scroll cue at phone width**: the 11-column table is `min-width:960px` (560px on ≤640px) inside `.scroll{overflow-x:auto}`; at a 390px viewport roughly a third of the table is off-screen with no visible scrollbar or affordance, so a first-time user may not realise more columns exist. | Fade the right edge or add a short "swipe for more columns" hint on small screens. |

## Verified OK (checked, no finding)

- Page shell 200; both API routes exist and the request/response shapes match the client.
- The table has a loading state, both empty states (no videos / no title match) and an error state with a working "Try again" that clears the cache key and re-asks; the compare block explains its dashes and its error with a "Reload this page" instruction.
- Sort (flips direction, title ascending first), search filter, and range picker handlers all live; `aria-sort` and a `role="status"` line announce the current sort.
- All colour pairs measured ≥ 4.5:1 (text) / ≥ 3:1 (icon) — nothing below the contract's critical threshold.
- `esc()` on every interpolated server string; no doubled-backslash regex literals; `P.api` exists so no "page is still starting" dead end; `#an_table`/`#an_kpi` ids do not clash with `index.html`; `analytics-empty.js` and `analytics-shorts.js` interleave with the table without rewriting it.
- Watch-time units align end to end: server pre-divides minutes to hours (`studio/api_analytics.py:315`), table `rowsOf()` sets `units.watch_time="hours"` (`:122-125`), `mmss()` renders `m:ss` and `h:mm:ss` correctly; own-data `watch_time: None` renders an honest hyphen.
