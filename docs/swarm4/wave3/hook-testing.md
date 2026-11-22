# hook-testing

## What I built

`studio/hookscore.py` gives a hook phrase a score from 0 to 100 without waiting for views, without a
model and without a network call. It is pure Python, uses only `unicodedata` and `typing`, and every
public function returns an empty shape instead of raising.

Public functions:

- `words(phrase)` -> list of words, punctuation and symbols removed, lowercased for comparison. The
  underscore is not a separator, so the word count stays the count a person would say. `don't` becomes
  `dont`, not `don t`.
- `score(phrase)` -> `{"score": int, "reasons": [str], "verdict": str}`. The score starts at 100 and the
  rules take points away, so a plain phrase that breaks no rule keeps 100. A blank or unreadable phrase
  returns 0 with the single reason `There is no hook to score.` and verdict `weak`.
- `compare(a, b)` -> `{"better": "a"|"b"|"same", "why": str, "a": dict, "b": dict}`. Equal scores answer
  `same`, and the sentence says both scores.
- `suggest(phrases, want=3)` -> the best of the phrases it was given, best first, blanks dropped, order
  kept among equal scores. It never invents a phrase, so a list of two returns two even when `want` is 5.

The rules and their weights, all in named constants at the top of the file:

| Rule | Weight | What it says |
|---|---|---|
| Under 2 words | 25 | PeakCut reads two words as the shortest thing that can be a hook |
| Past 7 words | 8 per extra word, capped at 24 | the clip moves on |
| Names nothing | 25 | no thing, number or consequence, so nothing is at stake |
| Opens with a filler | 20 | so, and, well, um, just, okay, hey |
| Bare question | 45 | ends in `?` and carries no stake word |
| Slow | 20, plus 10 past 3 seconds | `words / 2.5` seconds, past the 2 PeakCut wants for a first line |

Verdicts: `strong` at 85 or more, `workable` at 40 or more, otherwise `weak`. `strong` is set high on
purpose: the largest penalty a phrase can take and still be sound is a stray word (8, capped at 24), so
85 is the only threshold where `strong` means "broke no rule that matters" rather than "not badly
broken".

Two deliberate choices worth writing down, because they are judgement, not measurement:

- A filler never counts as an anchor. Without that rule the phrase `So` scored higher and was called
  workable, which is wrong on its face. Excluding fillers from the anchor check moved it to 30 and weak.
- A bare question costs 45 rather than 20. PeakCut treats "a bare question with no stakes" as a failure on
  its own, so at 20 it still scored 65 and read workable. At 45 it lands in the weak half.

No number in the file is presented as data, and none is attributed to the brief. `2.5 words per second` is
PeakCut's own reading pace, written as a named constant with a comment saying it is that pace and not a
measurement of any person. The same goes for every weight and for `2 seconds`: they are PeakCut's rules,
chosen and written down here, not quoted from anywhere and not measured from viewers.

## The file I own

`studio/hookscore.py`. I edited no other file.

## The command and its literal output

```
$ cd peakcut && python -m py_compile studio/hookscore.py; echo "EXIT=$?"
EXIT=0
```

A second run with sample phrases, to show the shape works end to end:

```
$ cd peakcut && python - <<'PY'
from studio import hookscore as h
given = ["", "So", "What happened?", "Do you like it?",
         "He lost the house in one bet", "You lose the account tonight"]
for phrase in given:
    got = h.score(phrase)
    print(repr(phrase), got["score"], got["verdict"])
print(h.suggest(given, 3))
PY
'' 0 weak
'So' 30 weak
'What happened?' 55 workable
'Do you like it?' 55 workable
'He lost the house in one bet' 80 workable
'You lose the account tonight' 100 strong
['You lose the account tonight', 'He lost the house in one bet', 'What happened?']
```

`He lost the house in one bet` used to read `90 strong`; the verdict threshold moved to 85 in the fix
pass, so a phrase carrying one real fault now reads `workable` rather than `strong`. `The shot` is the
shape `studio/brain.py` asks for and now keeps 100, and the one-word `CLUTCH` reads `workable` instead of
being told it is too short for a hook.

A check for em dashes and en dashes in the file returned no lines (`grep` exit 1, meaning no match).

## What I could not do

- I did not run `python tests/run.py`. It starts a server and downloads speech weights on a machine that
  may not have them, which does not fit a 25 minute budget, and this module has no import of its own to
  break. The compile check and the direct calls above are the evidence I have.
- I did not wire the module into `studio/api_learn.py`, `studio/learn.py` or the Improve page. Those
  files belong to the wire agents in this wave, and the brief says nobody else touches them. `score`,
  `compare` and `suggest` are the surface they would call. (As of the fix pass this is still true: no
  module in `studio/` imports `hookscore`, so the score is not on the page yet. Making it reachable is
  the owners' work, not this file's.)
- I did not tune the weights against real view data, because there is none available offline. The
  weights are readable judgement in one place, so a later owner can change them without reading the
  body of `score()`. That is a known open question, not a hidden one.
- I did not add a test file. `tests/` is outside the one file I own, and the wave brief assigns tests to
  another step.
