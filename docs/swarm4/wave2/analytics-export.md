# analytics-export

**Skill loaded.** `frontend-design`, before any reading.

**What I built.** An Export button on the Insights header row. It writes one CSV out of what is
already on the page: the key number cards and the video table rows. It asks the server for nothing
and adds nothing up, so a dash on the screen stays a dash in the file.

The button is:

- `<button class="btn aex" type="button" data-ae="export">` with the `down` icon and the word `Export`,
  appended to `.an-head`, the header row that already holds the channel name, the "Last updated" line
  and the date range line. It is the only child added there, and it is `flex:none` so the name on the
  left keeps its space.
- Its tooltip is the range line: "Save the numbers on this screen as a CSV file. Last 28 days, ending
  20 Nov 2026." The range sentence comes from `[data-an="range-line"]`, which the shell writes, so the
  button never states a date range of its own.
- It turns grey while the panel has nothing in it, with the title "Nothing on this screen has arrived
  yet. The button turns on when it does." A click is refused with a toast in that state.
- It is removed, not hidden, on Trends. Also on Audience and Traffic, because neither of those tabs
  holds rows of its own: the Audience body is a note and an empty box, and the Traffic body is a
  section with no table. A tab added later earns a button only by holding key cards or table rows
  (`.akpi-c` or `table tbody tr`) inside its own panel.

**The file.** `web/feat/analytics-export.js`, new, 252 lines, 11,416 bytes. It registers exactly one
plug-in, `PeakCut.add("analytics-export", ...)`, and it adds its CSS through `PeakCut.css` under the
same name. Nothing else was edited. I did not touch `web/index.html`, `analytics.js`, or any other
agent's file.

How it reads the screen:

- The panel: the first `[data-an-panel]` that is not `hidden`, falling back to `#view` if the shell
  has no panels. Only that panel is read, so the Content tab cannot pick up the Overview cards.
- Cards: each `.akpi-c` gives its label (`.akpi-l`), value (`.akpi-n`), unit (`.akpi-u`), the change
  sentence from the pill's `title` attribute, and the card's own range line (`.akpi-r`).
- Videos: the first `table.ant-t` (or plain `table`) in the panel. Header cells lose their sort icon
  and their `.ant-u` badge, and the badge becomes a unit in brackets, so `Views views` is written
  `Views (views)`. Each body row starts with the title from `.ant-name`, with the `.ant-short` badge
  in brackets after it, then the remaining cells as printed.
- The header block: channel name, date range, the view (tab) name, the "Last updated" time with its
  prefix stripped, the export time, the "N videos" count when the table prints one, and the note
  sentence the cards carry when a number is missing.

How it writes the file:

- A cell is trimmed and collapsed, and gets quotes only when it contains a comma or a quote; quotes
  inside are doubled. A value that starts with `=`, `+` or `@` is written with a leading apostrophe so
  a spreadsheet reads a video title as text instead of running it.
- Lines end `\r\n`, and the text starts with a byte order mark (written as `"\uFEFF"` in the source, not
  as a raw character in the file) so Excel opens the file as UTF-8.
- Sections: a title line, one `label,value` pair per header fact, the note, a blank line, `Key numbers`
  with the header `Label,Value,Unit,Change,Range`, a blank line, then `Videos` with its own header and
  rows. A section that has nothing in it is left out entirely rather than printed as an empty heading.
- The file name is `peakcut-insights-<range>.csv`, where the range is read from the shell in this
  order: `lifetime` for the Lifetime range, `last-<n>-days` from `PeakCutAnalytics.range.days`,
  `<start>-to-<end>` from the two dates, then the range sentence slugged, then `range-not-stated`.
  Never a name with a slash or a colon in it.
- The download is a `Blob` of type `text/csv;charset=utf-8` plus `URL.createObjectURL`, a hidden
  anchor with the `download` attribute, a click, the anchor removed, and `URL.revokeObjectURL` one
  second later so the browser has taken its copy first. If the browser has no `Blob` or no
  `createObjectURL`, a toast says so and nothing is thrown.

Why the redraw is a timer and not a frame: the page probe showed `document.hidden` true, and
`requestAnimationFrame` does not fire in a hidden tab, so the button was missing after a reload until
the tab was looked at. The first version used a frame; it now uses a `setTimeout(..., 0)`. This was
found and fixed in this session.

**What I ran, and what it printed.**

- `node --check web/feat/analytics-export.js` printed `NODE_OK`. Exit 0.
- `python tests/test_feat_files.py` printed `{"files": 37, "checks": 302}` then `All checks passed.`.
  Exit 0. My eight rows:
  `ok analytics-export.js parses`, `ok analytics-export.js declares one plug-in`,
  `ok analytics-export.js is named after itself`, `ok analytics-export.js is the only owner of
  analytics-export`, `ok analytics-export.js does not write into index.html`,
  `ok analytics-export.js escapes what it draws`, `ok analytics-export.js uses no absolute origin`,
  `ok analytics-export.js invents no clashing id`.
- `python tests/test_menu_pages.py` printed `All checks passed. 142 ok`. Exit 0. This file registers no
  page, so it adds no menu row and cannot clash with one.
- `curl -s http://127.0.0.1:8798/assets/feat` lists `analytics-export.js`, and
  `curl -o /dev/null -w "%{http_code} %{size_download}"` on `/assets/feat/analytics-export.js` printed
  `200 11129` before the redraw fix, `200 11416` once the byte order mark and line endings settled (`200 11416` after the byte order mark change).
- In the live page at `http://127.0.0.1:8798/app/analytics`, read back from the DOM after a reload:
  `{"tab":"overview","buttons":1,"label":"Export","icon":1,"disabled":false,"title":"Save the numbers
  on this screen as a CSV file. Last 28 days, ending 20 Nov 2026."}`.
- Trends: clicked the tab, then read `{"tab":"trends","buttons":0,"rows":0}`. Back on Overview:
  `{"tab":"overview","buttons":1,"disabled":false}`. Traffic and Audience, the other two tabs with no
  rows: `buttons: 0` on both.
- A real click with `URL.createObjectURL` wrapped to keep the Blob:
  `{"name":"peakcut-insights-last-28-days.csv","revoked":"blob:real-test","type":"text/csv;charset=utf-8",
  "crlf":16,"lines":17,"leftInDom":0}`, and the first bytes were `[239,187,191]`, the UTF-8 byte order
  mark. The anchor was gone from the page afterwards and the object URL had been revoked.
- The header of that file, verbatim:

  ```
  PeakCut Insights
  Channel,stream_sniper_369
  Date range,"Last 28 days, ending 20 Nov 2026"
  View,Overview
  Updated,05:00
  Exported,"20 Nov 2026, 05:00"
  Note,"PeakCut's own records. Connect a YouTube channel for views, watch time and click-through rate. Connect a channel in Connected apps to fill these in."

  Key numbers
  Label,Value,Unit,Change,Range
  Views,–,views,No comparison for this period,Oct 23 to Nov 19
  Watch time,–,hours,No comparison for this period,Oct 23 to Nov 19
  ```

- Row behaviour was checked by putting a table shaped like `analytics-table.js` output into the
  Content panel (real header markup: `<button data-sort>` wrapping the label, the unit in
  `.ant-u`, a caret svg; titles in `.ant-name` plus an `.ant-short` badge; a missing cell as
  `.ant-na` with the dash). The file came out:

  ```
  Videos on screen,2 videos

  Videos
  Video,Views (views),Watch time (hours),Average view duration (min:sec),Click-through rate (%)
  "Long talk, part 2 (Short)","12,480",311.5,1:24,–
  '=SUM(A1),7,0.4,0:12,3.1
  ```

  So: a comma in the title is quoted, a thousands separator is quoted because of its comma, a dash
  cell stays a dash, the header's unit badge moves into brackets, the sort icon and caret do not reach
  the header row, and a title starting with `=` is defused. The injected table was then removed and
  the page reloaded; `#an_table` now reads `0 videos` and 0 rows again, as the server sends it.
- Range and file name: `lifetime` printed name `peakcut-insights-lifetime.csv` with band
  "Lifetime, up to 20 Nov 2026"; `7` printed `peakcut-insights-last-7-days.csv` with band
  "Last 7 days, ending 20 Nov 2026".

**What I could not do.**

- The account on this machine has no YouTube channel connected, so the live video table is empty
  ("No numbers to show") and every key number is a dash. The row and quoting behaviour above was
  therefore proven against markup copied from `analytics-table.js` and injected into the page, not
  against real rows from the server. The code path is the same one the real rows take, and the
  injected markup was removed afterwards.
- I could not watch a real browser download land in a folder: the page tab reports itself hidden, and
  a headless download cannot be observed from here. What is proven is that the anchor carries the
  right `download` name, the Blob holds the full CSV, and the object URL is revoked afterwards.
- I did not test on a second browser. The only capability guard is the `Blob` / `createObjectURL`
  check, which shows a sentence instead of failing silently.
