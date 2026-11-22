# polish-errors

One way of showing a failure.

## File I own

`peakcut/web/feat/polish-errors.js` (331 lines). No other file was edited. I did not
touch `web/index.html`, `web/plugins.js`, or `studio/`.

## What it adds

- `PeakCut.fail.say(err, what)` turns any caught error into one plain sentence:
  "The clip list: That stream is private." or "The creator list had a problem on its
  side. Retry in a moment." It reads 401, 404, 5xx, offline, timeout, abort, and the
  network words. The server's own sentence is kept when it is a real sentence.
- `PeakCut.fail.show(box, err, {what, retry})` draws an inline `.pcerr` line at the top
  of a container, with a Retry button when a retry was supplied. A missing container
  falls back to a toast instead of a throw.
- `PeakCut.fail.guard(promise, opt)` shows the line and resolves to null. Never rethrows.
- `PeakCut.fail.clear(box)`, `.note(where, err)`, `.seen` for quiet bookkeeping.
- Wrapping `PeakCut.api` and `PeakCut.send` at boot. Every thrown error now carries the
  plain sentence, so all 28 files that already print `err.message` get plain English
  with no edit. This is the reach without touching other agents' files.

## Measured

- `node --check web/feat/polish-errors.js` -> `JS OK` (no output, exit 0).
- `python tests/test_feat_files.py` -> `{"files": 57, "checks": 462}` then
  `All checks passed.`
- Empty catch bodies across `web/feat/*.js`, counted by a brace matcher (not grep,
  because most empty catches carry a comment):
  - before: 0 of mine, 61 in the 47 existing files
  - after: 65 empty bodies in total, 0 of them in my file (the rise is other agents
    writing in parallel while I measured; my file contributes none)
- Sentences produced from 10 test errors: 0 of 10 contain "Something went wrong".
  Sample: `"Something went wrong"` + what `"The clip list"` ->
  "There was a problem with the clip list. Retry, and if it fails again reload the page."
- Escaping: a server string `<img src=x onerror=alert(1)>` renders as
  `&lt;img src=x onerror=alert(1)&gt;` inside the line. Verified in a DOM stub.

## Still missing, and needs another agent's file

These silent catches are the ones that should call `P.fail.show` or `P.fail.guard` but
live in files I do not own. Each is a two-line change:

- `web/feat/history.js:193` `catch { return; }` around `/api/jobs/<id>` reread. The
  refresh button goes quiet on failure and nothing says why.
- `web/feat/peek.js:244` `try { job = await P.api("/api/jobs/" + jid); } catch {}`.
- `web/feat/analytics-export.js:215` logs only, then the export silently stops.
- `web/feat/analytics-table.js:307` logs only around `mount()`.
- `web/feat/analytics-retention.js:428` logs only around `mount()`.
- `web/feat/learn.js:324` an empty catch around the report send.

Lines 3 to 6 are the two log-only catches plus their siblings. A one-word call to
`P.fail.note(...)` in each would also do, and is smaller.

## Left out

No page, no Tools card, no keys: this is a helper, not a screen. The loader's own
catches in `plugins.js` (63, 96, 179, 200, 241, 263, 273) are in a file I may not edit.
