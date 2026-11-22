# Fix wave: web/feat/streamer-mode.js

Fixer: agent-180 (QA swarm 40, fix wave). Date: 2026-11-22.
Rule set: docs/qa/CONTRACT.md. Findings source: docs/qa/FINDINGS.md section "## web/feat/streamer-mode.js".
Audit reports read: docs/qa/audit/streamer-live.md, docs/qa/audit/x-copy.md.

## Files owned and touched

| Path | Change |
|---|---|
| web/feat/streamer-mode.js | 6 findings fixed, 1 skipped. 712 lines before, 700 after (36,679 bytes) |

No other file was written. The lead's `web/index.html` and every `studio/*.py` file were only read.

## Findings dispositions

### 1. [important] "Recording now" goes blank on every revisit after the first (was streamer-mode.js:487, declared at :149) - FIXED

paintResults built its html, compared it with the module-level `lastLiveHtml`, and returned early when
nothing had changed - but the app rebuilds the page DOM fresh on every visit and re-render
(web/plugins.js drawPage 124-141, web/index.html:2533), so the fresh empty `#str_live` was never filled
when the job state had not moved. `lastLiveHtml` had only three occurrences (declare, compare, set) and
no reset.

Fix: the first statement of `load()` (now streamer-mode.js:619) sets `lastLiveHtml = ""`, with a
plain-English comment. The first paint on every visit now always writes `#str_live`, `#str_count` and
runs paintCreators(), because the painted cache belongs to the previous, dead DOM.

Proof:
- `node --check web/feat/streamer-mode.js` - exit 0.
- `curl -s http://127.0.0.1:8798/assets/feat/streamer-mode.js | grep -c 'lastLiveHtml = ""'` - 2 hits
  (the declaration and the new reset inside load()); served file read from disk per request, so the fix
  is live without a restart.
- `tests/test_feat_files.py` and `tests/test_text_ink.py` still pass (see gates).

### 2. [important] Pressing the already-active mode card silently wiped every typed number (was streamer-mode.js:352-355) - FIXED

switchMode read the draft, kept only the URL, then ran `Object.assign(draft, START.live)` on the
active-card branch, reverting clips, min/max length, style, minutes and hook words with no message. For
the live card the mode stayed "live", so nothing visible changed at all while the values were lost.

Fix: the active-card branch (now streamer-mode.js:338-346) only sets `mode = "live"` - the
`Object.assign` and the URL restore are gone, so everything the person typed stays in the boxes. The
card still unpresses and the form still follows (visible feedback); comments rewritten in plain
English. Switching to a different mode still refills that mode's starting numbers and keeps only the
link, which is the documented behaviour ("Picking a mode fills the form with that mode's starting
numbers").

Proof:
- `node --check web/feat/streamer-mode.js` - exit 0.
- `curl -s http://127.0.0.1:8798/assets/feat/streamer-mode.js | grep -c 'Object.assign(draft, START.live)'`
  - 0 hits (the wipe is gone; the picked-mode refill `Object.assign(draft, START[k])` remains).

### 3. [important] Chase-tick hint was pure backend mechanism (was streamer-mode.js:303-305) - FIXED (truthful rewrite)

The hint read "A note, not a filter. The job route has no field for it, so it is not sent..." - jargon a
beginner cannot parse, and it overclaimed ("It can name a clip a chase or a crash after it is made"),
because the page sends nothing about the tick, so the note is never used anywhere.

Fix: the hint (now streamer-mode.js:289-290) reads "This is a preference note, not a hard filter.
PeakCut does not read this tick yet, so clips are picked by what it hears, the same way for every
video." The auditor's suggested last clause ("after a clip is made it can use the note to label it") was
dropped on purpose: with no route field the note never reaches anything, and writing that it does would
be inventing (contract rule 7).

Proof:
- `node --check web/feat/streamer-mode.js` - exit 0.
- `curl -s http://127.0.0.1:8798/assets/feat/streamer-mode.js | grep -c 'This is a preference note, not a hard filter'`
  - 1 hit.

### 4. [important] Spike mode's "How loud chat must get" select did nothing, hint in mechanism language (was streamer-mode.js:269-270) - FIXED by removal

### 5. [important] Catch mode's garbled "Keep recording for at most, minutes" label on a dead box (was streamer-mode.js:274-277) - FIXED by removal

### 6. [minor] The two dead controls (str_chat, str_minutes) are never sent (was streamer-mode.js:262-271, 272-278) - FIXED

Findings 4, 5 and 6 describe the same two controls; the streamer-live audit's fix offers "Remove both
fields until a route reads them, or make the routes read them". Wiring was not possible (no `studio/*.py`
file is mine to edit and `jobs.py` clean_options throws away unknown keys), so both template blocks were
removed (finding 6's fix), which also removes the jargon hints flagged in 4 and 5. A plain-English
comment before the form template (now streamer-mode.js:226-229) records why: "Spike and catch used to
carry two boxes no route reads... so both are gone until a route grows a field for them." The inert
`chat`/`minutes` starting values stay in START and readDraft (guarded reads of absent elements, so
nothing else changes).

Proof:
- `node --check web/feat/streamer-mode.js` - exit 0.
- `curl -s http://127.0.0.1:8798/assets/feat/streamer-mode.js | grep -c 'id="str_chat"\|id="str_minutes"'`
  - 0 hits (both controls are gone from the served page).
- `tests/test_feat_files.py` still passes, including "streamer-mode.js escapes what it draws" and
  "invents no clashing id".

### 7. [minor] "Save these words to my brand" silently truncated to 120 characters (was streamer-mode.js:686) - FIXED

The page cut typed hook words with `.trim().slice(0, 120)` and the success toast never mentioned the
cut. The 120 limit is the server's own: `studio/brand.py:171` does
`out["hook_words"] = str(out.get("hook_words") or "")[:120]`.

Fix: `maxlength="120"` on the `#str_hooks` input (now streamer-mode.js:271), so the browser stops
typing/pasting past the limit in the first place and the limit is visible behaviour rather than a silent
cut; the hint under the box now ends "The box holds up to 120 characters." The defensive `.slice(0, 120)`
in str_savehooks stays as a guard.

Proof:
- `node --check web/feat/streamer-mode.js` - exit 0.
- `curl -s http://127.0.0.1:8798/assets/feat/streamer-mode.js | grep -c 'maxlength="120"'` - 1 hit.

### 8. [minor] "The 2.5 s results timer is never cleared" (was streamer-mode.js:661-665) - SKIPPED, evidence does not hold

The finding claims "load() sets setInterval on every visit... so each visit to the page stacks one more
interval". The code has a guard the finding misses: `if (!paintResults.timer)` (streamer-mode.js:645)
wraps the assignment, and `paintResults.timer` persists on the function object for the tab's lifetime.
The interval is therefore created exactly once per tab, not once per visit - visits cannot stack timers.
The single interval's tick is a deliberate no-op once the page is left (`if (at("str_live"))`, with a
comment saying so). One 2.5 s timer doing nothing off-page is not the growth the finding describes, so
the evidence does not hold and no change was made.

## Gates run

| Gate | Result |
|---|---|
| `node --check web/feat/streamer-mode.js` | exit 0 |
| `python tests/test_feat_files.py` | 75 files, 606 checks, all passed (exit 0), including all 8 streamer-mode.js checks |
| `python tests/test_text_ink.py` | 10 checks passed (exit 0) |
| `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8798/app/streamer` | 200 |
| Served-file verification, `curl http://127.0.0.1:8798/assets/feat/streamer-mode.js` | 36,679 bytes, matches the edited disk file; reset in load() present, dead ids absent, maxlength present, new hint present, START.live assign absent |

## Notes for the lead

- Static feature files are read from disk per request (server.py /assets/feat/{name}, and "pages in web/
  never need a restart" per server.py:1905), so every fix above is already live on
  http://127.0.0.1:8798 - no restart needed for this file.
- No Python file was touched, so nothing here waits on the final restart.
- No em dashes, no `!important`, no shadows, no colour changes, no CSS touched; every new user-visible
  string and comment is in the app's plain tone; all drawn markup still goes through `esc(...)`.
