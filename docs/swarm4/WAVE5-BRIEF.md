# Wave 5 — polish

Read this first, then write. It is short and every line is a rule.

## What already exists

PeakCut is a clipping app: a Python FastAPI server (`studio/`) and one page
(`web/index.html`, 7,000 lines, **frozen — never edit it**). Everything new lives in
`web/feat/<slug>.js` and `web/plugins.js` loads it.

48 feature files are in `web/feat/` right now (47 served; `_example.js` never is).
They register pages, panels and handlers. Read `web/feat/heard.js` first — it is the
smallest correct example — then `web/plugins.js` so you know exactly which helper you have.

Helpers: `PeakCut.add(name, def)`, `PeakCut.page(name, def)`, `PeakCut.css(id, text)`,
`PeakCut.api(path)`, `PeakCut.send(path, body, method)`, `PeakCut.toast(msg, kind)`,
`PeakCut.state()`, and the page globals `$(sel)`, `$$(sel)`, `esc(s)`, `ic(name)`,
`put(el, html)`, `api()`, `send()`, `toast()`.

`def` keys that work: `tools()`, `load()`, `act{...}`, `keys(e)`, `after{...}`,
`view()`, `nav`, `icon`, `group`, `order`, `path`, `tip`.

**Handlers declared inside `PeakCut.page(...)` never fire.** Clicks and keys are routed
only through `PeakCut.add`. Any page file needs its handlers in a separate
`PeakCut.add("<slug>", { act: {...} })` block. This was measured, not guessed.

## What this wave is for

Waves 1-4 built the features. This wave makes them feel finished: type, spacing,
colour, contrast, motion, small screens, wide screens, dark screens, empty states,
loading states, forms, tables, keyboard, and screen-reader labels.

Every agent owns exactly one file. Do not touch another agent's file, `web/index.html`,
`web/plugins.js`, or anything in `studio/` (the one exception is the a11y test slot,
which owns `tests/test_a11y_pages.py`).

## Rules

1. `node --check <your file>` must pass. Run it and paste the output.
2. `python tests/test_feat_files.py` must still say "All checks passed." (it requires
   one plug-in per file, named after the file, and `esc(` around interpolated HTML).
3. Escape every server string with `esc()` before it goes into HTML.
4. Plain English, short sentences. No emoji. **No em dash** (use a comma or a full stop).
5. No new dependencies. No web fonts. No shadows (house style). Hover changes colour only.
6. Fail soft: one quiet line, never a throw into the page. No empty `catch {}`.
7. Every CSS rule you add must be scoped to something real on the page. Do not restyle
   the whole document from a polish file, and do not use `!important`.
8. `prefers-reduced-motion: reduce` must be respected by anything that moves.
9. Tap targets at least 44 by 44 CSS pixels below 640 px wide.
10. Never invent a number, a name or a page.

## Your budget

You have **25 minutes**. Read only the two or three files you actually need, then write.
A working, checked file beats a perfect plan. Write what you left out into your report.

## Report

Write `peakcut/docs/swarm4/wave5/<slug>.md` with: what you added, the file you own, the
`node --check` result, what you measured, and what is still missing. Keep it under 60 lines.

## Prove it before you claim it

`node --check` is not proof a rule works. If you can, measure the thing you changed:
read a computed style, count a tap-target size, list the aria labels you added. Say what
you measured and what the numbers were.
