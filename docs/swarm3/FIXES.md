# What the fixer changed

One line per finding from `docs/swarm3/REVIEW.md`, with the disposition and the reason.

## Important

- **I1: the sound picker never reaches a render.** Not reached. `studio/jobs.py:373 request_render` has no
  `mood` key and `studio/render.py:360 render_clip` has no audio step, so wiring it is a new back-end
  feature and this job must not add features. Its owner recorded the gap in `docs/swarm3/mood.md`.
- **I2: error text from the loader went into the page unescaped.** Fixed in `web/plugins.js:112`. Reason:
  the contract forbids building markup from an unescaped value, and this is the line every card passes
  through. Proved with a payload in the running page: a card that throws `<img src=x onerror=alert(1)>` now
  shows that text and the raw tag never appears.
- **I3: a card whose `load()` failed vanished without a word.** Fixed in `web/plugins.js:123`. Reason: the
  contract asks for a soft failure with one quiet line, never silence, so it now shows one toast and one
  console warning and keeps going with the other cards.

## Rejected

- **The two `#toolsec` watchers race and can duplicate a card.** Rejected, no code changed. Reason: their
  guards are mutually exclusive, `grid.js:143` writes only into an empty mount and `autopilot.js:324`
  returns as soon as its own card is present, so neither can overwrite the other. Checked live with a cold
  Tools tab: exactly two cards, one of each, no duplicates.
- **`day.js:141` has a mangled address regex.** Rejected, no code changed. Reason: the bytes are
  `^https?:\/\/`, backslash-slash twice plus the closing slash and `i`, which is a correct regex; the
  doubled backslashes were an artefact of how `grep` printed the line.
- **A feature file calls `/api/posts`, which does not exist.** Rejected, no code changed. Reason: no file
  in `web/feat/` mentions that address, so there is no caller to repoint at `/api/overview`.

## Minor, recorded and deliberately not fixed

- `web/plugins.js:84` watches `#cbody` under the name `drawCreator`, but the page function is
  `drawCreatorForm` (`web/index.html:1937`). Dormant: no feature file registers that hook, and guessing a
  name would be worse than leaving it.
- The paint cache at `web/plugins.js:72` keys on `innerHTML.length`, so a same-length repaint is skipped.
  `mood.js`, `stats.js` and `day.js` each add their own listener to cover that. Recorded, not reworked:
  every file is correct on its own.
- `filters.js` counts every 800 ms and `pill.js` repaints every 1200 ms. Both write only on a real change,
  so they are cheap enough to leave alone.

## Files touched

- `web/plugins.js`: two small edits, both described above.
- `docs/swarm3/REVIEW.md`: written by me, because the reviewer slot never produced one.

Not touched: any `web/feat/*.js`, `web/index.html` (still 3214 lines), and every file under `studio/`.

## Checks run after the change

- `node --check web/plugins.js` and all fourteen `web/feat/*.js`: all parse.
- `python tests/test_feat_files.py`: `{"files": 14, "checks": 118}`, all checks passed, the same counts as
  before my edits.
- `ast.parse` on all 61 `studio/*.py`: none fail, confirming nothing there was disturbed.
- Live page on port 8798, not restarted: all fourteen plug-ins register, both Tools cards mount with no
  duplicates and show real data, and the console has no errors.
