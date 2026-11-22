"""Judge a hook phrase without waiting for views.

A hook is the few words burned at the top of a clip. Nothing here talks to a model, a network or a
video: it is a fixed, readable set of rules about the phrase itself, so the same phrase always gets
the same score and a round of improvement costs nothing to judge.

The score starts at 100 and the rules take points away. A phrase that breaks no rule therefore keeps
the 100, because that is PeakCut's own preference: plain but sound beats clever and broken. The rules
below are PeakCut's, not anything measured or quoted: no number here comes from data.
"""
from __future__ import annotations

import unicodedata
from typing import Any, Iterable

__all__ = ["words", "score", "compare", "suggest"]

# Everything a rule can take away, in one place, so the weights can be argued about without reading
# the body of score(). Nothing here is measured data; these are the rule weights.
PENALTY_TOO_FEW = 25
PENALTY_TOO_MANY = 8          # per word past the seventh, so a rambling line loses more than a long one
PENALTY_TOO_MANY_CAP = 24
PENALTY_NO_ANCHOR = 25        # a hook that names nothing and risks nothing has nothing to stop for
PENALTY_FILLER_OPEN = 20      # one filler and the phrase is no longer strong, so this costs more than that
PENALTY_BARE_QUESTION = 45    # PeakCut treats this as a failure on its own, so it has to cost real points
PENALTY_SLOW = 20             # once it passes two seconds, which alone is more than strong allows
PENALTY_VERY_SLOW = 10        # and again once it passes three, because a clip has already moved on

# Two words is a hook: brain.py asks for the name of what happened in two or three words, and its examples
# are "1 VS 3", "THE SHOT" and "HE GOT ME". A single word is still named as a shape there ("CLUTCH"), so it
# costs the too-few points but keeps enough to read as workable rather than weak.
MIN_WORDS, MAX_WORDS = 2, 7
WORDS_PER_SECOND = 2.5        # PeakCut's own reading pace, chosen so a first line lands in time;
                              # not a measurement of any person
TWO_SECONDS = 2.0

# Strong means the phrase broke no rule that costs more than a stray word, so any single real fault
# sends it down to workable instead of reading as strong at 70.
STRONG_AT, WORKABLE_AT = 85, 40

FILLERS = ("so", "and", "well", "um", "just", "okay", "hey")

# Function words carry no picture. A phrase built only from these says nothing about the world.
STOPWORDS = frozenset("""
a an the this that these those it its is are was were be been being am
to of in on at for with from by as into onto over under about than then
and or but if while because since although though
i me my we us our you your he she his her they them their
there here what which who whom whose how when where why
will would can could should shall may might must
do does did have has had
not no yes all any some more most very too also only own same such both each few other another
""".split())

# Words that describe nothing a viewer can see. A phrase whose only content is one of these has no anchor.
ABSTRACT = frozenset("""
thing things stuff something anything everything nothing way ways kind sorts sort
part parts idea ideas issue issues aspect aspects matter matters point points
reason reasons situation case cases amount level levels type types
""".split())

# Outcomes: what a viewer could gain or lose by watching. These make a phrase concrete even when the
# subject is a general one ("you lose the account"), so they count as an anchor.
CONSEQUENCE = frozenset("""
lose loses lost win wins won fail fails failed break breaks broke broken
die dies died dead kill kills killed cost costs paid pay pays ruin ruins ruined
save saves saved stop stops stopped end ends ended never gone wrong
banned ban bans hidden secret rich free
""".split())

# A question is only a hook when something is at stake in it; these words show what could be lost.
STAKE = frozenset("""
money cash rent job jobs home family kids time health sleep car phone
account channel views followers pay bill bills food
""".split())

EMPTY_REASON = "There is no hook to score."


def _is_punct(ch: str) -> bool:
    """True for punctuation and symbols, so words() can drop them and keep the letters."""
    return unicodedata.category(ch)[0] in ("P", "S")


def words(phrase: Any) -> list[str]:
    """The phrase as comparable words: punctuation removed and every word lowercased.

    Removing punctuation without a space is deliberate. "Don't" becomes "dont" rather than "don t",
    so the word count stays the count a person would say out loud.
    """
    try:
        if not isinstance(phrase, str):
            return []
        kept = "".join(ch for ch in phrase if not _is_punct(ch))
        return [w for w in kept.lower().split() if w]
    except Exception:  # noqa: BLE001 - a screen must never raise
        return []


def _is_question(phrase: str) -> bool:
    """True when the phrase is written as a question."""
    return phrase.strip().endswith("?")


def _names_something(tokens: list[str]) -> bool:
    """True when at least one word names a thing, a number or a consequence.

    A filler is never an anchor: "So" is a word only in the sense that it has letters, and letting it
    count as content is how a scorer ends up calling a grunt a hook.
    """
    for word in tokens:
        if word in FILLERS:
            continue
        if any(ch.isdigit() for ch in word):
            return True
        if word in CONSEQUENCE:
            return True
        if word not in STOPWORDS and word not in ABSTRACT:
            return True
    return False


def _has_stake(tokens: list[str]) -> bool:
    """True when a question carries something the viewer could lose or gain."""
    for word in tokens:
        if any(ch.isdigit() for ch in word) or word in CONSEQUENCE or word in STAKE:
            return True
    return False


def _verdict(value: int) -> str:
    """The word the page shows for a score."""
    if value >= STRONG_AT:
        return "strong"
    if value >= WORKABLE_AT:
        return "workable"
    return "weak"


def _empty_score() -> dict:
    """The shape returned for a blank phrase or an unexpected failure."""
    return {"score": 0, "reasons": [EMPTY_REASON], "verdict": _verdict(0)}


def score(phrase: Any) -> dict:
    """Score one hook phrase from 0 to 100 and say why, in one short sentence per rule.

    Returns {"score": int, "reasons": [str], "verdict": "strong"|"workable"|"weak"}. A blank or
    unreadable phrase scores 0 with a single reason. This never raises.
    """
    try:
        tokens = words(phrase)
        if not tokens:
            return _empty_score()

        points = 100
        reasons: list[str] = []
        count = len(tokens)

        if count < MIN_WORDS:
            points -= PENALTY_TOO_FEW
            reasons.append(f"It is {count} word{'s' if count != 1 else ''} long, under the 2 PeakCut reads as a hook.")
        elif count > MAX_WORDS:
            over = count - MAX_WORDS
            points -= min(PENALTY_TOO_MANY_CAP, PENALTY_TOO_MANY * over)
            reasons.append(f"It is {count} words long, past the 7 a hook can carry before the clip moves on.")

        if not _names_something(tokens):
            points -= PENALTY_NO_ANCHOR
            reasons.append("It names no thing, number or consequence, so nothing is at stake.")

        first = tokens[0]
        if first in FILLERS:
            points -= PENALTY_FILLER_OPEN
            reasons.append(f'It opens with "{first}", a filler that spends the first moment on nothing.')

        if _is_question(phrase) and not _has_stake(tokens):
            points -= PENALTY_BARE_QUESTION
            reasons.append("It is a question with nothing at stake, so it asks without a reason to stay.")

        seconds = count / WORDS_PER_SECOND
        if seconds > TWO_SECONDS:
            points -= PENALTY_SLOW
            if seconds > 3.0:
                points -= PENALTY_VERY_SLOW
            reasons.append(f"At PeakCut's own pace of {WORDS_PER_SECOND} words a second, this takes about "
                           f"{seconds:.1f} seconds to say, and PeakCut wants the first line inside "
                           f"{TWO_SECONDS:.0f}.")

        points = max(0, min(100, int(points)))
        if not reasons:
            reasons.append("It breaks none of the rules this check knows.")
        return {"score": points, "reasons": reasons, "verdict": _verdict(points)}
    except Exception:  # noqa: BLE001 - a screen must never raise
        return _empty_score()


def _safe_score(phrase: Any) -> dict:
    """score() with the same fallback, used where one bad phrase must not sink a comparison."""
    try:
        return score(phrase)
    except Exception:  # noqa: BLE001
        return _empty_score()


def compare(a: Any, b: Any) -> dict:
    """Say which of two hook phrases is better and why, with both scores included.

    Returns {"better": "a"|"b"|"same", "why": str, "a": dict, "b": dict}. When the scores are equal
    the answer is "same"; this never raises.
    """
    try:
        left = _safe_score(a)
        right = _safe_score(b)
        if left["score"] > right["score"]:
            why = (f"A scores {left['score']} and B scores {right['score']}, so A keeps more of what"
                   f" makes a hook work.")
            better = "a"
        elif right["score"] > left["score"]:
            why = (f"B scores {right['score']} and A scores {left['score']}, so B keeps more of what"
                   f" makes a hook work.")
            better = "b"
        else:
            why = f"Both score {left['score']}, so neither is the better hook on these rules."
            better = "same"
        return {"better": better, "why": why, "a": left, "b": right}
    except Exception:  # noqa: BLE001
        return {"better": "same", "why": "The check could not read these phrases.",
                "a": _empty_score(), "b": _empty_score()}


def suggest(phrases: Iterable[Any], want: int = 3) -> list[str]:
    """The best of the phrases given, best first, and never a phrase that was not given.

    Blanks are dropped, so fewer than `want` come back when fewer were supplied. Order is stable: two
    phrases that score the same keep the order they arrived in. This never raises.
    """
    try:
        if not isinstance(want, int) or isinstance(want, bool):
            want = 3
        want = max(0, want)
        if want == 0:
            return []
        kept: list[tuple[int, int, str]] = []
        for index, phrase in enumerate(phrases):  # type: ignore[arg-type]
            if not isinstance(phrase, str):
                continue
            text = " ".join(phrase.split())
            if not words(text):
                continue
            kept.append((_safe_score(text)["score"], index, text))
        # Sort by score first, then by arrival, so the result is reproducible.
        kept.sort(key=lambda row: (-row[0], row[1]))
        return [text for _, _, text in kept[:want]]
    except Exception:  # noqa: BLE001
        return []
