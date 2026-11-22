# Review of the Swarm 3 features

Author: agent-16, the fixer. The reviewer slot never produced this file, so the lead asked the fixer to
review the work and then fix it. Everything below was checked by reading the code, then confirmed against
the running server on port 8798 and in a real browser.

Scope reviewed: all fourteen feature files in `web/feat/`, the loader `web/plugins.js`, and the parts of
`studio/` those files call. `web/index.html` is frozen by the contract and was not edited.

## How this was checked

The seven checks the lead asked for, each run against the code and then against the live page:

1. Every feature file parses, and registers exactly one plug-in named after its own file.
2. Interpolated markup goes through `esc()`, so no server or user text reaches `innerHTML` raw.
3. No `id="..."` a feature file invents clashes with an id in `web/index.html`.
4. Every `data-act` a feature file emits has a handler behind it, in that file or in `index.html`.
5. Every fetch address exists as a route under `studio/`.
6. A failed fetch or a failed step is shown to the person, not swallowed.
7. No absolute `http://127.0.0.1` or `http://localhost` origin anywhere.

## Result in one line

Nothing is broken badly enough to stop a person using the app. One real injection hole and one silent
failure were found in the loader and are fixed. One control cannot work yet because the back end has no
step for it; its owner reported that honestly rather than faking it. Three suspicions turned out to be
wrong and no code was changed for them.

## Critical

None.

## Important

### I1. The sound picker cannot reach a render

`web/feat/mood.js` adds a `select data-f="mood"` to the clip dialog. The page collects every `[data-f]`
field when a clip is re-made (`web/index.html:3137`) and sends the body to
`POST /api/jobs/{jid}/clips/{cid}/render`. That route calls `studio/jobs.py:373 request_render`, which
reads only `captions`, `start`, `end`, `format`, `hook`, `title`, `description`, `style` and `layout`.
`mood` is not in that list, so it is dropped without a word. `studio/render.py:360 render_clip` has no
audio step either, and `studio/meme.py:491 apply` / `studio/music.py:206 apply` are imported only by
`studio/api_sound.py`. A person picks a sound and nothing changes in the clip.

This is not a web bug, and fixing it means adding a feature to the render pipeline, which this job must
not do. The owner of `mood.js` already wrote the gap down in `docs/swarm3/mood.md` under "What I could not
test", which is the right way to handle it.

**Disposition: CLOSED after the review, in the pipeline.** `studio/jobs.py` now reads `mood` in
`request_render` and applies it in `_add_sound` after the picture is rendered: the meme table first
(`meme.apply`), a music bed second (`music.apply`), because `funny` and `hype` are both. `mood` is written on
the clip only when the file really changed, so the page never shows a word about audio the clip does not
carry. Verified end to end on job `20261120-003159-e8505dbf42`: no sound → 11.0 s / 7.67 MB; `funny` →
11.6 s / 9.26 MB; `chill` → a different audio track with the bed 17.4 dB under the voice; `hype` → a frame at
8.5 s shows the shake; `win` → a fourth distinct track. `tests/test_mood_sound.py` (10 checks) pins it.

A second real bug was found on the way: `/api/moods` reported every meme noise as "not built yet", because it
asked for `<mood>.wav` while a mood names its own sounds (`hype` is airhorn then bass_drop). `meme.sound_ready()`
now follows the mood's own names and is a folder look, never a build.

### I2. The loader put an error message into the page unescaped: FIXED

`web/plugins.js:112` builds the "this part did not load" line with
`${String(err.message || err)}` straight into `innerHTML`. Any error whose text came from the server would
be injected as markup. The contract says never build markup from an unescaped value, and the loader is the
one place every card passes through, so it matters more there than anywhere else.

Fixed by escaping the message the same way the page does. Proved with a payload: a card that throws
`<img src=x onerror=alert(1)>` now renders as visible text, and the string `<img src=x` never appears in
the output. Checked in the running page against the served file, not just on disk.

### I3. A part that fails to load disappeared without a word: FIXED

`web/plugins.js:123` was `try { await def.load(); } catch {}`. A card whose `load()` threw simply never
appeared, and nothing said why. The contract asks for a soft failure: one quiet line, never a thrown
error, and never silence. Fixed with a single toast and one console warning, keeping the loop going so one
bad card cannot stop the others.

## Rejected

Three things looked wrong and were not. No code was changed for any of them.

- **The two mount watchers do not race.** `grid.js:139` and `autopilot.js:321` both watch `#toolsec` for a
  slow cold load. That looked like a duplicate-mount bug, but their guards are mutually exclusive:
  `grid.js:143` writes only when `mount.childElementCount` is zero, and `autopilot.js:325` returns at once
  when its own card is already there, otherwise appends only its own card and never touches what is
  already in the mount. Neither can overwrite the other's work. Checked live: with the Tools tab opened
  cold, the mount held exactly two cards, one `#tool_autopilot` and one `#tool_grid`, with no duplicates.
- **`day.js:141`'s address test is correct.** The bytes are `^https?:\/\/`, backslash-slash twice, then
  the closing slash and `i`. It is a well formed regex, not a mangled one; the doubled backslashes in a
  `grep` display are the raw file bytes, not a defect.
- **Nothing calls `/api/posts`.** That route was planned for the queue agent and never built. No feature
  file mentions it, so there is nothing to point at `/api/overview`.

## Minor, recorded and not fixed

- `web/plugins.js:84` still watches `#cbody` under the hook name `drawCreator`, but `index.html` has no
  function of that name (it is `drawCreatorForm` at `index.html:1937`). No feature file registers that
  hook, so the watch never has anything to call. Dormant, harmless, and fixing it would mean guessing
  which name was intended.
- The paint cache at `web/plugins.js:72` keys on `innerHTML.length`, so a repaint that happens to leave the
  length unchanged is skipped. `mood.js`, `stats.js` and `day.js` each work around this with their own
  `toggle` or `change` listener. Three workarounds for one loader limitation, but each file is correct on
  its own and none of them is broken, so this is recorded rather than reworked.
- `filters.js` re-counts every 800 ms and `pill.js` repaints every 1200 ms. Both write only when a value
  actually changed, so they are cheap. Not worth changing.

## What was actually changed

Two edits, both in `web/plugins.js`, both small:

1. Line 112: the "did not load" message is escaped before it goes into markup.
2. Lines 123 to 126: a failing `load()` now shows one toast and one console warning instead of nothing.

Nothing else was touched. No feature file was edited, `web/index.html` still has its 3214 lines, and no
Python file was changed.

## Checks after the change

- `node --check` on `web/plugins.js` and all fourteen `web/feat/*.js`: all parse.
- `python tests/test_feat_files.py`: `{"files": 14, "checks": 118}`, all checks passed, the same counts as
  before the change.
- `ast.parse` on all 61 `studio/*.py`: none fail, which confirms nothing there was disturbed.
- Live page on port 8798: all fourteen plug-ins register, `#toolsec` mounts both cards with no duplicates,
  both cards show real data, no console errors.
