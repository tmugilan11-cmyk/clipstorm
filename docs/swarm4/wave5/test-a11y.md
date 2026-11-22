# test-a11y

**File I own:** `peakcut/tests/test_a11y_pages.py` (358 lines), the one a11y slot the
brief lets sit outside `web/feat/`. Nothing else edited.

## What I added

A static test of what is on disk. No browser, no network. Plain asserts, stdlib only
(`json`, `re`, `sys`, `pathlib`), same shape as `tests/test_menu_pages.py`: `ok`/`bad`
lists, `check(name, good, detail)`, `ok   ...` lines, `All checks passed. 8 ok`, and
`sys.exit(1)` on any failure. It reads `web/index.html` and every served `web/feat/*.js`
(`_example.js` skipped by its `_` prefix).

The seven rules, each its own check: an `<img>` has `alt`; an icon-only `<button>` has
`aria-label` or `title`; an `<input>` has a label, `aria-label` or `placeholder`; no
`tabindex` above 0 in a feature file; no focus ring removed without a replacement; a
clickable element is a native control, not a bare `<div data-act>`; `index.html` declares
a language. Comments are stripped first, but a bare `//` only counts at line start, since
a blanket split eats `https://` in strings.

## The two exceptions, encoded not deleted

`KNOWN_NAMELESS` in `web/index.html`: the tour "next" button gets its words one line
after it is created, and the Zernio cog names itself in the sentence beside it.
`index.html` is frozen, so this wave cannot add the label. Both match by exact attribute
string, so a third one still fails. `KNOWN_BARE`: `<div class="scrim" data-act="menu">`
is the dim layer behind the open sidebar. No text, never focused, same close on a button.

## Measured on the real tree

```
59 feature files read
24 images, 0 without alt
189 buttons, 20 icon-only, 0 without a name (2 known exceptions)
80 inputs, 0 without a label.  4 tabindex values, 0 above 0
2 rules remove the focus ring, 0 unreplaced
153 clickable: 146 button, 5 a, 1 input, 1 div; 0 bare (1 known exception)
html lang="en"
```
All 7 were then broken on a throwaway copy (language, an `alt`, `<div data-act>`,
`<button><svg></svg></button>`, `<input id="noLabel">`, `<img src="/x.png">`,
`tabindex="3"`, `.bad:focus{outline:none}`). All seven failed and named the snippet.

## `node --check`

```
$ node --check tests/test_a11y_pages.py
TypeError [ERR_UNKNOWN_FILE_EXTENSION]: Unknown file extension ".py"
```

Python, so node refuses it before parsing. The checks that apply ran instead: `py_compile`
is clean, `test_feat_files.py` prints `{"files": 59, "checks": 478}` then
`All checks passed.`, and `test_menu_pages.py` prints `All checks passed. 326 ok`.
Both counts move as other agents land files; this test reads what is on disk.

## Still missing

It reads source text, not a rendered page, so a label written by a neighbouring `put()`,
a name arriving at runtime, and contrast are all invisible to it. An axe-core run is next.
