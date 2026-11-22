"""The wide audio page: its clip picker, the route it asks, and the AI's timeout.

Three things on this page were wrong in ways a person sees but a test never noticed, so each one gets a
check here:

  * "Edit audio" closed the clip dialog and sent the person to the newest clip, because the handover was
    written on the dialog's own object and the page reads the app's shared state. The wrong clip opening is
    exactly the bug this file was written after.
  * A video handed to PeakCut twice produced picker rows that read the same, so nothing said which one you
    were editing.
  * The AI placement answered "PeakCut couldn't reach Logfare" for real answers, because the route waited
    90 s where the measured answer on this install was 48 s, 85 s and then 121 s.

None of these are visible in a screenshot of an empty page, which is why they are pinned here.

Run: python tests/test_audio_page.py
"""
import os
import re
import sys
from pathlib import Path

FAILED = []
OK = 0


def check(name, fn):
    global OK
    try:
        fn()
    except AssertionError as e:
        FAILED.append((name, str(e) or "failed"))
        print(f"  FAIL {name}\n       {e}")
    except Exception as e:  # noqa: BLE001 - a crash is a failure too
        FAILED.append((name, f"{type(e).__name__}: {e}"))
        print(f"  FAIL {name}\n       {type(e).__name__}: {e}")
    else:
        OK += 1


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tests" / "audpage-data"
DATA.mkdir(parents=True, exist_ok=True)
os.environ["PEAKCUT_DATA"] = str(DATA)

# The audio work is two pages now: a LIBRARY that lists sounds to browse, and an EDITOR that puts one on a clip.
# Everything this file checks about a timeline, a drag or a clip handover lives in the editor, so that is the file
# read for those checks. The library is read too, because the split itself is worth pinning: neither page may grow
# the other's job back.
LIBRARY = (ROOT / "web" / "feat" / "audio-page.js").read_text(encoding="utf-8")
PAGE = (ROOT / "web" / "feat" / "audio-edit.js").read_text(encoding="utf-8")
INDEX = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
ROUTE = (ROOT / "studio" / "api_memesound.py").read_text(encoding="utf-8")


def test_edit_audio_hands_over_the_clip():
    """The button must name the clip, and the page must prefer that name over the newest clip."""
    assert 'D.audioFrom = {jid: D.jid, cid: D.cid}' in INDEX or "S.audioFrom = {jid: D.jid, cid: D.cid}" in INDEX, \
        "the Edit audio button does not record which clip it came from"
    # The page reads the app's shared state, not the dialog's own object: the dialog is closed by then.
    assert "audioFrom" in PAGE, "the audio page never reads the handover"
    assert "stateOf().audioFrom" in PAGE or "state().audioFrom" in PAGE, \
        "the audio page reads the handover from somewhere other than the app state"
    # and it must actually be able to pick a row by it
    assert re.search(r"audioFrom[\s\S]{0,400}?findIndex", PAGE), \
        "the handover is read but never used to choose the clip"


def test_duplicate_rows_all_carry_a_tail():
    """Two copies of one video must not produce two identical rows."""
    # The picker moved to the editor page with the rest of the timeline work, and the function that follows it is
    # `pageHtml`, not the old `readClipPicker`.
    seg = PAGE[PAGE.index("function allClips()"):PAGE.index("function pageHtml()")]
    assert "same.get(row.label) > 1" in seg, "a duplicate group is not detected before the labels are built"
    # the tail has to be added to EVERY row of the group, which is only true when the count map is built first
    order = seg.index("same.set(") < seg.index("if (same.get(row.label) > 1)")
    assert order, "the count is built while the labels are rewritten, so the first twin keeps no tail"
    assert "seen.get(row.label) || 0) + 1" not in seg, \
        "the old one-at-a-time counter is back: the first row of a duplicate pair would have no tail"


def test_the_ai_ask_has_the_measured_timeout():
    """The route waits as long as this install measurably needs, and tries again once."""
    # `ai.ask` is mentioned in a comment explaining the bug it used to be, so look for a CALL not the word:
    assert not re.search(r"ai\.ask\(", ROUTE), "ai.ask does not exist; the route must call ai.call"
    seg = ROUTE[ROUTE.index("def ask(prompt: str) -> str:"):]
    seg = seg[:seg.index("def work()")]
    assert "ai.call(model, prompt, None," in seg, "the ask must not pass a schema: it made this model 4x slower"
    wait = float(re.search(r"ai\.call\(model, prompt, None, ([\d.]+)\)", seg).group(1))
    assert wait >= 150.0, f"the wait is {wait}s and a real answer measured 121s, so slow answers become errors"
    assert "* 2" in seg, "a dropped answer is not retried; this service drops its slowest answers"


def test_the_route_names_the_real_jobs_lookup():
    """`jobs.find` does not exist; the timeline answered 500 on its first load because of it."""
    assert "jobs.find" not in ROUTE, "the route is back to jobs.find, which does not exist"
    assert "jobs.get(" in ROUTE, "the route no longer looks a job up at all"


def test_the_page_asks_only_routes_that_exist():
    """Every address the page fetches has to be a real route, or the button fails in the browser."""
    routes = (ROOT / "studio" / "api_memesound.py").read_text(encoding="utf-8")
    asked = set(re.findall(r'"(/api/[^"?]+)', PAGE))
    missing = []
    for path in sorted(asked):
        tail = path.replace("/api", "", 1)
        # routes are declared with {jid}/{cid} placeholders, so compare on the fixed part
        head = tail.split("/{jid}")[0].split("/{cid}")[0]
        if head and head not in routes:
            missing.append(path)
    assert not missing, f"the page asks {missing} and the route file has no such address"


def test_the_track_is_dark_and_the_chips_are_not_a_table():
    """The brief asked for a wide dark timeline; a white or narrow one is a different page."""
    assert "--track" in PAGE or "#17130F" in PAGE, "the track is not dark"
    assert "pointerdown" in PAGE and "pointermove" in PAGE, "chips cannot be dragged"
    assert "function drag" in PAGE or "onDown" in PAGE or "hold" in PAGE, "no drag state is kept"
    # wide: picture, a track that takes the middle, and the sounds column on the right
    grid = re.search(r"grid-template-columns:([^;]+);", PAGE)
    assert grid, "the editor has no column layout"
    assert grid.group(1).count("px") >= 3 or grid.group(1).count("fr") >= 1, \
        f"the editor is not three zones wide: {grid.group(1)}"


def test_the_two_pages_keep_their_own_jobs():
    """The library browses and the editor places. A page that grew the other's job back is the bug."""
    assert "pcaud_lane" not in LIBRARY and "aed-lane" not in LIBRARY, "the library grew a timeline again"
    for gone in ("sounds/suggest", "sounds/hear"):
        assert gone not in LIBRARY, f"the library is placing sounds ({gone}); that is the editor's job"
    assert "memesounds/search" in LIBRARY or "memesounds/for" in LIBRARY, "the library does not search the catalogue"
    assert "memesounds/library" in PAGE or "sounds" in PAGE, "the editor cannot see the kept sounds"


check("Edit audio opens the clip it came from", test_edit_audio_hands_over_the_clip)
check("every duplicate row says which one it is", test_duplicate_rows_all_carry_a_tail)
check("the AI ask waits as long as a real answer takes", test_the_ai_ask_has_the_measured_timeout)
check("the route uses the real jobs lookup", test_the_route_names_the_real_jobs_lookup)
check("the page asks only addresses that exist", test_the_page_asks_only_routes_that_exist)
check("the track is wide, dark and draggable", test_the_track_is_dark_and_the_chips_are_not_a_table)
check("the library browses and the editor places", test_the_two_pages_keep_their_own_jobs)


def test_the_track_uses_the_width_it_was_given():
    """Measured on /app/audio-edit: the middle column was 926x762 and its contents stopped at 319 px.

    Two thirds of the widest column on the page was empty black while the right column's cards were squeezed into
    360 px and scrolled. The track is the reason the page exists, so it has to be a real height - but not every
    pixel either: stretching the lane to 621 px turned three sound chips into 621 px tall brown blocks. The
    numbers below are the measured, readable answer.
    """
    lane = re.search(r"\.aed-lane\{([^}]*)\}", PAGE, re.S)
    assert lane, "the lane rule is gone"
    h = re.search(r"height:(\d+)px", lane.group(1))
    assert h, "the lane has no fixed height, so it stretches to the whole column and the chips become blocks"
    px = int(h.group(1))
    assert 200 <= px <= 300, f"the lane is {px}px; measured readable is 240, a chip taller than {px} would read as a bar"

    mid = re.search(r"\.aed-mid\{([^}]*)\}", PAGE, re.S)
    assert mid, "the middle column rule is gone"
    assert "1fr" not in mid.group(1).split("grid-template-rows")[-1], \
        "the middle column hands the lane every pixel again, which is how the chips became blocks"


def test_the_picture_card_does_not_stretch():
    """The three zones share a height, so the picture card grew to 750 px with the frame at the top.

    `align-self:start` is what keeps a picture card hugging its picture.
    """
    vid = re.search(r"\.aed-vid\{([^}]*)\}", PAGE, re.S)
    assert vid, "the picture card rule is gone"
    assert "align-self:start" in vid.group(1), \
        "the picture card stretches to the tallest zone again, leaving black under the frame"


check("the track uses the width it was given", test_the_track_uses_the_width_it_was_given)
check("the picture card hugs its picture", test_the_picture_card_does_not_stretch)

print()
if FAILED:
    print(f"{len(FAILED)} check(s) failed - {', '.join(n for n, _ in FAILED)}")
    sys.exit(1)
print(f"All checks passed. {OK} ok")
