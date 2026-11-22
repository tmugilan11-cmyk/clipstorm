# stage: four dots on a running job card

## What I built

`web/feat/stage.js`. One file, no other file touched.

A job that is queued or running now shows its four steps as small chips under the existing
progress bar: **Download**, **Listen**, **Pick moments**, **Make clips**. Each chip is `done`,
`now` or `wait`. The card already prints a percentage and a sentence, so the chips carry no
number at all: they show *where* the job is, not *how far*.

The hook is `after: { drawJobs(root) }`, as the contract requires.

## Skill loaded

`ui-design-guide`. Its advice that mattered here: consistent pill radius, one accent used
sparingly, and a real hover/transition on state change rather than a static picture. I also
followed `peakcut/AGENTS.md`, which says keep the existing palette and **no shadows**, so the
active chip is a flat brand fill with no shadow.

## The real stage strings

Read from `peakcut/studio/jobs.py`, not guessed. The full list of strings the code sets:

| String set in `studio/jobs.py` | Line | Maps to |
| --- | --- | --- |
| `"Waiting"` (initial, at job creation) | 326 | 0 Download |
| `"Picking up where it stopped"` | 240, 663 | by progress |
| `"Getting the audio"` | 665, 670 | 0 Download |
| `"Getting the speech model (one time, about 480 MB)"` | 668 | 0 Download |
| `"Reading the transcript" + where` | 815 | 1 Listen |
| `"Writing the transcript" + where` | 818 | 1 Listen |
| `"Finding the best moments" + where` | 827 | 2 Pick moments |
| `"Finishing the clips"` | 872 | 3 Make clips |
| `"Done"` / `"Done, but nothing clip-worthy was found"` | 886 | not drawn (finished) |
| `"Stopped"` | 928 | not drawn (failed) |
| `"High demand right now: N videos ahead of yours"` | 186 | 0 Download |
| `"High demand right now: yours is next"` | 189 | 0 Download |
| `"Waiting in line: N videos ahead of yours"` | 186 | 0 Download |

Note the two the brief did not predict: `"Getting the audio"` is the **audio download**, so it
lights Download, not Listen. And `"Picking up where it stopped"` is reused for every restart,
so it says nothing about the step; the progress figure decides that one.

`studio/live.py` also sets `"Recording"`, `"Connecting to the stream"`, `"Could not record"`
and a free-text end note. Those belong to `status: "live"` jobs, which `index.html` draws with
`liveHtml()` and which never produce a `.bar`, so this file never sees them.

## Mapping rules

Strings are matched in the order a job meets them, first match wins:

```js
[/transcript|transcrib|listening|hearing/i, 1],
[/best moment|finding|moments?\b|\bai\b|thinking/i, 2],
[/finishing|making the clips|render|caption|export/i, 3],
[/getting|download|fetch|speech model|waiting|ahead of yours|high demand|queue/i, 0],
```

`Picking up where it stopped` and `Waiting` are handled before the list, by `band(progress)`,
using the bands the server's own numbers walk: fetch to ~.13, transcript .14 to .92, clips
from .92.

**Anything unrecognised returns 0 and draws nothing extra.** It does not throw, does not toast,
and does not name the unknown stage anywhere.

## Contract rules I checked against

- **Escaping.** Every string interpolated into the HTML is mine: the four labels are a local
  constant array, `now` is an integer 0 to 3, `state` is one of three literals. No server value
  reaches `innerHTML`, so `esc()` is not needed and no unescaped value is possible. This is
  deliberate and is the strongest version of rule 3/4 rather than an omission.
- **No duplicate percentage.** No `%`, no progress number anywhere in the chips. Verified in the
  browser: `chipTextHasPercent: false`.
- **Nothing on a finished job.** Gated on `LIVE = new Set(["queued", "running"])`, checked against
  `job.status` from `PeakCut.state().jobs`, not against the card's markup.
- **Idempotent and cheap.** The hook runs on every animation frame. It skips a card whose chip
  already matches the current step, and replaces only a stale one. Measured: three consecutive
  draws for the same step produced one insert.
- **Fail soft.** If `state()` or `jobs` is missing it does nothing. If a card has no `.bar` it
  skips that card. If the job is not in the list it skips.
- **Plain English, no emoji, no em dash.** Checked with grep: zero em or en dashes in the file.

## Exact commands and their output

Syntax check:

```
$ cd peakcut && node --check web/feat/stage.js && echo "JS OK"
JS OK
```

The required grep, full output:

```
$ cd peakcut && grep -n 'stage=' studio/jobs.py | head -20
240:        job.update(status="queued", stage="Picking up where it stopped", error=None, resume=True)
242:        job.update(status="done", stage="Recording paused by a server update", was_live=True)
663:        _set(job, status="running", stage="Picking up where it stopped", error=None)
665:        _set(job, status="running", stage="Getting the audio", progress=0.03, error=None, clips=[], ai={}, done_blocks=0)
668:        _set(job, stage="Getting the speech model (one time, about 480 MB)")
670:        _set(job, stage="Getting the audio")
815:            _set(job, stage="Reading the transcript" + where)
818:            _set(job, stage="Writing the transcript" + where)
827:        _set(job, stage="Finding the best moments" + where, word_count=len(words))
872:        _set(job, stage="Finishing the clips", progress=max(job["progress"], 0.92))
887:    _set(job, status="done", stage=stage, progress=1.0, took=round(time.time() - t0))
928:                _set(job, status="error", error=safe.friendly(e), stage="Stopped")
```

Serverside check that the live server serves the file:

```
$ cd peakcut && python - <<'PY'
import httpx
r = httpx.get("http://127.0.0.1:8798/assets/feat").json()
print("served files:", r["files"])
PY
status: 200
served files: ['grid.js', 'heard.js', 'stage.js']
```

## Live browser proof

I have browser tools, so I loaded `/app` and proved the code really runs, rather than reasoning
statically.

Registered and booted:

```
{"order":["grid","filters","heard","stage"],"hasStage":true,"hook":true,"css":true}
```

`stage` is in `PeakCut._order` and the stylesheet `#pcss_stage` exists.

I inserted a fake running job into the live page's own state, called the page's real `drawJobs()`,
and let the loader's animation frame run the `after` hook. Every real stage string, in the real DOM:

| `job.stage` | status | chips drawn |
| --- | --- | --- |
| `Getting the audio` | running | Download:now Listen:wait Pick moments:wait Make clips:wait |
| `Getting the speech model (one time, about 480 MB)` | running | Download:now Listen:wait Pick moments:wait Make clips:wait |
| `Reading the transcript (minute 3 of 20)` | running | Download:done Listen:now Pick moments:wait Make clips:wait |
| `Writing the transcript (minute 3 of 20)` | running | Download:done Listen:now Pick moments:wait Make clips:wait |
| `Finding the best moments (minute 5 of 20)` | running | Download:done Listen:done Pick moments:now Make clips:wait |
| `Finishing the clips` | running | Download:done Listen:done Pick moments:done Make clips:now |
| `Waiting` | queued | Download:now Listen:wait Pick moments:wait Make clips:wait |
| `High demand right now: 2 videos ahead of yours` | queued | Download:now Listen:wait Pick moments:wait Make clips:wait |
| `Picking up where it stopped` | running, 0.5 | Download:done Listen:now Pick moments:wait Make clips:wait |
| `Done` | done | **nothing drawn** |
| `Stopped` | error | **nothing drawn** |
| `a stage nobody has ever seen` | running | Download:now Listen:wait Pick moments:wait Make clips:wait (no throw) |
| `undefined` | running | Download:now Listen:wait Pick moments:wait Make clips:wait (no throw) |

Placement, checked on the live cards:

```
[{"job":"fake-stage-job-1","hasBar":true,"hasChip":true,"chipIsRightAfterBar":true,
  "nextAfterBar":"DIV.pcstage","chipTextHasPercent":false},
 {"job":"20261119-171742-d88f","hasBar":false,"hasChip":false,...}]
```

The chip is the immediate next sibling of `.bar`, and the finished job next to it gets nothing.

Console was clean afterwards: `No console lines yet (nothing logged since the page probe was
installed)`. No thrown errors from the hook across all thirteen draws.

A screenshot confirmed the look: chips sit directly under the bar, above the "Finding the best
moments (minute 5 of 20) · 62%" line, with Download and Listen in soft brand, Pick moments
solid brand, Make clips greyed back.

I removed my fake job from the page state afterwards, so the running server was left as I found it.

## What I could not test

- **A genuinely live job.** There was no real in-flight job on the test server, so I drove the
  real `drawJobs()` with a fake job in the real state instead of waiting for a real encode. The
  code path is identical; only the data is synthetic.
- **The live recording path.** `status: "live"` jobs use `liveHtml()` and have no `.bar`, so this
  feature correctly never touches them. I did not exercise a live recording.
- **Very small viewports.** I added a `max-width:560px` rule but only verified at desktop width.

## For the reviewer

- **`Getting the audio` means download, not listen.** This is the one place a reading of the
  brief would go wrong. Line 665 and 670: the audio is *fetched* there, so it lights Download.
  Listen only starts at `Writing the transcript`.
- **`Picking up where it stopped` is ambiguous by design.** It is set on every restart at both
  line 240 and 663, after any stage. Falling back to `progress` is the only honest mapping.
- **Middle band is mostly Listen.** `Finding the best moments` fires once per part, then
  `Writing the transcript` again. So the chip flickers Listen, Pick, Listen, Pick as parts are
  written. That is the truth of the pipeline, not a bug, but the reviewer should know it is
  expected.
- **No `esc()` call on purpose.** Nothing server-supplied is interpolated. If a later change
  wants to put `job.stage` into the chip text, `esc()` becomes mandatory at that point.
- **The stale-chip replace path.** If a card somehow survives a redraw with an old step, the hook
  removes it and redraws rather than leaving a wrong chip. This is belt and braces; normal
  redraws replace the whole card body.
