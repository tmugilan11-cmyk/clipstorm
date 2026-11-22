# menu-icons-check

Wave 4. Adds the missing icons without touching `web/index.html`.

## What I built

`web/feat/icons-extra.js` (169 lines, one plug-in named `icons-extra`).

It publishes three icon paths on `window.PeakCutIcons`, then writes them into the page's own
icon map so the existing `ic()` draws them. The map is the object declared as `const I = {` at
`web/index.html:884`. A feature file is loaded as a plain `<script>` by `web/plugins.js:237-248`,
so it shares the page's global scope and can read that `const` by name. No edit to
`web/index.html` was needed.

How it behaves:

- `seed()` copies each path into the map only when the name is absent. A name that is already
  there is reported as `present` and left alone, so a later wave that adds `refresh` to the map
  wins and this file quietly stops contributing it.
- Every path is checked against `/^[Mm][0-9A-Za-z.,+\- ]*$/` before it goes in. A path that does
  not look like SVG path data is reported as `refused` and not written.
- After seeding it fires `document.dispatchEvent(new Event("peakcut:render"))` so the sidebar
  repaints once. There is no observer, no timer, no polling.
- The Tools card lists each name with its state (added / already present / refused) and one
  plain-English line underneath. It draws the previews with `createElementNS`, so no icon name
  is ever pasted into markup. The "Check again" button re-runs the check and toasts the count.
- If the Tools card cannot read the map it shows one sentence saying so. It never swallows the
  failure.

## Icon audit

Every name below was collected from `web/feat/*.js` (as `ic("...")` or `icon: "..."`) and from
`web/index.html`, then diffed against the 58 keys of the map at `web/index.html:884-943`.

48 names are referenced. 45 are present. **3 are missing.**

| Icon name | Used by | Present or missing |
|---|---|---|
| bolt | `web/feat/learn.js`, `web/feat/menu-pages.js` | present |
| caret | `web/feat/analytics-table.js` | present |
| chart | `web/feat/analytics-retention.js`, `web/feat/analytics.js`, `web/feat/usage.js` | present |
| check | `web/feat/analytics-trends.js`, `web/index.html` (9 uses) | present |
| clock | `web/feat/analytics-realtime.js`, `web/feat/schedule.js` | present |
| cog | `web/feat/creators.js`, `web/feat/menu-pages.js`, `web/feat/schedule.js` | present |
| copy | `web/feat/schedule.js` | present |
| film | `web/feat/analytics-table.js`, `web/feat/creators.js`, `web/feat/formats.js` | present |
| folder | `web/feat/menu-pages.js` | present |
| microphone | `web/feat/menu-pages.js` | present |
| palette | `web/feat/menu-pages.js` | present |
| plug | `web/feat/menu-pages.js` | present |
| plus | `web/feat/analytics-trends.js`, `web/feat/schedule.js` | present |
| plusc | `web/feat/creators.js` | present |
| radio | `web/feat/sounds.js` | present |
| trash | `web/feat/schedule.js` | present |
| user | `web/feat/creators.js`, `web/feat/menu-pages.js` | present |
| video | `web/feat/live.js` | present |
| wand | `web/feat/menu-pages.js` | present |
| x | `web/feat/analytics-trends.js` | present |
| arrowr, bell, chat, down, eye, github, globe, instagram, link, menu, minus, play, receipt, scissors, send, shield, sidebar, signout, sliders, stop, up, upright, warn | `web/index.html` only | present |
| film_f, home_f | `web/index.html:945`, the filled twins `navIc` asks for on the Formats and Home rows | present |
| **refresh** | `web/index.html:2576`, the Refresh button on the Zernio card | **missing, now supplied** |
| **check_f** | `web/index.html:1297`, the filled twin `navIc("check", "review")` asks for | **missing, now supplied** |
| **grid** | `web/plugins.js:98`, the default for a menu page that names no icon | **missing, now supplied** |

Notes on the three:

- `refresh` drew an empty `<svg>` before this file, so the Zernio Refresh button had a gap where
  its icon belongs and the word "Refresh" only.
- `check_f` is the filled version of `check` for the Review row. `navIc` at `web/index.html:945`
  reads `I[n + "_f"]` and falls back to the outline drawing, so the Review row looked stale while
  Review was the open page. `film_f` and `home_f` were already in the map; `check_f` was not.
- `grid` is not in the map, so any wave-4 menu registration written without an `icon` drew a menu
  row with no picture at all. `plugins.js:98` asks for `"grid"` before its own guard, and the guard
  sees the name is absent and returns an empty string.

Also worth knowing: 14 names in the map are never asked for (bug, bulb, chart_f, cog_f, crown,
film_f, home, home_f, lock, money, pause, play_f, rec, rec_f, users). They cost nothing and are
left in place.

## Routes it reads

None. This file makes no network request. It reads the page's icon map and writes strings into
it, so there is no route to name and nothing that can fail over the wire.

## What it cannot do yet

1. **It cannot make `ic()` look at `window.PeakCutIcons`.** The function at `web/index.html:944`
   is `${I[n]}` and nothing else. What this file does instead is put the paths into `I`, which any
   file loaded after `index.html` can reach. The fallback the brief asked for (`ic()` reading
   `window.PeakCutIcons` when `I[n]` is absent) still needs one line in `web/index.html`. If a
   later wave wants it, the exact addition is, at `web/index.html:944`:

   ```js
   const ic = n => `<svg viewBox="0 0 256 256" aria-hidden="true">${I[n] || (window.PeakCutIcons || {})[n] || ""}</svg>`;
   ```

   That line is not applied. It is a suggestion for whoever owns that file.

2. **It only works for files loaded after it.** `plugins.js` injects the feature files in the
   order `/assets/feat` returns, and this file is one of 47. Any markup drawn before its script
   runs keeps the empty icon until the page repaints. The `peakcut:render` event it fires covers
   the normal case; a menu row drawn earlier in the same tick is fixed by that repaint, not before
   it.

3. **It cannot fix an icon that is drawn with a name nobody registered.** If a future feature
   file calls `ic("something-new")` and no file supplies it, the button is still blank. Nothing
   here can guess a picture for a name.

4. **The drawing is my own.** The three paths are 256x256 outline shapes in the same style as the
   rest of the map (stroke-free filled paths, since `ic()` emits no stroke attributes). They are
   not copies of a licensed icon set, but they are also not reviewed by a designer.

## Commands run, with results

```
$ node --check web/feat/icons-extra.js
JS OK

$ grep -n '—\|–' web/feat/icons-extra.js
(no output: no em dash, no en dash)

$ python tests/test_feat_files.py
...
{"files": 47, "checks": 382}
All checks passed.

$ python tests/test_menu_pages.py
ok   live.js draws its page
ok   menu-pages.js draws its page
ok   schedule.js draws its page
ok   sounds.js draws its page
ok   usage.js draws its page

1 check(s) failed
  - creators sits under a known heading
```

The one failing check in `tests/test_menu_pages.py` is `creators sits under a known heading`. It
comes from `web/feat/creators.js`, which is another agent's file and which this task never
opened for writing. `icons-extra.js` registers no page at all, so it cannot affect that check.

Browser checks against the running app at `http://127.0.0.1:8798/app`, after this file loaded:

```
typeof window.PeakCutIcons === "object" && !!window.PeakCutIcons.refresh && ic("refresh").includes("<path")
-> PASS

["refresh","check_f","grid"].every(n => I[n] && I[n] === '<path d="' + window.PeakCutIcons[n] + '"/>')
-> PASS

(() => { const d = document.createElement("div"); d.innerHTML = ic("refresh");
         const p = d.querySelector("path"); return p.getAttribute("d").startsWith("M128,32A96,96"); })()
-> PASS

ic("check_f").includes("M60,150L112,202") && ic("grid").split("<path").length === 2
  && (ic("grid").match(/Z/g)||[]).length === 4
-> PASS

window.PeakCut._order.includes("icons-extra") && !!window.PeakCut["icons-extra"].tools
-> PASS

(() => { const old = S.view; S.view = "review"; const out = navIc("check","review");
         S.view = old; return out.includes("M60,150L112,202"); })()
-> PASS   (the Review row now picks the filled twin when Review is open)
```

Two earlier probes of mine failed and are worth recording so nobody repeats them:

- `!!window.PeakCut.iconsExtra` is `false`. The plug-in is stored under its literal registered
  name, so the property is `window.PeakCut["icons-extra"]`. The camelCase name does not exist.
- `Object.keys(I).length === 61` was my wrong guess. Inside the live page the map holds 75 keys,
  because `web/feat/menu-icons.js` (another wave-4 file) also adds to it at load. The count is not
  a stable number and should not be asserted.
