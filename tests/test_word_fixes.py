"""A streamer says "chat" all day, and the speech engine writes "chad". The transcript is put right as it is heard.

No audio and no service: `fix_words` works on the words the engine returned."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio import transcribe

FAILED = []


def check(name, ok, why=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({why})"))
    if not ok:
        FAILED.append(name)


def said(text):
    return [{"w": w, "s": float(i), "e": i + 0.4} for i, w in enumerate(text.split())]


def fixed(text):
    return " ".join(w["w"] for w in transcribe.fix_words(said(text)))


def main():
    check("chad is chat", fixed("what do you think chad") == "what do you think chat", fixed("what do you think chad"))
    check("a capital in the middle of a sentence goes", fixed("hey Chad look at this") == "hey chat look at this",
          fixed("hey Chad look at this"))
    check("a capital at the start of a sentence stays", fixed("Chad, which door? Chad! help") == "Chat, which door? Chat! help",
          fixed("Chad, which door? Chad! help"))
    check("shouting stays shouting", fixed("oh my god CHAD") == "oh my god CHAT", fixed("oh my god CHAD"))
    check("punctuation and 's stay where they were", fixed("that is chad's fault, chad.") == "that is chat's fault, chat.",
          fixed("that is chad's fault, chat."))
    check("giga chad is left alone", fixed("he is a giga chad") == "he is a giga chad", fixed("he is a giga chad"))
    check("other words are untouched", fixed("the chadwick chart chatter") == "the chadwick chart chatter")
    words = said("yo chad")
    transcribe.fix_words(words)
    check("the times are not touched", [(w["s"], w["e"]) for w in words] == [(0.0, 0.4), (1.0, 1.4)])
    check("nothing to fix is fine", transcribe.fix_words([]) == [])

    os.environ["PEAKCUT_WORD_FIXES"] = "chad=chat, speeds=Speed's"
    check("the list can be added to", fixed("speeds chad") == "Speed's chat", fixed("speeds chad"))
    os.environ["PEAKCUT_WORD_FIXES"] = ""
    check("an empty list fixes nothing", fixed("yo chad") == "yo chad")
    os.environ.pop("PEAKCUT_WORD_FIXES", None)

    # the whole path: whatever engine hears it, transcribe() hands back the fixed words
    real = transcribe._transcribe
    transcribe._transcribe = lambda audio, on_progress=None, quiet_ok=False: said("chad you lied to me")
    try:
        check("transcribe() itself returns the fixed words",
              " ".join(w["w"] for w in transcribe.transcribe(None)) == "chat you lied to me")
    finally:
        transcribe._transcribe = real

    print()
    if FAILED:
        print(f"{len(FAILED)} failed: " + ", ".join(FAILED))
        raise SystemExit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
