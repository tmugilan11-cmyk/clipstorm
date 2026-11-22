# retention-signals

## What I built

`studio/learn_signals.py`: it turns one video's YouTube retention curve into sentences a
person can act on, and stays completely quiet when there is no channel connected.

Public functions, each with a plain-English docstring:

- `curve(video_id, days=28)` gives `{"points": [{"at", "kept"}], "source"}`, `at` and
  `kept` as percentages 0 to 100. It reads through `studio.api_analytics._token` and
  `_ask` when those import cleanly. When that import does not work it reads the token the
  same way that file does (`accounts.youtube_token()`) and calls `ytstats.analytics`
  directly. No channel, no token, no rows or any error gives `{"points": [], "source": ""}`.
- `drop_off(points, keep=0.5)` finds the first point at or below `keep` times the first
  point's kept value. Fewer than three points gives `{"at": None, "kept": None}`.
- `hook_signal(points)` one sentence about the first tenth. It names the share still
  watching at 5 percent in and how far below the opening share that is.
- `length_signal(points, seconds)` one sentence about the tail: what is left at 90
  percent in, and whether the last stretch still loses people (which is what says a
  shorter cut would hold more of them). Names the length only when a positive `seconds`
  was given.
- `signals(video_id, days=28, seconds=0.0)` gives `{"hook", "length", "drop", "points"}`.
- `lines(video_id, days=28, seconds=0.0)` gives the non-empty sentences in reading
  order: hook, then where the audience halves, then length. This is what `studio/learn.py`
  should call.

Decisions worth knowing:

- The metric pair is the one already measured in this repository:
  `audienceWatchRatio` by `elapsedVideoTimeRatio`, filtered `video==<id>`. That is the
  call at `studio/api_analytics.py:416-417` and `studio/ytstats.py:335-336`. I did not
  also ask for `relativeRetentionPerformance`: nothing in a sentence needs it, and asking
  for less is less that can be refused.
- One wide retry. The retention route asks over 3650 days because Analytics answers by
  upload date, so a 28-day window hides an older video. `curve` tries the caller's `days`
  first and retries once at 3650 days only when the first ask returned no rows. That is at
  most two calls, never a loop.
- A sample only counts as "at 5 percent" or "at 90 percent" when it is within 2.5 points
  of that mark. On a sparse curve the nearest sample can be half the video away, and a
  sentence about 5 percent in would then be quoting a number measured somewhere else.
  Beyond that distance the sentence is empty instead.
- Differences under 0.05 points are treated as level, because the curve is rounded to one
  decimal on the way out. A 0.2 point move is spoken as "0.2 points above", which is what
  the numbers say.
- Ratios become percentages once, in `curve`, matching the Insights retention route. No
  figure is written anywhere it was not measured.

Failure behaviour, verified: every public function wraps its body and returns its empty
shape. A curve with two points gives `points: 0`, empty sentences and no drop. Junk points
(`{"at": "x", "kept": None}`) are dropped, not guessed at. A raising `curve` gives
`lines` an empty list.

## The file I own

`studio/learn_signals.py`. No other file was edited.

## The exact command and its output

```
$ cd peakcut && python -m py_compile studio/learn_signals.py; echo "[exit $?]"
[exit 0]
```

Behaviour check on this install, which has no channel connected:

```
no-channel curve: {'points': [], 'source': ''}
no-channel signals: {'hook': '', 'length': '', 'drop': {'at': None, 'kept': None}, 'points': 0}
no-channel lines: []
drop: {'at': 25.0, 'kept': 48.0}
hook: At 5 percent in, 68 percent are still watching, 32 points below where the curve starts.
length: This 32 second clip still has 24 percent watching at 90 percent in, and the last part loses 4 more points, so a shorter cut would keep more people.
short drop (2 points): {'at': None, 'kept': None}
junk hook: ''
flat: At 5 percent in, 70.2 percent are still watching, 0.2 points above where the curve starts.
tail flat: At 90 percent in, 30 percent are still watching, and the last part does not lose viewers, so the length is not what is costing people.
short lines (2 points): []
raising lines: []
```

The sample curve used for those sentences is synthetic and only proves the arithmetic and
the wording. It is not a claim about any real video.

## What I could not do

- I could not run a real curve end to end. There is no channel connected in this install,
  so no token exists and YouTube was never asked. The live path (`_token`, `_ask`, the
  ratio-to-percent conversion, the wide retry) is written against the shapes already used
  at `studio/api_analytics.py:402-424` and `studio/ytstats.py:317-355`, but it has not
  been exercised against Google's answer.
- I did not run `python tests/run.py`, the repository's own suite. It starts a server, and
  this is a headless subagent slot with a 25 minute budget; the module is not yet called
  from anywhere, so the suite cannot see it either way.
- I did not wire this into `studio/learn.py`. That file belongs to another owner in this
  wave, per the brief. The handoff is one call: `learn_signals.lines(video_id, days,
  seconds)` returns ready sentences, and an empty list means there was nothing to say.

## For the reviewer

- The import of `api_analytics` is inside `_reader()`, not at module top, because that
  module builds a FastAPI router. Reading one curve should not require the web layer to
  import, and a broken import there must not stop a round.
- `hook_signal` and `length_signal` both refuse a curve under three points, so a two point
  curve cannot produce a sentence that reads like a measurement.
- The sentences use "percent" and "points" as words, no symbols, and name the share before
  the movement. There is no em dash and no emoji.
