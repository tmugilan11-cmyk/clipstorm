"""How the sound work talks to the AI: one helper for words, one for pictures, both counted.

Every prompt in the sound work names the one JSON object it wants, so no schema is sent (AGENTS.md: a schema
made the identical sound prompt four times slower and ran past the timeout). The answer is checked by the
caller instead. A busy service ("503", "429", a dropped read) is waited out and asked again a few times, because
this install's service answers the same prompt fine a few seconds later.

`ask()` raises when no answer came at all, with the words `ai.explain` gives; the callers turn that into a
sentence on the page or a log line. Tokens are written to the usage record with a purpose that starts with
"Sounds:", so the AI usage page shows what the sound picker costs.
"""
from __future__ import annotations

import io
import json
import threading
import time
from typing import Optional

from . import ai, config, usage

PROBE_FILE = "sound_vision.json"
PROBE_KEEP_NO = 24 * 3600
PROBE_KEEP_YES = 7 * 24 * 3600
_lock = threading.Lock()


class Tally:
    """What one piece of work spent: calls, tokens, and the web lookups made for it."""

    def __init__(self):
        self.calls = 0
        self.tokens = 0
        self.web = 0
        self.vision = 0
        self._lock = threading.Lock()

    def add(self, tokens: int = 0, calls: int = 1, web: int = 0, vision: int = 0):
        with self._lock:
            self.calls += calls
            self.tokens += int(tokens or 0)
            self.web += web
            self.vision += vision

    def view(self) -> dict:
        return {"calls": self.calls, "tokens": self.tokens, "web": self.web, "vision": self.vision}


def ready() -> bool:
    return ai.ready()


def ask(prompt: str, purpose: str, timeout: float = 150.0, tally: Optional[Tally] = None, tries: int = 4):
    """One answer from the configured AI, as parsed JSON (a dict or a list). Raises when none came."""
    if not ai.ready():
        raise RuntimeError("No AI is set up, so PeakCut cannot choose sounds. Set one up under AI.")
    last = None
    models = list(ai.models()) or [""]
    for attempt in range(max(1, tries)):
        for model in models:
            try:
                out, sent, wrote = ai.call(model, prompt, None, timeout)
            except Exception as e:  # noqa: BLE001 - tried again below, then explained
                last = e
                continue
            try:
                usage.record(sent, wrote, ("Sounds: " + purpose)[:60])
            except Exception:  # noqa: BLE001 - a usage row that cannot be written never loses an answer
                pass
            if tally is not None:
                tally.add(sent + wrote, calls=0)      # the caller counts the call itself
            ai.clear_problem()
            if isinstance(out, str):
                out = ai._parse(out)
            return out
        low = str(last or "").lower()
        busy = any(w in low for w in ("503", "429", "unavailable", "overloaded", "timed out", "timeout",
                                      "rate limit", "502", "504", "read operation"))
        if not busy:
            break
        time.sleep(min(30.0, 5.0 * (attempt + 1)))
    ai.note_problem(last)
    raise RuntimeError(ai.explain(last) or f"The AI did not answer: {last}")


# ---------------------------------------------------------------- pictures
def vision_on() -> bool:
    """Whether the sound picker may show the AI frames of the clip. `PEAKCUT_SOUND_VISION=0` turns it off."""
    return config.env("PEAKCUT_SOUND_VISION", "1").strip() != "0"


def _probe_file():
    return config.DATA_DIR / PROBE_FILE


def _red_square() -> bytes:
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (96, 96), "white")
    ImageDraw.Draw(im).rectangle([20, 20, 76, 76], fill=(220, 20, 20))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return buf.getvalue()


def can_see(timeout: float = 60.0) -> bool:
    """Whether the AI in use looks at pictures. Asked once per model and address, remembered in the data folder
    (a "no" for a day, a "yes" for a week), so a text-only model is not sent pictures on every clip."""
    if not vision_on() or not ai.ready():
        return False
    who = f"{ai.base_url()}|{(ai.models() or [''])[0]}"
    with _lock:
        try:
            book = json.loads(_probe_file().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            book = {}
        book = book if isinstance(book, dict) else {}
        hit = book.get(who)
        keep = PROBE_KEEP_YES if (hit or {}).get("ok") else float((hit or {}).get("keep") or PROBE_KEEP_NO)
        if hit and time.time() - hit.get("at", 0) < keep:
            return bool(hit.get("ok"))
        ok, why, keep = False, "", PROBE_KEEP_NO
        try:
            text, sent, wrote = ai.see("What colour is the square in this picture? Answer with one word.",
                                       _red_square(), timeout)
            if sent or wrote:
                usage.record(sent, wrote, "Sounds: can the AI see pictures?")
            ok = "red" in (text or "").lower()
            why = "" if ok else "answered without seeing the picture"
        except Exception as e:  # noqa: BLE001
            low = str(e).lower()
            if any(w in low for w in ("timed out", "timeout", "connect", "429")):
                return False              # not reachable now: not an answer, asked again next time
            why = str(e)[:160]
            if "503" in low or "unavailable" in low:
                # Measured on this install: words are answered while a picture gets "503 model unavailable",
                # every time. That is a "no" too, but a short one: it is asked again in an hour.
                keep = 3600
        book[who] = {"ok": ok, "at": time.time(), "why": why, "keep": keep}
        try:
            tmp = _probe_file().with_suffix(".tmp")
            tmp.write_text(json.dumps(book), encoding="utf-8")
            tmp.replace(_probe_file())
        except OSError:
            pass
        return ok


def see(prompt: str, picture: bytes, purpose: str, timeout: float = 120.0, tally: Optional[Tally] = None) -> str:
    """What the AI says about one picture, or "" when it could not look. Never raises."""
    if not picture or not can_see():
        return ""
    for attempt in range(3):
        try:
            text, sent, wrote = ai.see(prompt, picture, timeout)
        except Exception as e:  # noqa: BLE001
            low = str(e).lower()
            if any(w in low for w in ("503", "429", "unavailable", "timed out", "timeout")):
                time.sleep(5.0 * (attempt + 1))
                continue
            return ""
        try:
            usage.record(sent, wrote, ("Sounds: " + purpose)[:60])
        except Exception:  # noqa: BLE001
            pass
        if tally is not None:
            tally.add(sent + wrote, vision=1)
        return str(text or "")
    return ""
