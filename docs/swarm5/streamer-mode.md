# Streamer clipping

One new file: `web/feat/streamer-mode.js`. No other file was touched. It registers one menu page
(`/app/streamer`, nav "Streamer clipping", icon `video`, group "Make", order 37) and one plug-in
(`streamer-mode`) that owns every click handler, because `web/plugins.js` only looks for `[data-act]`
handlers on objects registered with `add()`.

## What the page is

The Live page answers "who is on air". This page is the desk where the clipping actually happens, so it is
built around one rule: every box on the form either belongs to a route that exists, or it says in plain words
which part of PeakCut ignores it.

- A hero strip of four big cards: Clip a live stream, Watch for a spike, Catch the whole stream, GTA 6 mode.
  Each card carries a one-line explanation, and picking a mode refills the form below with that mode's own
  starting numbers and its own short reasoning under each field.
- The clip form, which changes with the mode.
- A summary line in GTA 6 mode that reads `6 clips, 12 to 45 seconds, Beast captions, intro skipped` and is
  redrawn as the fields change.
- A "Recording now" block: every job in `PeakCut.state().jobs` whose `kind` is `live`, with its id, title,
  stage and progress, a "Clip the last 30 seconds" button and a "Stop recording" button. The list is re-read
  from `PeakCut.state()` on every repaint (every 2.5 seconds while the page is open) and never cached. The
  last built HTML is kept only to skip an identical rewrite, so the DOM does not flicker under a click.
- Below it, a creator picker and "Start recording", which is the real way to record a stream.

## Where each field goes

| Field | Sent as | Route |
|---|---|---|
| Stream or video link | `url` | `POST /api/jobs` |
| How many clips | `options.max_clips` (1 to 20) | `POST /api/jobs` |
| Shortest clip | `options.min_len` (5 to 120 seconds) | `POST /api/jobs` |
| Longest clip | `options.max_len` (10 to 180 seconds) | `POST /api/jobs` |
| Caption look | `options.style` (a key of `PeakCut.state().status.styles`) | `POST /api/jobs` |
| Captions | `options.captions` (true or false) | `POST /api/jobs` |
| Skip the intro | `options.range_start = 8` | `POST /api/jobs` |
| Link check before posting | `?url=` | `GET /api/preview` |
| Caption look list, if state is empty | none | `GET /api/status` |
| Start recording | `{channel}` | `POST /api/creators/{cid}/live` |
| Clip the last 30 seconds | `{seconds: 30}` | `POST /api/live/{jid}/clip` |
| Stop recording | none | `POST /api/live/{jid}/stop` |

`POST /api/jobs` is `create_from_link` in `studio/server.py`. It reads exactly `url`, `options` and
`creator`, then hands `options` to `jobs.clean_options`, which drops every key it does not know without a
word. So the page sends only the six keys above and never invents a seventh.

## What is shown but deliberately not sent

| Field | Why it cannot be sent | What the page says |
|---|---|---|
| How loud chat must get (Quiet / Normal / Busy) | A spike is decided by `studio/chat.py` (`RATIO = 3.0`, `MIN_PEOPLE = 15`) and by the creator's "only check on a spike" setting. There is no per-job threshold. | The hint under the select names the Chat settings and the creator setting, and says the box is not sent. |
| Keep recording for at most N minutes | Recording length is `buffer_min` on the creator (`studio/creators.py`), not a job option. | The hint names the creator's Setup page. |
| Hook words to listen for | Hook words come from the saved brand document, not from one job (`jobs._hook_words`). | The hint names the Brand page. The words stay editable so the mode reads as GTA 6, and no request is made with them. |
| Prefer moments with a police chase, a crash or a wanted level | There is no such field. `options.moment_labels` only writes a label on a clip after it is made (`studio/moments.py`); it labels, it does not choose. | The hint says it is a note, not a filter, that it is not sent, and that labelling is not choosing. |

The GTA 6 word list had to be written here: `docs/research/` holds no Grand Theft Auto file, and the only
GTA note in the repo (`docs/GTA6-PORT-BRIEF.md`) names moment types and vision banners but no hook words.
The defaults are `wanted level, police chase, crash, heist, WASTED, BUSTED`.

## The one honest limit on live links

`POST /api/jobs` downloads a finished video. In `studio/jobs.py` the url branch probes the link with
`media.info` and raises "This link is a live stream, so it would never finish downloading" when the link is
on air. So the page checks `GET /api/preview` first and, when the link is live, says so instead of making a
job that is certain to fail, and points at Start recording, which uses the real live route. The preview check
is best effort: if it cannot answer, the job is posted and the route has the final word.

## Copy and house rules

Every id starts with `str_`. Every interpolated string goes through the file's own `esc()`. Plain English, no
em dashes, no exclamation marks, no shadows, hover changes colour only, palette untouched. Every fetch sits
in try/catch and writes a sentence from the route, or a plain fallback, into an `.err` box on the page.

## Verification

- `node --check web/feat/streamer-mode.js` prints PARSE_OK.
- `python tests/test_feat_files.py` prints `{"files": 69, "checks": 558}` then `All checks passed.`
