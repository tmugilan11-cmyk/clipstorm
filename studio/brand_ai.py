"""The bridge between what an improvement round learned and the brand a person saved.

`studio/learn.py` decides what should change (the caption look, the hook words, the length, the sound,
whether captions are burned in). `studio/brand.py` owns the document those values live in and is the
only code that writes it. This file sits between them so a round can ask two questions and never has
to know the document's shape:

    preview(uid, changes)   what would the brand look like if these landed? Nothing is written.
    apply(uid, changes)     write the ones the document accepts, and name the reason for the rest.

The document is the judge, not this file. A look it cannot draw, a length outside the range a job
accepts, or a word that is not a yes or a no is refused with a sentence. It is never quietly replaced
by a different number, because a number the person did not ask for is worse than no change at all.

A brand that will not load reads as the neutral look and never raises: a page still has to draw and
the pipeline still has to make a clip.
"""
from __future__ import annotations

import copy
import math

from . import brand

# The five settings a round may touch: the name learn's own constant carries, and the key in the brand
# document it lands on. The key is read from brand.DEFAULTS before it is ever offered, so a setting the
# document stopped keeping disappears from `known()` instead of being written into nothing.
_FROM_LEARN = (("STYLE", "style"), ("HOOK", "hook_words"), ("LENGTH", "clip_len"),
               ("MOOD", "sound"), ("COUNTER", "captions"))

# The names to use when learn cannot be imported. They are the same five names, kept here so this file
# still answers with a full set: the mapping is part of the contract, not of the import.
_PLAIN_NAMES = {"STYLE": "style", "HOOK": "hook_words", "LENGTH": "clip_len",
                "MOOD": "sound", "COUNTER": "captions_always"}

# How each key reads inside a sentence for a person, never as a code name.
_LABELS = {"style": "Caption look", "hook_words": "Hook words", "clip_len": "Clip length",
           "sound": "The sound under every clip", "captions": "Captions"}


def known() -> set:
    """The brand keys one improvement round may touch, as names in the brand document.

    Only keys the document actually keeps are returned. A setting learn knows about but the brand has
    no home for is left out, so a round can never write into a key that would be dropped on save."""
    try:
        return {key for key in _settings().values() if key in brand.DEFAULTS}
    except Exception:  # noqa: BLE001 - a broken import must not stop the page drawing
        return set()


def preview(user_id: str = "default", changes=None) -> dict:
    """What the document would look like after these changes, without writing anything.

    Returns the brand before, the brand as it would be stored, and one plain sentence for each setting
    that would move. A change the document cannot keep is explained in its own line and leaves the
    document alone. `before` and `after` are full documents, so a page can show any key it likes."""
    before, unread = _look(user_id)
    lines = [unread.strip()] if unread else []
    try:
        work = copy.deepcopy(before)
        touched = []
        for name, value in _pairs(changes):
            key = _key_for(name)
            if key is None:
                lines.append(_unknown_line(name))
                continue
            clean, because = _value_for(key, value)
            if clean is None:
                lines.append(_stay_line(key, before.get(key), because))
                continue
            work[key] = clean
            if key not in touched:
                touched.append(key)
        after = _stored(work)
        # The final value is only known once the whole document has been normalised, because the
        # document clamps a length and trims a phrase. Compare there, so a line is never a guess.
        for name, value in _pairs(changes):
            key = _key_for(name)
            if key is None:
                continue
            if _same(before.get(key), after.get(key)):
                if key not in touched:
                    continue
                if _count_line(lines, key):
                    continue
                lines.append("%s would stay at %s." % (_label(key), _say(key, after.get(key))))
                touched.remove(key)
                continue
            if _count_line(lines, key):
                continue
            lines.append("%s would go from %s to %s." % (
                _label(key), _say(key, before.get(key)), _say(key, after.get(key))))
        return {"before": before, "after": after, "lines": lines}
    except Exception:  # noqa: BLE001 - a preview is a question, never a failure
        return {"before": before, "after": copy.deepcopy(before),
                "lines": lines + ["PeakCut could not work out what that change would do."]}


def apply(user_id: str = "default", changes=None) -> dict:
    """Write the changes the saved brand accepts, and name the reason for each one it leaves alone.

    `written` holds the settings that moved, each with its old and new value. `ignored` holds the ones
    the document would keep as they are, each with a sentence saying why. Everything accepted is written
    in one save, so a failure cannot leave half a round on disk. `why` says in one line what happened."""
    written, ignored = [], []
    try:
        before, unread = _look(user_id)
        work = copy.deepcopy(before)
        wanted = []
        for name, value in _pairs(changes):
            setting = _name(name)
            key = _key_for(setting)
            if key is None:
                ignored.append({"setting": setting, "why": _unknown_line(setting)})
                continue
            clean, because = _value_for(key, value)
            if clean is None:
                ignored.append({"setting": setting, "why": _stay_line(key, before.get(key), because)})
                continue
            # Try the value against a copy first: a value the document would keep exactly as it already
            # is does not need a save, and saying so is more useful than a write nobody can see.
            trial = copy.deepcopy(work)
            trial[key] = clean
            would = _stored(trial).get(key)
            if _same(would, before.get(key)):
                ignored.append({"setting": setting,
                                "why": "%s would stay at %s." % (_label(key), _say(key, would))})
                continue
            work = trial
            wanted.append((setting, key, clean, value, would))

        if wanted:
            try:
                saved = brand.save(user_id, work)
            except Exception as e:  # noqa: BLE001 - brand.save raises ValueError; a page is still owed an answer
                because = "PeakCut could not save the brand: %s" % str(e)[:160]
                for setting, key, clean, value, would in wanted:
                    ignored.append({"setting": setting, "why": because})
                wanted = []
            else:
                for setting, key, clean, value, would in wanted:
                    entry = {"setting": setting, "key": key,
                             "from": before.get(key), "to": saved.get(key)}
                    # Keep what was asked for beside what was stored whenever the document adjusted it,
                    # so a clamped length reads as "asked 3, kept 5" rather than looking like a mistake.
                    # The comparison is against the cleaned value, not the raw one: "45" and 45 are one ask.
                    if not _same(would, clean):
                        entry["asked"] = value
                    written.append(entry)

        return {"written": written, "ignored": ignored, "why": unread + _why(written, ignored)}
    except Exception as e:  # noqa: BLE001 - the empty shape, never an exception to a caller
        return {"written": [], "ignored": ignored,
                "why": "PeakCut could not apply that change: %s" % str(e)[:160]}


# ---------------------------------------------------------------- reading the document

def _look(user_id):
    """This person's brand as the renderer would see it, and a note when it had to be replaced.

    A brand that will not load is the neutral look, never an exception. The note is empty when the
    document was read normally, so a page is not told about a problem that did not happen."""
    who = user_id if isinstance(user_id, str) and user_id.strip() else "default"
    try:
        got = brand.load(who)
        if isinstance(got, dict) and got:
            return copy.deepcopy(got), ""
    except Exception:  # noqa: BLE001 - the neutral look below is the answer
        return _neutral("The saved brand could not be read, so PeakCut used the neutral look. ")
    return _neutral("")


def _neutral(note: str):
    """The document with nothing set, as a fresh copy two callers cannot share."""
    try:
        return brand.defaults(), note
    except Exception:  # noqa: BLE001 - DEFAULTS is the last honest answer
        return copy.deepcopy(brand.DEFAULTS), note


def _stored(doc: dict) -> dict:
    """The document as the disk would hold it, so a preview shows what brand.save would really keep."""
    try:
        got = brand.normalise(doc)
        return got if isinstance(got, dict) else copy.deepcopy(doc)
    except Exception:  # noqa: BLE001 - a document we can still show is better than none
        return copy.deepcopy(doc)


def _settings() -> dict:
    """Every setting a round may touch, as {name learn calls it: key in the brand document}.

    learn is imported inside the function on purpose. It pulls in the AI settings, and a page reading a
    preview must never fail to draw because that import failed."""
    mod = None
    try:
        from . import learn as mod  # noqa: PLC0415 - deliberately late, see above
    except Exception:  # noqa: BLE001 - the plain names below still describe the contract
        mod = None
    out = {}
    for const, key in _FROM_LEARN:
        name = _PLAIN_NAMES[const]
        got = getattr(mod, const, None) if mod is not None else None
        if isinstance(got, (tuple, list)) and got and isinstance(got[0], str) and got[0].strip():
            name = got[0].strip()
        out[name] = key
    return out


def _key_for(name) -> str | None:
    """The brand key a setting name lands on, or None when the document keeps nothing for it."""
    clean = _name(name)
    if not clean:
        return None
    try:
        for setting, key in _settings().items():
            if setting == clean:
                return key if key in brand.DEFAULTS else None
    except Exception:  # noqa: BLE001 - an unknown setting is simply not offered
        return None
    return None


def _value_for(key: str, value):
    """The value in the shape the document speaks, or None and a clause saying what is wrong with it.

    The clause is built to sit after "because" in a sentence, which is why it is lower case and has no
    full stop. Only a value that cannot be read at all is refused here; a value the document merely
    adjusts (a length held inside its range) is cleaned and then reported with what was kept."""
    if key == "clip_len":
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None, "a length has to be a number of seconds"
        if not math.isfinite(number):
            return None, "a length has to be a real number of seconds"
        return number, ""
    if key == "captions":
        if isinstance(value, bool):
            return value, ""
        if isinstance(value, (int, float)):
            return bool(value), ""
        word = str(value or "").strip().lower()
        if word in ("true", "1", "yes", "on"):
            return True, ""
        if word in ("false", "0", "no", "off"):
            return False, ""
        return None, "captions are either on or off"
    text = str(value or "").strip()
    if key == "style":
        if not text:
            return None, "a caption look cannot be empty"
        return text.lower()[:40], ""
    if key == "sound":
        return text.lower()[:20], ""
    return text[:120], ""


# ---------------------------------------------------------------- reading the changes

def _pairs(changes) -> list:
    """The changes as a list of (setting, value), whatever shape the caller had them in.

    A round hands a list of {"setting": ..., "value": ...}. A settings form may hand the same thing as a
    plain map. Both are read here so the rest of the file only ever sees one shape."""
    out = []
    items = []
    if isinstance(changes, dict):
        items = list(changes.items())
    elif isinstance(changes, (list, tuple)):
        for c in changes:
            if isinstance(c, dict):
                items.append((c.get("setting", c.get("name")), c.get("value")))
            elif isinstance(c, (list, tuple)) and len(c) == 2:
                items.append((c[0], c[1]))
    for name, value in items:
        setting = _name(name)
        if setting:
            out.append((setting, value))
    return out


# ---------------------------------------------------------------- saying it in English

def _label(key: str) -> str:
    """How a key reads at the start of a sentence."""
    return _LABELS.get(key) or key.replace("_", " ").capitalize()


def _say(key: str, value) -> str:
    """A stored value as a person reads it, never as the type it happens to be."""
    if key == "clip_len":
        try:
            return "%d seconds" % int(round(float(value)))
        except (TypeError, ValueError):
            return _short(value)
    if key == "captions":
        return "on" if bool(value) else "off"
    return _short(value)


def _short(value, width: int = 80) -> str:
    """A value small enough to sit inside one sentence, with an empty one named as none."""
    if isinstance(value, bool):
        return "on" if value else "off"
    if value is None:
        return "none"
    text = str(value).strip()
    if not text:
        return "none"
    return text if len(text) <= width else text[:width - 3].rstrip() + "..."


def _unknown_line(name: str) -> str:
    """One sentence saying the document has no home for this setting."""
    return "PeakCut's brand keeps nothing called %s, so that change would be dropped." % _short(name, 40)


def _stay_line(key: str, value, because: str) -> str:
    """One sentence saying a setting would not move, and why, in the same words everywhere."""
    return "%s would stay at %s, because %s." % (_label(key), _say(key, value), because)


def _why(written: list, ignored: list) -> str:
    """The whole call in one line: what was written, and what was left alone."""
    if written and ignored:
        return "Wrote %s. %s refused, with the reason beside it." % (
            _count(len(written), "setting"),
            "One change was" if len(ignored) == 1 else "%d changes were" % len(ignored))
    if written:
        return "Wrote %s." % _count(len(written), "setting")
    if ignored:
        return "Nothing was written. " + str(ignored[0].get("why") or "")
    return "There was nothing to apply."


def _count(number: int, word: str) -> str:
    """One item with its word, or several, so a sentence never says "1 settings"."""
    return "1 %s" % word if number == 1 else "%d %ss" % (number, word)


def _count_line(lines: list, key: str) -> bool:
    """Whether a line about this setting is already there, so a setting mentioned twice reads once."""
    head = _label(key) + " would "
    return any(line.startswith(head) for line in lines)


def _same(a, b) -> bool:
    """Whether two stored values are the same value, with numbers compared as numbers.

    A bool is compared as a bool even though Python counts it as a number, so on and off are never read
    as 1 and 0."""
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return float(a) == float(b)
    return str(a if a is not None else "") == str(b if b is not None else "")


def _name(value) -> str:
    """A setting name with nothing around it, short enough to print."""
    return str(value or "").strip()[:40]
