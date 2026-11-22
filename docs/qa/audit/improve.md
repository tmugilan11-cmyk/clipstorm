# QA audit — agent-140 — `/app/improve` + owned feat files

Swarm: PeakCut 40-agent QA · server `http://127.0.0.1:8798` · rules: `docs/qa/CONTRACT.md`
Method: static file audit (ops_grep / ops_glob / ops_inspect_local_file) + curl against the running server. No browser tools (lead owns the browser).

## Pages / files owned

- Page `/app/improve` — registered by `web/feat/learn.js` (`P.page("improve", …)`, learn.js:354-363)
- `web/feat/learn.js` (372 lines, read fully)
- `web/feat/learn-hooks.js` (52 lines, read fully)
- `web/feat/learn-arrows.js` (55 lines, read fully)
- `web/feat/brand-ai.js` (94 lines, read fully)
- `web/feat/post-time.js` (48 lines, read fully)
- Brief named `web/feat/learn-signals-ui.js` and `web/feat/learn-arms-ui.js` — **do not exist**. The real files are `web/feat/learn-signals.js` and `web/feat/learn-arms.js`; both audited (learn-arms.js 356 lines, learn-signals.js ~210 lines, key sections read; their server shapes verified pre-report).
- `web/feat/learn-report.js` exists but is not in the brief — not audited in depth.

## Checks run (every one)

| Check | Result |
|---|---|
| `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8798/app/improve` | **200** (exit 0) |
| Route existence for every endpoint the owned files call | all exist (see per-finding evidence) |
| Field-by-field match of client reads vs server responses | 1 critical mismatch (brand-ai), 1 important (learn-arrows); rest match |
| Contrast math for every ink/background pair used by owned CSS | all pass (min 4.5:1; details below) |
| 390px-viewport overflow pass over owned CSS | pass (wrapping flex/grid, `minmax(0,1fr)`, `.two` collapses ≤620px) |
| Dead-control sweep over every `[data-act]`/listener in owned files | none dead (`#lrn_days` feeds run() at learn.js:317) |
| Loading / empty / error state sweep per card | 1 finding (premature empty state, minor) |
| Console-risky code sweep | 1 finding (TypeError on every Ask, critical) |
| `--panel`/`--panel2` definition search across `web/` | **not defined anywhere** (0 hits for `--panel2?\s*:` over `web/*.html` + `web/**/*.js`; grep "panel" in index.html = only class names/comments) |

## Findings

| # | Severity | Where | What | Evidence | Fix |
|---|---|---|---|---|---|
| 1 | **critical** | `web/feat/brand-ai.js:32-34` | "Ask for a brand" card calls `.map` on the server's `changes` OBJECT → `TypeError: LINES.changes.map is not a function` on **every successful Ask**; the `.catch` (brand-ai.js:69) shows the raw error text in the note line. The card can never show a suggestion. It also throws away the server's ready-to-print sentences (`lines`, api_brandai.py:110) and its `note` (api_brandai.py:107). | Server: `changes = {k: values[k] for k in values if k in brand_ai.known()}` (api_brandai.py:103) and returns `"changes": {}` / `"changes": changes` (api_brandai.py:106,111) — a dict, truthy even when empty, so the `\|\| []` fallback never helps. Client: `(LINES.changes \|\| []).map((c) =>` (brand-ai.js:32). | Render the server's own `lines` array (ready sentences) as the list, or iterate `Object.entries(got.changes)`; show `got.note` when `changes` is empty. |
| 2 | **important** | `web/feat/learn-arrows.js:28` | Every row in the "Every round, before and after" card loses its setting name: the code reads `c.key`, but report change rows carry the field `setting` → `c.key` is `undefined` → `NAMES[undefined] \|\| undefined` → `esc` gives `""` → blank label next to the from→to arrows. | Rows are `{"setting": _text(c.get("setting")), "from": _text(before), …}` (learn_report.py:127). Client: `<span>${esc(NAMES[c.key] \|\| c.key)}</span>` (learn-arrows.js:28). learn.js's own `changeLine` reads `c.setting` correctly (learn.js:100), so the two cards disagree. | Use `c.setting` (and keep the `NAMES[c.setting] \|\| c.setting` fallback). |
| 3 | **important** | `web/feat/learn.js:284-290` | `paint()` sets `view.innerHTML = body()` and is called from `load()` (learn.js:307), `run()` (315, 337) and `undo()` (350) — always after `P.drawPage`'s `settle()`/`runAfter` has appended the four decorative cards (learn-hooks `[data-lhk]`, learn-arrows `[data-lra]`, brand-ai `[data-bai]`, post-time `[data-ptm]`; each mounts only via `after.drawSettings`, plugins.js:116-122 + 192). Net effect: the cards appear for an instant on page load and are wiped by the first state repaint; they stay gone until the page is revisited. Only learn-signals (MutationObserver, learn-signals.js:196-205) and learn-arms (interval tick, learn-arms.js:355) re-mount. | `view.innerHTML = body()` (learn.js:289); `runAfter` is the only non-watch caller of `after.drawSettings` (plugins.js:116-122; watch list plugins.js:188-193 has no Improve-page host). load()→paint() runs after the async state read (learn.js:296-307), i.e. after runAfter has fired. | After `paint()`, re-run the same after-hook pass (`runAfter(document.getElementById("view"))` equivalent), or give the four cards a self-re-mount like learn-signals' MutationObserver. |
| 4 | minor | `web/feat/learn-hooks.js:24,27` · `web/feat/post-time.js:24` | Server numbers interpolated into `innerHTML` without `esc()`: `got.strong`/`got.workable`/`got.weak` (learn-hooks.js:24), `h.score` inside the verdict pill (learn-hooks.js:27), `b.mean_views` (post-time.js:24). All are server-coerced numbers today (api_hooks.py:66 `"score": int(…)`, counts at api_hooks.py:77-84; mean_views numeric in api_posttime.py), so nothing is exploitable now — but this breaks the escape rule and becomes markup injection the day a field changes type. | learn-hooks.js:24 `${got.strong} strong…`, learn-hooks.js:27 `<span class="pill …">${h.score}</span>`, post-time.js:24 `${b.mean_views} views on average` — none wrapped in the files' own `esc`. | Wrap each in `esc()` like every other interpolation in these files. |
| 5 | minor (visual) | `web/index.html:19` + learn.js:11,19,20,26 · brand-ai.js:12,17 · learn-arrows.js:14 · learn-arms.js:17,21,23 | The whole-app palette never defines `--panel` or `--panel2`, so every owned-file rule that uses them computes to transparent: `.lrn .box`, `.lrn select`, `.lrn .why`, `.lrn .chg code`, `.bai input`/`.bai code`, `.lra code`, `.lar select/input/.said` lose their intended panel fill and blend into the card behind them. Text contrast is unaffected (ink `#F5F5F5` on the page's near-black still passes), so this is polish, not a WCAG failure. | Grep `--panel2?\s*:` over `web/*.html` + `web/**/*.js` → 0 hits; grep "panel" in index.html → only class names/comments (index.html:116,355,375,657…). Palette at index.html:19 defines `--card:#111111;--field:#141414` but no `--panel*`. | Define `--panel/--panel2` next to `--card/--field` (index.html:19), or change the seven rules to `var(--card)`/`var(--field)`. |

## Usability findings

| # | Severity | Where | What | Evidence | Fix |
|---|---|---|---|---|---|
| U1 | minor | `web/feat/learn.js:83-86, 249, 292-307` | Premature empty state on first load: while `/api/learn/state` is still in flight, the page already prints "PeakCut has not looked yet. Press the button below and it will read the last 28 days first." and shows the "Analyse and improve" button disabled with no reason — a false claim ("has not looked yet") over a page that is merely loading. | `factsBlock` prints the has-not-looked copy whenever `st.length` is 0 (learn.js:83-86), which includes `STATE === null`; `runBlock` disables the button when `STATE` is null (`can = STATE && STATE.can_run`, learn.js:249) with `why` empty; `load()` paints `body()` before awaiting the read (learn.js:292-307). | While `STATE` is null, show a one-line "Reading the numbers…" state (the learn-hooks/post-time cards already use exactly this pattern, e.g. learn-hooks.js:37). |
| U2 | minor | `web/feat/learn.js:260-263, 317` | The "Look at [28 days]" select has no visible effect until a run button is pressed: its value is only read inside `run()` (learn.js:317). Changing it redraws nothing and nothing says so — a beginner can believe the page ignored their choice. (The control is not dead — the value does reach `/api/learn/run`.) | Select `#lrn_days` (learn.js:261-263) has no `data-act` and plugins.js has no change-event wiring (grep `addEventListener\("change"\|onchange` over plugins.js → only MutationObserver watches, plugins.js:175-193); consumed at learn.js:317. | Either a one-line hint under the run row ("the buttons use the years you pick here"), or re-read the preview when the select changes. |

## What passed (no finding)

- **HTTP**: `/app/improve` → 200. Every route the owned files call exists: `/api/learn/state` (api_learn.py:57), `run` (72), `undo` (103), `signals` (188), `arms` GET/POST/DELETE (224/239/275), `cost` (288), `/api/learn/report` (api_learnreport.py:38), `/api/learn/hooks` (api_hooks.py:43), `/api/posttime` (api_posttime.py:43), `/api/brandai/suggest` (api_brandai.py:52), `PUT /api/brand` (api_brand.py:48).
- **Server-shape matches** (client reads vs server fields): learn.js vs `learn.log()` (studio/learn.py:85-97 `{rounds,can_run,why_not,content:{clips,lines}}`) ✓; learn.js `costLine` vs `/api/learn/cost` `{calls,tokens,at,report}` incl. the `report` string branch (learn.js:123-125) ✓; learn.js `changeLine` reads `c.setting`/`c.value`/`c.why`/`c.expect` ✓; learn-hooks vs `/api/learn/hooks` `{ok,hooks,count,strong,workable,weak,note}` (api_hooks.py:84-85) ✓; post-time vs `/api/posttime` `{enough,best:[{hour,label,mean_views,posts,note}],total,note,ok}` ✓; learn-arms vs `/api/learn/arms` GET `{"trial":…}` / POST `{target,value,other,other_value}` ✓; learn-arrows row fields `when`/`days`/`saying`/`effect` exist (learn_report.py:21-22,185-197) ✓.
- **Contrast** (WCAG relative-luminance math from the palette at web/index.html:17-23, page body bg `--frame:#000000`, cards on `--bg:#0A0A0A`/`--card:#111111`): `--ink #F5F5F5` on bg ≈ 18.9:1; `--dim #A3A3A3` on bg ≈ 7.9:1, on card ≈ 7.5:1; `--faint #7C7C7C` on card ≈ 4.5:1 (≥4.5 for the 13px text it carries); `--good #34D399` on `--good-soft #0B2A1E` ≈ 8.0:1; `--bad #F87171` on `--bad-soft #2B1416` ≈ 6.3:1; `--brand #FF8B33` on bg ≈ 8.5:1; `.lhk .pill.w #B98900` on card ≈ 6.0:1; `--brand-ink #160D05` on `--brand` ≈ 8.2:1. All text pairs ≥ 4.5:1.
- **390px viewport**: learn.js grid `max-width:900px` only (no forced width), all `.run`/`.hd`/`.top` rows `flex-wrap:wrap`; brand-ai `.ask` wraps with input `min-width:220px` (fits the ~320px box content width alongside the Ask button); learn-arms `.two` collapses to one column at ≤620px (learn-arms.js:24) with `min-width:0` on fields (learn-arms.js:18); learn-hooks/post-time rows wrap. No fixed-width or non-wrapping rule found in any owned file.
- **Controls alive**: `data-act="lrnrun"/"lrndry"/"lrnundone"` all have handlers (learn.js:365-371); click routing passes the button through (plugins.js:165), so `undo(btn.dataset.at)` works; `#lrn_days` feeds run (learn.js:317). brand-ai's Apply disables itself while saving and restores on failure (brand-ai.js:72-84). learn-arms keeps form answers across redraws (learn-arms.js:51-54).
- **States**: every owned card has a loading text, an empty state from the server's own words, and a catch that writes one sentence (learn-hooks.js:37/25/45-48; post-time.js:33/21/41-44; learn-arrows.js:40/32/48-51; learn.js:244-247 working state, 276 error box, 218-220 rounds empty state).
- **Empty-state honesty**: `noClips()`/`noChannel()` require positive knowledge before showing "Nothing to read yet" (learn.js:148-172) — matches the contract's "a zero is a claim" rule; `num()` treats non-finite values as missing rather than zero (learn.js:111-115).

## One-line summary

Page loads (200) and most cards are honest and well-stated, but the brand-ai card crashes on every Ask (`.map` on a dict), the learn-arrows card blanks every setting name (`c.key` vs `setting`), and learn.js's repaint wipes the four decorative cards on every load/action.
