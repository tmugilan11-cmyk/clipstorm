# Wave 4: Help page

Agent: agent-76. Slug: `help`. File created: `peakcut/web/feat/help.js` (145 lines, 9.4 KB). Skill loaded first: **frontend-design**.

## What I built

A main-menu page called **Help**, in the group **Set up**, at order 80, at the address `/app/help`.

It answers six questions a first-run person really asks, each folded into a `<details>` so the page stays
short. Opening one shows 2 to 4 sentences of plain English and, because every one of the six answers ends on a
setting, one button that goes to the page holding it plus a `.hint` line saying what will be found there.

| Question | Answer is about | Button goes to |
|---|---|---|
| Where do clips come from? | Add a video first; speech, moments, then the cutter | `/app/videos` (All videos) |
| Why is nothing posting? | The four gates plus the one pause switch | `/app/apps` (Connected apps) |
| What does an Improve round actually change? | The five settings it may touch, and the dry run | `/app/improve` (Improve) |
| What does it cost? | Tokens, not money; no price is printed anywhere | `/app/ai-usage` (Usage) |
| What happens to my videos? | They stay on this machine; deleting removes the folder | `/app/storage` (Storage) |
| How do I make it run by itself? | The schedule text, the two-press Install, the Live watch list | `/app/schedule` (Schedule) |

Every sentence is a statement about behaviour that already exists in the code, so none can drift out of date
with a number:

- The four posting gates and `REVIEW_FIRST` come from `studio/posting.py` (`on_clip_ready` at line 96, the flag
  at line 27).
- The five settings an Improve round may change are `STYLE`, `HOOK`, `LENGTH`, `MOOD`, `COUNTER` in
  `studio/learn.py:33-39`; `_allowed` drops a proposal outside the accepted values.
- The cost answer follows `studio/usage.py:52`: `brief()` counts calls and tokens and records no money.
- The delete answer follows `studio/jobs.py:408`: `delete()` does `shutil.rmtree(job["dir"])`.
- The schedule answer follows `studio/autopilot.py:46`: `install()` refuses without `confirm=True`.

## Routes it reads

**None.** This page makes no fetch at all. It is static copy plus plain `<a href="/app/...">` anchors, which is
why there is no loading state, no error state and nothing that can show a stale number. `grep` on the file for
`api(`, `send(` and `fetch(` returns 0 for each.

The one listener in the file upgrades a click to `go(name)` only when `fromPath()` yields a name that
`PeakCut.hasPage()` confirms; otherwise it lets the browser follow the `href`. That keeps the address bar, the
menu highlight and a reload in step, and means a missing page is a real 404 instead of a silent landing on Home.

## Design notes

- Folded rows are hairlines (`--line`), not cards, so the page reads as one list rather than six boxes. The open
  answer sits against a 2px `--brand-line` rule, which is the only colour on the page.
- The caret is the frame's own `ic("caret")`, rotated 180 degrees on `[open]`. `prefers-reduced-motion` is
  already handled globally by `index.html:824`, so the transition simply stops.
- Questions use `<h2>` inside `<summary>`. That is valid and gives a screen reader heading navigation through the
  six questions even while the answers are folded.
- `.hint` is hidden on phones by the frame; this file re-shows `.hlp-hint` under 560px because those sentences
  are the "where to go" text, not decoration.
- No shadow, no new colour, no emoji, no em dash. ASCII only (verified: zero non-ASCII code points).

## What it cannot do yet

- **The `help` icon is registered at runtime, not in `index.html`.** `web/feat/menu-icons.js:92` adds the path to
  the live icon map. Early in this run that made the check fail, because `tests/test_menu_pages.py:45` scraped
  icon names from `index.html` alone. The test has since been widened (lines 54 to 76 now also read
  `PeakCut.icon(...)` calls and `icons:`/`SET:` maps out of the feature files), and the check now reads
  `ok help has an icon the page knows help`. Nothing in `help.js` needed to change for it. If that widening is
  reverted, this row fails a test this file cannot fix, because the icon source is not mine to edit.
- No search over the questions, no anchor per question (so a single answer cannot be linked to from elsewhere),
  and no "open all". Each of those would need ids, and ids in this file are checked for clashes with
  `index.html`.
- It does not read the machine it is running on, so it cannot say "you have no account connected" in the answer
  to the posting question. It points at Connected apps instead of guessing. That is deliberate: a help page that
  states a number has to fetch one, and a wrong one is worse than none.
- The copy is written in English only. There is no translation layer in this app yet.

## Exact commands run, with results

Run from `C:\Users\Asus\Documents\deepseek-harness\default-workspace\peakcut`.

```
node --check web/feat/help.js
  -> JS OK

python tests/test_feat_files.py
  -> {"files": 47, "checks": 382}
  -> All checks passed.

python tests/test_menu_pages.py
  -> 17 help-related checks ok, including:
       ok   help.js parses
       ok   help has an icon the page knows   help
       ok   help sits under a known heading   Set up
       ok   help does not shadow a feature file   help
       ok   help.js draws its page
       ok   the Help row is in the menu
       ok   Help row points at a feature file that exists   help.js
       ok   help.js escapes what it puts in markup
  -> 8 check(s) failed, none of them in help.js:
       Usage row's file registers its page
       analytics-traffic.js escapes the server fields it names
       filters.js escapes what it puts in markup
       icons-extra.js escapes what it puts in markup
       keys.js escapes what it puts in markup
       menu-icons.js escapes what it puts in markup
       nav-search.js escapes what it puts in markup
       stage.js escapes what it puts in markup
```

ASCII check over the file: `non-ascii chars: none`, `em dash: False`, `en dash: False`, `bytes: 9343`.
Fetch check: `api(` 0, `send(` 0, `fetch(` 0.

Served check against the running test server (port 8798, not restarted):

```
curl -s http://127.0.0.1:8798/assets/feat        -> 47 files, help.js present
curl -s -o /dev/null -w '%{http_code}' \
     http://127.0.0.1:8798/assets/feat/help.js  -> 200
```

Browser check of the drawn page at `http://127.0.0.1:8798/app/help`: heading, lede, six folded questions, six
buttons and six hints all render; clicking a question opens its answer and flips the caret; clicking
"Connected apps" moves the address to `/app/apps` without a reload.

## For the four wave-2 fixes and for the lead

Not mine and not touched, but seen while running the suite:

1. `tests/test_menu_pages.py` still reports **"Usage row's file registers its page"** failing for `usage.js`.
   That is the same class of defect as the icon check I hit: the test looks for a registration the file makes in
   a shape it does not parse. Whoever owns `usage.js` should read the test's regex before changing the page.
2. The seven `escapes ...` failures listed above are all in files owned by other agents in this wave
   (`filters.js`, `icons-extra.js`, `keys.js`, `menu-icons.js`, `nav-search.js`, `stage.js`,
   `analytics-traffic.js`). Worth one more pass before the wave is called done, since that check is what stops a
   server value reaching markup raw.
