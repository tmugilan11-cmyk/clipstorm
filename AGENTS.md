# Working on PeakCut

A short map for contributors and AI coding assistants.

## Installing or updating PeakCut for someone

**Before installing, ask the person where to put it**, and suggest a short, permanent folder: `C:\peakcut` on
Windows, `~/peakcut` on a Mac or Linux. Do not just clone into the folder you happen to be running in: AI assistants
often run in a temporary, scratch or session workspace, which gets deleted, and whose path is long enough that
Windows cannot load the speech library (Windows can't open files whose full path is over 260 characters; the error
is "DLL load failed ... The filename or extension is too long"). Tell the person where you put it.

**When updating**, look at where PeakCut is first. If its folder path is long (roughly over 100 characters) or inside
a temporary or assistant workspace, ask the person whether to move it to `C:\peakcut` (or `~/peakcut`) as part of the
update. Moving is safe when done like this: clone the latest version into the new folder, copy over `.env`,
`storage.json` and the `data` folder if there is one (the videos and clips; `storage.json` may point to a data folder
elsewhere, which then stays where it is), install the requirements, start it from the new folder, check the clips
are there, and only then offer to delete the old folder. Never delete anything without asking.

## Run and test

- Run: `python -m studio.server` (settings from `.env`; see `.env.example`). Needs Python 3.10+ and `ffmpeg`.
- The speech model (about 480 MB) downloads by itself on first start; `python -m studio.fetch_model` gets it ahead of time.
- Tests: `python tests/run.py`. It starts a throwaway copy on a spare port with an empty data folder. Run it
  before and after any change to `studio/`. No keys needed.
- To try a risky change by hand without touching real data:
  `PEAKCUT_DATA=<temp folder> PEAKCUT_PORT=8766 python -m studio.server`.

## Where things are

| File | What it does |
|---|---|
| `studio/server.py` | Every web route, and the gate that runs before each request (who is asking, limits, headers) |
| `studio/config.py` | Every setting, read from environment variables |
| `studio/ai.py` | The only code that talks to an AI service, and the AI settings saved from the dashboard (`ai.json` in the data folder) |
| `studio/brain.py` | The prompts: finding clips, live judging, hooks and titles, caption fixes |
| `studio/usage.py` | The record of AI calls and tokens shown on the AI usage page |
| `studio/jobs.py` | The video pipeline and the fair queue |
| `studio/live.py` | Live recording and clipping |
| `studio/transcribe.py`, `studio/asr_worker.py` | Speech to text: on this machine, on a second machine, or sent to Logfare with a chosen model |
| `studio/posting.py` | The post queue, and the review gate (rejected clips never post) |
| `studio/zernio.py` | Posting and view numbers through Zernio: one key, sixteen platforms |
| `studio/render.py` | Cutting, layouts and captions (ffmpeg and Pillow) |
| `studio/media.py` | Downloading (yt-dlp), probing, audio |
| `studio/auth.py`, `studio/account.py`, `studio/admin.py` | Sign-in, deleting things, the admin dashboard |
| `studio/db.py` | Database tables (SQLAlchemy core; SQLite or PostgreSQL) |
| `web/index.html` | The whole signed-in app, one file, no build step |

## Rules worth knowing

- **Sign-in is off by default** (`config.ACCOUNTS`): every request then belongs to one built-in owner
  (`auth.local_user()`). With `PEAKCUT_ACCOUNTS=1` it is a normal multi-user site. Both paths are tested.
- **Who is asking** always comes from the session (`ctx.uid()`), never from the request body. Background threads
  set it themselves with `ctx.as_user(...)`.
- **Anything that changes what a user sees must call `ctx.bump()`**. The page polls `/api/sync`, which answers
  from memory when that user's counter has not moved.
- **Text from videos is untrusted**: it goes into prompts through `brain._safe` and out through `brain._text`.
- **Adding an AI provider**: add a row to `PROVIDERS` in `studio/ai.py`. If it speaks the OpenAI chat format that
  is all; otherwise add one function that returns `(parsed JSON, tokens in, tokens out)`.
- **The AI address is spoken to in one shape.** `studio/ai.py` `wire()` decides gemini/anthropic/openai: a
  service's own address keeps that service's shape, and anything a person types into the Address field is
  spoken to in the OpenAI chat format (that is what "OpenAI-compatible" means). `ai.where()` names the thing
  actually being talked to in errors, so a typed address shows up instead of a company the row came from.
  Checked by `tests/test_ai_address.py`.
- **A model is told one shape and one only.** `studio/ai.py` `_wrapped(prompt, schema)` adds the "answer with one
  object under `items`" sentence only when a schema is passed; a prompt that names its own object must not be
  contradicted, and the JSON word `null` is raised as an error rather than returned, because `None` reads to every
  caller as "the AI deliberately chose nothing". Checked by `tests/test_ai_address.py`.
- **Clips are rendered in a short temporary folder** and moved into place (`render.render_clip`): ffmpeg's caption
  step cannot open paths longer than 260 characters on Windows.
- **Secrets** are read from the environment or from files named by `*_FILE` settings. Never write a key, a real
  address or a personal path into a tracked file.
- **Pages** are plain HTML, CSS and JavaScript. Keep the existing palette, no shadows, and hover states that
  change colour only.
- **New pieces of the page go in `web/feat/<name>.js`**, not into `web/index.html`. Each file registers one plug-in
  through `web/plugins.js` (`PeakCut.add`), which gives it a Tools card, a `load`, `[data-act]` handlers, `after`
  hooks and `keys`. `web/feat/heard.js` is the file to copy; `docs/swarm3/CONTRACT.md` is the rule set, and
  `tests/test_feat_files.py` checks every file follows it (parses, one plug-in named after itself, escapes its
  markup, no id clashing with `index.html`, no absolute origin).
- **A clip's sound** is one word on the clip (`mood`), read by `jobs.request_render` and applied by `jobs._add_sound`
  after the picture is rendered: a meme noise from `studio/meme.py` first, a music bed from `studio/music.py` second,
  because `funny` and `hype` are both. A sound that cannot be applied leaves the file alone and does **not** write
  `mood` on the clip, so the page never shows a word about audio the clip does not carry.
- **A menu page is also a feature file.** `PeakCut.page("name", {nav, icon, tip, path, group, order, view, load})`
  puts a row in the main sidebar with its own address and its own draw. Never a link back to Settings: the page calls
  the same `drawSettingTab(tab, box)` that Settings uses, so one form serves both places and cannot drift.
  `tests/test_menu_pages.py` checks every registration (label, path, tip, group, real icon, no shared path).
- **A saved brand is the source of a clip's look, length, sound and hook words.** `jobs._brand_prefs` reads it on
  `create`, and only a value the person actually changed counts, so a brand nobody has touched adds nothing.
  `jobs._hook_words` feeds `brain._rules`, which is the one place the prompt is built.
- **Logfare is both the speech service and an AI provider.** `studio/ai.py` `_SHARED = {"logfare": _logfare_key}`
  means the key pasted under Transcription is found again under AI, so the person is never asked twice.
- **YouTube's analytics page is called Insights now.** The nav row says "Insights"; internal names stay "analytics".
- Comments and messages are written in plain language for people who do not program. Keep that tone.

**A caption look is a table row, and its font has two names.** `caption.STYLES[name]` is
`(file stem, family name, …)`: the stem is the `.ttf` copied into the render folder, the family is what libass
is told to draw with, and `FONT_FILES` is keyed by the family. Post captions do not belong in this table. The existing script fallback remains for real multilingual speech.
`tests/test_caption_looks.py` checks style names, fonts and implemented motion.

**A look's motion is one name in `ANIM`, and that name must be implemented.** `ANIM[name]` picks a kind; the kinds
that only change the word being said live in `NOW`, the ones that change the line live as branches in `build()`.
A name in `ANIM` with no branch and no `NOW` entry is not an error anywhere: the look silently falls back to a plain
word pop and two looks called "glow" did nothing a person could see until `NOW["glow"]` was added.
`tests/test_caption_looks.py` now fails when a name a look uses is implemented by neither.

**The AI is asked through `ai.call(model, prompt, schema, timeout)`, and a schema makes it slower.** Measured on
this install: the identical sound-placement prompt took 8.9 s with no schema and 38.3 s with one, and the long
version ran past the timeout so every press said "could not reach Logfare". Send no schema when the prompt already
names its object, and let the caller check the answer (`soundplan.cues()` does). `ai._parse` raises on a JSON `null`
rather than returning `None`, because `None` reads to a caller as "the AI deliberately chose nothing".

**An Instagram post caption is saved text, separate from video subtitles.** `studio/igcaption.py` accepts
manual Unicode text or an optional Japanese/Chinese AI draft. The complete caption is saved on the clip and sent
verbatim by both native Instagram publishing and the Zernio Instagram branch. Do not add fonts, colors, animation,
artificial karaoke line breaks or unsupported popularity rankings to post descriptions. `captions.POST_ONLY_STYLES`
lists removed video styles only for migration, never for selection. Tests: `tests/test_igcaption.py` and
`tests/test_post_caption.py`. See `docs/IGCAPTION.md`.

**A box a person types into shows the result before they commit.** Two controls were blind and cost a full render to
check: the clip editor's "Big text" (the heading) and the Text tab's title and description. `studio/api_heading.py`
draws one real frame of the clip - its own video, its own look, its own brand - with the heading on it, and
`web/feat/live-heading.js` puts that picture under the box and assembles the post as it will be written. The frame is
cached per (clip, words) so typing does not redraw the same words; a hidden Look tab spends nothing.
`tests/test_live_heading.py` checks the two things that made this wrong the first time: the caption file needs its own
clock with the input seeked (otherwise the heading lands on a different second), and the page's paint hook is handed
`#clipdlg` itself rather than a parent to search inside (getting that wrong fails silently and the hook just returns).

**Quiet text has to be lighter than body text on a dark page.** `--faint` is the one quiet grey, and
`web/feat/polish-contrast.js` sets it for the whole app (`#main, dialog`). That sheet was written when the page was
white and it forced `#75695F`, which is 3.72:1 on the page's black and fails every `.hint`. It now sets `#A0948C`, the
palette's own warm grey: 7.24 on `--bg`, 6.86 on `--muted`, 5.68 on `--brand-soft`. Every number is in that file's
header. Change a colour by measuring it, not by looking at it; `tests/test_text_ink.py` fails if dark ink comes back onto
the page colour, and it follows the parent rule so ink on the brand colour is judged against the orange.
`docs/TEXT-PASS.md` records the sweep behind this: every page, 0 low-contrast nodes, 0 clipped-text nodes.

**A number on the page has to come from somewhere.** `web/feat/audio-page.js` printed `0.0s` under every catalogue
sound because `/api/memesounds/trending` sends no duration and the formatter fell back to zero. A zero is a claim - "this
sound is empty" - not a blank. Draw the value only when the response carried one, and say why in a comment; a row with
no length shows a globe instead, which is true: it is in the catalogue and not on this machine yet.

**A live recording is fetched fragment by fragment, and its clock is its own sound.** `studio/live.py` resolves the
stream once (`resolve`, with the bot-check retries) and then records one of two ways. YouTube keeps every two-second
fragment of a live stream and hands any of them over by number (`sq=N`), which is the only way back to the first
minute: the live playlist lists the last fifteen minutes and `ffmpeg -live_start_index 0` can reach no further. So
`_fragments` downloads the fragments itself, several pieces ahead, and `_mux` joins a few seconds of picture and sound
into one `.ts` piece with a short ffmpeg that exits (`-copyts`, nothing reset, so pieces join end to end). Anything
that cannot be walked that way goes to `_direct`: one ffmpeg on the resolved address, never a pipe from another
program. Things that broke earlier designs and must not come back: a `yt-dlp | ffmpeg` pipe (the merged pipe carries
no sound, and two extractions of one URL kill each other); a second long-lived connection for the sound (it starved,
and the card sat on "Connecting"); `-reset_timestamps` (the sound drifts at every join). The words are heard in the
finished pieces themselves (`_commit` reads each piece's sound), so the transcript, the loudness and the clip are the
same file and cannot drift; a stretch with nobody talking is an answer (`transcribe(..., quiet_ok=True)`), not a
failure to retry. While a running stream is caught up on, the listening takes long stretches three at a time, waits
for the AI rather than run past it, and "clips this hour" is counted on the stream's clock. A restart carries on from
`frag_done`; the pieces of a recording that was cut short are swept at start-up. Checked by
`tests/test_live_from_start.py`.

**A webcam with no border is found by its stillness.** `facecam._drift` walks in from each side of the frame for as
long as the picture stays still, then measures again inside that strip. It needs a moving game round it (`CALM_OUT`),
so a camera that fills the frame is not taken for a webcam on a game. `render._filter`'s `stack` branch slides the
game panel sideways away from a webcam that sits half-way down a side. Checked by `tests/test_facecam_calm.py`.

**The judge is three scouts and two critics, and a score comes from the critics' marks.** `studio/judge.py` `pick()`
is the one place a moment is chosen, for a finished video (`brain.find_clips`) and for a live stream
(`live._ai_check`). One scout follows the talk, one starts from the reactions (the `(LOUD)`, `(CHAT)` and
`(PAUSE n)` marks) and works backwards, one hunts for the line people will quote. Two critics who never see each
other's answer (an editor, and a viewer who swipes fast) then see each find with the lines around it and the
loudness through it, mark hook, payoff, emotion, share and standalone, may move the cut, and say post or skip.
`together()` averages them (one generous answer cannot make a clip) and `final_score` turns the marks into the
clip's score; a "skip" can never score past `SKIP_CAP`, so 80 means the same thing on every clip. The taste
(`TASTE`) was written from `docs/research/viral-clips.md`: trolling, someone caught off guard, shock and rage
first; calm explaining is never a clip, however clean the sentences. A video makes fewer clips rather than weak
ones (`brain.MIN_SCORE`, the best one is still kept when it is decent). `studio/trends.py` reads two public feeds
once a day so the judge recognises a reference; it is a hint, never a requirement. Measured on the owner's stream:
the stretch where the old judge kept "I DON'T KNOW WHAT'S GOING ON" (now 33-59) gave "CHAT LIED TO SPEED" (90-96).
Checked by `tests/test_judge.py`.

**A clip's type is drawn onto the finished file.** `formats.plan()` works out the tag, bar, blur and flash;
`studio/format_finish.py` draws them, called from `jobs.render_one` right after `render_clip`. For a long time the
plan was made and never used, so all eight types rendered the same clip. Moment, Wait for it and Reveal (needs a
webcam, uses the stack layout) are real; the four that join several moments and Chat are marked `available: false`
with a reason rather than offered. In the stack and gameplay layouts the tag moves above the heading
(`jobs.render_one`). Checked by `tests/test_formats_real.py`.

**A reader goes before the scouts, and the web is asked.** `judge.read_scene()` is the first of the six AI reads: the
transcript has no speaker labels, so it works out who is here, whose voice each part is, who "he" and "they" point
at, the beats of the stretch and what was referred to, and names up to three web searches. `studio/web.py` runs
them (`search`, a plain results page, kept three days) and fetches the most-watched real clips of the same streamer
through YouTube's own search (`top_clips`, titles with view counts, kept a week); both go into every scout's and
critic's prompt as context and taste, marked as data. `PEAKCUT_JUDGE_WEB=0` turns the web off, and the tests set
it. A creator's "What should it look for?" (`clip_focus`) is passed to `judge.pick(focus=...)` in the person's own
words. Instagram is not read: it offers nothing without a sign-in. Checked by `tests/test_judge.py`.

**The app is shown as Clipstorm; the code still says PeakCut.** Only words a person reads were renamed (titles,
headings, help, the files in `web/brand/`). `window.PeakCut`, `PEAKCUT_*` settings, storage keys and module names
are unchanged on purpose. Logo addresses carry `?v=3` because the brand route is cached hard.

**Quality.** Downloads and live pieces go up to 1080p (H.264 + AAC preferred); clips are encoded at x264 `crf 18`
`fast` (Quick Sync `global_quality 19`), 192k sound, lanczos scaling; the later passes that re-encode a finished
clip (pictures, clip type) use `crf 17`. In the stacked layout the top panel is centred on the person
(`facecam.person_center`), not on the middle of the webcam box.

**One Audio page, and sound editing starts from a clip.** The sidebar has one audio row (the `sounds` page: sound
library + music). "Edit audio" is the button in the clip editor's Sound tab; the audio editor has no sidebar row and
shows a pointer to My videos when opened without a clip. Pictures are put on a clip from the editor's Look tab.

**A finished YouTube video brings its audience with it.** `studio/signals.py` reads YouTube's own "most replayed"
graph, the timestamped comments and the chapters through yt-dlp (no key), keeps them a day, and `jobs.py` hands the
judge the part that falls inside each block (`brain.find_clips(context_for=...)` -> `judge.pick(context=...)`). It
is evidence of what landed, never a rule. Live streams have no such data. Checked by `tests/test_signals.py`.

**Installing on a new Windows PC is two double-clicks.** `setup.bat` runs `setup.ps1`: Python 3.12 and ffmpeg through
winget when missing, a private `.venv`, the libraries one by one if the whole list will not install, `.env` from
the example. `start.bat` starts the server on port 8765 and opens the page. The repository is
`tmugilan11-cmyk/clipstorm` (private); `data/`, `.env`, `.pctest/` and the bulky reference material under
`docs/research/` are never published (`.gitignore`).

**One recording makes at most `MAX_LIVE_CLIPS` (100) by itself**, however high "clips per hour" is set.

**What the first whole-stream run taught (2026-11-23, 5 h 45 min, 47 clips).** Three things were wrong and are fixed.
Ten clips failed with "no longer in the buffer": while a stream is caught up on, clips are chosen far faster than
they render, so `live._scan_segments` now keeps the pieces of every clip still waiting (`queued`/`rendering` with
no `src`). All 37 finished clips came out without the streamer: the webcam was looked for once, in the first clip,
which was the full-screen intro; `live._webcam_for` now checks every clip, confirming the usual place against that
clip's own picture with `facecam.still_there` (a border strength of 6-100 with the webcam, about 1 without) and
searching afresh only when it is not there. And choosing "Facecam on top" in the editor did nothing for a clip with
no saved webcam box: `jobs.render_one` now finds the webcam in the clip's own video (`_webcam_in`) and writes
`layout_note` when there is none. A live clip whose pieces are gone is re-made from the stream's replay once the
stream is over (`jobs._piece_again`): the replay's clock was measured against the recording's at three points and
was within 0.03 s.

**"Chat" is heard as "chad", so the transcript is put right as it arrives.** `transcribe.transcribe()` runs
`fix_words` on whatever engine heard it: a table from `PEAKCUT_WORD_FIXES` (built in: `chad=chat`; add more as
`heard=meant, ...`). Timings are untouched, capitals and "'s" keep their shape, "giga chad" is left alone. On the
first whole-stream run the engine wrote "chad" 268 times and "chat" 92 times, and the judge then titled clips
about "his friend Chad". Checked by `tests/test_word_fixes.py`.

**Picture and sound are cut on one clock, never by `-ss` before a .ts input.** On an MPEG-TS source (every live
clip) `ffmpeg -ss X -i piece.ts` lands after X, the picture waits for the next keyframe (two seconds apart on a
YouTube stream) and the sound does not: the finished clip had the streamer's voice up to two seconds before his lips
(clip003 of the first whole-stream run: picture 23.23 s, sound 25.00 s, picture 1.77 s late). `render._render_in`
now opens the input `PREROLL` (12 s) early and cuts both tracks with `render._trim` at the same timestamp, renumbered
by that fixed amount (never `PTS-STARTPTS`, which hid the gap). The finished file is measured (`render.av_gap`); a
gap over 0.15 s re-renders from the very start of the source. Measured after the fix on the real clip003 source: the
first frame matches the source frame at the asked time, the sound is within 7 ms (the stream's own offset). Any new
code that cuts video must do the same. Checked by `tests/test_av_sync.py`.

**Clips are listed best first.** `byScore` in `web/index.html` (also `window.PeakCut.byScore`) orders every clip
list by score, highest at the top; the live page and the review queue use the same order.

**The accent is violet.** Every orange in `web/` was turned into a violet of the same brightness (same WCAG
luminance, so every measured contrast ratio in the comments still holds): `--brand #AF9BFF`, `--brand-deep #C8BAFF`,
`--brand-soft #20183F`. Warning amber, Google and Instagram colours were left alone. Logo addresses carry `?v=4`.

**The judge learns from the owner's own results.** `studio/own_results.py` joins every posted clip
(`posting._mine()`) to its clip record (hook, title, kind, rubric marks, length, judge score, layout) and its
numbers: views, likes, comments from YouTube when connected (`ytstats.bulk`: Data API counts, Analytics average
watched, and the 3-second hold from the retention curve for the newest 20), from Zernio for posts that went through
it, else the views PeakCut already tracks. The pass is cached in `users/<uid>/own_results.json`, run at most every
6 h (Refresh still waits 5 min) and never inside a render; a failed pass keeps the old numbers.
`own_results.taste_lines(creator=None, n=12)` reads the cache only and never raises: "Did well / Did badly" against
the channel's own median (per platform once it has 3+ clips) plus a judge-score-versus-reality line; clips under 2
days old are listed but never judged, and with fewer than 3 measured clips it returns []. `studio/api_own_results.py`
serves the "What worked" page (`web/feat/own-results.js`) with the step-by-step "Connect your YouTube channel" guide.
`accounts.youtube_status()` records the scopes Google granted and reports a retired refresh token (Google ends it
after 7 days while the app is in Testing). Checked by `tests/test_own_results.py`.

**A montage joins several moments of one video, and every part is cut like any other clip.** `studio/montage.py`
`choose()` takes the ticked clips or the best-scoring non-overlapping ones (a Compilation plays worst to best, the
other types in time order); `fit()` shortens each moment from its start until the whole fits the creator's `max_len`
(never under `formats.MIN_PART`); `make()` renders each moment with `render.render_clip` and joins the finished parts
with a numbered card, a whoosh and a flash. It never cuts a source with its own `-ss`: each part is trimmed to the
shorter of its picture and sound before joining, and the file is refused if `render.av_gap` is 0.06 s or more. A
moment's picture comes from the clip's `src`, else `source_path`, else (live recording over) a fresh
`download_section(exact=True)` into the montage's own work folder; a clip is never changed. Routes in
`studio/api_montage.py`, page in `web/feat/montage.js` ("Montages"), records in `montages.json` and `montage/` in the
video's folder (a montage is not a clip and is not in the post queue). Chat only counts messages and never keeps their
words, so the Chat type shows up to five lines the person types. Checked by `tests/test_montage.py` (includes a
beep-on-the-frame sync check).

**The structure follows OpusClip** (`docs/research/opusclip-structure.md`, every saved help page read, gaps ranked).
The submit box has "What to look for" (saved on the chosen creator as `clip_focus`), length buttons, clip kind and
saved setups; every video has its own page at `/app/videos/<id>` with sort, score/length/kind/decision filters, a
grid/list switch, letter grades from the judge's marks, Keep/Skip and bulk Post (`web/feat/project-tools.js`); the
clip editor is three columns (live transcript, video, tab rail); `web/feat/calendar.js` is a real month calendar and
the old timers page is "Timers". Open-source ideas and skills found are in `docs/research/open-source-ideas.md`.

**The judge remembers the stream, reads the screen, and has a final desk.** `studio/judge_story.py` keeps a story
beside the judge: cast, running jokes, setups with their payoffs, beats. A finished video's story is read once in
parallel parts and joined (`build`, kept as `story.json` in the job's folder, so every stretch also knows what happens
later); a live recording moves it on with every regular check on a thread of its own (`advance`), keeps it short in
`job["story"]`, and carries it over a restart (`carried`). `judge.pick(story=...)` puts it in front of the reader,
scouts and critics. Critics see 75 s before a candidate (`BEFORE`) and may pull the start back to the setup a stranger
needs; a cut longer than `max_len` loses its front, never its payoff. `studio/judge_look.py` looks at the picture:
frames are cut from absolute paths, the AI is asked once whether it can see pictures (`data/judge_vision.json`; the
qwen model in use cannot: HTTP 503), and without vision the text on screen is read with Windows' own OCR, so game
subtitles show which lines are a game character's. `PEAKCUT_JUDGE_VISION=0` turns it off; the tests do. A third
critic, the clip-page admin, sees only contenders, writes the posted hook, and names a made clip it repeats (a repeat
counts only when `judge.same_story` finds two shared telling words). `studio/judge_show.py` compares a block's
finalists side by side: drops repeats, re-ranks, moves a score at most +6/-15, a skip stays under `SKIP_CAP`.
`own_results.taste_lines()` reaches scouts and critics. Measured in `docs/research/judge-v3-comparison.md`: 7 calls,
46k tokens, 41 s per 8-minute live check (old: 6, 27k, 32 s), plus one story read in parallel. Checked by
`tests/test_judge.py`.

**A meme sound is chosen by a team, from sounds that were researched.** `studio/sound_kb.py` keeps
`memesounds/knowledge.json` (myinstants' all-time and trending lists, the catalogue's trending lists, the classic names
in `SEEDS`, the owner's shelf) and researches it again after a week: each sound is looked up on its myinstants page,
Know Your Meme and YouTube (`studio/sound_web.py`; `studio/web.py`'s Bing search returns unrelated pages here), the AI
writes what it means, its `MOMENTS`, when not to use it, whether it has words and how popular it is, and each file is
measured for length, silent start (`lead`) and loudness. Files come only from the catalogue (dankmachine.com) into
`memesounds/kb/` and reach the shelf only when put on a clip (`sound_pick.keep_cues`). `studio/sound_pick.py`
`choose()` works like the judge: a reader finds beats hung on a real word, myinstants is searched for this clip, three
pickers propose, every proposal is placed for real (`place`: the hit on the beat, a talking sound never over the next
line), two critics judge it, and a sound designer keeps at most `most_for(seconds)` sounds; none is a valid answer.
`memesound.mix` ducks any sound longer than 1.5 s under the voice and ends the file with the picture.
`PEAKCUT_SOUND_WEB=0` and `PEAKCUT_SOUND_VISION=0` turn off the web and the frames. The old picker (a mood word, then
the catalogue's first row) is kept in `soundplan.py` for comparison: `docs/research/meme-sound-v2.md`. Checked by
`tests/test_sound_kb.py` and `tests/test_sound_pick.py`.

**0 clips means all of them.** "How many" (`max_clips`) accepts 0 to 100; 0 makes `jobs._run_job` judge every block
and keep every strong find up to `jobs.ALL_CLIPS` (100, the same cap as one live recording). A creator's "Most live
clips per hour" of 0 removes the hourly limit; `live.MAX_LIVE_CLIPS` still stops one recording at 100. The score bar
(`min_score`) still applies, so "all" means all the good ones. Checked by `tests/test_all_clips.py`.
