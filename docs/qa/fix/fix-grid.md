# Fix report: web/feat/grid.js

Fixer agent-171, fix wave for PeakCut. One file owned: `web/feat/grid.js`.
Findings read from `docs/qa/FINDINGS.md` ("## web/feat/grid.js"), evidence checked
against the audit `docs/qa/audit/tools-schedule.md` before any change.

## Files

| File | Role |
|---|---|
| `web/feat/grid.js` | The only file this fixer owns and changed |

`web/index.html` was not edited (the lead owns it). The server was not restarted or killed.

## Finding 1 (critical): the "This week" card could never appear

**The finding.** The card mounted itself into `#toolsec` on the Settings > Tools page.
That mount no longer exists, so the card was unreachable from anywhere in the app.

**Evidence, verified before fixing.**

- `grep toolsec web/index.html` returns 0 matches: the mount is gone.
- The Tools page is now hand-written markup in `toolsPage()` (web/index.html:2363-2372),
  and the comment above it (web/index.html:2362) says "Tools contains scheduling only.
  Developer diagnostic cards must not mount here." The lead will not re-add `#toolsec`,
  so grid.js had to find a different home; waiting for the lead was not an option.
- The old code worked around the gap anyway: `remount()` (grid.js, former lines 139-150)
  tried to fill `#toolsec` every visit, `watchMount()` (former 152-159) polled for seven
  seconds, and a bootstrap (former 194-197) started the watch. All three were dead code
  once the mount disappeared.

**The fix.** The card is now a page of its own, the way every other read-only summary
reaches the person. `PeakCut.page("week", {...})` puts a "This week" row in the main
menu under the "Understand" heading, serves it at the address `/app/week`, and draws the
same card the Tools tab used to (heading, help text, Refresh button, the day grid and
the waiting queue). This path is documented (AGENTS.md, "A menu page is also a feature
file") and machine-checked (`tests/test_menu_pages.py`), so it cannot silently break the
way the Tools mount did.

What was removed: `remount()`, `watchMount()`, the bootstrap that ran them, and the
`tools()` method on the plug-in. What was kept: `PeakCut.add("grid", ...)` (one plug-in
named after the file, with the `pcgridrefresh` action), `draw()`, `paint()`, `body()`
and all helpers. `paint()` still writes only when `#pcgrid` is on the page, so a draw
that finishes after the person navigates away returns quietly.

Details of the registration: `nav: "This week"` (9 characters), `icon: "chart"` (in the
page's icon map), `path: "week"`, `group: "Understand"`, `order: 21` (between analytics
at 20 and Improve at 22, both summaries of the same numbers). The heading is now
`h1.pcgrid-h` (23px, page-title size, matching the other plugin pages) instead of the
old card `h2`.

**Proof.** `tests/test_menu_pages.py` passes with the page registered (439 checks ok):
"week says what to call it", "week says where it lives", "week has a one-line tip",
"week has a group", "week has an icon the page knows (chart)", "week sits under a known
heading (Understand)", "grid.js draws its page", "no two pages share an address",
"no two pages share a name", "week does not take a built-in address",
"week does not shadow a feature file".

## Finding 2 (minor): the waiting list was drawn in the wrong order

**The finding.** The comment said the list showed "the order the queue runs in", but the
code sorted descending by `due_at`, so the row on top was the last post to go out, not
the next one. The server queue is sorted ascending by `due_at`
(studio/posting.py:273: `queue = sorted((p for p in _posts if p["status"] in OPEN), key=lambda p: p["due_at"])`).

**The fix.** The sort now ascends, matching the queue:

```js
const waitingAll = posts.filter(p => p && WAITING.has(String(p.status || "")))
  .sort((a, b) => (Number(a.due_at) || 0) - (Number(b.due_at) || 0));
```

The comment was rewritten to say what is true now, and every "newest first" phrase in
the file (header comment, sort comment, help text) was changed to "soonest out first",
so the code, the comment and the help text all describe the same order.

**Proof.** `node --check web/feat/grid.js` exit 0; the comparator in the file now reads
`(Number(a.due_at) || 0) - (Number(b.due_at) || 0)`; `grep newest` over the file returns
0 matches.

## Finding 3 (minor): the zero-day bar floor was invisible

**The finding.** The 2px floor under an empty day was drawn in `var(--line-2)` (#2A2A2A)
on the day panel background `var(--muted)` (#111111). Measured (Python, WCAG
(L1+0.05)/(L2+0.05)):

| Candidate | On #111111 (day panel) | On #2A1B10 (today panel) |
|---|---|---|
| #2A2A2A (current, var(--line-2)) | 1.32:1 | 1.16:1 |
| #666666 | 3.29:1 | 2.90:1 |
| **#6B6B6B (chosen)** | **3.54:1** | **3.12:1** |
| #7C7C7C | 4.52:1 | 3.98:1 |
| #A3A3A3 (var(--dim)) | 7.49:1 | 6.59:1 |

The 3:1 non-text minimum (WCAG 1.4.11) is failed at 1.32:1, and the today panel ground
(#2A1B10) is where the bar actually sits on the current day, so the colour must pass
there too. #666666 passes on one ground but not the other.

**The fix.** `.pcgrid .bar.zero{background:#6B6B6B}` with the measured numbers in a
comment beside the rule: 3.54:1 on the day panel, 3.12:1 on the today panel, above the
3:1 minimum on both grounds, and clearly quieter than a filled bar (#FF8B33 measures
8.09:1), so an empty day still reads as quieter than a full one.

**Proof.** The measurement table above was produced by the Python script in this
session (exit 0); the rule in the file now reads `background:#6B6B6B`.

## Gates run

| Gate | Result |
|---|---|
| `node --check web/feat/grid.js` | exit 0 |
| `python tests/test_feat_files.py` | 606 checks, all pass, exit 0 (grid.js parses, declares one plug-in named after itself, is the only owner of grid, escapes what it draws, uses no absolute origin, invents no clashing id, draws only fixed markup, draws its page) |
| `python tests/test_text_ink.py` | 10 ok, exit 0 |
| `python tests/test_menu_pages.py` | 439 ok, exit 0, week page registered and valid |

## Skips

None. All three findings held up against the code and were fixed.

## Note for the lead

The card now lives at `/app/week` and no longer mounts into Settings > Tools. Nothing in
`web/index.html` needs to change for it; the page registers itself through the same
plugin loader the other 20 pages use, and `tests/test_menu_pages.py` now counts 21 pages.
No Python route was touched, so no restart is needed for this file.
