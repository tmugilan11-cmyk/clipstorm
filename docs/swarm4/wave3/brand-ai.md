# brand-ai: the improvement engine writes through the brand document

## What I built

`studio/brand_ai.py` is the bridge between a round of the improvement engine and the saved brand
document. It lets a round ask two questions without knowing the document's shape.

- `known() -> set` returns the brand keys a round may touch, read from `brand.DEFAULTS` and mapped from
  the learn setting names: `style -> style`, `hook_words -> hook_words`, `clip_len -> clip_len`,
  `sound -> sound`, `captions_always -> captions`. A setting the document does not keep is left out, so
  a round can never write into a key that would be dropped on save.
- `preview(user_id, changes) -> {"before", "after", "lines"}` shows what the document would look like,
  with one plain sentence per setting that moves, for example
  "Caption look would go from hormozi to beast." Nothing is written. `after` is the document as
  `brand.normalise` would really keep it, so the sentence is never a guess.
- `apply(user_id, changes) -> {"written", "ignored", "why"}` writes what the document accepts through
  `brand.save`, in one save, and returns a sentence for each change it refused. A value the document
  merely adjusted (a length held inside its range) is reported with `asked` beside `to`.

The document is the judge, not this file. An empty caption look, a length that is not a real number, a
word that is neither yes nor no, or a setting the brand has no home for is refused with a reason instead
of being silently replaced by a different number. A brand that will not load is the neutral look from
`brand.defaults()`, never an exception; `preview` and `apply` both return their empty shape instead of
raising.

`learn` is imported inside `_settings()` on purpose. It pulls in the AI settings, and a page reading a
preview must not fail to draw because that import failed. If it fails, the plain setting names are used,
so the five-name mapping still answers.

## The file I own

`studio/brand_ai.py` (364 lines). No other file was edited.

## The exact command and what it printed

```
$ cd peakcut && python -m py_compile studio/brand_ai.py && echo COMPILE_OK
COMPILE_OK

[exit code: 0]
```

Behaviour checked by hand against a throwaway data folder (`PEAKCUT_DATA=$(mktemp -d)`), with this
output from `preview` then `apply` on a fresh brand:

```
KNOWN ['captions', 'clip_len', 'hook_words', 'sound', 'style']
PREVIEW_LINES
  Caption look would go from hormozi to beast.
  Clip length would go from 30 seconds to 45 seconds.
  Captions would go from on to off.
AFTER style/clip_len/captions -> beast 45 False
PREVIEW WROTE NOTHING -> hormozi
APPLY why: Wrote 3 settings. One change was refused, with the reason beside it.
  written [{'setting': 'style', 'key': 'style', 'from': 'hormozi', 'to': 'beast'},
           {'setting': 'clip_len', 'key': 'clip_len', 'from': 30, 'to': 5, 'asked': 3},
           {'setting': 'sound', 'key': 'sound', 'from': '', 'to': 'funny'}]
  ignored [{'setting': 'nope',
            'why': "PeakCut's brand keeps nothing called nope, so that change would be dropped."}]
SAVED -> beast 5 funny
EMPTY {'written': [], 'ignored': [], 'why': 'There was nothing to apply.'}
```

The `asked: 3` on the length is the document clamping 3 seconds up to its own 5-second floor, and the
report says so rather than pretending 3 was kept.

A corrupt brand file (`brand_broken.json` holding `not json at all`) loaded as the neutral look:

```
PREVIEW lines: ['Caption look would go from hormozi to beast.']
APPLY why: Wrote 1 setting. One change was refused, with the reason beside it.
  ignored [{'setting': 'style',
            'why': 'Caption look would stay at hormozi, because a caption look cannot be empty.'}]
NO RAISE: ok
```

I did not run `python tests/run.py`. It starts a whole server, and this file is not wired into anything
yet, so the suite would exercise it only through the agents who own `learn.py` and `api_learn.py`.

## What I could not do

1. **Nothing calls this yet.** Wiring `brand_ai` into `learn.py` and `api_learn.py` belongs to the three
   wire agents in this wave, and I own only `studio/brand_ai.py`.
2. **A sound name is only lower-cased, not checked against a real pack.** `brand.normalise` says a
   missing sound pack must never block a save, so the check belongs where a clip is rendered, not here.
3. **A caption look is not checked against captions.STYLES.** The same reason: the renderer already
   falls back on an unknown look, and refusing it here would need reading a module the brief did not
   allow. `sound` and `style` are therefore accepted whenever they are a non-empty word.
4. **No test file of my own.** The brief said one file, and tests are a different owner in this wave.
