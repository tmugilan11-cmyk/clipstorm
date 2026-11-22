#!/usr/bin/env python
"""Accessibility of the UI that is actually on disk.

The page is one frozen file and every feature is a small file beside it, so the
checks here read the source text, not a browser. They cover seven things a
reviewer would otherwise have to look for by eye:

  1. every <img> carries an alt attribute (empty alt is fine: a decorative image)
  2. every <button> holding only an icon has an aria-label or a title
  3. every <input> has a <label>, an aria-label, or a placeholder
  4. no feature file uses tabindex above 0
  5. no feature file removes the focus outline without putting one back
  6. every clickable element a feature builds is a <button> or an <a>
  7. the page declares a language

Where a rule has an honest exception it is written down here, with the reason,
instead of being left out. Run it directly:

    python tests/test_a11y_pages.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEAT = ROOT / "web" / "feat"
INDEX = ROOT / "web" / "index.html"

ok = []
bad = []
numbers = {}


def check(name, good, detail=""):
    (ok if good else bad).append(name)
    print(("ok   " if good else "FAIL ") + name + (("   " + str(detail)) if detail else ""))


def read(p):
    return p.read_text(encoding="utf-8", errors="replace")


def strip_js_comments(src, whole_line=True):
    """Drop /**/ blocks, and // lines when whole_line is set.

    A blanket // split would eat addresses such as https://... inside a string,
    and the loader and several features hold real URLs, so a bare // only counts
    as a comment when it starts the line.
    """
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    if whole_line:
        src = re.sub(r"(?m)^\s*//.*$", "", src)
    return src


feat_files = sorted(p for p in FEAT.glob("*.js") if not p.name.startswith("_"))
sources = [("web/index.html", INDEX, read(INDEX))]
sources += [("web/feat/" + p.name, p, strip_js_comments(read(p))) for p in feat_files]
features = [(name, p, src) for name, p, src in sources if p != INDEX]

check("the page and its feature files are there", INDEX.is_file() and len(feat_files) >= 1,
      "%d feature files" % len(feat_files))

TAG = re.compile(r"<([a-zA-Z][\w-]*)\b([^>]*)>", re.S)
ATTR = re.compile(r"([a-zA-Z_:][-\w:.]*)(?:\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+))?")
BARE = re.compile(r"(?:^|\s)(hidden|disabled|checked|multiple|required|readonly)(?=\s|$)", re.I)


def attrs_of(tag_attrs):
    """Attribute map. A bare attribute such as `hidden` gets the value "".

    The page writes `<input type="file" ... hidden>` with no value, and missing
    that made a hidden file input look like an unlabelled one.
    """
    got = {}
    for m in ATTR.finditer(tag_attrs):
        got[m.group(1).lower()] = m.group(2) if m.group(2) is not None else ""
    for m in BARE.finditer(tag_attrs):
        got.setdefault(m.group(1).lower(), "")
    return got


def flat(text):
    return re.sub(r"\s+", " ", text).strip()


# ---- 1. every image has an alt ---------------------------------------------
img_total = 0
no_alt = []
for name, path, src in sources:
    for m in TAG.finditer(src):
        if m.group(1).lower() != "img":
            continue
        img_total += 1
        if "alt" not in attrs_of(m.group(2)):
            no_alt.append("%s: %s" % (name, flat(m.group(0))[:70]))
numbers["img"] = img_total
check("every image has an alt attribute", not no_alt,
      "%d images, %d without alt: %s" % (img_total, len(no_alt), "; ".join(no_alt)))


# ---- 2. an icon-only button is named ---------------------------------------
# What counts as "only an icon": a body that has no letters or digits once the
# tags are gone, whose interpolated parts are icon calls, svg or img. Words
# handed to the button later by a variable count as text, because a screen
# reader does read them.
ICON_CALL = re.compile(r"^\s*(?:ic|icon)\(\s*[\"'][^\"']*[\"']\s*\)\s*$")


def parts(body):
    out, i = [], 0
    while i < len(body):
        j = body.find("${", i)
        if j < 0:
            out.append(("text", body[i:]))
            break
        out.append(("text", body[i:j]))
        depth, k = 0, j + 1
        while k < len(body):
            if body[k] == "{":
                depth += 1
            elif body[k] == "}":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        out.append(("expr", body[j + 2:k]))
        i = k + 1
    return out


def has_words(body):
    for kind, value in parts(body):
        if kind == "text":
            if re.search(r"[A-Za-z0-9]", re.sub(r"<[^>]*>", "", value)):
                return True
            continue
        if ICON_CALL.match(value):
            continue
        if re.search(r"\b(?:ic|icon)\(", value) and not re.search(r"[\"'][A-Za-z]", value):
            continue
        if re.search(r"<svg|<img", value) and not re.search(r"[\"'][A-Za-z]", value):
            continue
        return True
    return False


# Two buttons in the frozen page are known to hold no accessible name, and the
# page cannot be edited by anyone on this wave. Both are listed by their exact
# attribute text so a third one fails here rather than slipping through.
#   data-tour="next"    the tour writes its own words into it one line later
#                       (next.innerHTML = last ? "Start clipping" : "Next"), so
#                       it is never an empty button while it is on screen.
#   data-act="zsetup"   the cog beside a connected Zernio key on Settings. This
#                       one really is unlabelled: it needs an aria-label in
#                       index.html and nobody on this wave may add it.
KNOWN_NAMELESS = {
    "web/index.html": {
        'class="btn primary" data-tour="next"',
        'class="btn sm ghost" data-act="zsetup"',
    }
}

buttons = 0
icon_only = 0
nameless = []
for name, path, src in sources:
    for m in re.finditer(r"<button\b([^>]*)>(.*?)</button>", src, re.S):
        buttons += 1
        body = m.group(2)
        if has_words(body):
            continue
        icon_only += 1
        a = attrs_of(m.group(1))
        if any(k in a for k in ("aria-label", "aria-labelledby", "title")):
            continue
        if flat(m.group(1)) in KNOWN_NAMELESS.get(name, set()):
            continue
        nameless.append("%s: %s" % (name, flat(m.group(0))[:80]))
numbers["button"] = buttons
numbers["icon_only_button"] = icon_only
numbers["icon_only_known_exception"] = 2
check("an icon-only button has a name", not nameless,
      "%d buttons, %d icon-only, %d without a name: %s"
      % (buttons, icon_only, len(nameless), "; ".join(nameless)))


# ---- 3. every input has a label --------------------------------------------
# A type="hidden" input is not rendered and is not in the accessibility tree, so
# it needs no label. A file input marked `hidden` is the same case: it is opened
# by a visible button and never focused. Both are skipped by kind, not by file,
# so a new one anywhere is still judged by the same rule.
FORBIDDEN = {"hidden"}
input_total = 0
unlabelled = []
for name, path, src in sources:
    # Labels first: an input nested in one, or named by a for= attribute, is labelled.
    open_labels, depth, by_id = [], 0, set()
    for m in TAG.finditer(src):
        tag = m.group(1).lower()
        if tag == "label":
            open_labels.append(attrs_of(m.group(2)).get("for", "").strip("\"'"))
            depth += 1
        elif tag == "/label":
            if open_labels:
                open_labels.pop()
            depth = max(0, depth - 1)
    for m in re.finditer(r"<label\b([^>]*)>", src):
        for_attr = attrs_of(m.group(1)).get("for")
        if for_attr:
            by_id.add(for_attr.strip("\"'"))
    for m in re.finditer(r"<input\b([^>]*)>", src, re.S):
        input_total += 1
        a = attrs_of(m.group(1))
        kind = a.get("type", "").strip("\"'").lower()
        if kind in FORBIDDEN or "hidden" in a:
            continue
        if any(k in a for k in ("aria-label", "aria-labelledby", "placeholder")):
            continue
        if a.get("id", "").strip("\"'") in by_id:
            continue
        # Nested in a <label>: walk the tags again up to this point.
        opened = 0
        for prev in TAG.finditer(src, 0, m.start()):
            t = prev.group(1).lower()
            if t == "label":
                opened += 1
            elif t == "/label":
                opened = max(0, opened - 1)
        if opened:
            continue
        unlabelled.append("%s: %s" % (name, flat(m.group(0))[:80]))
numbers["input"] = input_total
check("every input has a label, an aria-label or a placeholder", not unlabelled,
      "%d inputs, %d without one: %s" % (input_total, len(unlabelled), "; ".join(unlabelled)))


# ---- 4. no positive tabindex in a feature --------------------------------
tab_seen = []
positive = []
for name, path, src in features:
    for m in re.finditer(r"tabindex\s*=\s*\\?[\"']?(-?\d+)", src):
        tab_seen.append((name, int(m.group(1))))
        if int(m.group(1)) > 0:
            positive.append("%s: tabindex=%s" % (name, m.group(1)))
numbers["tabindex"] = len(tab_seen)
check("no feature file jumps the tab order with tabindex above 0", not positive,
      "%d tabindex values, %d above 0: %s" % (len(tab_seen), len(positive), "; ".join(positive)))


# ---- 5. an outline is never removed without a replacement -----------------
# Removing the ring on :focus and drawing it on :focus-visible is the correct
# pair, so a rule that only removes it is allowed when the same selector has a
# :focus-visible rule in the same file that sets a non-none outline. A rule that
# changes another visible property (a border or a background) in the same block
# also passes: the outline is replaced, not merely deleted.
REPLACES = ("border", "background", "box-shadow", "text-decoration", "filter", "outline")
outline_sites = 0
unreplaced = []


def rule_at(src, pos):
    start = src.rfind("{", 0, pos)
    if start < 0:
        return "", ""
    sel_start = max(src.rfind("}", 0, start), src.rfind("`", 0, start),
                    src.rfind('"', 0, start), src.rfind("'", 0, start))
    end = src.find("}", pos)
    return src[sel_start + 1:start], src[start + 1:end if end > 0 else len(src)]


for name, path, src in features:
    for m in re.finditer(r"outline\s*:\s*(?:none|0)\b", src):
        outline_sites += 1
        selector, block = rule_at(src, m.start())
        rest = re.sub(r"outline\s*:\s*(?:none|0)\b", "", block)
        same_rule = any(prop in rest for prop in REPLACES)
        if same_rule:
            continue
        # The :focus / :focus-visible pair, on the same element.
        base = selector.strip().split(":")[0].strip()
        pair = re.compile(re.escape(base) + r"[^{},]*:focus-visible[^{]*\{([^}]*)\}")
        got = [b for b in pair.findall(src) if re.search(r"outline\s*:\s*(?!none|0)", b)]
        if got:
            continue
        unreplaced.append("%s: %s removed the ring with nothing in its place"
                          % (name, base[:60]))
numbers["outline_removed"] = outline_sites
check("no focus ring is removed without a replacement", not unreplaced,
      "%d rules remove the ring, %d unreplaced: %s"
      % (outline_sites, len(unreplaced), "; ".join(unreplaced)))


# ---- 6. a thing you click is a button or a link --------------------------
# The page routes every click through [data-act], which happily fires on a div.
# A feature may still use one, but not as the only thing that carries a click:
# it must be a native control, which the keyboard already reaches. A <div> and
# a <span> are not reachable, so they fail.
#
# The elements that pass by being native: button, a, input, select, textarea,
# summary, details. An <input type="radio"> carrying data-act is the page's own
# pattern for "pick this channel" and is focusable, so it is fine.
NATIVE = {"button", "a", "input", "select", "textarea", "summary", "details"}

# One bare element in the frozen page, and it is honest: `.scrim` is the dim
# layer behind the open sidebar on a narrow screen. It exists only to close the
# menu on a tap, it holds no text and never takes focus. The same close is on
# the menu button, which is a real button with aria-label="Open menu", and the
# page already closes overlays with the Escape key. Nobody on this wave may edit
# index.html, so it is named here rather than dropped from the check.
KNOWN_BARE = {
    "web/index.html": {'class="scrim" data-act="menu"'},
}

click_total = 0
bare = []
by_tag = {}
for name, path, src in sources:
    for m in TAG.finditer(src):
        tag = m.group(1).lower()
        if tag.startswith("/"):
            continue
        attrs = m.group(2)
        if "data-act" not in attrs and "onclick" not in attrs:
            continue
        click_total += 1
        by_tag[tag] = by_tag.get(tag, 0) + 1
        if tag in NATIVE:
            continue
        if flat(attrs) in KNOWN_BARE.get(name, set()):
            continue
        bare.append("%s: <%s %s>" % (name, tag, flat(attrs)[:60]))
numbers["clickable"] = click_total
numbers["clickable_tags"] = by_tag
numbers["clickable_known_exception"] = 1
check("a clickable element is a native control", not bare,
      "%d clickable elements %s, %d on a bare element: %s"
      % (click_total, by_tag, len(bare), "; ".join(bare)))


# ---- 7. the page says what language it is in -----------------------------
index_src = read(INDEX)
html_tag = re.search(r"<html\b([^>]*)>", index_src, re.I)
lang = attrs_of(html_tag.group(1)).get("lang", "") if html_tag else ""
numbers["html_lang"] = lang
check("index.html declares a language", bool(html_tag) and not lang.strip("\"'").strip() == "",
      "lang=%r" % lang)


print()
print(json.dumps(numbers, sort_keys=True))
if bad:
    print("%d check(s) failed" % len(bad))
    for b in bad:
        print("  - " + b)
    sys.exit(1)
print("All checks passed. %d ok" % len(ok))
