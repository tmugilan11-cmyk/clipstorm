# Wave 1 review: the menu and the analytics pages

Author: agent-34, the fixer. The reviewer slot (child 16, agent-33) never produced this file, so the lead asked
the fixer to review the work as well as fix it. This is the same thing that happened in swarm3, where
`docs/swarm3/REVIEW.md` opens the same way. Everything below was checked against the files as they stand, not
against the plan.

## How this was checked

Eight questions, in the order the lead set them. Every one was answered by reading the file, or by running it,
not by looking at it and guessing.

1. Does the file parse, and does it register exactly one plug-in named after itself?
2. Does every string that reaches the page go through `esc(`?
3. Does it invent an `id` that would clash with `web/index.html`?
4. Does every `data-act` it binds have a real handler?
5. Does every address it fetches exist in `studio/*.py`?
6. Does a failure reach the person as a sentence, or is it swallowed?
7. Does it carry an absolute `http://127.0.0.1` or `http://localhost` origin?
8. Does it write into `#sform`, or call `drawSettings()` in a way that fights the page?

Also run: `node --check` on all thirteen wave-1 feature files and on `web/plugins.js`.

## What was right

All thirteen files parse. All thirteen register exactly one plug-in named after their own file
(`analytics`, `analytics-kpi`, `analytics-charts`, `analytics-table`, `analytics-audience`, `analytics-traffic`,
`menu`, `menu-pages`, `menu-icons`, `nav-search`, `nav-responsive`, `page-guard`, `settings-explain`).
`web/plugins.js` parses.

Every fetched address is a real route in `studio/`: `/api/analytics/summary`, `/api/analytics/timeseries`,
`/api/analytics/videos`, `/api/analytics/audience`, `/api/analytics/traffic`. No file carries an absolute origin.
No file invents an `id` that clashes with `web/index.html`. No file calls a bare helper through `window.` — they
are all called as plain names.

Every server-supplied string that reaches markup is wrapped in `esc(`. The values left unwrapped are numbers,
SVG geometry, and string constants that never leave the file. Two worth naming because they look wrong and are
not: `analytics-kpi.js` prints `${v.tail || ""}` unescaped, but `tail` is only ever set to the literal
"Reload this page to try again."; and `analytics-kpi.js` passes `c.title` into `head()`, which escapes it when it
writes the column. `nav-search.js` writes its box with a static string and never echoes the typed query into
markup. `settings-explain.js` and `page-guard.js` use `textContent`, so nothing they add can become markup.

Failures do reach the person. `analytics-kpi.js` says "The summary could not be read" and adds why, plus
"Reload this page to try again." `analytics-table.js` keeps an error on the box and prints "Could not load the
video numbers" with a Try again button. `analytics-charts.js` and `analytics-traffic.js` each save the reason and
print a sentence. When a whole page's `load()` rejects, `web/plugins.js` toasts "That page could not finish
loading." The `catch` blocks that return `""`, `null` or `false` are formatters and parsers, where the fallback
is the answer, not a swallowed failure.

No file writes into `#sform` and no file calls the page's `drawSettings()`. `settings-explain.js` only reads
`document.getElementById("sform")` to watch it, and both it and `style-tiles.js` merely *define* a
`drawSettings(root)` for the `after` hook, which is the sanctioned mechanism. That is correct and was left alone.

`menu-pages.js` draws the real form through `drawSettingTab(d.tab, box)` and hands the promise back, so the paint
hooks run after the form exists. Its owner-only page checks `state.status.user.is_admin`, which `studio/auth.py`
really sends. I looked for a reason to call any of this a defect and did not find one.

## Findings

### Critical

**C1. `refreshHost()` calls itself forever. In `web/index.html:2443-2447`. NOT FIXED — this file is frozen.**

```js
async function refreshHost() {
  if ($("#sform")) return refreshHost();
  if (window.PeakCut && PeakCut.hasPage && PeakCut.hasPage(S.view)) return PeakCut.drawPage(S.view);
  return refreshHost();
}
```

All three branches re-enter the function. The middle line, which is the only one that does anything, can never
run: `#sform` is created whenever the settings view is drawn, so the first branch always fires first.

Proved, not assumed. I copied the body out to a scratch file, gave it a `$` that answers `{id:"sform"}` for
`"#sform"`, and ran it. The result was `RangeError: Maximum call stack size exceeded`.

It is reachable. `web/index.html:1403` creates `#sform` when the settings view is drawn, and that is the only
place the id is created. Seventeen places call `refreshHost()`: `web/index.html:3026, 3109, 3113, 3121, 3123,
3124, 3128, 3130, 3139, 3145, 3151, 3163, 3166, 3171`, plus the definition and its own internal calls. Those are
the sixteen save handlers the lead changed from `return drawSettings()`. So saving anything on the Settings page
throws instead of redrawing.

The correct line is `if ($("#sform")) return drawSettings();` — the other two branches are already what you want
to do when there is no settings form on screen. I did not make that change, because this wave's contract freezes
`web/index.html` and the lead owns those sixteen handlers. **This one needs the lead to apply it.**

### Important

**I1. The menu spine did not know the "Set up" heading. In `web/feat/menu.js:16`. FIXED.**

`menu-pages.js` puts five pages under `group: "Set up"` (tools, apps, ai, storage, account). The spine's list of
headings had no "Set up" in it, and `rank()` returns 500 for a heading it does not know, so `pageRows()` sorted
all five to the bottom of the menu, under Help.

One thing to be clear about: the sidebar a person actually sees did not have this bug. The live nav is
`PeakCut.navHtml()` in `web/plugins.js`, which groups rows by the group string itself and never consults this
list. The spine's `pageRows`, `menuGroups` and `groupFor` currently have no callers outside their own file, so
this was a latent fault — it would have surfaced the moment anything started reading the spine. Fixed anyway,
because a registry that disagrees with itself is a trap for the next file that leans on it.

The fix is one entry: `["Set up", 35]`, which sits between "Look and sound" (30) and "Connect" (40). It has to
be below 40: `navHtml` orders headings by the smallest page order beneath them, and tools/apps sit at 30 and 40,
so a "Set up" of 50 would print the group after Connect in the real sidebar. At 35 the spine and the sidebar
agree. Verified by loading the file and printing `pageRows()`: the five pages now come out under "Set up", in
order, between "Understand" and the rest.

## Left alone on purpose

These looked like findings and are not. Recording them so nobody re-reports them:

- Nine `data-act` values in other files (`joblog`, `pcauto_install`, `pcauto_plan`, `pcauto_remove`,
  `pcgridrefresh`, `pchistkeep`, `pcstatsread`, `peektake`, `pickstyle`) do have handlers. My first check missed
  them because it only matched `act: { name() {` and not the method-shorthand or arrow-value forms. No wave-1
  file emits a `data-act` at all; `nav-responsive.js` only *reads* `[data-act="collapse"]`, which
  `web/index.html` handles.
- `nav-search.js` hides rows with the `hidden` attribute, and `web/index.html:22` has
  `[hidden]{display:none!important}`, so it works even though `.nav-item` is `display:flex`.
- `menu-icons.js` checks path data against `/^[Mm][0-9A-Za-z.,+\- ]*$/` before it reaches the page, so an icon
  cannot inject markup.
- The `catch` blocks that return a fallback are formatters, parsers and observer feature-detection. Failures that
  matter are all printed.
- The four shape changes the lead made (the `drawSettingTab` split, the promise hand-back, the `runAfter` hook,
  `refreshHost` replacing `drawSettings` in the save handlers) are in place and were not reverted. C1 is the one
  defect inside that work.

## Gates

Run after the fix:

```
python tests/test_feat_files.py
{"files": 28, "checks": 230}
All checks passed.

python tests/test_menu_pages.py
All checks passed. 133 ok
```

`node --check` passes on all thirteen wave-1 feature files and on `web/plugins.js`.

## Count

One Critical, one Important. One fixed (`menu.js`), one escalated (`index.html`, frozen).
