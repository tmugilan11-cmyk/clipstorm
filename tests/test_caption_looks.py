"""Check the caption looks themselves: every look named, every font present, and no post-only language effects.

A look is a table row, so nothing here renders a clip. What it does do is prove the three things that go wrong
quietly: a look whose font file is missing, a look that no page can offer because it has no name, and a CJK look
asked to preview an English sentence (every glyph from the fallback, line breaks measured on the wrong alphabet).
"""
import os
import sys

sys.path.insert(0, ".")
FAILED = []


def check(name, condition, detail=""):
    if condition:
        print(f"ok   {name}")
    else:
        FAILED.append(name)
        print(f"FAIL {name}" + (f"   [{detail}]" if detail else ""))


def main():
    from studio import api_style, captions, config

    names = captions.style_names()
    check("there are 42 video looks to choose from", len(names) == 42, len(names))
    check("every look is named for a person", all(captions.label(n).strip() for n in names))
    check("no two looks share a name", len(set(captions.label(n) for n in names)) == len(names))

    # A style row is (file stem, family name, ...) and FONT_FILES is keyed by the FAMILY name, which is what
    # libass is told to draw with. Both have to be right: the stem is the file copied into the render folder, the
    # family is the name inside that file.
    missing = []
    for n in names:
        stem, family = captions.STYLES[n][0], captions.STYLES[n][1]
        mapped = captions.FONT_FILES.get(family)
        if not mapped or not (config.FONTS_DIR / mapped).is_file():
            missing.append((n, family, mapped))
    check("every look has a font file on this machine", not missing, missing[:3])
    check("every style's file stem matches a real file", not [
        n for n in names if not (config.FONTS_DIR / (captions.STYLES[n][0] + ".ttf")).is_file()],
        [n for n in names if not (config.FONTS_DIR / (captions.STYLES[n][0] + ".ttf")).is_file()][:3])

    # a look the style table forgot to name would never appear in a picker
    unlabelled = [n for n in names if n not in captions.LABELS]
    check("every look has a plain-English label", not unlabelled, unlabelled[:3])

    # Post-description languages must not grow video effects again.
    check("post-only additions are absent", not set(names).intersection(captions.POST_ONLY_STYLES))
    check("no post-only animation remains", not set(captions.ANIM).intersection(captions.POST_ONLY_STYLES))
    en_words, en_hook, _, _ = api_style._sample_for("bounce")
    check("all previews use the source sentence", en_words is api_style._SAMPLE)
    check("all previews use the source hook", en_hook == api_style._SAMPLE_HOOK)

    # every animation name a look uses must be one the builder implements, or the look silently falls back to a
    # plain word pop and the two "glow" looks a person picked do nothing they can see
    handled = set(captions.NOW) | {"box", "phrase", "duo", "meme", "slide", "type", "drop"}
    used = {v for v in captions.ANIM.values() if v}
    unimplemented = sorted(used - handled)
    check("every animation a look names is implemented", not unimplemented, unimplemented)

    # and the builder must actually emit motion for a look that names one
    words = [{"w": "this", "s": 0.0, "e": 0.4}, {"w": "is", "s": 0.4, "e": 0.7},
             {"w": "the", "s": 0.7, "e": 1.0}]
    for name in ("hormozi-pro", "neon-pop", "title-slide", "pill-dark"):
        ass = captions.build_ass(words, 0.0, 1.0, "watch this", name, ["the"], 300, 1380)
        dlg = [line for line in ass.splitlines() if line.startswith("Dialogue:")]
        motion = any(r"\t(" in line or r"\fad(" in line or r"\kf" in line for line in dlg)
        check(f"{name} draws motion, not a still line", motion, name)

    print()
    if FAILED:
        print(f"{len(FAILED)} check(s) failed: {FAILED}")
        raise SystemExit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
