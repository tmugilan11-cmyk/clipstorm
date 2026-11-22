# 08 — Offline caption and hook translation (es fr pt de ar hi)

## 1. What it does

A creator can pick a target language for a clip, and both the burned-in captions and the hook title come out in
that language instead of English. Translation runs entirely on the server's own CPU against a small offline
neural model — no API key, no per-word cost, no network after the one-time model download of roughly 90–100 MB per
language. Because translated sentences have different word counts and different word lengths than the English they
replace, the timing is rebuilt: each new word gets a slice of the sentence's original time window, proportional to
its own length, so captions still land on the voice. The feature is strictly opt-in per clip: with no language set,
every code path below is skipped and the clip is exactly what PeakCut renders today.

## 2. Exact mechanics

Source: `gta6-clipper-main/translate.py` (105 lines, no classes, six public functions). It is ~90 % reusable as
written; the parts that must change are the storage directory, the download trigger, and the interaction with
PeakCut's romanisation step (§4.3).

### 2.1 Language set and module constants

`translate.py:7-13`

```python
DIR = Path.home() / ".local" / "share" / "argos-translate" / "packages"
LANGS = "es fr pt ar hi de he it nl tr ru pl id ja ko zh".split()   # translate.py:8
RTL = {"ar", "he", "fa", "ur"}                                     # translate.py:9
_cache = {}                                                        # translate.py:10
_PUNCT = re.compile(r'[,.;:"«»“”،。、¿¡।()]+')                       # translate.py:11
_BAD = re.compile(r"^(mierda|…)$", re.I)                           # translate.py:12-13, full table in §2.2
```

- `LANGS` is a **capability list, not a guarantee**. The comment on line 8 is explicit: "whatever the Argos index
  offers for English -> X". Only the six named in the feature (`es fr pt de ar hi`) are promised in the UI.
- `RTL` is **dead code**. Grep shows it appears only at its definition (`translate.py:9`) and inside an assertion in
  the offline selftest (`translate.py:82`). Neither `translate_text` nor `translate_words` ever reads it. Do not
  port it as if it drove anything — it does not. Arabic right-to-left layout is *not* handled by this module; it is
  handled (badly) downstream by the subtitle renderer, which is the largest single risk in this port (see §6.4).
- `_cache` is an unbounded module-level dict keyed by language code. Each entry holds a loaded
  `ctranslate2.Translator` plus a `sentencepiece.SentencePieceProcessor`. This is a single-user assumption; see §6.1.

`_PUNCT` is the exact character class to reproduce. It strips ASCII and typographic commas/periods/colons/semicolons,
both guillemet styles, both curly-quote styles, the Arabic comma `،`, the ideographic full stop `。`, the ideographic
comma `、`, the inverted Spanish marks `¿ ¡`, the Devanagari danda `।`, and both parentheses. It deliberately does
**not** contain `?`, `!` or `؟`, so all three question/exclamation marks survive into the caption. The comment on
line 11 calls this "same rule as clip.py clean(): only ? ! stay (also ؟ for Arabic)". Verified behaviour:

| input | `_PUNCT.sub("", …)` |
|---|---|
| `«¿Hola,») mundo.` | `Hola mundo` |
| `ok?` | `ok?` |
| `ça va !` | `ça va !` |
| `لماذا؟` | `لماذا؟` |

### 2.2 Profanity mask — the complete table

`translate.py:12-13`. English profanity is masked upstream before it reaches the screen; the translated line gets
the same treatment through a short hard-coded per-language list.

```python
_BAD = re.compile(r"^(mierda|joder|coño|puta|puto|cabrón|cabron|merde|putain|connard|salope|foda-se|porra|caralho|puta|scheiße|scheisse|fick\w*|arschloch|kurwa|كس\w*|شرموط\w*)$", re.I)
```

Reproduced as a table, in order, with the language each entry belongs to:

| # | pattern | language | note |
|---|---|---|---|
| 1 | `mierda` | es | |
| 2 | `joder` | es | |
| 3 | `coño` | es | |
| 4 | `puta` | es / pt | appears twice in the alternation (positions 4 and 14) — harmless |
| 5 | `puto` | es | |
| 6 | `cabrón` | es | accented form |
| 7 | `cabron` | es | unaccented form, listed separately |
| 8 | `merde` | fr | |
| 9 | `putain` | fr | |
| 10 | `connard` | fr | |
| 11 | `salope` | fr | |
| 12 | `foda-se` | pt | hyphenated |
| 13 | `porra` | pt | |
| 14 | `caralho` | pt | |
| 15 | `scheiße` | de | eszett form |
| 16 | `scheisse` | de | ss form |
| 17 | `fick\w*` | de | prefix match: `fick`, `ficken`, `ficker`… |
| 18 | `arschloch` | de | |
| 19 | `kurwa` | pl | not in the six shipped languages |
| 20 | `كس\w*` | ar | Arabic prefix match |
| 21 | `شرموط\w*` | ar | Arabic prefix match |

Anchored `^…$` with `re.I`, so it matches **whole words only** (except the `\w*` entries, which are prefix matches
on a single token). The mask itself:

```python
def _mask(w): return w[0] + "*" * (len(w) - 1) if _BAD.match(w) else w    # translate.py:41
```

First character kept, every remaining character replaced by `*`. So `mierda` → `m*****`, `Hola` → `Hola`,
`كسمك` → `ك***`. A single-character profanity would be returned unchanged (zero asterisks). Note it masks by
**character count, not grapheme count** — Arabic entries are treated as sequences of code points, so the asterisk
count does not match the visual length. That is the upstream behaviour; do not "fix" it without a decision.

### 2.3 Model loading and download

`translate.py:15-29`

```python
def _load(lang):
    import ctranslate2, sentencepiece
    if lang in _cache: return _cache[lang]
    find = lambda: next((x for x in DIR.glob(f"*en_{lang}*") if (x / "model").exists()), None)
    d = find()
    if not d:
        import argostranslate.package as p
        p.update_package_index()
        pk = next((a for a in p.get_available_packages() if a.from_code == "en" and a.to_code == lang), None)
        if not pk: raise SystemExit(f"no offline model for English -> {lang}")
        print(f"  downloading English -> {lang} model (~90 MB, once)", file=sys.stderr)
        zipfile.ZipFile(pk.download()).extractall(DIR)
        d = find()
    _cache[lang] = (ctranslate2.Translator(str(d / "model"), device="cpu", inter_threads=1),
                    sentencepiece.SentencePieceProcessor(model_file=str(d / "sentencepiece.model")))
    return _cache[lang]
```

Mechanics a build agent must reproduce exactly:

1. **Layout on disk.** One directory per language inside `DIR`. The glob is `*en_{lang}*` — it tolerates both
   `en_es` and the versioned `translate-en_es-1_9`. A candidate only counts if `<dir>/model/` is a directory.
2. **Lazy imports.** `ctranslate2` and `sentencepiece` are imported *inside* the function, and
   `argostranslate.package` is imported only on the download path. The comment at line 21 is load-bearing:
   `argostranslate.package` imports fine without torch; only `argostranslate.translate` needs stanza. **PeakCut must
   never import `argostranslate.translate`** — that pulls torch and stanza and would multiply the dependency
   footprint by an order of magnitude.
3. **Download.** `p.update_package_index()` fetches the Argos index (the only network call in the module), then the
   first package with `from_code == "en"` and `to_code == lang` is downloaded and extracted. The zip contains its own
   top-level folder, so `extractall(DIR)` lands correctly without a path prefix.
4. **Failure mode.** No matching package raises `SystemExit`, not an exception. That is fatal and wrong for a server
   — §4.2 replaces it with a caught error.
5. **Engine settings.** `device="cpu"`, `inter_threads=1`. `inter_threads` caps intra-op parallelism to one thread
   so a render does not starve the worker pool. Keep it.

### 2.4 The translation call

`translate.py:31-34`

```python
def _tr(texts, lang):
    t, sp = _load(lang)
    out = t.translate_batch([sp.encode(x, out_type=str) for x in texts],
                            beam_size=4, length_penalty=0.2, max_batch_size=16)
    return [re.sub(r"\s+", " ", sp.decode(o.hypotheses[0]).replace("▁", " ")).strip() for o in out]
```

- `sp.encode(x, out_type=str)` produces SentencePiece **string tokens**, not ids — that is what ctranslate2 wants.
- `beam_size=4`, `length_penalty=0.2`, `max_batch_size=16`. These are the whole tuning surface. Copy them.
- Decoding: take `hypotheses[0]`, decode, then `.replace("▁", " ")` — the comment on line 34 notes that the French and
  Portuguese models leave the literal SentencePiece word-start mark in the decoded output. Then collapse all
  whitespace runs to one space and strip. The `re.sub(r"\s+", " ")` is not cosmetic: it is what makes
  `.split()` produce clean tokens in §2.6.

### 2.5 Hook translation

`translate.py:36-39`

```python
def translate_text(text, lang):
    """One line (the hook) -> target language; same text back if lang is empty/en."""
    if not text or lang in ("", "en", None): return text
    return _tr([text.capitalize() if text.isupper() else text], lang)[0].translate(str.maketrans('', '', '()'))
```

Three load-bearing behaviours:

1. **No-op guard.** `not text or lang in ("", "en", None)` returns the input unchanged. This is the "off by default"
   contract — with no language, the hook string is never sent anywhere.
2. **ALL-CAPS downcasing.** If the whole hook `isupper()`, it is passed through `str.capitalize()` before
   translation. The comment: "ALL-CAPS hooks translate badly (sentence case is best)". PeakCut hooks are frequently
   all-caps, so this branch will fire often. Note `capitalize()` lowercases every remaining character — a hook like
   `I CAN'T BELIEVE THIS` becomes `I can't believe this`, and any acronym inside it is destroyed.
3. **Parenthesis strip.** `str.maketrans('', '', '()')` deletes *every* `(` and `)` from the *output*. The comment
   explains why: "Arabic wraps names in ( )". This runs unconditionally, so an intentional parenthesis in a Spanish
   hook is also removed. Preserve as-is; it is a deliberate trade.

### 2.6 Sentence splitting

`translate.py:43-49`

```python
def sentences(words, cap=22):
    out, cur = [], []
    for w in words:
        cur.append(w)
        if w.get("end") or len(cur) >= cap: out.append(cur); cur = []
    return out + ([cur] if cur else [])
```

- Input is a list of word dicts carrying at least `w`, `s`, `e`; the `end` key is optional.
- The word is appended **first**, then the boundary is tested — so a word flagged `end` closes its sentence
  *including itself*, and the cap closes at exactly `cap` words.
- Two close conditions: the word carries a truthy `end` flag, **or** the running sentence reached `cap` words.
- `cap=22` exists so that a transcript with no punctuation ("one run-on never becomes one huge translation",
  docstring line 44) still gets chunked into translatable units instead of one giant sentence.
- The trailing partial sentence is appended if non-empty.

Verified by `translate.py:78-79`: 50 synthetic words with `end` set on index 5 and none after produce sentence
lengths `[6, 22, 22]` — the end flag closes the first at 6, and the two remaining 44 words are cut by the cap.

### 2.7 Re-timing — `spread`

`translate.py:51-57`

```python
def spread(tokens, s0, e1, end):
    """Place translated tokens over [s0, e1], time share proportional to word length."""
    n = [len(t) + 1 for t in tokens]; tot = sum(n); t0 = s0; res = []
    for i, (t, k) in enumerate(zip(tokens, n)):
        t1 = e1 if i == len(tokens) - 1 else t0 + (e1 - s0) * k / tot
        res.append(dict(w=t, s=round(t0, 3), e=round(t1, 3), end=bool(end and i == len(tokens) - 1))); t0 = t1
    return res
```

The formula, stated plainly:

- Weight of token *i*: `n[i] = len(token) + 1`. The `+1` gives every word a minimum weight so a one-letter word
  (`a`, `y`, `e`) still gets a visible slice and does not collapse to zero duration.
- Total weight: `tot = Σ n[i]`.
- Token *i* starts where token *i−1* ended (`t0 = t1` each iteration), so the output is **contiguous with no gaps
  and no overlaps** — asserted at `translate.py:77`.
- Token *i*'s end is `t0 + (e1 − s0) · n[i] / tot`.
- **The last token is forced to `e1`** regardless of its computed share, so rounding never leaves a sliver of the
  sentence's original window unfilled. Asserted at `translate.py:76`: `sp[0]["s"] == 1.0 and sp[-1]["e"] == 2.0`.
- `end` is set on the last token only, and only when the caller passed `end=True`.
- All times rounded to 3 decimal places.

Consequence to be aware of: the timing is **proportional to character count in the target language**, not to any
real measurement of the translated speech. A Spanish sentence is typically ~20 % longer in characters than its
English source, so individual words drift within the sentence window; the sentence boundaries stay exact, which is
what keeps the caption on the voice.

### 2.8 The main entry point — `translate_words`

`translate.py:59-71`

```python
def translate_words(words, lang):
    """words = [{"w","s","e","end"}] in English (raw, unmasked is best) -> same shape in `lang`, ends kept."""
    if lang in ("", "en", None): return words
    ss = sentences(words)
    texts = [" ".join(w["w"] for w in s) for s in ss]
    out = []
    for s, tx in zip(ss, _tr(texts, lang)):
        toks = []
        for y in re.sub(r"\s+([?!؟])", lambda m: m[1], tx).split():
            y = _PUNCT.sub("", y)
            if y: toks.append(_mask(y))
        if toks:
            out += spread(toks, s[0]["s"], s[-1]["e"],
                          s[-1].get("end") or re.search(r"[.?!؟]$", tx) is not None)
    return out
```

Step by step, because every line matters:

1. **No-op guard returns the same object**, `return words` (identity, asserted at `translate.py:82` with `is words`).
   In a server this is a mutation hazard — see §4.2.
2. **Split** into sentences with `sentences(words)` using the default `cap=22`.
3. **Join** each sentence's words with single spaces into one string per sentence. The whole sentence is translated
   as a unit; word-level translation would destroy grammar.
4. **One `_tr` call for all sentences of the clip** — batched, so a 60-second clip is one inference call, not one
   per sentence.
5. **Detach trailing punctuation before splitting.** `re.sub(r"\s+([?!؟])", lambda m: m[1], tx)` removes the space
   before a `?`, `!` or Arabic question mark `؟`, gluing it to the preceding word. Comment on line 67: French
   `" ?"` would otherwise become a caption word of its own — a lone `?` displayed as a word. This runs **before**
   `.split()`.
6. **Strip punctuation per token** with `_PUNCT`, then drop any token that became empty.
7. **Mask** each surviving token with `_mask`.
8. **Re-time** with `spread`, over `[s[0]["s"], s[-1]["e"]]` — the first word's start to the last word's end of the
   *English* sentence. The `end` argument is the OR of two things: the source's last word carried `end`, **or** the
   translated text ends with `.`, `?`, `!` or `؟`.
9. **Empty results are dropped**: if every token was punctuation, `spread` is never called and that sentence
   contributes nothing.

### 2.9 Call site in the source

`clip.py:553-557`

```python
lang = str(opt("lang", opts, brand, "") or "")  # caption language (es fr pt de ar hi): translate.py is only imported
                                                # when one is set
words = [dict(w=w["w"] if lang else clean(w["w"]), s=w["s"] - start, e=w["e"] - start,
              end=bool(re.search(r"[.?!]$", w["w"]))) for w in allw ...]
if lang:
    import translate
    words = [w | dict(w=clean(w["w"])) for w in translate.translate_words(words, lang)]
    hook = translate.translate_text(hook, lang)
    keys = ""                                   # keywords are English
```

Three things to carry over:

- **`end` is synthesised from the raw English word's trailing `[.?!]`** — `bool(re.search(r"[.?!]$", w["w"]))`. The
  ASR does not supply an `end` flag. PeakCut must do the same before calling `sentences()`.
- The module is **imported only when a language is set** (`import translate` inside the `if`). Keep that: an
  installation that never translates must never pay the import cost.
- `keys = ""` — keywords/hashtags are deliberately left in English.

### 2.10 Constants summary

| constant | value | where |
|---|---|---|
| `cap` (words per translatable sentence) | `22` | `translate.py:43` |
| `beam_size` | `4` | `translate.py:33` |
| `length_penalty` | `0.2` | `translate.py:33` |
| `max_batch_size` | `16` | `translate.py:33` |
| `inter_threads` | `1` | `translate.py:28` |
| `device` | `"cpu"` | `translate.py:28` |
| spread weight | `len(token) + 1` | `translate.py:53` |
| time rounding | 3 decimals | `translate.py:56` |
| model size on disk | ~90 MB (brief says ~100 MB) | `translate.py:2`, `SKILL-REFERENCE.md:55` |
| mask | keep first char, `*` for the rest | `translate.py:41` |

### 2.11 The offline selftest — reuse it verbatim

`translate.py:73-83` needs **no model** and is the cheapest possible proof that the port is faithful. It asserts,
in order: `spread` bounds and last-token `end`; contiguity between adjacent tokens; longer word gets a longer slice;
`sentences` yields `[6, 22, 22]`; `_PUNCT` strips `«¿Hola,») mundo.` to `Hola mundo` and leaves `ok?` alone;
`_mask("mierda") == "m*****"`, `_mask("Hola") == "Hola"`, `_mask("كسمك")[0] == "ك"`; `"ar" in RTL`,
`"es" not in RTL`; `translate_words(W, "en") is W` and `translate_text("hi", "") == "hi"`. Port all of it.

## 3. PeakCut today

### 3.1 What already exists that overlaps

| Surface | Location | What it does |
|---|---|---|
| Caption builder | `peakcut/studio/render.py:159` `build_ass(words, start, end, hook, style_name, highlight, hook_y, cap_y) -> str` | Builds the ASS file: per-word placement, per-word pop animation. |
| Caption looks | `peakcut/studio/render.py:14-21` `STYLES` | Three entries, not one: `bounce` (Poppins ExtraBold, 132, `upper` True, 3 words/group), `hype` (Anton, 152, `upper` True, 2/group), `clean` (Poppins ExtraBold, 100, `upper` False, 4/group). |
| Non-Latin fallback | `peakcut/studio/render.py:195-201` | If `roman.drawable(t)` is false for any word, the group is drawn **as one whole centred line** in a system font at `fs = max(44, min(int(size*0.7), int(1500/max(1,len(line))*1.6)))`, losing per-word timing and the pop. |
| Only-Latin rule | `peakcut/studio/roman.py:44-46` `drawable()` | `not any(ch.isalpha() and not (ord(ch) < 0x250 or 0x1E00 <= ord(ch) <= 0x1EFF) for ch in text)`. The bundled fonts are Latin-only, so **every Arabic and Hindi word fails this test.** |
| Romanisation | `peakcut/studio/roman.py:261-263` `words(ws)` | Rewrites every word containing Devanagari, Urdu/Arabic, Cyrillic, Greek or Hangul into Latin letters. Timings untouched. |
| Line-level translation | `peakcut/studio/brain.py:500-520` `translate_caption_words(words, lang, title)` | **The opposite direction**: translates a non-English clip INTO English, via the AI, line by line, then `_spread`s the result. Raises if the AI's answer does not match the line count. |
| Always-English captions | `peakcut/studio/brain.py:523-540` `english_captions(words, lang, title, youtube_english)` | Orchestrates: `needs_translation(lang)` → YouTube English first, then AI, then romanised-as-heard. |
| Language gate | `peakcut/studio/brain.py:482` `KEEP_LANGS = ("en","hi","ur")`; `:485-488` `needs_translation(lang)` | Only three languages keep their script; everything else is forced to English. |
| Caption word cache | `peakcut/studio/jobs.py:405-420` `_caption_words(job, clip, words, off)` | Cache key at `:406` is `span = [round(clip["start"],2), round(clip["end"],2), "en2"]`; on hit reuses `clip["fixed_words"]` if none of them need romanising (`:407-409`); on miss calls `brain.english_captions` (`:414`) and stores (`:416`). **Ends with `roman.words(raw)` at `:420`.** |
| Hook path | `peakcut/studio/jobs.py:384` | `local = dict(clip, start=…, end=…, hook=roman.to_roman(clip.get("hook") or ""))` — the hook is romanised, then passed to `render.render_clip`. |
| Render entry | `peakcut/studio/jobs.py:373-402` `render_one(job, clip, words)` → `render.render_clip` at `:386` → `build_ass` at `render.py:276-277` | The only place captions reach ffmpeg. |
| Job options | `peakcut/studio/jobs.py:110-114` `DEFAULTS`/`LIMITS`; `:117-142` `clean_options`; `:361-367` `request_render` | `style`/`layout` validated against `render.STYLES`/`render.LAYOUTS` at `:131-134`; the `else` branch at `:135-138` does `float(v)` for everything unrecognised. |
| Render concurrency | `peakcut/studio/jobs.py:663` | `renders = ThreadPoolExecutor(2 if cpus < 8 else min(6, cpus // 6))` — up to six clips render at once, each calling `build_ass`. |
| Settings pattern | `peakcut/studio/ai.py:39-70`; `peakcut/studio/server.py:1318-1340`, `:1343-1347`, `:1350-1353`, `:1356-1396` | File-over-env merge, atomic `tmp.replace(f)`, `os.chmod(tmp, 0o600)`, secrets never in `public()`. |
| Admin gate / throttle | `peakcut/studio/server.py:310` `_admin(request)`; `:633-637` `_throttle(key, limit, window, msg)` | Every settings route starts with `_admin`; model/test routes add `_throttle("…:" + ctx.uid(), N, 600)`. |
| Data dirs | `peakcut/studio/config.py:119-123` | `DATA_DIR`, `USERS_DIR`, `MODELS_DIR = Path(env("PEAKCUT_MODELS") or DATA_DIR / "models")`, `TMP_DIR`, `FONTS_DIR`. |
| Output frame | `peakcut/studio/config.py:259` | `OUT_W, OUT_H, OUT_FPS = 1080, 1920, 30`. |
| Dependencies | `peakcut/requirements.txt:1-12` | Twelve pins, **none of them `ctranslate2`, `sentencepiece` or `argostranslate`.** |

### 3.2 The gap, stated concretely

1. **No outbound translation exists at all.** `brain.py:500` translates *into* English. Nothing translates a clip
   into `es/fr/pt/de/ar/hi`. `KEEP_LANGS` (`brain.py:482`) actively forces every other language to English.
2. **The romaniser destroys the deliverable.** `_caption_words` returns `roman.words(raw)` at `jobs.py:420`, and
   `roman.words` rewrites Arabic and Devanagari into Latin letters (`roman.py:261-263`). A port that inserts the
   translation *before* that line produces transliterated Arabic — `marhaba` instead of `مرحبا` — which is worse
   than English for an Arabic viewer. **The translation must run after the romanisation, and the romanisation must
   be skipped on that path.**
3. **The cache key would serve the wrong language.** `jobs.py:406` is `[start, end, "en2"]`. Re-rendering the same
   span with a different `lang` would hit the cache and reuse English words. It must become `"en2:es"` etc.
4. **`build_ass` cannot draw the result.** `roman.drawable` (`roman.py:44`) rejects every Arabic and Hindi word, so
   each caption group falls into the whole-line branch at `render.py:195-201`: one centred shrunk line per group,
   no per-word pop, and the font is whatever the system has. `STYLES` also apply `.upper()` (`render.py:194`),
   harmless for Arabic but pointless for German `ß`.
5. **No settings surface.** There is no `translate.json`, no `GET/PUT /api/translate`, no admin download action, no
   way to see which models are installed.
6. **No dependency.** `ctranslate2` and `sentencepiece` are absent from `requirements.txt`; `argostranslate` is
   absent too. This is the one place the brief's "no new heavyweight dependencies" rule (`GTA6-PORT-BRIEF.md:26-28`)
   must be satisfied by an explicit, documented opt-in.

## 4. Port plan

### 4.1 New module: `peakcut/studio/translate.py`

Created per `GTA6-PORT-BRIEF.md:76-77`, which already names `translate.py` as a one-concern module. Public surface,
with type hints:

```python
"""Offline caption and hook translation (es fr pt de ar hi)."""
from __future__ import annotations
import re, threading
from collections import OrderedDict
from pathlib import Path
from . import config

LANGS: tuple[str, ...] = ("es", "fr", "pt", "de", "ar", "hi")
LABELS: dict[str, str] = {"es": "Spanish", "fr": "French", "pt": "Portuguese",
                          "de": "German", "ar": "Arabic", "hi": "Hindi"}
RTL: frozenset[str] = frozenset({"ar"})          # informational only; nothing shapes text with it
PUNCT = re.compile(r'[,.;:"«»“”،。、¿¡।()]+')
BAD = re.compile(r"^(mierda|…|شرموط\w*)$", re.I)  # the 21-entry table from §2.2, verbatim
CAP_WORDS = 22


def models_dir() -> Path: ...
def installed(lang: str) -> bool: ...
def available() -> list[str]: ...
def ensure_model(lang: str) -> Path: ...
def translate_text(text: str, lang: str) -> str: ...
def sentences(words: list[dict], cap: int = CAP_WORDS) -> list[list[dict]]: ...
def spread(tokens: list[str], s0: float, e1: float, end: bool) -> list[dict]: ...
def translate_words(words: list[dict], lang: str) -> list[dict]: ...
```

Function-by-function contract:

| function | input | output | notes |
|---|---|---|---|
| `models_dir() -> Path` | — | `config.MODELS_DIR / "argos"` | **Not** `Path.home()`. See §4.2. Must tolerate being called repeatedly (mkdir `parents=True, exist_ok=True`). |
| `installed(lang: str) -> bool` | language code | True if `<models_dir()>/*en_{lang}*/model/` exists | Cheap glob; safe on every settings GET. Never imports ctranslate2. |
| `available() -> list[str]` | — | the subset of `LANGS` where `installed()` is True | What the settings page shows as "downloaded". |
| `ensure_model(lang: str) -> Path` | language code | the model directory | Validates `lang in LANGS` (`ValueError` otherwise — maps to `HTTPException(400)`); returns early if installed, else downloads via `argostranslate.package`. **Raises `RuntimeError`** on "no package for this language" instead of `SystemExit`. Holds a per-language lock so two concurrent admin requests cannot double-download. |
| `translate_text(text: str, lang: str) -> str` | one line, language | translated line | Identical semantics to `translate.py:36-39`: `""`/`"en"`/`None` returns the input unchanged; `.capitalize()` when `isupper()`; strip every `(`/`)` from the output. |
| `sentences(words, cap=22) -> list[list[dict]]` | word dicts | list of word-dict lists | Verbatim port of `translate.py:43-49`. Pure, no model, unit-testable offline. |
| `spread(tokens, s0, e1, end) -> list[dict]` | token strings + window | `[{"w","s","e","end"}]` | Verbatim port of `translate.py:51-57`, rounding to 3 dp. Pure. |
| `translate_words(words: list[dict], lang: str) -> list[dict]` | `[{"w","s","e", optional "end"}]` | a **new** list, same keys plus `end` | Verbatim port of `translate.py:59-71`, **except** it returns a copy rather than `words` itself (§4.2). |

### 4.2 Storage, engine lifetime, concurrency

- `DIR` becomes `config.MODELS_DIR / "argos"` (`config.py:121`). `MODELS_DIR` is already `PEAKCUT_MODELS`-overridable
  and already created at boot (`config.py:142`), so a deployment can put the models on a bigger volume, and no
  per-user home directory is assumed.
- Engine construction is unchanged from `translate.py:28`:
  `ctranslate2.Translator(str(d / "model"), device="cpu", inter_threads=1)` +
  `sentencepiece.SentencePieceProcessor(model_file=str(d / "sentencepiece.model"))`.
- **Guard the loaded translators with a lock.** PeakCut renders with a `ThreadPoolExecutor` of up to six threads
  (`jobs.py:663`); ctranslate2's Python wrapper is not documented as safe for concurrent `translate_batch` on one
  translator. Put a `threading.Lock` around the `translate_batch` call (per language), not around the whole function,
  so two clips in different languages still run in parallel.
- **Cap the cache.** Replace the unbounded `_cache` with an LRU holding at most **2** loaded languages (each is
  roughly one model's worth of RAM plus the sentencepiece processor). Eviction just drops the tuple; the next call
  reloads from disk. An `OrderedDict` + `move_to_end` is enough — do not add a dependency.
- **Import lazily.** `ctranslate2` and `sentencepiece` are imported inside the loader, exactly as at
  `translate.py:16`, and the module itself is imported inside the caller, matching `clip.py:556`.

### 4.3 Wiring into the pipeline

The integration point is **`_caption_words`** at `peakcut/studio/jobs.py:405`, plus the hook line at `jobs.py:384`.
Concretely, the build agent changes:

**(a) `peakcut/studio/jobs.py:405-420` — `_caption_words`.**

Current tail:

```python
span = [round(clip["start"], 2), round(clip["end"], 2), "en2"]      # :406  "en2": captions made always-English
…
return [dict(w, s=w["s"] - off, e=w["e"] - off) for w in roman.words(raw)]   # :420
```

New shape — the order of operations is what matters:

1. Read `lang = str(clip.get("lang") or job.get("target_lang") or "")`. Validate against `translate.LANGS`; an
   unknown value falls back to `""` (today's behaviour) rather than raising.
2. Change the cache key at `:406` to `span = [round(clip["start"],2), round(clip["end"],2), "en2", lang]`. Without
   this, switching a clip from English to Spanish and back serves stale words from `clip["fixed_words"]`.
3. Keep the existing `brain.english_captions` call (`:414`) **exactly as it is** — it is what produces clean,
   correctly spelled, correctly timed English words, and it is also the fallback if translation fails.
4. Apply the romanisation (`roman.words`) only when `lang == ""`. When a target language is set, **skip it**: its
   whole purpose is to destroy the script we are trying to produce.
5. Translate last: `raw = translate.translate_words(raw, lang)`, wrapped in `try/except Exception` that logs and
   falls back to the English words — the same defensive shape as the existing `except Exception: pass` at
   `jobs.py:417-418`. A missing model or a failed download must never fail a clip.
6. Keep the `end` flags. `_caption_words` currently emits `w`, `s`, `e` only; synthesise `end` before calling
   `translate_words`, the way the source does at `clip.py:554`:
   `end=bool(re.search(r"[.?!]$", w["w"]))`.

**(b) `peakcut/studio/jobs.py:384` — the hook.**

```python
local = dict(clip, start=clip["start"] - off, end=clip["end"] - off,
             hook=roman.to_roman(clip.get("hook") or ""))
```

The hook must be translated **after** `roman.to_roman` and only when a language is set — same reason as the
captions: romanising an Arabic hook produces Latin letters. Shape:

```python
hook = roman.to_roman(clip.get("hook") or "")
if lang:
    try: hook = translate.translate_text(hook, lang)
    except Exception: pass          # the English hook still renders
local = dict(clip, start=…, end=…, hook=hook)
```

Note `translate_text` applies `.capitalize()` when the hook `isupper()`, so it must receive the *displayed* hook
(already romanised), not the raw one.

**(c) `peakcut/studio/jobs.py:110-142` — options.**

- Add `"lang": ""` to `DEFAULTS` (`:110-111`). Because `clean_options` skips `v in ("", None)` at `:126`, an empty
  string is simply absent from `out` — which is the correct "feature off" representation.
- `lang` must **not** fall into the `else` branch at `:135-138`, which coerces to `float`. Add a branch beside
  `style`/`layout` at `:131-134`: `elif k == "lang": v = v if v in translate.LANGS else ""`.
- In `request_render` (`:361`), add `"lang"` to the loop's key tuple so a per-clip re-render can switch language, and
  give it an explicit cap in the length map: `{"hook": 60, "title": 100, "description": 2000}.get(k, 20)` currently
  defaults to 20, which is harmless for `lang` but explicit is better.

**(d) `peakcut/studio/server.py` — settings routes.**

Follow the transcription block exactly (`:1318-1396`): `_translate_file()` returning
`config.DATA_DIR / "translate.json"`, a module-level `_translate_lock = threading.Lock()`, `_translate_saved()` doing
the file-over-env merge with the `isinstance(data, dict)` guard (`:1333-1334`), and `_translate_public()` which never
leaks anything secret — here nothing is secret, so it returns the enabled language, the installed list and the
in-flight download state.

| route | gate | behaviour |
|---|---|---|
| `GET /api/translate` | `_admin` | `{"lang": str, "installed": [str], "langs": [{"code","label"}], "downloading": str\|None}` |
| `PUT /api/translate` | `_admin` | Body `{"lang": "es"\|""}`. 400 if the code is not in `translate.LANGS`. Atomic write via `tmp` + `os.chmod(tmp, 0o600)` + `tmp.replace(f)` (`server.py:1378-1386` pattern). Returns `_translate_public()`. |
| `POST /api/translate/model` | `_admin` + `_throttle("trmodel:" + ctx.uid(), 6, 600)` | Body `{"lang": "es"}`. Kicks `translate.ensure_model` onto the existing job queue rather than blocking the request — a 90–100 MB download must not hold an HTTP connection. `502` for an upstream/index failure, `400` for a language with no package. |

**(e) UI — `peakcut/web/index.html`.** A new settings tab registered in `setTabs()`, with its icon added to the
`I` map (`const ic = n =>`). The per-clip language picker goes in the existing clip editor, next to the style and
layout controls that `request_render` already accepts. Per `GTA6-PORT-BRIEF.md:29-30`, a user who never opens it must
get today's clips.

### 4.4 Renderer changes — the part that decides whether Arabic works at all

`build_ass` (`render.py:159`) needs two targeted changes; neither may alter English output.

1. **`render.py:195-201`, the drawable branch.** Today any group containing a non-Latin word is collapsed to one
   centred line. With a target language set, *every* Arabic and Hindi group takes this path, so the caption style
   silently degrades. Two acceptable resolutions, in order of preference:
   - Ship a font with Arabic and Devanagari coverage in `peakcut/studio/fonts/` and extend `FONT_FILES`
     (`render.py:24`) plus `roman.drawable`; or
   - Accept the whole-line branch deliberately, and document it: for `ar`/`hi` the caption is one centred line per
     group in a system font, with no per-word pop. This is effectively what the upstream single-user tool does too,
     and it is legible.

   Either way the build agent must **state which** was chosen.
2. **`render.py:194`, the uppercase rule.** `texts.append(t.upper() if st["upper"] else t)` — `bounce` and `hype`
   both set `"upper": True` (`render.py:16-18`). Uppercasing Arabic is a no-op; uppercasing German is correct;
   uppercasing French `é` yields `É` correctly in Python. Leave it, but do not add `casefold()` anywhere — it would
   corrupt `ß` into `ss` and change string length.

No other renderer change is required. `_clean` (`render.py:91`) already strips `{`, `}`, `\` and control characters,
which is exactly the injection guard translated text needs before it reaches ASS. `CAP_MAX_W = 960` (`render.py:25`)
already shrinks an over-wide phrase (`render.py:205-208`), and translated romance languages run ~20 % longer, so that
path will fire more often — verify it visually, do not change the constant.

### 4.5 What must not change

- `brain.english_captions` / `translate_caption_words` / `fix_caption_words` (`brain.py:500-547`) — the *into-English*
  direction stays exactly as it is. Two translation directions coexist; do not merge them.
- `roman.words` (`roman.py:261-263`) — still used on the English path. Only the new target-language path skips it.
- `render.build_ass`'s English output — byte-identical when `lang == ""`.

## 5. Data files

**`config.DATA_DIR / "translate.json"`** — the settings file, mode `0600`, written atomically.

```json
{
  "lang": "es"
}
```

| field | type | default | meaning |
|---|---|---|---|
| `lang` | `str` | `""` | Server-wide default target language. `""` = off. Must be one of `translate.LANGS`. |

The same file may carry an optional `"downloading"` string written by the download job so a restart mid-download is
visible; it is informational and must never be trusted as state.

**Model directories** — `config.MODELS_DIR / "argos" / <package folder> /`, each containing `model/` and
`sentencepiece.model`. Created by `ensure_model`; **gitignored and never committed**. Roughly 90–100 MB per
language, six languages maximum → ~600 MB worst case on the data volume.

**No per-user JSON.** The language default is server-wide because the models are server-wide; a per-clip override
lives in the job/clip dict, not in a new file.

**`peakcut/requirements-translate.txt`** (new, optional — see §6.3):

```
ctranslate2
sentencepiece
argostranslate
```

Installed with `--no-deps` for the reason the source gives at `gta6-clipper-main/requirements-translate.txt:3`: the
full dependency set pulls torch.

## 6. Risks

1. **Unbounded translator cache.** `_cache` (`translate.py:10`) never evicts. In a server, six languages × (model +
   sentencepiece) will exhaust RAM. Mitigation: LRU of 2 (§4.2).
2. **Thread safety.** Up to six concurrent renders (`jobs.py:663`) can call `translate_batch` on one translator.
   ctranslate2 does not document that as safe. Mitigation: a per-language lock around the inference call.
3. **Dependency weight.** `ctranslate2` and `sentencepiece` are not in `requirements.txt` (`requirements.txt:1-12`).
   `argostranslate` is only needed for the *download* path. This is the one deliberate exception to
   `GTA6-PORT-BRIEF.md:26-28`; the build agent must say so explicitly in the PR and keep the import lazy so an
   install without them still boots and renders English clips.
4. **RTL is not implemented.** `RTL` (`translate.py:9`) is unused, and libass will not shape or reorder Arabic
   correctly from a naively built ASS file: the glyphs are unjoined and the word order is visual-left-to-right.
   Arabic will render *legibly but wrongly* unless the build agent either (a) pre-shapes the string with
   `arabic-reshaper` + `python-bidi` (two new dependencies), or (b) documents Arabic as "text correct, shaping
   imperfect". Do not ship `ar` claiming it looks right without looking at a frame.
5. **`SystemExit` instead of an exception.** `translate.py:24` raises `SystemExit` for a missing package. In a
   FastAPI worker that is fatal and not caught by `except Exception`. Must become `RuntimeError`.
6. **Identity return is a mutation hazard.** `translate_words(words, "en")` returns the *same list object*
   (`translate.py:61`). Callers in a server may hold that list elsewhere. Return a copy.
7. **Download on the request thread.** `ensure_model` downloads ~100 MB. Doing that inline in `PUT /api/translate`
   holds a connection for minutes and can be killed by a proxy timeout. Must go on the job queue (§4.3d).
8. **Cache key collision.** If `jobs.py:406` is not extended with the language, a clip re-rendered in a second
   language reuses the first language's `fixed_words`. Silent, wrong, and easy to miss.
9. **Single-user assumption: `Path.home()`.** `translate.py:7` writes into the invoking user's home. A server may
   run as a service account with no writable home, or with a home on a small volume. Use `config.MODELS_DIR`.
10. **Single-user assumption: `print(...)` to stderr.** `translate.py:25` narrates the download with `print`.
    A server needs it in the job log / `creators.log` (`jobs.py:392`), not stdout.
11. **`capitalize()` destroys acronyms.** `translate_text` (`translate.py:39`) lowercases everything after the first
    character when the hook is all-caps. `GTA 6 IS CRAZY` → `Gta 6 is crazy`. Acceptable for a hook, but it is a
    visible change; document it.
12. **Longer romance-language captions.** `CAP_MAX_W = 960` (`render.py:25`) will shrink more phrases, and `_groups`
    (`render.py:99-109`) breaks at 16 characters, so translated groups will be shorter and the caption will flicker
    faster. Cosmetic, but verify on one `es` clip before shipping.

## 7. Verification

**Offline, no model, runs in CI** — port the source's own assertions (`translate.py:73-83`) into
`peakcut/tests/test_translate.py`, in the existing house style (`check(name, condition)`, `main(data)`, registered in
`tests/run.py`):

```
cd peakcut && python tests/test_translate.py
```

It must assert, without downloading anything: `spread` bounds and contiguity (`sp[0]["s"] == 1.0`,
`sp[-1]["e"] == 2.0`, `sp[-1]["end"]`, adjacent `e == s`, longer word gets a longer slice); `sentences` on 50 words
with an end flag at index 5 yields `[6, 22, 22]`; `PUNCT.sub("", "«¿Hola,») mundo.") == "Hola mundo"` and
`PUNCT.sub("", "ok?") == "ok?"`; masking `mierda` → `m*****` and `Hola` → `Hola`; `translate_words(W, "en") == W`
and `translate_text("hi", "") == "hi"`.

**With one model installed** — a second test guarded on `translate.installed("es")`:

```
cd peakcut && python -c "from studio import translate as t; print(t.translate_text('We are going to the beach. It is a very good day.', 'es'))"
```

must contain `playa`, and the word list from `translate_words` must carry exactly two words with `end=True` and a
last `e` equal to the English last `e` — the exact assertions at `translate.py:88-92`.

**End to end, in the app** — start PeakCut, upload a 30 s English clip, set the clip language to `es`, render, then:

```
ffprobe -v error -show_entries stream=codec_type -of csv <clip>.mp4        # file is playable
grep -c "^Dialogue:" <clip>.ass                                            # captions were emitted
```

and read the `.ass` — a translated clip must contain Spanish words in the caption events and an accented character
somewhere (proving UTF-8 survived). For `ar`, additionally open one frame and confirm the glyphs are joined.

**Regression gate** — `python tests/run.py` must stay green, in particular the existing captions and romanisation
suites (`tests/test_captions.py`, `tests/test_roman.py`), and a render with `lang == ""` must produce an `.ass`
byte-identical to the pre-change output.
