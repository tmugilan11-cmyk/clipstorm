# autopilot: install the clipping schedule from the browser

Slug: `autopilot`. One file owned and changed: `peakcut/web/feat/autopilot.js` (391 lines, 16,482 bytes).
The report itself is `peakcut/docs/swarm3/autopilot.md`.
Nothing else in the repository was edited. No git command was run. The server was not restarted.

Skill loaded with the `skill` tool: **`ui-design-guide`**.

## What it does

Settings > Tools gains one card, "Clip on a schedule", directly below the existing "A schedule you can paste".

- **A times box.** `<input id="pcauto_times" value="09:00,18:30">`, accepting a comma, semicolon or space
  separated list, up to 12 entries, on a 24 hour clock.
- **"Show me the plan".** Renders the platform as a label (`Windows`), one sentence stating the days and times
  and how many scheduler commands that means, the command text itself in a `<pre>`, one line saying it can also be
  pasted by hand, and the platform's own warning in a warm callout when the server sends one.
- **"Install the schedule"**, primary. Confirms, then `POST /api/autopilot/install` with `{"confirm": true}`, then
  shows the result.
- **"Remove it"**. Confirms, then `POST /api/autopilot/remove` with `{"confirm": true}` and the same times.
- **A status line** under the buttons, `role="status" aria-live="polite"`, which carries every message: the plan
  errors, the "one more click" state, the install/remove result, and any refusal sentence from the server.

Every server sentence is printed through the page's `esc()`, exactly as it arrived.

### Which confirm it uses, and why

`index.html` defines `ask(title, text, okLabel, danger)` as a plain top-level function in a non-module `<script>`,
so it is on `window` and **is** reachable from a feature file. Verified in the live page before relying on it:
`typeof window.ask === "function"`.

So the card uses the page's own dialog. Proof it really goes through it, taken in the live browser:

```
{ open: true, ret: "no",
  text: "Install the schedule?This asks this computer to run a batch of clips on Monday, Wednesday and Friday at
         09:00 and 18:30. Nothing else on the machine changes, and you can remove it again from this card.
         CancelInstall it" }
```

Cancel sends nothing at all. Measured with `fetch` wrapped: the only requests were the page's own `/api/status`
and `/api/sync`. No `/api/autopilot/install` was sent.

The brief also asked for the second-click fallback if `ask()` cannot be reached. It is still there, behind
`typeof window.ask === "function"`, because the helper is a page detail and could move. Proven by setting
`window.ask = undefined` and clicking:

```
first  click: { label: "Really install it?", cls: "btn danger", arm: "1", net: [] }
second click: { label: "Install the schedule", arm: "", sent: 1 }
```

The second click sent `["/api/autopilot/install", {"confirm": true, "times": "09:00,18:30"}]` and painted
`Installed The schedule is on this machine now.` plus the scheduler's own line. The first click sends nothing, the
button turns into `Really install it?` in the danger style, the status line says
`One more click / Nothing has happened yet. Press the same button again to go ahead.`, and the armed state drops
itself after eight seconds.

Getting this right needed one fix: the `finally` block first reset the button even when it had just been armed,
so the arm was overwritten immediately and the second click re-armed instead of sending. `confirmStep` now returns
`true`, `false` or `"armed"`, and the caller leaves an armed button alone.

### The refusal is shown as-is, never retried

`studio/api_auto.py:146` refuses every write that does not carry `confirm: true` with a 400 and a full sentence.
The card shows that sentence unchanged. Proven end to end by forcing the POST to be sent without the flag:

```
msg:  Not done Nothing was changed on this machine. Sending "confirm": true is what installs a schedule,
      and it is never filled in for you.
pill: pill bad
```

That is the exact `detail` string from the route, relayed by `PeakCut.send`'s throw, with no rewording, no
truncation and no automatic retry. A refusal is never turned into a success and never re-sent.

### Remove

Proven with the same setup: confirm dialog titled `Remove the schedule?` with the confirm button styled `btn danger`,
Cancel sending nothing, and a confirmed click sending `["/api/autopilot/remove", {"confirm": true, "times": "09:00"}]`.
The success render is:

```html
<p><span class="pill ok">Removed</span> <span>The schedule is off this machine now.</span></p>
<pre class="pcauto-pre">SUCCESS: The scheduled task "PeakCutAutopilot" was successfully deleted.</pre>
```

The result sentence and the scheduler's own output line both come from the response, not from this file.

### Times are checked in the page, because the server is silent about them

`studio/autopilot.py:_times` drops any entry `_clock` rejects and then falls back to `09:00` when nothing survives.
So `9am` and an empty box would both quietly become 09:00. The card checks first and clears the old plan, so a
previous plan cannot sit under a message about a new one and look like the answer:

```
"9am"          -> "Check the times  \"9am\" is not a time. Write it like 09:00."   (plan box emptied)
""             -> "Check the times  Type at least one time, like 09:00."
over 12 times  -> "Check the times  That is 13 times. PeakCut takes up to 12."
"09:00, 18:30, 21:15" -> "Runs Monday, Wednesday and Friday at 09:00, 18:30 and 21:15. That is 3 commands."
```

### One wording decision worth a reviewer's eye

`GET /api/autopilot/preview` ends with `note: "Copy this and run it yourself. PeakCut does not touch your
scheduler."` Directly above an Install button that reads as a flat contradiction. `spec` and `preview` return the
same command text, so the card shows the preview text (it is the copy a person would paste) and its own line
instead of that note: "That is the text to paste if you would rather run it yourself. Install runs it here instead."
The note is not hidden from the API; it is only not repeated in the one place where it would be false.

## Endpoints used, and their real shapes

All three are in `peakcut/studio/api_auto.py`. `spec` and `preview` also call `_admin`-adjacent `_me(request)`, and
install and remove call `_admin(request)` before reading the body, so a signed-out caller gets 401/403, not 400.

`GET /api/autopilot/spec`. Params `os`, `times`, `command`, all `Query` with max lengths. Answers
`{ok, platform, label, days, times, argv, cmds, off, file, body, text, warn, error}`. `cmds` is an array of argv
arrays; `text` is the paste-ready script; `error` is `""` on success.

`GET /api/autopilot/preview`. Same three params. Answers `{ok, preview, times, os, note}`. `os` reads
`"this machine"` when none was asked for. An unknown platform comes back as `ok: true` with `preview` starting
`"# "`, so the failure is inside the text, not in a 400.

`POST /api/autopilot/install`. Body `{confirm, times, os, command}`. `confirm` must be exactly `true` or the answer
is 400 `_NEEDS_CONFIRM`. Success is `{ok: true, installed: true, schedule}`. Throttled 6 per 300 s after a change.
The card only treats `installed === true` as success and otherwise prints `schedule.error`.

`POST /api/autopilot/remove`. Body `{confirm, times, os}`. Same gate and throttle. Success is
`{ok: true, removed: true, schedule}`. Note the remove path's `schedule` carries no `text` or `warn` key, so the card
reads `schedule.ran[].out` for the result sentence, which both paths do provide.

## Exact commands and their output

```
$ cd peakcut && node --check web/feat/autopilot.js && echo "JS OK"
JS OK
```

```
$ curl -s http://127.0.0.1:8798/api/autopilot/spec
{"ok":true,"platform":"windows","label":"PeakCutAutopilot","days":["MON","WED","FRI"],"times":["09:00"],"argv":["C:\\Users\\Asus\\AppData\\Local\\Programs\\Python\\Python315\\python.exe","-m","studio.autopilot","--run"],"cmds":[["schtasks","/Create","/TN","PeakCutAutopilot","/TR","C:\\Users\\Asus\\AppData\\Local\\Programs\\Python\\Python315\\python.exe -m studio.autopilot --run","/SC","WEEKLY","/D","MON,WED,FRI","/ST","09:00","/F"]],"off":[["schtasks","/Delete","/TN","PeakCutAutopilot","/F"]],"file":"","body":"","text":"rem PeakCut autopilot, MON, WED, FRI at 09:00\nrem Nothing here runs until an operator pastes it.\n\nschtasks /Create /TN PeakCutAutopilot /TR \"C:\\Users\\Asus\\AppData\\Local\\Programs\\Python\\Python315\\python.exe -m studio.autopilot --run\" /SC WEEKLY /D MON,WED,FRI /ST 09:00 /F\n\nrem to remove it again:\n\nschtasks /Delete /TN PeakCutAutopilot /F\n","warn":"Windows keeps no log of its own, so a wrapper .cmd is the only way to keep output; the task name has to match again when you remove it.","error":""}
```

```
$ curl -s "http://127.0.0.1:8798/api/autopilot/preview?times=09:00"
{"ok":true,"preview":"rem PeakCut autopilot, MON, WED, FRI at 09:00\nrem Nothing here runs until an operator pastes it.\n\nschtasks /Create /TN PeakCutAutopilot /TR \"C:\\Users\\Asus\\AppData\\Local\\Programs\\Python\\Python315\\python.exe -m studio.autopilot --run\" /SC WEEKLY /D MON,WED,FRI /ST 09:00 /F\n\nrem to remove it again:\n\nschtasks /Delete /TN PeakCutAutopilot /F\n","times":["09:00"],"os":"this machine","note":"Copy this and run it yourself. PeakCut does not touch your scheduler."}
```

```
$ curl -s -w "\n[http %{http_code}]\n" -X POST http://127.0.0.1:8798/api/autopilot/install -H "Content-Type: application/json" -d '{}'
{"detail":"Nothing was changed on this machine. Sending \"confirm\": true is what installs a schedule, and it is never filled in for you."}
[http 400]
```

The third one is the refusal, and it is the correct, expected answer. Nothing was installed.

```
$ schtasks /Query /TN PeakCutAutopilot
ERROR: The system cannot find the file specified.
```

No task exists on this machine, before or after the whole session. The task-creation path was exercised only against
a stubbed `PeakCut.send`, never against the real route.

## Live browser checks

The page was loaded, the Tools tab opened, and the card measured and driven.

- `window.PeakCut._order` contains `autopilot`; `document.getElementById("pcss_autopilot")` exists, so the CSS is
  registered once.
- The card's own markup: `#pcauto_times` value `09:00,18:30`, `#pcauto_out`, `#pcauto_msg`, and the three
  `data-act` names `pcauto_plan`, `pcauto_install`, `pcauto_remove`. All three are distinct from every act name
  `index.html` already handles.
- Measured box: card 944 px wide, the times input 280×40, the `<pre>` 944×259 with its own horizontal scroll (the
  long `schtasks` line is wider than the card, which is why it is `overflow: auto`), the install button 162×38 in
  `rgb(255,139,51)` and the remove button 97×38 in white. The warning callout is `rgb(255,242,232)`.
- The plan survives leaving the tab and coming back: typed `07:15,12:45`, planned, went to AI, came back to Tools,
  and the box still read `07:15,12:45` with the same plan still drawn, exactly one card on the page.
- No console output at all after the whole session: `No console lines yet`.
- `/assets/feat` grew from ten files to fourteen while this was being tested (other agents' files landing). The
  card was re-sampled against the larger set and still came up once, next to `grid`, on a hard load.
- Screenshots of the finished card are outside the repo, under `C:\Users\Asus\Downloads\`: `autopilot-final.png`
  shows the plan drawn (the `Windows` pill, the two-command line, the plan in its `<pre>`, the note line, the warm
  warning callout and the two buttons), `autopilot-final3.png` shows the card at rest, and `autopilot-card2.png`
  shows a refusal sentence sitting under the buttons.

Final state of the mount, read once more at the very end of the session:

```
PeakCut._order includes "autopilot"  -> true
#pcss_autopilot present              -> true
#toolsec children                    -> ["autopilot", "grid"]
.pcauto sections on the page         -> 1
#pcauto_times value                  -> "09:00,18:30"
.pcauto [data-act]                   -> ["pcauto_plan", "pcauto_install", "pcauto_remove"]
console                              -> No console lines yet
```

## The cold-load gap, and what this file does about it

`index.html` paints the Tools tab once, when it opens, and calls `loadTools()`. `plugins.js` only loads the feature
files about 1.4 s after boot. So a hard load of `/app/settings/tools` builds the mount before any feature file has
registered, and every card is missing until the user opens another tab and comes back.

`grid.js` already carries a watch for this. The first version of mine filled in only its own card, which meant that
on a cold load whichever watch ran first won and the other card stayed missing. Measured: `boxes: "autopilot"` at
first, and `grid` only appeared after a tab round-trip. That was my file starving another agent's card.

It now behaves cooperatively, and the two cases are deliberately different:

- **The mount is empty.** Nothing has filled it, so the whole mount is rebuilt with `PeakCut.toolsHtml()` followed
  by `PeakCut.loadTools()`, exactly what `index.html` would have done, and only once `PeakCut._booted` is true so
  that every feature file has registered. Every card comes back, not just this one, so a second watch for the same
  gap finds nothing to do.
- **The mount has other cards but not this one.** Only this card is appended, and nothing already there is touched.

Verified after the change, sampling the page every 500 ms from the moment it loaded:

```
{cards: 2, autos: 1, boxes: "autopilot,grid"}   (stable across all eight samples)
[...toolsec.children] -> ["autopilot", "grid"]
PeakCut.toolSections().map(s => s.name) -> ["autopilot", "grid"]
```

Only two registered features define `tools()` at the time of writing (`autopilot` and `grid`); the other twelve
register acts, keys and hooks with no Tools card, so two boxes is the correct total, not a shortfall. Both cards are
present from the first sample no matter which file registers first, and the plan button still works after the cold
fill (`Runs Monday, Wednesday and Friday at 06:00. That is 1 command for the scheduler.`). Re-checked at the end of
the session, after the feature folder had grown from ten files to fourteen, with the same result: one `autopilot`
box and one `grid` box, both from the first sample.

This is still a work-around inside my own file for a load-order gap in `peakcut/web/plugins.js`, which I do not own.
The proper fix belongs there: either mount the Tools sections lazily when the tab opens, or add `#toolsec` to the
`repaint()` watch list.

## What could not be tested

- **A real install.** The brief says the `{}` POST must be the refusal and nothing should actually be installed, so
  no real `schtasks /Create` was ever run. The success path was exercised against a stubbed `PeakCut.send` that
  returns the documented `{ok, installed: true, schedule: {ran: [...]}}` shape, and the render was checked
  (`pill ok` "Installed" plus the scheduler's line). The real success sentence from Windows would come from
  `schedule.ran[].out` and is printed verbatim, but it has not been seen live.
- **The same for remove.** No real task existed to delete, so the removal success was also stubbed.
- **macOS and Linux.** The box is Windows and the live spec is `platform: "windows"`. `launchd` and `cron` output
  come through the same `schedule.ran[].out` path, so the rendering should be identical, but only the Windows
  command text has been seen.
- **Sign-in on.** The live server runs with sign-in off, so the card was checked as the built-in owner. `install` and
  `remove` call `_admin` first, so with `PEAKCUT_ACCOUNTS=1` a non-operator would get 403 "Only the operator can
  change the schedule on this machine." and that sentence would be shown as-is by the same catch. Not exercised.
- **The 6-per-300 s throttle.** Not triggered, so "The schedule was just changed. Give it a moment." has not been
  seen through the card, though it would arrive through the same path.
- **Narrow screens.** The form wraps below about 500 px (`flex-wrap: wrap`) and `node --check` passes, but the
  window was not resized to look at it.

## Reviewer notes

- The file is self-contained: one IIFE, CSS registered once with `PeakCut.css("autopilot", …)`, one
  `PeakCut.add("autopilot", …)`. No dependency, no global beyond `window.PeakCut`, and it reads `window.ask` only
  behind a type check.
- CSS uses only variables `index.html` already defines at `:root`: `--line`, `--muted`, `--text`, `--dim`,
  `--faint`, `--brand`, `--brand-soft`, `--brand-ink`, `--r-sm`. It deliberately avoids `--bg2` and `--ink`.
  `--bg2` is referenced by the existing `.toolpre` rule but is not actually defined in the palette, which is why
  that rule falls back to transparent; `.pcauto-pre` sets its own `--muted` background instead. No shadow, per
  `AGENTS.md`. No hover rule of its own; the buttons use the page's `.btn` styles unchanged.
- One accessibility addition: `.pcauto .btn:focus-visible { outline: 2px solid var(--brand); outline-offset: 2px }`.
  `index.html` suppresses the default outline on `.btn` but the surrounding field rules do not restore one for
  buttons, so a keyboard user would otherwise have no visible focus ring on these two buttons.
- `prefers-reduced-motion: reduce` turns off transitions inside the card (there are none today; the rule is there
  so a later change cannot quietly add one).
- The status line is `role="status" aria-live="polite"`, so a refusal or a result is announced rather than only
  appearing.
- Nothing in this file throws into the page's click handler: `planTimes`, both writes and the mount fill are all
  wrapped, and every failure paints one quiet line.
- A plan you asked for survives switching Settings tabs, because it is kept in a module-level `last` object and
  re-drawn by `load()`. A bad time clears that memory, so a stale plan can never sit above a new error.
- The times box will accept a value it then rejects, which is intentional: the server would silently substitute
  09:00, and a person who typed `9:00` should be told rather than have a schedule quietly created for the wrong
  hour.
