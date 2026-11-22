# audio-page: a wide page for the meme sound track of one clip

One new file: `web/feat/audio-page.js` (1112 lines). No other file was edited. It registers one menu page
(`/app/audio`, nav "Audio", icon `music`, group "Make", order 36) and one plug-in (`audio-page`) that owns
every click handler, because `web/plugins.js` only looks for `[data-act]` handlers on objects registered with
`add()`. Handlers declared inside a `page()` definition are silently dead: `plugins.js` walks `P._order`, and
only `add()` fills it.

**File owned:** `peakcut/web/feat/audio-page.js`. No other file was edited.
**Skill loaded:** frontend-design.

## What I built

The timeline that used to live in the clip dialog is now the whole page, and it is wide. The idea is that the
track is the subject, so everything else is arranged around it: the clip picker and the category bar above,
the track across the full width, the video preview under it, the shelf under that, and a column of every cue
on the right so the numbers stay visible while the chips are dragged.

- **Clip picker.** One `<select id="aud_pick">` built from `PeakCut.state().jobs` on load. It never fetches a
  list. Every job is walked, every `clip.status === "done"` becomes an option, and the label reads
  `speech_video.mp4 · clip01 · 7.0s` (`source.name`, clip id, `end - start`). Choosing an option calls
  `GET /api/jobs/{jid}/clips/{cid}/sounds` and redraws. If `PeakCut.state()` is not ready yet, the picker says
  so in a sentence instead of standing empty.
- **Category bar.** Eleven coloured chips, uppercase, in one rounded row: Trending, Reaction, Funny, Fail,
  Hype, Shock, Awkward, Win, Suspense, Cringe, Mine. Trending reads `/api/memesounds/trending`, the moods read
  `/api/memesounds/for?situation=<mood>`, and Mine filters the shelf to the sounds `library` reports as kept.
  Each chip carries its own colour through a `--c` custom property, taken from the darker end of the palette so
  the white label still clears 4.5:1. The chip for the current category stays pressed.
- **Filter row.** A text input and a max-length `<select>` (Any / Under 2s / Under 5s / Under 10s). Both work
  on `A.rows`, the list already in memory, and neither touches the network. "Under 2s" is strict: a sound of
  exactly 2.0 s is longer than "under 2s", so it is hidden. The count next to the row follows the filter.
- **The track.** Full width, dark, on `#17130F`. A ruler with a tick every second (every fifth second is
  labelled, and the step widens to 5 s and 10 s for long clips), a lane the height of the clip, and one
  orange chip per cue showing its start time and its title. Chips snap to 0.05 s while dragged. A chip is
  never rebuilt mid-gesture: pointerdown stores `{i, grab, chip}` and pointermove only writes `chip.style.left`
  and the chip's own label, so the element cannot be detached under the pointer. A click selects, Delete or
  Backspace removes the selected chip and says so. A 2 px caret follows the preview video.
- **The column.** Every cue in order: title, `starts 0:01.7 · vol 0 dB · plays to the end`, a Jump button and a
  Remove button. Above it, the summary line: `3 meme sounds · 0:01.7, 0:03.6, 0:04.9`. A cue that came back
  from the AI with a truthy `why` gets a small `AI` pill in the column and on its chip. Ordinary saved cues do
  not, because `memesound.tidy()` does not persist `why`: the pill marks what the AI just placed, which is
  exactly the case where the claim is true.
- **Preview.** `<video controls>` at `/media/{jid}/{file}?v={version}`. Jump seeks it, and Mix reloads it with
  a fresh `?mx=` stamp, so the mixed track can be heard without a page reload.
- **Buttons.** Ask the AI to place them (`POST .../sounds/suggest`, body `{}`), Save sounds (`PUT` the cues),
  Mix into the clip (`POST .../sounds/hear`), Upload a sound (a real `<input type="file">` posting `FormData`
  with field `file` to `/api/memesounds/upload`, then refreshing the shelf).
- **Search under the list.** A second box, deliberately below the shelf: it searches the whole catalogue with
  `GET /api/memesounds/search?q=`, and each result shows its title, its seconds and a Keep button.
- **The shelf.** What the category bar filters. Each row: Play, title, length, Add to clip, and Keep or Remove
  depending on whether the sound is already on this machine.

## Decisions worth naming

- **No number is ever invented.** Volume and stop-after come from the cue, or the row says "plays to the end".
  A catalogue row that does not report a length says "length unknown" rather than guessing 0 s. When the AI
  refuses, the page prints the route's own sentence in the note area, unchanged, because that sentence says
  what to do about it.
- **Every fetch fails with a sentence.** Each failing read writes into a named element: `#aud_catnote` for the
  category, `#aud_shelf` for the shelf, `#aud_results` for search, `#aud_note` for anything that changes the
  track, `#aud_ai` for the AI route. No box is ever left silently empty. `read()` and `write()` fall back to
  "PeakCut is still starting. Try again in a moment." when the helpers are not on `window` yet.
- **Ids cannot clash.** All 22 ids start with `aud_`, and every class starts with `aud-`. `tests/test_feat_files.py`
  checks the ids against `web/index.html`.
- **The page is forced wide.** `#main>.content:has(.aud-page){max-width:none}` beats the shell column. The
  `#main>` prefix is needed to outrank `polish-wide.js`'s `#main>.content{max-width:1480px}`.
- **The palette is the dark token set from `polish-dark.js`**: `#17130F` ground, `#221C17` ruler, `#342C25`
  rule, `#2A1A12` chip, `var(--brand)` border, `var(--brand-deep)` for the start time. Nothing hardcodes a
  colour the token set already names.
- **Reused from `meme-timeline.js`**, not copied blind: the waveform decode (`barsFor`, one shared
  `AudioContext`, 40 peaks, cached per slug) and `paintWave`, the chip width from a cue's `end` or the sound's
  length, the `pct()`/`clamp()` maths, the Delete/Backspace rule, and the upload `FormData` handshake.

## Exact names

Ids, all `aud_` prefixed: `aud_pick`, `aud_len`, `aud_cat`, `aud_catnote`, `aud_catcount`, `aud_tl`,
`aud_cliplabel`, `aud_where`, `aud_ruler`, `aud_lane`, `aud_caret`, `aud_note`, `aud_video`, `aud_vcap`,
`aud_shelf`, `aud_q`, `aud_max`, `aud_search`, `aud_results`, `aud_file`, `aud_sum`, `aud_cues`.

Data-act names, twelve: `aud-cat`, `aud-play`, `aud-add`, `aud-keep`, `aud-drop`, `aud-upload`, `aud-ask`,
`aud-save`, `aud-mix`, `aud-jump`, `aud-del`, `aud-search`. Keyboard removal lives in the plug-in's `keys(e)`,
not in an act.

Routes called: `GET /api/jobs/{jid}/clips/{cid}/sounds`, `PUT` on the same path, `POST .../sounds/suggest`,
`POST .../sounds/hear`, `GET /api/memesounds/trending`, `GET /api/memesounds/for?situation=`,
`GET /api/memesounds/library`, `POST /api/memesounds/keep`, `DELETE /api/memesounds/library/{slug}`,
`POST /api/memesounds/upload`, `GET /api/memesounds/search?q=`.

## What I verified

- `cd peakcut && node --check web/feat/audio-page.js` printed `CHECK_OK`.
- `cd peakcut && python tests/test_feat_files.py` printed `{"files": 70, "checks": 566}` and
  `All checks passed.`, with the audio-page block all ok: it parses, declares exactly one plug-in, that plug-in
  is named after the file, it owns the name, it does not write into `index.html`, it escapes what it draws, it
  uses no absolute origin, and it invents no clashing id.
- `cd peakcut && python tests/test_menu_pages.py` printed `All checks passed. 389 ok`, including
  `ok audio has an icon the page knows music`.
- Regex scan of the file: zero em or en dashes; every `id="` value starts with `aud_`; twelve data-act names;
  exactly one `P.add("audio-page")` and one `P.page("audio")`; the only places an exclamation glyph appears are
  `!==` comparisons and negated guards, never in a sentence the person reads.
- Live server at `http://127.0.0.1:8798` (already running, never restarted) serves `/app/audio` with 200.
  On the real page: the picker holds 4 options and the first reads `speech_video.mp4 · clip01 · 7.0s`; the bar
  has 11 chips with `trending` pressed; the note reads `3 meme sounds · 0:01.0, 0:03.6, 0:04.9`; the column
  lists Fart, Fart and Vine Boom (Longer) with Jump and Remove; the summary line matches; the video src is
  `/media/20261120-200119-5fdd2d8f89/clip01.mp4?v=5`; the ruler draws 8 ticks labelled 0:00 and 0:05; 3 chips
  sit in a 1592x84 lane; the max select offers Any length / Under 2s / Under 5s / Under 10s; the shelf draws
  10 rows with Play, Add to clip and Keep or Remove. No console errors.
- Filtering: typing `air` cut the shelf from 10 rows to 2 ("DJ Airhorn", "Air Horn") with no request;
  clearing restored 10. Category clicks: `funny` gave "Sounds for a funny moment. 5 sounds here." with 5 rows;
  `mine` gave the 3 kept sounds.
- Search: `boom` returned 12 results with Keep buttons.
- Drag: pointerdown plus three moves took a chip from `left:14.286%` to `17.143%`, `20%`, `24.286%` with the
  label going 0:01.2 → 0:01.4 → 0:01.7, and the summary line followed to `0:01.7`.
- Delete removed a chip (3 → 2) and wrote "Removed from the track. Press Save sounds to keep that."
- Jump on the third cue set `video.currentTime` to 4.9 and moved the caret to 70%.
- Save wrote the cues and the note read "Saved. The next re-make mixes these in."
- Failure paths, forced by stubbing the helpers: a rejected `PeakCut.api` made the category note and the shelf
  read "That list could not be read: The server is not answering right now."; a rejected `PeakCut.send` made
  Ask print the route's own sentence, "No AI is set up, so PeakCut cannot choose the sounds. Set one up under
  AI.", in the bad-tone note.
- AI pills: a stubbed suggest returning two cues with `why` rendered 2 `AI` pills in the column and 2 on the
  lane, and the second row read `starts 0:02.0 · vol +3 dB · stops after 1.0s`.

One thing outside this page: while I was working, this file was overwritten once by another process with a
different implementation that missed several of the brief's requirements (6 category chips instead of 11, no
video preview, no Jump, no `AI` pill, `pcaud_` id prefix). I rebuilt the file to the brief and the results
above are from that rebuilt version.
