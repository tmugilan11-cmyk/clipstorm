"""Offline caption and hook translation into Spanish, French, Portuguese, German, Arabic or Hindi.

Nothing here talks to a cloud service. A language needs a small Argos/OPUS model (about 90 MB per language) once;
it is unpacked into PeakCut's own models folder and then runs on this machine's CPU through ctranslate2 and
sentencepiece. `text()` and `words()` never touch the network: only `ensure_model()` downloads, and only when the
owner asks for it from the settings page (a 90 MB download must not sit on a render thread).

The two pip packages are optional on purpose, so a server that never translates still boots and renders English
clips exactly as before: `available()` answers whether they are here, and the translation calls raise a
TranslateError that names the install line instead of failing the request or the clip.
"""
from __future__ import annotations

import json
import os
import re
import threading
import zipfile
from collections import OrderedDict
from pathlib import Path

from . import config

# code -> the name shown on the settings page. This is a capability list, not a guarantee: a language can be
# chosen only once its model is downloaded, and there is one Argos package per language for English -> X.
LANGS: dict[str, str] = {"es": "Spanish", "fr": "French", "pt": "Portuguese",
                         "de": "German", "ar": "Arabic", "hi": "Hindi"}
LABELS = LANGS                  # same table, under the name the settings code reads
RTL = frozenset({"ar"})         # shown to the dashboard only; nothing in this module shapes Arabic text
CAP_WORDS = 22                  # a transcript with no punctuation is cut this often, so one run-on never becomes one huge translation
BEAM = 4                        # the whole tuning surface of the model, as in the original
LEN_PEN = 0.2
BATCH = 16
PUNCT = re.compile(r'[,.;:"«»“”،。、¿¡।()]+')   # only ? ! and ؟ survive into a caption
# English profanity is masked before it reaches the screen; the translated line gets the same mask, from a short
# per-language list. Anchored, so whole words only (the \w* entries also catch ficken/ficker and Arabic prefixes).
BAD = re.compile(r"^(mierda|joder|coño|puta|puto|cabrón|cabron|merde|putain|connard|salope|foda-se|porra|caralho|"
                 r"puta|scheiße|scheisse|fick\w*|arschloch|kurwa|كس\w*|شرموط\w*)$", re.I)
DROP_PARENS = str.maketrans("", "", "()")       # the Arabic model wraps names in ( ), which captions cannot show
INSTALL = "pip install ctranslate2 sentencepiece"


class TranslateError(RuntimeError):
    """Translation could not run. The caller logs it and keeps the English captions, so a clip never fails."""


def _no_engine() -> TranslateError:
    return TranslateError("Offline translation needs two packages PeakCut does not ship with. On the server run "
                          f"'{INSTALL}' (then restart PeakCut).")


# ---------------------------------------------------------------- the engine, and where the models live
_ENGINE_READY = False


def available() -> bool:
    """Are the two translation packages installed here? False keeps every other part of PeakCut working."""
    global _ENGINE_READY
    if _ENGINE_READY:
        return True
    try:
        import ctranslate2      # noqa: F401  imported late: an install without it must still boot
        import sentencepiece    # noqa: F401
    except Exception:           # noqa: BLE001  a broken wheel raises OSError, not just ImportError
        return False
    _ENGINE_READY = True
    return True


def models_dir() -> Path:
    """Where the per-language model folders live: inside PeakCut's models folder, never a user's home."""
    d = config.MODELS_DIR / "argos"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass        # a read-only volume must not break the settings page; it just shows nothing installed
    return d


def _find(lang: str):
    """The model folder for one language, tolerating both en_es and translate-en_es-1_9."""
    for d in sorted(models_dir().glob(f"*en_{lang}*")):
        if (d / "model").is_dir():
            return d
    return None


def installed(lang: str) -> bool:
    """Is this language's model on disk? Cheap and import-free, so every settings page load can ask."""
    code = str(lang or "").strip()
    return bool(code) and _find(code) is not None


def installed_langs() -> list[str]:
    """The languages that can be translated right now."""
    return [c for c in LANGS if installed(c)]


_state = {"lang": "", "error": ""}       # what is being downloaded, and why the last one failed (dashboard only)
_dl_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _download_lock(lang: str) -> threading.Lock:
    with _locks_guard:
        return _dl_locks.setdefault(lang, threading.Lock())


def downloading() -> str:
    """The language being downloaded at this moment, or "" when nothing is."""
    return _state["lang"]


def ensure_model(lang: str) -> Path:
    """Download English -> lang once and return its folder. Raises TranslateError, never SystemExit.

    Two admins asking at the same time wait on one lock, so the 90 MB is fetched once. This is the only function
    in the module that uses the network."""
    code = str(lang or "").strip().lower()
    if code not in LANGS:
        raise ValueError(f"{lang!r} is not one of the languages PeakCut translates to: {', '.join(LANGS)}.")
    d = _find(code)
    if d:
        return d
    with _download_lock(code):
        d = _find(code)
        if d:
            return d
        _state.update(lang=code, error="")
        try:
            _download(code)
        except TranslateError as e:
            _state["error"] = str(e)[:300]
            raise
        except Exception as e:      # noqa: BLE001  every failure here has to become a message, not a crash
            _state["error"] = str(e)[:300]
            raise TranslateError(f"PeakCut couldn't download the {LANGS[code]} model. Check the internet connection "
                                 "and free disk space, then try again.") from e
        finally:
            _state["lang"] = ""
        d = _find(code)
        if not d:
            raise TranslateError(f"The {LANGS[code]} model downloaded but isn't where PeakCut looks for it "
                                 f"({models_dir()}).")
        return d


def _download(lang: str) -> None:
    """Fetch one package from the Argos index and unpack it. Only argostranslate.package is imported here:
    argostranslate.translate would pull torch and stanza, which this feature must never need."""
    try:
        import argostranslate.package as package
    except Exception as e:      # noqa: BLE001
        raise TranslateError("Downloading a translation model needs one more package. On the server run "
                             "'pip install argostranslate --no-deps' (then restart PeakCut).") from e
    try:
        package.update_package_index()
        packs = package.get_available_packages()
    except Exception as e:      # noqa: BLE001
        raise TranslateError("PeakCut couldn't read the list of translation models. Check the internet connection "
                             "and try again.") from e
    pack = next((p for p in packs if p.from_code == "en" and p.to_code == lang), None)
    if pack is None:
        raise TranslateError(f"There is no offline {LANGS[lang]} model for English -> {lang}.")
    target = models_dir()
    with zipfile.ZipFile(str(pack.download())) as z:
        for name in z.namelist():       # plain entries only, and never outside the models folder
            if name.startswith(("/", "\\")) or ".." in name.replace("\\", "/").split("/"):
                continue
            z.extract(name, str(target))


# ---------------------------------------------------------------- loaded models
_engines: "OrderedDict[str, tuple]" = OrderedDict()     # lang -> (ctranslate2.Translator, SentencePieceProcessor)
_engines_lock = threading.Lock()
_run_locks: dict[str, threading.Lock] = {}


def _run_lock(lang: str) -> threading.Lock:
    with _locks_guard:
        return _run_locks.setdefault(lang, threading.Lock())


def _load(lang: str):
    """The translator and its sentencepiece processor for one language, with at most two languages in memory."""
    hit = _engines.get(lang)
    if hit is not None:
        with _engines_lock:
            _engines.move_to_end(lang)
        return hit
    d = _find(lang)
    if d is None:
        raise TranslateError(f"The {LANGS.get(lang, lang)} model isn't downloaded yet. Download it once in Settings, "
                             "Languages (about 90 MB).")
    if not available():
        raise _no_engine()
    import ctranslate2
    import sentencepiece
    try:
        made = (ctranslate2.Translator(str(d / "model"), device="cpu", inter_threads=1),
                sentencepiece.SentencePieceProcessor(model_file=str(d / "sentencepiece.model")))
    except Exception as e:      # noqa: BLE001  a half-downloaded model is a message, not a broken clip
        raise TranslateError(f"The {LANGS.get(lang, lang)} model can't be loaded ({e}). Delete {d} and download "
                             "it again.") from e
    with _engines_lock:
        if lang in _engines:                    # another thread loaded it meanwhile: keep that one
            _engines.move_to_end(lang)
            return _engines[lang]
        _engines[lang] = made
        _engines.move_to_end(lang)
        while len(_engines) > 2:                # each entry is a whole model: two is plenty for a render queue
            _engines.popitem(last=False)
    return made


def _tr(texts: list[str], lang: str) -> list[str]:
    """Translate a batch of lines in one inference call."""
    if not texts:
        return []
    translator, sp = _load(lang)
    with _run_lock(lang):       # ctranslate2 does not promise one translator is safe for concurrent calls
        try:
            out = translator.translate_batch([sp.encode(x, out_type=str) for x in texts],
                                             beam_size=BEAM, length_penalty=LEN_PEN, max_batch_size=BATCH)
        except Exception as e:  # noqa: BLE001
            raise TranslateError(f"The {LANGS.get(lang, lang)} translation failed ({e}).") from e
    # the French and Portuguese models leave the SentencePiece word-start mark in the text, and some runs repeat
    # spaces: both are cleaned here, which is also what makes .split() give clean caption words.
    return [re.sub(r"\s+", " ", sp.decode(o.hypotheses[0]).replace("▁", " ")).strip() for o in out]


# ---------------------------------------------------------------- one line (the hook)
def text(s: str, lang: str) -> str:
    """One line (the hook) in the target language; an empty or English request gets the line back untouched."""
    if not s or lang in ("", "en", None):
        return s
    code = str(lang).strip().lower()
    if code not in LANGS:
        raise ValueError(f"{lang!r} is not one of the languages PeakCut translates to: {', '.join(LANGS)}.")
    if not available():
        raise _no_engine()
    line = s.capitalize() if s.isupper() else s     # ALL-CAPS hooks translate badly; sentence case is best
    return _tr([line], code)[0].translate(DROP_PARENS)


# ---------------------------------------------------------------- word captions
def sentences(words: list[dict], cap: int = CAP_WORDS) -> list[list[dict]]:
    """Cut word captions into translatable sentences: at each word flagged `end`, or after `cap` words."""
    cap = max(1, int(cap))
    out, cur = [], []
    for w in words or []:
        cur.append(w)
        if w.get("end") or len(cur) >= cap:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def spread(tokens: list[str], s0: float, e1: float, end: bool) -> list[dict]:
    """Place translated words over [s0, e1], each one's share of the time proportional to its own length."""
    if not tokens:
        return []
    s0 = _num(s0)
    e1 = max(s0, _num(e1))
    weights = [len(t) + 1 for t in tokens]      # the +1 gives a one-letter word a visible slice
    total = sum(weights) or 1
    t0 = s0
    res = []
    for i, (t, k) in enumerate(zip(tokens, weights)):
        t1 = e1 if i == len(tokens) - 1 else t0 + (e1 - s0) * k / total
        res.append(dict(w=t, s=round(t0, 3), e=round(t1, 3), end=bool(end and i == len(tokens) - 1)))
        t0 = t1
    return res


def _mask(w: str) -> str:
    """Keep the first letter of a known profanity and hide the rest, as the English caption path already does."""
    if not w or not BAD.match(w):
        return w
    return w[0] + "*" * (len(w) - 1)


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def words(words: list[dict], lang: str) -> list[dict]:
    """Word captions in the target language, re-timed over each sentence's own window.

    Input is [{"w", "s", "e", optional "end"}]; the output always carries "end". An empty or English request gets a
    copy back (never the same list: the caller may still be holding it for the English render)."""
    items = list(words or [])
    if lang in ("", "en", None):
        return [dict(w) for w in items]
    code = str(lang).strip().lower()
    if code not in LANGS:
        raise ValueError(f"{lang!r} is not one of the languages PeakCut translates to: {', '.join(LANGS)}.")
    if not items:
        return []
    if not available():
        raise _no_engine()
    groups = sentences(items)
    texts = [" ".join(str(w.get("w") or "") for w in g).strip() for g in groups]
    out: list[dict] = []
    for g, tx in zip(groups, _tr(texts, code)):
        toks = []
        for y in re.sub(r"\s+([?!؟])", lambda m: m[1], tx).split():   # French " ?" would otherwise be a word of its own
            y = PUNCT.sub("", y)
            if y:
                toks.append(_mask(y))
        if not toks:            # the whole line was punctuation
            continue
        s0 = _num(g[0].get("s"))
        e1 = max(s0, _num(g[-1].get("e")))
        ended = bool(g[-1].get("end")) or re.search(r"[.?!؟]$", tx) is not None
        out += spread(toks, s0, e1, ended)
    return out


translate_text = text        # the names the port spec and the render pipeline use
translate_words = words


# ---------------------------------------------------------------- the saved choice (translate.json)
_settings_lock = threading.Lock()


def _file() -> Path:
    return config.DATA_DIR / "translate.json"


def load() -> dict:
    """The saved choice: the server-wide target language, "" when translation is off."""
    try:
        data = json.loads(_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    lang = str(data.get("lang") or "") if isinstance(data, dict) else ""
    return {"lang": lang if lang in LANGS else ""}


def save(lang: str) -> dict:
    """Save the target language for the whole server; "" turns translation off."""
    code = str(lang or "").strip().lower()
    if code and code not in LANGS:
        raise ValueError(f"Choose one of {', '.join(LANGS)}, or nothing for no translation.")
    with _settings_lock:
        f = _file()
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps({"lang": code}), encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)        # only whoever runs the server changes it
        except OSError:
            pass
        tmp.replace(f)
    return public()


def public() -> dict:
    """What the settings page may see: the choice, the models present here, and any download in flight.

    Nothing in this file is secret, so nothing has to be hidden."""
    return {"lang": load()["lang"], "installed": installed_langs(), "engine": available(),
            "langs": [{"code": c, "label": l, "rtl": c in RTL} for c, l in LANGS.items()],
            "downloading": downloading(), "error": _state.get("error", "")}
