"""One round of learning, in the shapes a page can draw without guessing.

`studio/learn.py` records a round as a dict with keys that grew over time (`changes` kept,
`applied` landed, `moved` compared, `undone` stamped later). This module is the one place that
turns such a record into the fixed shape the Improve page and the Insights CSV use, so a page never
has to defend against a missing key or print "None" into a sentence.

Nothing here reads the database, calls an AI or changes a setting. It only reads a dict and writes
plain words, and every public function returns its empty shape instead of raising.
"""

import time

# The keys a page is promised. Kept in one place so a test, or a reader, can see the whole contract.
_KEYS = ("at", "when", "days", "source", "facts", "changes", "dropped", "applied",
         "saying", "effect", "moved", "reading", "undone")


def _empty() -> dict:
    """The row for a round that is not there: every key present, each one empty for its type."""
    return {"at": 0.0, "when": "", "days": 0, "source": "", "facts": [], "changes": [],
            "dropped": [], "applied": [], "saying": "", "effect": "", "moved": [],
            "reading": {}, "undone": False}


def _num(value, fallback: float = 0.0) -> float:
    """A number or the fallback. Also refuses the not-a-number and infinite values a float can hold."""
    try:
        got = float(value)
    except (TypeError, ValueError):
        return fallback
    if got != got or got in (float("inf"), float("-inf")):
        return fallback
    return got


def _text(value) -> str:
    """A value as words a person can read. Missing becomes "not set" so a sentence never says None."""
    if value is None or value == "":
        return "not set"
    if isinstance(value, bool):
        return "yes" if value else "no"
    try:
        text = str(value).strip()
    except Exception:  # noqa: BLE001 - a value that cannot become text is not worth an exception
        return "not set"
    return text[:200] if text else "not set"


def _words(value) -> list:
    """A list of sentences with anything that is not a non-empty string dropped."""
    if not isinstance(value, (list, tuple)):
        return []
    return [str(v)[:400] for v in value if isinstance(v, (str, int, float)) and str(v).strip()]


def _dicts(value) -> list:
    """The dict entries of a list, which is all the page can draw from."""
    if not isinstance(value, (list, tuple)):
        return []
    return [v for v in value if isinstance(v, dict)]


def _ago(seconds: float) -> str:
    """A stretch of time the way a person says it: "just now", "12 minutes ago", "3 h 5 min ago"."""
    seconds = max(0.0, _num(seconds))
    if seconds < 90:
        return "just now"
    mins = int(seconds // 60)
    if mins < 60:
        return f"{mins} minutes ago"
    hours, mins = divmod(mins, 60)
    if hours < 24:
        return f"{hours} h {mins} min ago" if mins else f"{hours} h ago"
    days, hours = divmod(hours, 24)
    return f"{days} days ago" if not hours else f"{days} days {hours} h ago"


def when(at) -> str:
    """A moment the way a person says it, relative to now.

    `learn._ago` is imported inside the function on purpose: it is tried first so a round shown on the
    page and the cooldown sentence on the same page use one wording. Importing at the top would make
    `learn` and this module wait on each other if `learn` starts using the report.
    """
    moment = _num(at, 0.0)
    if moment <= 0:
        # No time was recorded. Saying "just now" would be a claim about the past that nothing supports.
        return "at an unknown time"
    gap = max(0.0, time.time() - moment)
    try:
        from . import learn
        said = learn._ago(gap)
        if isinstance(said, str) and said.strip():
            return said
    except Exception:  # noqa: BLE001 - the fallback below is the whole contract of this function
        pass
    return _ago(gap)


def _change_rows(row: dict) -> list:
    """The changes a round proposed, each with what the setting was and what it is now.

    `changes` holds the proposal and `applied` holds what actually landed, including the value read
    from the brand before writing. Pairing them by position is how `learn.run` writes them, and the
    setting name is the fallback when a record was made by hand.
    """
    kept = _dicts(row.get("changes"))
    landed = _dicts(row.get("applied"))
    if not kept:
        # An older record kept only what landed. Showing that is better than showing no change at all.
        kept = landed
    out = []
    for i, c in enumerate(kept):
        same = landed[i] if i < len(landed) else None
        if same is None:
            for a in landed:
                if _text(a.get("setting")) == _text(c.get("setting")):
                    same = a
                    break
        before = same.get("from") if same else None
        after = c.get("value")
        # The applied record is the truth about what the setting now holds; the proposal is the fallback
        # because a dry round never writes anything and only has the proposal to show.
        if same is not None and same.get("to") not in (None, ""):
            after = same.get("to")
        out.append({"setting": _text(c.get("setting")), "from": _text(before),
                    "to": _text(after), "why": _text(c.get("why")), "expect": _text(c.get("expect"))})
    return out


def _dropped_rows(row: dict) -> list:
    """The proposals PeakCut refused, with the reason, so a refusal is visible and not silent."""
    out = []
    for d in _dicts(row.get("dropped")):
        out.append({"setting": _text(d.get("setting")), "value": _text(d.get("value")),
                    "reason": _text(d.get("reason"))})
    return out


def _applied_rows(row: dict) -> list:
    """The changes that really landed, with the value that was there before and the one written."""
    out = []
    for a in _dicts(row.get("applied")):
        out.append({"setting": _text(a.get("setting")), "value": _text(a.get("value")),
                    "ok": bool(a.get("ok")), "from": _text(a.get("from")), "to": _text(a.get("to"))})
    return out


def _moved(row: dict, reading: dict, previous) -> list:
    """Sentences about what changed since the round before this one.

    A round normally carries `moved`, written by `learn.run`. When an older record does not, the two
    readings are compared here, which is arithmetic on the same numbers and not a second opinion.
    """
    said = _words(row.get("moved"))
    if said:
        return said
    if not reading or not isinstance(previous, dict):
        return []
    was = previous.get("reading")
    if not isinstance(was, dict) or not was:
        return []
    try:
        from . import learn
        return _words(learn.compare(was, reading))
    except Exception:  # noqa: BLE001 - a missing comparison is a shorter report, not a failed one
        return []


def shape(round_doc, previous=None) -> dict:
    """The fixed shape of one round: thirteen keys, every one present and never None.

    `round_doc` is a round as `learn.run` records it, or something older with fewer keys. `previous`
    is the round before it and is only used to fill `moved` when the record did not keep it. A missing
    value becomes the empty shape for its type, so a page can print the row as it stands.
    """
    out = _empty()
    try:
        row = round_doc if isinstance(round_doc, dict) else {}
        at = _num(row.get("at"), 0.0)
        reading = row.get("reading") if isinstance(row.get("reading"), dict) else {}
        changes = _change_rows(row)
        out["at"] = at
        out["days"] = int(_num(row.get("days"), 0.0))
        out["source"] = "" if row.get("source") in (None, "") else str(row.get("source"))[:80]
        out["facts"] = _words(row.get("facts"))
        out["changes"] = changes
        out["dropped"] = _dropped_rows(row)
        out["applied"] = _applied_rows(row)
        out["saying"] = "" if row.get("saying") in (None, "") else str(row.get("saying"))[:400]
        out["effect"] = "" if row.get("effect") in (None, "") else str(row.get("effect"))[:400]
        out["moved"] = _moved(row, reading, previous)
        out["reading"] = reading
        # `undo` stamps the moment on the round itself. Any stamp means the settings were put back.
        out["undone"] = bool(row.get("undone"))
        out["when"] = when(at)
        # The contract is the whole point of this module, so it is checked rather than assumed.
        if set(_KEYS) - set(out):
            out.update({k: v for k, v in _empty().items() if k in set(_KEYS) - set(out)})
        return out
    except Exception:  # noqa: BLE001 - the page asks for a row, and an empty row is a usable answer
        return _empty()


def _sentence(text: str) -> str:
    """A line made safe to sit next to another one: it ends with a mark, so two lines cannot run together."""
    said = str(text or "").strip()
    if not said:
        return ""
    return said if said[-1] in ".!?" else said + "."


def _change_sentence(change: dict) -> str:
    """One change as a sentence: what the setting was and what it became."""
    said = f"{change['setting']} from {change['from']} to {change['to']}"
    if change["why"] != "not set":
        said += ", because " + change["why"].rstrip(".").lower()
    return _sentence(said)


def story(row) -> str:
    """One paragraph a person can read without the JSON: what was read, what changed, what it did.

    Accepts a shaped row or a raw round record, so a page can pass either. An empty round says so
    rather than describing nothing at length.
    """
    try:
        got = shape(row)
        if not got["at"] and not got["facts"] and not got["changes"] and not got["applied"]:
            return "Nothing has run yet."

        parts = []
        span = f"the last {got['days']} days" if got["days"] > 0 else "the numbers it had"
        source = f" from {got['source']}" if got["source"] else ""
        # "2 h ago" reads as an ending, "at an unknown time" does not, so the two are phrased apart
        # rather than forced into one template that is wrong for one of them.
        if got["at"]:
            parts.append(f"PeakCut read {span}{source} {when(got['at'])}.")
        else:
            parts.append(f"PeakCut read {span}{source}, at a time it did not record.")

        facts = got["facts"]
        if facts:
            # Two lines is enough for a paragraph; the full list stays in the row for the page to show.
            parts.append("It saw " + " ".join(_sentence(f) for f in facts[:2]))
            if len(facts) > 2:
                parts.append(f"There were {len(facts)} lines in all.")

        changes = got["changes"]
        if changes:
            if got["applied"]:
                parts.append("It changed " + " ".join(_change_sentence(c) for c in changes[:2]))
            else:
                parts.append("It proposed " + " ".join(_change_sentence(c) for c in changes[:2])
                             + " Nothing was written down, so nothing changed.")
        else:
            parts.append("It changed nothing.")

        if got["undone"]:
            parts.append("This round was undone, so those settings are back to what they were.")
        elif got["moved"]:
            parts.append("Against the round before, " + " ".join(_sentence(m).lower()
                                                                for m in got["moved"][:2]))
        elif got["effect"]:
            parts.append(_sentence(got["effect"]))
        else:
            parts.append("There is nothing to compare it with yet.")
        return " ".join(p for p in parts if p)
    except Exception:  # noqa: BLE001 - a paragraph is a courtesy; the row above is the record
        return "This round cannot be read."


def table(rounds) -> dict:
    """A round history as head and rows, for the table and the CSV the Insights page exports.

    The columns are fixed: when, days, source, changed, effect. Every cell is a string, because a CSV
    and a table both want words, and an empty history returns the head with no rows rather than None.
    """
    head = ["when", "days", "source", "changed", "effect"]
    rows = []
    try:
        for item in _dicts(rounds):
            got = shape(item)
            changed = "; ".join(f"{c['setting']} from {c['from']} to {c['to']}"
                                for c in (got["changes"] or got["applied"]))
            if got["undone"]:
                changed = (changed + "; " if changed else "") + "undone"
            rows.append([got["when"], str(got["days"]), got["source"] or "not known",
                         changed or "nothing", got["effect"] or "not known yet"])
    except Exception:  # noqa: BLE001 - a broken row is skipped, the rest of the history still prints
        pass
    return {"head": head, "rows": rows}
