# PROOF — PeakCut measure-and-report run

Measured, not asserted. Every command below was run on the live host against the real tree and the real
server on `127.0.0.1:8798`. Output is transcribed verbatim (whitespace trimmed only).

- Working tree: `peakcut/`
- Python: `Python 3.15.0`
- Node: `v24.22.2`
- Run date: 2026-11-20 (Asia/Calcutta)
- Note: `tests/run.py` was not used — this host's temp-dir trick fails. Every suite was executed directly, one at a time.

---

## Summary table

| # | Check | Command | Result | Verdict |
|---|-------|---------|--------|---------|
| 1 | Feature files exist | `ls web/feat/` | 15 files listed: `_example.js autopilot.js day.js filters.js grid.js heard.js history.js keys.js log.js mood.js peek.js pill.js stage.js stats.js style-tiles.js` | PASS |
| 2 | Every feature file syntax-checks | `for f in web/feat/*.js; do node --check "$f" && echo "OK $f" \|\| echo "FAIL $f"; done` | 15 × `OK`, 0 × `FAIL`, exit 0 | PASS |
| 3 | Health endpoint | `curl -s http://127.0.0.1:8798/healthz` | `{"ok":true}` | PASS |
| 4 | Feature manifest endpoint | `curl -s http://127.0.0.1:8798/assets/feat` | `{"files":["autopilot.js","day.js","filters.js","grid.js","heard.js","history.js","keys.js","log.js","mood.js","peek.js","pill.js","stage.js","stats.js","style-tiles.js"]}` — 14 files | PASS |
| 5 | Regression: overhaul | `python tests/test_overhaul.py` | 58 × `ok`; `skip translate.text (no engine installed)`, `skip translate.words (no engine installed)`; final line `All checks passed.`; exit 0 | PASS |
| 6 | Regression: transcribe × Logfare | `python tests/test_transcribe_logfare.py` | 27 × `ok`; final line `All checks passed.`; exit 0 | PASS |
| 7 | Regression: transcribe settings | `python tests/test_transcribe_settings.py` | 21 × `ok`; final line `All checks passed.`; exit 0 | PASS |
| 8 | Regression: review gate | `python tests/test_review_gate.py` | 10 × `ok`; final line `All checks passed.`; exit 0 | PASS |
| 9 | Regression: connect | `python tests/test_connect.py` | 38 × `PASS`; final line `ALL PASSED`; exit 0 | PASS |
| 10 | Regression: delete | `python tests/test_delete.py` | 17 × `PASS`; final line `ALL PASSED`; exit 0 | PASS |
| 11 | All studio modules parse | `python -c "import ast,glob; [ast.parse(open(f,encoding='utf-8').read()) for f in glob.glob('studio/*.py')]; print('all studio modules parse')"` | `all studio modules parse`; exit 0 | PASS |
| 12 | Every served feature file is retrievable | `httpx` sweep over `/assets/feat` + each `/assets/feat/<f>` | `14 feature files served`; 14 × `200`, sizes 3906–16725 bytes, 0 non-200 | PASS |

**Total: 12 of 12 checks passed. 0 failed.**

---

## Detail

### 1. Feature files present — `ls web/feat/`

```
_example.js
autopilot.js
day.js
filters.js
grid.js
heard.js
history.js
keys.js
log.js
mood.js
peek.js
pill.js
stage.js
stats.js
style-tiles.js
```

### 2. Syntax check — all 15 files

```
OK web/feat/_example.js
OK web/feat/autopilot.js
OK web/feat/day.js
OK web/feat/filters.js
OK web/feat/grid.js
OK web/feat/heard.js
OK web/feat/history.js
OK web/feat/keys.js
OK web/feat/log.js
OK web/feat/mood.js
OK web/feat/peek.js
OK web/feat/pill.js
OK web/feat/stage.js
OK web/feat/stats.js
OK web/feat/style-tiles.js
```

`node --check` is a parse-only gate: it proves no syntax error, not that the modules run.

### 3–4. Live endpoints

```
$ curl -s http://127.0.0.1:8798/healthz
{"ok":true}

$ curl -s http://127.0.0.1:8798/assets/feat
{"files":["autopilot.js","day.js","filters.js","grid.js","heard.js","history.js","keys.js","log.js","mood.js","peek.js","pill.js","stage.js","stats.js","style-tiles.js"]}
```

**15 files on disk vs 14 served — this is correct, not drift.** `studio/server.py:452-459` builds the
manifest with `if not p.name.startswith("_")`, so `_example.js` is deliberately withheld from the
manifest and is not a loadable feature. Confirmed by reading the route, not assumed.

### 5. `python tests/test_overhaul.py` — 58 ok, 2 skips, exit 0

```
brand
  ok    defaults has the whole schema
  ok    defaults normalise to the same keys
  ok    colours are hex without #
  ok    a theme is in the list
  ok    a lower-case #colour is cleaned
  ok    what was saved comes back
  ok    the file is on disk
  ok    a bad colour falls back
  ok    an unknown key is dropped
  ok    a path in the user id cannot escape
  ok    apply_style keeps the 13 fields
  ok    apply_style leaves a short tuple alone
captions
  ok    there are 32 looks
  ok    the names are strings
  ok    style() resolves a look
  ok    the subtitle file has a header
  ok    the subtitle file has a line of dialogue
formats
  ok    there is at least one format
  ok    an empty pick is still a known format
  ok    a plan is a dict
chat
  ok    top_phrases finds the repeated word
  ok    find_spikes returns a list
  ok    heat is a 0-100 number
  ok    heat of an empty window is 0
  ok    find_spikes on nothing is empty
moments
  ok    scoring nothing is a dict
vision
  ok    vision says whether it can work
  ok    vision.available() gives a yes or no
  ok    tagging nothing is a list
meme
  ok    there are moods
  ok    meme says whether it can work
music
  ok    there are beds
  ok    music says whether it can work
translate
  ok    there are languages
  ok    translate says whether it can work
peek
  ok    four moments are offered
  ok    they sit inside the clip
  ok    they are in order
rules
  ok    the rules document is not empty
  ok    a known channel answers with a rule
  ok    an unknown channel does not raise
  ok    badge renders
hunt
  ok    watching is a list
  ok    a key is a string
ytstats
  ok    a bare id is kept
  ok    a watch link gives up its id
  ok    a shorts link gives up its id
  ok    nonsense gives nothing
voice
  ok    voice can be applied
autopilot
  ok    a preview is text
  ok    the preview names the time
  ok    the preview does not run anything
  ok    installing needs a deliberate confirmation
  ok    and says why
edit
  ok    the change mentions the end
  ok    apply gives back a clip
  ok    apply leaves the original alone
  ok    unclear words are not an error

  skip  translate.text (no engine installed)
  skip  translate.words (no engine installed)
All checks passed.
```

The 2 skips are declared environment skips (`no engine installed`), reported as skips by the suite itself,
not silently swallowed. They are not counted as passes above.

### 6. `python tests/test_transcribe_logfare.py` — 27 ok, exit 0

```
A request to Logfare is built correctly
  ok    endpoint
  ok    model sent
  ok    key sent as a bearer header
  ok    uploaded as a wav
  ok    uploaded with a wav type
  ok    the audio is actually attached
The reply becomes word timings
  ok    word count
  ok    first word
  ok    last word
  ok    starts at zero
  ok    timings only go forward
  ok    stays inside the audio
  ok    every word has the three keys PeakCut needs
Audio in either scale goes out as the same 16-bit sound
  ok    float samples are not flattened to silence
  ok    both scales send identical bytes
Silence is never sent, because the answer would be invented
  ok    silence returns no words
  ok    ...and costs no call
transcribe() takes the cloud path when it is chosen
  ok    words came from Logfare
  ok    no word lasts longer than a breath
Both reply shapes become word timings
  ok    the whisper shape is read
  ok    the nova shape is read
  ok    ...with the same timings either way
A failure falls back to the local model when that model is installed
  Logfare transcription failed, falling back to local: Traceback (most recent call last):
  File "...\peakcut\studio\transcribe.py", line 479, in transcribe
    words = _logfare_transcribe(audio)
  File "...\peakcut\studio\transcribe.py", line 148, in _logfare_transcribe
    r = httpx.post(
        f"{LOGFARE_BASE_URL}/audio/transcriptions",
    ...<3 lines>...
        timeout=httpx.Timeout(120, connect=10),
    )
  File "...\peakcut\tests\test_transcribe_logfare.py", line 153, in boom
    raise RuntimeError("network went away")
RuntimeError: network went away

  ok    local transcription was tried
  ok    nothing invented on failure
With no engine here, the real reason is reported instead of a library name
  ok    it says Logfare could not do it
  ok    ...carries the underlying reason
  ok    ...and names no library the person never chose

All checks passed.
```

**Read this one carefully.** A `Traceback` and a `RuntimeError: network went away` appear in the middle of
the output — they are **not a failure**. That block is the suite deliberately injecting a network fault
(`test_transcribe_logfare.py:153`, `def boom`) to exercise the fallback path, and the very next lines are
`ok local transcription was tried` and `ok nothing invented on failure`. The suite ends `All checks passed.`
with exit 0. A line-grep for "Traceback" or "Error:" flags this file spuriously; exit code and the final
line are the authoritative signals here.

### 7. `python tests/test_transcribe_settings.py` — 21 ok, exit 0

```
  ok    save a key and model
  ok    blank model keeps the saved one
  ok    Local save keeps the key
  ok    Local save keeps the model
  ok    forget_key clears the key
  ok    logfare without a key refused
  ok    forgetting the key on logfare refused
  ok    still no key after the refusals
  ok    logfare without any model refused
  ok    refusal text
  ok    toggle on is saved
  ok    toggle on moves the calls
  ok    toggle off is saved
  ok    toggle off moves the calls back
  ok    toggle survives a save that omits it
  ok    junk tr.json survives: null
  ok    junk tr.json survives: []
  ok    junk tr.json survives: 3
  ok    junk tr.json survives: "text"
  ok    junk tr.json survives: {"provider": 42, "prox
  ok    AI base url untouched

All checks passed.
```

### 8. `python tests/test_review_gate.py` — 10 ok, exit 0

```
  ok    approved clip is queued
  ok    rejected clip is never queued
  ok    undecided clip waits for a person
  ok    undecided posts with review-first off
  ok    rejected still never posts with review-first off
  ok    low score still waits
  ok    review_pending counts undecided
  ok    review_pending drops to zero
  ok    last-mile guard fails the post
  ok    the error says why

All checks passed.
```

### 9. `python tests/test_connect.py` — 38 PASS, exit 0

```
PASS nothing can be connected before setup
PASS a normal user cannot see the setup
PASS ...or change it
PASS Connect before setup comes back with a reason
PASS setup from another website is refused
PASS a bad id is refused
PASS youtube app saved
PASS instagram app saved
PASS tiktok app saved
PASS secrets are never sent back
PASS each platform shows the address to register
PASS a new secret alone keeps the saved id
PASS everyone can connect now
PASS YouTube: Google's page, asking to upload
PASS YouTube: back on Connected apps, connected
PASS Instagram: Instagram's own page, with publishing permission
PASS Instagram: connected, with the #_ Instagram adds to the code removed
PASS TikTok: TikTok's own page, asking to post
PASS TikTok: connected
PASS all three accounts are listed with their names
PASS tokens never reach the page
PASS someone else's accounts are not mine
PASS a made-up return is refused
PASS cancelling on the platform says so
PASS one person's sign-in cannot be finished by another
PASS an unknown platform does not exist
PASS a signed link serves the clip to anyone, no sign-in
PASS a changed link does not
PASS a made-up link does not
PASS an expired link does not
PASS Instagram: a Reel from the signed link
PASS Instagram: published, with its link
PASS TikTok: an app not yet reviewed posts privately instead of failing
PASS TikTok: the whole file in one piece, with the right range
PASS TikTok: the account says why posts are private
PASS TikTok: once reviewed, public, with the video's link
PASS TikTok: big files go in pieces, the last taking the rest
PASS TikTok: an old sign-in is renewed, and the new refresh token kept
ALL PASSED
```

### 10. `python tests/test_delete.py` — 17 PASS, exit 0

```
PASS one clip is deleted with its files
PASS ...and its captions, notes and cut-out piece of video too  []
PASS ...while the other clips keep theirs
PASS the video's own file is never taken for a clip's piece
PASS several clips download as one zip with distinct names  ['Same title.mp4', 'Same title (2).mp4', 'Same title (3).mp4']
PASS bulk delete removes videos and clips, leaves work in progress alone  {'videos': 1, 'clips': 1, 'skipped': 1}
PASS the deleted video's folder is gone
PASS someone else cannot delete my clip
PASS someone else cannot download my clips
PASS someone else cannot delete my creator
PASS deleting a creator removes their videos and folder  {'ok': True, 'videos': 1}
PASS an account with a video in progress is not deleted
PASS the account is deleted
PASS nothing of theirs is left in the database  {'email_ok': 0, 'email_tokens': 0, 'feedback': 0, 'notices': 0, 'sessions': 0, 'usage': 0}
PASS the other account is untouched
PASS posts waiting for the deleted account are gone, the other account's stay
PASS the same email can sign up again afterwards, as a new account
ALL PASSED
```

### 11. Studio modules parse

```
$ python -c "import ast,glob; [ast.parse(open(f,encoding='utf-8').read()) for f in glob.glob('studio/*.py')]; print('all studio modules parse')"
all studio modules parse
```

Parse-only, same caveat as step 2: proves no syntax error in any `studio/*.py`, not that any of them
import cleanly or behave correctly.

### 12. Every served feature file is actually retrievable

```
14 feature files served
200 16482 autopilot.js
200 9494 day.js
200 9986 filters.js
200 11880 grid.js
200 3906 heard.js
200 11300 history.js
200 6327 keys.js
200 5741 log.js
200 9052 mood.js
200 12888 peek.js
200 8999 pill.js
200 4797 stage.js
200 16725 stats.js
200 14294 style-tiles.js
```

14/14 returned `200` with non-trivial bodies. This closes the loop that step 4 only opened: the manifest
advertising a file is not the same claim as the file being served, and both are now measured.

---

## What this proof does and does not establish

**Established by measurement:** all 15 feature files parse; the server is up and healthy; the manifest and
every file it names are served with 200; all six regression suites pass with exit 0; every studio module
is syntactically valid.

**Not established here:** that the features work in a browser (no DOM/render test was in scope — `node
--check` is parse-only); that anything imports cleanly at runtime (`ast.parse` is syntax-only); the 2
declared `translate` skips (no engine installed on this host). None of these were asked for, and none is
claimed above.
