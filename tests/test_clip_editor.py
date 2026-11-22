"""The clip dialog's editor rail: six tabs, one pane at a time, and a preview that fits its frame.

The rail used to be a single column 2160 px tall. Every control was on screen, which sounds generous until you
open a clip to change the caption style and find "Trim" two screens below the score. The rebuild gives the rail
one tab per subject, and that rebuild introduced two bugs a screenshot would have missed, so both are pinned:

  * The sound picker is added by `web/feat/mood.js`, which anchored itself to the "Post text" heading. With tabs
    that heading lives on the Text tab, so the sound row would have been drawn on the wrong pane - present,
    selectable, and somewhere nobody looking for a sound would go.
  * The preview video was `width:100%` with a 9/16 aspect ratio. In an 878 px column that asks for 1561 px of
    height inside a 1063 px stage, so the clip was shown cropped from its top-left corner.

Run: python tests/test_clip_editor.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
MOOD = (ROOT / "web" / "feat" / "mood.js").read_text(encoding="utf-8")
STATS = (ROOT / "web" / "feat" / "stats.js").read_text(encoding="utf-8")

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


def draw():
    """Just the drawClipDlg body, so a rule cannot be satisfied by markup somewhere else on the page."""
    start = INDEX.index("function drawClipDlg(full) {")
    end = INDEX.index("function wireEditor(", start)
    return INDEX[start:end]


def between(text, a, b):
    i = text.index(a)
    return text[i:text.index(b, i)]


# ------------------------------------------------------------------ the seven tabs
def one_tab_per_subject():
    body = draw()
    tabs = re.findall(r'data-pane="([a-z]+)"', body)
    seen = []
    for t in tabs:
        if t not in seen:
            seen.append(t)
    assert seen == ["look", "pics", "trim", "sound", "text", "more", "post"], seen


def every_tab_has_a_pane():
    body = draw()
    tabs = re.findall(r'<button[^>]+role="tab"[^>]+data-pane="([a-z]+)"', body) or re.findall(
        r'data-pane="([a-z]+)"[^>]*role="tab"', body
    )
    panes = re.findall(r'class="ed-pane[^"]*" data-pane="([a-z]+)"', body)
    assert sorted(tabs) == sorted(panes), (tabs, panes)
    assert len(tabs) == 7, len(tabs)


def one_pane_is_open_on_arrival():
    body = draw()
    openers = re.findall(r'class="ed-pane on" data-pane="([a-z]+)"', body)
    assert openers == ["look"], openers
    hidden = re.findall(r'class="ed-pane" data-pane="[a-z]+" role="tabpanel" hidden', body)
    assert len(hidden) == 6, len(hidden)


def the_tabs_actually_switch():
    start = INDEX.index("function wireEditor(")
    body = INDEX[start:INDEX.index("function mmss(", start)]
    assert 'data-pane' in body and "aria-selected" in body, "no tab wiring"
    assert ".ed-pane" in body, "the panes are never looked up"
    assert 'pn.removeAttribute("hidden")' in body or "removeAttribute('hidden')" in body, (
        "a pane is never shown, so every tab would look the same"
    )
    assert 'setAttribute("hidden", "")' in body or "setAttribute('hidden', '')" in body, (
        "the other panes are never hidden, so they would all stack"
    )


def the_rail_nav_is_a_tablist():
    body = draw()
    strip = body[body.index('class="ed-railnav"'):body.index("</div>", body.index('class="ed-railnav"'))]
    assert 'role="tablist"' in strip, "a row of buttons with no tablist role"
    assert strip.count('role="tab"') == 7, strip.count('role="tab"')


# ---------------------------------------------------------------- nothing was lost in the move
def every_sent_field_still_exists():
    """The re-make button collects `#clipdlg [data-f]`, so a field dropped in the rebuild stops being sent."""
    body = draw()
    for name in ("hook", "captions", "style", "layout", "bg", "start", "end", "title", "description"):
        assert 'data-f="%s"' % name in body, "data-f=%s is gone" % name
    assert 'data-note' in body, "the note box is gone"
    assert 'id="clip_lang"' in body, "the language picker is gone"


def the_commit_button_is_outside_the_panes():
    """It applies to every tab, so it must not be hidden by switching tabs."""
    body = draw()
    foot = body[body.index('class="ed-foot"'):body.index('</div></div>`;')]
    assert 'data-act="remake"' in foot, "a hidden re-make button would look like a broken dialog"


def the_post_actions_live_on_the_post_tab():
    body = draw()
    post = between(body, 'data-pane="post" role="tabpanel"', 'class="ed-foot"')
    for act in ("postnow", "postqueue", "copy"):
        assert 'data-act="%s"' % act in post, "%s is not on the Post tab" % act


# ---------------------------------------------------------------- the two bugs the rebuild caused
def the_sound_picker_lands_on_the_sound_tab():
    """mood.js must anchor to the Sound pane. Anchoring to the "Post text" heading puts it on Text."""
    assert 'data-pane="sound"' in MOOD, "mood.js does not know the Sound pane exists"
    mount = MOOD[MOOD.index("function mount(root)"):MOOD.index("function arm(")]
    sound_at = mount.index('data-pane="sound"')
    post_at = mount.find("postHead")
    assert post_at == -1 or sound_at < post_at, (
        "mood.js still prefers the Post text heading, so the sound row is drawn on the Text tab"
    )
    assert mount.index('data-pane="sound"') < mount.find("insertAdjacentHTML", mount.find("if (soundPane)"))


def the_numbers_box_stays_with_the_look_controls():
    # The box is re-homed between the tab rail and the panes, so it shows on every tab (the old
    # "after the first h3" spot tucked it inside the Look pane, above its heading).
    assert '<summary>YouTube numbers</summary>' in STATS, (
        "the Numbers summary is back to jargon; the rest of the app says YouTube numbers"
    )
    assert 'panel.querySelector(".ed-railnav")' in STATS, (
        "stats.js no longer anchors after the tab rail, so the box lands in one pane again"
    )


def the_preview_cannot_be_taller_than_its_frame():
    """Measured before the fix: 878 x 1561 inside an 878 x 1063 stage, so the clip was shown cropped."""
    rule = re.search(r"\.editor \.stage video[^{]*\{([^}]*)\}", INDEX)
    assert rule, "no rule for the preview video"
    body = rule.group(1)
    assert "position:absolute" in body, (
        "the video is a grid item again; its own 9/16 ratio beats height:100%, so it grows past the stage"
    )
    assert "inset:0" in body, "the video is not pinned to the stage"
    assert "object-fit:contain" in body, "the frame would be cropped instead of letterboxed"
    assert "aspect-ratio:auto" in body, "the intrinsic ratio wins over the box the stage sets"


# ---------------------------------------------------------------- nothing overflowing the rail
def the_panel_scrolls_in_the_panes_not_whole():
    rule = re.search(r"\.editor \.panel\{([^}]*)\}", INDEX)
    assert rule, "no .editor .panel rule"
    body = rule.group(1)
    assert "overflow:hidden" in body, (
        "the whole rail scrolls again, so the tab strip and the commit button slide away with the content"
    )
    assert "min-height:0" in body, "without this the middle pane refuses to shrink and pushes the footer off"
    panes = re.search(r"\.ed-panes\{([^}]*)\}", INDEX)
    assert panes and "overflow:auto" in panes.group(1), "nothing scrolls the pane contents"


def the_tab_strip_does_not_scroll_away():
    strip = re.search(r"\.ed-railnav\{([^}]*)\}", INDEX)
    assert strip, "no .ed-railnav rule"
    assert "flex:none" in strip.group(1), (
        "the strip shares the scrolling box, so the tabs disappear when a pane is long"
    )



def every_tab_fits_on_the_strip():
    """All seven names have to be readable at once.

    Measured in the browser before this was fixed: the strip was 379 px wide, its buttons wanted 455, and "Post" was
    pushed out of sight behind a horizontal scroll nobody would think to look for. Seven labels had to fit, so the
    strip wraps rather than scrolls, and its buttons are narrower than they were."""
    strip = re.search(r"\.ed-railnav\{([^}]*)\}", INDEX)
    assert strip, "no .ed-railnav rule"
    rule = strip.group(1)
    assert "flex-wrap:wrap" in rule, "a strip that cannot wrap hides the last tab behind a scroll"
    button = re.search(r"\.ed-railnav button\{([^}]*)\}", INDEX)
    assert button, "no .ed-railnav button rule"
    pad = re.search(r"padding:6px (\d+)px", button.group(1))
    assert pad, "the tab padding is not the shape this check measures"
    assert int(pad.group(1)) <= 9, (
        "each tab has %s px of side padding, which is what pushed the last one off a 380 px rail" % pad.group(1)
    )

def main():
    check("the rail has one tab per subject", one_tab_per_subject)
    check("every tab has a pane to show", every_tab_has_a_pane)
    check("the first tab is open and the rest are not", one_pane_is_open_on_arrival)
    check("the tabs really switch panes", the_tabs_actually_switch)
    check("the tab strip says it is a tablist", the_rail_nav_is_a_tablist)
    check("every field the re-make button sends is still there", every_sent_field_still_exists)
    check("re-make is outside the panes", the_commit_button_is_outside_the_panes)
    check("post actions are on the Post tab", the_post_actions_live_on_the_post_tab)
    check("the sound picker lands on the Sound tab", the_sound_picker_lands_on_the_sound_tab)
    check("the Numbers box stays with the look controls", the_numbers_box_stays_with_the_look_controls)
    check("the preview cannot be taller than its frame", the_preview_cannot_be_taller_than_its_frame)
    check("the rail scrolls inside the panes", the_panel_scrolls_in_the_panes_not_whole)
    check("the tab strip does not scroll away", the_tab_strip_does_not_scroll_away)
    check("every tab fits on the strip", every_tab_fits_on_the_strip)

    print()
    if FAILED:
        print("%d check(s) failed" % len(FAILED))
        for f in FAILED:
            print("  " + f)
        return 1
    print("All checks passed. %d ok" % OK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
