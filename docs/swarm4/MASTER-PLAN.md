# The ten swarms: what each one builds

PeakCut gets a rebuilt menu, a YouTube-Studio-style Analytics section, an AI that reads the
numbers and improves the pipeline, and a deep clean of everything else. That is far too much
for one pass, so it is split into ten waves of eighteen agents. Each wave has one job, and the
next wave starts from what the last one left behind.

## The rule every agent follows

Read `docs/swarm3/CONTRACT.md` first, then `web/feat/heard.js` as the file to copy. A feature is
one file in `web/feat/`, it registers through `window.PeakCut`, and it never edits `web/index.html`.
The gates are `node --check`, `tests/test_feat_files.py`, and a live look in the browser.

## Wave 1 — the menu and the pages it opens

The complaint that started this: everything useful is buried in Settings. This wave moves it out.

| # | Agent | Builds |
|---|---|---|
| 1 | menu-core | `web/feat/menu.js`: the menu grouping helper and the page registry conventions the rest of the wave uses |
| 2 | analytics-shell | `web/feat/analytics.js`: the Analytics page shell — tabs, date-range control, filter bar, empty states |
| 3 | analytics-kpi | The top row of number cards on Analytics (views, watch time, impressions, CTR, average view duration, subscribers) |
| 4 | analytics-charts | The two big charts: views over time and watch time over time, with a comparison period |
| 5 | analytics-table | The video-by-video table with sortable columns and per-row numbers |
| 6 | analytics-audience | The Audience tab: returning vs new, geographies, when viewers are on |
| 7 | analytics-traffic | The traffic-source breakdown, including the Shorts feed |
| 8 | settings-move | Moves Brand, Transcription, Tools and Connected apps out of Settings into the main menu, keeping every existing address working |
| 9 | settings-explain | A one-line plain-English note beside every option on every settings page |
| 10 | menu-icons | The icons the new pages need, added to the icon map |
| 11 | nav-search | A quick filter at the top of the menu that narrows the rows as you type |
| 12 | nav-responsive | The narrow-window behaviour of the longer menu |
| 13 | page-guard | A page that is asked for but not built yet says so instead of drawing nothing |
| 14 | docs-menu | `docs/menu.md`: what each menu row is for, in one line |
| 15 | tests-menu | `tests/test_menu_pages.py`: every registered page has a path, a label, an icon that exists, and no clash |
| 16 | reviewer | Reads the wave's diff and writes `docs/swarm3/WAVE1-REVIEW.md` |
| 17 | fixer | Fixes what the reviewer found, writes `docs/swarm3/WAVE1-FIXES.md` |
| 18 | prover | Runs every gate and writes `docs/swarm3/WAVE1-PROOF.md` |

## Wave 2 — the analytics backend

The page needs real numbers. This wave builds the server side, against the YouTube Analytics API
and against PeakCut's own records.

| # | Agent | Builds |
|---|---|---|
| 1 | scope | Adds `yt-analytics.readonly` to `accounts.YT_SCOPES` and a reconnect path so an existing account can grant it |
| 2 | summary | `studio/api_analytics.py`: `GET /api/analytics/summary` — the KPI numbers for a date range |
| 3 | timeseries | `GET /api/analytics/timeseries` — one metric over a range, daily |
| 4 | videos | `GET /api/analytics/videos` — per-video rows with every column the table needs |
| 5 | audience | `GET /api/analytics/audience` — returning vs new, geography, hours |
| 6 | traffic | `GET /api/analytics/traffic` — traffic sources, Shorts feed included |
| 7 | retention | `GET /api/analytics/retention` — the audience-retention curve for one video |
| 8 | own-numbers | The same numbers from PeakCut's own records (clips made, posts, views we already track) so the page works with no YouTube connection |
| 9 | cache | A short-lived cache so a page reload does not spend quota |
| 10 | errors | Honest failure text for every case: no connection, no scope, quota spent, no data yet |
| 11 | mock | `tests/fixtures/analytics_*.json`: recorded response shapes, so tests need no network |
| 12 | contract | `docs/ANALYTICS-API.md`: every route, its parameters, its answer |
| 13 | tests-summary | `tests/test_analytics_api.py` — the summary and timeseries shapes |
| 14 | tests-tables | `tests/test_analytics_tables.py` — videos, audience, traffic |
| 15 | tests-own | `tests/test_analytics_own.py` — the numbers with no YouTube connection |
| 16 | reviewer | `docs/swarm3/WAVE2-REVIEW.md` |
| 17 | fixer | `docs/swarm3/WAVE2-FIXES.md` |
| 18 | prover | `docs/swarm3/WAVE2-PROOF.md` |

## Wave 3 — the AI that reads the numbers

The button the person asked for: press it, and PeakCut studies what worked and improves itself.

| # | Agent | Builds |
|---|---|---|
| 1 | research | A deep web read on what makes short-form video perform: hook writing, retention, titles, thumbnails, posting cadence. Writes `docs/research/shortform-performance.md` |
| 2 | signals | `studio/learn.py`: turns raw analytics into plain facts ("the first 3 seconds lose 60%") |
| 3 | prompt | `studio/learn.py`: the prompt that asks the AI for concrete changes, written so the answer can be applied |
| 4 | apply | Applying the AI's answer: brand, hook style, clip length, caption look — each one recorded so it can be undone |
| 5 | versioning | Every applied change is a numbered version with its before and after, so it can be compared and rolled back |
| 6 | route | `POST /api/learn/run`, `GET /api/learn/state`, `POST /api/learn/undo` |
| 7 | report | The written report the AI produces, saved as a page a person can read |
| 8 | ui-button | `web/feat/learn.js`: the button, the progress, the report, and the undo |
| 9 | ui-report | The report page: what changed, why, and what it expects to improve |
| 10 | offline | What happens with no AI key: the facts are still shown, only the advice is missing |
| 11 | safety | The rules: never more than one change per press, never a change that cannot be undone, never a claim without a number behind it |
| 12 | docs | `docs/LEARN.md` |
| 13 | tests-signals | `tests/test_learn_signals.py` |
| 14 | tests-apply | `tests/test_learn_apply.py` |
| 15 | tests-undo | `tests/test_learn_undo.py` |
| 16 | reviewer | `docs/swarm3/WAVE3-REVIEW.md` |
| 17 | fixer | `docs/swarm3/WAVE3-FIXES.md` |
| 18 | prover | `docs/swarm3/WAVE3-PROOF.md` |

## Wave 4 — the rest of the menu

Every remaining feature gets a home in the main menu, and the Settings page is cut down to the
things that are genuinely settings.

| # | Agent | Builds |
|---|---|---|
| 1 | brand-page | Brand as its own page |
| 2 | transcribe-page | Transcription as its own page |
| 3 | tools-page | The Tools page, split into one row per tool |
| 4 | apps-page | Connected apps as its own page |
| 5 | creators-page | A creators overview page |
| 6 | live-page | A page for what is recording right now |
| 7 | schedule-page | A page for the posting schedule |
| 8 | ai-page | AI settings as their own page |
| 9 | storage-page | Storage as its own page |
| 10 | account-page | Profile and security as one page |
| 11 | admin-page | The owner's page |
| 12 | help-page | A page that explains each part of PeakCut in a line |
| 13 | old-links | Every old address still works and redirects |
| 14 | docs | `docs/menu.md` updated |
| 15 | tests | `tests/test_menu_pages.py` extended |
| 16 | reviewer | `docs/swarm3/WAVE4-REVIEW.md` |
| 17 | fixer | `docs/swarm3/WAVE4-FIXES.md` |
| 18 | prover | `docs/swarm3/WAVE4-PROOF.md` |

## Wave 5 — polish

| # | Agent | Builds |
|---|---|---|
| 1-4 | empty, loading, error, narrow | Every new page in its four hard states |
| 5-8 | wording, icons, spacing, colour | The look, matched to the existing palette |
| 9-12 | keyboard, focus, labels, contrast | Getting around without a mouse |
| 13-16 | speed, caching, big numbers, long lists | The page stays quick with a year of data |
| 17 | reviewer | `docs/swarm3/WAVE5-REVIEW.md` |
| 18 | prover | `docs/swarm3/WAVE5-PROOF.md` |

## Wave 6 — the AI deep link

The engine from wave 3, made to actually change what PeakCut does, end to end.

| # | Agent | Builds |
|---|---|---|
| 1-4 | prompt-per-part | One prompt per thing being improved: hooks, clip length, captions, posting time |
| 5-8 | wire-per-part | Each improvement reaches the pipeline (`brain.py`, `jobs.py`, `render.py`, `posting.py`) |
| 9-12 | measure | Before-and-after measurement, so a change can be judged |
| 13-15 | guard | The rules that stop a bad change: rate limits, minimum sample, no change on a guess |
| 16 | reviewer | `docs/swarm3/WAVE6-REVIEW.md` |
| 17 | fixer | `docs/swarm3/WAVE6-FIXES.md` |
| 18 | prover | `docs/swarm3/WAVE6-PROOF.md` |

## Wave 7 — tests and evidence

| # | Agent | Builds |
|---|---|---|
| 1-6 | route tests | Every analytics and learn route, tested |
| 7-12 | page tests | Every new page, tested for shape and for its hard states |
| 13-15 | regression | The existing suites still pass |
| 16 | reviewer | `docs/swarm3/WAVE7-REVIEW.md` |
| 17 | fixer | `docs/swarm3/WAVE7-FIXES.md` |
| 18 | prover | `docs/swarm3/WAVE7-PROOF.md` |

## Wave 8 — the documents

| # | Agent | Builds |
|---|---|---|
| 1-6 | README, DEPLOY, AGENTS, .env.example, landing page, admin page | Every place that describes PeakCut now describes the new menu and the new numbers |
| 7-12 | docs/menu.md, docs/ANALYTICS-API.md, docs/LEARN.md, docs/research/shortform-performance.md, docs/SWARM-PLAN-3.md, docs/swarm3/* | Kept true |
| 13-15 | screenshots | Real pictures of the new pages |
| 16 | reviewer | `docs/swarm3/WAVE8-REVIEW.md` |
| 17 | fixer | `docs/swarm3/WAVE8-FIXES.md` |
| 18 | prover | `docs/swarm3/WAVE8-PROOF.md` |

## Wave 9 — the whole thing, run

| # | Agent | Builds |
|---|---|---|
| 1-6 | one real video through the pipeline, and every frame looked at |
| 7-12 | every test, run, with the output kept |
| 13-15 | every page, opened, with a picture |
| 16 | reviewer | `docs/swarm3/WAVE9-REVIEW.md` |
| 17 | fixer | `docs/swarm3/WAVE9-FIXES.md` |
| 18 | prover | `docs/swarm3/WAVE9-PROOF.md` |

## Wave 10 — the last word

| # | Agent | Builds |
|---|---|---|
| 1-6 | a read-only audit of the whole change, one area each |
| 7-12 | the fixes those audits found |
| 13-15 | the final regression run |
| 16 | the final review | `docs/swarm3/FINAL-REVIEW.md` |
| 17 | the final fixes | `docs/swarm3/FINAL-FIXES.md` |
| 18 | the final proof | `docs/swarm3/FINAL-PROOF.md` |
