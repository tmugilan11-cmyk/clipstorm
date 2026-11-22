"""Checks the Logfare transcription path without spending a key.

Runs the real code in studio/transcribe.py, but answers the HTTP call itself, so what is tested is the
request PeakCut builds and what it does with the reply. No network, no key, no credits.

    python tests/test_transcribe_logfare.py
"""
import io
import sys
from pathlib import Path

import httpx
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio import config, transcribe  # noqa: E402

failures = []


def check(name, got, want):
    if got == want:
        print(f"  ok    {name}")
    else:
        print(f"  FAIL  {name}: got {got!r}, wanted {want!r}")
        failures.append(name)


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def main() -> int:
    seen = {}

    def fake_post(url, data=None, files=None, headers=None, timeout=None, **kw):
        seen["url"] = url
        seen["data"] = data
        seen["headers"] = headers
        seen["filename"] = files["file"][0]
        seen["mimetype"] = files["file"][2]
        body = files["file"][1]
        seen["audio_bytes"] = body.read() if hasattr(body, "read") else body
        return FakeResponse({"text": "The quick brown fox jumps over the lazy dog."})

    # The module imports httpx inside the function, so the patch goes on the real module.
    real_post = httpx.post
    transcribe.LOGFARE_KEY = "test-key-not-real"
    transcribe.LOGFARE_MODEL = "nova-3"
    config.TRANSCRIBE_PROVIDER = "logfare"

    audio = (np.random.randn(16000 * 5) * 800).astype(np.int16)     # five seconds

    print("A request to Logfare is built correctly")
    httpx.post = fake_post
    words = transcribe._logfare_transcribe(audio)
    check("endpoint", seen["url"], "https://logfare.ai/v1/audio/transcriptions")
    check("model sent", seen["data"]["model"], "nova-3")
    check("key sent as a bearer header", seen["headers"]["Authorization"], "Bearer test-key-not-real")
    check("uploaded as a wav", seen["filename"], "audio.wav")
    check("uploaded with a wav type", seen["mimetype"], "audio/wav")
    check("the audio is actually attached", seen["audio_bytes"][:4], b"RIFF")

    print("The reply becomes word timings")
    check("word count", len(words), 9)
    check("first word", words[0]["w"], "The")
    check("last word", words[-1]["w"], "dog")
    check("starts at zero", words[0]["s"], 0.0)
    check("timings only go forward", all(words[i]["s"] <= words[i + 1]["s"] for i in range(len(words) - 1)), True)
    check("stays inside the audio", words[-1]["e"] <= 5.0, True)
    check("every word has the three keys PeakCut needs", sorted(words[0]), ["e", "s", "w"])

    # The scale of the samples handed in. media.load_audio gives int16, but a caller passing floats in -1..1
    # used to be cast straight to int16 — every sample became zero, the service was sent silence, and it
    # answered silence with an invented sentence. Both scales must now produce the same audio, and true
    # silence must not be sent at all.
    print("Audio in either scale goes out as the same 16-bit sound")
    sent = {}

    def capture(url, data=None, files=None, headers=None, timeout=None, **kw):
        body = files["file"][1]
        sent["wav"] = body.read() if hasattr(body, "read") else body
        return FakeResponse({"text": "hello there"})

    httpx.post = capture
    tone = (np.sin(np.linspace(0, 400 * np.pi, 16000)) * 9000).astype(np.int16)
    transcribe._logfare_transcribe(tone)
    as_int16 = sent["wav"][44:]                      # past the RIFF/fmt/data header
    transcribe._logfare_transcribe(tone.astype(np.float32) / 32768.0)
    as_float = sent["wav"][44:]
    httpx.post = fake_post                           # put the original stub back for the checks below
    check("float samples are not flattened to silence", any(b != 0 for b in as_float), True)
    check("both scales send identical bytes", as_int16, as_float)

    print("Silence is never sent, because the answer would be invented")
    calls = []

    def count(url, data=None, files=None, headers=None, timeout=None, **kw):
        calls.append(url)
        return FakeResponse({"text": "Thank you."})

    httpx.post = count
    silent_words = transcribe._logfare_transcribe(np.zeros(16000, dtype=np.int16))
    httpx.post = fake_post                           # ...and again, so the cloud-path checks see the real stub
    check("silence returns no words", silent_words, [])
    check("...and costs no call", len(calls), 0)

    print("transcribe() takes the cloud path when it is chosen")
    got = transcribe.transcribe(audio)
    check("words came from Logfare", [w["w"] for w in got][:3], ["The", "quick", "brown"])
    check("no word lasts longer than a breath", max(w["e"] - w["s"] for w in got) <= 0.61, True)

    # Picking a model in the page has to be enough to change the answer. The service answers in two different
    # shapes depending on the model, and only one of them used to be read — so nova-3 always came back empty and
    # the job quietly fell through to the engine on this machine.
    print("Both reply shapes become word timings")
    whisper_like = {"result": {"text": "ask not what", "segments": [
        {"words": [{"word": "ask", "start": 0.0, "end": 0.3},
                   {"word": "not", "start": 0.3, "end": 0.6},
                   {"word": "what", "start": 0.6, "end": 0.9}]}]}}
    nova_like = {"result": {"results": {"channels": [{"alternatives": [{
        "transcript": "ask not what",
        "words": [{"word": "ask", "start": 0.0, "end": 0.3, "confidence": 0.9},
                  {"word": "not", "start": 0.3, "end": 0.6, "confidence": 0.9},
                  {"word": "what", "start": 0.6, "end": 0.9, "confidence": 0.9}]}]}]}}}

    def reply(payload):
        def post(url, data=None, files=None, headers=None, timeout=None, **kw):
            return FakeResponse(payload)
        return post

    httpx.post = reply(whisper_like)
    got_whisper = transcribe._logfare_transcribe(audio)
    httpx.post = reply(nova_like)
    got_nova = transcribe._logfare_transcribe(audio)
    httpx.post = fake_post
    check("the whisper shape is read", [w["w"] for w in got_whisper], ["ask", "not", "what"])
    check("the nova shape is read", [w["w"] for w in got_nova], ["ask", "not", "what"])
    check("...with the same timings either way", got_nova, got_whisper)

    print("A failure falls back to the local model when that model is installed")
    def boom(*a, **kw):
        raise RuntimeError("network went away")
    httpx.post = boom
    called = {"local": False}
    real_chunks = transcribe._chunks
    real_ready = transcribe.model_ready

    def fake_chunks(a):
        called["local"] = True
        return []                               # nothing to decode, so the local path finishes immediately
    transcribe._chunks = fake_chunks
    transcribe.model_ready = lambda: True       # there is an engine on this machine to fall back to
    out = transcribe.transcribe(audio)
    transcribe._chunks = real_chunks
    check("local transcription was tried", called["local"], True)
    check("nothing invented on failure", out, [])

    # With no engine on this machine there is nowhere to fall back to, and saying "no module named
    # sherpa_onnx" would name a library the person never chose. The real reason has to come through instead.
    print("With no engine here, the real reason is reported instead of a library name")
    transcribe.model_ready = lambda: False
    raised = ""
    try:
        transcribe.transcribe(audio)
    except RuntimeError as exc:
        raised = str(exc)
    transcribe.model_ready = real_ready
    httpx.post = fake_post
    check("it says Logfare could not do it", raised.startswith("Logfare could not transcribe this audio:"), True)
    check("...carries the underlying reason", "network went away" in raised, True)
    check("...and names no library the person never chose", "sherpa" in raised.lower(), False)

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())