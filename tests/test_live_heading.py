"""The live previews inside the clip editor.

Two boxes were blind and were complained about in the same words: "rebuild them with live previews". Typing a heading
and pressing "Save and re-make clip" meant waiting for a full render to find out the words did not fit, and typing a
description meant not seeing the post until it went out.

This checks the four things that make the fix real rather than decorative, plus the two failures that were actually
hit while building it:

* the heading route builds its caption file on its OWN clock and seeks the input, so the frame really is the second
  the captions were drawn for - an unscoped `trim` (or a lavfi `-ss`) hands back a frame with different timestamps and
  the heading lands on a different second entirely;
* the page's paint hook is handed `#clipdlg` itself, not a parent to search inside, and getting that wrong fails
  silently - the hook runs, finds nothing, and returns;
* a heading drawn from words near the shown second only, so a clip whose words are all far away still gets a frame;
* the post preview reads the hashtags from the page's own job list instead of inventing them.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROUTE = (ROOT / "studio" / "api_heading.py").read_text(encoding="utf-8")
PAGE = (ROOT / "web" / "feat" / "live-heading.js").read_text(encoding="utf-8")
SERVER = (ROOT / "studio" / "server.py").read_text(encoding="utf-8")
INDEX = (ROOT / "web" / "index.html").read_text(encoding="utf-8")

ok = 0
bad = 0


def check(name, cond, detail=""):
    global ok, bad
    if cond:
        ok += 1
        print("ok   " + name)
    else:
        bad += 1
        print("FAIL " + name + ("   " + str(detail) if detail else ""))


def body(text, start, end):
    i = text.index(start)
    j = text.index(end, i)
    return text[i:j]


# ---- the route says what it is for

check("the heading route is mounted",
      "api_heading" in SERVER and "app.include_router(api_heading.router)" in SERVER)

check("it is read-only",
      '@router.get(' in ROUTE and "@router.post(" not in ROUTE and "@router.put(" not in ROUTE)

check("it answers about one clip",
      "/api/jobs/{jid}/clips/{cid}/preview/heading" in ROUTE)

check("the heading comes from the query, not from the job",
      'hook: str = Query("", max_length=120)' in ROUTE)

# ---- the frame is the second the captions were drawn for

fit = body(ROUTE, "def _draw(", "def render_paths")
check("the input is seeked before it is read, so timestamps start at zero",
      '"-ss", f"{seek:.3f}"' in fit, "an unseeked trim leaves the source's own timestamps in place")
check("the caption file's own second is where the trim lands",
      "trim=start={_SHOWN_AT:.3f}" in fit)
check("the seek is the wanted second minus the caption clock",
      "seek = max(0.0, (when - offset) - _SHOWN_AT)" in fit)
check("the frame is brought to the size a finished clip is",
      "force_original_aspect_ratio=increase" in fit and "crop={render.W}:{render.H}" in fit)
check("the clip's own words are used, then the job's",
      'clip.get("fixed_words") or job.get("words")' in ROUTE)
check("a frame with no words near it still shows the heading",
      "if e < 0.0 or s > _SHOWN_AT + _TAIL:" in ROUTE and "continue" in ROUTE)
check("the clip's own look and brand are used, not a default",
      'clip.get("style")' in ROUTE and 'brand.load(job.get("user")' in ROUTE)
check("someone else's video is not found",
      'if job.get("user") != ctx.uid():' in ROUTE)
check("the frame is cached, so typing does not redraw for the same words",
      "_CACHE" in ROUTE and "_TTL" in ROUTE)

# ---- the page: the hook is handed the dialog itself

plug = body(PAGE, 'P.add("live-heading"', "})();")
check("it registers exactly one plug-in, named after its file",
      PAGE.count("P.add(") == 1 and 'P.add("live-heading"' in PAGE)
check("the paint hook accepts the dialog element itself",
      'root.id === "clipdlg"' in plug,
      "the hook is given #clipdlg, so searching inside it for #clipdlg finds nothing and returns silently")
check("it still works when it is handed something else",
      'root.querySelector("#clipdlg")' in plug)
check("typing waits for a pause rather than firing per key",
      "WAIT = 700" in PAGE and "window.setTimeout(go, WAIT)" in PAGE)
check("the same words do not redraw the same picture",
      "if (src === shown) return;" in PAGE)
check("an old picture stays on screen while a new one comes",
      "lh-wait" in PAGE and "remove(\"lh-wait\")" in PAGE)
check("a failure says so instead of showing a broken picture",
      "could not be drawn" in PAGE)
check("a hidden Look tab spends nothing",
      'if (look && !look.hasAttribute("hidden")) want(root);' in PAGE)
check("the post preview reads the real hashtags",
      "jobOf(" in PAGE and "hashtags" in PAGE)
check("the post preview joins the parts the way posting does",
      'parts.join("\\n\\n")' in PAGE)
check("both boxes sit under the field they belong to",
      'closest("label").insertAdjacentElement("afterend", host)' in PAGE)

# ---- the page has the fields these hooks name

check("the page has a Big text field", 'data-f="hook"' in INDEX)
check("the page has a title and a description", 'data-f="title"' in INDEX and 'data-f="description"' in INDEX)
check("the Look tab and the Text tab exist", 'data-pane="look"' in INDEX and 'data-pane="text"' in INDEX)

# ---- the feature-file contract still holds for the file itself

# This file writes its own two panels once, with fixed markup, and puts every value in through `textContent`, so there
# is nothing to escape. The check that matters is that nothing interpolated ever reaches an `innerHTML` assignment:
# every right-hand side is reduced to just its string literals, and anything left over means a value is being written
# into markup.
def leftovers(text):
    """The parts of an `innerHTML = ...` right-hand side that are not plain string literals.

    Written as a small scanner rather than a regular expression: quoted JavaScript with escaped quotes inside it is
    exactly the case a one-line pattern gets wrong, and a wrong pattern here would pass anything.
    """
    out = []
    for m in re.finditer(r"innerHTML\s*=\s*(.+?);", text, re.S):
        rest = m.group(1)
        keep = []
        i = 0
        while i < len(rest):
            c = rest[i]
            if c in "'\"":
                quote = c
                i += 1
                while i < len(rest):
                    if rest[i] == "\\":
                        i += 2
                        continue
                    if rest[i] == quote:
                        i += 1
                        break
                    i += 1
                continue
            if c == "+":
                i += 1
                continue
            keep.append(c)
            i += 1
        got = "".join(keep).strip()
        if got:
            out.append(got)
    return out


check("no value is ever written into markup", not leftovers(PAGE), leftovers(PAGE))
check("the values go in through textContent",
      "textContent = " in PAGE or "textContent=" in PAGE)
check("the file carries no dead escape helper", "const esc = " not in PAGE)

print()
if bad:
    print("%d check(s) failed" % bad)
    raise SystemExit(1)
print("All checks passed. %d ok" % ok)
