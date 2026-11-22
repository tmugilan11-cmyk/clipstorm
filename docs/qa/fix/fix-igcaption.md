# Fix report: web/feat/mood.js and web/feat/igcaption.js (agent-200)

Fix wave for the PeakCut QA swarm. Contract: docs/qa/CONTRACT.md. Findings:
docs/qa/FINDINGS.md sections `## web/feat/mood.js` and `## web/feat/igcaption.js`.
Backing audits: docs/qa/audit/api-formats-schedule.md, docs/qa/audit/clip-dialog.md,
docs/qa/audit/api-igcaption.md.

## Files owned

- `web/feat/mood.js` — the sound picker row in the clip dialog.
- `web/feat/igcaption.js` — the editable Instagram post caption box in the clip dialog.

No other file was edited. `web/index.html`, `web/feat/sounds.js` and
`studio/api_igcaption.py` are named in the findings but are owned by the lead and
other agents; they were only read.

## Fixes

### 1. web/feat/mood.js:55 — `ready` flag read with the opposite polarity from sounds.js:212 (minor)

- Finding: the clip dialog treated a missing `ready` flag as playable
  (`r.ready !== false`) while the Sounds page treated it as not built
  (`r.ready === true`). The two consumers of the same `/api/moods` response
  disagreed about a row that says nothing about itself.
- Verification: both lines read as quoted in the finding. The server
  (studio/api_sound.py:78 and :85) always sends `ready` on both the meme and music
  rows, so nothing was wrong today; the change only fixes what a hypothetical
  silent row would mean.
- Fix: changed mood.js to the Sounds page's polarity —
  `ready: r.ready === true` with a plain comment naming sounds.js as the other
  consumer. A row that says nothing about itself is now shown as "(not built yet)"
  instead of being treated as playable, so the page makes no claim without a
  source. `web/feat/sounds.js` already held the safer polarity, so one polarity
  now covers both files without touching the other agent's file.
- Proof: `node --check web/feat/mood.js` → OK; `python tests/test_feat_files.py`
  → `{"files": 75, "checks": 606}` all checks passed (mood.js parses, one plug-in,
  no clashing id, no absolute origin).

### 2. web/feat/mood.js:135 — the sound field's label "Sound" repeated the pane heading "Sound" (minor)

- Finding: the Sound pane has the heading `h3#ed_sound` "Sound" (index.html:2794)
  and the picker row rendered a second "Sound" label above the select.
- Verification: both read as quoted; the pane's own help text
  (index.html:2795, "Choose a background sound, or open the editor...") already
  says "background sound", so the new label is the page's own language.
- Fix: the field label is now "Background sound".
- Proof: `node --check web/feat/mood.js` → OK; `python tests/test_feat_files.py`
  → all 606 checks passed.

### 3. web/feat/igcaption.js:42, :58 — the UI hardcoded the 2,200-character limit (minor)

- Finding: the counter printed the literal `" / 2,200 characters"` and the
  textarea had `maxlength="2200"`, while the server sends the limit with both
  `/api/igcaption/looks` (api_igcaption.py:56) and the clip view
  (igcaption.py:51, `MAX_LENGTH` at igcaption.py:11), so the UI could silently
  drift from `MAX_LENGTH`.
- Verification: all quoted lines and the two API sources read as quoted.
- Fix: the counter now uses the `limit` the API sent with the caption draft
  (`draft.limit`), formatted with a thousands separator, and falls back to
  showing just the count when the response carried no limit — a number on the
  page only appears when it came from somewhere. A plain comment explains where
  the limit comes from.
- Proof: `node --check web/feat/igcaption.js` → OK; live read-only curls:
  `GET /api/igcaption/looks` → `"limit":2200`, and
  `GET /api/jobs/20261122-122201-798840cfbf/clips/clip01/igcaption` →
  `"limit":2200`, so the counter's data source exists on both paths;
  `python tests/test_feat_files.py` → all 606 checks passed.

### 4. web/feat/igcaption.js:42 vs :58 — the counter and the textarea maxlength counted different units (minor)

- Finding: `Array.from(caption).length` counts code points while HTML
  `maxlength` counts UTF-16 units; with emoji the box blocked input while the
  counter still showed room.
- Verification: confirmed on the two lines. The server counts code points too
  (`len(text)`, igcaption.py:26), so the counter's unit is the correct one.
- Fix: dropped `maxlength` from the textarea (the finding's first suggested
  option), aligning everything to one counting unit — the code point, which is
  what both the counter and the server count. A person who types past the limit
  sees the numbers in the counter and gets the server's clear 400 message
  ("An Instagram caption can have up to 2,200 characters, including hashtags.")
  when saving; no silent truncation, no disagreeing numbers.
- Proof: `node --check web/feat/igcaption.js` → OK; `python tests/test_igcaption.py`
  → all checks passed; `python tests/test_post_caption.py` → all checks passed;
  `python tests/test_feat_files.py` → all 606 checks passed.

## Skips

None. All four findings held against the source and the audit evidence.

## Gates run

| Gate | Result |
|---|---|
| `node --check web/feat/mood.js` | OK (exit 0) |
| `node --check web/feat/igcaption.js` | OK (exit 0) |
| `python tests/test_feat_files.py` | `{"files": 75, "checks": 606}` — all checks passed |
| `python tests/test_igcaption.py` | all checks passed |
| `python tests/test_post_caption.py` | all checks passed |
| `python tests/test_text_ink.py` | 1 pre-existing failure, see the note below |
| `python -m py_compile` | not applicable: no Python file was edited by this agent |

## Note for the lead (outside this agent's scope)

`python tests/test_text_ink.py` fails one check: "dark ink is used as page text in:
index.html .pill.live (behind it: var(--live))" — `web/index.html:258`
`.pill.live{color:var(--brand-ink);background:var(--live)}`. That file is owned by
the lead and was not touched by this agent; neither of this agent's files contains
any colour reference (grep for `pill`, `--live` and hex colours returns zero hits in
both), so the failure is unrelated to these fixes and pre-existing in the current
tree.

Server checks were read-only curls against http://127.0.0.1:8798; no route was
changed by this agent, so no restart is needed for these fixes (they are page
files served statically).
