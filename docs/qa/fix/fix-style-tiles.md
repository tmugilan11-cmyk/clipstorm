# Fix report — web/feat/style-tiles.js

Agent: agent-202, fix wave for PeakCut. Brief: docs/qa/FINDINGS.md, section
`## web/feat/style-tiles.js` (FINDINGS.md:1216-1225). Rules: docs/qa/CONTRACT.md.

## Files owned

- `web/feat/style-tiles.js` (the only file I wrote)

## Fixes

### 1. Check mark ink on the selected tile (finding 1, minor, audit: transcribe-brand)

**Where:** `web/feat/style-tiles.js:47-50` — the `.stilegrid .stile-check` rule.

**Finding (verified real):** the selected tile's check glyph was white on the orange
`--brand` #FF8B33. Measured WCAG ratio (relative luminance, 1.4.11 non-text minimum 3:1):
L(#FF8B33)=0.3996, so white on it is 1.05/0.4496 = **2.34:1** — below the 3:1 minimum.
Confirmed the evidence first by re-reading the audit (`docs/qa/audit/transcribe-brand.md:74`)
and the rule in the file.

**Fix applied:** changed `color:#fff` to `color:var(--brand-ink)`, which resolves to
`#160D05` on the main app (`web/index.html:17`), and added a short measured comment above
the rule. This is also the app's own pattern for small marks on the orange
(`.nav-item.on` index.html:52, `.badge` index.html:567 both use `color:var(--brand-ink)`
on `background:var(--brand)`), so the palette is unchanged.

**Proof:** measured the pair before choosing it, not by eye:

```
L(#FF8B33) = 0.3996
white #FFFFFF on #FF8B33      = 2.34:1  (current check glyph, fails 3:1)
#160D05 --brand-ink on #FF8B33 = 8.22:1  (proposed check stroke, passes)
```

(The audit's suggested fix said "about 8.5:1"; the measured value is 8.22:1 — same
conclusion.) The new text ink on orange is 8.22:1, above both 4.5:1 and 3:1.

**Gates:** `node --check web/feat/style-tiles.js` → OK; `python tests/test_feat_files.py`
→ "All checks passed." (75 files, 606 checks); the check named
"a chosen tile and segment use a page ink" in `tests/test_text_ink.py` passes with the
new colour.

### 2. Silent styles-route catch (finding 2, minor, audit: x-states)

**Where:** `web/feat/style-tiles.js:113-115` — the `.catch(() => {})` on the one-shot
`/api/captions/styles` read.

**Finding (verified real):** the fetch fails silently. The audit itself found the design
acceptable — the grid is drawn from the page's own select first, the re-mount only runs
when the fetched list actually differs (`if (g.dataset.names === names(list)) continue;`),
so the fetch only refines what is already shown. The suggested fix was "a one-line note
would be polish".

**Fix applied:** added that one-line note (a plain-English comment above the catch
explaining the silence is on purpose), no behaviour change.

**Proof:** `node --check web/feat/style-tiles.js` → OK; `python tests/test_feat_files.py`
→ "All checks passed."; `grep` confirms the comment sits directly above the catch and no
`color:#fff` remains in the file.

## Skips

None. Both findings in my section were verified against their audit reports and the code,
and both were fixed.

## Gates run

1. `node --check web/feat/style-tiles.js` — exit 0.
2. `python tests/test_feat_files.py` — "All checks passed." (75 files, 606 checks), exit 0.
3. `python tests/test_text_ink.py` — 1 check fails: "dark ink is only used on the brand
   colour", naming `index.html .pill.live (behind it: var(--live))`. That rule is in
   `web/index.html`, which I do not own (the lead owns it). Proven pre-existing, not
   caused by my edits: I temporarily reverted the check-colour change, re-ran the gate,
   and the same single failure appeared; then restored the fix and re-ran
   `node --check` (OK).
4. Em-dash check on the file: `grep -c` for U+2014 → 0 matches. No `!important`, no
   shadows added.

## Server note

No Python route was touched, so no restart is needed for these fixes to take effect; the
two changes are CSS and comments inside one feat file, picked up on the next page load.
