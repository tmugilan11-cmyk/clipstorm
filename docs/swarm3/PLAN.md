# Swarm 3 — 18 agents, one pass

The contract every agent must read first: `docs/swarm3/CONTRACT.md`.
The reference implementation of a feature file: `web/feat/heard.js` (already built,
`node --check` clean, live in the browser, and its drawing was verified against
a fake running job: fill 41.3%, 8 part marks, 3 lit, "Listened to 20:40 of 50:00").

## Why this shape

`index.html` is frozen. Every feature is one new file in `web/feat/`. The loader
`web/plugins.js` finds every file in that folder, runs it, and calls it on the
hooks it declares. So eighteen agents can work at once and never write to the
same file.

## The eighteen

Front end (one file each, `web/feat/<slug>.js`):

| # | slug | what it does | endpoint it uses |
| --- | --- | --- | --- |
| 1 | `style-tiles` | caption style becomes a grid of real preview frames | `GET /api/captions/styles`, `GET /api/style/preview` |
| 2 | `mood` | pick a meme noise or music bed for a clip | `GET /api/moods` |
| 3 | `stats` | a clip's own YouTube numbers, in the clip dialog | `GET /api/stats/video` |
| 4 | `filters` | All videos: status pills with counts + a search box | none (client side) |
| 5 | `stage` | four dots on each job card: download, listen, pick, make | none (reads `stage`) |
| 6 | `pill` | topbar: "2 videos running" with a jump button | none (reads `S.jobs`) |
| 7 | `log` | "Show log" on a failed job | `GET /api/jobs/{jid}` `log_tail` |
| 8 | `peek` | stills on finished clips, one button to take them | `POST /api/jobs/{jid}/peek`, `GET .../peek/{cid}` |
| 9 | `grid` | a week of posting, as a grid, in Settings > Tools | `GET /api/overview` |
| 10 | `autopilot` | install the automatic clipping schedule from the browser | `GET /api/autopilot/spec`, `/preview`, `POST /install` |
| 11 | `keys` | keyboard shortcuts that never fire while typing | none |
| 12 | `day` | "Make my day": one button, one confirm, a job | `GET /api/overview`, `POST /api/jobs` |
| 13 | `history` | version chips for a rendered clip | `GET .../clips/{cid}/history`, `PATCH` |

Back end and proof:

| # | what it does |
| --- | --- |
| 14 | `queue` — add `GET /api/posts` (the posting queue, read only) so the grid has something real to draw |
| 15 | `log_tail` — extend `GET /api/jobs/{jid}` with the last lines of the job's log |
| 16 | tests — one plain-assert file per new route and per new file on disk |
| 17 | reviewer — read only, hunts for broken code, XSS, dead handlers, lies in docs |
| 18 | fixer — fixes only what the reviewer found |

## Order

Everything except 17 and 18 runs at once. 17 runs when they are done, 18 runs
after 17. There is no barrier between the other phases because each file is
independent by construction.
