"""Speech to text with word timestamps, using Parakeet 0.6b through sherpa-onnx.

It runs in one of two places. On this machine's processors (the default), or, when PEAKCUT_ASR_URL is set, on a
separate machine with a graphics card (studio/asr_worker.py), which does the same work many times faster. If that
machine cannot be reached, the pieces are done here instead, so transcription never stops because of it.

Also supports cloud transcription through Logfare (logfare.ai) with selectable models."""
import io
import math
import os
import queue
import re
import threading
import time

import numpy as np

from . import config

_lock = threading.Lock()

# Several copies of the speech model, each on a few cores, instead of one copy on all of them: one copy cannot keep
# a big machine busy, and several videos transcribing at once would queue behind each other inside it. On a small
# machine (under 8 cores) this is still a single copy, as before.
_CPUS = os.cpu_count() or 4
PROVIDER = os.environ.get("PEAKCUT_ASR_PROVIDER", "cpu").strip().lower() or "cpu"      # "cuda" on a graphics card
THREADS = int(os.environ.get("PEAKCUT_ASR_THREADS") or (4 if _CPUS >= 8 else max(2, _CPUS - 2)))
COPIES = int(os.environ.get("PEAKCUT_ASR_COPIES") or (1 if PROVIDER != "cpu" else max(1, _CPUS // THREADS) if _CPUS >= 8 else 1))
_free: "queue.LifoQueue" = queue.LifoQueue()
_made = 0

# The machine with the graphics card, if there is one.
REMOTE = os.environ.get("PEAKCUT_ASR_URL", "").strip().rstrip("/")
REMOTE_TOKEN = os.environ.get("PEAKCUT_ASR_TOKEN", "").strip()
REMOTE_BATCH = int(os.environ.get("PEAKCUT_ASR_REMOTE_BATCH", "8"))         # pieces sent together: the card does them at once
REMOTE_PARALLEL = int(os.environ.get("PEAKCUT_ASR_REMOTE_PARALLEL", "4"))   # pieces of one video worked on at once
# The card has a ceiling: beyond a few requests at once it gets no faster. So only this many are sent to it at a
# time (all videos together), and the rest is done on this machine's own processors at the same moment: both are used.
REMOTE_SLOTS = threading.BoundedSemaphore(max(1, int(os.environ.get("PEAKCUT_ASR_REMOTE_INFLIGHT", "6"))))
_remote_down_until = 0.0

# ---------------------------------------------------------------- Logfare cloud transcription
# Where the calls go: logfare.ai itself, or a relay of your own when that toggle is on. Refreshed at boot and
# whenever the settings are saved, so a toggle takes effect without a restart.
LOGFARE_BASE_URL = config.logfare_base_url()
LOGFARE_KEY = config.LOGFARE_KEY
LOGFARE_MODEL = config.LOGFARE_MODEL


def use_base_url() -> str:
    """Re-read where transcription calls go. Called at boot and after the settings are saved."""
    global LOGFARE_BASE_URL
    LOGFARE_BASE_URL = config.logfare_base_url()
    return LOGFARE_BASE_URL


def cloud() -> bool:
    """True when transcription goes to Logfare instead of this machine. Read lazily so a settings
    change takes effect for the next job without a restart."""
    return config.TRANSCRIBE_PROVIDER == "logfare" and bool(LOGFARE_KEY)


# What the timings on the last returned words came from: "real" when the engine gave them, "estimated" when
# they were spread across the audio here. Kept as a module-level flag so the shape of the words never changes.
LAST_TIMING = "real"

_WORD_FLOOR = 2.0        # characters a word is given before it costs anything: "a" is not three times shorter than "the"
_MAX_WORD_SECONDS = 0.62  # a word longer than this is read as two words run together, not as one spoken slowly


def timing_quality(words: list) -> str:
    """Whether the words carry timings from the engine ("real") or were spread across the audio here
    ("estimated"). Judge them the way the last call to transcribe() judged them."""
    if not words:
        return "real"
    return LAST_TIMING


def _align(words: list, duration: float) -> list:
    """Give words that have no timing of their own one that fits the audio, weighted by how long each word
    takes to say: a long word lasts longer than "a", so captions stay near the voice instead of drifting.

    A word's weight is its characters plus a small floor, so short words still get a share. Weights are
    normalised to the audio duration, and no single word is stretched past 0.62 s unless it is long enough
    that it genuinely takes that long, in which case the short words around it give the time back."""
    out = []
    if not words:
        return out
    try:
        duration = float(duration)
    except (TypeError, ValueError):
        duration = 0.0
    if not math.isfinite(duration) or duration <= 0:
        return out

    weights = []
    for w in words:
        text = str((w or {}).get("w") or "").strip()
        weights.append(len(text) + _WORD_FLOOR)
    total = sum(weights)
    if total <= 0:
        return out

    # Seconds per unit of weight, then a ceiling: a word may only take longer than 0.62 s if its own weight
    # earns it, and never more than a quarter of the audio.
    per_unit = duration / total
    cap = max(_MAX_WORD_SECONDS, min(duration / 4.0, duration))

    t = 0.0
    for w, weight in zip(words, weights):
        start = round(min(t, duration), 2)
        span = min(weight * per_unit, cap)
        end = round(min(start + max(span, 0.08), duration), 2)
        out.append({"w": (w or {}).get("w", ""), "s": start, "e": end})
        t = end
    return out


def _logfare_transcribe(audio: np.ndarray) -> list:
    """Send audio to Logfare.ai and return [{'w': word, 's': start_sec, 'e': end_sec}, ...].
    The reply carries real word timings under result.segments[*].words (checked against the live
    API 2026-11-19); they are used directly. When a reply has none, timings fall back to an even
    spread across the audio, which makes captions drift away from the voice."""
    import httpx
    import soundfile as sf

    # Write audio to an in-memory WAV (16-bit mono 16 kHz — what Logfare expects).
    # Callers hand this either int16 samples (what media.load_audio returns) or floats in -1..1. Casting
    # floats straight to int16 would turn a whole waveform into zeros — silence — and the service answers
    # silence with an invented sentence instead of nothing, so the scale is settled here, once.
    samples = np.asarray(audio)
    if samples.dtype.kind == "f":
        peak = float(np.max(np.abs(samples))) if samples.size else 0.0
        if peak <= 1.0:
            samples = samples * 32768.0    # 32768, not 32767: this is the exact scale int16 samples were made with
    samples = np.clip(samples, -32768, 32767).astype(np.int16)
    if not samples.size or not np.any(samples):
        return []          # nothing was said: do not pay for a call that can only invent words
    buf = io.BytesIO()
    sf.write(buf, samples, 16000, format="WAV", subtype="PCM_16")
    buf.seek(0)

    # Send to Logfare
    files = {"file": ("audio.wav", buf, "audio/wav")}
    data = {"model": LOGFARE_MODEL, "word_timestamps": "true"}
    headers = {"Authorization": f"Bearer {LOGFARE_KEY}"}

    r = httpx.post(
        f"{LOGFARE_BASE_URL}/audio/transcriptions",
        data=data,
        files=files,
        headers=headers,
        timeout=httpx.Timeout(120, connect=10),
    )
    r.raise_for_status()
    body = r.json()
    # The live API wraps the payload in {"result": {...}}; accept a bare {"text": ...} too.
    res = body.get("result") if isinstance(body.get("result"), dict) else body

    # Two reply shapes come back, and which one arrives depends on the model chosen. Both are read here, so
    # picking a model in the page is enough to change the answer — no model needs its own code path:
    #   whisper-*  {"result": {"text": ..., "segments": [{"words": [{"word", "start", "end"}]}]}}
    #   nova-3     {"result": {"results": {"channels": [{"alternatives": [{"transcript", "words": [...]}]}]}}}
    # Every word in both shapes carries {"word", "start", "end"}.
    raw_words = []
    text = ""
    chans = (res.get("results") or {}).get("channels") if isinstance(res.get("results"), dict) else None
    alts = (chans[0].get("alternatives") or []) if chans and isinstance(chans[0], dict) else []
    if alts and isinstance(alts[0], dict):
        text = str(alts[0].get("transcript") or "").strip()
        raw_words = alts[0].get("words") or []
    else:
        text = str(res.get("text") or "").strip()
        for seg in res.get("segments") or []:
            if isinstance(seg, dict):
                raw_words.extend(seg.get("words") or [])
    if not text and not raw_words:
        return []

    # Real word timings straight from the reply: {"word": "hello", "start": 0.0, "end": 0.4}
    out = []
    for word in raw_words:
        if not isinstance(word, dict):
            continue
        w = str(word.get("word") or "").strip()
        if not w:
            continue
        s, e = word.get("start"), word.get("end")
        if not isinstance(s, (int, float)) or not isinstance(e, (int, float)) or e < s:
            continue
        out.append({"w": w, "s": round(float(s), 2), "e": round(float(e), 2)})
    if out:
        return out

    # No timings in the reply: spread the words evenly across the audio duration
    words = re.findall(r"\w+(?:['’]\w+)?", text)
    if not words:
        return []

    duration = len(audio) / 16000.0
    if len(words) == 1:
        return [{"w": words[0], "s": 0.0, "e": round(duration, 2)}]

    word_duration = max(0.08, duration / len(words))
    t = 0.0
    for w in words:
        end = round(min(t + word_duration, duration), 2)
        out.append({"w": w, "s": round(t, 2), "e": end})
        t = end
    return out


def model_ready() -> bool:
    from . import fetch_model
    return fetch_model.ready()


def ready() -> bool:
    """Can this server transcribe at all, by either route?

    The settings page and the admin page both ask this: a machine set to Logfare has no local model and does not
    need one, so asking `model_ready` there showed a failing pill on a perfectly working install."""
    return cloud() or model_ready()


def label() -> str:
    """One plain phrase for whichever route is in use, for a status pill."""
    if cloud():
        return "Logfare · " + (LOGFARE_MODEL or "no model chosen")
    return "on this machine"


def _model_files(d) -> dict:
    """The model's three parts. A graphics card wants the full-precision files; processors the compact ones."""
    kinds = ("fp16", "", "int8") if PROVIDER != "cpu" else ("int8", "", "fp16")
    for k in kinds:
        names = {p: d / (f"{p}.{k}.onnx" if k else f"{p}.onnx") for p in ("encoder", "decoder", "joiner")}
        if all(f.is_file() for f in names.values()):
            return {p: str(f) for p, f in names.items()}
    raise FileNotFoundError(f"No speech model files in {d}")


_lib = {"mod": None}
_lib_lock = threading.Lock()


def _sherpa():
    """The speech library, loaded once. Several copies of the model start on parallel threads, so loading is done
    under a lock: two threads loading it at the same moment would trip over each other."""
    with _lib_lock:
        if _lib["mod"] is None:
            _lib["mod"] = _load_sherpa()
        return _lib["mod"]


def _load_sherpa():
    """On Windows a file whose full path is over 260 characters cannot be loaded, which happens when PeakCut sits in a
    deep folder ("DLL load failed ... The filename or extension is too long"). Then the library is loaded through
    the folder's short name (C:\\Users\\...\\SITE-P~1), which points at the same files, or else from a copy of it
    in a short folder (AppData\\Local\\PeakCut\\lib), made once."""
    import sys
    try:
        import sherpa_onnx
        return sherpa_onnx
    except ImportError as e:
        if os.name != "nt" or "too long" not in str(e).lower():
            raise
        first = e
    import ctypes
    import importlib
    import importlib.util
    import shutil
    from pathlib import Path

    def forget():
        for k in [m for m in sys.modules if m == "sherpa_onnx" or m.startswith("sherpa_onnx.")]:
            del sys.modules[k]
        importlib.invalidate_caches()

    def load_from(folder: str):
        forget()
        sys.path.insert(0, folder)          # stays first: later imports inside the library look here too
        try:
            return importlib.import_module("sherpa_onnx")
        except ImportError:
            sys.path.remove(folder)
            forget()
            return None

    forget()
    spec = importlib.util.find_spec("sherpa_onnx")
    pkg = Path(spec.origin).parent if spec and spec.origin else None
    if pkg is None:
        raise first
    buf = ctypes.create_unicode_buffer(1024)
    if ctypes.windll.kernel32.GetShortPathNameW(str(pkg.parent), buf, 1024) and len(buf.value) < len(str(pkg.parent)):
        mod = load_from(buf.value)
        if mod:
            return mod
    # A copy of the library in a short folder. Same version check each start, so an update replaces it.
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "PeakCut" / "lib"
    stamp = base / "sherpa_onnx.from"
    want = f"{pkg}|{(pkg / '__init__.py').stat().st_mtime_ns}"
    try:
        if not (base / "sherpa_onnx").is_dir() or not stamp.is_file() or stamp.read_text(encoding="utf-8") != want:
            shutil.rmtree(base / "sherpa_onnx", ignore_errors=True)
            shutil.copytree(pkg, base / "sherpa_onnx")
            stamp.write_text(want, encoding="utf-8")
        mod = load_from(str(base))
        if mod:
            return mod
    except OSError:
        pass
    raise RuntimeError("PeakCut is in a folder too deep for Windows to load the speech model from. Move the PeakCut "
                       "folder somewhere short, like C:\\peakcut, and start it again.") from first


def _new():
    sherpa_onnx = _sherpa()
    from . import fetch_model
    fetch_model.ensure()             # downloaded here, once, if it was never fetched
    d = config.ASR_MODEL_DIR
    return sherpa_onnx.OfflineRecognizer.from_transducer(
        **_model_files(d),
        tokens=str(d / "tokens.txt"),
        num_threads=THREADS,
        sample_rate=16000,
        feature_dim=80,
        decoding_method="greedy_search",
        model_type="nemo_transducer",
        provider=PROVIDER,
    )


def _take():
    """A free copy of the model: one that is idle, a new one while there is room for more, else wait for one."""
    global _made
    try:
        return _free.get_nowait()
    except queue.Empty:
        pass
    with _lock:
        make = _made < COPIES
        if make:
            _made += 1
    if make:
        try:
            return _new()
        except Exception:
            with _lock:
                _made -= 1
            raise
    return _free.get()


def _take_now():
    """A copy of the model if one is free (or can still be made) this instant, else None."""
    global _made
    try:
        return _free.get_nowait()
    except queue.Empty:
        pass
    with _lock:
        make = _made < COPIES
        if make:
            _made += 1
    if not make:
        return None
    try:
        return _new()
    except Exception:
        with _lock:
            _made -= 1
        raise


def _recognizer():
    """Kept for callers that only need the model loaded (warm-up)."""
    rec = _take()
    _free.put(rec)
    return rec


def _chunks(audio: np.ndarray, lo=12.0, hi=24.0):
    """Split at the quietest point between lo and hi seconds so words are not cut in half."""
    sr, hop = 16000, 800  # 50 ms frames
    n = len(audio)
    frames = n // hop
    if frames == 0:
        return
    x = audio[: frames * hop].reshape(frames, hop).astype(np.float32)
    rms = np.sqrt((x ** 2).mean(axis=1))
    pos = 0
    while pos < n:
        if n - pos <= hi * sr:
            yield pos, n
            return
        a, b = (pos + int(lo * sr)) // hop, (pos + int(hi * sr)) // hop
        cut = (a + int(np.argmin(rms[a:b]))) * hop + hop // 2
        yield pos, cut
        pos = cut


BATCH = int(os.environ.get("PEAKCUT_ASR_BATCH", "1"))   # pieces decoded together. Measured: no faster on CPU, since
# each piece already uses every core, so one at a time (which also keeps the words exactly as before).


def _words(tokens, timestamps, a: int, b: int) -> list:
    out = []
    off, seg_end = a / 16000.0, b / 16000.0
    cur, gap = None, False
    for tok, t in zip(tokens, timestamps):
        new_word = tok.startswith((" ", "▁")) or gap
        piece = tok.replace("▁", " ").strip()
        if not piece:
            gap = True      # a space on its own: whatever comes next starts a new word ("in" "120", not "in120")
            continue
        gap = False
        is_punct = all(not c.isalnum() for c in piece)
        if cur is None or (new_word and not is_punct):
            if cur:
                out.append(cur)
            cur = {"w": piece, "s": round(off + t, 2), "e": round(off + t + 0.12, 2)}
        else:
            cur["w"] += piece
            cur["e"] = round(off + t + 0.12, 2)
    if cur:
        cur["e"] = min(cur["e"], round(seg_end, 2))
        out.append(cur)
    return out


def decode_pieces(pieces: list, rec=None) -> list:
    """[(tokens, timestamps), ...] for float32 pieces of audio, done on this machine with one copy of the model."""
    streams = []
    rec = rec or _take()       # held only for these pieces, so videos transcribing at once take turns fairly
    try:
        for seg in pieces:
            st = rec.create_stream()
            st.accept_waveform(16000, seg)
            streams.append(st)
        rec.decode_streams(streams)
    finally:
        _free.put(rec)
    return [(list(st.result.tokens), [float(t) for t in st.result.timestamps]) for st in streams]


def _remote_ok() -> bool:
    return bool(REMOTE) and time.time() >= _remote_down_until


def _decode_remote(pieces: list) -> list:
    """The same, on the machine with the graphics card. Audio goes as 16-bit sound, the answer comes back as text."""
    import httpx
    raw = [np.clip(seg * 32768.0, -32768, 32767).astype("<i2") for seg in pieces]
    r = httpx.post(REMOTE + "/decode", content=b"".join(x.tobytes() for x in raw), timeout=httpx.Timeout(120, connect=4),
                   headers={"Authorization": "Bearer " + REMOTE_TOKEN, "X-Lens": ",".join(str(len(x)) for x in raw),
                            "Content-Type": "application/octet-stream"})
    r.raise_for_status()
    got = r.json()["pieces"]
    if len(got) != len(pieces):
        raise ValueError("wrong number of pieces came back")
    return [(p["tokens"], p["timestamps"]) for p in got]


def transcribe(audio: np.ndarray, on_progress=None, quiet_ok: bool = False) -> list:
    """Returns [{'w': word, 's': start_sec, 'e': end_sec}, ...] for the whole audio.
    Speech is cut at quiet moments into 12-24 s pieces; silent pieces are skipped.

    When PEAKCUT_TRANSCRIBE_PROVIDER is "logfare", the whole audio is sent to Logfare.ai
    in one go instead of being transcribed locally.

    `quiet_ok` is for a live stream, which is listened to a few seconds at a time: a stretch with nobody
    talking (a waiting screen, music, gameplay) is normal there, so when the speech service answers with no
    words that is taken as the answer instead of being tried again on a second engine."""
    global _remote_down_until

    # --- Logfare cloud transcription path ------------------------------------------------
    if cloud():
        if on_progress:
            on_progress(0.0)
        answered = True
        try:
            words = _logfare_transcribe(audio)
        except Exception as exc:  # noqa: BLE001
            answered = False
            # Only fall back to the engine on this machine when that engine can actually run. Otherwise the
            # job would die on "no module named sherpa_onnx" — a message that names a library the person never
            # chose instead of saying what really went wrong.
            if not model_ready() and not _remote_ok():
                raise RuntimeError(
                    "Logfare could not transcribe this audio: " + (str(exc)[:200] or exc.__class__.__name__)
                    + ". The speech engine on this machine is not installed either, so there was nothing to "
                      "fall back to. Check the key and the model under Settings, Transcription."
                ) from exc
            import traceback
            print("  Logfare transcription failed, falling back to local:", traceback.format_exc(), flush=True)
            words = []
        if on_progress:
            on_progress(1.0)
        if words:
            # A word lasts until the next one starts, capped so pauses stay pauses.
            for i, w in enumerate(words):
                nxt = words[i + 1]["s"] if i + 1 < len(words) else w["e"] + 0.4
                w["e"] = round(max(w["s"] + 0.08, min(nxt, max(w["e"], w["s"] + 0.6))), 2)
            return words
        if quiet_ok and answered:
            return []          # the service heard it and nobody was talking
        # Nothing usable came back. Falling through quietly would hand the work to a different engine without
        # saying so, and an empty answer is far more often a broken key or a wrong model than a silent video.
        if not model_ready() and not _remote_ok():
            raise RuntimeError(
                "Logfare answered, but with no words. Nothing was heard in this audio, or the chosen model does "
                "not return speech. Check the model under Settings, Transcription."
            )
        # If Logfare returned empty or failed, continue with local transcription below.

    # --- Local transcription path --------------------------------------------------------
    words = []
    todo = []
    for a, b in _chunks(audio):
        seg = audio[a:b].astype(np.float32) / 32768.0
        if len(seg) < 4800 or float(np.sqrt((seg ** 2).mean())) < 0.003:
            continue  # silence: skip, saves time and avoids made-up words
        todo.append((a, b, seg))
    remote = _remote_ok()
    size = max(1, REMOTE_BATCH if remote else BATCH)
    groups = [todo[i:i + size] for i in range(0, len(todo), size)]
    done = [0]

    def decode(group):
        global _remote_down_until
        segs = [seg for _, _, seg in group]
        got = None
        while got is None:
            # whichever is free first: a place on the card's machine, or a copy of the model on this one
            if remote and _remote_ok() and REMOTE_SLOTS.acquire(blocking=False):
                try:
                    got = _decode_remote(segs)
                except Exception:  # noqa: BLE001 - the card's machine is away or busy: these pieces are done here
                    _remote_down_until = time.time() + 60
                finally:
                    REMOTE_SLOTS.release()
                continue
            rec = _take_now()
            if rec is None and not (remote and _remote_ok()):
                rec = _take()                                # nothing else to wait for: wait for a copy here
            if rec is not None:
                got = []
                step = max(1, BATCH)
                try:
                    for i in range(0, len(segs), step):
                        got += decode_pieces(segs[i:i + step], rec)
                        rec = None if i + step >= len(segs) else _take()
                except Exception:
                    got = None
                    raise
                continue
            time.sleep(0.02)
        out = [_words(tok, ts, a, b) for (a, b, _), (tok, ts) in zip(group, got)]
        done[0] += 1
        if on_progress:
            on_progress(done[0] / len(groups))
        return out

    # Pieces are independent, so they go to every copy of the model that is free: a video alone on the server
    # uses all of it, and several videos share it piece by piece. The words come back in order.
    workers = REMOTE_PARALLEL if remote else COPIES
    if workers > 1 and len(groups) > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(min(workers, len(groups)), thread_name_prefix="asr") as ex:
            results = list(ex.map(decode, groups))
    else:
        results = [decode(g) for g in groups]
    for out in results:
        for piece in out:
            for w in piece:
                if words and words[-1]["w"] == w["w"] and words[-1]["s"] == w["s"]:
                    continue  # the model sometimes says the same word twice at the same moment
                words.append(w)
    # A word lasts until the next one starts, capped so pauses stay pauses.
    for i, w in enumerate(words):
        nxt = words[i + 1]["s"] if i + 1 < len(words) else w["e"] + 0.4
        w["e"] = round(max(w["s"] + 0.08, min(nxt, max(w["e"], w["s"] + 0.6))), 2)
    return words
