"""Draws a clip's shape (its tag, bar, blur, flash and chat bubbles) onto the clip that was just rendered.

`studio/formats.py` works out WHAT to draw and WHEN (the plan). This file does the drawing, in one short ffmpeg
pass over the finished 1080x1920 file, the same way `jobs._add_pictures` adds pictures. Nothing here can lose a
clip: when anything goes wrong the file is left exactly as it was and the reason comes back in `skipped`.

Shapes that join several separate moments (Callback, Compilation, Escalation, Then vs now) are not drawn here, because
one rendered clip has only one moment in it."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import config, formats, render

DRAWS = ("reveal", "waitforit", "chat")        # the shapes this file can put on a single clip


def _t(sec) -> str:
    """Seconds as the H:MM:SS.cc time an ASS file wants."""
    sec = max(0.0, float(sec))
    cs = int(round(sec * 100))
    return "%d:%02d:%02d.%02d" % (cs // 360000, cs % 360000 // 6000, cs % 6000 // 100, cs % 100)


def _rect(x, y, w, h, colour, alpha, t0, t1, grow=None) -> str:
    """One filled rectangle for a while. `grow` is the number of seconds it takes to widen from nothing to full."""
    anim = f"\\fscx1\\t(0,{int(grow * 1000)},\\fscx100)" if grow else ""
    return (f"Dialogue: 1,{_t(t0)},{_t(t1)},Box,,0,0,0,,{{\\an7\\pos({x},{y})\\bord0\\shad0\\1c{colour}"
            f"\\1a{alpha}{anim}\\p1}}m 0 0 l {w} 0 {w} {h} 0 {h}{{\\p0}}")


def _tag(chip: dict, t0, t1) -> str:
    """A tag or badge: white words on a coloured box, top left under the platform's own bar."""
    rose = chip.get("box") == formats.TAG_BOX
    colour = formats._ass_colour(formats.ROSE if rose else "000000")
    alpha = "&H1A&" if rose else "&H73&"            # the box is 90 % solid for a tag, 55 % for a badge
    size = int(chip.get("size") or 80)
    return (f"Dialogue: 3,{_t(t0)},{_t(t1)},Tag,,0,0,0,,{{\\an7\\pos({chip.get('x', formats.BADGE_X)},"
            f"{chip.get('y', formats.BADGE_Y)})\\fs{size}\\3c{colour}\\3a{alpha}\\bord16\\1c{formats._ass_colour(chip.get('color'))}}}"
            f"{formats._clean(chip.get('text'))}")


def build_ass(plan: dict, length: float) -> str:
    """The caption-file drawing of everything in the plan except the blur (which is a video filter)."""
    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: %d\nPlayResY: %d\nWrapStyle: 2\n\n[V4+ Styles]\n"
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,"
            "Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,"
            "MarginV,Encoding\n"
            "Style: Tag,Montserrat ExtraBold,80,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,&H00000000&,0,0,0,0,100,100,0,0,3,16,0,7,0,0,0,1\n"
            "Style: Box,Montserrat ExtraBold,40,&H00FFFFFF&,&H00FFFFFF&,&H00000000&,&H00000000&,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1\n"
            "\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n") % (formats.W, formats.H)
    rows = []
    for c in plan.get("chips") or []:
        kind = c.get("kind")
        t0 = c.get("t0") if c.get("t0") is not None else 0.0
        t1 = min(c.get("t1") if c.get("t1") is not None else length, length)
        if t1 <= t0:
            continue
        if kind in ("tag", "badge"):
            rows.append(_tag(c, t0, t1))
        elif kind == "bar":
            y, h = int(c.get("y") or formats.BAR_Y), int(c.get("h") or formats.BAR_H)
            rows.append(_rect(0, y, formats.W, h, "&H000000&", "&H80&", t0, t1))                 # the empty track
            rows.append(_rect(0, y, formats.W, h, formats._ass_colour(c.get("color")),
                              "&H00&", t0, t1, grow=t1 - t0))
        elif kind == "flash":
            rows.append(_rect(0, 0, formats.W, formats.H, "&HFFFFFF&", "&H40&", t0, t1))
        elif kind == "chat":
            n = int(c.get("row") or 0)
            y = int(c.get("y") or formats.CHAT_YB) - (formats.CHAT_MAX - 1 - n) * int(c.get("step") or formats.CHAT_ROW)
            rows.append(f"Dialogue: 3,{_t(t0)},{_t(t1)},Tag,,0,0,0,,{{\\an4\\pos({c.get('x', formats.CHAT_X)},{y})"
                        f"\\fs56\\3c&H000000&\\3a&H33&\\bord14\\fad(120,200)}}{formats._clean(c.get('text'))}")
    return head + "\n".join(rows) + "\n"


def finish(plan, made: Path, has_face: bool = False) -> dict:
    """Draw the plan's tag, bar, blur, flash and chat on the file `made`, in place.

    Returns {"applied": [...kinds drawn...], "skipped": "why nothing was drawn"}; never raises. `has_face` says the
    clip was rendered with a webcam picture on top (the stacked layout), which is what Reveal blurs."""
    try:
        if not isinstance(plan, dict) or not plan.get("ok") or plan.get("format") not in DRAWS:
            return {"applied": [], "skipped": ""}
        fmt = plan["format"]
        chips = [c for c in plan.get("chips") or []]
        if fmt == "reveal" and not has_face:
            return {"applied": [], "skipped": "this clip has no webcam picture to hide, so Reveal was left off"}
        if fmt == "chat" and not [c for c in chips if c.get("kind") == "chat"]:
            return {"applied": [], "skipped": "there were no chat messages for this clip"}
        made = Path(made)
        if not made.is_file():
            return {"applied": [], "skipped": "the clip file was not found"}
        length = float(plan.get("total") or 0.0) or 60.0
        work = render._workdir()
        try:
            (work / "f").mkdir()
            for f in config.FONTS_DIR.glob("*.ttf"):
                shutil.copyfile(f, work / "f" / f.name)
            (work / "deco.ass").write_text(build_ass(plan, length + 5), encoding="utf-8")
            shutil.copyfile(made, work / "in.mp4")
            blur = [c for c in chips if c.get("kind") == "blur"]
            if blur:
                b = blur[0]
                graph = (f"[0:v]split[a][b];[b]crop={formats.W}:{int(b['h'])}:0:{int(b.get('y') or 0)},boxblur=40:6,"
                         f"eq=brightness=-0.25[bl];[a][bl]overlay=0:{int(b.get('y') or 0)}:"
                         f"enable='between(t,{b['t0']},{b['t1']})'[v0];[v0]ass=deco.ass:fontsdir=f[v]")
            else:
                graph = "[0:v]ass=deco.ass:fontsdir=f[v]"
            r = subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-i", "in.mp4", "-filter_complex", graph, "-map", "[v]", "-map", "0:a?",
                 "-c:a", "copy", "-c:v", "libx264", "-crf", "17", "-preset", "fast", "-pix_fmt", "yuv420p",
                 "-movflags", "+faststart", "out.mp4"],
                cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace",
                creationflags=render.NO_WINDOW, timeout=render.RENDER_SECONDS)
            out = work / "out.mp4"
            if r.returncode != 0 or not out.is_file() or out.stat().st_size < 1000:
                return {"applied": [], "skipped": "the picture step failed: " + (r.stderr or "")[-200:].strip()}
            # Copied beside the clip and swapped in, so a full disk or a crash half-way leaves the clip as it was.
            beside = made.with_name(made.stem + ".fin.mp4")
            try:
                shutil.copyfile(out, beside)
                beside.replace(made)
            finally:
                beside.unlink(missing_ok=True)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        return {"applied": sorted({c["kind"] for c in chips}), "skipped": ""}
    except Exception as e:                        # noqa: BLE001 - a shape that cannot be drawn must never lose the clip
        return {"applied": [], "skipped": f"{type(e).__name__}: {e}"[:200]}
