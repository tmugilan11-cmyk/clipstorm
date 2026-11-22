# menu-icons

## What I built

The extra icons the new menu rows need, added without touching the frozen page.

The page keeps its icon map and its `ic()` as bare `const`s inside its own script. A `const` binding
cannot be wrapped or replaced from a feature file. Its contents can still be written to, though, and
`web/plugins.js:74-91` already reads that map by bare name when it draws the menu:
`const icons = typeof I === "object" && I ? I : {};` then `const draw = (n) => (typeof ic === "function" && icons[n] ? ic(n) : "")`.
So writing `I[name] = '<path d="..."/>'` is enough for a menu row to show it. No change to the page.

Three things are on `PeakCut`:

- `PeakCut.icon(name, d, box)` remembers one path and also puts it in the page's live map, so the menu
  can draw it. It returns true when it accepted the path and false when it did not.
  `box` is the width of the viewBox and defaults to 256. A non-256 box is kept here but not written
  into the page's map, because `ic()` hardcodes `viewBox="0 0 256 256"`.
- `PeakCut.iconHtml(name)` returns one icon as markup, in the same shape `ic()` returns. An unknown
  name gives an empty svg rather than a broken tag.
- `PeakCut.iconNames()` lists every name that can be drawn right now, ours and the page's together.

**A page that needs a new icon must call `PeakCut.icon(...)` once, at load, before it registers with
`PeakCut.page`.** The menu is drawn from the page's map, so a name that is only stored here will not
appear in the left menu. The fourteen built in below are already registered by this file, so those
work the moment this file loads.

The fourteen names: analytics, hook, pipeline, ai, report, audience, traffic, search, filter,
calendar, clock-extra, help, star, sparkle.

Each is one path on the page's 256 grid, filled and not stroked, at the weight of the icons already
there. Holes are made the way the page's own icons make them: an inner subpath wound the other way
against the default nonzero fill. Nothing here sets a fill-rule, so these behave like the icons
beside them. I checked every hole by parsing the paths back and measuring the signed area of each
subpath. The holes in report, calendar, clock-extra, help and search are all opposite-wound to their
body. The rest are separate solids, which never cancel.

The plug-in body is deliberately inert: no Tools card, no click handler, no keys. Settings keeps only
settings. These names exist for menu rows to draw with.

## The file I own

`web/feat/menu-icons.js`, 103 lines. One plug-in, `menu-icons`. I touched no other file. `web/index.html`
is unchanged and I did not edit any other agent's file.

I wrote two throwaway scripts while checking the winding and the mechanism, in the repo root. They
were not mine to keep, so I deleted them and re-ran all three gates on the clean tree afterwards.

## The commands I ran and what they printed

```
node --check web/feat/menu-icons.js
JS OK
wc -l web/feat/menu-icons.js
103
```

```
python tests/test_feat_files.py
{"files": 24, "checks": 198}
All checks passed.
```

```
python tests/test_menu_pages.py
All checks passed. 53 ok
```

I also loaded the file the way the page loads it, as a second classic script after a stand-in for the
frozen page, in a real VM context. Fourteen checks, all passing:

- All fourteen names registered.
- `iconHtml` returns the same svg shape `ic()` returns.
- The name landed in the page's own map, and the page's own `ic()` then drew it.
- An icon the page already had was left exactly as it was.
- An unknown name gave a clean empty svg.
- A path carrying `"/><script>` was refused and not registered, so nothing but path data reaches
  markup the page pastes in unescaped.
- An empty path was refused.
- A custom 24 box was honoured in `iconHtml` and deliberately not written into the page's map.
- The plug-in registered exactly once and has no Tools card.

## What I could not do

- **The brief said 24x24. The page is 256x256.** `web/index.html:944` is
  ``const ic = n => `<svg viewBox="0 0 256 256" aria-hidden="true">${I[n]}</svg>` `` and the map at
  `:884-943` is drawn on that grid. I built on 256, because a 24-grid path would have come out at a
  tenth of the size of every icon beside it. `PeakCut.icon` still takes a `box` argument, so a 24 icon
  can be registered, but it will not reach the menu.
- I did not run the page live. The contract says not to restart the server, and the page would have to
  be reloaded to pick up the file. The VM run above is the evidence I have that the map is reached and
  that the menu's own lookup finds the name.
- `tests/test_menu_pages.py` only knows the icon names in `index.html`. It does not know about the
  names this file adds. A page that uses one of the fourteen will pass that gate only because the name
  is written into the page's map at load, which happens at runtime and not at test time. So the gate
  cannot see it either way. This file registers no page, so it is not affected today, but the next
  wave should know.
- The icons are simple shapes drawn to match the existing weight, not traced from a set. If the design
  owner wants a different look for any one of them, it is one string in `SET` at the bottom of the file.

Skill loaded: `frontend-design`.
