"""Turning a YouTube retention curve into sentences a person can act on.

The curve is YouTube's own: one row per step through a video, each row carrying how much
of the video has played and how much of the audience is still there. This module reads
that curve and says the two things worth putting in front of a round of the AI: what
happens in the first tenth of the video, and whether the tail says the clip is longer
than it needs to be.

There is no channel connected in this install. Every function here therefore has a quiet
answer for a PeakCut that cannot see a curve: no points, no sentences, no exception. A
sentence is never written from a number that was not given; when the curve cannot support
one, the answer is an empty string and the caller says what is missing.

The shape of the data is the one already measured in this repository, at
`studio/api_analytics.py` (the `/api/analytics/retention` route) and `studio/ytstats.py`
(`deep`). Both ask for `audienceWatchRatio` by `elapsedVideoTimeRatio` for one video, and
both turn the ratios into percentages, which is what a person can read.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

# The metrics and dimension the report needs. Same pair the existing retention route asks
# for; a second metric there (relativeRetentionPerformance) is not needed to say a
# sentence, and asking for less is less that can be refused.
_METRICS = "audienceWatchRatio"
_DIMENSION = "elapsedVideoTimeRatio"

# The retention route asks over a wide window (3650 days) because Analytics answers by
# upload date, so a short window hides an older video entirely. The same reasoning holds
# here: the caller's `days` is tried first, and one wide retry happens only when the
# first ask came back with nothing.
_WIDE_DAYS = 3650

# The points of interest, in percent through the video. Five percent is inside the first
# tenth, which is where a hook is won or lost; ninety percent is the tail.
_HOOK_AT = 5.0
_TAIL_AT = 90.0

# A curve's steps are not evenly spaced, so "at 5 percent in" is answered by the nearest
# sample to 5, and only when that sample really is near 5. A quarter of a tenth is far
# enough to cover the usual 1 percent steps and close enough that the sentence is not
# talking about some other part of the video.
_NEAR = 2.5

# Presentation granularity. The curve is rounded to one decimal on the way out, so a
# difference smaller than half of that is noise, not a loss of viewers.
_STEP = 0.05


# ------------------------------------------------------------------ small private tools
def _num(value: Any) -> float | None:
    """A number from a report cell, or None when the cell is empty or not a number."""
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _window(days: int) -> tuple[str, str]:
    """The start and end date strings Analytics wants, counting back from today.

    Mirrors `studio/api_analytics.py:_window` so a curve asked for here covers the same
    days as the one the Insights page draws.
    """
    end = datetime.now(timezone.utc).date()
    span = days if isinstance(days, int) and days > 0 else _WIDE_DAYS
    start = end - timedelta(days=span - 1)
    return start.isoformat(), end.isoformat()


def _reader():
    """(token getter, asker) from `api_analytics`, or a stand-in that is just as quiet.

    The import is done here, not at the top of the module, because importing
    `api_analytics` pulls in FastAPI and the router; a module that only wants to read one
    curve should not need the web layer to be importable, and a broken import must not
    stop a round of the AI. When that import is not available, the token is read the same
    way that file reads it and the report is asked for through `ytstats.analytics`.
    """
    try:
        from . import api_analytics

        return api_analytics._token, api_analytics._ask
    except Exception:  # noqa: BLE001 - the fallback below is the point, not the exception
        pass
    try:
        from . import accounts, ytstats

        return (lambda: accounts.youtube_token() or ""), ytstats.analytics
    except Exception:  # noqa: BLE001 - no reader at all means no curve, which is an answer
        return None, None


def _clean(points: Any) -> list[dict]:
    """The points that can be spoken about, sorted by how far into the video they are.

    Anything that is not a pair of finite numbers is dropped rather than guessed at, and
    an exact repeat of a position keeps the later row, because that is the one the API
    returned last.
    """
    out: dict[float, dict] = {}
    for point in points or []:
        if not isinstance(point, dict):
            continue
        at, kept = _num(point.get("at")), _num(point.get("kept"))
        if at is None or kept is None:
            continue
        out[round(at, 4)] = {"at": float(at), "kept": float(kept)}
    return [out[key] for key in sorted(out)]


def _pct(value: float) -> str:
    """A percentage written the way a person says it: 62, not 62.0."""
    text = f"{round(float(value), 1):.1f}"
    return text[:-2] if text.endswith(".0") else text


def _near(points: list[dict], at: float, lowest: float, highest: float) -> dict | None:
    """The sample closest to `at`, provided one sits within `_NEAR` of it.

    Without that guard the nearest sample on a sparse curve can be half the video away,
    and a sentence about "5 percent in" would then be describing a number measured
    somewhere else, which is the one thing this module must not do.
    """
    band = [p for p in points if lowest <= p["at"] <= highest]
    if not band:
        return None
    best = min(band, key=lambda p: abs(p["at"] - at))
    return best if abs(best["at"] - at) <= _NEAR else None


# --------------------------------------------------------------------------- the curve
def curve(video_id: str, days: int = 28) -> dict:
    """The audience-retention curve for one video, as percentages a person can read.

    Returns `{"points": [{"at": float, "kept": float}], "source": str}`, where `at` is how
    far through the video a sample was taken, from 0 to 100, and `kept` is the share still
    watching at that point, from 0 to 100. `source` is "youtube" when the points came from
    YouTube and "" when there is nothing to show.

    No channel, no token, a video YouTube has no rows for, or any error at all gives
    `{"points": [], "source": ""}`. This function never raises.
    """
    empty = {"points": [], "source": ""}
    try:
        token_get, asker = _reader()
        if token_get is None or asker is None:
            return empty
        raw = str(video_id or "").strip()
        if not raw:
            return empty
        try:
            from . import ytstats

            video = ytstats.vid_id(raw) or raw  # a pasted link is as good as an id
        except Exception:  # noqa: BLE001 - the id is still usable without the helper
            video = raw
        token = str(token_get() or "").strip()
        if not token:
            return empty

        rows: list = []
        for span in (days, _WIDE_DAYS):
            start, end = _window(span)
            rows = asker(token, start, end, _METRICS, dimensions=_DIMENSION,
                         filters="video==" + video) or []
            if rows:
                break
        if not rows:
            return empty

        points: dict[float, dict] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            at = _num(row.get("elapsedVideoTimeRatio"))
            kept = _num(row.get("audienceWatchRatio"))
            if at is None or kept is None:
                continue
            # The API answers in ratios. A person reads percentages, and the rest of
            # PeakCut already speaks in them (the Insights retention route does).
            points[round(at * 100.0, 4)] = {"at": round(at * 100.0, 1),
                                            "kept": round(kept * 100.0, 1)}
        ordered = [points[key] for key in sorted(points)]
        if not ordered:
            return empty
        return {"points": ordered, "source": "youtube"}
    except Exception:  # noqa: BLE001 - a curve is an extra, never a reason to stop
        return empty


# ------------------------------------------------------------------------ the sentences
def drop_off(points: Any, keep: float = 0.5) -> dict:
    """Where the audience first falls to `keep` times the share it started with.

    Returns `{"at": float | None, "kept": float | None}`. `at` is the percentage through
    the video where that happened and `kept` is the share still watching there, both
    rounded to one decimal. Fewer than three points, a starting share of zero, or a
    `keep` that is not a positive number all give `{"at": None, "kept": None}`, because a
    curve that short cannot show a fall rather than a wobble.
    """
    empty = {"at": None, "kept": None}
    try:
        clean = _clean(points)
        if len(clean) < 3:
            return empty
        share = _num(keep)
        if share is None or share <= 0:
            return empty
        start = clean[0]["kept"]
        if start <= 0:
            return empty
        floor = start * share
        for point in clean:
            if point["kept"] <= floor:
                return {"at": round(point["at"], 1), "kept": round(point["kept"], 1)}
        return empty
    except Exception:  # noqa: BLE001 - the empty shape is the answer when this cannot work
        return empty


def hook_signal(points: Any) -> str:
    """One sentence about the first tenth of the video.

    It says how much of the audience is still there at 5 percent in, and how far that is
    below the share the curve started with. An empty string when the curve has no sample
    near 5 percent, or when there are fewer than three points to make a curve of.
    """
    try:
        clean = _clean(points)
        if len(clean) < 3:
            return ""
        near = _near(clean, _HOOK_AT, 0.0, 10.0)
        if near is None:
            return ""
        kept = near["kept"]
        delta = round(clean[0]["kept"] - kept, 1)
        head = f"At {_pct(_HOOK_AT)} percent in, {_pct(kept)} percent are still watching"
        if delta > _STEP:
            return f"{head}, {_pct(delta)} points below where the curve starts."
        if delta < -_STEP:
            return f"{head}, {_pct(abs(delta))} points above where the curve starts."
        return f"{head}, level with where the curve starts."
    except Exception:  # noqa: BLE001 - no sentence is better than a wrong one
        return ""


def length_signal(points: Any, seconds: float = 0.0) -> str:
    """One sentence about the tail of the video.

    It says how much of the audience is left at 90 percent in, and whether the rest of
    the video still loses people, which is what says a shorter cut would hold more of
    them. `seconds` is the clip's own length; when it is given and positive, it is named
    in the sentence. An empty string when the curve has no sample near 90 percent, or
    when there are fewer than three points.
    """
    try:
        clean = _clean(points)
        if len(clean) < 3:
            return ""
        near = _near(clean, _TAIL_AT, 80.0, 100.0)
        if near is None:
            return ""
        end = clean[-1]
        tail = round(near["kept"] - end["kept"], 1)
        length = _num(seconds)
        opening = (f"This {_pct(length)} second clip still has " if length is not None and length > 0
                   else f"At {_pct(_TAIL_AT)} percent in, ")
        body = (f"{_pct(near['kept'])} percent watching at {_pct(_TAIL_AT)} percent in"
                if length is not None and length > 0
                else f"{_pct(near['kept'])} percent are still watching")
        if tail > _STEP:
            return (f"{opening}{body}, and the last part loses {_pct(tail)} more points, "
                    f"so a shorter cut would keep more people.")
        return (f"{opening}{body}, and the last part does not lose viewers, "
                f"so the length is not what is costing people.")
    except Exception:  # noqa: BLE001 - no sentence is better than a wrong one
        return ""


def _drop_sentence(points: Any) -> str:
    """One sentence naming where half the starting audience had gone, or "" when unknown."""
    try:
        half = drop_off(points, 0.5)
        if half["at"] is None:
            return ""
        clean = _clean(points)
        if len(clean) < 3 or clean[0]["kept"] <= 0:
            return ""
        return (f"Half the starting audience is gone by {_pct(half['at'])} percent in, "
                f"with {_pct(half['kept'])} percent still watching.")
    except Exception:  # noqa: BLE001
        return ""


def signals(video_id: str, days: int = 28, seconds: float = 0.0) -> dict:
    """Everything this module can say about one video in a single answer.

    Returns `{"hook": str, "length": str, "drop": dict, "points": int}`. `hook` and
    `length` are the sentences above, empty when the curve cannot support them; `drop` is
    `drop_off`'s answer and `points` is how many samples the curve had. With no channel
    connected the answer is two empty sentences, an empty drop and zero points.
    """
    out = {"hook": "", "length": "", "drop": {"at": None, "kept": None}, "points": 0}
    try:
        got = curve(video_id, days)
        points = got.get("points") or []
        out["points"] = len(points)
        if not points:
            return out
        out["hook"] = hook_signal(points)
        out["length"] = length_signal(points, seconds)
        out["drop"] = drop_off(points)
        return out
    except Exception:  # noqa: BLE001 - the empty shape keeps a round of the AI going
        return out


def lines(video_id: str, days: int = 28, seconds: float = 0.0) -> list:
    """The sentences worth adding to the facts a round of the AI is given.

    Only the sentences that could be written are returned, in the order a person reads
    them: the hook, then where the audience halves, then the length. No channel, no
    curve, or a curve too short to speak about gives an empty list, never an exception.
    """
    try:
        got = curve(video_id, days)
        points = got.get("points") or []
        if len(points) < 3:
            return []
        out = [hook_signal(points), _drop_sentence(points), length_signal(points, seconds)]
        return [text for text in out if text]
    except Exception:  # noqa: BLE001 - a round must never be stopped by an extra
        return []
