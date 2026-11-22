"""The 32 caption looks of gta6-clipper as ASS text, so a clip can be captioned in any of them instead of PeakCut's
single bouncy look."""
from __future__ import annotations

import re
from typing import Callable, Dict, List, Optional, Sequence, Tuple

# ASS sizes and positions below are for a 1080x1920 frame, which is what PeakCut renders.
W, H = 1080, 1920
PLAYRES_Y = 1920
Y_REF = 1250          # STYLES["classic"][12]: every style's height is relative to this one
HOOK_S = 3.0          # the hook title stays this long, as in clip.py
HOOK_Y = 330          # hook centre when the caller does not say otherwise
KEY = "5CFF3D"        # keywords are green in every look

# name -> (font file, family, bold, size, caps, text, spoken, outline, outline px, shadow, pill, words per line, y)
# Ported verbatim from gta6-clipper clip.py:19-50. `bold` is the ASS Bold flag (-1 is bold), `caps` uppercases the
# caption text, `pill` is the colour of the halo behind the spoken word (None for most), `y` the anchor in the frame.
STYLES: Dict[str, Tuple[str, str, int, float, int, str, str, str, float, float, Optional[str], int, int]] = {
    "classic": ("Montserrat-ExtraBold", "Montserrat ExtraBold", -1, 84, 1, "FFFFFF", "FFE500", "000000", 7, 3, None, 3, 1250),
    "beast": ("Anton-Regular", "Anton", 0, 173, 1, "FFFFFF", "FFD400", "000000", 3.2, 1, None, 3, 1382),
    "hormozi": ("Anton-Regular", "Anton", 0, 166, 1, "FFFFFF", "F7C204", "000000", 5, 2, None, 3, 1344),
    "mozi": ("Anton-Regular", "Anton", 0, 166, 1, "FFFFFF", "FFFFFF", "000000", 2.8, 1, "16A34A", 3, 1344),
    "karaoke": ("Poppins-Bold", "Poppins", -1, 155, 0, "A3A3A3", "F7C204", "000000", 2.6, 1, None, 4, 1421),
    "pill": ("Anton-Regular", "Anton", 0, 146, 1, "FFFFFF", "FFFFFF", "000000", 2, 0, "7C3AED", 3, 1421),
    "lemon": ("Anton-Regular", "Anton", 0, 152, 1, "FFFFFF", "111111", "000000", 1.8, 0, "FACC15", 3, 1421),
    "neon": ("Poppins-Bold", "Poppins", -1, 155, 0, "FFFFFF", "22D3EE", "164E63", 3, 2, None, 4, 1421),
    "ember": ("Anton-Regular", "Anton", 0, 173, 1, "FFF7ED", "FB923C", "431407", 3.2, 1, None, 3, 1382),
    "bubble": ("Poppins-Bold", "Poppins", -1, 143, 0, "FFFFFF", "FFFFFF", "000000", 2, 0, "2563EB", 4, 1440),
    "retro": ("Anton-Regular", "Anton", 0, 166, 1, "FDE68A", "F472B6", "3B0764", 3, 2, None, 3, 1382),
    "crimson": ("Poppins-Bold", "Poppins", -1, 162, 1, "FFFFFF", "EF4444", "000000", 3, 1, None, 3, 1382),
    "minimal": ("Poppins-Medium", "Poppins Medium", 0, 129, 0, "FFFFFF", "FFFFFF", "000000", 1.6, 0, None, 5, 1440),
    "word": ("Anton-Regular", "Anton", 0, 210, 1, "FFFFFF", "FFE500", "000000", 6, 3, None, 1, 1250),
    "pop": ("LilitaOne-Regular", "Lilita One", 0, 106, 1, "FFFFFF", "FFD60A", "000000", 6, 2, None, 3, 1340),
    "typewriter": ("CourierPrime-Bold", "Courier Prime", -1, 108, 0, "F8F8F2", "4ADE80", "000000", 5, 2, None, 3, 1400),
    "slide": ("ArchivoBlack-Regular", "Archivo Black", 0, 104, 1, "FFFFFF", "FF4D6D", "000000", 6, 2, None, 3, 1360),
    "shake": ("Anton-Regular", "Anton", 0, 173, 1, "FFFFFF", "FF3B30", "000000", 5, 2, None, 3, 1382),
    "sweep": ("BowlbyOne-Regular", "Bowlby One", 0, 116, 1, "FFFFFF", "FFFFFF", "000000", 4, 1, "FF2E93", 3, 1382),
    "twotone": ("ArchivoBlack-Regular", "Archivo Black", 0, 103, 1, "FFF200", "FF3D00", "000000", 6, 2, None, 3, 1382),
    "emoji": ("LilitaOne-Regular", "Lilita One", 0, 113, 1, "FFFFFF", "FFD60A", "000000", 6, 2, None, 3, 1380),
    "lower": ("Poppins-Medium", "Poppins Medium", 0, 100, 0, "FFFFFF", "FFE500", "000000", 14, 0, None, 6, 1480),
    "duo": ("Poppins-Bold", "Poppins", -1, 123, 1, "9CA3AF", "FFFFFF", "000000", 4, 1, None, 6, 1380),
    "meme": ("Anton-Regular", "Anton", 0, 200, 1, "FFFFFF", "FFFFFF", "000000", 9, 0, None, 6, 1380),
    "glow": ("Righteous-Regular", "Righteous", 0, 124, 0, "FFFFFF", "FF4FD8", "FF00C8", 3, 0, None, 3, 1380),
    "comic": ("Bangers-Regular", "Bangers", 0, 211, 1, "FFE600", "FFFFFF", "000000", 9, 5, None, 3, 1380),
    "whisper": ("Poppins-Medium", "Poppins Medium", 0, 106, 0, "FFFFFF", "FFFFFF", "000000", 2.4, 3, None, 5, 1420),
    "punch": ("BowlbyOne-Regular", "Bowlby One", 0, 196, 1, "FFFFFF", "FFE500", "000000", 8, 4, None, 1, 1150),
    "tiktok": ("Poppins-Bold", "Poppins", -1, 113, 0, "FFFFFF", "FFFFFF", "000000", 4.5, 2, None, 4, 1380),
    "drop": ("Montserrat-ExtraBold", "Montserrat ExtraBold", -1, 107, 1, "FFFFFF", "A78BFA", "000000", 6, 2, None, 3, 1360),
    "hollow": ("BebasNeue-Regular", "Bebas Neue", 0, 184, 1, "FFFFFF", "FFE500", "000000", 5, 3, None, 3, 1380),
    "stamp": ("ArchivoBlack-Regular", "Archivo Black", 0, 103, 1, "FFFFFF", "FFFFFF", "000000", 2, 0, "E11D48", 3, 1400),

    # ---- the ten viral Instagram looks ---------------------------------
    # Researched in 2026 from dated sources (docs/research/viral-fonts/FINDINGS.md): the fonts are the three the
    # sources name most often, and every colour below is a hex a source printed. They differ from the gta6 table above
    # by pairing a face with the colour scheme the sources tie to it, not by inventing anything.
    "hormozi-pro": ("Montserrat-ExtraBold", "Montserrat ExtraBold", -1, 150, 1, "FFFFFF", "F7C204", "000000", 5,
                    2, None, 2, 1344),
    "red-alert": ("Anton-Regular", "Anton", 0, 166, 1, "FFFFFF", "FF3B30", "000000", 5, 2, None, 3, 1344),
    "butter-cozy": ("Poppins-Bold", "Poppins", -1, 122, 0, "F5D76E", "FFFFFF", "000000", 4, 1, None, 5, 1440),
    "pill-dark": ("Poppins-Bold", "Poppins", -1, 118, 0, "FFFFFF", "1A1A1A", "000000", 4, 1, "FFFFFF", 3, 1420),
    "cream-ink": ("Poppins-Medium", "Poppins Medium", 0, 116, 0, "FFF3E6", "111827", "1F1A17", 4, 1, "FFF3E6", 4,
                  1440),
    "neon-pop": ("Righteous-Regular", "Righteous", 0, 124, 1, "FF2E88", "00D2FF", "101018", 4, 1, None, 3, 1380),
    "brainrot": ("Anton-Regular", "Anton", 0, 214, 1, "FFFFFF", "02FB23", "000000", 8, 4, None, 1, 1250),
    "lowercase-hook": ("Poppins-Medium", "Poppins Medium", 0, 108, 0, "FFFFFF", "FFE066", "000000", 3, 0, None, 6,
                       1470),
    "duo-speaker": ("Poppins-Bold", "Poppins", -1, 123, 1, "FFFFFF", "F5D76E", "000000", 4, 1, None, 4, 1380),
    "title-slide": ("ArchivoBlack-Regular", "Archivo Black", 0, 118, 1, "FFFFFF", "FFFFFF", "000000", 6, 2, None, 5,
                    1420),


}

# Retired additions from a misread request: these belonged to post descriptions, not video effects.
# Keep the ids only to migrate saved choices; never advertise them as rendering styles.
POST_ONLY_STYLES = frozenset({"jp-gothic", "cn-douyin", "jp-box", "cn-karaoke", "jp-emphasis", "jp-hand", "jp-mincho"})

# How each look moves. A style that is not listed here is the plain per-word highlight.
ANIM: Dict[str, Optional[str]] = {
    "pop": "bounce", "typewriter": "type", "slide": "slide", "shake": "shake", "sweep": "sweep",
    "twotone": "twotone", "emoji": None, "lower": "box", "duo": "duo", "meme": "meme", "glow": "glow",
    "comic": "comic", "whisper": "whisper", "punch": "punch", "tiktok": "phrase", "drop": "drop",
    "hollow": "hollow", "stamp": "stamp",
    # The additional video looks move like the look they were researched from: a pop on the spoken word for the
    # high-energy ones, a plain phrase for the calm ones, a chip for the pill looks.
    "hormozi-pro": "punch", "red-alert": "punch", "butter-cozy": "box",
    "neon-pop": "glow", "brainrot": "shake", "lowercase-hook": "box", "duo-speaker": "duo", "title-slide": "slide",
}

# The name a person reads in a list. `word` is deliberately not "Word".
LABELS: Dict[str, str] = {
    "classic": "Classic", "beast": "Beast", "hormozi": "Hormozi", "mozi": "Mozi", "karaoke": "Karaoke",
    "pill": "Pill", "lemon": "Lemon", "neon": "Neon", "ember": "Ember", "bubble": "Bubble", "retro": "Retro",
    "crimson": "Crimson", "minimal": "Minimal", "word": "One word", "pop": "Pop", "typewriter": "Typewriter",
    "slide": "Slide", "shake": "Shake", "sweep": "Sweep", "twotone": "Two tone", "emoji": "Emoji",
    "lower": "Lower third", "duo": "Duo", "meme": "Meme", "glow": "Glow", "comic": "Comic", "whisper": "Whisper",
    "punch": "Punch", "tiktok": "TikTok", "drop": "Drop", "hollow": "Hollow", "stamp": "Stamp",
    # The viral Instagram looks. Named the way a person would describe them, not by the slug.
    "hormozi-pro": "Hormozi Pro", "red-alert": "Red alert", "butter-cozy": "Butter cozy", "pill-dark": "Dark pill",
    "cream-ink": "Cream ink", "neon-pop": "Neon pop", "brainrot": "Brainrot", "lowercase-hook": "Lowercase hook",
    "duo-speaker": "Two speakers", "title-slide": "Title slide",

}

# family (the ASS Fontname, which is also the key _Font.get uses) -> file in studio/fonts/.
# "Poppins" is the bold Poppins file; "Poppins Medium" is a separate family, as the name table says.
# The CJK faces are large (5-11 MB each), which is the price of a caption that can actually draw Japanese or
# Chinese: libass falls back to a box glyph when the style's own font has no glyph for the character.
FONT_FILES: Dict[str, str] = {
    "Montserrat ExtraBold": "Montserrat-ExtraBold.ttf", "Anton": "Anton-Regular.ttf",
    "Poppins": "Poppins-Bold.ttf", "Poppins Medium": "Poppins-Medium.ttf",
    "Lilita One": "LilitaOne-Regular.ttf", "Courier Prime": "CourierPrime-Bold.ttf",
    "Archivo Black": "ArchivoBlack-Regular.ttf", "Bowlby One": "BowlbyOne-Regular.ttf",
    "Righteous": "Righteous-Regular.ttf", "Bangers": "Bangers-Regular.ttf",
    "Bebas Neue": "BebasNeue-Regular.ttf",
    "Noto Sans JP Black": "NotoSansJP-Black.ttf", "Noto Sans SC Black": "NotoSansSC-Black.ttf",
    "Rounded Mplus 1c Black": "MPLUSRounded1c-Black.ttf", "Noto Serif JP": "NotoSerifJP-Bold.ttf",
    "Yusei Magic": "YuseiMagic-Regular.ttf",
}

# A rattle: the word swings left and right for about a third of a second. Defined above NOW because "shake" uses it.
SHAKE = (r"\frz-5\t(0,50,\frz5)\t(50,100,\frz-5)\t(100,150,\frz5)\t(150,200,\frz-5)"
         r"\t(200,250,\frz5)\t(250,320,\frz0)")

# Extra override tags a kind adds to the word being said.
NOW = {
    "bounce": r"\fscx72\fscy72\t(0,100,\fscx117\fscy117)\t(100,200,\fscx100\fscy100)",
    "punch": r"\fscx170\fscy170\t(0,110,\fscx100\fscy100)",
    "comic": r"\fscx70\fscy70\t(0,90,\fscx115\fscy115)\t(90,180,\fscx100\fscy100)",
    "stamp": r"\fscx165\fscy165\t(0,100,\fscx100\fscy100)",
    "hollow": r"\1a&H00&", "whisper": r"\1a&H00&",
    "shake": r"\fscx108\fscy108" + SHAKE,
    "twotone": "", "sweep": "",
    # A glow: the word arrives washed out and lights up while it is being said. `ANIM` has named a "glow" kind
    # since the neon looks were added, but nothing implemented it, so every neon look silently fell back to the
    # ordinary word pop and two looks called "glow" in the style table did nothing a person could see.
    "glow": (r"\blur6\fscx104\fscy104"
             r"\t(0,140,\blur0\fscx100\fscy100)"),
}
PUNCH_COL = ["FFFFFF", "FFE500", "22D3EE", "F472B6"]

# The two fixed styles PeakCut keeps in every document. The hook box itself is drawn by render._hook_events; the
# line exists so a document written here is complete on its own.
HOOK_STYLE = ("Style: Hook,Poppins ExtraBold,96,&H0014100E,&H0014100E,&H00FFFFFF,&H00000000,"
              "-1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1")
CTA_STYLE = ("Style: Cta,Poppins ExtraBold,96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,"
             "-1,0,0,0,100,100,0,0,3,26,0,5,70,70,0,1")

_FORMAT = ("Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
           "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
           "MarginR, MarginV, Encoding")
_EVENTS = "Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"

Measures = Callable[[str, str, float], float]      # (family, text, size) -> drawn width in px


# ---------------------------------------------------------------- small readers and formatters

def _bgr(h: str) -> str:
    """RRGGBB -> BBGGRR, which is the order ASS writes colours in."""
    h = str(h or "FFFFFF")
    return h[4:6] + h[2:4] + h[0:2]


def _ts(t: float) -> str:
    """A time as h:mm:ss.ss, the only shape ASS accepts."""
    t = max(0.0, float(t or 0.0))
    h, rest = divmod(t, 3600)
    m, s = divmod(rest, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _esc(s) -> str:
    """Caption text is user data: a `{` would start an override block and a newline would break the line."""
    return str(s).replace("{", "(").replace("}", ")").replace("\n", " ").replace("\r", " ")


def _kw(s: str) -> str:
    """The word without punctuation, upper case, as the highlight list and the keyword colour compare it."""
    return re.sub(r"\W", "", str(s or "").upper())


def has(name: str) -> bool:
    """Is this one of the 32 looks?"""
    return str(name or "") in STYLES


def get(name: str) -> tuple:
    """The 13-tuple for `name`, or the classic look for a name this version does not know (never raises)."""
    return STYLES.get(str(name or ""), STYLES["classic"])


def style(name: str) -> tuple:
    """The 13-tuple for `name`, falling back to classic. Same as get(), under the name the port plan uses."""
    return get(name)


def label(name: str) -> str:
    """The name to show a person in a list of looks."""
    n = str(name or "")
    return LABELS.get(n) or (n.replace("_", " ").title() if n else LABELS["classic"])


def style_names() -> List[str]:
    """Every look, in the table's own order (classic first)."""
    return list(STYLES)


# ---------------------------------------------------------------- text measuring

def _measure(measures: Optional[Measures], st: tuple, text: str) -> float:
    """How wide this text is drawn, in px. A caller's measurer wins; otherwise an estimate that keeps the layout sane."""
    size = float(st[3])
    if measures is not None:
        try:
            got = float(measures(st[1], text, size))
            if got > 0:
                return got
        except Exception:      # noqa: BLE001 - a font that cannot be read is a measurement problem, not a crash
            pass
    return max(1.0, len(text) * size * 0.42)


def _drawable(texts: Sequence[str]) -> bool:
    """Can the caption fonts draw these words? Hindi, Thai, CJK and the like need the whole-line fallback."""
    try:
        from . import roman
    except Exception:          # noqa: BLE001 - without roman there is no script knowledge: draw normally
        return True
    try:
        return all(roman.drawable(t) for t in texts)
    except Exception:          # noqa: BLE001
        return True


# ---------------------------------------------------------------- the ASS pieces

def _style_line(name: str, st: tuple, kind: Optional[str], box: bool = False) -> str:
    """One ASS style. The primary colour is the unspoken text, the secondary what karaoke sweeps to; two kinds hide or
    dim their fill through the primary alpha rather than a colour."""
    c1 = c2 = _bgr(st[5])
    if kind == "duo":
        c1 = _bgr(st[6])
    if kind == "twotone":
        c1 = c2 = _bgr(st[6])
    a1 = {"hollow": "FF", "whisper": "50"}.get(kind, "00")
    ang = {"comic": 3, "stamp": 3}.get(kind, 0)
    ol = _bgr(st[5]) if kind == "hollow" else _bgr(st[7])
    return (f"Style: {name},{st[1]},{st[3]},&H{a1}{c1},&H00{c2},&H00{ol},&H64000000,"
            f"{st[2]},0,0,0,100,100,0,{ang},{3 if box else 1},{st[8]},{st[9]},5,60,60,0,1")


def _groups(words: Sequence[dict], size: int = 3, gap: float = 0.6) -> List[List[dict]]:
    """Break the words into caption lines: a full line, a pause, or the end of a sentence (a sentence's last word may
    join an already full line, so a line never ends up holding one stray word)."""
    g: List[List[dict]] = []
    for w in words:
        full = (len(g[-1]) >= size and not (w.get("end") and len(g[-1]) == size)) if g else False
        if g and (full or g[-1][-1].get("end") or w["s"] - g[-1][-1]["e"] > gap):
            g.append([w])
        elif g:
            g[-1].append(w)
        else:
            g.append([w])
    return g


def _word(x: dict, now: bool, keys: set, st: tuple, kind: Optional[str] = None, idx: int = 0) -> str:
    """One caption word. The word being said gets the style's colour and its motion; a keyword is green all the time;
    anything else is bare text and inherits the style line."""
    w = _esc(x["w"].upper() if st[4] else x["w"])
    key = _kw(w) in keys
    if not (now or key):
        return w
    tag = r"\c&H" + (_bgr(KEY) if key else _bgr(PUNCH_COL[idx % 4] if kind == "punch" and now else st[6])) + "&"
    if kind == "shake" and key and not now:
        tag += SHAKE
    if now and kind in NOW:
        tag += NOW[kind] + (rf"\bord12\3c&H{_bgr(st[10])}&" if kind == "stamp" else "")
    elif now:
        tag += (r"\fscx112\fscy112" if st[:2] == STYLES["classic"][:2] and st[3] == 84
                else r"\fscx100\fscy100\t(0,70,\fscx109\fscy109)" + (rf"\bord10\3c&H{_bgr(st[10])}&" if st[10] else ""))
    return "{" + tag + "}" + w + r"{\r}"


def _plain(g: Sequence[dict], st: tuple, keys: set, top: Optional[str] = None) -> str:
    """A run of words with no highlight, only keywords in green (back to `top`'s colour afterwards when given)."""
    parts = []
    for x in g:
        w = _esc(x["w"].upper() if st[4] else x["w"])
        if _kw(w) in keys:
            parts.append(r"{\c&H" + _bgr(KEY) + "&}" + w + (r"{\c&H" + _bgr(top) + "&}" if top else r"{\r}"))
        else:
            parts.append(w)
    return " ".join(parts)


SAFE_W = 900          # the widest a caption line may be drawn: 90 px of air each side in the 1080 px frame
LOW_Y = 1430          # the lowest a caption's middle may sit (74% of the height), above where the platform buttons are
PER_LINE = {"box": 3, "phrase": 2}


def _lines(g: Sequence[dict], kind: Optional[str]) -> List[Sequence[dict]]:
    """The separate lines of text one caption group is drawn as, for measuring how wide the widest one is."""
    if kind in ("duo", "meme"):
        half = (len(g) + 1) // 2
        return [x for x in (g[:half], g[half:]) if x]
    per = PER_LINE.get(kind or "", 0)
    return [g[k:k + per] for k in range(0, len(g), per)] if per else [g]


def _fit(gs: List[List[dict]], st: tuple, kind: Optional[str], measures: Optional[Measures]) -> List[List[dict]]:
    """Split any caption group whose widest line would not fit the frame, so a look never runs off the edges. A line
    holding one word is left as it is (it is as small as it can get); the halves keep their own times."""
    sp = _measure(measures, st, " ")
    out: List[List[dict]] = []
    todo = list(reversed(gs))
    while todo:
        g = todo.pop()
        widest = max((sum(_measure(measures, st, (x["w"].upper() if st[4] else x["w"])) for x in ln)
                      + sp * (len(ln) - 1) for ln in _lines(g, kind)), default=0.0)
        if widest > SAFE_W and len(g) > 1:
            half = (len(g) + 1) // 2
            todo.append(g[half:])
            todo.append(g[:half])
        else:
            out.append(g)
    return out


# ---------------------------------------------------------------- words in and out

def _clip_words(words: Sequence[dict], start: float, end: float) -> List[dict]:
    """The words that fall inside the clip, moved to clip time (the clip starts at 0), with each end clamped to the
    next word's start and the sentence-end flag the grouper reads. Never mutates the caller's list."""
    out: List[dict] = []
    for w in words or []:
        try:
            s, e = float(w["s"]), float(w["e"])
            text = str(w.get("w") or "").strip()
        except (KeyError, TypeError, ValueError):
            continue                      # a word without times cannot be drawn: skip it, never raise
        if not text or s < start - 0.05 or s >= end:
            continue
        out.append({"w": text, "s": s - start, "e": max(s, e) - start,
                    "end": bool(re.search(r"[.?!]\s*$", text))})
    out.sort(key=lambda x: x["s"])
    for i, w in enumerate(out[:-1]):
        w["e"] = max(w["s"], min(w["e"], out[i + 1]["s"]))
    return out


def _head(st: tuple, kind: Optional[str]) -> str:
    """Everything up to and including the events Format line: two caption styles, the hook, the end card."""
    return (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {W}\n"
        f"PlayResY: {PLAYRES_Y}\n"
        "WrapStyle: 2\n"
        "ScaledBorderAndShadow: yes\n"
        "\n"
        "[V4+ Styles]\n"
        f"Format: {_FORMAT}\n"
        f"{_style_line('Cap', st, kind)}\n"
        f"{_style_line('Box', st, kind, True)}\n"
        f"{HOOK_STYLE}\n"
        f"{CTA_STYLE}\n"
        "\n"
        "[Events]\n"
        f"Format: {_EVENTS}\n"
    )


def _empty_document() -> str:
    """The smallest valid caption file: used when building one badly enough has gone wrong that nothing else is safe."""
    try:
        return _head(STYLES["classic"], None) + "\n"
    except Exception:          # noqa: BLE001
        return ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[Events]\n"
                f"Format: {_EVENTS}\n")


# ---------------------------------------------------------------- the document

def build(words: Sequence[dict], start: float, end: float, style_name: str, highlight: Sequence[str] = (),
          cap_y: int = 1380, hook_events: Optional[Sequence[str]] = None, measures: Optional[Measures] = None,
          hook: str = "", hook_y: int = HOOK_Y, layout: str = "crop") -> str:
    """A complete ASS document for one clip in one look.

    words        [{"w", "s", "e"}] already in clip time (0 = the clip's first frame); source seconds are accepted too
    start, end   the clip window, used for its length
    style_name   a key of STYLES; anything else falls back to "classic" and never raises
    highlight    words the AI called out, compared without case or punctuation
    cap_y        where the captions sit in the 1080x1920 frame, from render.geometry()
    hook_events  finished Dialogue lines for the hook, written out before the captions
    measures     text measurement; without one, widths are estimated so nothing has to be installed
    layout       "gameplay" keeps the meme look on one line (the webcam owns the top corner)
    """
    st = STYLES.get(str(style_name or ""), STYLES["classic"])
    kind = ANIM.get(str(style_name or ""))
    keys = {_kw(h) for h in (highlight or []) if str(h or "").strip()}
    dur = max(0.0, float(end) - float(start))
    ws = _clip_words(words, 0.0, dur)
    if not ws and words:
        ws = _clip_words(words, start, end)      # the caller handed source seconds instead of clip seconds
    # Each look used to add its whole distance from the classic look to the caller's height, which pushed the big
    # looks (and every look on a letterboxed clip) down into the strip the platform buttons cover. A third of the
    # distance keeps their order, and LOW_Y is the floor.
    y = min(int(cap_y) + int(round((int(st[12]) - Y_REF) * 0.3)), LOW_Y)
    stacked = str(layout or "") in ("gameplay", "stack")
    head = _head(st, kind)

    ev: List[str] = []
    if hook_events:
        ev.extend(str(x) for x in hook_events)
    elif str(hook or "").strip() and dur > 0.02:
        # The real hook is the white rounded box from render._hook_events. This is the standalone fallback, so a bare
        # string still reads over any picture.
        ev.append(f"Dialogue: 1,{_ts(0)},{_ts(min(HOOK_S, dur))},Hook,,0,0,0,,"
                  rf"{{\an5\pos(540,{int(hook_y)})\c&HFFFFFF&\bord6\3c&H000000&\fad(0,250)}}"
                  f"{_esc(str(hook).upper())}")

    def E(a: float, b: float, lay: int, tags: str, txt: str, sty: str = "Cap") -> None:
        """One Dialogue line, the shape every kind below fills in."""
        ev.append(f"Dialogue: {lay},{_ts(a)},{_ts(b)},{sty},,0,0,0,,{{{tags}}}{txt}")

    sp = _measure(measures, st, " ")
    fs = float(st[3])

    gs = _fit(_groups(ws, int(st[11])), st, kind, measures)
    for gi, g in enumerate(gs):
        # A line lasts until a moment after its last word, and never runs into the next line.
        nxt = gs[gi + 1][0]["s"] if gi + 1 < len(gs) else dur
        gend = min(g[-1]["e"] + 0.15, nxt)
        if gend <= g[0]["s"] + 0.001:
            continue                                   # nothing would be on screen: skip the line rather than draw it empty
        half = (len(g) + 1) // 2

        texts = [(x["w"].upper() if st[4] else x["w"]) for x in g]
        if not _drawable(texts):
            # A script the caption font cannot draw: place the line whole and centred instead of word by word.
            # Keep real multilingual speech readable without adding a separate foreign-language video effect.
            line = " ".join(texts)
            size = max(44, min(int(fs * 0.7), int(1500 / max(1, len(line)) * 1.6)))
            E(g[0]["s"], gend, 1, rf"\an5\pos(540,{y})\q0\fs{size}", _esc(line))
            continue

        two = len(g) > PER_LINE.get(kind or "", 99) if kind in PER_LINE else (kind == "duo" and len(g) > 1)
        gy = y - int(fs * 0.6) if two else y            # two lines: lift the pair so the bottom line stays clear

        if kind == "phrase":                           # TikTok auto-captions: one event per line, no highlight
            txt = r"\N".join(_plain(g[k:k + 2], st, keys) for k in range(0, len(g), 2))
            E(g[0]["s"], gend, 0, rf"\pos(540,{gy})\fad(70,0)", txt, "Cap")

        elif kind == "box":                            # subtitle box: the line stands, the spoken word lights up
            for i, w in enumerate(g):
                wend = g[i + 1]["s"] if i + 1 < len(g) else gend
                txt = r"\N".join(" ".join(_word(x, j == i, keys, st, None, j) for j, x in enumerate(g) if k <= j < k + 3)
                                  for k in range(0, len(g), 3))
                E(w["s"], wend, 0, rf"\pos(540,{gy})" + r"\3c&H000000&\3a&H5A&", txt, "Box")

        elif kind == "duo":                            # two lines, each word sweeping grey -> white over its own time
            cs = [max(int(round(((g[i + 1]["s"] if i + 1 < len(g) else min(w["e"] + .1, gend)) - w["s"]) * 100)), 1)
                  for i, w in enumerate(g)]
            parts = [r"{\kf" + str(c) + "}" + _esc(w["w"].upper() if st[4] else w["w"]) for w, c in zip(g, cs)]
            E(g[0]["s"], gend, 0, rf"\pos(540,{gy})",
              " ".join(parts[:half]) + (r"\N" + " ".join(parts[half:]) if g[half:] else ""))

        elif kind == "meme" and not stacked:           # first half at the top of the frame, second half at the bottom
            if g[half:]:
                E(g[0]["s"], gend, 0, r"\pos(540,520)", _plain(g[:half], st, keys))
            E(g[half]["s"] if g[half:] else g[0]["s"], gend, 0, r"\pos(540,1380)", _plain(g[half:] or g, st, keys))

        elif kind == "meme":                           # one line broken in two, at the caption height
            parts = [_plain([x], st, keys) for x in g]
            E(g[0]["s"], gend, 0, rf"\pos(540,{y})",
              r"\N".join(p for p in (" ".join(parts[:half]), " ".join(parts[half:])) if p))

        else:                                          # one event per spoken word: the line stands, the word changes
            for i, w in enumerate(g):
                wend = g[i + 1]["s"] if i + 1 < len(g) else gend
                pre = (rf"\move(540,{y + 70},540,{y},0,140)\fad(90,0)" if kind == "slide" and i == 0
                       else rf"\pos(540,{y})")
                if kind == "type":                     # typed out character by character; the rest stays invisible
                    n = len(w["w"])
                    step = max(min((wend - w["s"]) * 1000 * .6 / max(n, 1), 60), 15)
                    cur = "".join(r"{\alpha&HFF&\t(" + f"{int(k * step)},{int(k * step) + 1}" + r",\alpha&H00&)}"
                                  + _esc(c) for k, c in enumerate(w["w"].upper() if st[4] else w["w"])) + r"{\r}"
                    line = " ".join([_word(x, False, keys, st) for x in g[:i]] + [cur]
                                    + [r"{\alpha&HFF&}" + _word(x, False, keys, st) + r"{\r}" for x in g[i + 1:]])
                elif kind == "drop":                   # words fall in as they are spoken
                    cur = (r"{\alpha&HFF&\fscy150\t(0,110,\alpha&H00&\fscy100)}"
                           + _word(w, False, keys, st) + r"{\r}")
                    line = " ".join([_word(x, False, keys, st) for x in g[:i]] + [cur]
                                    + [r"{\alpha&HFF&}" + _word(x, False, keys, st) + r"{\r}" for x in g[i + 1:]])
                else:
                    line = " ".join(_word(x, j == i, keys, st, kind, j) for j, x in enumerate(g))

                if kind == "sweep":                    # a colour bar slides across behind the spoken word
                    widths = [_measure(measures, st, (x["w"].upper() if st[4] else x["w"])) for x in g]
                    tot = sum(widths) + sp * (len(g) - 1)
                    a = 540 - tot / 2 + sum(widths[:i]) + sp * i
                    b = a + widths[i]
                    pad = 22
                    E(w["s"], wend, 0,
                      rf"\pos(540,{y})\1a&HFF&\bord22\3c&H{_bgr(st[10])}&\shad0"
                      rf"\clip({a - pad:.0f},0,{a - pad:.0f},{PLAYRES_Y})"
                      rf"\t(0,140,\clip({a - pad:.0f},0,{b + pad:.0f},{PLAYRES_Y}))",
                      _plain(g, st, ()))
                if kind == "glow":                     # a soft halo in the outline colour, behind the text
                    E(w["s"], wend, 0,
                      rf"\pos(540,{y})\1a&H40&\1c&H{_bgr(st[7])}&\3c&H{_bgr(st[7])}&\bord16\blur14\shad0",
                      _plain(g, st, ()))
                if kind == "twotone":                  # top slice in the first colour over a base layer in the second
                    E(w["s"], wend, 2,
                      rf"\pos(540,{y})\1c&H{_bgr(st[5])}&\bord0\shad0"
                      rf"\clip(0,{y - int(fs)},1080,{y - int(fs * .02)})",
                      _plain(g, st, keys, st[5]))
                E(w["s"], wend, 1 if kind in ("sweep", "glow") else (0 if kind != "twotone" else 1), pre, line)

    return head + "\n".join(ev) + "\n"


def build_ass(words: Sequence[dict], start: float, end: float, hook: str, style: str = "classic",
              highlight: Sequence[str] = (), hook_y: int = HOOK_Y, cap_y: int = 1380,
              measures: Optional[Measures] = None, hook_events: Optional[Sequence[str]] = None,
              layout: str = "crop") -> str:
    """A whole caption file for one clip, from the transcript's source seconds: the look named by `style`, the hook on
    top. This is the entry point render.build_ass calls; a failure returns a valid empty document, never an exception.

    words        [{"w": str, "s": float, "e": float}] in source seconds, ordered or not
    start, end   the clip window, same seconds
    hook         the heading text (the white box itself is render's job)
    style        one of style_names(); an unknown name becomes "classic"
    highlight    words the AI called out
    hook_y       where the heading sits, from render.geometry()
    cap_y        where the captions sit, from render.geometry()
    """
    try:
        return build(_clip_words(words, start, end), start, end, style, highlight, cap_y,
                     hook_events=hook_events, measures=measures, hook=hook, hook_y=hook_y, layout=layout)
    except Exception:          # noqa: BLE001 - one bad clip must never fail a render job or a worker thread
        return _empty_document()


def emoji_hits(words: Sequence[dict], start: float, end: float) -> List[Tuple[float, str]]:
    """Emoji placed over the captions, at least 1.4 s apart: (seconds from the clip's start, glyph). Returned rather
    than drawn, because an emoji glyph needs a font the caption fonts do not carry."""
    dur = max(0.0, float(end) - float(start))
    out: List[Tuple[float, str]] = []
    last = -9.0
    for x in _clip_words(words, start, end):
        glyph = EMOJI.get(re.sub(r"\W", "", x["w"].lower()))
        if glyph and x["s"] - last >= EMOJI_GAP and HOOK_S <= x["s"] < dur - 0.4:
            out.append((x["s"], glyph))
            last = x["s"]
    return out


EMOJI_GAP = 1.4       # seconds between two emoji pops
EMOJI = {
    "fire": "\U0001F525", "hot": "\U0001F525", "burn": "\U0001F525", "money": "\U0001F4B0", "cash": "\U0001F4B0",
    "dollars": "\U0001F4B0", "rich": "\U0001F4B0", "paid": "\U0001F4B0", "crazy": "\U0001F92F", "insane": "\U0001F92F",
    "wild": "\U0001F92F", "mind": "\U0001F92F", "laugh": "\U0001F602", "funny": "\U0001F602", "lol": "\U0001F602",
    "haha": "\U0001F602", "love": "\u2764\ufe0f", "heart": "\u2764\ufe0f", "omg": "\U0001F631", "wtf": "\U0001F631",
    "scared": "\U0001F631", "dead": "\U0001F480", "die": "\U0001F480", "died": "\U0001F480", "kill": "\U0001F480",
    "win": "\U0001F3C6", "won": "\U0001F3C6", "winner": "\U0001F3C6", "champion": "\U0001F3C6", "gun": "\U0001F52B",
    "shoot": "\U0001F52B", "car": "\U0001F697", "drive": "\U0001F697", "fast": "\u26A1", "speed": "\u26A1",
    "cry": "\U0001F62D", "sad": "\U0001F62D", "look": "\U0001F440", "watch": "\U0001F440", "see": "\U0001F440",
    "boom": "\U0001F4A5", "bomb": "\U0001F4A5", "explode": "\U0001F4A5", "game": "\U0001F3AE", "gaming": "\U0001F3AE",
    "hundred": "\U0001F4AF", "ghost": "\U0001F47B", "chicken": "\U0001F357", "eat": "\U0001F357",
    "king": "\U0001F451", "stop": "\U0001F6D1", "time": "\u23F0", "secret": "\U0001F92B", "shh": "\U0001F92B",
    "kidding": "\U0001F928", "joking": "\U0001F928", "wait": "\u270B", "help": "\U0001F198", "gold": "\U0001F947",
    "boss": "\U0001F60E", "gas": "\u26FD", "bro": "\U0001F624", "no": "\U0001F6AB", "yes": "\u2705",
}
