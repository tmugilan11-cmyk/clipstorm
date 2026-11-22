# settings-explain

**What I built.** `web/feat/settings-explain.js` puts one plain English line under every option in
Settings, saying what changing it does. 140 lines, one plug-in, no page of its own.

The line table has 50 entries keyed by control id. It covers all 46 ids in `web/index.html` matching
`br_`, `tr_`, `ai_`, `stor`, plus `pw_cur`, `pw_new`, `app_id`, `app_secret`, `z_key` and the nine `tl_`
fields on the Tools tab, which are settings controls too.

The hook is `after.drawSettings`. It walks every `input[id], select[id], textarea[id]` inside `#setbody`
and, where the field has no `.hint` and no `small` already, appends one. Existing lines are never
touched. Idempotence is a `data-sx-note="1"` mark on the label, so a second pass finds nothing to do.

Three shapes are handled apart:
- a plain `label.f` takes the line at its end, in the page's own `.hint` style;
- a toggle (`label.sw`) already shows a caption, so the line goes in as a `small` under its words;
- a checkbox pill (`label.ck`) cannot hold a second line, so the line sits after it as `.sx-note`.

The ids I found, and what each one says:

**Brand (27).** `br_theme`, `br_style`, `br_font`, `br_c_text`, `br_c_spoken`, `br_c_outline`, `br_c_key`,
`br_c_box`, `br_hook_text`, `br_hook_box`, `br_position`, `br_watermark`, `br_watermark_color`,
`br_watermark_pos`, `br_watermark_opacity`, `br_watermark_size`, `br_progress`, `br_progress_color`,
`br_endcard`, `br_lang`, `br_fillers`, `br_emoji`, `br_denoise`, `br_blackfix`, `br_lift`, `br_flash`,
`br_flip`.

**AI (4).** `ai_provider`, `ai_key`, `ai_base`, `ai_model`.

**Transcription (4).** `tr_provider`, `tr_key`, `tr_model`, `tr_proxy`.

**Storage (2).** `stor_new`, `stor_move`.

**Security (2).** `pw_cur`, `pw_new`. **Connected apps (3).** `app_id`, `app_secret`, `z_key`.
**Tools (9).** `tl_platform`, `tl_handle`, `tl_wplatform`, `tl_wident`, `tl_times`, `tl_os`, `tl_video`,
`tl_key`.

Note on `br_layout`: the task named it, but it is not in `web/index.html` (0 hits). The closest real id
is `br_position`, which covers it. I did not invent a `br_layout` entry, since an id that is never drawn
can never fire.

**The file I own.** `web/feat/settings-explain.js` only. I did not edit `web/index.html` or any other
agent's file.

**The commands I ran and what they printed.**

```
$ node --check web/feat/settings-explain.js
JS OK

$ python tests/test_feat_files.py
ok   settings-explain.js parses
ok   settings-explain.js declares one plug-in
ok   settings-explain.js is named after itself
ok   settings-explain.js is the only owner of settings-explain
ok   settings-explain.js does not write into index.html
ok   settings-explain.js draws no markup
ok   settings-explain.js uses no absolute origin
ok   settings-explain.js invents no clashing id
{"files": 24, "checks": 198}
All checks passed.

$ python tests/test_menu_pages.py
All checks passed. 53 ok
```

The second gate reports no page from my file, which is the allowed case: this is a fill-in, not a page.

Live, in the browser at `http://127.0.0.1:8798/app`, Settings, each tab clicked in turn:

```
brand       27 controls, 0 missing   (the tab ships its own line on every field)
ai           4 controls, 0 missing   (my line lands on ai_provider)
transcribe   4 controls, 0 missing   (my line lands on tr_provider)
tools        9 controls, 8 described (the ninth is below)
storage      2 controls, 0 missing   (only after "Change folder", see below)
apps         0 controls at runtime
```

Checked by hand, on the live page:
- three extra passes over the Brand tab left 27 lines, not 81: idempotent;
- `br_theme` still reads "A ready-made look to start from. `None` leaves everything below as it is",
  the page's own wording, unchanged: I never overwrite an existing `.hint`;
- no label carries two added lines;
- the colours read "Six letters or numbers, without the #." from `index.html:2357`, not from me.

**What I could not do.**

1. `pcauto_times`, on the Tools tab, belongs to `web/feat/autopilot.js`, another agent's file. It
   already has its own `.hint` ("Up to N times on a 24 hour clock, separated by commas"), drawn as a
   sibling of the form rather than inside the label. My walk correctly leaves it alone. Two lines on
   that field would be worse than one, so I did not add mine.

2. The Storage panel is opened by the "Change folder" button and fires no render event, and each tab
   click replaces `#setbody` outright. A hook that runs only on a redraw would step over both. I added
   a `MutationObserver` on `#sform` (which outlives the tab switches) that looks `#setbody` up again on
   every change and re-runs the pass. A pass that finds everything already described adds nothing, so
   this stays quiet. It is a small extra watcher; the contract's hook alone was not enough for the two
   click-only panels.

3. `index.html` hides every `.hint` under 560px wide. These lines are the whole point of the tab, so my
   stylesheet restores them inside `#setbody` at that width. Confirmed the rule is live:
   `@media (max-width: 560px) { #setbody .hint { display: block; } }`. That is a deliberate override of
   a global page rule, scoped to the settings body only.

4. I could not make the Apps tab describe anything, because at runtime it draws no controls. Its ids
   (`app_id`, `app_secret`, `z_key`) ship in `index.html` and are in my table, so the lines will appear
   wherever those fields are drawn. If another agent draws that tab later, the table already covers it.

Skill loaded: `frontend-design`. Applied: written copy is design content, so every line is a full
sentence about consequence rather than a restatement of the label; line length kept short; colour and
weight inherited from the page rather than invented.
