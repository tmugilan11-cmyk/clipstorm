# formats: the "Clip formats" page

Agent slug: `formats`. Skill loaded before any file was read: **frontend-design**.

## What I built

One new file, `web/feat/formats.js` (375 lines), and nothing else. It adds a main-menu page called
**Clip formats** under the **Make** group, icon `film`, order 32, at the address `/formats`.

The page has two sections.

**The eight shapes.** One card per shape returned by the server, each with its name, one plain
sentence about when to use it, and how many parts it needs. The sentence is the server's own `hint`
with only its first letter capitalised, so the page can never drift from `studio/formats.py`. The
parts count is drawn as up to six small marks plus the words "N pieces" or "one piece", and goes
through `num()` before it reaches the markup.

**The looks.** A read-only grid of tiles, one per caption look, each loading a real frame from
`GET /api/style/preview?style=<name>` as an `<img width="270" height="480" data-src="...">`. The
loading is our own, copied from `web/feat/style-tiles.js`: four slots at a time, a waiting queue, an
`IntersectionObserver` with `rootMargin: "350px 0px"`, a fallback that asks for every frame at once
when the tab is hidden, an 8 s net for anything near the viewport and a 20 s timeout per slot so one
dead frame cannot stall the rest. There is no `loading="lazy"` anywhere: a background tab never fires
it, and the whole point of the page is that the frames arrive anyway. A frame that fails is hidden
by CSS (`data-st="off"`) rather than removed, so the label stays and the tile keeps its shape.

A "Check again" button under the shapes heading re-reads both lists and says so in a toast.

### Failures are sentences

`/api/formats` and `/api/captions/styles` are asked for separately, so one failing does not blank
the other half of the page. A failure writes one sentence into the page naming which list could not
be read and why, taken from the error's own `message`, and the same sentence is what the "Check
again" toast shows. An empty list is `[]` and draws a sentence saying the PeakCut returned no shapes
(or no looks), not a fake row. An unknown total is a sentence saying the count was not sent, never a
made-up number.

### One hint under every control

The "Check again" button has a `.hint` line: "Reads both lists from this PeakCut. Use it after a
rebuild, when a shape or a look may have been added." The two sections carry a `.hint` each too. No
em dashes, no emoji, no shadows, hover changes colour only, and the existing palette CSS variables
are used rather than new colours.

## Routes it reads

| Route | Where it is declared | What the page uses |
|---|---|---|
| `GET /api/formats` | `studio/api_style.py:73` | `formats[].id`, `label`, `needs_parts`, `hint`, plus `count` and `default` |
| `GET /api/captions/styles` | `studio/api_style.py:44` | `styles[].name`, `label`, plus `count` and `default` |
| `GET /api/style/preview?style=<name>` | `studio/api_style.py:182` | the frame itself, as an `<img>` source only |

All three were confirmed to exist with `grep -rn 'router.get\|@app.get' studio/` before they were
used, and all three were called against the live test server (see the commands below).

## What it cannot do yet

- **Nothing on the page changes anything.** The looks grid is read-only on purpose: there is no
  click that selects a look, applies it to a clip or saves it. Making a tile selectable needs a place
  to remember the choice, which is the clip form's job, not this page's.
- **It does not plan a clip.** `POST /api/formats/plan` exists and would take a chosen shape plus a
  list of moments and answer which clips to cut, but the page has no moment picker to feed it, so
  calling it here would only ever produce a refusal.
- **The frames are the house preview**, one per look, not a frame from the person's own video. A real
  frame per look depends on a clip existing, which this page does not have.
- **A look added to the server appears only after a reload or a "Check again" press**; the page does
  not poll. That is deliberate: it is a reference page, not a live panel.
- **No search or filter over the 35 looks.** With 35 tiles it did not seem worth the extra control;
  if the look list grows to hundreds this page wants a filter box.
- I could not exercise the page in a real browser tab (no browser session was used for this job), so
  the frame loading is verified by the code path and by fetching the preview route directly, not by
  watching pixels arrive.

## Commands I ran and what they said

Run from `C:\Users\Asus\Documents\deepseek-harness\default-workspace\peakcut`.

```
$ node --check web/feat/formats.js
JS OK

$ python tests/test_feat_files.py
... ok   usage.js invents no clashing id
ok   loader keeps the documented folder
{"files": 43, "checks": 350}
All checks passed.

$ python tests/test_menu_pages.py
ok   usage.js draws its page

All checks passed. 192 ok
```

Live probes against the running test server on `http://127.0.0.1:8798` (not restarted):

```
GET /api/formats            200  count=8  default=moment
  ids = [moment, callback, compilation, escalation, thenvsnow, reveal, chat, waitforit]
  sample = {"id": "moment", "label": "Moment", "needs_parts": 0, "hint": "one strong clip, the default"}
GET /api/captions/styles    200  count=35  default=bounce  n=35
  sample = {"name": "bounce", "label": "Bounce", "house": true}
GET /api/style/preview?style=bounce   200  image/jpeg  43161 bytes
GET /assets/feat            200  served count: 42  |  formats.js served: True
GET /assets/feat/formats.js 200  17679 bytes
  loading="lazy" present: False
  data-src occurrences: 5
  width="270": True
  PeakCut.page: True
  group Make: True
  order 32: True
```

The counts in the last block were taken after this file's own edits, so they describe what the
server is serving now, not what was true earlier in the job.

## Files touched

- Created: `web/feat/formats.js`
- Created: `docs/swarm4/wave4/formats.md` (this report)

Nothing else was edited. No change is needed in `web/index.html`, `web/plugins.js` or `studio/` for
this page to work: the loader picks the file up from `web/feat/` on its own, which the
`/assets/feat` listing above confirms.
