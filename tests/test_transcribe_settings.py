"""Checks the transcription settings endpoint: what it saves, what it refuses to wipe,
and where the Logfare calls go when the relay toggle is on or off.

Runs the real route in studio/server.py without a server: the function is called directly
with a fake signed-in admin. Everything lands in a throwaway data folder.

    python tests/test_transcribe_settings.py
"""
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tests" / "settings-data"          # a plain folder: tempfile.mkdtemp is unwritable on some hosts
DATA.mkdir(parents=True, exist_ok=True)
os.environ["PEAKCUT_DATA"] = str(DATA)

sys.path.insert(0, str(ROOT))

from fastapi import HTTPException                # noqa: E402
from starlette.requests import Request           # noqa: E402

from studio import config, server, transcribe    # noqa: E402

failures = []


def check(name, got, want):
    if got == want:
        print(f"  ok    {name}")
    else:
        print(f"  FAIL  {name}: got {got!r}, wanted {want!r}")
        failures.append(name)


def admin_request() -> Request:
    req = Request({"type": "http", "method": "PUT", "headers": [], "query_string": b"", "path": "/api/transcribe"})
    req.state.user = types.SimpleNamespace(is_admin=True, disabled=False)
    return req


def put(body: dict) -> dict:
    return server.transcribe_put(admin_request(), body)


def refused(body: dict) -> HTTPException:
    try:
        put(body)
    except HTTPException as e:
        return e
    raise AssertionError(f"the call should have been refused: {body!r}")


def reset():
    (DATA / "tr.json").unlink(missing_ok=True)
    config.LOGFARE_PROXY = bool(config.env("PEAKCUT_LOGFARE_PROXY", "").strip().lower() in ("1", "true", "on", "yes"))
    transcribe.use_base_url()


def main() -> int:
    reset()
    ai_base_before = config.AI_BASE_URL          # the relay must never touch the AI provider's address

    # a key can be saved, and a missing model keeps the saved one
    out = put({"provider": "logfare", "key": "lf-test-abcdefghijkl", "model": "nova-3"})
    check("save a key and model", (out["provider"], out["model"], out["has_key"]), ("logfare", "nova-3", True))
    out = put({"provider": "logfare"})           # no model given: the saved one must survive
    check("blank model keeps the saved one", out["model"], "nova-3")

    # switching to Local without a key in the box must NOT wipe the stored key
    out = put({"provider": "local"})
    check("Local save keeps the key", out["has_key"], True)
    check("Local save keeps the model", out["model"], "nova-3")

    # forget_key really clears it, even with no key field in the body (this used to be a no-op)
    out = put({"provider": "local", "forget_key": True})
    check("forget_key clears the key", out["has_key"], False)

    # a Logfare save without a key is refused, and forgetting the key while Logfare is picked is refused too
    e = refused({"provider": "logfare"})
    check("logfare without a key refused", e.status_code, 400)
    e = refused({"provider": "logfare", "model": "nova-3", "forget_key": True})
    check("forgetting the key on logfare refused", e.status_code, 400)
    out = put({"provider": "local"})             # leave a clean slate
    check("still no key after the refusals", out["has_key"], False)

    # a Logfare save without any model at all is refused (fresh data folder, no env default either)
    reset()
    saved_model = config.LOGFARE_MODEL
    config.LOGFARE_MODEL = ""
    try:
        e = refused({"provider": "logfare", "key": "lf-test-abcdefghijkl"})
        check("logfare without any model refused", e.status_code, 400)
        check("refusal text", e.detail, "Pick a model for Logfare.")
    finally:
        config.LOGFARE_MODEL = saved_model

    # the relay toggle: on sends the calls to the relay, off sends them to logfare.ai
    reset()
    out = put({"provider": "logfare", "key": "lf-test-abcdefghijkl", "model": "nova-3", "proxy": True})
    check("toggle on is saved", out["proxy"], True)
    check("toggle on moves the calls", out["where"], config.LOGFARE_PROXY_URL)
    out = put({"provider": "logfare", "proxy": False})
    check("toggle off is saved", out["proxy"], False)
    check("toggle off moves the calls back", out["where"], "https://logfare.ai/v1")
    out = put({"provider": "logfare"})           # body without "proxy": the saved choice survives
    check("toggle survives a save that omits it", out["proxy"], False)
    put({"provider": "local", "forget_key": True})

    # a hand-edited tr.json must not break anything, and a non-bool proxy is ignored
    for junk in ("null", "[]", "3", '"text"', '{"provider": 42, "proxy": "yes"}'):
        (DATA / "tr.json").write_text(junk, encoding="utf-8")
        s = server._tr_saved()
        check(f"junk tr.json survives: {junk[:22]}", (s["provider"], isinstance(s["proxy"], bool)), ("local", True))
    reset()

    # the relay only ever moves the transcription calls
    check("AI base url untouched", config.AI_BASE_URL, ai_base_before)
    reset()
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
