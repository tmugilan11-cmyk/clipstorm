"""One small brand document per person, dressing every Short they make.

A brand is a set of colours, a caption look, a font, a watermark, a progress bar and a closing card. It is
edited once in Settings and each clip rendered afterwards comes out in that look without touching the clip
again. It is written to the user's own file, so two people on the same server get two different channels.

Nothing is filled in until the user saves something, so an untouched account renders exactly the clips PeakCut
renders today. A named theme can pre-fill the whole document, and a per-clip value (the style on the pick) still
wins over the saved default.

    PEAKCUT_BRAND_THEMES   extra theme names, comma separated (optional)

Colours are hex without the #. Every key starting with "_" is a note for a human and is never read."""
from __future__ import annotations

import json
import re
import threading

from . import config

# The document, with the value used when the user has never set that key. This is the whole schema: an unknown
# key is dropped on save, so the file on disk is always exactly these keys.
DEFAULTS = {
    "style": "hormozi",             # a caption look name, looked up in captions.STYLES
    "font": "Anton-Regular",        # a font stem, overriding the look's own face
    "colors": {
        "text": "FFFFFF",           # words not being said yet
        "spoken": "00E5FF",         # the word being said right now
        "outline": "000000",        # outline behind every word
        "key": "FF3B30",            # a keyword worth shouting
        "box": "FF2E93",            # the pill behind the spoken word
    },
    "hook_text": "FFFFFF",          # the hook title's colour
    "hook_box": "0B3D91",           # the slab behind the hook title
    "hook_words": "",               # a few words the hook should be built like, "" for whatever works best
    "position": "auto",             # auto | top | middle | bottom
    "watermark": "@nocodehack",     # a handle, a path to a PNG logo, or "" for none
    "watermark_color": "FFFFFF",
    "watermark_pos": "bounce",      # tl | tr | bl | br | bounce
    "watermark_opacity": 0.65,      # 0-1
    "watermark_size": 0.2,          # fraction of the 1080 width
    "progress": True,               # the bar along the bottom
    "progress_color": "00E5FF",
    "endcard": "FOLLOW FOR MORE",   # "" for no closing card
    "aspects": [],                  # extra exports, any of 1:1 and 4:5
    "lang": "",                     # es fr pt de ar hi, picks a Noto caption face
    "fillers": True,                # drop "um", "uh", "like"
    "emoji": False,                 # an emoji pops over a keyword
    "captions": True,               # burn the words into the picture
    "clip_len": 30,                 # the length a clip starts from, in seconds
    "sound": "",                    # a mood name to put under every clip, "" for none
    "denoise": True,                # light noise reduction before the loudness pass
    "blackfix": True,               # hold the last frame over a game-over black flash
    "lift": True,                   # brighten a very dark cam or game panel
    "flash": False,                 # a white flash on the punch-in
    "theme": "",                    # a name from THEMES, "" for none
    "flip": False,                  # stacked layouts put the cam below the game
}

# A theme pre-fills the document. These are the stock looks, deliberately few and deliberately plain.
THEMES = {
    "clean": {"style": "clean", "font": "Poppins-ExtraBold", "endcard": "FOLLOW FOR MORE",
              "colors": {"text": "FFFFFF", "spoken": "FFFFFF", "outline": "000000", "key": "FFFFFF", "box": "101010"},
              "progress": True, "progress_color": "FFFFFF", "watermark_pos": "br"},
    "nocodehack": {"style": "hormozi", "font": "Anton-Regular", "endcard": "FOLLOW FOR MORE",
                   "colors": {"text": "FFFFFF", "spoken": "00E5FF", "outline": "000000", "key": "FF3B30", "box": "FF2E93"},
                   "hook_text": "FFFFFF", "hook_box": "0B3D91", "progress": True, "progress_color": "00E5FF"},
    "neon": {"style": "neon", "font": "BebasNeue-Regular",
             "colors": {"text": "FFFFFF", "spoken": "39FF14", "outline": "0A0020", "key": "FF2E93", "box": "1A0033"},
             "progress": True, "progress_color": "39FF14"},
    "bold-yellow": {"style": "classic", "font": "Montserrat-ExtraBold",
                    "colors": {"text": "FFFFFF", "spoken": "FFE500", "outline": "000000", "key": "FFE500", "box": "000000"},
                    "progress": True, "progress_color": "FFE500"},
    "minimal-white": {"style": "clean", "font": "Poppins-Medium", "endcard": "",
                      "colors": {"text": "FFFFFF", "spoken": "FFFFFF", "outline": "000000", "key": "FFFFFF", "box": "000000"},
                      "progress": False, "watermark": "", "watermark_opacity": 0.5},
}

POSITIONS = {"auto", "top", "middle", "bottom"}
WM_POSITIONS = {"tl", "tr", "bl", "br", "bounce"}
LANGS = {"", "es", "fr", "pt", "de", "ar", "hi"}
ASPECTS = {"1:1", "4:5"}
HEX = re.compile(r"^[0-9A-Fa-f]{6}$")

_lock = threading.Lock()
# What was last read, re-read only when the file changes. The person's own id is part of the key: two people on
# one server can have files that happen to be written at the same nanosecond, and sharing a cache entry between
# them would dress one person's clips in the other's colours.
_cache = {"who": None, "at": None, "data": {}}


def _file(user_id: str):
    """Each person keeps their own document. The name is made safe, never taken from the client as a path."""
    who = re.sub(r"[^a-z0-9_-]+", "_", str(user_id or "").strip().lower())[:40] or "default"
    return config.DATA_DIR / ("brand_%s.json" % who)


def _hex(value, fallback: str) -> str:
    """A colour is six hex digits without the #; anything else falls back."""
    s = str(value or "").strip().lstrip("#").upper()
    return s if HEX.match(s) else fallback


def _bool(value, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    s = str(value or "").strip().lower()
    if s in {"1", "true", "yes", "on"}:
        return True
    if s in {"0", "false", "no", "off", ""}:
        return False
    return fallback


def _float(value, fallback: float, low: float, high: float) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return fallback
    return min(high, max(low, f))


def normalise(d: dict) -> dict:
    """A brand document that is safe to render with. Runs on read and on save, so disk is always clean.

    Unknown keys are dropped, wrong types are replaced with the default, colours are made upper case without
    the #, and every value is brought inside the range the renderer can actually use."""
    if not isinstance(d, dict):
        d = {}

    # A theme fills the document first; anything named after it then wins, which is what "theme < saved < pick"
    # means in practice.
    out = _deep(DEFAULTS)
    theme = str(d.get("theme") or "").strip().lower()
    if theme in THEMES:
        _merge(out, THEMES[theme])

    # The legacy single-user shape kept a few values at the top level under different names.
    if isinstance(d.get("colors"), dict) is False and isinstance(d.get("color"), str):
        d = dict(d, colors={"spoken": d.get("color")})
    if "watermark_pos" not in d and isinstance(d.get("wm_pos"), str):
        d = dict(d, watermark_pos=d["wm_pos"])
    if "style" not in d and isinstance(d.get("look"), str):
        d = dict(d, style=d["look"])

    _merge(out, d)

    out["style"] = str(out.get("style") or DEFAULTS["style"]).strip().lower()[:40]
    from . import captions
    if out["style"] in captions.POST_ONLY_STYLES:
        out["style"] = DEFAULTS["style"]
    out["font"] = str(out.get("font") or DEFAULTS["font"]).strip()[:60]
    out["theme"] = theme if theme in THEMES else ""
    out["position"] = str(out.get("position") or "auto").strip().lower()
    if out["position"] not in POSITIONS:
        out["position"] = "auto"
    out["watermark_pos"] = str(out.get("watermark_pos") or "bounce").strip().lower()
    if out["watermark_pos"] not in WM_POSITIONS:
        out["watermark_pos"] = "bounce"
    out["lang"] = str(out.get("lang") or "").strip().lower()
    if out["lang"] not in LANGS:
        out["lang"] = ""
    out["watermark"] = str(out.get("watermark") or "")[:240]
    out["endcard"] = str(out.get("endcard") or "")[:80]

    # A few words to shape the hook a clip is given. Not the hook title's colour (that is hook_text), so
    # the one setting the improvement engine may rewrite can never paint anything.
    out["hook_words"] = str(out.get("hook_words") or "")[:120]
    out["watermark_opacity"] = _float(out.get("watermark_opacity"), 0.65, 0.0, 1.0)
    out["watermark_size"] = _float(out.get("watermark_size"), 0.2, 0.05, 0.5)

    colors = out.get("colors") if isinstance(out.get("colors"), dict) else {}
    out["colors"] = {k: _hex(colors.get(k), v) for k, v in DEFAULTS["colors"].items()}
    for key in ("hook_text", "hook_box", "watermark_color", "progress_color"):
        out[key] = _hex(out.get(key), DEFAULTS[key])

    for key in ("progress", "fillers", "emoji", "denoise", "blackfix", "lift", "flash", "flip",
                "captions"):
        out[key] = _bool(out.get(key), DEFAULTS[key])

    # A clip starts from this length. Held inside the range the job form accepts, so the number here can
    # never make a job that cannot be made.
    out["clip_len"] = int(_float(out.get("clip_len"), float(DEFAULTS["clip_len"]), 5.0, 600.0))

    # The mood put under every clip. Empty means "keep the clip's own audio"; a name here is checked
    # against the sounds that really exist when it is used, not here, so a missing pack never blocks a save.
    out["sound"] = str(out.get("sound") or "").strip().lower()[:20]

    seen, aspects = set(), []
    for a in out.get("aspects") if isinstance(out.get("aspects"), list) else []:
        a = str(a or "").strip()
        if a in ASPECTS and a not in seen:
            seen.add(a)
            aspects.append(a)
    out["aspects"] = aspects[:2]

    return {k: out[k] for k in DEFAULTS}


def _deep(d: dict) -> dict:
    return {k: (_deep(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v) for k, v in d.items()}


def _merge(base: dict, extra: dict) -> None:
    """Copy the keys that are actually present, ignoring notes for humans (_help and friends)."""
    for k, v in extra.items():
        if not isinstance(k, str) or k.startswith("_"):
            continue
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        elif k in base:
            base[k] = v


def defaults() -> dict:
    """The document with nothing set, for a page that wants to show a starting point."""
    return normalise({})


def load(user_id: str = "default") -> dict:
    """This person's brand, or the neutral one if they have never saved."""
    f = _file(user_id)
    try:
        at = f.stat().st_mtime_ns
    except OSError:
        at = 0
    if _cache["who"] != user_id or _cache["at"] != at or not _cache["data"]:
        data = {}
        if at:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = {}
        _cache.update(who=user_id, at=at, data=normalise(data if isinstance(data, dict) else {}))
    return _deep(_cache["data"])


def save(user_id: str = "default", body: dict | None = None) -> dict:
    """Write this person's brand and hand back what was stored, which is what the page should show."""
    clean = normalise(body or {})
    f = _file(user_id)
    with _lock:
        try:
            config.DATA_DIR.mkdir(parents=True, exist_ok=True)
            tmp = f.with_suffix(".tmp")
            tmp.write_text(json.dumps(clean, indent=2, sort_keys=True), encoding="utf-8")
            tmp.replace(f)
        except OSError as e:
            raise ValueError("Could not save the brand: %s" % e) from e
        try:
            _cache.update(who=user_id, at=f.stat().st_mtime_ns, data=_deep(clean))
        except OSError:
            _cache.update(who=user_id, at=None, data=_deep(clean))
    return _deep(clean)


def _face(name) -> tuple:
    """The `(stem, family)` a caption builder needs for a font the person named, or () for none.

    A brand may hold either form: an older document carries a file stem like "Anton-Regular", and the picker on the
    Brand page sends the family name libass uses like "Anton". Both must reach the same face, or a saved font would
    quietly stop working when the picker changed its value."""
    raw = str(name or "").strip()
    if not raw:
        return ()
    try:
        from . import captions

        files = captions.FONT_FILES              # family -> file name
        for family, file_name in files.items():
            if raw == family:
                return family, family
            stem = str(file_name).rsplit(".", 1)[0]
            if raw == stem:
                return stem, family
        # An unknown family: hand it on unchanged. libass falls back for a missing face, and refusing here would
        # throw away a font a newer build knows about.
        return raw, raw.split("-")[0]
    except Exception:                            # noqa: BLE001 - a font must never fail a clip
        return raw, raw.split("-")[0]


def apply_style(style_tuple: tuple, brand: dict) -> tuple:
    """Lay the brand's colours and font over a caption look, returning a 13-tuple the caption builder takes.

    The look keeps its own geometry - the size, the spacing, the height, the outline width - because those come
    from the look the user picked and are what makes it read as that look. Only the face and the colours are
    the brand's, and only when the brand actually sets them."""
    if not isinstance(style_tuple, (tuple, list)) or len(style_tuple) != 13:
        return style_tuple
    if not isinstance(brand, dict):
        return tuple(style_tuple)
    b = normalise(brand)
    out = list(style_tuple)

    face = _face(b.get("font"))
    if face:
        # The face the person chose always wins, whether or not they also chose a look.
        #
        # It used to be applied only when no look was named, which meant the ordinary case - a look plus a font -
        # silently kept the look's own face and nothing said so. That is the "font controls are not reliable"
        # complaint: the picker changed, the preview changed, and the clips did not.
        out[0], out[1] = face[0], face[1]

    colors = b.get("colors") or {}
    if colors.get("text"):
        out[5] = colors["text"]
    if colors.get("spoken"):
        out[6] = colors["spoken"]
    if colors.get("outline"):
        out[7] = colors["outline"]
    if colors.get("box"):
        out[10] = colors["box"]        # the pill behind the word being said, where the look draws one
    return tuple(out)


def styles_for(brand: dict, style_names: list) -> dict:
    """What the picker on a clip should offer: the brand's own look first, then everything else."""
    b = normalise(brand or {})
    names = list(style_names or [])
    own = b.get("style") or ""
    if own in names:
        names.remove(own)
        names.insert(0, own)
    return {"default": own, "names": names}


def public(user_id: str = "default") -> dict:
    """What a settings page needs: the document, the themes it can pick from, and the safe choices."""
    return {"brand": load(user_id),
            "defaults": defaults(),
            "themes": sorted(THEMES),
            "positions": sorted(POSITIONS),
            "watermark_positions": sorted(WM_POSITIONS),
            "langs": sorted(LANGS),
            "aspects": sorted(ASPECTS)}
