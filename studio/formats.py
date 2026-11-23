"""Plans one clip in one of PeakCut's eight shapes - the spans, label cards, corner badges, blur spans, chat rows
and payoff bar a renderer has to draw - with no ffmpeg, network or file access at all."""
from __future__ import annotations

import re
import unicodedata
from typing import Optional, Sequence

from . import config

Clip = dict
Word = dict
Span = dict
Chip = dict

W, H = config.OUT_W, config.OUT_H

# ---------------------------------------------------------------- the colours and the one frame they sit on
# Every colour here is plain RRGGBB (no 0x, no #), the shape _ass_colour() expects. Pixel numbers are for the
# 1080x1920 frame PeakCut renders, so they do not have to be scaled anywhere.
YEL, RED, ORANGE, WHITE, ROSE = "FFD400", "FF3B30", "FF9500", "FFFFFF", "E11D48"
HEAT = (WHITE, YEL, ORANGE, RED)     # escalation warms up: white -> yellow -> orange -> red
BADGE_X, BADGE_Y = 50, 215           # a corner badge or tag, under the platform's own top bar
BADGE_BOX = "000000@0.55"            # the small dark box behind a badge
TAG_BOX = ROSE + "@0.9"              # the rose box behind an EARLIER / WAIT FOR IT / WATCH HIS FACE tag
CARD_MID = W // 2                    # cards are centred
CARD_FIRST, CARD_REST = 0.9, 0.6     # how long a label card stays up: longer for the first one
CARD_HOOK, CARD_BIG, CARD_SMALL, CARD_LABEL = 78, 330, 190, 80
JUMP_LINE, JUMP_LAST = 150, 170      # the time-jump card is smaller than a numbered card, like the source
BAR_Y, BAR_H = 170, 18               # the waitforit bar, above the badge
BLUR_H = 940                         # the blur box covers the whole webcam panel of the stacked layout (render.STACK_TOP_H)
FLASH = 0.08                         # the white flash that covers a cut, in seconds
TAG_GAP = 600                        # a 10 minute jump is worth an EARLIER tag on its own
MIN_PART, PART_LIMIT = 2.0, 6        # a part must be at least 2 s, and six parts is as many as a Short holds
MIN_TOTAL, MAX_TOTAL = 3.0, 180.0    # the same clip length limit jobs.request_render already enforces
MAX_LABEL, MAX_TEXT, MAX_LABELS = 24, 24, 16
REVEAL_DEFAULT, REVEAL_MIN, REVEAL_MAX = 1.6, 0.3, 6.0
SQUEEZE_DEFAULT, SQUEEZE_MAX = 1.5, 5.0
CHAT_MAX, CHAT_TEXT_MAX = 5, 40
CHAT_LIFE, CHAT_GAP, CHAT_FIRST = 2.2, 0.55, 0.2      # one bubble lives 2.2 s, the next pops 0.55 s later
CHAT_X, CHAT_YB, CHAT_ROW = 40, 1440, 112             # left edge, the first bubble's centre, one row per bubble
CUT_MIN_PIECE, CUT_MAX_PIECES = 1.2, 8                # squeeze: never leave a stub, never make a stutter reel
ENDCARD_MAX = 60

# The eight shapes. needs_parts is what check() enforces; the hint is the one line the clip dialog shows.
FORMATS = {
    "moment": {"label": "Moment", "needs_parts": 0, "hint": "one strong clip, the default"},
    "callback": {"label": "Callback", "needs_parts": 2,
                 "hint": "a setup early and its payoff much later (a promise, a prediction, a bet)"},
    "compilation": {"label": "Compilation", "needs_parts": 3,
                    "hint": "the same thing happens 3-5 times in a stream: numbered, best last"},
    "escalation": {"label": "Escalation", "needs_parts": 3,
                   "hint": "the same thing keeps getting worse in order (strike 1, 2, 3)"},
    "thenvsnow": {"label": "Then vs now", "needs_parts": 2,
                  "hint": "a claim or a plan, then what really happened (prediction vs reality)"},
    "reveal": {"label": "Reveal", "needs_parts": 0,
               "hint": "the face is hidden for a second or two while the thing plays, then it clears"},
    "chat": {"label": "Chat", "needs_parts": 0, "hint": "the moment is funny but chat's lines are the joke"},
    "waitforit": {"label": "Wait for it", "needs_parts": 0,
                  "hint": "a quiet or slow build into one big payoff: the bar teases it"},
}
KINDS = tuple(FORMATS)
NEEDS_PARTS = {k: int(v["needs_parts"]) for k, v in FORMATS.items() if v["needs_parts"]}

# The extra shapes the final pass can cut out of the joined Short: name -> (width, height, crop y).
ASPECTS = {"4:5": (1080, 1350, 190), "1:1": (1080, 1080, 320)}


# What a person is told about each shape, in plain words: the sentence says what the viewer sees, "best" says when
# to pick it. `joins` shapes stitch several separate moments of one video into one Short: studio/montage.py picks the
# moments and joins them, and the "Montages" page asks for it (they are not in the single-clip editor, because one
# clip holds one moment). `chat` needs lines of chat text, which PeakCut cannot know (see _REASON).
INFO = {
    "moment": {"line": "One highlight, cut cleanly, with your hook title and captions. Nothing else is added.",
               "best": "most clips: a funny, loud or surprising moment"},
    "callback": {"line": "Shows the setup first, then jumps to the payoff much later in the stream.",
                 "best": "promises, predictions and bets that pay off later", "joins": True},
    "compilation": {"line": "Counts down several similar moments, #3, #2, #1, with the best one last.",
                    "best": "the same thing happening again and again", "joins": True},
    "escalation": {"line": "Strike 1, 2, 3: the same thing getting worse each time, the label heating up.",
                   "best": "rage, fails and running jokes that build", "joins": True},
    "thenvsnow": {"line": "A THEN card with the claim, a NOW card with what really happened.",
                  "best": "predictions versus reality", "joins": True},
    "reveal": {"line": "The webcam on top is blurred under a WATCH HIS FACE tag, then clears with a flash.",
               "best": "jump scares and reactions to something shocking", "webcam": True},
    "chat": {"line": "Chat messages pop up over the clip right after the big moment.",
             "best": "trolling and reactions where chat is the joke", "chat": True},
    "waitforit": {"line": "A WAIT FOR IT tag and a bar that fills up, then a flash on the big moment.",
                  "best": "a slow build into one big payoff"},
}
# How many moments each joining shape takes, as (fewest, most). Two for the pair shapes, three to five for a count.
MONTAGE_RULES = {"callback": (2, 2), "thenvsnow": (2, 2), "compilation": (3, 5), "escalation": (3, 5)}
JOINS = tuple(MONTAGE_RULES)

_REASON = {
    "joins": "It needs several moments of one video joined into one Short, and the part of Clipstorm that does that "
             "could not be loaded.",
    "chat": "Clipstorm only counts how busy chat was, it does not keep what chat wrote, so it cannot show real "
            "messages. You can type the lines yourself.",
}


def _wired() -> bool:
    """True when the video pipeline hands a finished clip to studio/format_finish.py. Without that hand-over a
    chosen shape changes nothing, so the page must not offer the shapes that need it."""
    try:
        import inspect

        from . import jobs
        return "format_finish" in inspect.getsource(jobs.render_one)
    except Exception:                      # noqa: BLE001 - an unreadable pipeline means "not connected", never a crash
        return False


def _joiner_ready() -> bool:
    """True when studio/montage.py loads, which is what makes the joining shapes real."""
    try:
        from . import montage      # noqa: F401
        return True
    except Exception:              # noqa: BLE001 - a part that will not load means "not available", never a crash
        return False


def public() -> list:
    """The format catalogue for the pages: ids, labels, one plain sentence each, and whether each one really works.
    `state` is "ready", "needs_webcam" (works only on a clip with a webcam picture), "montage" (made from several of
    a video's clips on the Montages page), "needs_lines" (chat: the person types the chat lines) or "unavailable"
    (with `reason`)."""
    wired = _wired()
    joined = _joiner_ready()
    rows = []
    for k, v in FORMATS.items():
        info = INFO.get(k, {})
        state, reason = "ready", ""
        if info.get("joins"):
            state, reason = ("montage", "") if joined and wired else ("unavailable", _REASON["joins"])
        elif info.get("chat"):
            # The recording keeps how many messages arrived each second, never their words. So the lines are typed
            # by the person, and the page says so instead of pretending the stream's chat was copied.
            state, reason = ("needs_lines", _REASON["chat"]) if wired else ("unavailable", _REASON["chat"])
        elif k != "moment" and not wired:
            state, reason = "unavailable", "It is built, but the editor has not been connected to it yet."
        elif info.get("webcam"):
            state = "needs_webcam"
        rows.append({"id": k, "label": v["label"], "needs_parts": v["needs_parts"], "hint": v["hint"],
                     "line": info.get("line", v["hint"]), "best_for": info.get("best", ""),
                     "available": state != "unavailable", "state": state, "reason": reason,
                     "needs_webcam": bool(info.get("webcam")),
                     "min_parts": MONTAGE_RULES.get(k, (0, 0))[0], "max_parts": MONTAGE_RULES.get(k, (0, 0))[1]})
    return rows


# ---------------------------------------------------------------- small, defensive readers
# Clip values arrive from the web form, from an older job.json, and from the AI, so none of them is trusted:
# a missing or silly value becomes the default, and a whole broken clip becomes a plain moment (see plan()).
def _num(value, default=None):
    """A finite float out of whatever was stored, or the default."""
    if value is None or isinstance(value, bool):
        return default
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if v != v or v in (float("inf"), float("-inf")):
        return default
    return v


def _round(value) -> float:
    return round(_num(value, 0.0), 2)


def _parts(pick: dict) -> list:
    """The clip's parts that are objects; anything else in the list is ignored rather than crashed on."""
    raw = pick.get("parts")
    return [p for p in raw if isinstance(p, dict)] if isinstance(raw, list) else []


def _span_duration(pick: dict):
    """The clip's own length in seconds, or None when it does not say."""
    a, b = _num(pick.get("start")), _num(pick.get("end"))
    return (b - a) if a is not None and b is not None and b > a else None


def clean_text(text) -> str:
    """Card and badge text: upper case, every Unicode letter/digit/mark kept, only space # / . ! ? - allowed
    besides. That is what turns "Kai's #3, 2/3!" into "KAIS #3 2/3!" and leaves "Café Ñandú مرحبا" alone."""
    if text is None:
        return ""
    return "".join(c for c in str(text).upper()
                   if unicodedata.category(c)[0] in "LNM" or c in " #/.!?-")


def _clean(text) -> str:
    """Text that is safe in an ASS event: no braces (they start an override block) and no backslashes."""
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", str(text if text is not None else ""))
    return re.sub(r"[\\{}]", "", text).strip()


def _ass_colour(hex_rgb, opacity: float = 1.0) -> str:
    """'FFD400' -> '&H00D4FF&' (ASS stores BGR); with opacity, an alpha byte goes in front, inverted, so
    opacity 0.55 becomes '&H73...' (0x73 == round(255 * 0.45))."""
    rgb = re.sub(r"[^0-9A-Fa-f]", "", str(hex_rgb or "")).upper()
    if not rgb:
        rgb = {"white": "FFFFFF", "black": "000000"}.get(str(hex_rgb or "").strip().lower(), "FFFFFF")
    rgb = rgb[-6:].rjust(6, "0")
    r, g, b = rgb[0:2], rgb[2:4], rgb[4:6]
    body = b + g + r
    alpha = max(0.0, min(1.0, _num(opacity, 1.0)))
    if alpha >= 1.0:
        return "&H" + body + "&"
    return "&H%02X%s&" % (int(round(255 * (1.0 - alpha))), body)


# ---------------------------------------------------------------- what a clip is
def fmt_of(pick: dict) -> str:
    """The clip's format: a clip with parts and no format is a callback, one without either is a moment."""
    if not isinstance(pick, dict):
        raise ValueError("a clip must be an object")
    fmt = pick.get("format")
    if fmt is None or (isinstance(fmt, str) and not fmt.strip()):
        # the presence of a parts list is the signal, even a malformed one: check() then says what is wrong
        raw = pick.get("parts")
        has_parts = isinstance(raw, list) and bool(raw)
        return "callback" if has_parts else "moment"
    fmt = str(fmt).strip().lower()
    if fmt not in FORMATS:
        raise ValueError(f"unknown format {fmt!r}; formats: {', '.join(FORMATS)}")
    return fmt


def spans(pick: dict) -> list:
    """The ordered spans to render: the clip's own parts for the part formats, its start/end for the others."""
    fmt = fmt_of(pick)
    layout = str(pick.get("layout") or "blur")
    hook = _clean(pick.get("hook"))
    if fmt in NEEDS_PARTS:
        out = []
        for k, part in enumerate(_parts(pick)):
            out.append({"start": _round(part.get("start")), "end": _round(part.get("end")),
                        "label": clean_text(part.get("label"))[:MAX_LABEL],
                        "layout": str(part.get("layout") or layout),
                        # the hook is burned into one part only: the card carries it for the numbered formats
                        "hook": hook if (fmt == "callback" and k == 0) else ""})
        return out
    return [{"start": _round(pick.get("start")), "end": _round(pick.get("end")), "label": "",
             # reveal blurs the top of the frame, which is where the facecam is in the stack layout
             "layout": "stack" if fmt == "reveal" else layout, "hook": hook}]


def _covers(low: float, high: float, parts: list) -> bool:
    """True when the clip's own start and end already take in every part (so a part outside them is a mistake)."""
    starts = [_num(p.get("start")) for p in parts]
    ends = [_num(p.get("end")) for p in parts]
    if any(v is None for v in starts + ends):
        return False
    return low <= min(starts) + 0.5 and high >= max(ends) - 0.5


def _check_total(fmt: str, total: float) -> None:
    if total < MIN_TOTAL or total > MAX_TOTAL:
        raise ValueError(f"a {fmt} clip must be {MIN_TOTAL:.0f}-{MAX_TOTAL:.0f} s long (this one is {total:.1f} s)")


def _check_text(pick: dict, key: str, limit: int = MAX_TEXT) -> None:
    if pick.get(key) is not None and len(clean_text(pick.get(key))) > limit:
        raise ValueError(f"{key} can be at most {limit} characters")


def check(pick: dict) -> None:
    """Raises ValueError, in words a person can act on, when this clip cannot be rendered as its format."""
    if not isinstance(pick, dict):
        raise ValueError("a clip must be an object")
    fmt = fmt_of(pick)
    dur = _span_duration(pick)
    if fmt in NEEDS_PARTS:
        parts = _parts(pick)
        need = NEEDS_PARTS[fmt]
        if len(parts) < need:
            raise ValueError(f"{fmt} needs at least {need} parts")
        if len(parts) > PART_LIMIT:
            raise ValueError(f"{fmt} takes at most {PART_LIMIT} parts")
        low, high = _num(pick.get("start")), _num(pick.get("end"))
        bounded = low is not None and high is not None and high > low
        total = 0.0
        for i, part in enumerate(parts):
            a, b = _num(part.get("start")), _num(part.get("end"))
            if a is None or b is None:
                raise ValueError(f"part {i + 1} needs a start and an end")
            if b <= a:
                raise ValueError(f"part {i + 1} ends before it starts")
            if b - a < MIN_PART:
                raise ValueError(f"part {i + 1} is {b - a:.1f} s long; every part must be at least {MIN_PART:.0f} s")
            # A callback can jump 40 minutes, far beyond one clip's own span, so the parts are the widest thing
            # that may be checked: a part is only out of bounds when a span that already covers every part
            # still misses it.
            if bounded and _covers(low, high, parts) and (a < low - 0.5 or b > high + 0.5):
                raise ValueError(f"part {i + 1} ({a:.1f}-{b:.1f} s) is outside this clip ({low:.1f}-{high:.1f} s)")
            if len(clean_text(part.get("label"))) > MAX_LABEL:
                raise ValueError(f"a part label can be at most {MAX_LABEL} characters")
            total += b - a
        _check_total(fmt, total)
    elif dur is not None:
        _check_total(fmt, dur)
    _check_text(pick, "tag")
    if fmt == "callback":
        _check_text(pick, "jump")
    if fmt == "escalation":
        _check_text(pick, "word")
    if fmt == "thenvsnow" and pick.get("labels") is not None:
        labels = pick.get("labels")
        if not isinstance(labels, list) or len(labels) != 2:
            raise ValueError('thenvsnow needs two labels, like ["THEN", "NOW"]')
        if any(len(clean_text(x)) > MAX_LABELS for x in labels):
            raise ValueError(f"a label can be at most {MAX_LABELS} characters")
    if fmt == "reveal" and pick.get("reveal") is not None:
        r = _num(pick.get("reveal"), REVEAL_DEFAULT)
        if not REVEAL_MIN <= r <= REVEAL_MAX:
            raise ValueError(f"reveal must be {REVEAL_MIN}-{REVEAL_MAX:.0f} s of blur")
    if fmt == "waitforit" and pick.get("squeeze") is not None:
        gap = _num(pick.get("squeeze"), SQUEEZE_DEFAULT)
        if not 0.0 <= gap <= SQUEEZE_MAX:
            raise ValueError(f"squeeze must be 0-{SQUEEZE_MAX:.0f} s (0 keeps every pause)")
    if fmt in ("chat", "waitforit") and pick.get("payoff") is not None:
        own = _num(pick.get("payoff"))
        if own is None:
            raise ValueError("payoff must be a number of seconds")
        if own < 0.5 or (dur is not None and own > dur):
            raise ValueError(f"payoff must be between 0.5 and {dur:.1f} s" if dur else "payoff must be at least 0.5 s")
    if fmt == "chat" and pick.get("chat") is not None:
        lines = pick.get("chat")
        if not isinstance(lines, list):
            raise ValueError("chat must be a list of lines")
        if len(lines) > CHAT_MAX:
            raise ValueError(f"chat takes at most {CHAT_MAX} lines")
        for line in lines:
            if not isinstance(line, str):
                raise ValueError("every chat line must be text")
            if len(line) > CHAT_TEXT_MAX:
                raise ValueError(f"a chat line can be at most {CHAT_TEXT_MAX} characters")


# ---------------------------------------------------------------- where the payoff is
def _payoff_floor(dur: float) -> float:
    """The source's fallback when nothing can measure the payoff: a bit past the middle of the clip."""
    if dur <= 0.5:
        return round(max(0.05, dur * 0.6), 2)
    return round(min(dur * 0.6, dur - 0.05), 2)


def _word_peak(span: dict, words, dur: float):
    """Start of the busiest second of speech in the last two thirds of the span, seconds into the span.
    A stand-in for the source's loudest 50 ms: at plan time there is no audio yet, only the transcript."""
    start = _num(span.get("start"), 0.0)
    hits = []
    for w in words or []:
        if not isinstance(w, dict):
            continue
        s = _num(w.get("s"))
        if s is None:
            continue
        rel = s - start
        if 0.0 <= rel < dur:
            hits.append(rel)
    if not hits:
        return None
    tail = [t for t in hits if t >= dur / 3.0] or hits
    narrow = [t for t in tail if t + 1.0 <= dur] or tail
    # the most words in one second wins; on a tie the later one does, because a payoff usually lands late
    return max(narrow, key=lambda t: (sum(1 for x in narrow if t <= x < t + 1.0), t))


def payoff_at(pick: dict, words: Optional[Sequence[dict]], span: dict) -> tuple:
    """(seconds into the span, how it was found): the clip's own payoff if it has one, else the busiest speech
    in the last two thirds, else 0.6 of the span. The renderer can replace the guess with a real audio measure."""
    dur = max(0.1, _num(span.get("end"), 0.0) - _num(span.get("start"), 0.0))
    own = _num(pick.get("payoff"))
    if own is not None:
        return round(max(0.0, min(own, dur)), 2), "pick"
    peak = _word_peak(span, words, dur)
    if peak is None:
        return _payoff_floor(dur), "fallback"
    return round(max(dur / 3.0 + 0.02, min(peak, dur - 0.02)), 2), "words"


def squeeze_cuts(span: dict, words: Optional[Sequence[dict]], gap: float = SQUEEZE_DEFAULT) -> list:
    """The quiet stretches longer than `gap` taken out of a span, as pieces of {start, end, t} where t is where the
    piece begins in the joined result. No words, or gap 0, means one piece: exactly the clip as it is today."""
    start = _num(span.get("start"), 0.0)
    end = _num(span.get("end"), 0.0)
    whole = [{"start": round(start, 2), "end": round(end, 2), "t": 0.0}]
    if not gap or gap <= 0 or end - start < MIN_PART:
        return whole
    inside = []
    for w in words or []:
        if not isinstance(w, dict):
            continue
        s = _num(w.get("s"))
        if s is not None and start <= s < end:
            inside.append(w)
    if len(inside) < 2:
        return whole
    inside.sort(key=lambda w: _num(w.get("s"), 0.0))
    cuts, prev_end = [], None
    for w in inside:
        s = _num(w.get("s"))
        e = _num(w.get("e"))
        if s is None:
            continue
        if prev_end is not None and s - prev_end > gap:
            cuts.append((prev_end, s))
        prev_end = s if prev_end is None else max(prev_end, e if e is not None else s)
    if not cuts:
        return whole
    bounds, cursor = [], start
    for a, b in cuts:
        if a - cursor >= CUT_MIN_PIECE:      # a piece too short to read is not worth a jump cut: keep it whole
            bounds.append((cursor, a))
            cursor = b
    bounds.append((cursor, end))
    if len(bounds) < 2 or len(bounds) > CUT_MAX_PIECES:
        return whole                          # one stub, or a stutter reel: leave the clip alone
    pieces, at = [], 0.0
    for a, b in bounds:
        pieces.append({"start": round(a, 2), "end": round(b, 2), "t": round(at, 2)})
        at += b - a
    return pieces


def _squeezed_time(pieces: list, start: float, rel: float) -> float:
    """Where a moment of the original span ends up in the joined result (a cut moment joins the piece after it)."""
    at = start + rel
    for piece in pieces:
        if piece["start"] <= at <= piece["end"]:
            return round(piece["t"] + (at - piece["start"]), 2)
    after = [p for p in pieces if p["start"] > at]
    if after:
        return round(after[0]["t"], 2)
    last = pieces[-1]
    return round(last["t"] + last["end"] - last["start"], 2)


# ---------------------------------------------------------------- the decoration plan
def _chip(kind: str, span: int, **fields) -> Chip:
    """One thing drawn on one span. Every chip carries every key so a renderer never has to test for presence."""
    chip = {"kind": kind, "span": span, "text": "", "size": 0, "color": WHITE, "box": None,
            "t0": None, "t1": None, "dur": None, "lines": []}
    chip.update(fields)
    return chip


def _badge_chip(span: int, text: str, size: int, color: str, box: Optional[str], t0=None, t1=None,
                kind: str = "badge") -> Chip:
    return _chip(kind, span, text=text, size=size, color=color, box=box, t0=t0, t1=t1, x=BADGE_X, y=BADGE_Y)


def _card_chip(span: int, text: str, lines: list, dur: float) -> Chip:
    """A label card. It goes *before* its span in the joined clip, and its lines are (text, size, colour)."""
    return _chip("card", span, text=text, lines=list(lines), dur=float(dur), x=CARD_MID, at="before")


def _jump_lines(text: str) -> list:
    """A time-jump card puts its last word on its own line, the way the source's card did."""
    words = text.split() or ["LATER"]
    lines = [" ".join(words[:-1]), words[-1]] if len(words) > 1 else words
    return [(line, JUMP_LAST if i == len(lines) - 1 else JUMP_LINE, WHITE) for i, line in enumerate(lines)]


def _labels(pick: dict) -> list:
    """thenvsnow's two words, cleaned, with the source's defaults for anything missing."""
    raw = pick.get("labels")
    out = ["THEN", "NOW"]
    if isinstance(raw, list) and len(raw) == 2:
        for i, x in enumerate(raw):
            out[i] = clean_text(x)[:MAX_LABELS] or out[i]
    return out


def _heat(k: int, n: int) -> str:
    """The escalation ramp: index round(3k/(n-1)) clamped to 3, so 3 parts go white -> orange -> red."""
    return HEAT[min(3, round(3.0 * k / max(n - 1, 1)))]


def _numbered_text(fmt: str, pick: dict, k: int, n: int) -> tuple:
    """(big card text, badge text, colour) for part k of a numbered format."""
    if fmt == "compilation":
        text = f"#{n - k}"          # counts down, so the best clip is last
        return text, text, YEL
    if fmt == "escalation":
        word = clean_text(pick.get("word") or "ATTEMPT")[:MAX_LABEL].strip() or "ATTEMPT"
        return f"{word} {k + 1}", f"{word} {k + 1}/{n}", _heat(k, n)
    labels = _labels(pick)
    text = labels[min(k, 1)]
    return text, text, YEL if k == 0 else RED


def _chips_callback(pick: dict, sp: list, out: list) -> None:
    """A small EARLIER tag when the jump is over 10 minutes (or a tag is given), or a full card with jump_card."""
    n = len(sp)
    jump = bool(pick.get("jump_card"))
    for k in range(n):
        if k and jump:
            text = clean_text(pick.get("jump") or "LATER") or "LATER"
            out.append(_card_chip(k, text, _jump_lines(text), CARD_REST))
        if k == 0:
            gap = sp[1]["start"] - sp[0]["end"] if n > 1 else 0.0
            tag = clean_text(pick.get("tag"))
            if gap > TAG_GAP or tag:
                out.append(_badge_chip(0, tag or "EARLIER", 64, WHITE, TAG_BOX, kind="tag"))


def _chips_numbered(pick: dict, sp: list, fmt: str, out: list) -> None:
    """Card before each part, badge during it; the hook rides on the first card, not on the parts."""
    n = len(sp)
    hook = clean_text(pick.get("hook"))
    for k, span in enumerate(sp):
        big, badge, color = _numbered_text(fmt, pick, k, n)
        lines = []
        if k == 0 and hook:
            lines.append((hook, CARD_HOOK, YEL))
        lines.append((big, CARD_BIG if len(big) < 5 else CARD_SMALL, color))
        if span.get("label"):
            lines.append((span["label"], CARD_LABEL, WHITE))
        out.append(_card_chip(k, big, lines, CARD_FIRST if k == 0 else CARD_REST))
        out.append(_badge_chip(k, badge, 100, color, BADGE_BOX))


def _reveal_seconds(pick: dict) -> float:
    r = _num(pick.get("reveal"), REVEAL_DEFAULT)
    return max(REVEAL_MIN, min(float(r), REVEAL_MAX))


def _chips_reveal(pick: dict, sp: list, out: list) -> None:
    """Tag and blur box for the first R seconds, then a white flash on the frame it clears."""
    r = _reveal_seconds(pick)
    tag = clean_text(pick.get("tag")) or "WATCH HIS FACE"
    out.append(_badge_chip(0, tag, 90, WHITE, TAG_BOX, t0=0.0, t1=r, kind="tag"))
    out.append(_chip("blur", 0, t0=0.0, t1=r, h=BLUR_H, y=0))
    out.append(_chip("flash", 0, t0=r, t1=r + FLASH))


def _chips_waitforit(pick: dict, sp: list, out: list, payoff: Optional[float]) -> None:
    """Tag and a bar that fills to the payoff, then both vanish in a flash."""
    dur = max(0.1, sp[0]["end"] - sp[0]["start"])
    t0 = _num(payoff)
    if t0 is None:
        t0 = _num(pick.get("payoff"))
    if t0 is None:
        t0 = _payoff_floor(dur)
    t0 = max(0.3, min(float(t0), max(0.3, dur - 0.05)))
    tag = clean_text(pick.get("tag")) or "WAIT FOR IT"
    out.append(_badge_chip(0, tag, 100, WHITE, TAG_BOX, t0=0.0, t1=t0, kind="tag"))
    out.append(_chip("bar", 0, t0=0.0, t1=t0, y=BAR_Y, h=BAR_H, color=YEL, track="000000@0.5"))
    out.append(_chip("flash", 0, t0=t0, t1=t0 + FLASH))


def chat_rows(pick: dict, t0: float, dur: float, n: int = CHAT_MAX) -> list:
    """The bubbles for the chat format, one every 0.55 s from the payoff: [{t, name, color, text}].
    Only the clip's own lines are used here; real Twitch VOD chat is a network call and belongs to the fetch step."""
    raw = pick.get("chat")
    rows = []
    if not isinstance(raw, list):
        return rows
    for i, line in enumerate([x for x in raw if isinstance(x, str)][:n]):
        text = clean_text(line)[:CHAT_TEXT_MAX]
        at = round(float(t0) + CHAT_FIRST + i * CHAT_GAP, 2)
        if not text or at >= dur:
            continue
        rows.append({"t": at, "name": "", "color": WHITE, "text": text})
    return rows


def _chips_chat(pick: dict, sp: list, out: list, payoff: Optional[float]) -> list:
    dur = max(0.1, sp[0]["end"] - sp[0]["start"])
    t0 = _num(payoff)
    if t0 is None:
        t0 = _num(pick.get("payoff"))
    if t0 is None:
        t0 = _payoff_floor(dur)
    rows = chat_rows(pick, float(t0), dur)
    for i, row in enumerate(rows):
        out.append(_chip("chat", 0, text=row["text"], t0=row["t"], t1=row["t"] + CHAT_LIFE, row=i,
                         name=row["name"], name_color=row["color"], life=CHAT_LIFE,
                         x=CHAT_X, y=CHAT_YB, step=CHAT_ROW))
    return rows


def chips(pick: dict, payoff: Optional[float] = None) -> list:
    """The pure decoration plan: one chip per thing drawn, no ffmpeg and no files. Pass `payoff` when it was
    measured from the words or the audio, so the bar and the chat rows land on the right frame."""
    fmt = fmt_of(pick)
    sp = spans(pick)
    out: list = []
    if not sp:
        return out
    if fmt == "callback":
        _chips_callback(pick, sp, out)
    elif fmt in ("compilation", "escalation", "thenvsnow"):
        _chips_numbered(pick, sp, fmt, out)
    elif fmt == "reveal":
        _chips_reveal(pick, sp, out)
    elif fmt == "waitforit":
        _chips_waitforit(pick, sp, out, payoff)
    elif fmt == "chat":
        _chips_chat(pick, sp, out, payoff)
    return out


def finish_options(pick: dict) -> dict:
    """The final pass over the joined Short: all of it off unless the clip asks, so today's clips are untouched."""
    raw = pick.get("aspects")
    aspects = [a for a in raw if isinstance(a, str) and a in ASPECTS] if isinstance(raw, list) else []
    return {"progress": bool(pick.get("progress")), "endcard": _clean(pick.get("endcard"))[:ENDCARD_MAX],
            "aspects": aspects, "bar_h": 12}


# ---------------------------------------------------------------- the plan itself
def _result(fmt: str, sp: list, ch: list, total: float, payoff, squeeze, finish, notes: list,
            warnings: list, error: Optional[str] = None) -> dict:
    """One shape for every answer, so a renderer can index the same keys whether the clip planned or not."""
    for i, span in enumerate(sp):
        span["chips"] = [c for c in ch if c["span"] == i]
    return {
        "ok": error is None,
        "error": error,
        "format": fmt,
        "label": (FORMATS.get(fmt) or {}).get("label", ""),
        "spans": sp,
        "chips": ch,
        "cards": [c for c in ch if c["kind"] == "card"],
        "badges": [c for c in ch if c["kind"] in ("badge", "tag")],
        "blur": [c for c in ch if c["kind"] == "blur"],
        "bars": [c for c in ch if c["kind"] == "bar"],
        "flashes": [c for c in ch if c["kind"] == "flash"],
        "chat": [c for c in ch if c["kind"] == "chat"],
        "payoff": payoff,
        "squeeze": squeeze,
        "finish": finish,
        "layout": sp[0]["layout"] if sp else "blur",
        "hook": sp[0]["hook"] if sp else "",
        "total": round(float(total), 2),
        "notes": notes,
        "warnings": warnings,
    }


def _failed(pick: dict, message: str) -> dict:
    """A clip that cannot be planned still renders: as the plain moment it would have been before formats existed."""
    span = {"start": _round(pick.get("start")), "end": _round(pick.get("end")), "label": "",
            "layout": str(pick.get("layout") or "blur"), "hook": _clean(pick.get("hook"))}
    dur = max(0.0, span["end"] - span["start"])
    return _result("moment", [span], [], dur, None, None, finish_options(pick), [], [message], error=message)


def _plan_span(pick: dict, words, span: dict, fmt: str, notes: list, warnings: list):
    """The payoff and the silent cuts for the formats that need them; (payoff, squeeze, total)."""
    total = max(0.0, span["end"] - span["start"])
    if fmt not in ("chat", "waitforit"):
        return None, None, total
    t0, how = payoff_at(pick, words, span)
    if how == "fallback":
        notes.append(f"payoff at {t0:.1f}s (no transcript to measure it, so 0.6 of the clip)")
    else:
        notes.append(f"payoff at {t0:.1f}s ({how})")
    payoff = {"span": 0, "t": t0, "how": how}
    if t0 < 2.5:
        warnings.append("payoff in the first 2.5 s, nothing to wait for; use format moment")
    # The quiet-stretch cuts (squeeze_cuts) are not applied to the finished clip, so the payoff stays where the
    # clip really has it. Cutting a clip's pauses is the "Remove dead air" option, which does it for every format.
    squeeze = None
    return payoff, squeeze, total


def plan(pick: dict, words: Optional[Sequence[dict]] = None) -> dict:
    """Everything a renderer needs for one clip. The parts, the cards, the badges and the blur spans are here;
    nothing is drawn, and nothing is measured with ffmpeg, so this never raises - a clip that cannot be planned
    comes back as a plain moment with the reason in `error` and in `warnings`."""
    if not isinstance(pick, dict):
        return _failed({}, "a clip must be an object")
    try:
        fmt = fmt_of(pick)
        check(pick)
    except Exception as e:                  # noqa: BLE001 - the docstring promises plan() never raises
        return _failed(pick, str(e))

    sp = spans(pick)
    if not sp:
        return _failed(pick, "this clip has no span to render")
    notes, warnings = [], []
    payoff, squeeze, total = _plan_span(pick, words, sp[0], fmt, notes, warnings)
    if len(sp) > 1:
        total = sum(max(0.0, s["end"] - s["start"]) for s in sp)

    ch = chips(pick, payoff["t"] if payoff else None)
    if fmt == "reveal":
        notes.append(f"facecam blurred for {_reveal_seconds(pick):.1f}s, then a {FLASH:.2f}s flash")
        warnings.append("reveal wants the stack layout (facecam on top); without it the blur covers the top of the frame")
    if fmt == "chat" and not [c for c in ch if c["kind"] == "chat"]:
        warnings.append('chat needs its own lines: "chat": ["KEKW", ...]')
    if fmt in ("chat", "waitforit") and payoff:
        notes.append(f"payoff at {payoff['t']:.1f}s ({payoff['how']})")

    total += sum(c["dur"] or 0.0 for c in ch if c["kind"] == "card")
    if total and not 8.0 <= total <= 40.0:
        warnings.append(f"outside 8-40 s ({total:.1f}s)")
    return _result(fmt, sp, ch, total, payoff, squeeze, finish_options(pick), notes, warnings)
