# Two arm trial card on the Improve page

Skill named for this job: `frontend-patterns`.

## What I built

`web/feat/learn-arms.js` is one plug-in, registered as `PeakCut.add("learn-arms", ...)`, that puts a
"Two arm trial" card on the Improve page. It owns no page and no route. It hangs off the
`after.drawSettings` hook, which is the only hook that fires with the drawn page node, and it does
nothing at all when the node does not carry the Improve page's `.lrn` root.

The card reads `GET /api/learn/arms` and has three faces:

- **No trial yet.** One sentence on what a trial is for, and a "Start a trial" button. The button opens
  a form with two `<select>`s built from the five settings the page already names (`style`,
  `hook_words`, `clip_len`, `sound`, `captions_always`) and one text input per setting for the value.
  The value is a text input on purpose: a caption look is a name and a length is a number, and the
  server takes both as text. It POSTs `{target, value, other, other_value}` to `/api/learn/arms`.
- **A trial is running.** Which setting is on trial and at what value, which arm is running now, which
  arm waits behind it, and a Stop button that sends `DELETE /api/learn/arms`.
- **Both arms have run.** The same lines, plus the comparison sentence exactly as the server sent it,
  quoted through `esc()` and never rewritten. A sentence that says the difference is inside the noise
  is printed like any other, because that is the answer.

A failure is one sentence in the card and nothing else changes: the card stays, the page keeps
working, and the form keeps what the person typed.

## Details worth knowing

- The Improve page redraws its whole body after every action, which removes anything a feature put
  inside it. So this card puts itself back. It does that from the `after.drawSettings` hook and from a
  700 ms tick that only runs while `.lrn` is on screen and stays silent when the card is already
  correct (`SIG` holds the last markup drawn).
- The record shape is `studio/ai_arms.py`, not a guess: `{at, target, value, other, other_value, arm,
  runs}`. `runs` holds `"a"` and `"b"`, so "both arms have run" is the same test as `ai_arms.done()`.
- The sentence key is not settled yet, because the wire agent owns the route. The card tries
  `result`, `read`, `saying`, `summary`, `effect`, `said`, then falls back to any string field that
  reads as a sentence (six or more words ending in a full stop). It never composes a sentence of its own.
- A failed start reopens the form with `FILL` still holding the four values, so one error costs one
  sentence rather than the whole form.
- When both arms have run but no sentence arrived, the card says that sentence is missing. It does not
  fill the gap with invented words or numbers. No number in this file comes from anywhere but the server.
- No new dependencies, no absolute origin, no id that clashes with `index.html`, no em dash, no emoji.

## The file I own

`C:/Users/Asus/Documents/deepseek-harness/default-workspace/peakcut/web/feat/learn-arms.js`

I edited no other file. This report is the one other file I wrote, as the task asked.

## The checks, with their literal output

```
$ cd peakcut && node --check web/feat/learn-arms.js && echo "node --check: OK"
node --check: OK
```

```
$ cd peakcut && python tests/test_feat_files.py
ok   learn-arms.js parses
ok   learn-arms.js declares one plug-in
ok   learn-arms.js is named after itself
ok   learn-arms.js is the only owner of learn-arms
ok   learn-arms.js does not write into index.html
ok   learn-arms.js draws only fixed markup
ok   learn-arms.js uses no absolute origin
ok   learn-arms.js invents no clashing id
{"files": 39, "checks": 318}
All checks passed.
```

I also loaded the file in Node against a stub `PeakCut` to check behaviour the two gates cannot see:
it registers slug `learn-arms` with the `drawSettings` hook and five actions, the hook returns quietly
when the page is not on screen, the trial branch draws the server's sentence word for word including
"inside the noise", and a 404 draws exactly one error sentence and leaves the card and its button in
place.

## What I could not do

- **The route does not exist yet.** `GET /api/learn/arms` answers `404 {"detail":"Not Found"}` on the
  test server at `127.0.0.1:8798`, because `studio/api_learn.py` and `studio/learn.py` belong to other
  agents in this wave and neither mentions arms. So every request from this card fails today, softly,
  with one sentence. The card is written against the brief's contract and will light up when the wire
  agent lands `GET`, `POST` and `DELETE /api/learn/arms`. Until then the start button cannot be tried
  end to end.
- **The sentence key is a guess about a file I do not own.** If the route returns the sentence under a
  name outside my list and not shaped like a sentence, the card will say the comparison is missing
  rather than show it wrongly. If that happens, adding the real key to `SAYS` is a one line change.
- **No browser check.** I did not open the card in the running app, because the route is missing and
  the honest picture would have been the failure sentence. The visual work (palette, spacing, the two
  column form collapsing to one column under 620 px) has been matched to `learn.js` by reading it, not
  by looking at it.
