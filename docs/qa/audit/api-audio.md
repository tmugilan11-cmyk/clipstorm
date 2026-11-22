# Audit: API audio area (meme-sound and sound-bed routes)

Auditor: agent-148, QA swarm audit wave. Skill loaded first: systematic-debugging.
Rules followed: docs/qa/CONTRACT.md (measured findings only, no browser, one owner per file).

## Files owned

- `studio/api_memesound.py` (415 lines) - every meme-sound route: search, for, trending, library, keep, upload, remove, play, and the per-clip sounds routes
- `studio/api_sound.py` (177 lines) - the sound-bed routes: moods, the WAV files, prime
- `studio/memesound.py` (630 lines) - the code behind those routes (catalogue, downloads, mixing, upload checks)
- `studio/soundplan.py` (271 lines) - the AI sound-placement prompt and the answer check

## Every check run

1. Read `docs/qa/CONTRACT.md`; loaded the `systematic-debugging` skill before starting.
2. Read all four owned files in full, plus the gate middleware (`studio/server.py:80-189`) and every frontend caller of these routes (`web/feat/audio-page.js`, `web/feat/audio-edit.js`, `web/feat/meme-timeline.js`, `web/feat/mood.js`, `web/feat/sounds.js`).
3. Routers: both files are registered on the app (`studio/server.py:251` api_sound, `:260` api_memesound). There is no global exception handler anywhere, so an unhandled exception answers as a plain-text Starlette 500 - which is why the suggest `float()` case below is flagged.
4. Live curl of every route against 127.0.0.1:8798 with realistic input, with invalid input, and with a real oversize file upload (see the critical finding). No route answered 500 and nothing crashed.
5. Upload test files were real WAVs built for the audit (valid 8 KB, 0 B, and 300 KB PCM, headers checked) and were removed from the shelf and from the workspace afterwards; the library was back to its original 4 sounds at the end.

## Findings

### Critical

**C1. The gate caps every upload at 256 KB, so the route's own 8 MB limit is unreachable.**
`studio/server.py:118-125` caps every non-GET body at `256 * 1024` unless the path is `/api/upload` (or a PUT under it): `cap = (...) * 1024 * 1024 if path == "/api/upload" or piece else 256 * 1024`. `POST /api/memesounds/upload` is not on that list, but `studio/memesound.py:290` sets `MAX_UPLOAD = 8 * 1024 * 1024` and `studio/api_memesound.py:176-177` checks against it - a check the request can never reach, because the gate refuses anything over 256 KB first with 413 "That request is too large."
Live proof: a valid 300,044-byte WAV (18.75 s of 8 kHz PCM, far inside 8 MB) → **413** "That request is too large."; the same file at 8,044 bytes → **200 ok**. Most real sound effects are bigger than 256 KB, so the upload control is broken for normal files, and the message never mentions the limit that actually applies. Fix: exempt `/api/memesounds/upload` from the small-body cap the way `/api/upload` is (the route already enforces its own 8 MB), or raise the cap for this path and say the real limit in the message.

### Important

**I1. Trending echoes a window it did not use.** `studio/api_memesound.py:119` echoes the raw `window` parameter into the response, while `studio/memesound.py:149-154` silently falls back to "24h" for anything it does not know. Live: `GET /api/memesounds/trending?window=bogus` → 200 with `"window":"bogus"` in the answer while the rows are the 24-hour set. The page then shows a label the data does not carry. Fix: echo the value `memesound.window()` actually returned (same pattern the rest of the file uses for cleaned input).

**I2. Keep answers 400 for a dead catalogue, the other routes answer 502.** `studio/api_memesound.py:149-150` maps `CatalogueDown` (a `RuntimeError`) to HTTP 400 on keep, while search/for/trending map the same failure to 502 (`:91-92`, `:106-107`, `:117-118`). Same failure, wrong status class on one route - a network problem is not something the person typed wrong. Fix: use the same 502 mapping keep uses for `RuntimeError` from the download.

**I3. Keep and upload block the event loop.** `studio/api_memesound.py:138-151` (`memesounds_keep`) and `:162-195` (`memesounds_upload`) are `async def` but call blocking work directly: the streaming download (`studio/memesound.py:266`, httpx timeout 60.0 s), ffprobe length (timeout 30 s, `:413-425`), and the store/probe path on upload. A slow catalogue download stalls every other request on this app for up to a minute. The suggest and hear handlers already do it right with `run_in_threadpool`. Fix: wrap the download/probe calls the same way.

### Minor

**M1. Stale docstring.** `studio/api_memesound.py:13` documents `POST /api/memesounds/play/{slug}`; the route (`:198`) is `GET`/`HEAD` only. The frontend plays with GET everywhere (`audio-page.js:416,470,504`, `audio-edit.js:556`, `meme-timeline.js:110`), so nothing breaks - the comment is just wrong.

**M2. Suggest parses `start` with a bare float.** `studio/api_memesound.py:295-296` does `start = float(clip.get("start") or 0.0)` without the try/except its own `_clip_len` uses (`:73-78`). A non-numeric `start` on a clip would answer a plain-text 500. Low risk today (clips are written by this app), but it is the one unguarded parse in the file.

## What held up well

- Error copy is plain-language and consistent everywhere: "That job is not here." (404), "That clip is not here." (404), "This clip has no meme sounds on it yet." (400), "Which sound?" (400), "The file arrived empty." (400), "The sound sad-violin-the-meme-one is not on this machine yet. Add it from the meme sounds page first." (400), "There is no music bed called hcill." (404), "Sounds are served as music or meme, not foo." (404).
- Empty states answer with a clear message instead of a blank list; removing a sound that is not on the shelf answers `ok:false` instead of an error.
- `PUT` on a clip's sounds with no cues answers 400 with the send-a-list message and never writes; an empty cue list answers 200 and leaves the version alone.
- Suggest returned a real AI cue (spongebob-fail-11236, `kept:false` with `need` naming the sound to download first), and the AI-failure paths cannot 500 - `soundplan.cues()` is fully defensive and a failed ask returns a why-sentence (`studio/soundplan.py:222-225`).
- Play answers `audio/mpeg` with private 5-minute caching for kept sounds and a clear 404 for ones not on this machine; HEAD carries the content length.
- The 0.0 s duration bug from AGENTS.md is already fixed on the page (a globe is drawn when the catalogue sends no length).
- Moods prime is idempotent (built 10 sounds + 4 beds, `errors:[]`) and every mood answered `ready:true`.
