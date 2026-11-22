# polish-contrast

One scoped stylesheet lifting `--faint` until it passes WCAG 2.2 AA for body text. `--dim`
already passed and is untouched. The brand accent, the type and the layout do not move.

```css
#main, dialog { --faint: #75695F; }
```

`#main` holds every view and the top bar inside it. The two dialogs sit outside it with
their own white background, so they are named too. The dark sidebar uses `--frame-dim`
(6.55 on `#1E1612`) and needed nothing.

File I own: `web/feat/polish-contrast.js`, 43 lines. No other file was edited.

## node --check
`node --check web/feat/polish-contrast.js && echo "JS OK"` prints `JS OK`, exit 0. The
check prints nothing on success, so the `&& echo` is the proof.

## Test suite
`cd peakcut && python tests/test_feat_files.py` ends with:

```
{"files": 57, "checks": 462}
All checks passed.
```

## Measured: before and after

Ratio is `(L1 + 0.05) / (L2 + 0.05)` from relative luminance. Body text needs 4.5.

| Token | Surface | Before | After | |
|---|---|---|---|---|
| `--faint` `#A0948C` -> `#75695F` | `--bg` `#FFFFFF` | **2.95** | **5.33** | fail -> pass |
| `--faint` | `--muted` `#F7F4F1` | **2.70** | **4.86** | fail -> pass |
| `--faint` | `--brand-soft` `#FFF2E8` | **2.69** | **4.85** | fail -> pass |
| `--faint` | `--good-soft` `#E6F6EE` | 2.64 | 4.76 | fail -> pass |
| `--faint` | `--bad-soft` `#FDECEE` | 2.59 | 4.67 | fail -> pass |

`--dim` `#6D6159` measured 5.99 on `--bg` and 5.47 on `--muted`, so it already passed. Old
`--faint` failed even the 3.0 bar for large text, so no size made it readable. `#75695F`
is the lightest warm grey on the same hue line that clears 4.5 on all five surfaces, and it
stays lighter than `--dim`, so the two quiet levels still read as two levels.

## Measured in the running page

Loaded `/app` on the live server at `127.0.0.1:8798` and read computed styles. `--faint` in
`#main` is `rgb(117, 105, 95)`; in `.side` it is still `#A0948C`; in `#clipdlg` `#75695F`.
`--dim`, `--brand`, `--bg` and `--muted` read their original hex. Walked all 16 menu pages:
16 text nodes used the old grey with the sheet off, 20 used the new one with it on. The
sheet holds one rule, no `!important`, no shadow, no transition or animation, and names no
colour token except `--faint`.

## Still missing

- `--brand` at 2.34 stays under 4.5, per the brief. It carries `--brand-ink` `#2A1A12` as its
  label, which measures 7.17 against it.
- `--faint` on `--line` `#EEE8E4` is 4.39 and on `--line-2` 3.82. No text sits on either.
- Placeholder text in `auth.html` uses `--faint`, but that page is not loaded by
  `plugins.js`. No dark-mode pass: `color-scheme` is light only.
