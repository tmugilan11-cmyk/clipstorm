"""Turns a time range into a vertical clip: 9:16 layout, bouncy word captions, hook title, cover."""
import re
import shutil
import subprocess
import tempfile
import threading
import traceback
from pathlib import Path
from typing import Optional

from . import clean, config, roman
from .media import NO_WINDOW, run

try:      # the extra caption looks and the brand document are optional parts of the renderer: if one of them will not
    from . import brand as brand_mod, captions      # import, every clip still renders in the looks in STYLES below
except Exception:          # noqa: BLE001
    brand_mod = captions = None  # type: ignore[assignment]

W, H = config.OUT_W, config.OUT_H

# ASS colours are &HBBGGRR. `size` is the ASS font size (line height); _Font turns it into real pixels.
# These three looks are PeakCut's own. A job asking for any other name gets the matching look from captions.py instead.
STYLES = {
    "bounce": {"label": "Bounce", "font": "Poppins ExtraBold", "size": 132, "base": "FFFFFF", "active": "00F0FF",
               "strong": "FFFFFF", "outline": 7, "pop": 112, "upper": True, "per": 3},
    "hype": {"label": "Hype", "font": "Anton", "size": 152, "base": "FFFFFF", "active": "3C3CFF",
             "strong": "00D7FF", "outline": 7, "pop": 114, "upper": True, "per": 2},
    "clean": {"label": "Clean", "font": "Poppins ExtraBold", "size": 100, "base": "FFFFFF", "active": "6BD7FF",
              "strong": "FFFFFF", "outline": 5, "pop": 106, "upper": False, "per": 4},
}
HOOK = {"font": "Poppins ExtraBold", "size": 96, "ink": "14100E", "box": "FFFFFF", "pad_x": 36, "pad_y": 22, "radius": 26,
        "max_w": 900}
FONT_FILES = {"Poppins ExtraBold": "Poppins-ExtraBold.ttf", "Anton": "Anton-Regular.ttf", "Archivo Black": "ArchivoBlack-Regular.ttf",
              # The CJK faces, so a Japanese or Chinese look is measured with the font it is drawn in. Without them
              # _Font.get would silently measure every look with Poppins and the line breaks would be wrong.
              "Noto Sans JP Black": "NotoSansJP-Black.ttf", "Noto Sans SC Black": "NotoSansSC-Black.ttf",
              "Rounded Mplus 1c Black": "MPLUSRounded1c-Black.ttf", "Noto Serif JP": "NotoSerifJP-Bold.ttf",
              "Yusei Magic": "YuseiMagic-Regular.ttf", "Montserrat ExtraBold": "Montserrat-ExtraBold.ttf",
              "Poppins": "Poppins-Bold.ttf", "Poppins Medium": "Poppins-Medium.ttf",
              "Lilita One": "LilitaOne-Regular.ttf", "Bangers": "Bangers-Regular.ttf", "Righteous": "Righteous-Regular.ttf",
              "Bowlby One": "BowlbyOne-Regular.ttf", "Bebas Neue": "BebasNeue-Regular.ttf",
              "Courier Prime": "CourierPrime-Bold.ttf"}
CAP_MAX_W = 960   # captions never run wider than this, whatever is said


class _Font:
    """Measures text exactly as the renderer will draw it, so every word can be placed by hand: the highlighted
    word can grow without pushing its neighbours, and the heading box fits its text."""
    _cache: dict = {}

    def __init__(self, name):
        import struct
        path = Path(__file__).resolve().parent / "fonts" / FONT_FILES.get(name, FONT_FILES["Poppins ExtraBold"])
        d = path.read_bytes()
        tables = {}
        for i in range(struct.unpack(">H", d[4:6])[0]):
            tag, _, off, _ = struct.unpack(">4sIII", d[12 + 16 * i: 28 + 16 * i])
            tables[tag] = off
        self.upm = struct.unpack(">H", d[tables[b"head"] + 18: tables[b"head"] + 20])[0]
        o = tables[b"OS/2"]
        self.asc, self.desc = struct.unpack(">HH", d[o + 74: o + 78])      # what the renderer sizes the font by
        self.cap = struct.unpack(">h", d[o + 88: o + 90])[0] or int(self.upm * 0.7)
        self.path = str(path)
        self._pil = {}

    @classmethod
    def get(cls, name):
        if name not in cls._cache:
            cls._cache[name] = cls(name)
        return cls._cache[name]

    def em(self, size):
        return size * self.upm / (self.asc + self.desc)

    def width(self, text, size):
        """Pixels wide at this ASS size."""
        try:
            from PIL import ImageFont
            if "f" not in self._pil:
                self._pil["f"] = ImageFont.truetype(self.path, 200)
            return self._pil["f"].getlength(text) * self.em(size) / 200
        except Exception:  # noqa: BLE001 - no measuring library: a fair estimate keeps clips rendering
            return len(text) * self.em(size) * 0.62

    def cap_shift(self, size):
        """How far below the anchor the middle of a capital letter sits when text is centred on a point."""
        return ((self.asc - self.desc) / 2 - self.cap / 2) * size / (self.asc + self.desc)


CAPTION_LEAD = 0.0  # measured: word stamps are within 0.15 s of the voice, so no shift is needed
def install_fonts():
    """Copy the bundled caption fonts next to the data, so captions look the same on every machine and server."""
    src = Path(__file__).resolve().parent / "fonts"
    for f in src.glob("*.ttf"):
        if not (config.FONTS_DIR / f.name).exists():
            shutil.copyfile(f, config.FONTS_DIR / f.name)


LAYOUTS = {"blur": "Full frame + blurred fill", "zoom": "Zoomed in + blurred fill", "crop": "Fill the screen (centre crop)",
           "gameplay": "Gameplay fills the screen, facecam in the corner",
           "stack": "Facecam on top, game below"}

#: How much of the frame the facecam takes in the stacked layout, in pixels of the 1080x1920 frame. Even,
#: because vstack refuses an odd height.
STACK_TOP_H = 940


def _ts(t):
    t = max(0.0, t)
    h, m = int(t // 3600), int(t % 3600 // 60)
    return f"{h}:{m:02d}:{t % 60:05.2f}"


def _clean(text):
    return re.sub(r"[\x00-\x1f\x7f]+", " ", re.sub(r"[{}\\]", "", str(text))).strip()


def _key(word):
    return re.sub(r"[^a-z0-9']", "", word.lower())


def _groups(words, per):
    out, cur = [], []
    for w in words:
        if cur and (len(cur) >= per or sum(len(x["w"]) for x in cur) + len(w["w"]) > 16
                    or w["s"] - cur[-1]["e"] > 0.45 or cur[-1]["w"][-1:] in ".?!"):
            out.append(cur)
            cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return out


def geometry(src_w, src_h, layout):
    """Where the video sits in the 1080x1920 frame, and where hook and captions go."""
    if src_h >= src_w and layout != "crop":
        layout = "crop"  # already vertical or square: nothing to gain from a blurred fill
    if layout == "blur":
        fg_h = min(H, int(round(W * src_h / src_w / 2)) * 2)
    elif layout == "zoom":
        fg_h = 1000
    else:
        fg_h = H
    top = (H - fg_h) // 2
    if layout == "stack":
        # The face sits above and the game below, so the words go over the join, which is the part of
        # the frame nothing important is happening in.
        return layout, fg_h, 300, STACK_TOP_H - 40
    if layout in ("crop", "gameplay"):
        return layout, fg_h, 300, 1380
    return layout, fg_h, max(230, top - 190), min(1640, top + fg_h + 180)


def _hook_events(hook, dur, y, slab: Optional[str] = None):
    """The heading: dark text in a rounded box that fits it, on one line or two balanced ones.

    `slab` recolours the box behind the words (the person's brand hook colour); without it the box stays white.
    The words themselves are drawn by the document's Hook style line, which the brand recolours in `_caption_ass`.
    """
    f, size = _Font.get(HOOK["font"]), HOOK["size"]
    words = hook.split()
    if not words:
        return []
    lines = [" ".join(words)]
    if f.width(lines[0], size) > HOOK["max_w"] and len(words) > 1:      # two lines, split where they come out most even
        cut = min(range(1, len(words)), key=lambda i: max(f.width(" ".join(words[:i]), size), f.width(" ".join(words[i:]), size)))
        lines = [" ".join(words[:cut]), " ".join(words[cut:])]
    widest = max(f.width(l, size) for l in lines)
    if widest > HOOK["max_w"]:
        size = max(40, int(size * HOOK["max_w"] / widest))
        widest = max(f.width(l, size) for l in lines)
    line_h = f.em(size) * 1.16
    bw, bh = widest + 2 * HOOK["pad_x"], line_h * len(lines) + 2 * HOOK["pad_y"]
    x0, y0, r = (W - bw) / 2, y - bh / 2, min(HOOK["radius"], bh / 2)
    x1, y1 = x0 + bw, y0 + bh
    n = lambda v: f"{v:.0f}"                                                         # noqa: E731
    box = (f"m {n(x0 + r)} {n(y0)} l {n(x1 - r)} {n(y0)} b {n(x1)} {n(y0)} {n(x1)} {n(y0)} {n(x1)} {n(y0 + r)} "
           f"l {n(x1)} {n(y1 - r)} b {n(x1)} {n(y1)} {n(x1)} {n(y1)} {n(x1 - r)} {n(y1)} "
           f"l {n(x0 + r)} {n(y1)} b {n(x0)} {n(y1)} {n(x0)} {n(y1)} {n(x0)} {n(y1 - r)} "
           f"l {n(x0)} {n(y0 + r)} b {n(x0)} {n(y0)} {n(x0)} {n(y0)} {n(x0 + r)} {n(y0)}")
    span = f"{_ts(0)},{_ts(dur)}"
    # ASS reads colours in BGR; every value here is stored RRGGBB, so it is swapped here once (white reads the
    # same either way, which is why the old hardcoded value never showed the mistake).
    box_col = slab or HOOK["box"]
    box_col = (box_col or "FFFFFF").strip().lstrip("#").upper()
    if len(box_col) != 6:
        box_col = "FFFFFF"
    box_col = box_col[4:6] + box_col[2:4] + box_col[0:2]
    ev = [f"Dialogue: 3,{span},Hook,,0,0,0,,{{\\an7\\pos(0,0)\\fad(160,0)\\c&H{box_col}&\\p1}}{box}{{\\p0}}"]
    for i, line in enumerate(lines):
        cy = y - line_h * (len(lines) - 1) / 2 + i * line_h - f.cap_shift(size)
        ev.append(f"Dialogue: 4,{span},Hook,,0,0,0,,{{\\an5\\pos({W // 2},{cy:.0f})\\fad(160,0)\\fs{size}}}{line}")
    return ev


def _caption_look(style_name) -> bool:
    """True when the name is one of captions.py's looks rather than one of PeakCut's own three in STYLES."""
    if captions is None:
        return False
    try:
        return str(style_name or "") not in STYLES and captions.has(style_name)
    except Exception:          # noqa: BLE001 - a name that cannot even be compared is simply not a caption look
        return False


def _measure_caption(family: str, text: str, size: float) -> float:
    """How wide captions.py should draw this text in this face. _Font falls back to the bundled face, so an unknown
    family measures sensibly instead of failing the clip."""
    return _Font.get(family).width(text, size)


# captions.build reads its look from captions.STYLES by name, so a brand's colours reach it by putting the adjusted
# tuple in place for the length of one build. The lock keeps two clips rendering at once from seeing each other's
# colours, and the tuple is always put back, even when the build fails.
_caption_lock = threading.Lock()


def _caption_ass(words, start, end, hook, style_name, highlight, hook_y, cap_y, brand) -> str:
    """One clip's caption file in one of captions.py's looks, wearing the person's brand when they have one."""
    name = str(style_name or "")
    look = captions.style(name)
    dressed = look
    colors = (brand or {}).get("colors") or {}
    key_col = str(colors.get("key") or "").strip().lstrip("#").upper()
    ink = str((brand or {}).get("hook_text") or "").strip().lstrip("#").upper()
    slab = str((brand or {}).get("hook_box") or "").strip().lstrip("#").upper()
    if brand:
        try:
            dressed = brand_mod.apply_style(look, brand) if brand_mod is not None else look
        except Exception:      # noqa: BLE001 - brand colours that will not apply are not worth a failed render
            dressed = look
    hook_events = _hook_events(_clean(hook), max(0.0, end - start), hook_y, slab or None)

    def build() -> str:
        return captions.build_ass(words, start, end, hook, style=name, highlight=highlight, hook_y=hook_y,
                                  cap_y=cap_y, measures=_measure_caption, hook_events=hook_events)
    if name not in captions.STYLES:
        return build()
    _hex6 = re.compile(r"[0-9A-F]{6}$")
    with _caption_lock:
        # captions.build reads its look, its keyword colour and its hook style from module globals, so the brand's
        # versions are put in place for the length of one build. The lock keeps two clips rendering at once from
        # seeing each other's colours, and every value is put back, even when the build fails.
        original = captions.STYLES[name]
        original_key, original_hook = captions.KEY, captions.HOOK_STYLE
        captions.STYLES[name] = tuple(dressed)
        if _hex6.fullmatch(key_col):
            captions.KEY = key_col                  # keywords draw in the brand's key colour, not always green
        if _hex6.fullmatch(ink):
            bgr = lambda h: h[4:6] + h[2:4] + h[0:2]   # noqa: E731 - RRGGBB to the BGR order ASS writes
            captions.HOOK_STYLE = original_hook.replace("&H0014100E", f"&H00{bgr(ink)}")
        try:
            return build()
        finally:
            captions.STYLES[name] = original
            captions.KEY, captions.HOOK_STYLE = original_key, original_hook


def _house_face(own: str, brand: Optional[dict]) -> str:
    """The face a house look should use: the brand's, when the person changed it, otherwise the look's own.

    `brand.DEFAULTS["font"]` is the value a brand that has never been edited carries, so it is the one value that
    must not count as a choice. Anything else is a font the person picked, and it must reach the clip."""
    if not isinstance(brand, dict):
        return own
    try:
        from . import brand as brand_mod

        said = str(brand.get("font") or "").strip()
        unchanged = said in ("", str(brand_mod.DEFAULTS.get("font") or "").strip())
        if unchanged:
            return own
        face = brand_mod._face(said)
        return face[1] if face else own
    except Exception:              # noqa: BLE001 - a font that cannot be resolved keeps the look's own face
        return own


def build_ass(words, start, end, hook, style_name, highlight, hook_y, cap_y, brand: Optional[dict] = None) -> str:
    """The caption file for one clip.

    "bounce", "hype" and "clean" are PeakCut's own looks and are built below, exactly as they always were. Any other
    name that captions.py knows is built by captions.py instead. `brand` is the person's brand document: it recolours
    and refonts a captions.py look, and is ignored by the three looks above so those clips never change.
    """
    if _caption_look(style_name):
        try:
            return _caption_ass(words, start, end, hook, style_name, highlight, hook_y, cap_y, brand)
        except Exception:      # noqa: BLE001 - a look that will not build falls back to bounce rather than failing
            pass
    st = dict(STYLES.get(style_name, STYLES["bounce"]))
    # The three house looks used to ignore the brand's font completely, so choosing a face on the Brand page changed
    # the preview and left every bounce/hype/clean clip on its own face. That is the "font controls are not reliable"
    # complaint. The face now applies here too, but only when the person actually changed it: a brand nobody touched
    # still holds the default, and those clips must not change.
    st["font"] = _house_face(st["font"], brand)
    words = [dict(w, s=w["s"] - CAPTION_LEAD, e=w["e"] - CAPTION_LEAD) for w in words]
    strong = {_key(h) for h in highlight if _key(h)}
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{st['font']},{st['size']},&H00{st['base']},&H00{st['base']},&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,{st['outline']},0,5,0,0,0,1
Style: Hook,{HOOK['font']},{HOOK['size']},&H00{HOOK['ink']},&H00{HOOK['ink']},&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    dur = end - start
    ev = _hook_events(_clean(hook), dur, hook_y)
    f = _Font.get(st["font"])
    inside = [dict(w, w=_clean(w["w"])) for w in words if w["s"] >= start - 0.05 and w["s"] < end]
    inside = sorted((w for w in inside if w["w"]), key=lambda w: w["s"])
    for i, w in enumerate(inside[:-1]):
        w["e"] = max(w["s"], min(w["e"], inside[i + 1]["s"]))
    groups = _groups(inside, st["per"])
    for gi, g in enumerate(groups):
        g_start = max(0.0, g[0]["s"] - start)
        g_end = min(g[-1]["e"] + 0.25, groups[gi + 1][0]["s"] if gi + 1 < len(groups) else end) - start
        if g_end - g_start < 0.02:
            continue
        texts = []
        for x in g:
            t = re.sub(r"[.,;:]+$", "", x["w"])
            texts.append(t.upper() if st["upper"] else t)
        if not all(roman.drawable(t) for t in texts):
            # A script the caption font cannot draw (Japanese, Thai, Chinese...): its words cannot be measured, so
            # they are not placed one by one. The line is drawn whole and centred, in a font the system has for it.
            line = " ".join(texts)
            fs = max(44, min(int(st["size"] * 0.7), int(1500 / max(1, len(line)) * 1.6)))
            ev.append(f"Dialogue: 1,{_ts(g_start)},{_ts(g_end)},Cap,,60,60,0,,{{\\an5\\pos({W // 2},{cap_y:.0f})\\q0\\fs{fs}}}{line}")
            continue
        size = st["size"]
        gap = f.width("n n", size) - 2 * f.width("n", size) + (2 * st["outline"] + 6) * size / st["size"]   # a space, plus room for both outlines
        total = sum(f.width(t, size) for t in texts) + gap * (len(texts) - 1)
        if total > CAP_MAX_W:                                  # a long phrase: shrink it to fit, never run off the frame
            size = max(36, int(size * CAP_MAX_W / total))
            gap = f.width("n n", size) - 2 * f.width("n", size) + (2 * st["outline"] + 6) * size / st["size"]   # a space, plus room for both outlines
            total = sum(f.width(t, size) for t in texts) + gap * (len(texts) - 1)
        cy = cap_y - f.cap_shift(size)
        x = (W - total) / 2
        p = st["pop"]
        for i, (w, t) in enumerate(zip(g, texts)):
            wd = f.width(t, size)
            p = max(104, min(st["pop"], 100 + int(2200 / max(wd, 1))))   # long words grow less, so they never touch their neighbours
            pos = f"\\an5\\pos({x + wd / 2:.0f},{cy:.0f})\\fs{size}"
            x += wd + gap
            a = max(g_start, w["s"] - start)
            b = (g[i + 1]["s"] - start) if i + 1 < len(g) else g_end
            base = st["strong"] if _key(w["w"]) in strong else st["base"]
            if a - g_start >= 0.02:                                                   # waiting to be said
                ev.append(f"Dialogue: 1,{_ts(g_start)},{_ts(a)},Cap,,0,0,0,,{{{pos}\\c&H{base}&}}{t}")
            if b - a >= 0.02:                                                         # being said: colour and a quick pop, in front
                ev.append(f"Dialogue: 2,{_ts(a)},{_ts(b)},Cap,,0,0,0,,{{{pos}\\c&H{st['active']}&\\fscx94\\fscy94"
                          f"\\t(0,90,\\fscx{p}\\fscy{p})\\t(90,200,\\fscx{p - 5}\\fscy{p - 5})}}{t}")
            if g_end - b >= 0.02:                                                     # said
                ev.append(f"Dialogue: 1,{_ts(b)},{_ts(g_end)},Cap,,0,0,0,,{{{pos}\\c&H{base}&\\fscx{p - 5}\\fscy{p - 5}"
                          f"\\t(0,90,\\fscx100\\fscy100)}}{t}")
    return head + "\n".join(ev) + "\n"


PIP_W = 380            # how wide the facecam is in the 1080-wide frame
PIP_MARGIN = 26


def _filter(layout, fg_h, facecam=None, bg="", keep=None, src_w=0, src_h=0, cam_cx=None):
    """The picture. `bg` only matters when the video does not fill the frame: "" keeps the blurred copy of the video
    behind it, "black" or "white" paints that space a flat colour instead.

    `keep` is the list of pieces that survive the cleanup cut, in seconds from the clip's start. When it is given the
    picture is re-timed to match, because the sound is cut too and a picture that still plays the removed sentences
    would be a mouth moving to words nobody hears.
    """
    # A cleanup cut re-times the picture first, before any layout work, so the layout sees a clip that is already the
    # right length. `setpts` renumbers the kept frames from zero, which is what makes the sound and the captions line
    # up afterwards.
    head = f"[0:v]fps={config.OUT_FPS}"
    tail = ""
    spans = [(float(a), float(b)) for a, b in (keep or []) if float(b) - float(a) > 0.01]
    if spans:
        test = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in spans)
        head += f",select='{test}',setpts=N/({config.OUT_FPS}*TB)"
    src = "t0" if spans else "0:v"
    if layout == "gameplay" and facecam:
        # The game fills the screen, and the webcam sits in the top corner of it, so a viewer sees
        # the play and the face at the same time.
        fx, fy, fw, fh = (int(v) for v in facecam)
        if fw > 8 and fh > 8:
            pip_h = max(2, int(round(PIP_W * fh / fw)))
            return (head + f",split=2[base][fc];"
                    f"[base]scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},setsar=1[b];"
                    f"[fc]crop={fw}:{fh}:{fx}:{fy},scale={PIP_W}:{pip_h}:flags=lanczos,setsar=1[p];"
                    f"[b][p]overlay={W - PIP_W - PIP_MARGIN}:{PIP_MARGIN}[v0];")
    if layout == "stack" and facecam and len(facecam) == 4 and src_w and src_h:
        # The streamer above, the game below: one frame holds both, exactly the shape a phone plays. The game
        # panel is cut from the part of the stream the webcam does not cover, so the face is not shown twice.
        fx, fy, fw, fh = (int(v) for v in facecam)
        if fw > 8 and fh > 8:
            top = STACK_TOP_H
            bot = H - top
            gy, gh = 0, int(src_h)
            if fy + fh <= src_h * 0.55:
                gy, gh = fy + fh, int(src_h) - (fy + fh)
            elif fy >= src_h * 0.45:
                gy, gh = 0, fy
            if gh < src_h * 0.4:          # the webcam sits in the middle: the whole frame is the game
                gy, gh = 0, int(src_h)
            gx, gw = 0, int(src_w)
            if gh == int(src_h):
                # The webcam is beside the game, not above or below it. The game panel only shows a middle
                # slice of the frame's width anyway, so that slice is slid away from the webcam: a webcam
                # half-way down the left side would otherwise leave a strip of itself at the panel's edge.
                gw = min(int(src_w), int(round(gh * W / bot / 2)) * 2)
                mid = (int(src_w) - gw) // 2
                if fx + fw <= src_w * 0.5:
                    gx = min(max(mid, fx + fw + 4), int(src_w) - gw)
                elif fx >= src_w * 0.5:
                    gx = max(min(mid, fx - 4 - gw), 0)
                else:
                    gx = mid
            if cam_cx is None:
                camcrop = (f"crop={fw}:{fh}:{fx}:{fy},"
                           f"scale={W}:{top}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{top},setsar=1[cam];")
            else:
                # The person is not always in the middle of their webcam picture. The panel shows a window of the
                # right shape (1080:940) cut from the webcam, centred on the person and kept inside the picture.
                cw, ch = fw, int(round(fw * top / W))
                if ch > fh:
                    cw, ch = int(round(fh * W / top)), fh
                cw, ch = max(2, cw - cw % 2), max(2, ch - ch % 2)
                cx = fx + min(max(float(cam_cx) * fw - cw / 2, 0), fw - cw)
                cy = fy + (fh - ch) / 2
                camcrop = (f"crop={cw}:{ch}:{int(round(cx))}:{int(round(cy))},"
                           f"scale={W}:{top}:flags=lanczos,setsar=1[cam];")
            return (head + f",split=2[cs][gs];"
                    f"[cs]" + camcrop +
                    f"[gs]crop={gw}:{gh}:{gx}:{gy},"
                    f"scale={W}:{bot}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{bot},setsar=1[game];"
                    f"[cam][game]vstack=inputs=2,setsar=1[v0];")
    if layout == "crop" or (layout in ("gameplay", "stack") and not facecam):
        return head + f",scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},setsar=1[v0];"
    flat = {"black": "black", "white": "white"}.get(str(bg or "").strip().lower(), "")
    if flat:
        # A flat colour behind the picture. The video is scaled to fit the width and laid over a still colour, which
        # is what a person means by "a black background": the frame is filled, and nothing of the video is repeated.
        return (head + f",scale={W}:{fg_h}:force_original_aspect_ratio=increase:flags=lanczos,"
                f"crop={W}:{fg_h}[fg];"
                f"color=c={flat}:s={W}x{H}:r={config.OUT_FPS}[bgn];"
                f"[bgn][fg]overlay=0:(H-h)/2:shortest=1,setsar=1[v0];")
    return (head + f",split=2[a][b];"
            f"[a]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,boxblur=6:2,"
            f"scale={W}:{H},eq=brightness=-0.14:saturation=1.15[bg];"
            f"[b]scale={W}:{fg_h}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{fg_h}[fg];"
            f"[bg][fg]overlay=0:(H-h)/2,setsar=1[v0];")


def _hook_y(layout, hook_y, facecam=None):
    """Where the heading goes. In the gameplay layout the webcam sits in the top corner, so a heading
    across the top would run under it: it goes just below the picture instead."""
    if layout == "gameplay" and facecam and len(facecam) == 4 and facecam[2] > 8:
        return PIP_MARGIN + int(round(PIP_W * facecam[3] / facecam[2])) + 32
    return hook_y


_qsv_ok = None
QSV_ARGS = ["-global_quality", "19", "-preset", "medium"]
X264_ARGS = ["-crf", "18", "-preset", "fast"]
PROFILE = ["-profile:v", "high", "-level", "4.2"]
RENDER_SECONDS = 600      # one clip's video encode; far beyond normal, so a frozen encoder is stopped, not waited on


_cx_cache: dict = {}


def _person_x(src, face):
    """Where the streamer sits inside the webcam box (0..1), worked out once per (source, box)."""
    try:
        key = (str(src), tuple(int(v) for v in face))
    except (TypeError, ValueError):
        return None
    if key not in _cx_cache:
        try:
            from . import facecam
            _cx_cache[key] = facecam.person_center(src, list(key[1]))
        except Exception:      # noqa: BLE001
            _cx_cache[key] = None
    return _cx_cache[key]


def render_clip(src: Path, out_dir: Path, name: str, clip: dict, words: list, src_w: int, src_h: int,
                brand: Optional[dict] = None) -> dict:
    """Writes <name>.mp4, <name>.jpg and <name>.ass into out_dir. Returns file names.

    `brand` is the person's brand document, or nothing. It only dresses the caption looks from captions.py; a clip in
    "bounce", "hype" or "clean" comes out exactly as it did before brands existed.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    start, end = clip["start"], clip["end"]
    layout, fg_h, hook_y, cap_y = geometry(src_w, src_h, clip.get("layout", "blur"))
    face = clip.get("facecam")
    if layout in ("gameplay", "stack") and not (face and len(face) == 4):
        layout = "crop"     # no webcam found: the game fills the screen, which is still the right shape
    hook_y = _hook_y(layout, hook_y, face)
    cam_cx = _person_x(src, face) if layout == "stack" else None
    # Swearing taken out, dead air taken out. The plan is worked out once, before the captions, because when time is
    # removed the captions have to be re-timed to the cut clip or they drift later with every cut.
    try:
        plan = clean.plan(words, start, end, clean.rules(clip))
    except Exception:      # noqa: BLE001 - a cleanup that cannot be planned must never cost someone their clip
        traceback.print_exc()
        plan = clean.plan([], start, end, clean.Rules())
    said = words if clip.get("captions", True) else []
    if plan.get("bleeped"):
        said = clean.bleep(said, clean.rules(clip).curses())
    shown_end = end
    if plan.get("cut"):
        said = clean.retime(said, start, plan["keep"])
        # The caption file is built for the length that survives, because the clip really is shorter now.
        shown_end = start + float(plan["kept_seconds"])
    ass = build_ass(said, start, shown_end, clip.get("hook", ""), clip.get("style", "bounce"),
                    clip.get("highlight_words", []), hook_y, cap_y, brand=brand)
    # The clip is made in a short work folder and moved into place afterwards. The caption step of ffmpeg cannot
    # open files whose full path is longer than 260 characters on Windows, which a data folder deep inside other
    # folders easily reaches. Inside the work folder every name is short and relative (a drive colon would also
    # break the filter syntax).
    work = _workdir()
    try:
        return _render_in(work, src, out_dir, name, start, end, layout, fg_h, ass, face=face,
                          bg=str(clip.get("bg") or ""), keep=plan.get("keep"), mute=plan.get("mute"),
                          src_w=src_w, src_h=src_h, cam_cx=cam_cx)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _short_workdir() -> Path:
    """A fresh folder with a short path that this process can actually write into.

    `tempfile.mkdtemp` is the usual answer, but on Windows some machines hand back a folder whose permissions the
    running account cannot use (a tightened access list from a parent folder, or a restricted sandbox). Clipping
    would then fail on the very first write. So each candidate is tried with a real write before it is used, and a
    folder inside PeakCut's own temporary area is the fallback.
    """
    tried = []
    for make in (lambda: Path(tempfile.mkdtemp(prefix="pk")),
                 lambda: _made(config.TMP_DIR / "render"),
                 lambda: _made(Path.cwd() / ".peakcut-tmp")):
        try:
            d = make()
        except OSError as e:
            tried.append(str(e))
            continue
        probe = d / "probe.tmp"
        try:
            probe.write_bytes(b"ok")
            probe.unlink()
            return d
        except OSError as e:
            tried.append(str(e))
            shutil.rmtree(d, ignore_errors=True)
    raise RuntimeError("No folder PeakCut can write a clip into. " + (tried[-1] if tried else ""))


def _made(parent: Path) -> Path:
    """A new numbered folder under `parent`, made with a plain mkdir so the permissions are the normal ones."""
    parent.mkdir(parents=True, exist_ok=True)
    for n in range(1, 500):
        d = parent / f"w{n}"
        try:
            d.mkdir()
            return d
        except FileExistsError:
            continue
    raise OSError("Too many temporary folders in %s" % parent)


_workdir = _short_workdir     # the name render_clip uses; kept separate so a test can stand in for it


def _audio_chain(keep=None, mute=None) -> str:
    """The pieces of the sound that survive, and the moments that are silenced, as one filter chain.

    `keep` is the cleanup plan: the sound is cut exactly where the picture was, with `aselect` choosing the matching
    samples and `asetpts` renumbering them so the two stay in step. `mute` is censoring, which is applied afterwards
    because the silences were re-timed onto the cut timeline already.
    """
    chain = "loudnorm=I=-14:TP=-1.5:LRA=11"
    spans = [(float(a), float(b)) for a, b in (keep or []) if float(b) - float(a) > 0.01]
    if spans:
        test = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in spans)
        chain = f"aselect='{test}',asetpts=N/SR/TB," + chain
    for a, b in (mute or []):
        if float(b) > float(a):
            chain += f",volume=volume=0:enable='between(t,{float(a):.3f},{float(b):.3f})'"
    return chain


def _has_audio(src) -> bool:
    """Whether the source has any sound in it. When that cannot be told, yes: the clip is made as it always was."""
    try:
        p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_type",
                            "-of", "csv=p=0", str(src)], capture_output=True, text=True, timeout=60,
                           creationflags=NO_WINDOW)
        return p.returncode != 0 or "audio" in (p.stdout or "")
    except Exception:      # noqa: BLE001
        return True


def _render_in(work: Path, src: Path, out_dir: Path, name: str, start, end, layout, fg_h, ass: str, face=None,
               bg: str = "", keep=None, mute=None, src_w: int = 0, src_h: int = 0, cam_cx=None) -> dict:
    global _qsv_ok
    (work / f"{name}.ass").write_text(ass, encoding="utf-8")
    (work / "f").mkdir()
    for f in config.FONTS_DIR.glob("*.ttf"):
        shutil.copyfile(f, work / "f" / f.name)
    fc = _filter(layout, fg_h, face, bg, keep, src_w, src_h, cam_cx) + f"[v0]ass={name}.ass:fontsdir=f[v]"
    # ffmpeg runs inside the short work folder, so the source has to be named in full or it is not found.
    src = Path(src).resolve()
    if _has_audio(src):
        quiet, sound = [], ["-map", "0:a:0", "-af", _audio_chain(keep, mute)]
    else:
        # A source with no sound at all (a screen recording, a picture-only stream piece) still makes a clip:
        # it is given a silent track as long as its picture, so everything after this finds the sound it expects.
        quiet = ["-f", "lavfi", "-t", f"{end - start:.2f}", "-i", "anullsrc=r=48000:cl=stereo"]
        sound = ["-map", "1:a:0", "-shortest"]
    base = (["ffmpeg", "-y", "-v", "error", "-ss", f"{start:.2f}", "-t", f"{end - start:.2f}", "-i", str(src)] + quiet +
            ["-filter_complex", fc, "-map", "[v]"] + sound +
            ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-pix_fmt"])
    encoders = []
    if _qsv_ok is not False:
        encoders.append(("qsv", ["nv12", "-c:v", "h264_qsv"] + QSV_ARGS + PROFILE))
    encoders.append(("x264", ["yuv420p", "-c:v", "libx264"] + X264_ARGS + PROFILE))
    err = None
    for label, enc in encoders:
        p = subprocess.run(base + enc + [f"{name}.mp4"], cwd=work, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", creationflags=NO_WINDOW, timeout=RENDER_SECONDS)
        if p.returncode == 0:
            if label == "qsv":
                _qsv_ok = True
            break
        err = p.stderr[-1200:]
        if label == "qsv":
            _qsv_ok = False
    else:
        raise RuntimeError(f"Render failed: {err}")
    cover_t = min(1.2, (end - start) / 2)
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{cover_t:.2f}", "-i", f"{name}.mp4", "-frames:v", "1",
         "-q:v", "3", f"{name}.jpg"], cwd=work)
    for ext in ("mp4", "jpg", "ass"):
        shutil.move(str(work / f"{name}.{ext}"), str(out_dir / f"{name}.{ext}"))
    return {"file": f"{name}.mp4", "cover": f"{name}.jpg", "layout": layout}
