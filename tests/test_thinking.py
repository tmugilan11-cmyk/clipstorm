"""A thinking model is told how hard to think: the critics briefly, everything else not at all, and a service that
refuses the setting is never sent it again. No network: the request is caught before it leaves."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio import ai, brain

FAILED = []


def check(name, ok, why=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({why})"))
    if not ok:
        FAILED.append(name)


class Resp:
    def __init__(self, code):
        self.status_code = code
        self.text = "{}"

    def json(self):
        return {"choices": [{"message": {"content": '{"items": []}'}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}}


def main():
    check("a scout does not think", brain.think_for("Video: scout (the talk)") == "off")
    check("the story does not think", brain.think_for("Video: story (a part)") == "off")
    check("a critic thinks briefly", brain.think_for("Video: critic (the editor)") == "low")
    check("the showrunner thinks briefly", brain.think_for("Video: showrunner") == "low")

    sent = []
    real = (ai.httpx.post, ai.base_url, ai.key, ai._openai_body)
    ai.base_url, ai.key, ai._openai_body = (lambda: "http://fake/v1"), (lambda: ""), (lambda r: r.json())
    try:
        ai.httpx.post = lambda url, json=None, headers=None, timeout=None: sent.append(json) or Resp(200)
        with ai.thinking("off"):
            ai._openai("m1", "say hi", None)
        check("thinking off is asked for", sent[-1].get("chat_template_kwargs") == {"enable_thinking": False}, sent[-1])
        with ai.thinking("low"):
            ai._openai("m1", "say hi", None)
        check("brief thinking is asked for", sent[-1].get("reasoning_effort") == "low", sent[-1])
        ai._openai("m1", "say hi", None)
        check("outside a block nothing about thinking is sent",
              "reasoning_effort" not in sent[-1] and "chat_template_kwargs" not in sent[-1], sent[-1])

        sent.clear()
        ai.httpx.post = lambda url, json=None, headers=None, timeout=None: sent.append(json) or Resp(
            400 if ("thinking" in json or "reasoning_effort" in json) else 200)
        with ai.thinking("off"):
            out = ai._openai("m2", "say hi", None)
        check("a service that refuses the setting still answers", out[0] == [] and len(sent) == 2, len(sent))
        sent.clear()
        with ai.thinking("off"):
            ai._openai("m2", "say hi", None)
        check("and is never sent it again", len(sent) == 1 and "thinking" not in sent[0], sent)
    finally:
        ai.httpx.post, ai.base_url, ai.key, ai._openai_body = real
        ai._think_refused.discard(("http://fake/v1", "m2"))
    print()
    if FAILED:
        print(f"{len(FAILED)} failed: " + ", ".join(FAILED))
        raise SystemExit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
