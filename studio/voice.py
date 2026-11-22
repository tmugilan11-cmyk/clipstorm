"""Your own line over a finished Short: while you talk the game audio steps back, and swells up again when you stop."""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import threading
from pathlib import Path

from . import config
from .media import NO_WINDOW

# ---------------------------------------------------------------- the numbers
# Taken from the one-file original (gta6-clipper-main/voice.py) unless a comment says "port", so a Short made here
# sounds like the one the feature was ported from.
VOICE_LUFS: float = -16.0          # the level your line is brought to first: the ducker listens to it afterwards
VOICE_TP: float = -1.5             # ... and the true peak it may reach on the way in
MIX_RATE: int = 48000
DUCK_RATIO: float = 20.0           # how hard the ducker leans once the line is above its threshold
DUCK_ATTACK_MS: int = 15           # quick enough to be there on the first syllable
DUCK_RELEASE_MS: int = 400         # the game is back at full about half a second after the line ends
DUCK_DEFAULT_DB: float = 18.0      # how far the game steps back, which is what the user is really choosing
DUCK_MAX_DB: float = 30.0
DUCK_THRESHOLD: float = 0.015      # what the original shipped (-36.5 dBFS); only used when no level was measured
LIMIT: float = 0.95                # the last thing before the encoder: -0.45 dBFS, so nothing can clip
GAME_LUFS: float = -14.0           # port: a finished PeakCut clip is already normalised to this (render.py's -af)
GAME_TP: float = -1.5
GAME_LRA: float = 11.0
THRESHOLD_MIN: float = 0.001       # -60 dBFS, and ffmpeg's own floor: it refuses anything under 0.000976563
THRESHOLD_MAX: float = 0.20        # -14 dBFS
MAX_AT_PAST_END: float = 0.20      # port: a line starting in the last fifth of a second is not a line
SILENT_DB: float = -70.0           # port: a line this quiet is a recording that never started, not a quiet room
KEY_OFFSET_DB: float = 3.0         # port: how far volumedetect's mean sits under the level sidechaincompress reacts to
VOICE_MAX_MB: int = 25
VOICE_EXTS: tuple[str, ...] = (".wav", ".mp3", ".m4a", ".aac", ".ogg", ".opus",
                               ".flac", ".aiff", ".mp4", ".mov", ".m4v", ".webm")
MIX_SECONDS = 600                  # a mix is seconds of work; far past this ffmpeg is stuck, not slow

_MEAN_VOLUME = re.compile(r"mean_volume:\s*(-?\d+(?:\.\d+)?) dB")
_NAME = re.compile(r"[\w.\-]{1,120}")


class VoiceError(RuntimeError):
    """Something the machine could not do: ffmpeg, a file, a timeout. The message is a sentence for the user."""


# ---------------------------------------------------------------- levels
def db_to_linear(db: float) -> float:
    """A level in dB as a plain multiplier (0 dB is 1.0)."""
    return 10.0 ** (float(db) / 20.0)


def linear_to_db(x: float) -> float:
    """A plain multiplier as a level in dB. Silence is -240 dB rather than an error."""
    return 20.0 * math.log10(max(float(x), 1e-12))


def threshold_for(duck_db: float, voice_db: float, ratio: float = DUCK_RATIO) -> float:
    """The sidechain threshold that makes a line measured at `voice_db` push the game down by `duck_db`.

    The depth is not a setting inside sidechaincompress: it falls out of how far the key sits above the
    threshold (slope 1 - 1/ratio), so the threshold is what has to be worked out from the depth asked for.
    Without this the graph only ever gives the ~16 dB the shipped constant happens to produce, and a quiet
    phone recording ducks nothing at all."""
    duck_db, voice_db = float(duck_db), float(voice_db)
    if not math.isfinite(duck_db) or not 0.0 <= duck_db <= DUCK_MAX_DB:
        raise ValueError("The duck has to be between 0 and 30 dB.")
    if not math.isfinite(voice_db):
        raise ValueError("I couldn't measure how loud your line is.")
    slope = 1.0 - 1.0 / float(ratio)
    excess = duck_db / slope
    return min(THRESHOLD_MAX, max(THRESHOLD_MIN, db_to_linear(voice_db - excess)))


def _ffmpeg(args: list, timeout: int) -> subprocess.CompletedProcess:
    """Run ffmpeg and hand back the finished process whatever its exit code. The only things that can come out
    of here are VoiceError, so a broken install or a hung encode can never reach the server as a raw OSError."""
    try:
        return subprocess.run(["ffmpeg", *args], capture_output=True, text=True, encoding="utf-8",
                              errors="replace", creationflags=NO_WINDOW, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise VoiceError("Mixing your line took too long and was stopped. Try a shorter line.") from None
    except OSError as e:
        raise VoiceError("ffmpeg isn't installed on this machine, so your line can't be mixed in.") from e


def _why(err: str) -> str:
    """ffmpeg's last words, said in a way a person can act on."""
    text = (err or "").strip()
    low = text.lower()
    if "stream map '0:v' matches no streams" in low or "no video" in low:
        return "That clip has no picture in it."
    if ("matches no streams" in low or "does not contain any stream" in low
            or "stream map '[a]'" in low):
        return "That clip has no sound in it, so there is nothing to duck."
    if "invalid data found" in low or "moov atom not found" in low:
        return "The clip or the recording is damaged and can't be read."
    if "unknown encoder" in low or "encoder not found" in low:
        return "This copy of ffmpeg can't encode the mixed audio."
    return (text.splitlines()[-1] if text else "ffmpeg stopped without saying why.")[:300]


def probe_db(path: Path, timeout: int = 120) -> float:
    """How loud a recording is on average, in dBFS, measured by ffmpeg's own volumedetect.

    volumedetect writes to stderr, which is why this is not a media.run call (that returns stdout only).
    Raises ValueError when the file holds no sound, VoiceError when ffmpeg cannot read it at all."""
    path = Path(path)
    if not path.is_file():
        raise ValueError("That recording isn't there any more. Record your line again.")
    p = _ffmpeg(["-hide_banner", "-nostats", "-v", "info", "-i", str(path), "-map", "0:a:0",
                 "-af", "volumedetect", "-f", "null", "-"], timeout)
    err = p.stderr or ""
    found = _MEAN_VOLUME.search(err)
    if found:
        mean = float(found.group(1))
        # A silent file is measured, not refused, by volumedetect: -91 dBFS or so. Saying so here means the
        # user is told their recording is empty instead of getting a clip with no duck and no explanation.
        if mean < SILENT_DB:
            raise ValueError("That file has no sound in it.")
        return mean
    if "does not contain any stream" in err or "matches no streams" in err:
        raise ValueError("That file has no sound in it.")
    if p.returncode != 0:
        raise VoiceError(f"ffmpeg couldn't read your line: {_why(err)}")
    raise ValueError("That file has no sound in it.")


def key_db(path: Path, loudness: float = VOICE_LUFS, timeout: int = 120) -> float:
    """The level to calibrate the ducker on: the line after the graph's own normalisation, lifted by
    `KEY_OFFSET_DB`.

    `probe_db` measures the file as it was handed in, which is the number worth showing the user. That is the
    wrong number to calibrate on. Two corrections, both measured on ffmpeg 9.0.2 with a 10 s / 200 Hz bed and a
    line starting at 2.0 s:

    - a quiet phone recording is lifted to -16 LUFS before the ducker hears it, so calibrating on the raw level
      over-ducks badly (a -37 dBFS line asking for 18 dB came out at 34.6 dB);
    - volumedetect's mean sits about 3 dB under the level sidechaincompress reacts to, because its detector
      follows peaks rather than the mean: that read as 20.4 dB for a request of 18, and 21.4 dB for speech-like
      content.

    With both applied the same measurement gives the depth that was asked for. A stored level should be
    `probe_db`, not this. Falls back to the raw level when the second measurement cannot be had, so a mix never
    fails over a nicety."""
    try:
        p = _ffmpeg(["-hide_banner", "-nostats", "-v", "info", "-i", str(path), "-map", "0:a:0",
                     "-af", f"loudnorm=I={loudness}:TP={VOICE_TP},aresample={MIX_RATE},"
                            f"aformat=channel_layouts=stereo,volumedetect", "-f", "null", "-"], timeout)
        found = _MEAN_VOLUME.search(p.stderr or "")
        if found:
            return float(found.group(1)) + KEY_OFFSET_DB
    except VoiceError:
        pass
    return probe_db(path, timeout)


# ---------------------------------------------------------------- the filter graph
def mix_chain(at: float, duck_db: float, voice_db: float, *,
              loudness: float = VOICE_LUFS, true_peak: float = VOICE_TP,
              ratio: float = DUCK_RATIO, attack_ms: int = DUCK_ATTACK_MS,
              release_ms: int = DUCK_RELEASE_MS, limit: float = LIMIT, rate: int = MIX_RATE,
              game_lufs: float | None = GAME_LUFS) -> str:
    """The graph that puts the line at `at` seconds over the game and ducks the game by `duck_db`, producing `[a]`.

    Input 0 is the game, input 1 is the line. The fragment starts with `;` because render.py appends it straight
    after its `[v0]ass=...` chain; a caller using it as the whole graph strips that first character.

    `game_lufs` None leaves the game's level alone, which is right for `apply` (a finished clip is already at
    -14 LUFS); a render that starts from the raw source keeps it so the order is normalise, duck, mix."""
    at = float(at)
    if not math.isfinite(at) or at < 0:
        raise ValueError("Your line can't start before the clip does.")
    ms = int(at * 1000)                      # truncates, exactly as the original did: 2.999 s is 2999 ms
    thr = threshold_for(duck_db, voice_db, ratio)
    game = f"[0:a]aresample={rate},aformat=channel_layouts=stereo"
    if game_lufs is not None:
        # loudnorm hands its output back at 192 kHz. Left there, amix's duration=first takes its length from a
        # clock that no longer matches the voice and cuts the clip short (10 s in, 7.16 s out, measured on
        # ffmpeg 9.0.2), so the rate is put back before the ducker sees it.
        game += (f",loudnorm=I={game_lufs}:TP={GAME_TP}:LRA={GAME_LRA},"
                 f"aresample={rate},aformat=channel_layouts=stereo")
    # apad is not cosmetic: sidechaincompress stops when its key stops, so without it the whole mix is cut off
    # at the end of the line instead of the end of the clip.
    return (
        f";{game}[gm];"
        f"[1:a]loudnorm=I={loudness}:TP={true_peak},aresample={rate},"
        f"aformat=channel_layouts=stereo,adelay=delays={ms}:all=1,apad,asplit=2[vo][sc];"
        f"[gm][sc]sidechaincompress=threshold={thr:.6f}:ratio={ratio}:"
        f"attack={attack_ms}:release={release_ms}:makeup=1[duck];"
        f"[duck][vo]amix=inputs=2:duration=first:normalize=0,alimiter=limit={limit}[a]"
    )


# ---------------------------------------------------------------- what the page sends
def _number(value: object) -> float | None:
    """A finite number out of whatever JSON, a form field or the settings file holds, or None."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _safe_name(name: str) -> bool:
    """A bare file name that can only ever mean a file inside the clip's own folder."""
    return bool(_NAME.fullmatch(name)) and ".." not in name


def clean_spec(raw: object, duration: float, *, default_duck: float = DUCK_DEFAULT_DB) -> dict | None:
    """Check what the page sent about one clip's line, and return it as four plain values.

    Returns None when the line is being taken off. Raises ValueError with the sentence to show the user, so a
    route can turn it straight into a 400. `duration` is the clip's own length in seconds."""
    if raw is None or raw == {} or (isinstance(raw, dict) and raw.get("off")):
        return None
    if not isinstance(raw, dict):
        raise ValueError("The voice setting is not valid.")
    at = _number(raw.get("at"))
    if at is None:
        raise ValueError("Say what second your line should start on.")
    if at < 0:
        raise ValueError("Your line can't start before the clip does.")
    if at > float(duration) - MAX_AT_PAST_END:
        raise ValueError("Your line starts after the clip ends. Pick an earlier second.")
    duck = default_duck if raw.get("duck") in (None, "") else _number(raw.get("duck"))
    if duck is None or not 0.0 <= duck <= DUCK_MAX_DB:
        raise ValueError("The duck has to be between 0 and 30 dB.")
    db = _number(raw.get("db"))
    if db is None:
        raise ValueError("I couldn't measure how loud your line is.")
    name = str(raw.get("file") or "").strip()
    if not _safe_name(name):
        raise ValueError("The voice file is missing.")
    return {"file": name, "at": round(at, 3), "duck": round(duck, 1), "db": round(db, 2)}


def remove(path: Path) -> None:
    """Delete a line's file, and shrug if it has already gone: the delete paths call this more than once."""
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass


# ---------------------------------------------------------------- the feature itself
def apply(short: Path, line: Path, at: float, out: Path, duck: float = 18.0) -> Path:
    """Put `line` at `at` seconds over the finished `short`, ducking the game by `duck` dB while it plays.

    The picture is copied, not re-encoded, so this is only ever used on a clip that is already made. Writes
    `out` and returns it. Everything raised is ValueError (something about the request) or VoiceError (something
    about the machine), each carrying a sentence for the user; nothing here can stop the server."""
    short, line, out = Path(short), Path(line), Path(out)
    at = _number(at)
    if at is None:
        raise ValueError("Say what second your line should start on.")
    if at < 0:
        raise ValueError("Your line can't start before the clip does.")
    duck = _number(duck)
    if duck is None or not 0.0 <= duck <= DUCK_MAX_DB:
        raise ValueError("The duck has to be between 0 and 30 dB.")
    if not short.is_file():
        raise ValueError("That clip isn't there any more. Make it again first.")
    if not line.is_file():
        raise ValueError("That recording isn't there any more. Record your line again.")
    probe_db(line)               # refuses a silent file with a sentence before any mixing is attempted
    heard = key_db(line)         # the same line after the graph's loudnorm: the level the ducker actually hears
    chain = mix_chain(at, duck, heard, game_lufs=None).lstrip(";")
    # The mix lands next to its destination first and is renamed into place when ffmpeg has finished, so a
    # crashed or killed mix can never leave a half-written file where a good clip used to be.
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.parent / f".{out.stem}.{os.urandom(6).hex()}{out.suffix or '.mp4'}"
    try:
        p = _ffmpeg(["-y", "-v", "error", "-i", str(short), "-i", str(line),
                     "-filter_complex", chain, "-map", "0:v", "-map", "[a]",
                     "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", str(MIX_RATE),
                     "-movflags", "+faststart", str(tmp)], MIX_SECONDS)
        if p.returncode != 0:
            raise VoiceError(f"Couldn't mix your line in: {_why(p.stderr)}")
        tmp.replace(out)
    finally:
        remove(tmp)
    return out


def ready() -> bool:
    """Whether this machine can mix at all (ffmpeg on the PATH). Cheap enough to call while drawing a page."""
    return shutil.which("ffmpeg") is not None


# ---------------------------------------------------------------- settings (voice.json, the ai.py pattern)
_lock = threading.Lock()
_saved = {"at": None, "data": {}}
DEFAULTS = {"duck": DUCK_DEFAULT_DB, "loudness": VOICE_LUFS, "max_mb": VOICE_MAX_MB}
BOUNDS = {"duck": (0.0, DUCK_MAX_DB), "loudness": (-30.0, -8.0), "max_mb": (1.0, 200.0)}
ENV = {"duck": "PEAKCUT_VOICE_DUCK", "loudness": "PEAKCUT_VOICE_LUFS", "max_mb": "PEAKCUT_VOICE_MAX_MB"}


def _file() -> Path:
    return config.DATA_DIR / "voice.json"


def _from_dashboard() -> dict:
    """What was saved from the settings page, read again only when the file changes."""
    f = _file()
    try:
        at = f.stat().st_mtime_ns
    except OSError:
        at = 0
    if _saved["at"] != at:
        try:
            data = json.loads(f.read_text(encoding="utf-8")) if at else {}
        except (OSError, ValueError):
            data = {}
        _saved.update(at=at, data=data if isinstance(data, dict) else {})
    return _saved["data"]


def current() -> dict:
    """The three numbers in use: what the settings page saved, else the environment, else the defaults.

    A hand-edited file holding null, [], a number or text is ignored field by field rather than breaking a render."""
    saved = _from_dashboard()
    out = {}
    for key, default in DEFAULTS.items():
        value = _number(saved.get(key))
        if value is None:
            value = _number(config.env(ENV[key]))
        if value is None:
            value = default
        low, high = BOUNDS[key]
        value = min(high, max(low, value))
        out[key] = int(round(value)) if key == "max_mb" else round(value, 2)
    return out


def public() -> dict:
    """What the settings page may see: the three numbers, plus where the ducker's threshold sits for a line
    normalised to `loudness`. There is nothing secret in here, so it is all of it."""
    c = current()
    threshold = threshold_for(c["duck"], c["loudness"])
    return {**c, "threshold": round(threshold, 6), "threshold_db": round(linear_to_db(threshold), 1)}


def save(values: dict) -> dict:
    """Save the numbers the settings page sent. One left out keeps what is there; one out of range is refused."""
    if not isinstance(values, dict):
        raise ValueError("The voice settings are not valid.")
    now = current()
    refuses = {"duck": "The duck has to be between 0 and 30 dB.",
               "loudness": "The line's level has to be between -30 and -8 LUFS.",
               "max_mb": "A recording may be between 1 and 200 MB."}
    for key in DEFAULTS:
        value = _number(values.get(key))
        if value is None:
            continue
        low, high = BOUNDS[key]
        if not low <= value <= high:
            raise ValueError(refuses[key])
        now[key] = int(round(value)) if key == "max_mb" else round(value, 2)
    with _lock:
        f = _file()
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(now, indent=1), encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        tmp.replace(f)
        _saved["at"] = None
    return public()
