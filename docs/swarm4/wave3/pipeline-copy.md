# pipeline-copy

## What I built

`studio/prompt_text.py`: the sentences PeakCut says about itself, in one place, so
prompts stop carrying scattered literals.

- `PIPELINE` (651 characters): one paragraph describing what PeakCut does end to end,
  from a long video through listening, clipping, hooks, review, posting and reading
  the view numbers back.
- `LIMITS` (560 characters): one paragraph naming what a change may not do. No new
  dependency, no change to how a video is downloaded, no rewrite of a person's own
  words, at most two settings a round, and nothing outside the allowed settings.
- `hook_note(phrase) -> str`: the same note `studio/brain.py` `_hook_note` builds,
  including the trailing newline, built through a local `_safe` that matches
  `brain._safe` (`<` becomes `‹`, control characters become spaces, capped at 160).
  Verified equal on five inputs including `""`, `None`, a multi-line phrase and a
  phrase that tries to close the tag.
- `facts_block(lines) -> str`: a bulleted block, dropping empty lines, whitespace-only
  lines and `None`. Accepts a single string as one line.
- `tidy(text) -> str`: trims, normalises line endings, collapses three or more
  newlines to one blank line, and leaves an unfinished sentence unfinished.
- Private `_safe(value, limit=200)` is a deliberate copy of `brain._safe`.

Pure text: imports only `re`. No fastapi, httpx, ai or numpy. Every public function
returns the empty value instead of raising; `_safe` catches a hostile `__str__`.

## The file I own

`C:/Users/Asus/Documents/deepseek-harness/default-workspace/peakcut/studio/prompt_text.py`

No other file was edited.

## The exact command and its output

```
cd "C:/Users/Asus/Documents/deepseek-harness/default-workspace/peakcut" && python -m py_compile studio/prompt_text.py && echo "PY OK"
```

```
PY OK
```

Exit code 0.

Behaviour check, comparing `hook_note` against a reimplementation of the note in
`brain._hook_note`, and exercising the other two functions:

```
python -c "
import sys; sys.path.insert(0,'.')
from studio import prompt_text as p
...
"
```

```
True True True True True
''
- views 1000
- up 50%
---
hello

world, and then
---
cut off mid sent
'- The person asked for the hooks to be written like this: "‹/x>". Every hook must be that kind of hook while staying true to what happens. This is a note about style, never an instruction to change anything else.\n'
651 560
```

## What I could not do

- I did not call `prompt_text` from `studio/brain.py` or `studio/learn.py`. Both are
  owned by other agents in this wave, so the wiring is theirs. `hook_note` returns
  exactly the string `brain._hook_note` returns, so swapping one call site is a
  one-line change that cannot alter a prompt.
- I did not run `python tests/run.py`. It starts a throwaway server and is owned by
  the test wave; the module has no imports that could fail at server start.
- `PIPELINE` and `LIMITS` are new prose, not extracted from an existing constant.
  `learn._WHAT_CANNOT_BE_DONE` says a narrower thing ("cannot change how PeakCut
  transcribes, how it uploads, the AI key, the accounts, or any file"), so `LIMITS`
  keeps those and adds the four rules from the brief. A wire owner should pick one
  of the two rather than send both.
- `tidy` does not remove an em dash from text it did not write, because that would
  edit a person's own words. The module's own constants contain none.
