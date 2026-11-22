# analytics-help

A question mark beside each of the six numbers at the top of Insights. Clicking it opens one plain
sentence saying what that number means and how it is counted, worded from `yt-studio-analytics-spec.md`
(section 7, "Exact definitions"). Closing happens on Escape, on a click outside, or on opening another.

Skill loaded: **fastapi-patterns**.

## Files

- `peakcut/web/feat/analytics-help.js` (new, 276 lines) - the whole feature.
- `peakcut/docs/swarm4/wave2/analytics-help.md` (new) - this report.

Nothing else was touched. `web/index.html` and `web/feat/analytics-kpi.js` were read, never edited.

## What it does

`PeakCut.add("analytics-help", { load, keys, after.drawSettings })`.

It does not draw the cards and does not ask the server for anything. It walks `#view .akpi-c`, reads the
text of each card's own `.akpi-l`, decides which of the six known metrics that card shows, and puts a
`<button class="akhelp" aria-expanded="false" aria-controls="akhelp-<raw>">` plus its sibling
`<div class="akhelp-s" id="akhelp-<raw>" role="note" hidden>` beside the label. Each panel's text is one
sentence, set with `textContent`, never `innerHTML`.

Which card is which is decided by the longest matching phrase among the card's label and its short name,
so "Average view duration" cannot be mistaken for "Views". Matching reads only the label, not the whole
card, because the sentence this file adds also passes through the card and would otherwise help decide
which card it belongs to. A card with no match gets nothing.

The panel is `position: fixed` and is placed under the mark, or above it when there is no room below.
It therefore adds no height to the card and cannot be clipped by a card, an overflow box or a scroll
container: opening and closing never moves anything on the page.

Calling `load()` twice, or on every repaint, is safe: a card that already carries `.akhelp` is skipped.
The box is watched with a `MutationObserver`, so a redraw of `#an_kpi` re-dresses all six cards without
duplicates.

## The six sentences and where each comes from

- **Views** - spec 7.1. "The number of legitimate views: one is counted when a video starts to play, in any format including Shorts and live streams, with an estimate added when people watch together on a TV."
- **Watch time** - spec 7.3, including the hours unit the page labels. "The total time people spent watching, added up and shown in hours, including the time of people who watched together on a TV screen."
- **Impressions** - spec 7.2. "The number of times your thumbnails were shown on YouTube, counted only when a thumbnail was on screen for more than one second and at least half of it was visible."
- **Click-through rate** - spec 7.9. "How often a viewer watched after seeing a thumbnail: views that began from a counted impression divided by the counted impressions, so it is not total views divided by impressions." The second half is taken from the spec's explicit warning never to compute total views over impressions.
- **Average view duration** - spec 7.4 with 7.10. "The average time one view lasted, worked out as watch time divided by engaged views, which count the times someone stayed to watch past the first seconds and leave out loops."
- **Subscribers gained** - spec 7.8. "The change in subscribers over the range, worked out as subscribers gained minus subscribers lost, and it counts everyone who subscribed anywhere on YouTube, not just under one video."

One extra sentence exists for the no-channel card set the same route can send: "Views PeakCut tracked"
gets "The views PeakCut itself recorded on the posts it sent out, added up for this range, so it is
smaller than the view count YouTube would show for the same videos." A probe card with that label was
added to the live page and received exactly that sentence, so the fallback row resolves to its own
definition rather than to the YouTube "Views" one.

No number is invented anywhere: this file writes no digits into the page and never reads a value from a
card.

## Gates

```
$ node --check web/feat/analytics-help.js
JS OK

$ python tests/test_feat_files.py      (the analytics-help lines, then the tail)
ok   analytics-help.js parses
ok   analytics-help.js declares one plug-in
ok   analytics-help.js is named after itself
ok   analytics-help.js is the only owner of analytics-help
ok   analytics-help.js does not write into index.html
ok   analytics-help.js draws no markup
ok   analytics-help.js uses no absolute origin
ok   analytics-help.js invents no clashing id
{"files": 37, "checks": 302}
All checks passed.

$ python tests/test_menu_pages.py
All checks passed. 142 ok
```

`draws no markup` passes because this file never calls `put()` and never sets `innerHTML`; it builds its
two nodes with `createElement` and `textContent`.

Hygiene greps over the file for an em dash, an en dash, emoji, the words "seamless" and "powerful", a
trailing exclamation mark, and `window.ic` / `window.esc` / `window.go`: no matches. `GET /assets/feat`
serves 37 files and includes `analytics-help.js`. No reference in `web/index.html` was needed or added:
`web/plugins.js:244` loads every file found under `/assets/feat/`, so dropping the file in is the whole
registration.

## Live check in the browser

Against `http://127.0.0.1:8798/app/analytics` in the shared browser, reloaded so the served file is the
final one:

- 6 cards, 6 buttons, 6 panels. Every button is `type="button"`, `aria-expanded="false"` at rest, carries
  an `aria-controls` that resolves to a real element, and that element is its `nextElementSibling` with a
  matching id. Every panel is `hidden` at rest and has exactly one sentence.
- Every mark sits 5px after the end of its own label text. (The label box is the growing child of the row,
  so a mark placed after it landed 93px away; the fix wraps the label and the mark in a small flex
  wrapper that takes the growing instead, and the word label is allowed to shrink and ellipsis inside it.)
- A real mouse click at the mark's screen position opened the panel. It renders white with a
  `1px solid var(--line)` border, no shadow, 12.5px text, 320px wide, fully inside the 1920x1111 viewport,
  no overflow, and the topmost element at three probe points inside it is the panel itself.
- Escape on the document closes it and returns focus to the button (`aria-expanded` back to false,
  panel `hidden`, `document.activeElement` is the button). Escape typed with focus on the button, sent as
  a real key press, also closes it. Exactly one panel is ever open: opening a second closes the first.
- A click outside closes it. A click inside the panel keeps it open.
- After forcing a redraw of `#an_kpi` (empty the box, clear its dataset signature, call
  `window.PeakCut["analytics-kpi"].load()`), all 6 cards were re-dressed with 6 buttons, 6 panels, no
  nested wrappers and no duplicates, and clicking still worked.
- The page logs nothing to the console.

Screenshots read while checking: `C:\Users\Asus\Downloads\akhelp-final.png` (Click-through rate open),
`akhelp-settled.png` and a 3x crop `akhelp-zoom.png` of the Views panel.

## Style and house rules

`peakcut/AGENTS.md` asks for the existing palette, no shadows, and hover states that change colour only.
The panel uses a border rather than a shadow, matching the app's own `.pop` popover in `index.html`; hover
and focus swap `background` / `color` / `border-color` only. `prefers-reduced-motion` turns the 140ms
fade off. The mark is a 16px circle carrying the character `?`; no icon name is used, so no icon can be
wrong.

## Things worth knowing

- The route `GET /api/analytics/summary` never sends `impressions` or a CTR value today (the only hits for
  "impression" under `peakcut/studio/` are a docstring and a Zernio key alias). Spec 8.1 explains why:
  thumbnail impressions and impressions CTR are not in the Analytics API targeted queries at all. The
  Impressions and Click-through rate cards therefore show a dash, and their sentences describe the metric
  as the spec defines it rather than a number this build can currently fetch. The two are still correct
  when a build that reads the Reporting API is wired in.
- The route's own six cards are keyed differently from the page's six labels (`average_view_percentage`
  and `engagement` are among them, and the page still shows the fixed labels from
  `analytics-kpi.js`). This file describes the labels the page actually draws, which is what the task
  asked for, and it does not touch `analytics-kpi.js`.
- No `title` attribute is set on the button. A native tooltip opened on hover and covered the first line
  of the panel it opens; the `aria-label` names the button instead.
