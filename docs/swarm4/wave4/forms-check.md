# forms-check: every control on every menu page, and whether it has a hint

Skill loaded first, as the contract asks: **code-review**.

## What this is

A survey of every input, select and textarea reachable from the main menu, with the setting each one
writes and whether a plain-English `.hint` line sits under it. Then a small change to
`web/feat/settings-explain.js`, the file that adds those lines where a field has none: it now walks the
menu pages (`#view`) as well as Settings (`#setbody`), and it carries words for the wave-4 page controls.

Two numbers worth stating plainly, both counted rather than estimated. **59 controls on the menu pages
have an id**: 50 drawn by `index.html` for the Brand, AI, Transcription, Account, Storage, Apps and Tools
forms, plus 9 drawn by feature files (`pcauto_times`, `lrn_days`, the four `la_*`, `pclive_platform`,
`pclive_ident`, `sch_times`). An id is what lets one table describe a control, so those 59 are the ones
this change can reach. **6 controls on those same pages have no id at all**: 5 on the Insights page and
the group of shape checkboxes on Brand. Those cannot be described from my file and are listed at the end
rather than quietly left out.

## How a control gets a hint

`web/feat/settings-explain.js` holds a table keyed by control id. On every draw it walks the controls on
screen, looks the id up, and appends a line **only if the field has none already** (no `.hint` and no
`<small>` inside its wrapper). Nothing is replaced, and a second pass over the same markup adds nothing.

The hook it runs on is `after.drawSettings`, which `web/plugins.js` fires for **every** menu page
(`plugins.js:112-118` `runAfter`, called by `drawPage` at `plugins.js:120-137` after `load()` settles or
rejects). Settings passes `#setbody`; a page passes the whole `#view`. A MutationObserver on `#sform` and
`#view` catches the panels that arrive later with no redraw, so a card painted after the page is
described too. Nothing new was needed for the wave-4 pages beyond words in the table.

## The table, page by page

`Hint?` means a line of class `hint` (or a toggle's own `<small>`) inside that control's own wrapper.
`yes (own)` is what the page already had; `added` is what `settings-explain.js` puts there.

### Brand (menu-pages.js:130, form drawn by `drawSettingTab("brand")`, saved as one `PUT /api/brand`)

| Control | id | Setting it writes | Hint? |
|---|---|---|---|
| Theme | `br_theme` | `theme` | yes (own) |
| Caption look | `br_style` | `style` | yes (own) |
| Font | `br_font` | `font` | yes (own) |
| Colour, words not said yet | `br_c_text` | `colors.text` | yes (own) |
| Colour, spoken word | `br_c_spoken` | `colors.spoken` | yes (own) |
| Outline colour | `br_c_outline` | `colors.outline` | yes (own) |
| Keyword colour | `br_c_key` | `colors.key` | yes (own) |
| Box colour | `br_c_box` | `colors.box` | yes (own) |
| Hook text colour | `br_hook_text` | `hook_text` | yes (own) |
| Hook bar colour | `br_hook_box` | `hook_box` | yes (own) |
| Hook position | `br_position` | `position` | yes (own) |
| Watermark | `br_watermark` | `watermark` | yes (own) |
| Watermark colour | `br_watermark_color` | `watermark_color` | yes (own) |
| Watermark position | `br_watermark_pos` | `watermark_pos` | yes (own) |
| Watermark opacity | `br_watermark_opacity` | `watermark_opacity` | yes (own) |
| Watermark size | `br_watermark_size` | `watermark_size` | yes (own) |
| Progress bar | `br_progress` | `progress` | yes (toggle `<small>`) |
| Progress bar colour | `br_progress_color` | `progress_color` | yes (own) |
| End card words | `br_endcard` | `endcard` | yes (own) |
| Language | `br_lang` | `lang` | yes (own) |
| Drop fillers | `br_fillers` | `fillers` | yes (toggle `<small>`) |
| Emoji | `br_emoji` | `emoji` | yes (toggle `<small>`) |
| Denoise | `br_denoise` | `denoise` | yes (toggle `<small>`) |
| Black-frame fix | `br_blackfix` | `blackfix` | yes (toggle `<small>`) |
| Lift the shadows | `br_lift` | `lift` | yes (toggle `<small>`) |
| Punch flash | `br_flash` | `flash` | yes (toggle `<small>`) |
| Flip the layout | `br_flip` | `flip` | yes (toggle `<small>`) |
| Shape checkboxes (one per aspect) | *no id* | `aspects` | **no** |

Brand is the one tab that describes itself: 27 of 28 controls already had a line, which is why the
`br_*` words in the table are a dormant fallback that never fires.

### AI (menu-pages.js:198, `drawSettingTab("ai")`, saved with `PUT /api/ai`)

| Control | id | Setting it writes | Hint? |
|---|---|---|---|
| Provider | `ai_provider` | `provider` | **added** |
| Key | `ai_key` | `key` | yes (own, `#ai_keyhint`, filled by script) |
| Address | `ai_base` | `base_url` | yes (own) |
| Model | `ai_model` | `models` | yes (own) |

### Transcription (menu-pages.js:147, `drawSettingTab("transcribe")`, saved with `PUT /api/transcribe`)

| Control | id | Setting it writes | Hint? |
|---|---|---|---|
| Provider | `tr_provider` | `provider` | **added** |
| Logfare key | `tr_key` | `key` | yes (own) |
| Model | `tr_model` | `model` | yes (own, `#tr_modelhint`) |
| Own relay | `tr_proxy` | `proxy` | yes (own) |

### Account, security tab (menu-pages.js:234, saved with `POST /api/auth/password`)

| Control | id | Setting it writes | Hint? |
|---|---|---|---|
| Current password | `pw_cur` | `current` | **added** |
| New password | `pw_new` | `new` | **added** |

### Storage (menu-pages.js:216, saved with `PUT /api/storage`)

| Control | id | Setting it writes | Hint? |
|---|---|---|---|
| New folder | `stor_new` | `path` | **added** |
| Move existing files | `stor_move` | `move` | **added** (a `<p class="sub">` follows the row, but it explains the delay, not the tick) |

### Apps (menu-pages.js:181, saved with `PUT /api/apps`)

| Control | id | Setting it writes | Hint? |
|---|---|---|---|
| Client ID | `app_id` | `client_id` | **added** |
| Client secret | `app_secret` | `client_secret` | **added** |
| Zernio key | `z_key` | Zernio key (`studio/zernio.py`) | **added** |

### Tools (menu-pages.js:164, `drawSettingTab("tools")`)

| Control | id | Setting it writes | Hint? |
|---|---|---|---|
| Clip rules, platform | `tl_platform` | nothing saved; asks `GET /api/rules` | **added** |
| Clip rules, channel | `tl_handle` | nothing saved; sent in that query | **added** |
| Watch list, platform | `tl_wplatform` | nothing saved; `POST /api/hunt/watch` | **added** |
| Watch list, channel | `tl_wident` | nothing saved; sent in that body | **added** |
| Schedule, times | `tl_times` | nothing saved; `GET /api/schedule/preview` | **added** |
| Schedule, this computer | `tl_os` | nothing saved; sent in that query | **added** |
| Video address | `tl_video` | nothing saved; `GET /api/stats/video` | **added** |
| YouTube key | `tl_key` | nothing saved; sent in that query | **added** |
| Autopilot times (autopilot.js:60, same page) | `pcauto_times` | `autopilot.spec`, `POST /api/autopilot/install` | yes (own, `autopilot.js:64`) |

The eight `tl_*` fields save nothing: each is a question typed into a card and answered in a box below.
Their lines say what the answer will be used for, not that a setting changes.

### Creators (creators.js:254, `GET /api/creators`)

No inputs, selects or textareas. Buttons only: New creator, Refresh, and one Setup and one Clips per
card. The two buttons that need explaining have lines at `creators.js:245-246`.

### Live (live.js:302, `GET /api/hunt/watching`, `POST /api/hunt/watch`)

| Control | id | Setting it writes | Hint? |
|---|---|---|---|
| Platform | `pclive_platform` | `platform` in the watch body | **added** |
| Channel name | `pclive_ident` | `ident` in the watch body | **added** |

Both labels are siblings of their control, not wrappers, so the line lands inside the `.pclive-field`
div and reads as one more line under the field. The page's own format hint at `live.js:342-343` sits
after the whole form, outside both field divs, which is why neither field counted as described.

### Schedule (schedule.js:280, `GET /api/autopilot/spec`, `GET /api/schedule/preview`)

| Control | id | Setting it writes | Hint? |
|---|---|---|---|
| Clock times | `sch_times` | the times passed to `preview?times=` | yes (own, `#sch_times_hint` at `schedule.js:301-302`, referenced by `aria-describedby`) |

The hint sits outside the label wrapper, so a naive pass would have added a second line under the first.
It is deliberately left out of the table, so this field keeps its one good line.

### Improve (learn.js:354, `POST /api/learn/run`, `POST /api/learn/arms`)

| Control | id | Setting it writes | Hint? |
|---|---|---|---|
| Look at (days) | `lrn_days` | `days` in the run body | **added** |
| First setting to try | `la_target` | `target` in the arms body | **added** |
| Value for the first | `la_value` | `value` | **added** |
| Second setting to try | `la_other` | `other` | **added** |
| Value for the second | `la_other_value` | `other_value` | **added** |

These four trial fields shared one `<p class="sub">` at `learn-arms.js:144-145` below the whole form,
which explains the idea of two arms but not what to type in each box. Each now has its own line. The
card is painted after the page (`learn-arms.js:211-225`), and the observer on `#view` describes it then.

### Insights / analytics (analytics.js:210, `GET /api/analytics*`)

| Control | key | Setting it writes | Hint? |
|---|---|---|---|
| Date range | `data-an-range` (*no id*) | the query range | **no** |
| Compare to the previous period | `data-an-compare` (*no id*) | a second series | yes (its `<small data-an="compnote">` is filled by script) |
| Table range | `data-ant="range"` (*no id*) | the table's range | yes (`analytics-table.js:178`) |
| Table search | `data-ant="q"` (*no id*) | the text filter | yes (`analytics-table.js:181`) |
| Retention video | `data-ar="pick"` (*no id*) | which video's curve | **no** |

### Usage, Clip formats, Sounds, Help (usage.js:257, formats.js:339, sounds.js:326, help.js:124)

No inputs, selects or textareas on any of the four. Each has one button that fetches again, and each
carries a line saying what pressing it costs: `usage.js:272`, `formats.js:359`, `sounds.js:348`, and the
open/close line at `help.js:137`.

## Every control without a hint

Fixed by this change (line added from the table, in `settings-explain.js`):

1. `ai_provider` on the AI page
2. `tr_provider` on the Transcription page
3. `pw_cur` on the Account page
4. `pw_new` on the Account page
5. `stor_new` on the Storage page
6. `stor_move` on the Storage page
7. `app_id` on the Apps page
8. `app_secret` on the Apps page
9. `z_key` on the Apps page
10. `tl_platform`, `tl_handle`, `tl_wplatform`, `tl_wident`, `tl_times`, `tl_os`, `tl_video`, `tl_key` on the Tools page (8)
11. `pclive_platform`, `pclive_ident` on the Live page
12. `lrn_days` on the Improve page
13. `la_target`, `la_value`, `la_other`, `la_other_value` on the Improve page

Still without a hint, and **not fixable from my one file** because none of them has an id to key on:

1. The Brand shape checkboxes (`label.ck`, `value="1:1"` and so on, drawn at `index.html:2375`). They are
   built in a loop with no id. One line would cover the whole group; it needs an id on the wrapper, so it
   is `index.html` work, which is frozen.
2. `data-an-range` on the Insights page (`analytics.js:115`), the date range picker. It is the control
   that decides what every number on the page covers, so it is the one that most deserves a line.
3. `data-ar="pick"` on the Insights page (`analytics-retention.js:236`), which video the curve is for.
   Its wrapper is `label.rpick` with the word "Video" in it, so a line there would read naturally.

Outside the menu pages, three more id-less controls follow the same pattern and are mentioned only so
nobody assumes they were missed: `data-f="mood"` in the clip dialog (`mood.js:135`), `day-who` and
`day-url` in the day planner (`day.js:58`, `:66`), `pcf-q` in the search box (`filters.js:87`), the
menu search in `nav-search.js:58`, and `pcs-key` in the stats card (`stats.js:158`).

Two more notes for whoever owns those files: `analytics.js` keeps its controls keyed by `data-an-*`
rather than id, so a table like mine cannot describe them; and `analytics-retention.js` could reuse the
`label.rpick` wrapper if the select were given `id="ar_pick"`, which would make it describable with one
line in my table. Both are other agents' files, so this report is where the change belongs.

## What changed in `web/feat/settings-explain.js`

- The header comment now says it covers the menu pages as well as Settings, and why.
- A `.sx-under` rule was added to the injected CSS: a line that has to live inside a bare label becomes
  `display:block` and wraps at 56 characters instead of being squeezed beside the field. Only a `.sw` row
  lays its children out sideways, so only there does the rule also ask for `flex-basis:100%`. Most
  wrappers already stack (`label.f` is `flex-direction:column`, and so is live.js's `.pclive-field`), so
  the line drops under the field on its own and no full-width hint is needed.
- Seven new entries in the table under a `// Menu pages.` heading: `lrn_days`, `la_target`, `la_value`,
  `la_other`, `la_other_value`, `pclive_platform`, `pclive_ident`. The table now has 57 keys.
- The `.sw` branch falls back to `.sx-under` when a picker row has no `<span>` to put a `<small>` in
  (`learn.js` puts a select inside a `.sw` label). Previously that case appended an unstyled span.
- The final else branch adds `.sx-under` unless the wrapper is already a stacking `label.f`, so a line
  added inside a bare `<label>` or a wrapping div lands under the control rather than beside it.

Nothing that the page already writes is replaced, and no text is ever inserted as markup: every line goes
in through `textContent`, so a description can never carry a tag into the page.

## Routes

`settings-explain.js` itself reads **no route**. It only reads the DOM: it never calls `api`, `send` or
`fetch`, so it cannot fail on a server and cannot ask for a page that does not exist.

The controls it describes are saved by routes that all exist. Checked with
`grep -rn 'router.get\|@app.get' studio/` and the same for post, put and delete:

- `GET`/`PUT /api/brand` (api_brand.py:42, :48), `GET /api/brand/themes` (:76), `POST /api/brand/reset` (:83)
- `GET`/`PUT /api/ai` (server.py:1385, :1391), `GET /api/ai/models` (:1405), `POST /api/ai/test` (:1419)
- `GET`/`PUT /api/transcribe` (server.py:1472, :1478), `GET /api/transcribe/models` (:1528), `POST /api/transcribe/test` (:1547)
- `POST /api/auth/password` (server.py:586)
- `GET`/`PUT /api/storage` (server.py:1671, :1700), `POST /api/storage/pick` (:1691)
- `GET`/`PUT /api/apps` (server.py:1714, :1720)
- `GET /api/rules` (api_preview.py:46), `GET /api/hunt/watching` (:134), `POST /api/hunt/watch` (:143), `POST /api/hunt/unwatch` (:157)
- `GET /api/schedule/preview` (api_preview.py:173), `GET /api/autopilot/spec` (api_auto.py:97), `POST /api/autopilot/install` (:135)
- `GET /api/stats/video` (api_stats.py:71), read through `api` at `index.html:2904`
- `GET /api/learn/state` (api_learn.py:57), `POST /api/learn/run` (:72), `GET`/`POST /api/learn/arms` (:224, :239), `DELETE /api/learn/arms` (:275)
- `GET /api/analytics/summary`, `/timeseries`, `/videos`, `/audience`, `/traffic`, `/retention`
  (api_analytics.py:176, :237, :271, :327, :374, :402). These six are exactly the six the Insights pages
  ask for: the paths in `web/feat/analytics*.js` and the paths defined in `studio/api_analytics.py` match
  name for name, checked by listing both and comparing.

## What it cannot do yet

- It cannot describe a control with no id. Three menu-page controls are keyed by `data-*` and stay
  unexplained until their owners add an id (see the list above). Reading `data-*` keys would mean
  guessing at four unrelated naming schemes, and the contract says ids, so the table stays keyed on ids.
- It cannot tell you a field is *wrong*, only what it does. Validation stays with the page that saves it.
- It cannot put a line under a control whose wrapper already holds a `<small>` for another reason. That
  rule is what keeps it from fighting the page, but it does mean a toggle whose caption is unhelpful
  cannot be improved from here.
- On a very narrow screen the page hides `.hint` inside Settings unless the wider rule in this file
  applies. The rule covers `#setbody`, `.set-body` and `#view`, but a page that draws into some other
  container would lose its lines on a phone.

## Commands run, with results

```
cd C:/Users/Asus/Documents/deepseek-harness/default-workspace/peakcut
node --check web/feat/settings-explain.js
-> exit 0, no output (parses clean)

node -e "..."   # count registrations and table keys
-> add_calls 1
   line_keys 57
   new_keys lrn_days,la_target,la_value,la_other,la_other_value,pclive_platform,pclive_ident

python tests/test_feat_files.py
-> ok   settings-explain.js parses
   ok   settings-explain.js declares one plug-in
   ok   settings-explain.js is named after itself
   ...
   {"files": 47, "checks": 382}
   All checks passed.
```

The file is 173 lines, still one `PeakCut.add("settings-explain", ...)` registration named after itself,
still draws no markup of its own beyond the injected CSS, and mentions no absolute origin.
