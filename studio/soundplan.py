"""Where the sounds belong, and which one: the AI reading of a clip that decides both.

A meme sound is only funny if it lands on the right word. This module asks the configured AI to read a clip's own
words plus the catalogue's descriptions and answer with cues — a time, a mood, and why — and then maps each mood
onto a real sound from the catalogue. Two calls at most, never one per cue.

The rules it works under, which are the whole reason this is careful rather than clever:

  * A time is always a real word's time. The AI is given numbered lines with their times and must answer with a
    line number, so a cue cannot land in silence from a hallucinated timestamp.
  * The catalogue's own ranking is replaced by ours (`memesound.find`), because its top rows have popularity 0.
  * Few sounds. A short clip gets at most three; a long one at most five. More than that is noise.
  * Nothing is invented. If no AI is set up, or it answers badly, the cue list is empty and the clip is unchanged.

`plan()` is the only entry point a route or a job needs. `cues()` is the deterministic half, kept separate so it
can be tested without a network or a model.
"""
from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Sequence

from . import memesound, safe

MAX_FOR_SHORT = 3              # a fifteen second clip with four sounds on it is a soundboard, not a joke
MAX_FOR_LONG = 5
MIN_GAP_SECONDS = 1.2          # closer than this and two sounds arrive as one mess
FIRST_ALLOWED = 0.35           # never over the first frames: that is the hook, and it must be heard

# The moods the catalogue actually uses, as a closed list so an answer that invents a word is caught here rather
# than at the catalogue, which would answer with five unrelated sounds.
MOODS = ("funny", "fail", "win", "hype", "shock", "awkward", "sad", "angry", "scary", "dramatic", "surprise",
         "chaotic", "victory", "suspense")

_PROMPT = """You are choosing meme sound effects for a short vertical video clip.

The clip's own words, with their times in seconds:

{lines}

{mood_note}
Rules you must follow:
- Answer with between 0 and {most} sounds. Fewer is better. Zero is a correct answer when nothing deserves a noise.
- Never put a sound in the first {first} seconds: that is the hook and it must be heard.
- Never put two sounds closer than {gap} seconds apart.
- Each sound must land on the word that earns it: a punchline, a fail, a win, a reveal, a sudden shock, an awkward
  silence. Name the line number of that word.
- Pick a mood from exactly this list: {moods}
- Only use "truthful": true. Do not claim a sound is free to use.

Answer with JSON and nothing else:
{{"cues": [{{"line": <line number>, "mood": "<one mood>", "why": "<six words at most>", "loudness": <number>}}]}}

"loudness" is how much it should stand out, from -6 (gentle, far back) to 0 (normal, in front)."""


def _lines(words: Sequence[dict], start: float, end: float) -> List[dict]:
    """The clip's own words with an index, so the AI can name one and the time is looked up here.

    Times are given relative to the clip so the model never has to subtract, which is the one piece of arithmetic
    it reliably gets wrong."""
    out: List[dict] = []
    for w in words or []:
        if not isinstance(w, dict):
            continue
        try:
            at = float(w.get("s"))
            to = float(w.get("e"))
        except (TypeError, ValueError):
            continue
        if to < start or at > end:
            continue
        text = str(w.get("w") or "").strip()
        if not text:
            continue
        out.append({"w": text, "s": round(max(0.0, at - start), 2), "e": round(max(0.0, min(to, end) - start), 2)})
    return out


def _render_lines(lines: Sequence[dict]) -> str:
    """Numbered lines, three words to a line, so a line number points at a moment rather than a single word."""
    if not lines:
        return "(this clip has no recognised words)"
    rows: List[str] = []
    for i in range(0, len(lines), 3):
        group = lines[i:i + 3]
        said = " ".join(g["w"] for g in group)
        rows.append(f"{i // 3 + 1}. {group[0]['s']:.2f}s  {said}")
    return "\n".join(rows[:40])


def _mood_note(brand: Optional[dict]) -> str:
    """A line about the house style, when the brand says anything about it."""
    doc = brand if isinstance(brand, dict) else {}
    said = str(doc.get("sound") or "").strip().lower()
    if said:
        return f'The house sound style is "{said}". Prefer moods that fit it when it is a fair fit.'
    return ""


def most_for(seconds: float) -> int:
    """How many sounds a clip of this length is allowed. Short clips get very few."""
    try:
        secs = float(seconds)
    except (TypeError, ValueError):
        secs = 0.0
    if secs <= 0:
        return 0
    if secs < 10:
        return 1
    if secs < 25:
        return 2
    if secs < 45:
        return MAX_FOR_SHORT
    return MAX_FOR_LONG


_LINE = re.compile(r"^\s*(\d+)\.", re.M)


def cues(answer: str, lines: Sequence[dict], seconds: float,
         brand: Optional[dict] = None) -> List[dict]:
    """Turn the AI's answer into cues, keeping only the ones that survive every rule.

    Deterministic and network-free, so this half is testable on its own. A cue whose line number does not exist,
    whose mood is not on the list, that lands too early, or that crowds the previous one is dropped — never moved,
    because a moved cue is a sound in the wrong place and the whole point is the place."""
    got = _json_of(answer)
    raw = got.get("cues") if isinstance(got, dict) else None
    if not isinstance(raw, list):
        return []
    allowed = most_for(seconds)
    if allowed <= 0:
        return []
    first = float(FIRST_ALLOWED)
    if seconds < 4:
        return []                     # too short for a sound and a punchline in the same breath
    out: List[dict] = []
    for item in raw:
        if len(out) >= allowed:
            break
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("line"))
        except (TypeError, ValueError):
            continue
        at = _time_of(idx, lines)
        if at is None:
            continue
        mood = str(item.get("mood") or "").strip().lower()
        if mood not in MOODS:
            continue
        if at < first:
            continue
        if out and at - out[-1]["at"] < MIN_GAP_SECONDS:
            continue
        try:
            loud = float(item.get("loudness"))
        except (TypeError, ValueError):
            loud = 0.0
        out.append({"at": round(at, 2), "mood": mood,
                    "why": str(item.get("why") or "").strip()[:60],
                    "volume": round(max(-12.0, min(3.0, loud)), 1)})
    out.sort(key=lambda c: c["at"])
    return out[:allowed]


def _time_of(index: int, lines: Sequence[dict]) -> Optional[float]:
    """The time of a numbered line, or None when that line does not exist."""
    if index < 1:
        return None
    first = (index - 1) * 3
    if first >= len(lines):
        return None
    return float(lines[first]["s"])


def _json_of(text: str) -> dict:
    """The JSON in an answer that may have been wrapped in prose or a fence."""
    said = str(text or "").strip()
    if not said:
        return {}
    fence = re.search(r"```(?:json)?\s*(.+?)```", said, re.S)
    if fence:
        said = fence.group(1).strip()
    try:
        got = json.loads(said)
        return got if isinstance(got, dict) else {}
    except ValueError:
        pass
    start, end = said.find("{"), said.rfind("}")
    if start >= 0 and end > start:
        try:
            got = json.loads(said[start:end + 1])
            return got if isinstance(got, dict) else {}
        except ValueError:
            return {}
    return {}


def plan(words: Sequence[dict], start: float, end: float, *, brand: Optional[dict] = None,
         ask: Optional[object] = None, situation: str = "") -> dict:
    """Choose the sounds for one clip. Answers `{"cues": [...], "why": "...", "source": "ai"|"none"}`.

    `ask` is the callable that talks to the model (`ai.ask`), passed in so this stays testable and so a caller
    without a model simply gets nothing. Every failure is a sentence in `why`, never an exception: a clip must
    never fail to render because the sound picker had a bad day."""
    span = max(0.0, float(end) - float(start))
    allowed = most_for(span)
    if allowed <= 0:
        return {"cues": [], "why": f"The clip is {span:.1f} s long, which is too short for a sound.", "source": "none"}
    lines = _lines(words, float(start), float(end))
    if not lines:
        return {"cues": [], "why": "This clip has no recognised words to land a sound on.", "source": "none"}
    if ask is None:
        return {"cues": [], "why": "No AI is set up, so the sounds were not chosen.", "source": "none"}

    prompt = _PROMPT.format(lines=_render_lines(lines), mood_note=_mood_note(brand) + _about(situation),
                            most=allowed, first=FIRST_ALLOWED, gap=MIN_GAP_SECONDS, moods=", ".join(MOODS))
    try:
        answer = ask(prompt)          # type: ignore[operator]
    except Exception as e:            # noqa: BLE001 - the model is a helper, never a hard dependency
        return {"cues": [], "why": "The AI could not be asked: " + safe.friendly(e), "source": "none"}
    said = answer if isinstance(answer, str) else str(answer or "")
    got = cues(said, lines, span, brand)
    if not got:
        return {"cues": [], "why": "The AI did not name a moment that earns a sound.", "source": "ai"}
    return {"cues": got, "why": f"{len(got)} cue{'s' if len(got) != 1 else ''} chosen.", "source": "ai"}


def _about(situation: str) -> str:
    """A line about what happens in the clip, when the caller knows."""
    said = str(situation or "").strip()[:200]
    return f'\nWhat happens in the clip, in the maker\'s words: "{said}".' if said else ""


def sounds_for(chosen: Sequence[dict], limit_each: int = 1) -> Dict[str, List[dict]]:
    """Find the real catalogue sound behind each chosen mood.

    The mood is the part the AI is trusted with; picking the sound is this app's job, because the catalogue's own
    answer puts popularity 0 in front. One sound per mood is enough for a cue."""
    out: Dict[str, List[dict]] = {}
    for cue in chosen or []:
        mood = str((cue or {}).get("mood") or "").strip().lower()
        if not mood or mood in out:
            continue
        try:
            out[mood] = memesound.find(mood, limit=limit_each)
        except memesound.CatalogueDown:
            out[mood] = []
    return out


def with_sounds(chosen: Sequence[dict], picked: Dict[str, List[dict]]) -> List[dict]:
    """Attach a kept sound to each cue, dropping the cues no real sound could be found for.

    A cue with no sound is worse than no cue: the plan would promise a noise and the render would produce
    silence. So a mood with an empty list removes its cue."""
    out: List[dict] = []
    for cue in chosen or []:
        mood = str((cue or {}).get("mood") or "").strip().lower()
        rows = [r for r in (picked.get(mood) or []) if r.get("slug")]
        if not rows:
            continue
        row = rows[0]
        out.append({"slug": row["slug"], "title": row.get("title") or row["slug"],
                    "at": cue["at"], "volume": cue.get("volume", 0.0),
                    "why": cue.get("why", ""), "mood": mood})
    return out
