# Wave 4 brief — the rest of the menu

Read this first, then `docs/swarm4/CONTRACT.md`, then `web/feat/heard.js` as the file to copy, then
`web/feat/menu-pages.js` because every page here is one more row in its table.

## What already exists (do not rebuild it)

- `web/plugins.js` is the loader. `window.PeakCut` gives you `css(id, text)`, `page(name, def)`, `add(name, def)`,
  `state()`, `api(path)`, `send(path, body, method)`, `toast(msg, kind)`, `_order`.
- Bare page globals you may call: `ic(name)`, `esc(text)`, `go(path)`, `drawSettingTab(tab, box)`.
- 39 feature files already serve. The page has 11 main-menu rows: Home, All videos, Review, Brand, Improve,
  Insights, Transcription, Tools, Connected apps, AI, Storage, Account.
- `web/feat/menu-pages.js` holds a `MOVED` table with one entry per moved setting
  (`where, tab, icon, what, cta, admin?, two?`). Adding a row there is how a new menu page appears — you do NOT
  need to touch `navHtml`.
- Backend modules that already work and are tested: `studio/jobs.py`, `creators.py`, `live.py`, `hunt.py`,
  `posting.py`, `zernio.py`, `formats.py`, `captions.py`, `meme.py`, `music.py`, `translate.py`, `autopilot.py`,
  `schedule_ai.py`, `rules.py`, `ytstats.py`, `vision.py`, `moments.py`, `peek.py`, `edit.py`, `brand.py`,
  `learn.py`, `ai_arms.py`, `learn_guard.py`, `learn_signals.py`, `learn_report.py`, `hookscore.py`,
  `prompt_text.py`, `brand_ai.py`, `api_*.py`.

## What wave 4 adds

Seven new main-menu rows. Every one is a real page with real controls, one plain-English line beside each
control, and an honest empty state that names what is missing instead of showing zeros.

| slug | menu row | group | what it must show and do |
|---|---|---|---|
| `creators` | Creators | Creators | Every creator with its channel, its connected accounts, its track (gaming/irl/music), and a New creator button. Reads `/api/creators`; edits go through the existing creator routes. |
| `live` | Live | Make | Who is streaming now, the watch list with add/remove, and the auto-cut switch. Reads `/api/hunt/live`, `/api/hunt/watching`, `POST /api/hunt/watch`, `/api/hunt/unwatch`. |
| `schedule` | Schedule | Set up | The paste-ready Windows task text for clips (`autopilot.spec`) and for Improve rounds (`schedule_ai.spec`), a times field, and Install/Remove that only arms on a second press. Never installs on one click. |
| `help` | Help | Set up | Short answers to the questions a first-run person actually asks: where do clips come from, why is nothing posting, what does a round change, what does it cost. Links to the docs pages. |
| `usage` | Usage | Set up | The AI use page as a menu row: calls, tokens, cost, per-day bars. Reads `/api/usage`. |
| `formats` | Clip formats | Make | The 8 clip formats with one line each, and the 35 caption looks as read-only tiles that load a real `/api/style/preview` frame. Reads `/api/formats`, `/api/captions/styles`. |
| `sounds` | Sounds | Make | The 9 meme noises and 4 music beds, each with a Play button that uses an `<audio>` element pointed at the served wav, plus what makes it ready. Reads `/api/moods`. |

Plus, for the pages that already exist, wave 4 fixes the four known Important findings from wave 2's review:

1. `analytics-table.js:199` must send `days` (the route only reads `days`), not `from`/`to`.
2. `analytics-traffic.js:63` must stop labelling a window the server did not use.
3. The two dash characters in the analytics copy must both be the ASCII hyphen.
4. `tests/test_insights_pages.py:25`'s regex must also see `@router.delete(` so the DELETE route counts.

## Rules that decide whether your work is accepted

- One file per agent. Never edit `web/index.html`, `web/plugins.js`, or another agent's file.
- If you need something from `index.html` or `plugins.js`, say so in your report and draw around it.
- Escape every value that reaches markup with `esc(...)`. A number goes through `num(...)` first.
- Never invent a number. An empty list is `[]`, an unknown total is `—` or a sentence saying why it is unknown.
- Every fetch must name a route that exists in `studio/*.py`. Check with `grep -rn 'router.get\|@app.get' studio/`.
- A failure is one sentence in the page via `P.toast(...)` or an inline note. Never a silent catch.
- One plain-English line under each control, `.hint`, written for somebody who has never used the app.
- `node --check web/feat/<slug>.js` must pass, and `python tests/test_feat_files.py` must still pass.
- Write your report to `docs/swarm4/wave4/<slug>.md`: what you built, what it reads, what it cannot do, and the
  exact commands you ran.

## Time budget

You have 25 minutes. Read only the one or two files you need, then write. Ship a working file and write down
what is left rather than exploring for the whole budget.
