# API audit — formats, schedule, hunt, rules (agent-156)

Scope: GET /api/moods, GET /api/schedule/preview, GET /api/schedule/round,
GET /api/rules, GET /api/hunt/watching — plus the sounds routes and the page
code that consumes them. Server under test: http://127.0.0.1:8798.
Method: read `studio/api_sound.py`, `studio/api_preview.py`,
`studio/schedule_ai.py`, `studio/meme.py`, `studio/music.py`,
`studio/rules.py`, then curl every route with realistic and invalid
parameters, then trace each answer into `web/index.html` and
`web/feat/*.js`. No 500 was raised on any owned route.

## Findings

| Severity | Where | What | Evidence | Fix |
|---|---|---|---|---|
| important | `studio/api_preview.py` — GET /api/schedule/preview | An invalid clock is answered with internally inconsistent JSON: `preview` says `/ST 09:00` (the normalized default) while `times` echoes the raw input, so the answer claims 25:99 was scheduled | `GET /api/schedule/preview?times=25%3A99` → `{"ok":true, "preview":"... /ST 09:00 /F\n", "times":["25:99"], "note":"Copy this and run it yourself..."}` | Echo the clock the preview actually used, or answer `ok:false` with a note that the clock was replaced |
| important | `studio/api_preview.py` — GET /api/schedule/preview | When the platform is unknown the answer is `ok:false` with a good error preview, but the note still tells the person to run it | `GET /api/schedule/preview?times=09:00&os=banana` → `ok:false`, preview `# unknown platform 'banana', use windows, macos or linux`, note `Copy this and run it yourself. PeakCut does not touch your scheduler.` | When `ok` is false, the note should say the plan could not be made and what to change |
| important | `studio/schedule_ai.py:267` (`_clock`) via GET /api/schedule/round | An invalid clock is silently replaced with the default 06:00 and answered `ok:true` with no note | `GET /api/schedule/round?times=banana` → `{"ok":true, "times":["06:00"], "preview":"... at 06:00 ..."}` — banana nowhere in the answer | Say the clock was replaced (or reject); the times/preview pair at least agrees, so only the silence is wrong |
| important | `studio/api_preview.py:135-141` — GET /api/hunt/watching | Every exception is swallowed and the answer is `{"watching":[]}`, identical to a genuine empty answer. The page has an error path for this route that can never fire, so a crashed watcher reads as "you watch nothing" | Route body catches all exceptions and returns `{"watching":[]}` (lines 138-141); `web/feat/live.js:200-206` maps a failed read to `rows=[]` plus an error sentence | Answer `ok:false` with an error sentence on exception, so the page's existing handler works |
| important | `studio/api_sound.py:146` (via `_meme_file:99`) | A wrong mood name in the meme branch gets a message that blames the build step: banana is not a mood, so building can never make it. The music branch's message is correct | `GET /api/sounds/meme/banana` → 404 `The banana sound has not been made yet. Build the sounds first.`; `GET /api/sounds/music/banana` → 404 `There is no music bed called banana.` | Mirror the music wording, e.g. "There is no meme noise called banana." |
| important | `studio/api_sound.py:46` (`_note`) → `web/feat/sounds.js:246-250`, `web/feat/mood.js:97-99` | Meme rows carry a bare visual-treatment word as their description (`"freeze"`, `"push-in"`, `"shake"`, `"vignette"`), and both consumers prefer the server note over their own plain sentences, so the Sounds page describes hype as just "shake" | `GET /api/moods` → `{"name":"hype","kind":"meme","note":"shake"}` next to `{"name":"hype","kind":"music","note":"fast and loud: a big play, a win, a run"}`; `sounds.js` `about()` returns `row.note` first; `mood.js:97` pushes `row.note` first. The page's own copy says hype is "An airhorn, then a bass drop. The loudest pair here." (`sounds.js:52`) | Send a plain sentence from the server (meme.py has no hint; its `effect` is a list so `_note` falls through to `treatment`), or let `BY_NAME` win when the note is a single treatment word |
| minor | `web/ascii.js:171-182` (`rules()`, reached from `PeakTools.ruleBadge`) | The file is loaded by no page — `index.html:922` loads `/assets/gradient-ascii.js`, and a grep of all six HTML files plus all 76 `web/feat/*.js` finds no `PeakTools` caller — and its `/api/rules` call expects a `{rules:{...}}` table while the route answers a single badge, so if anything ever loads the file every badge reads "Rules unknown" | `grep PeakTools` over `web/` matches only `ascii.js` itself; `GET /api/rules` (no params) → `{"rule":"unknown",...,"label":"Rules unknown","tone":"","can_clip":true,"blocked":false}` with no `rules` key | Delete the dead file or update `rules()` to the badge shape and give it a page |
| minor | `studio/api_preview.py:54-56` | The built-in fallback for an unknown channel is unreachable in the live path and disagrees with the shape it would shadow: it lacks `tone`/`can_clip`/`blocked` and says label "Unknown" with a full note | `GET /api/rules` (no params) → label `Rules unknown`, empty `note`, `tone`/`can_clip`/`blocked` present — the live path goes through `rules.badge` (`studio/rules.py:201`) | Point the fallback at `badge` or give it the same keys |
| minor | `web/feat/mood.js:55` vs `web/feat/sounds.js:212` | The two consumers read the `ready` flag with opposite polarity: the clip dialog treats a missing flag as playable (`r.ready !== false`), the Sounds page as not built (`r.ready === true`) | Both lines as quoted; the server always sends `ready`, so nothing is wrong today | Pick one polarity in both files; the Sounds page's is the safer one |

## What checked out

- GET /api/moods → 200, 13 rows, `count`/`meme`/`music` index keys present; every row has `ready`.
- GET /api/rules?platform=twitch&handle=xqc → 200 with a real rule (`"rule":"ask"`, note about reposting, `tone:"warn"`, `can_clip:true`).
- GET /api/schedule/preview with a valid clock → 200, consistent preview and times.
- GET /api/schedule/round → 200, times echo agrees with the preview (both come from the plan).
- GET /api/hunt/watching → 200 `{"watching":[]}` on a fresh install (the empty answer itself is correct).
- GET /api/sounds/banana/hype → 404 `Sounds are served as music or meme, not banana.`; GET /api/sounds/meme/hype → 200, audio/wav, 261164 bytes.
- POST /api/jobs/nope-123/peek → 404 `No such job.`; POST /api/hunt/watch with `{}` → 400 `Name a platform and a channel.`
- Page side: `sounds.js` and `schedule.js` have loading, empty and error states; `mood.js` documents the duplicate-name rule ("hype" as meme and music) and keys rows as `kind:name` (`sounds.js:207`), so no id collides.
