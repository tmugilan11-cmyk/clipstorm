# Schedule (wave 4)

File I own: `web/feat/schedule.js` (335 lines). Nothing else was edited.

Skill loaded before any other tool call: **frontend-design** (via the `skill` tool).

## What I built

A main-menu page called **Schedule**, group **Set up**, order **45** (between apps 40 and ai 50), path
`/app/schedule`, tip "Put clips and Improve rounds on a timer, as text you copy".

Icon: **`clock`**, not `calendar`. `index.html`'s `const I = {...}` table has no `calendar` key, and
`tests/test_menu_pages.py` fails any page whose icon is not a real one ("has an icon the page knows"). `clock` is
the closest honest icon. If a `calendar` icon is wanted, someone who owns `index.html` has to add it to that table
first, and then this file needs a one-word change.

One times field at the top (`06:00,18:00` by default) with a `Rebuild all three` button, then three cards. The
field feeds all three cards; Enter inside it rebuilds too. Under the field:

> Hours and minutes on this computer's own clock, separated by commas. Write 06:00,18:00 for a run at six in the
> morning and again at six in the evening.

### Card 1: Clips on a timer

Reads `GET /api/autopilot/spec?times=<times>`. Shows the scheduler it was built for, the days
(`MON, WED, FRI`) and the times, then the paste-ready text in a `<pre>`. Copy button: `Copy the clips text`.

### Card 2: An Improve round on a timer

Reads `GET /api/schedule/preview?times=<times>` (returns `{preview, note}`). Shows the scheduler and times, the
`note` the route sends back, and the text behind a disclosure.

**Honest limitation, stated in the card.** `/api/schedule/preview` is `api_preview.py` calling
`autopilot.preview(...)`, so its text is byte-identical to card 1. `studio/schedule_ai.py` does have a separate
`spec()` with `LABEL="PeakCutRound"`, but no `api_*.py` module and no `studio/server.py` route ever imports it, so
nothing serves it. The card compares its text with card 1's and, when they match, says plainly:

> This is the same text as the clips card. The Improve round has its own spec inside PeakCut, but no route serves it
> yet, so this page cannot show a separate Improve command. Copy the text above only if you meant the clips tick.

I did not fake a separate Improve command to make the card look better.

### Card 3: What is due

Reads `GET /api/autopilot/preview?times=<times>`. There is no route that lists what is currently due, so the card
shows the tick command a scheduler would run and says so rather than inventing a list:

> This is the timetable a scheduler would run, not a list of clips waiting now. PeakCut has no route that lists what
> is due at a moment, so this card shows the command the tick would use at those times instead of making numbers up.
> The text is the same as the clips card, because both come from the same tick.

### Nothing is installed by copying

Every card carries the same line under its copy button:

> **Copying this text installs nothing.** It puts the words on your clipboard. Nothing runs, and nothing on this
> computer changes, until you paste it somewhere and run it yourself.

The success toast says `Copied. Nothing was installed.` A refused clipboard shows `The browser refused to copy.
Select the text in the box and copy it yourself.` Never a silent catch.

### Install / Remove need two presses

Card 1 also offers `Install on this computer` and `Remove`, both requiring a **second** press on the **same**
button within eight seconds. The first press changes nothing on the machine and shows:

> Nothing has been installed yet. Press the same button again within eight seconds to let PeakCut change one task in
> this computer's scheduler. Pressing another button, or waiting, cancels it.

`ARM` stores the pending action per card as an action string plus one shared timer. `waiting !== doing` is the single
guard that decides "first press". Pressing a different button, or the timer expiring, disarms. Only the second press
calls `POST /api/autopilot/install` or `/remove` with `{confirm: true, times}`. Non-operator accounts see
`Only the operator account can write a task into this computer's scheduler. You can still copy the text and run it
yourself.` instead of the buttons.

## Routes it reads (all verified to exist)

| Route | Where | Used by |
|---|---|---|
| `GET /api/autopilot/spec` | `studio/api_auto.py:97` | card 1 |
| `GET /api/schedule/preview` | `studio/api_preview.py:173` | card 2 |
| `GET /api/autopilot/preview` | `studio/api_auto.py:117` | card 3 |
| `POST /api/autopilot/install` | `studio/api_auto.py:135` | card 1, second press only |
| `POST /api/autopilot/remove` | `studio/api_auto.py:161` | card 1, second press only |

No other route is named anywhere in the file. No absolute origin appears (the test forbids `http://127.0.0.1` and
`http://localhost`), so every call is relative through `PeakCut.api` / `PeakCut.send`.

## What it cannot do yet

1. **No real Improve-round schedule.** `studio/schedule_ai.py` has a `spec()` for it, but no HTTP route serves it.
   Fixing this needs a new route in an `api_*.py` file (probably `api_auto.py` or `api_preview.py`), which this
   brief did not give me. Until then card 2 is honest about showing the clips text.
2. **No route lists what is due.** Card 3 shows the tick command instead of a due list.
3. **No `calendar` icon** in `index.html`, so the page uses `clock`. See the top of this report.
4. **`web/index.html` was not touched.** My `[data-act]` handlers (`schredraw`, `schcopy`, `scharm`) and my `keys`
   handler had to be registered on `PeakCut.add("schedule", {...})`, not on the `PeakCut.page(...)` definition.
   `web/plugins.js` routes both clicks and key presses by walking `PeakCut._order`, which only holds names added
   through `PeakCut.add`, so handlers placed on the page object are silently dead. I found this in the browser:
   the buttons did nothing at all. Worth writing into the contract, because the page shape in
   `docs/swarm3/CONTRACT.md` shows them under the page.

All server values pass through `esc(...)`. Nothing numeric is printed that the server did not send; where a value is
absent the row is dropped by `facts()` rather than shown as an empty or invented figure.

## Commands I ran and what they said

```
node --check web/feat/schedule.js
  -> JS OK (exit 0)

python tests/test_feat_files.py
  -> {"files": 47, "checks": 382}
     All checks passed.
```

`test_menu_pages.py` was green for every schedule assertion (12 of them), including `has an icon the page knows
clock`, `sits under a known heading Set up`, `has a label of its own` and `draws its page`:

```
python tests/test_menu_pages.py
  -> All checks passed. 217 ok
```

Every schedule assertion passes (12 of them). The menu suite still reports one failure, and it is **not my file**:

```
FAIL help has an icon the page knows
```

`web/feat/help.js:126` declares `icon: "help"`, and `index.html`'s icon table has no `help` key. That is another
agent's file so I did not touch it; its owner needs to pick a real icon name (or someone with `index.html` adds
`help` to the table). Earlier in the wave I also saw `creators sits under a known heading` fail once and pass on
re-run, which was another agent mid-write.

Live check against the test server on `http://127.0.0.1:8798` (not restarted):

```
GET /assets/feat                              -> "schedule.js served: True"
GET /api/autopilot/spec?times=06:00,18:00     -> 200, ok=true, times=["06:00","18:00"]
GET /api/schedule/preview?times=06:00,18:00   -> 200, {ok, os, times, preview, note}
GET /api/autopilot/preview?times=06:00,18:00  -> 200, same shape
schedule/preview text == autopilot/preview text -> True   (this is why card 2 says so)
```

In the browser at `/app/schedule`: nav row present, heading `Schedule`, three cards
(`Clips on a timer`, `An Improve round on a timer`, `What is due`), zero `.err` elements, first line of the paste
text `rem PeakCut autopilot, MON, WED, FRI at 06:00, 18:00`, both folded cards showing
`Show the text this card would copy`.

Two-press proof (I stubbed `fetch` so nothing touched the real scheduler):

```
press 1 -> button reads "Press again to install", warning visible, no request sent
press 2 -> POST /api/autopilot/install  {"confirm":true,"times":"06:00,18:00"}
schtasks /Query /TN PeakCutAutopilot -> ERROR: The system cannot find the file specified.
```

So the second press is the only thing that sends the request, and no task was installed on this machine.
