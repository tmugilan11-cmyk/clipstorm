# polish-space

## What I added

One vertical rhythm for the menu pages, as a stylesheet only. No markup, no handlers, no motion.

The scale is named on `#view` so a later file can reuse it instead of typing 14:
`--ps-1:4px --ps-2:8px --ps-3:12px --ps-4:16px --ps-5:20px --ps-6:24px --ps-8:32px`.

All rules scoped under `#view`:

| Rule | Before | After |
| --- | --- | --- |
| `section` margin-block | 24 top / 18 pad on one page, 26 bottom on another | `0 0 20px 0`, padding 0 |
| `.set-sec` padding-block-end | 26px | 16px |
| `.fmtp-sec` padding-block-start | 18px | 16px |
| `.card` padding-block | 22px | 20px |
| `.card > h2 + .help` margin-block-end | 18px | 16px |
| `label.f` gap | 7px | 8px |
| `.fields` row-gap | 18px | 16px |
| `.grid` gap | 16px | 16px (restated so it cannot drift) |

## The file I own
`peakcut/web/feat/polish-space.js`. Nothing else was edited.

## node --check
```
$ cd peakcut && node --check web/feat/polish-space.js && echo "JS OK"
JS OK
```

## python tests/test_feat_files.py
```
{"files": 57, "checks": 462}
All checks passed.
```

Eight `ok` lines cover `polish-space.js`. `/assets/feat` serves it.

## What I measured, with real numbers
Measured live on `http://127.0.0.1:8798` by disabling `#pcss_polish-space`, re-reading computed styles, then re-enabling it.

`/app/creators`, `margin-bottom` of the first three sections (the page holds one): before `26px`, after `20px`.

`/app/formats`, first three sections, `margin-top/margin-bottom/padding-top/padding-bottom`:
before `0/0/0/0`, `24/0/18/0`, `24/0/18/0`; after `0/20/0/0`, `0/20/16/0`, `0/20/16/0`.

`/app/schedule`, three `.card`: padding `22px/22px` became `20px/20px`, width stayed `820px`.

`/app/brand`: `label.f` gap `7px` became `8px`; `.fields` row-gap `18px` became `16px`.

Widths did not move: a format section stayed `900px`, a card `820px`, grid columns `292px 292px 292px`.

Sidebar and top bar match with the sheet on and off: `.side` padding `14px/10px` width `240`; `.topbar` padding `10px/28px` height `54`; document `scrollWidth` `1920`.

## What is still missing
- Only `section`, `.card`, `.fields`, `label.f` and `.grid` are normalised. `.row`, `.toolsbox`, `.set-sec h2` margins and `.hint` spacing were left alone.
- Feature card classes still differ (`.cr-card` `15px 16px 14px`, `.fmt-card` `13px 14px 12px`). Other agents own those files.
- Settings drawers (`#cbody`, `#sform`) are not `#view`, so Settings keeps its old rhythm. Scope stops at the menu pages on purpose.
- Measured at 1920 only. No mobile pass, though every change is vertical so no tap target moved.
