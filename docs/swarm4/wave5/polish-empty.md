# polish-empty

**File owned:** `peakcut/web/feat/polish-empty.js`. Nothing else touched. **Skill loaded:** `make-interfaces-feel-better`

## What I added

One way of saying "there is nothing here yet": a bold lead, one sentence, a button only when there is an obvious next step.

1. A scoped stylesheet, 9 rules, all rooted at `.pe-empty`. No `!important`, no shadow, no em dash. Hover changes colour and border only.
2. `PeakCut.empty({ lead, say, label, act })` builds the block. Every value goes through `esc()`.
3. One `act` handler `peemptyfocus`: puts the cursor in `#url` and scrolls it into view.
4. One `after.drawJobs` hook unifies the block the frozen page writes into `#jobs` when no video exists, reusing its own words and adding "Paste a link".

```
$ node --check web/feat/polish-empty.js   -> JS OK
$ python tests/test_feat_files.py         -> All checks passed.
```

## Measured, in the browser on http://127.0.0.1:8798/app

Empty states found: **28 of 47** files render one, in **74** phrases, under **9** class names: `aa-empty`, `ac-empty`, `an-empty`, `ant-empty`, `atr-empty`, `cr-empty`, `fmt-empty`, `pclive-empty`, `usg-empty`. One shape unified, measured:

- Rules added: 9, all scoped to `.pe-empty`. `!important`: 0. `box-shadow`: 0. Em dash: 0.
- Block padding `48px 20px` became `36px 18px 38px`. Gap `4px` became `9px`.
- Button box at 1920px: **105 by 36 px**. Under `max-width: 639px`: **44 by 44** minimum.
- Transition: colour at 0.15s, none under reduced motion. Clicking it moved `document.activeElement.id` from empty to `url`; `P.empty()` given `<img src=x onerror=alert(1)>"'&` came back fully escaped.

## Census, and where the other 27 should go

I unified `#jobs`: the first thing a new person sees, and the largest shape at 48px padding. In order of payoff, the rest:

1. `creators.js` `.cr-empty`, `formats.js` `.fmt-empty`, `usage.js` `.usg-empty`, `live.js` `.pclive-empty` already are dashed boxes with the right idea; they only need `P.empty()` and the class. Cheapest wins.
2. `analytics-table.js` `.ant-empty`, `analytics-trends.js` `.atr-empty`, `analytics-audience.js` `.aa-empty` are near-identical; one helper removes three sheets.
3. `analytics-charts.js` `.ac-empty` is a grey line with no box. It should gain the box.
4. `grid.js` (`Nothing queued.`) and `learn-signals.js` say it in a 13px paragraph with no room for a next step.
5. `filters.js` `.pcf-none` is a filter result, not an empty state. Leave it alone.

The other 18 (`analytics-compare`, `analytics-empty`, `analytics-export`, `analytics-kpi`, `analytics-retention`, `analytics-revenue`, `analytics-shorts`, `analytics-traffic`, `analytics`, `autopilot`, `day`, `learn`, `log`, `mood`, `nav-search`, `peek`, `schedule`, `sounds`) draw their own box; none has an `after` hook I can reach.

## Still missing

The hook needs `#jobs`, so it reaches Home and All videos only. The creator and review tabs draw `.empty` into `#cbody` and `#rv`, which have no `after` hook in `plugins.js`; that file is not mine to change.

The server has jobs, so I measured by emptying `S.jobs`, calling `drawJobs()`, reading the styles, then restoring (after: 4 jobs, no `.empty`).
