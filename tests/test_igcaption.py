"""Plain-text caption behavior. Route and upload integration lives in test_post_caption.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from studio import igcaption

CLIP = {"title": "1 VS 3", "description": "He won the last round.", "hashtags": ["#gaming"]}

def main():
    assert igcaption.default(CLIP) == "1 VS 3\n\nHe won the last round.\n\n#gaming"
    assert igcaption.default({}) == ""
    for text in ("日本語の説明。\n\n#ゲーム", "中文说明。\n\n#游戏", "Plain text", ""):
        clip = dict(CLIP, ig_caption_enabled=True, ig_caption=text)
        assert igcaption.for_post(clip, {"post_footer": "footer"}) == text
    assert igcaption.validate_text("line1\r\nline2") == "line1\nline2"
    for bad in (None, [], "x" * 2201):
        try:
            igcaption.validate_text(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid caption was accepted")
    seen = []
    def ask(prompt):
        seen.append(prompt)
        return {"caption": "最後のラウンドで逆転。"}
    for form in igcaption.FORMATS:
        got = igcaption.generate(CLIP, "ja", form, ask)
        assert got["caption"] == "最後のラウンドで逆転。" and got["saved"] is False
    assert len(seen) == len(igcaption.FORMATS)
    try:
        igcaption.generate(CLIP, "ja", ask_fn=lambda prompt: {"caption": "Still English"})
    except RuntimeError:
        pass
    else:
        raise AssertionError("English was claimed as a Japanese translation")
    assert not any(key in igcaption.view(CLIP) for key in ("rank", "font", "drawn_as"))
    print("All checks passed.")

if __name__ == "__main__":
    main()
