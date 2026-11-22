"""Taking the swearing out, and taking the dead air out.

Two jobs that look alike and are not:

* **Censor** keeps the clip exactly as long as it was and silences the words that should not be heard. Nothing moves,
  so a caption still lines up with the mouth. This is the one to use when the clip must stay identical in timing.
* **Cleanup** takes time out: a filler word and the silence around it are removed, so the clip gets shorter and
  everything after the cut moves earlier. That is what makes a rambling take watchable, and it is why the picture has
  to be re-timed along with the sound.

Both are decided here, from the same word list the captions come from, so the page, the captions and the render all
agree about which words were touched. Nothing in this file runs ffmpeg; it only says what should happen.
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

Span = Tuple[float, float]

# Words that get bleeped. This is a starting list, not a moral position: it is the ordinary English swearing that
# turns up in game clips, and a person can add their own on the clip. Matching is on the whole word after the
# punctuation is stripped, so "class" never matches "ass" and "Scunthorpe" stays intact.
CURSE: Tuple[str, ...] = (
    "ass", "asses", "asshole", "assholes", "bastard", "bastards", "bitch", "bitches", "bollocks",
    "bullshit", "cock", "cocks", "cunt", "cunts", "damn", "damned", "dick", "dicks", "dickhead",
    "fuck", "fucked", "fucker", "fuckers", "fucking", "fucks", "goddamn", "hell", "motherfucker",
    "motherfuckers", "motherfucking", "piss", "pissed", "prick", "pricks", "pussy", "shit", "shits",
    "shitty", "slut", "sluts", "twat", "twats", "wanker", "wankers", "whore", "whores",
)

# Words that carry no meaning and can be dropped without losing the sentence. Kept short on purpose: "like" and
# "right" are only fillers some of the time, so they are dropped only when they stand alone between pauses, which is
# handled by `_is_filler_run` below rather than by the list itself.
FILLER: Tuple[str, ...] = (
    "um", "umm", "uhm", "uh", "uhh", "uhhh", "erm", "er", "ah", "ahh", "eh", "hmm", "hmmm", "mmm",
    "mhm", "mm", "uh-huh", "uhhuh",
)

# The sounds that hold a place in a sentence. These are cut only as a run ("you know" as two words in a row).
FILLER_PAIRS: Tuple[Tuple[str, ...], ...] = (
    ("you", "know"), ("i", "mean"), ("sort", "of"), ("kind", "of"), ("you", "see"),
)

# A gap longer than this between two words is dead air worth shortening. A word is never cut for being slow: a pause
# inside a sentence is how people talk, and cutting every one of them makes the clip sound like a machine.
PAUSE_CUT_ABOVE = 0.85     # seconds
PAUSE_LEAVE = 0.30         # seconds of the gap that stays, so the sentence still breathes
EDGE_KEEP = 0.12           # never cut closer than this to a word, so no consonant is clipped in half

# A clip must never be cut down to nothing. A half-second clip whose only word is "um" would otherwise become a
# five-hundredth of a second of nothing at all, which is worse than the filler it removed. When the cuts would leave
# less than this, nothing is cut and the page says why.
MIN_KEPT = 1.0             # seconds
MIN_KEPT_SHARE = 0.4       # or this much of the original, whichever is smaller

_WORD = re.compile(r"[a-z']+")


def _plain(word: str) -> str:
    """The word as letters only, lower case, so "Fuck!" and "fuck," both read as "fuck"."""
    got = _WORD.findall(str(word or "").lower().replace("\u2019", "'"))
    return got[0] if got else ""


def words_of(text: str) -> List[str]:
    """Every plain word in a piece of text, in order."""
    return [_plain(w) for w in str(text or "").split() if _plain(w)]


class Rules:
    """What a person asked for. Two flags and the words they added by hand."""

    def __init__(self, censor: bool = False, cleanup: bool = False, extra: Optional[Iterable[str]] = None):
        self.censor = bool(censor)
        self.cleanup = bool(cleanup)
        self.extra = tuple(w.lower() for w in (extra or ()) if str(w).strip())

    @property
    def any(self) -> bool:
        return self.censor or self.cleanup

    def curses(self) -> frozenset:
        return frozenset(CURSE) | frozenset(self.extra)


def rules(clip: Optional[dict]) -> Rules:
    """Read the two flags off a clip. A clip from before this existed asks for neither."""
    c = clip or {}
    extra = c.get("censor_words")
    if isinstance(extra, str):
        extra = extra.replace(",", " ").split()
    return Rules(bool(c.get("censor")), bool(c.get("cleanup")), extra if isinstance(extra, (list, tuple)) else ())


# ---- what the words say -----------------------------------------------------------------------------------------

def bleep(words: Sequence[dict], curses: Iterable[str]) -> List[dict]:
    """The same words with every swear replaced by its first letter and three dots.

    The timings are untouched, so a caption built from these still lands on the mouth. Only the text changes.
    """
    bad = frozenset(curses)
    out = []
    for w in words:
        plain = _plain(w.get("w", ""))
        if plain and plain in bad:
            first = str(w.get("w", "")).strip()[:1].upper() or "?"
            out.append(dict(w, w=f"{first}...", bleeped=True))
        else:
            out.append(w)
    return out


def mute_spans(words: Sequence[dict], start: float, end: float, curses: Iterable[str]) -> List[Span]:
    """When to silence, in seconds from the start of the clip.

    A word's own timing is used, widened a little at both ends: speech does not begin and end on the sample the
    recogniser picked, so silencing exactly the word leaves the first consonant and the last hiss audible, which is
    the thing that gives the bleep away.
    """
    bad = frozenset(curses)
    out: List[Span] = []
    for w in words:
        plain = _plain(w.get("w", ""))
        if not plain or plain not in bad:
            continue
        try:
            s = float(w.get("s"))
            e = float(w.get("e"))
        except (TypeError, ValueError):
            continue
        a = max(0.0, min(s, e) - start - 0.04)
        b = min(end - start, max(s, e) - start + 0.06)
        if b - a >= 0.04:
            out.append((round(a, 3), round(b, 3)))
    return _merged(out)


def _merged(spans: List[Span]) -> List[Span]:
    """Spans joined where they touch, so one second of swearing is one silence rather than six."""
    if not spans:
        return []
    got = sorted(spans)
    out = [list(got[0])]
    for a, b in got[1:]:
        if a <= out[-1][1] + 0.02:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(round(a, 3), round(b, 3)) for a, b in out]


# ---- what the words do not say (the dead air) ------------------------------------------------------------------

def _is_filler(word: str, index: int, plain: Sequence[str]) -> bool:
    """True when this word adds nothing.

    Single fillers are always dropped. Two of them in a row ("um, uh") are dropped together, which is what makes the
    result sound edited rather than stuttered.
    """
    if word in FILLER:
        return True
    for pair in FILLER_PAIRS:
        n = len(pair)
        if index + n <= len(plain) and tuple(plain[index:index + n]) == pair:
            return True
    return False


def cut_spans(words: Sequence[dict], start: float, end: float) -> List[Span]:
    """What to take out, in seconds from the start of the clip, so the rest closes up.

    Two things go: filler words, and the part of a long gap beyond `PAUSE_LEAVE`. A cut never reaches closer than
    `EDGE_KEEP` to a word that is staying, because cutting half a consonant off the start of "and" is what makes an
    automatic editor sound broken.
    """
    span = max(0.0, end - start)
    if span <= 0 or not words:
        return []
    timings: List[Tuple[float, float, str]] = []
    for w in words:
        try:
            s = float(w.get("s")) - start
            e = float(w.get("e")) - start
        except (TypeError, ValueError):
            continue
        if e <= 0 or s >= span or e <= s:
            continue
        timings.append((max(0.0, s), min(span, e), _plain(w.get("w", ""))))
    if not timings:
        return []
    timings.sort()
    plain = [t[2] for t in timings]
    out: List[Span] = []
    for i, (s, e, word) in enumerate(timings):
        if _is_filler(word, i, plain):
            out.append((max(0.0, s - EDGE_KEEP), min(span, e + EDGE_KEEP)))
    for i in range(1, len(timings)):
        gap_a, gap_b = timings[i - 1][1], timings[i][0]
        if gap_b - gap_a > PAUSE_CUT_ABOVE:
            out.append((gap_a + PAUSE_LEAVE, gap_b))
    # A cut must never swallow a word that is staying: the filler pass can reach into the next word's start.
    keep_words = [(s, e) for (s, e, w), i in zip(timings, range(len(timings))) if not _is_filler(w, i, plain)]
    safe: List[Span] = []
    for a, b in _merged(out):
        safe.append((a, b))
    return _trim_round_words(safe, keep_words, span)


def _trim_round_words(spans: List[Span], keep: List[Tuple[float, float]], span: float) -> List[Span]:
    """Pull every cut back so it does not overlap a word that is being kept."""
    out: List[Span] = []
    for a, b in spans:
        for ks, ke in keep:
            if b <= ks or a >= ke:
                continue
            if a < ks:
                b = min(b, ks)
            elif b > ke:
                a = max(a, ke)
            else:
                a, b = 0.0, 0.0        # the whole cut sits inside a kept word: drop it rather than eat the word
        if b - a >= 0.05 and b <= span:
            out.append((round(a, 3), round(b, 3)))
    return _merged(out)


def kept_spans(cuts: Sequence[Span], span: float) -> List[Span]:
    """The pieces that stay, once the cuts are taken out."""
    if span <= 0:
        return []
    out: List[Span] = []
    at = 0.0
    for a, b in sorted(cuts):
        if a > at + 0.01:
            out.append((round(at, 3), round(min(a, span), 3)))
        at = max(at, b)
    if at < span - 0.01:
        out.append((round(at, 3), round(span, 3)))
    return [s for s in out if s[1] - s[0] >= 0.02]


def plan(words: Sequence[dict], start: float, end: float, rules_got: Rules) -> Dict[str, object]:
    """Everything the renderer needs to know, worked out once.

    Returns `{"mute", "cut", "keep", "kept_seconds", "dropped", "bleeped", "why"}`. `why` is always a sentence a page
    can print, and it says the plain truth when nothing was asked for.
    """
    span = max(0.0, float(end) - float(start))
    got: Dict[str, object] = {"mute": [], "mute_raw": [], "cut": [],
                              "keep": [(0.0, round(span, 3))] if span > 0 else [],
                              "span": round(span, 3), "kept_seconds": round(span, 3),
                              "bleeped": 0, "dropped": 0, "why": "Nothing was censored and nothing was cut."}
    if not rules_got.any or span <= 0:
        return got
    if rules_got.censor:
        mute = mute_spans(words, start, end, rules_got.curses())
        got["mute_raw"] = mute
        got["mute"] = mute
        got["bleeped"] = sum(1 for w in words if _plain(w.get("w", "")) in rules_got.curses())
    if rules_got.cleanup:
        cuts = cut_spans(words, start, end)
        keep = kept_spans(cuts, span)
        kept = sum(b - a for a, b in keep)
        # Cutting a short clip to nothing is worse than leaving the filler in. A clip that would lose more than this
        # is left whole, and the line below says so rather than quietly doing nothing.
        floor = min(MIN_KEPT, span * MIN_KEPT_SHARE)
        if kept < floor:
            got["why"] = ("This clip is too short to cut without gutting it, so it was left at its own length.")
            return got
        got["cut"] = cuts
        got["keep"] = keep
        got["dropped"] = round(max(0.0, span - kept), 3)
        got["kept_seconds"] = round(kept, 3)
        # Time moved, so the silences have to move with it or they land on the wrong word.
        if got["mute_raw"]:
            got["mute"] = remap(got["mute_raw"], keep)
    bits = []
    if got["mute"]:
        bits.append(f"{len(got['mute'])} word{'s' if len(got['mute']) != 1 else ''} silenced")
    if got["cut"]:
        bits.append(f"{got['dropped']:.1f} seconds of filler and pauses taken out")
    got["why"] = ("The clip is " + " and ".join(bits) + ".") if bits else got["why"]
    return got


# ---- telling ffmpeg ---------------------------------------------------------------------------------------------

def remap(spans: Sequence[Span], keep: Sequence[Span]) -> List[Span]:
    """Move spans from the original timeline onto the cut one.

    This is the whole reason bleeping and cleanup have to be decided together. Once time is taken out, "silence from
    1.5 to 2.0 seconds" points at a different thing: the cut clip is shorter, and everything after a cut has moved
    earlier. An un-remapped silence would land on the wrong word, which is worse than no silence at all.
    """
    if not spans:
        return []
    if not keep:
        return []
    out: List[Span] = []
    moved = 0.0                      # how much time has been taken out before this piece
    for ka, kb in keep:
        for a, b in spans:
            lo, hi = max(a, ka), min(b, kb)
            if hi - lo <= 0.001:
                continue
            out.append((round(moved + (lo - ka), 3), round(moved + (hi - ka), 3)))
        moved += kb - ka
    return _merged(out)


def retime(words: Sequence[dict], start: float, keep: Sequence[Span]) -> List[dict]:
    """The words as they will be heard in the cut clip, in seconds from its own start.

    Without this the captions would still be timed against the original clip, so once time is taken out every caption
    after the first cut drifts later and later, and by ten seconds in it is naming a word nobody is saying.
    """
    if not keep:
        return []
    out: List[dict] = []
    moved = 0.0
    for ka, kb in keep:
        for w in words:
            try:
                s = float(w.get("s")) - start
                e = float(w.get("e")) - start
            except (TypeError, ValueError):
                continue
            lo, hi = max(s, ka), min(e, kb)
            if hi - lo <= 0.001:
                continue
            out.append(dict(w, s=round(moved + (lo - ka), 3), e=round(moved + (hi - ka), 3)))
        moved += kb - ka
    return out


def keep_expression(keep: Sequence[Span]) -> str:
    """The `select` test that keeps the pieces in `keep`, as a filter expression.

    ffmpeg's `select` wants a truth value per frame, and `between` is inclusive at both ends, which is what stitches
    two neighbouring pieces back together without a missing frame.
    """
    parts = [f"between(t,{a:.3f},{b:.3f})" for a, b in keep if b > a]
    return "+".join(parts) if parts else "0"


def mute_filter(mute: Sequence[Span], chain: str = "") -> str:
    """`volume` filters that drop the sound to nothing over each span, leaving the timing alone.

    The `enable` window is what makes this safe: the rest of the audio is not passed through `volume` at all, so a
    clip with nothing to censor gets a chain that does nothing rather than a clip that was re-levelled.
    """
    out = chain
    for a, b in mute:
        if b > a:
            out += (f",volume=volume=0:enable='between(t,{a:.3f},{b:.3f})'")
    return out


def sentence(got: Dict[str, object]) -> str:
    """One line for the page, from the plan."""
    return str(got.get("why") or "")
