"""Every piece of text is readable on the surface it is drawn on.

`--brand-ink` is one colour with one job: it is the dark ink that sits ON the orange brand colour. It reads well
there (about 7:1) and is nearly invisible anywhere else on the dark page - measured 1.03:1 against `--bg #0A0A0A`
on /app/insights and /app/videos, which is what "the menu has serious visual bugs in text" looked like.

A colour sweep cannot simply rewrite every use, because the ones on the orange button are right. So this check
pins the rule instead of the sweep: a rule may use the dark ink only when that same rule (or the surface it is
declared for) paints the brand colour behind it. Everything else must use a page ink.

The known exception is `.nav-item.on .count`: its background is a translucent `rgba(42,26,18,.14)` laid over the
orange row, so the dark ink is correct and no single colour can prove it. It is named here rather than skipped
silently, so a new exception has to be argued for.

Run: python tests/test_text_ink.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEAT = ROOT / "web" / "feat"

FAILED = []
OK = 0


def check(name, fn):
    global OK
    try:
        fn()
    except AssertionError as e:
        FAILED.append("%s   %s" % (name, e))
        print("FAIL %s   %s" % (name, e))
    else:
        OK += 1
        print("ok   %s" % name)


# Rules whose dark ink is right because the brand colour is behind it. Anything not listed has to pass the
# "same rule paints the brand" test below.
OVER_TRANSLUCENT = (
    ".nav-item.on .count",
    ".utabs .tabbtn.on .n",
    ".nav-item.on .working",
)


def index_css():
    text = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    out = []
    for block in re.findall(r"<style>(.*?)</style>", text, re.S):
        out.append(block)
    return "\n".join(out)


def feat_css():
    """The styles every feature file declares, as (file name, style text) pairs."""
    pairs = []
    for f in sorted(FEAT.glob("*.js")):
        src = f.read_text(encoding="utf-8")
        body = "\n".join(re.findall(r'PeakCut\.css\("[^"]+",\s*`(.*?)`\)', src, re.S))
        if not body:
            body = "\n".join(re.findall(r'P\.css\("[^"]+",\s*`(.*?)`\)', src, re.S))
        pairs.append((f.name, body))
    return pairs


def rules_with_dark_ink():
    """Every rule that sets `color:var(--brand-ink)`, with the selector and the whole rule text."""
    found = []
    for where, text in [(("index.html"), index_css())] + list(feat_css()):
        for block in re.findall(r"([^{}]+)\{([^{}]*)\}", text):
            selector, body = block[0].strip(), block[1]
            if "color:var(--brand-ink)" in body:
                found.append((where, selector, body))
    return found


# ---------------------------------------------------------------- the rule
PALE = ("var(--brand)", "var(--frame-text)", "var(--text)", "#fff", "#FFFFFF")


def all_rules():
    """selector -> body for every rule, so a child can be judged by the surface its parent paints."""
    rules = {}
    for _where, text in [(("index.html"), index_css())] + list(feat_css()):
        for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", text):
            for one in selector.split(","):
                rules.setdefault(one.strip(), body)
    return rules


def surface_behind(selector, rules):
    """A child inherits the surface its parent draws, so `.nav-item.on svg` is read against `.nav-item.on`."""
    parts = selector.split()
    if len(parts) < 2:
        return ""
    parent = " ".join(parts[:-1])
    return rules.get(parent, "")


def no_dark_ink_on_a_page_surface():
    """The one that would have caught the bug: dark ink needs a pale or brand surface behind it."""
    rules = all_rules()
    bad = []
    for where, selector, body in rules_with_dark_ink():
        if any(sel in selector for sel in OVER_TRANSLUCENT):
            continue
        # a rule that paints its own brand ink background uses white text, not the same colour
        if "background:var(--brand-ink)" in body:
            continue
        own = [b for b in re.findall(r"background:(var\([^)]+\)|#[0-9A-Fa-f]{3,6})", body)]
        behind = own + re.findall(r"background:(var\([^)]+\)|#[0-9A-Fa-f]{3,6})", surface_behind(selector, rules))
        # dark ink is right on the brand colour or on a pale surface, and wrong on a tint or the page
        if any(b in PALE for b in behind):
            continue
        bad.append("%s  %s   (behind it: %s)" % (where, selector[:60], behind[0] if behind else "nothing"))
    assert not bad, "dark ink is used as page text in:\n    " + "\n    ".join(bad)


def the_page_ink_is_the_default():
    """`--text` has to be pale, or nothing else in this file means anything."""
    css = index_css()
    root = re.search(r":root\{(.*?)\}", css, re.S)
    assert root, "the shell has no :root block"
    val = re.search(r"--text:(#[0-9A-Fa-f]{6})", root.group(1))
    assert val, "--text is not declared in :root"
    hexval = val.group(1).lstrip("#")
    r, g, b = (int(hexval[i:i + 2], 16) for i in (0, 2, 4))
    lum = (0.2126 * (r / 255) + 0.7152 * (g / 255) + 0.0722 * (b / 255))
    assert lum > 0.6, "--text %s is not a pale ink (relative luminance %.2f)" % (val.group(1), lum)


def the_background_is_dark():
    css = index_css()
    root = re.search(r":root\{(.*?)\}", css, re.S)
    hexval = re.search(r"--bg:(#[0-9A-Fa-f]{6})", root.group(1)).group(1).lstrip("#")
    r, g, b = (int(hexval[i:i + 2], 16) for i in (0, 2, 4))
    assert (r + g + b) / 3 < 60, "--bg %s is not a dark page" % hexval


def the_two_inks_are_far_apart():
    """If the dark ink and the page ink were close, this whole file would be arguing about nothing."""
    css = index_css()
    root = re.search(r":root\{(.*?)\}", css, re.S).group(1)

    def lum(token):
        h = re.search(token + r":(#[0-9A-Fa-f]{6})", root).group(1).lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        return 0.2126 * (r / 255) + 0.7152 * (g / 255) + 0.0722 * (b / 255)

    dark, pale = lum("--brand-ink"), lum("--text")
    ratio = (pale + 0.05) / (dark + 0.05)
    assert ratio > 8, "the two inks are only %.1f:1 apart, so mixing them up would be hard to see" % ratio


def a_chosen_control_uses_a_page_ink():
    """The measured failures: a chosen tile, pill and segment each wore the dark ink on a dark tint."""
    css = index_css()
    for sel in (r"\.tile-o\[aria-pressed=true\]", r"\.seg button\[aria-pressed=true\]"):
        m = re.search(sel + r"\{([^}]*)\}", css)
        assert m, "%s is gone; this check needs updating" % sel
        assert "color:var(--brand-ink)" not in m.group(1), \
            "%s wears the dark ink on a dark tint, which measured 1.15:1" % sel

    filt = (FEAT / "filters.js").read_text(encoding="utf-8")
    m = re.search(r'\.pcf-pill\[aria-pressed="true"\]\{([^}]*)\}', filt)
    assert m, "the chosen filter pill rule is gone"
    assert "color:var(--brand-ink)" not in m.group(1), \
        "the chosen filter pill wears the dark ink on the dark brand tint"


def no_leftover_light_hover_washes():
    """A light-theme hover colour on a dark page turns a row nearly white behind pale text."""
    css = index_css()
    leftover = [h for h in ("#EDE3DB", "#FFFBF8", "#FFF4E6", "#FFE2CC") if h in css]
    assert not leftover, "old light-theme washes are still in the shell: %s" % leftover


def the_sweep_really_reached_the_feature_files():
    """The bug lived in 22 feature files as well as the page; a page-only fix would have looked fixed."""
    hits = []
    for name, text in feat_css():
        for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", text):
            if "color:var(--brand-ink)" in body and "background:var(--brand)" not in body:
                hits.append("%s %s" % (name, selector.strip()[:40]))
    assert not hits, "feature files still draw dark ink as page text:\n    " + "\n    ".join(hits[:6])



def the_sidebar_can_show_every_row():
    """Six headings and 22 rows came to 1004px inside a 897px nav, and the scrollbar was turned off, so the last
    row was sliced in half at the bottom edge with nothing on screen to say there was more."""
    css = index_css()
    nav = re.search(r"\n\.nav\{([^}]*)\}", css)
    assert nav, "the .nav rule is gone"
    body = nav.group(1)
    assert "scrollbar-width:none" not in body, "the nav hides its scrollbar while its rows can overflow"
    assert "scrollbar-width:thin" in body, "the nav should show a thin scrollbar when the rows do not fit"
    head = re.search(r"\.nav h4\{([^}]*)\}", css)
    assert head, "the heading rule is gone"
    pad = re.search(r"padding:\s*([0-9]+)px\s+10px\s+([0-9]+)px", head.group(1))
    assert pad, "the heading padding is not the three-value form any more"
    assert int(pad.group(1)) <= 8 and int(pad.group(2)) <= 3, (
        "the headings take %spx top and %spx bottom again; six of them is what pushed the last row out"
        % (pad.group(1), pad.group(2)))
    item = re.search(r"\.nav-item\{([^}]*)\}", css)
    assert item, "the row rule is gone"
    tall = re.search(r"min-height:\s*([0-9]+)px", item.group(1))
    assert tall, "the row height is not stated any more"
    assert int(tall.group(1)) <= 30, "rows are %spx tall again" % tall.group(1)


def the_library_filters_say_what_they_do():
    """The name box was labelled "Shortest" and the length select "Longest", so the words disagreed with the
    controls - which is exactly what a person reads first."""
    page = (FEAT / "audio-page.js").read_text(encoding="utf-8")
    q = re.search(r'<label>([^<]{1,24})<input[^>]*id="alb_q"', page)
    assert q, "the name box is not found"
    assert q.group(1).strip().lower() in ("find", "search"), (
        'the name box still reads "%s"' % q.group(1).strip())
    mx = re.search(r'<label>([^<]{1,24})<select[^>]*id="alb_max"', page)
    assert mx, "the length select is not found"
    assert "long" in mx.group(1).lower(), (
        'the length select reads "%s"' % mx.group(1).strip())


def a_length_is_only_drawn_when_there_is_one():
    """The catalogue sends no length for a sound that is not on this machine, and `(Number(n) || 0).toFixed(1)`
    turned that into "0.0s" on every card - a claim that the sound is empty."""
    page = (FEAT / "audio-page.js").read_text(encoding="utf-8")
    assert "known(" in page, "the guard that tells a real length from a missing one is gone"
    assert "secs1 = (n) => (known(n)" in page, "secs1 can print a zero again"
    assert "Number(n) || 0" not in page, "a missing length is turned into a zero again"


# ---------------------------------------------------------------- run
check("dark ink is only used on the brand colour", no_dark_ink_on_a_page_surface)
check("the page ink is pale", the_page_ink_is_the_default)
check("the page background is dark", the_background_is_dark)
check("the two inks are far apart", the_two_inks_are_far_apart)
check("a chosen tile and segment use a page ink", a_chosen_control_uses_a_page_ink)
check("no light-theme hover washes are left", no_leftover_light_hover_washes)
check("the feature files were swept too", the_sweep_really_reached_the_feature_files)
check("the sidebar can show every row", the_sidebar_can_show_every_row)
check("the library filters say what they do", the_library_filters_say_what_they_do)
check("a length is only drawn when there is one", a_length_is_only_drawn_when_there_is_one)

print()
if FAILED:
    print("%d check(s) failed" % len(FAILED))
    sys.exit(1)
print("All checks passed. %d ok" % OK)
