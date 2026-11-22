"""The brake on Improve rounds: how many may run in a day, and how many tokens they may cost.

A round spends the operator's own AI key, so it costs them money. `studio/learn.py` already refuses a second
round inside six hours, and that keeps ordinary use to about four a day. This file is the second brake, for
the cases where the first one is not enough: a preview pressed in a loop, `brain.ask_ai` retrying every model
three times after a rate limit, or a later change that forgets the six hour wait.

Both ceilings look back over a rolling 24 hours rather than resetting at midnight, so a round run this evening
is still counted tomorrow evening and a budget never comes back in the middle of a working night.

Nothing here talks to the AI and no web framework is imported: it reads and writes one small record of rounds.
Importing this module can never stop the server or the Improve page from drawing.

    studio/learn_guard.py   this file: the two ceilings, the round record, and the sentences about them
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from . import config

# ---------------------------------------------------------------- the two ceilings
# `learn.MIN_ROUND_SECONDS` is six hours, so an ordinary day is at most four rounds. Eight is twice that: someone
# who takes every round as soon as it is offered is never refused, and a loop that ignores the six hour wait
# still stops the same morning instead of running until the key has no credit left.
MAX_CALLS_PER_DAY = 8

# A round sends a dozen sentences about a channel and reads back a small JSON answer, which is a few thousand
# tokens on a small model. Eight of those stay well under 40000, so 60000 never refuses an honest day. It does
# stop the shapes that cost real money: a model that writes pages, or `brain.ask_ai` retrying three times on
# every model after a rate limit.
MAX_TOKENS_PER_DAY = 60_000

_WINDOW = 24 * 60 * 60       # what "in the last 24 hours" means, for both ceilings
_KEEP = 2 * _WINDOW          # rows older than this are dropped, so the small file cannot grow forever
_MAX_ROWS = 400              # a hard cap, in case a clock change writes rows dated far ahead

_lock = threading.Lock()     # two rounds for one person at once must not write over each other


def _file(uid: str) -> Path:
    """Where one person's rounds are recorded: next to their other Improve settings.

    One file per person, not one shared file, so two people running a round at the same moment cannot lose
    each other's count."""
    return config.user_dir(uid) / "learn_spend.json"


def _rows(uid: str) -> list:
    """Every saved round, oldest first, or an empty list when there is none or it cannot be read.

    A broken or hand-edited record reads as "nothing has been spent". That is the same rule `learn.py` applies
    to its own log, and it is the softer failure: a record of spending must never be the thing that stops a
    page from drawing."""
    try:
        got = json.loads(_file(uid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = got.get("rounds") if isinstance(got, dict) else None
    if not isinstance(rows, list):
        return []
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        try:
            at, tokens = float(r.get("at") or 0), int(r.get("tokens") or 0)
        except (TypeError, ValueError):
            continue
        if at > 0:
            out.append({"at": at, "tokens": max(0, tokens)})
    out.sort(key=lambda r: r["at"])
    return out


def _recent(rows: list, now: float | None = None) -> list:
    """The rounds that still count: the ones inside the last 24 hours."""
    now = time.time() if now is None else now
    # A row dated slightly in the future still counts, so moving the clock back cannot hand a spent budget back.
    return [r for r in rows if r["at"] > now - _WINDOW]


def spent(uid: str) -> dict:
    """What this person's rounds have used in the last 24 hours.

    `calls` is how many rounds ran, `tokens` is what they reported together, and `at` is when the newest one
    ran, or 0.0 when there was none. Every number is 0 when the record cannot be read, so a caller never has
    to handle a failure here."""
    empty = {"calls": 0, "tokens": 0, "at": 0.0}
    try:
        rows = _recent(_rows(uid))
    except Exception:  # noqa: BLE001 - a record PeakCut cannot read is an empty record
        return empty
    if not rows:
        return empty
    return {"calls": len(rows), "tokens": sum(r["tokens"] for r in rows), "at": rows[-1]["at"]}


def allow(uid: str) -> dict:
    """Whether a round may start now.

    `ok` is False only when one of the ceilings is used up, and `why` is then one sentence naming that ceiling
    and saying how long until it frees. It answers True when the record cannot be read: a record PeakCut cannot
    see cannot prove a ceiling was reached, and the AI key's own quota is still the backstop. Never raises."""
    try:
        rows = _recent(_rows(uid))
    except Exception:  # noqa: BLE001 - see the docstring: no record is no proof of spending
        rows = []
    calls, tokens = len(rows), sum(r["tokens"] for r in rows)
    if calls >= MAX_CALLS_PER_DAY:
        wait = _wait_text(rows[0]["at"] + _WINDOW - time.time())
        return {"ok": False, "why": (
            f"PeakCut has used all {MAX_CALLS_PER_DAY} rounds allowed in the last 24 hours. "
            f"The next one can start in {wait}, when the oldest round falls outside that window.")}
    if tokens >= MAX_TOKENS_PER_DAY:
        wait = _wait_text(_tokens_clear_at(rows) - time.time())
        return {"ok": False, "why": (
            f"PeakCut has used all {MAX_TOKENS_PER_DAY:,} tokens allowed in the last 24 hours. "
            f"The next round can start in {wait}, when earlier rounds fall outside that window.")}
    return {"ok": True, "why": ""}


def note(uid: str, tokens: int) -> None:
    """Record one round: it ran now, and it reported this many tokens.

    The round's AI call is already in the AI usage record, put there by `usage.record` inside `brain.ask_ai`.
    So this keeps a separate line per round instead of a second row there, which would show the operator one
    call twice and double the token total on the AI usage page. A record that cannot be written is dropped
    quietly: a round that already happened must not fail after the fact."""
    try:
        at, cost = time.time(), max(0, int(tokens))
    except (TypeError, ValueError):
        at, cost = time.time(), 0
    try:
        with _lock:
            rows = [r for r in _rows(uid) if r["at"] > at - _KEEP]
            rows.append({"at": at, "tokens": cost})
            f = _file(uid)
            f.parent.mkdir(parents=True, exist_ok=True)
            tmp = f.with_suffix(".tmp")
            tmp.write_text(json.dumps({"rounds": rows[-_MAX_ROWS:]}, indent=1), encoding="utf-8")
            tmp.replace(f)
    except Exception:  # noqa: BLE001 - a round that already happened is not worth failing over its record
        return


def report(uid: str) -> str:
    """One sentence about how much is left today, for the Improve page: "8 of 8 rounds left today".

    It says both budgets rather than implying the round count is the only ceiling, because a day can run out of
    tokens while rounds are still left. The window is the last 24 hours, which is what the page calls today.
    Never raises."""
    try:
        rows = _recent(_rows(uid))
    except Exception:  # noqa: BLE001 - no record is an empty record
        rows = []
    left = max(0, MAX_CALLS_PER_DAY - len(rows))
    tokens_left = max(0, MAX_TOKENS_PER_DAY - sum(r["tokens"] for r in rows))
    if not left:
        wait = _wait_text(rows[0]["at"] + _WINDOW - time.time())
        return f"No rounds left today. The next one can start in {wait}."
    if not tokens_left:
        wait = _wait_text(_tokens_clear_at(rows) - time.time())
        return (f"No round can run today: the {MAX_TOKENS_PER_DAY:,} token budget is used up, "
                f"with {left} of {MAX_CALLS_PER_DAY} rounds still unused. The next one can start in {wait}.")
    return f"{left} of {MAX_CALLS_PER_DAY} rounds left today, and {tokens_left:,} of {MAX_TOKENS_PER_DAY:,} tokens."


def _tokens_clear_at(rows: list) -> float:
    """The first moment the counted tokens drop under the ceiling, as the oldest rounds leave the window."""
    left = sum(r["tokens"] for r in rows)
    for r in rows:                      # oldest first, so the answer only moves forward
        left -= r["tokens"]
        if left < MAX_TOKENS_PER_DAY:
            return r["at"] + _WINDOW
    return (rows[-1]["at"] if rows else time.time()) + _WINDOW


def _wait_text(seconds: float) -> str:
    """A stretch of time the way a person says it, "2 h 14 min", rounded up so it never promises a moment that
    is still refused."""
    mins = int(max(0.0, float(seconds) + 59) // 60)
    hours, mins = divmod(mins, 60)
    if hours and mins:
        return f"{hours} h {mins} min"
    if hours:
        return f"{hours} h"
    return f"{mins} min" if mins else "less than a minute"
