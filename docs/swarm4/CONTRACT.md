# Swarm 4 contract

Read `docs/swarm3/CONTRACT.md` first. It still holds: one feature is one file in `web/feat/`,
`web/index.html` is frozen, `node --check` must pass, escape everything with `esc()`, plain
English, no emoji, fail soft, no new dependencies.

This file adds what wave 4 needs: **a whole page in the main menu**.

## A page is a file, not an edit

```js
/* Analytics: the numbers this channel earned, in one place. */
window.PeakCut.page("analytics", {
  nav:   "Analytics",          // the words in the menu; short
  icon:  "chart",              // a name in the page's icon map; ask, do not invent
  tip:   "Views, watch time and what people did with each video",
  path:  "analytics",          // the address is /app/analytics
  group: "Understand",         // the heading this row sits under in the menu
  order: 20,                   // lower is higher in the menu
  view() { return `<section class="set-sec">…</section>`; },   // the markup
  load() { /* called once, right after the markup is in the page */ },
});
```

`view()` and `load()` are the two you will actually use. Also available: `badge()`, which
returns a number to show beside the menu row, and `tab`, a sub-tab to open on.

The loader keeps `order`, so two pages that both say 20 appear in the order they registered.

## What the loader gives you

| Call | What it does |
|---|---|
| `PeakCut.api(path, opt)` | The page's own fetch wrapper. Throws on a bad answer. |
| `PeakCut.send(path, body, method)` | JSON body, JSON answer. |
| `PeakCut.toast(msg, kind)` | One quiet line. `kind` is `"ok"` or `"bad"`. |
| `PeakCut.state()` | The page state. Has `jobs`, `creators`, `accounts`, `status`, `view`. |
| `PeakCut.css(id, text)` | Add a stylesheet once. Same id twice is a no-op. |
| `PeakCut.add(name, def)` | A feature that is *not* a page: cards in Tools, or an `after` hook. |

Bare helpers from the page, which you must call as plain names, never as `window.x`:
`$`, `$$`, `esc`, `ic`, `put`, `api`, `send`, `toast`, `go`, `money`, `pretty`.

## Rules for a page

1. **The page must say something useful before any request finishes.** Draw the frame, then fill it.
2. **Every number shows its unit and its date range.** A number with no range is a rumour.
3. **An empty state is a sentence, not a blank box.** Say what would put something there.
4. **A failure is a sentence in the page, not a console line.** Say what failed and what to do.
5. **No page loads another page.** If two pages need the same number, put it in the server route.
6. **Never a number you did not receive.** Show a dash and say why.
7. **No em dash, no emoji, no "seamless", no "powerful".** Write like a person.
8. **Styled with the existing classes** — `set-sec`, `set-body`, `fields`, `row`, `help`, `hint`,
   `pill`, `count`, `stat-*`. Do not invent a second design language.

## Your report

Write `docs/swarm4/wave1/<slug>.md` with four lines: what you built, the file you own,
the command you ran to check it and what it printed, and anything you could not do.
Return only that path plus one sentence.

## The gates, all of which you run yourself

```
node --check web/feat/<your file>.js
python tests/test_feat_files.py
python tests/test_menu_pages.py
```

A gate you did not run is a gate you did not pass.
