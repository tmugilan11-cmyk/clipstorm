# polish-dark

A dark screen that is readable. The page was light only, so this adds a second
set of colour values that switch on only when the system asks for dark.

**File owned:** `web/feat/polish-dark.js`. Nothing else edited.

## What it does

`PeakCut.css("polish-dark", ...)` injects one stylesheet wrapped in
`@media (prefers-color-scheme: dark)`. Three roots carry it: `main#main`, `.pop`
and `dialog`. The sidebar is left alone, so its dark frame is intact.
`--brand` (`#FF8B33`) is not touched.

Tokens inside those roots, light -> dark: `--bg` `#FFFFFF` -> `#17130F`;
`--card` `#211B16` and `--field` `#201A16` (new); `--muted` `#221C17`;
`--line` `#342C25`; `--line-2` `#443A31`; `--text` `#211813` -> `#F2EDE8`;
`--dim` `#C6B9AE`; `--faint` `#A6988C`; `--brand-ink` `#2A1A12` -> `#FFD3AE`;
`--brand-soft` `#3A2415`; `--brand-deep` `#FFB27A`.

Two things were needed beyond the tokens. **The colour is set on the roots:**
the shell declares the text colour on `body`, so a card that only inherits keeps
the light value even though the token changed on `main`. Re-declaring
`color: var(--text)` on the three roots is what made the text readable.
**The rules that spell out `#fff`:** about 30 surfaces paint a literal white
rather than read a token, so the token change never reaches them. Each is named
and given `var(--card)` or `var(--field)`.

Pale ink on the orange reads 1.69, so the six places that write text or a tick
on `--brand` flip to `#2A1A12` (7.17). Hover still changes colour only. Nothing
animates, so reduced motion needs no branch. No image, video or canvas rule is
matched; nothing is inverted.

## Checks

```
$ cd peakcut && node --check web/feat/polish-dark.js
JS OK
$ cd peakcut && python tests/test_feat_files.py
{"files": 59, "checks": 478}
All checks passed.
```

## Measured

Headless Chrome, `Emulation.setEmulatedMedia` with `prefers-color-scheme: dark`,
live server on port 8798, WCAG 2.2 on the colour the eye sees. Card `#F2EDE8` on
`#211B16` = **14.64**. Table row and cell, same two colours = **14.64**. Input
`#F2EDE8` on `#201A16` = **14.79**. Hint `#C6B9AE` on `#211B16` = **8.88**, and
on the page ground `#17130F` = **9.64**. Table heading `#A6988C` on `#211B16` =
**6.08**. Every text node in `#view` on overview and analytics: **0** below 4.5.
Light mode still measures 17.43 for a card and 5.99 for a hint.

## Still missing

The demo server holds no published videos, so the table row and input above were
measured on the shell's own markup placed in the live content area. The `table`,
`th`, `td` and field rules are `index.html`'s and unchanged here, but were not
measured against real rows. Storage, Settings, Sounds and the clip dialog inherit
the same three roots and were not measured one by one. The live badge `#E5323F`
with white text reads 4.32 in light mode already and is left alone.