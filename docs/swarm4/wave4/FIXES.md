# Wave 4 — fixes

All findings from `REVIEW.md` are answered below. Every edit was followed by `node --check` on the file touched,
`python tests/test_feat_files.py` and `python tests/test_menu_pages.py`; the last two print "All checks passed."
after every change. `tests/test_menu_pages.py` went from 312 ok to 313 ok: the new `/api/sounds/{kind}/{mood}` route
adds one check.

**One finding could not be fixed here.** I5 needs three lines changed in `web/index.html`, which this task does not
allow me to edit. The exact change is written out at the bottom of this file.

## C1 — Sounds page pointed every Play button at a route that never existed — fixed

The page built `/media/bed_hype.wav` and `/media/hype.wav`. There is no such route: the only `/media` route is
`studio/server.py:1152` `@app.get("/media/{jid}/{name}")`, which wants a job id and only serves `.mp4`/`.jpg`. The
mood word was also wrong as a file name: `studio/meme.py:51` gives `"hype"` the sounds `["airhorn", "bass_drop"]`, so
even a real `/media/hype.wav` would 404 for 9 of the 13 buttons.

Two changes, server first:

- `studio/api_sound.py` — added `GET /api/sounds/{kind}/{mood}`. It answers with the actual file: for `kind="music"`
  it uses `music.MOODS` and `music.bed_path(mood)`; for `kind="meme"` it finds the mood in `meme.load_moods()` and
  asks `meme._resolve_sound(...)` for the path. It returns `FileResponse` with the same private cache header the
  other file routes use, and 404s with a sentence a person can read when the sound is simply not built yet.
  `music._mood()` silently falls back to `"chill"` for an unknown name, so the route checks membership itself
  rather than trusting it; and `meme.sound_ready()` is checked **before** resolving, so a plain GET can never start
  the multi-second `make_sounds` build.
  `_resolve_sound` is private, but it is the only resolver that answers "which file is this mood"; the public
  helpers (`sound_names`, `sound_ready`) cannot. The call is commented to say so.
- `web/feat/sounds.js` — `urlFor` now returns `` `/api/sounds/${kind}/${key}` ``. `play()` first sends a `HEAD` to
  that address, so the page can tell three cases apart instead of blaming the browser for all of them:
  a 404 says "The … sound has not been made yet. Press Build the missing sounds.", any other bad answer names the
  status, and only a good answer goes on to `el.src`/`el.play()`, where a decoder refusal keeps the old
  "could not be played by this browser" sentence. The header comment was rewritten: it used to document the missing
  route as a known gap, which is no longer true.

Proven by calling the route directly, not by reading it:

| call | result |
|---|---|
| `sound_file("music", "hype")` | 200, `…\data\music\bed_hype.wav` |
| `sound_file("meme", "hype")` | 200, `…\data\sounds\airhorn.wav` |
| `sound_file("meme", "embarrassing")` | 200, `…\data\sounds\sad_trombone.wav` |
| `sound_file("music", "nope")` | 404 "There is no music bed called nope." |
| `sound_file("meme", "nothere")` | 404 "The nothere sound has not been made yet. Build the sounds first." |
| `sound_file("bogus", "hype")` | 404 "Sounds are served as music or meme, not bogus." |

The second row is the whole finding: the mood word is not the file name. The third row is why the fix goes through
`_resolve_sound` rather than guessing: `embarrassing`'s first sound, `mine/hello_darkness`, does not exist, so a
first-name guess would break the one mood the review said was already half-right.

## I1 — Help promised an auto-cut switch that does not exist — fixed

`web/feat/help.js:96` ended a sentence "...the Live page holds the watch list and the auto-cut switch." A search of
`web/` for `auto.cut`/`autocut`/`auto_cut` finds only that line. The sentence now ends at "...the Live page holds the
watch list." and adds, in the same plain voice, "PeakCut cannot switch auto-cut on for a channel by itself yet."

## I2 — Traffic chart asked for dates the route ignores — fixed

`web/feat/analytics-traffic.js` sent `?start=…&end=…`. The route (`studio/api_analytics.py:374-375`) takes only
`days: int = Query(28, ge=0, le=3650)`, so FastAPI dropped those parameters, every tab was answered with the default
28 days, and the page then labelled the chart with the range the person had picked. The chart and its label
disagreed, and nothing said so.

`asked()` now asks only in `days`: an explicit `days` wins; otherwise a start+end pair is turned into a whole-day
span (`Math.round((end - start) / 86400000) + 1`, the same arithmetic `analytics-table.js` uses) and clamped to
0–3650 like the route's own `Query` bounds. `read()` already prefers the answer's own `range` field and `paint()`
already prefers it over the asked-for one, so the band now shows the window that was actually answered.

Checked against six inputs: no range -> no query string; `{days: 90}` -> `?days=90`; 1–30 Jan -> `?days=30`;
2000->2030 -> `?days=3650`; a reversed pair -> `?days=0`; `{days: 7, start, end}` -> `?days=7`.

## I3 — Clip formats invented "0" for a number nobody stated — fixed

`web/feat/formats.js:74` was `const num = (v) => { const n = Number(v); return Number.isFinite(n) ? n : 0; };`.
`Number(null)`, `Number("")` and `Number(undefined)` all pass that test, so a format with no `needs_parts` was drawn
as "0 pieces" — and the copy at `:200` then chose the plural, "0 pieces", which reads as a measured fact.

`num` now returns `null` for `null`/`undefined`/`""`/non-finite, matching `web/feat/live.js:53-57`. The three print
sites were then taught about the null: a shape card says "pieces not stated" instead of a count, and the two
headline counts at `:177-178` are printed only when the number is real. The two count fallbacks at `:110` and `:127`
are untouched: there `out.length` is a real count of rows that exist, not a guess.

Checked directly: `null`, `undefined`, `""` and `"abc"` all give `null`; `0` gives `0`; `2` gives `2`; `"3"` gives `3`.

## I4 — Schedule could not tell "not the operator" from "the page could not ask" — fixed

`web/feat/schedule.js:57-62` read the session inside a `try` and returned `false` from the `catch`, so a thrown
`P.state()` painted the same sentence as a signed-in non-operator: "Only the operator account can write a task into
this computer's scheduler."

`isOwner()` now has three answers — `true`, `false`, and `null` when it genuinely could not tell (the state threw, or
the user field was missing). `drawClipActs()` paints three things: the Install control for the operator, the
operator-only sentence plus the copy fallback for anyone else, and, for `null`, "PeakCut could not tell whether you
are the operator, so Install is hidden for now. Reload the page to ask again. You can still copy the text and run it
yourself." The person is never told they lack permission when what actually happened is that the page failed to ask.

## I5 — Two Usage screens both live — recorded, not fixed (needs `web/index.html`)

Not a wrong finding, and not fixable from here. `web/index.html:1404` still branches `v === "usage"` before the
feature-page branch, so `/app/usage` opens the old legacy screen, while the wave-4 `ai-usage` page only appears if
someone types `/app/ai-usage`. The two disagree on the same numbers: the legacy `fmtK` (`:1126`) prints `12.3K` and
turns a missing value into `0`, while `web/feat/usage.js:85-88` prints `12.3k` and says "not known".

The rename to `ai-usage` is required and is not the defect (note 1 in the review). The defect is that both screens
are reachable and the older one wins. Exact change, for whoever may edit `web/index.html`:

1. `:1404` — delete the branch, so the feature page draws:
   `  else if (v === "usage") { view.innerHTML = `<div id="usage"></div>`; loadUsage(); }`
2. `:1354` — drop `usage: "usage"` from `ROUTES`:
   `const ROUTES = {overview: "", library: "videos", settings: "settings", review: "review"};`
3. `:1114`, `:1213`, `:1308` — point the three entry buttons at the new page: `data-v="usage"` -> `data-v="ai-usage"`
   (and `S.view === "usage"` -> `=== "ai-usage"` at `:1308`, `:1316`, `:1348`).

After that the legacy `loadUsage`/`drawUsage`/`fmtK`/`tokenChart`/`hbars` block (`:2074` onward) has no caller and
can be deleted, which is also what removes the `12.3K`/`0` disagreement for good.

## M1 — creators.js used em dashes and a trailing ellipsis — fixed

`web/feat/creators.js` `:5` (header), `:267-268` (the lede's two dashes) and `:275` (the hint) now use `-`; `:223`
reads "Reading your creators." instead of ending on `…`. A search for `—` and `…` in that file now returns nothing.

## M2 — two silent `catch {}` blocks — fixed

- `web/feat/menu-icons.js:47` — `catch {}` became `catch (err) { return false; }`, so a refused write is reported as
  "this icon did not land" instead of looking like success.
- `web/feat/icons-extra.js:139` — the `try`/`catch` was removed entirely, with a comment: dispatching an event on
  `document` does not throw, so the guard was only hiding the possibility that it someday would.

## M3 — copy counted things that can grow — fixed

`sounds.js:337` said "Nine meme noises and four music beds." and `formats.js:1`, `:327`, `:356` said "eight shapes"
/ "The eight shapes". Both numbers are correct today (`meme.load_moods()` is 9, `music.MOODS` is 4, `formats.FORMATS`
is 8 — checked by running them), but neither file reads them from the server, so the sentence would quietly go stale
the day a row is added. The copy now names the things without counting them: "Meme noises and music beds.", "The
shapes a clip can take", "The clip shapes and the caption looks", "The shapes".

## M4 — Usage turned "the route said nothing" into zero — fixed

`web/feat/usage.js` contradicted its own rule at line 78 ("Never a silent zero for a value the route did not send").
Dropped the `|| 0` from the day series, the busiest-day line and the purposes rows. A day the route did not send a
count for is now drawn as nothing at all — not the zero-tick that `:149` draws for a day the route *did* report as
zero, because a tick claims a measured zero — and the page says how many days were left out and why. A missing call
count reads "calls not sent" rather than "0 calls". The same shape at `:106` (the "today" line in the three figures)
was fixed the same way, since it would have printed "0 calls" for a day the route said nothing about.

## Suite status

The three suites this task requires are green after every change and green now, together:

- `python tests/test_feat_files.py` — `{"files": 47, "checks": 382}` / "All checks passed."
- `python tests/test_menu_pages.py` — "All checks passed. 313 ok"
- `python tests/test_insights_pages.py` — "All checks passed. 83 ok"
- `node --check` and `python -m py_compile` on all ten touched files.

`python tests/run.py` (the whole server suite, required by `AGENTS.md` for a change under `studio/`) runs everything
else green but ends on **one** failure: `tests/test_updates.py`. **That failure is not mine and is not about this
wave.** It asserts `len(updates.current()) == 40`, which requires a `.git` folder; this checkout has none
(`ls -d .git` -> "No such file or directory", `git rev-parse` -> "not a git repository"), so the version reads `""`
and the cascade takes the rest of that file with it. `studio/updates.py` shares no code with anything I touched.
The other 28 groups in `run.py` pass, including the two that cover this work directly:
"the feature files: one plug-in each, escaped, no clashing ids" and "pages in the menu: a label, an address, an icon,
and no clashes", plus "the ported features: … sounds …".

## `docs/swarm4/wave4/sounds.md`

`sounds.md:64` still says "There is no route that serves a wav". That was true when the doc was written and is not
true now; the doc is wave-4 design record, outside what this fix touched, and is left for its author to amend.
