# mood — pick a meme noise or a music bed for a clip

**Slug:** `mood` · **File owned:** `web/feat/mood.js` (one file, nothing else edited)
**Skill loaded:** `ui-design-guide`

## What I built

The server could already make nine meme noises and four music beds and it listed them at
`GET /api/moods`, but the clip dialog had nowhere to choose one. So a person could not make the
choice at all. This adds exactly one labelled row to the clip dialog:

- **Where it sits:** at the end of the main fields, right after Start / End and right before the
  `<h3>Post text</h3>` heading. That is the natural end of the "On the video" block, before the
  post-text and the later word/language/look sections.
- **What it is:** a plain `<label class="f">Sound<select data-f="mood">`, which is the same shape
  as every other field in that dialog, plus a quiet line under it that says what the picked sound
  is like.
- **The options:** an empty first option "No sound", then `<optgroup label="Meme noises">` with the
  nine noises and `<optgroup label="Music beds">` with the four beds, in the order the server sends.
  An entry whose audio is not on disk yet keeps its name and gains " (not built yet)" and stays
  selectable, because the pick should still be recordable before the file exists.
- **Preselection:** the clip's own `mood`, when the clip has one. The clip is read from the page's
  state (`PeakCut.state()` plus the page's own `D.jid` / `D.cid`), not scraped out of the DOM.
- **The note under the select** repeats the server's own `note` for the chosen row, so the choice
  is explained in the server's words ("slow and warm: a talk, a story, a drive"), and adds
  "Not built yet." when the file is missing. "No sound" reads "No sound. The clip keeps its own
  audio."

## How the value gets saved

Nothing new was invented. `data-f="mood"` is the page's own collector for "re-make this clip"
values, at `web/index.html:3136-3141`:

```js
const body = {};
$$("#clipdlg [data-f]").forEach(i => {
  body[i.dataset.f] = i.type === "checkbox" ? i.checked : i.type === "number" ? Number(i.value) : i.value;
});
await send(`/api/jobs/${D.jid}/clips/${D.cid}/render`, body);
```

A bare `<select>` is accepted: its `.type` is the string `"select"`, which is neither `"checkbox"`
nor `"number"`, so it falls through to `i.value`. **No hidden input was needed.** I checked this
in the live page by running the collector's exact body verbatim and reading what it produced:

```json
{"hook":"He did not see that","captions":true,"style":"bounce","layout":"blur",
 "start":2,"end":8,"mood":"chill","title":"Test","description":"Test clip"}
```

The `mood` key is there, riding the existing save path, with no second request and no second copy
of the clip body.

## The re-draw guard

The hook fires on every repaint of `#clipdlg`, so the file is written to be cheap and safe to call
again:

- Closed dialog or no `.panel` yet: return immediately, draw nothing.
- My row already inside the dialog: **update it in place**, never add a second one. The option list
  is only rebuilt while it is still unfilled, so a dropdown that is open under the person's cursor
  is never yanked out from under them and the pick cannot silently move to the other group when a
  name exists as both a noise and a bed (`hype` and `funny` do).
- The sound list is fetched once and reused for every clip; a failure is quiet (the row shows
  "The sound list could not be read. The clip can still be re-made.") with no toast, no retry loop
  and no thrown error.

One thing I had to work around, which other feature owners should know about: `web/plugins.js`
keys its paint cache on `hookName + ":" + el.innerHTML.length` (`web/plugins.js:69-80`). A feature
file that finishes loading after `#clipdlg` was already painted can therefore wait forever for a
change in length that never comes. I hit exactly this — the row was present on the `#clipdlg`
hook path but missing on a freshly loaded page. So `mood.js` also listens for the dialog's own
`toggle` event and does one catch-up draw when the file loads. This is one listener, added once,
doing the same small job the hook does; it does not depend on the page re-painting for me.

## Verification (commands and real output)

```
$ cd peakcut && node --check web/feat/mood.js && echo "JS OK"
JS OK

$ python -c "import httpx;print(httpx.get('http://127.0.0.1:8798/assets/feat').json())"
{'files': ['autopilot.js', 'filters.js', 'grid.js', 'heard.js', 'log.js', 'mood.js',
           'peek.js', 'pill.js', 'stage.js', 'stats.js', 'style-tiles.js']}

$ python -c "
import httpx
r = httpx.get('http://127.0.0.1:8798/api/moods')
print('status', r.status_code)
print(r.text[:300])
"
status 200
{"moods":[{"name":"embarrassing","kind":"meme","note":"freeze","ready":false},{"name":"fail","kind":"meme","note":"push-in","ready":false},{"name":"shock","kind":"meme","note":"push-in","ready":false},{"name":"hype","kind":"meme","note":"shake","ready":false},{"name":"win","kind":"meme","note":"push
```

13 rows: 9 meme noises, 4 music beds. The four beds are `ready: true`; all nine noises are
`ready: false` on this machine.

### In the live page (real browser, real clip `20261119-171742-d88fe196d1` / `c0`)

- `window.PeakCut._order` contains `mood`; `PeakCut.mood` exists; the `#pcss_mood` style tag is
  present.
- Exactly one `[data-mood-pick]` row, positioned after the Start / End block and before
  `<h3>Post text</h3>`. Screenshot confirms it looks like the page's native fields.
- One `[data-f="mood"]`, optgroups "Meme noises (9)" and "Music beds (4)", 14 options total:
  `["", "embarrassing (not built yet)", … "suspense (not built yet)", "hype", "chill", "tense", "funny"]`.
- Picking "chill" updated the note to "slow and warm: a talk, a story, a drive". Picking
  "awkward" (a not-ready row) updated it to "freeze Not built yet." — the not-ready row is
  selectable, as asked.
- The page's collector produced the body above, with `"mood":"chill"`.
- **Re-draw guard:** calling the hook 6 times in a row on the open dialog left exactly 1 row and
  1 select and kept the pick (`"awkward"`). Closing and re-opening the same clip on a freshly
  loaded page, four rounds, gave `{rows: 1, opts: 14}` every time.
- A closed, emptied dialog is left alone (the hook returns without drawing).
- **Preselection:** the server does not store a mood yet, so I put one on the clip in the page's
  state (`clips[0].mood = "tense"`) and re-opened the dialog. The select came up on `"tense"`
  with that option `selected`, and the note read the bed's own words. A mood the list does not
  know (`"gone-from-the-list"`) fell back to "No sound" rather than a blank field. The test value
  was removed afterwards.

## What I could not test

**The sound does not reach the rendered clip yet, and that is a backend gap, not a UI one.** I
traced it and am reporting it rather than working around it, because `studio/` is not my file:

- `studio/jobs.py` `request_render(jid, cid, changes)` (`:373-405`) builds `new = dict(clip)` and
  then copies only `hook`, `title`, `description`, `style`, `layout` (plus captions and
  start/end). A `mood` key arriving in the request body is dropped there, so it never lands on
  the clip.
- `studio/render.py` `render_clip(src, out_dir, name, clip, words, src_w, src_h, brand=None)`
  (`:360-361`) has no mood parameter and never calls the mixers.
- `studio/music.py` (`MOODS` for hype/chill/tense/funny, `bed_path`, `bed_loop`, `make_beds`,
  `apply` with a sidechain duck at TARGET_LUFS -14.0) and `studio/meme.py` (the nine noises) are
  both finished and waiting to be called.

So the choice can now be made and it rides the save path correctly, but a backend owner must wire
`mood` through `request_render` → the clip dict → `render_clip` → `music.apply` / `meme.apply`
before anyone hears it. Until then the row is honest about it: a clip that has no mood keeps the
dialog on "No sound", and the note says "Not built yet." on the rows whose audio is missing.

I did not restart the server, did not run git, and did not edit any file other than
`web/feat/mood.js` and this report.

## Reviewer notes

- The one row is a plain `<select>` with the page's own `class="f"` label, so it inherits the
  existing field styling and focus ring. The only CSS I register (`#pcss_mood`) is a small grid
  and the muted note line; there are no colours of my own beyond the existing `--dim`, no shadows,
  and no motion.
- Comments and user-facing words are in plain language for people who do not program, per
  `AGENTS.md`.
- The catch-up draw described above is worth knowing about if another feature's row also goes
  missing on a freshly loaded page: the page's paint cache is keyed on markup length, so a
  late-loading feature has to arm itself.
