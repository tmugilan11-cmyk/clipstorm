"""Live sessions: record a stream into a rolling buffer, transcribe as it goes, let the AI pick clips."""
from __future__ import annotations

import collections
import json
import re
import socket
import ssl
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np

from . import alerts, auth, brain, config, creators, ctx, facecam, games, jobs, load, media, transcribe, usage

# ":username!user@host PRIVMSG #channel :the message"
_NICK = re.compile(r"(?m)^:([A-Za-z0-9_]{2,25})!")

SESSIONS: dict = {}
SEG_SEC = 6           # length of each buffer piece
PAD = 8               # seconds kept either side of a clip so it can be re-trimmed later
CHECK_EVERY = 180     # look at the stream every 3 minutes...
QUIET_MAX = 600       # ...but only ask the AI when something happened, or at most every 10 minutes when calm
WINDOW = 240          # seconds of transcript shown to the AI per check
CHAT_KEEP = 600       # seconds of chat names kept: only the last few minutes are ever read
SR = 16000
CATCHUP_KEEP = 4 * 3600   # the most stream kept while catching up, in seconds
AHEAD_MAX = 30 * 60       # how far the download may run ahead of the listening while it catches up
FRAG_WORKERS = 16         # stream fragments downloaded at once
FRAG_AHEAD = 8            # pieces whose fragments are downloading ahead of the one being written
RW_TIMEOUT = 15           # seconds a read from the stream may hang before ffmpeg gives up on it
CATCHUP_AI = 600          # seconds the listening may run ahead of the AI while it catches up
MAX_LIVE_CLIPS = int(config.env("PEAKCUT_MAX_LIVE_CLIPS", "100"))   # the most clips one recording makes by itself


class NotLive(Exception):
    pass


def _trim_names(users: dict, second: int, kept: int) -> int:
    """Drop the chat names older than CHAT_KEEP, and say when this was last done.

    Only the last few minutes are ever read, and a stream that runs for eight hours would otherwise hold
    a name for every second of it. Called under the session's lock, from the chat reader thread."""
    if second - kept < 60:
        return kept              # walking the whole dict on every message would cost more than it saves
    for t in [t for t in users if t < second - CHAT_KEEP]:
        del users[t]
    return second


def media_safe(e) -> str:
    from . import safe
    return safe.friendly(e, 300)


def normalize(url: str) -> str:
    url = url.strip()
    if not re.match(r"^https?://", url):
        url = "https://" + url
    m = re.match(r"^(https?://(?:www\.)?youtube\.com/(?:@[^/?#]+|channel/[^/?#]+|c/[^/?#]+))/?(?:[?#].*)?$", url)
    return m.group(1) + "/live" if m else url


class _Quiet:
    def debug(self, m): pass
    def info(self, m): pass
    def warning(self, m): pass
    def error(self, m): pass


# Tried in order after a "confirm you're not a bot" page: the same request over IPv4, then over IPv4 as the
# mobile web player, which still gets through when the usual one is challenged on both routes.
_BOT_FALLBACKS = ({"source_address": "0.0.0.0"},
                  {"source_address": "0.0.0.0", "extractor_args": {"youtube": {"player_client": ["mweb"]}}})
_UA = {"User-Agent": "Mozilla/5.0"}


def _is_bot_check(message) -> bool:
    low = str(message).lower()
    return "not a bot" in low or "sign in to confirm" in low


def _extract(opts: dict, url: str):
    import yt_dlp
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def resolve(url: str, from_start: bool = False) -> dict:
    """Ask yt-dlp, once, where the stream is. Raises NotLive if the channel is offline.

    "urls" is what one ffmpeg can read directly: one address, or the picture's and then the sound's when
    the platform serves them apart. With `from_start`, a stream that can be walked from its very first
    fragment (YouTube) also comes back with "frags": the picture's and the sound's fragment address and
    how many seconds each fragment lasts."""
    if media.is_youtube(url) and media.youtube_paused():
        raise NotLive(media.YT_BLOCKED)
    walk = bool(from_start) and media.is_youtube(url)
    opts = {"quiet": True, "no_warnings": True, "noplaylist": True, "skip_download": True, "logger": _Quiet(),
            "socket_timeout": 45,
            "format": "b[height<=1080]/bv*[height<=1080]+ba/b"}
    if walk:
        # H.264 picture and AAC sound: the two that go into a stream piece as they are, with no re-encoding
        opts.update(live_from_start=True,
                    format="bv*[height<=1080][vcodec^=avc1]+ba[acodec^=mp4a]/bv*[height<=1080]+ba/b")
    try:
        info = _extract(opts, url)
    except Exception as e:  # noqa: BLE001
        info, last = None, e
        if _is_bot_check(e):
            for extra in _BOT_FALLBACKS:
                try:
                    info = _extract({**opts, **extra}, url)
                    break
                except Exception as again:  # noqa: BLE001
                    last = again
                    if not _is_bot_check(again):
                        break
        if info is None:
            if media.note_refusal(url, last):
                raise NotLive(media.YT_BLOCKED) from last
            raise NotLive(str(last)[-200:]) from last
    if isinstance(info, list):
        info = info[0] if info else None
    if not info or not info.get("is_live"):
        raise NotLive("This channel is not live right now.")
    fmts = info.get("requested_formats") or [info]
    frags = None
    if walk:
        gen = [f for f in fmts if f.get("protocol") == "http_dash_segments_generator" and f.get("url")]
        pic = [f for f in gen if f.get("vcodec") not in (None, "none")]
        snd = [f for f in gen if f.get("vcodec") in (None, "none") and f.get("acodec") not in (None, "none")]
        if len(gen) == 2 and pic and snd:
            frags = [{"base": f["url"], "td": float(f.get("target_duration") or 2)} for f in (pic[0], snd[0])]
        else:
            return resolve(url)          # this stream cannot be walked from its start: record it from now
    title = info.get("title") or ""
    if "(live)" in title and info.get("description"):  # Twitch puts the real stream title here
        title = str(info["description"]).splitlines()[0][:120]
    return {"urls": [f["url"] for f in fmts if f.get("url")], "title": title, "frags": frags,
            "uploader": info.get("uploader") or info.get("channel") or ""}


_HOST_JOB = None
_HOST_JOB_LOCK = threading.Lock()


def _die_with_us(proc) -> bool:
    """Windows: make this ffmpeg end when PeakCut ends, however PeakCut ends.

    A recording's ffmpeg used to carry on after the server was killed or crashed, writing stream pieces
    nobody would ever read or delete for as long as the broadcast lasted. A job object that closes with
    this process ends every ffmpeg tied to it. Best effort: False where it cannot be done."""
    global _HOST_JOB
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)

        class _Basic(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                        ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                        ("SchedulingClass", wintypes.DWORD)]

        class _Extended(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", _Basic), ("IoInfo", ctypes.c_ulonglong * 6),
                        ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

        k32.CreateJobObjectW.restype = wintypes.HANDLE
        k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        with _HOST_JOB_LOCK:
            if _HOST_JOB is None:
                job = k32.CreateJobObjectW(None, None)
                if not job:
                    return False
                info = _Extended()
                info.BasicLimitInformation.LimitFlags = 0x2000          # kill everything in it when it closes
                if not k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
                    return False
                _HOST_JOB = int(job)
        return bool(k32.AssignProcessToJobObject(wintypes.HANDLE(_HOST_JOB), wintypes.HANDLE(int(proc._handle))))
    except Exception:  # noqa: BLE001 - never a reason to lose a recording
        return False


def _sweep(job) -> int:
    """Delete the stream pieces a finished recording left behind; how many files went.

    A recording frees its pieces when it ends, but one that was cut short (the server was closed or
    restarted) never got that far, and its pieces - gigabytes of them for a long stream - stayed on disk
    for good. Its clips are kept elsewhere and are not touched."""
    gone = 0
    try:
        for f in (Path(job["dir"]) / "buffer").glob("*"):
            try:
                f.unlink()
                gone += 1
            except OSError:
                pass             # still held open by something: it goes next time
    except Exception:  # noqa: BLE001
        pass
    return gone


def _fetch(url: str, timeout: float = 20) -> bytes:
    """One stream fragment."""
    import urllib.request
    with urllib.request.urlopen(urllib.request.Request(url, headers=_UA), timeout=timeout) as r:
        return r.read()


def _head_seq(base: str):
    """The number of the newest fragment the stream has, or None when it would not say."""
    import urllib.request
    try:
        with urllib.request.urlopen(urllib.request.Request(base, headers=_UA, method="HEAD"), timeout=15) as r:
            return int(r.headers.get("X-Head-Seqnum"))
    except Exception:  # noqa: BLE001
        return None


def _list_rows(path) -> list:
    """The finished pieces ffmpeg has listed so far: [(name, start, end)]. A row is written when its piece
    is closed, so a piece with a row is whole; a last line still being written is left for next time."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    lines = text.split("\n")
    lines.pop()                  # "" after a finished line, or a line cut off half-way
    rows = []
    for line in lines:
        parts = line.strip().rsplit(",", 2)
        if len(parts) != 3:
            continue
        try:
            rows.append((parts[0].strip().strip('"'), float(parts[1]), float(parts[2])))
        except ValueError:
            continue
    return rows


def _playlist_window(url: str):
    """(the last segment number the stream has, seconds per segment, segments in the window).

    A live playlist says how far the stream has got (`EXT-X-MEDIA-SEQUENCE` is the first segment it still
    lists), so asking it twice tells us how much stream went by in between. Only used to place a resumed
    recording; anything that is not a playlist is left to ffmpeg."""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    text = urllib.request.urlopen(req, timeout=15).read(400_000).decode("utf-8", "ignore")
    if "#EXTM3U" not in text:
        raise ValueError("not a playlist")
    seq = re.search(r"#EXT-X-MEDIA-SEQUENCE:(\d+)", text)
    dur = re.search(r"#EXT-X-TARGETDURATION:([\d.]+)", text)
    return (int(seq.group(1)) if seq else 0,
            float(dur.group(1)) if dur else 5.0,
            max(1, text.count("#EXTINF")))


def _goes_back(url: str) -> bool:
    """Whether ffmpeg can be asked to start earlier than now in this address."""
    return ".m3u8" in url or "hls_playlist" in url or "manifest" in url


def active():
    return [s for s in SESSIONS.values() if not s.finished and not s.user_stopped]


def active_mine():
    u = ctx.uid()
    return [s for s in active() if s.job["user"] == u]


def active_for(cid):
    return next((s for s in active_mine() if s.job["creator"] == cid), None)


def mine(jid):
    """The signed-in user's recording with this id, or None."""
    s = SESSIONS.get(jid)
    return s if s and s.job["user"] == ctx.uid() else None


class Session:
    def __init__(self, job, settings):
        self.job, self.settings = job, settings
        self.dir = Path(job["dir"])
        self.buf = (self.dir / "buffer").resolve()   # absolute: ffmpeg is handed these paths as they are
        self.buf.mkdir(exist_ok=True)
        (self.dir / "clips").mkdir(exist_ok=True)
        self.lock = threading.RLock()
        self.stop_flag = threading.Event()
        self.ended = False            # recording has stopped (stream over, stopped, or failed)
        self.finished = False         # everything is wrapped up
        self.end_note = "Stream ended"
        self.user_stopped = False     # Stop pressed: wrap up at once, no last AI check
        self.proc = None
        self.kids = []                # every process this connection started, so Stop can end them all
        self.pending = bytearray()    # audio received but not yet transcribed
        self.pending_base = 0         # sample index where `pending` starts
        self.db_rest = bytearray()    # sound not yet long enough to make one second of loudness
        self.mode = ""                # "start": fetched from the stream's first fragment; "edge": read live by ffmpeg
        self.seg_n = 0                # the number the next piece gets
        self.frag0 = int(job.get("frag_start") or 0)   # the stream fragment this recording begins at
        self.frag_next = self.frag0   # the next stream fragment to fetch
        self.frag_td = 2.0            # seconds per stream fragment
        self.frag_bad = 0             # times in a row the next piece could not be had
        self.head = -1                # the newest fragment the stream has, last time it was asked
        self.spike_pos = 0            # the second up to which loudness has been looked at for jumps
        self.judged_to = 0.0          # the second up to which the AI has read the whole transcript
        self.reading_from = 0.0       # where the AI check now running began reading
        self.last_frags = None        # the stream's fragment addresses, last time they were resolved
        self.samples = 0              # total audio samples received
        self.db = []                  # loudness per second
        self.words = []
        self.t_done = 0.0             # transcript is complete up to this second
        self.segments = []            # (path, start, end) on the session clock
        self.seg_clock = 0.0
        self.part = 0
        self.chat = collections.Counter()   # second -> messages
        self.chat_users = {}                 # second -> the people who talked, when it can be told
        self.chat_kept = 0                   # the second this was last pruned at
        self.chat_total = 0
        self.chat_on = False
        self.last_check = 0.0
        self.words_at_check = 0
        self.checks = 0
        self.rejected = 0
        self.verdicts = []
        self.last_trigger = -999.0
        self.started_at = time.time()
        self.skipped = 0
        self.last_ai = 0.0
        self.tokens = 0
        self.manual = []
        self.n = 0
        self.spike = None             # a jump in loudness or chat waiting for its transcript
        self.said = None              # someone said "clip": that moment, waiting for its transcript
        self.last_said = -999.0
        self.last_spike = -999.0      # when the last jump was sent to the AI (stream seconds)
        self.base = {}                # running averages the jumps are measured against, shown on the card
        self.spikes = 0
        self.game = ""                # which game this stream is, when it can be told
        self.facecam_box = None       # where the webcam has been found most often
        self.facecam_votes = {}       # (x, y, w, h) -> clips it was found in; each clip confirms it afresh
        self.ai_busy = 0.0            # when the AI check now running was started, 0 when none is
        self.seq0 = None              # the stream's first listed segment when this recording began
        self.tgt = 5.0                # seconds per stream piece, as the playlist says
        self.behind = 0.0             # seconds the recording is behind the live edge while it catches up

    def _ask_ai(self, window=None, why=None):
        """Ask the AI on its own thread, so a slow answer never stops the recording.

        While the AI thinks, the speech keeps being written and a "clip that" still works. One check
        runs at a time; if the running one is stuck far past its own timeout, a new one is let through.
        """
        now = time.time()
        # A check is four answers one after another (a reader, the scouts, two critics, the final desk), each
        # allowed LIVE_AI_TIMEOUT; only one stuck well past all of that lets a second check through.
        if self.ai_busy and now - self.ai_busy < 5 * config.LIVE_AI_TIMEOUT + 60:
            return False

        def work():
            try:
                self._ai_check(window, why)
            except Exception as e:  # noqa: BLE001
                self.job["ai"]["last_error"] = str(e)[-200:]
            finally:
                self.ai_busy = 0.0
        self.ai_busy = now
        threading.Thread(target=ctx.bind(work), daemon=True, name="ai_check").start()
        return True

    def _webcam_for(self, src):
        """Where the webcam is in this clip's own picture, or None when it is not on screen.

        A stream does not show its webcam the whole time: it opens with the camera filling the screen, cuts to
        other scenes, comes back. Looking once, in the first clip, marked a whole five-hour stream as having
        no webcam because its first clip was the intro, and all its clips were made without the streamer. So
        every clip is checked. The place the webcam has been found most often is confirmed against this
        clip's picture (its border must be there); only when it is not there is the picture searched afresh,
        and a place found that way is used for this clip and remembered as a vote."""
        try:
            votes = self.facecam_votes
            usual = max(votes, key=votes.get) if votes else None
            if usual and facecam.still_there(src, usual):
                return list(usual)
            found = self._find_facecam(src)
            if not found:
                return None
            key = tuple(int(v) for v in found)
            votes[key] = votes.get(key, 0) + 1
            self.facecam_box = list(max(votes, key=votes.get))
            self.job["facecam"] = self.facecam_box
            return list(key)
        except Exception:  # noqa: BLE001 - no webcam is a layout, not a failure
            return None

    def _find_facecam(self, src):
        """Where the webcam is in the stream, once. Only a sure answer is used.

        One frame goes to the AI as well, and whatever it says is measured again on the
        picture. A stream where the webcam is a square picture along the right edge, or
        one where there is no webcam at all and the game has panels of its own, is told
        apart from a real camera by what moves: a person sits still, the game does not."""
        try:
            box = facecam.detect(src, ask=brain.look_for_facecam)
        except Exception:  # noqa: BLE001 - a missing facecam is not a failure
            return None
        if not box or box.get("conf") != "high":
            return None
        self.job["facecam"] = [box["x"], box["y"], box["w"], box["h"]]
        return self.job["facecam"]

    # ---------------------------------------------------------------- the game this stream is
    def _game(self):
        """The game, from what the creator set or from what the stream's title says.

        The stream title is the best place to look: on launch night it says the game."""
        if self.game:
            return self.game
        found = games.detect(self.settings.get("game"), self.job.get("title"), self.job.get("uploader"),
                             self.job.get("source", {}).get("name"))
        self.game = found[0] or ""
        if self.game:
            try:
                self.job["game"] = self.game
            except Exception:  # noqa: BLE001
                pass
        return self.game

    # ---------------------------------------------------------------- recording
    def start(self):
        SESSIONS[self.job["id"]] = self
        threading.Thread(target=ctx.bind(self._ingest), daemon=True).start()
        threading.Thread(target=ctx.bind(self._analyze), daemon=True).start()
        m = re.match(r"^https?://(?:www\.)?twitch\.tv/([A-Za-z0-9_]+)", self.job["source"]["url"])
        if m:
            threading.Thread(target=ctx.bind(self._chat), args=(m.group(1).lower(),), daemon=True).start()

    def stop(self, note="Stopped by you"):
        """Instant for the user: the card and the creator show as stopped straight away. Clips already being made
        still finish in the background, but nothing new is transcribed or sent to the AI."""
        self.end_note = note
        self.user_stopped = True
        self.stop_flag.set()
        with self.lock:
            self.job.update(status="done", stage=note)
        jobs.save(self.job)
        for p in [self.proc] + list(getattr(self, "kids", [])):
            if p and p.poll() is None:
                try:
                    p.terminate()
                except Exception:  # noqa: BLE001 - a process already gone needs no ending
                    pass

    def _ingest(self):
        """Record the stream. However this ends, even when ffmpeg cannot start at all, the session is marked as
        ended, so it stops showing as recording and gives its place to the next one."""
        try:
            self._ingest_loop()
        except Exception as e:  # noqa: BLE001
            self.job["error"] = f"Recording stopped: {media_safe(e)}"
        finally:
            self.ended = True

    def _start_index(self, url):
        """Which piece of the stream this connection should begin at.

        The first connection begins at the oldest piece the platform still offers, so a stream that has
        already been running for half an hour is recorded from its first minute and caught up on, rather
        than from the moment the button was pressed. Later connections begin where the recording got to,
        so a dropped connection neither repeats a stretch nor silently drops one. None means "carry on
        from the live edge", which is what a platform with no backlog gets."""
        if not self.settings.get("from_start", True) or not _goes_back(url):
            return None
        try:
            seq, tgt, count = _playlist_window(url)
        except Exception:  # noqa: BLE001 - a playlist that will not open is not worth failing a recording over
            return 0 if self.samples == 0 else None
        self.tgt = tgt
        if self.samples == 0 or self.seq0 is None:
            self.seq0 = seq
            return 0
        moved = max(0, seq - self.seq0)                       # pieces the live edge moved on while we worked
        done = int(self.samples / SR / max(tgt, 1.0))          # pieces we have already recorded
        at = done - moved
        if at <= 0:
            return None                                        # the rest has scrolled out of the window
        return min(at, max(0, count - 1))

    def _note(self, text):
        """One plain line in this recording's log, for whoever has to work out later what happened."""
        try:
            with open(self.dir / "ffmpeg.log", "a", encoding="utf-8") as f:
                f.write(time.strftime("%H:%M:%S ") + str(text)[:400] + "\n")
        except OSError:
            pass

    def _end_kids(self):
        for p in list(getattr(self, "kids", [])):
            if p is not None and p.poll() is None:
                try:
                    p.terminate()
                except Exception:  # noqa: BLE001
                    pass
        self.kids = []
        self.proc = None

    def _ingest_loop(self):
        """Keep the stream arriving until it ends or Stop is pressed.

        Each time round the stream is resolved once and then recorded one of two ways. A stream that can be
        walked from its first fragment (YouTube) is fetched by `_fragments`, which is how a stream that has
        been running for three hours is still recorded from its first minute. Anything else is handed to one
        ffmpeg by `_direct`. Either way every finished piece holds the picture and the sound together."""
        fails = 0
        url = self.job["source"]["url"]
        want_start = bool(self.settings.get("from_start", True))
        while not self.stop_flag.is_set():
            try:
                info = resolve(url, from_start=want_start)
            except NotLive as e:
                if self.last_frags and self.head >= 0 and self.frag_next <= self.head and fails < 3:
                    # The stream is over, but what was not fetched yet is still there to be had by number. The
                    # listening was simply behind: carry on to the end with the addresses we already hold.
                    before = self.samples
                    self._note(f"the stream ended with fragments {self.frag_next}-{self.head} still to fetch; fetching them")
                    try:
                        self._fragments(self.last_frags)
                    except Exception as again:  # noqa: BLE001
                        self._note(f"the rest could not be fetched: {again}")
                    fails = 0 if self.samples - before > SR * 20 else fails + 1
                    if self.frag_next > self.head:
                        break
                    self.stop_flag.wait(3)
                    continue
                fails += 1
                if self.samples == 0 or fails >= 3:
                    if self.samples == 0:
                        self.job["error"] = f"Could not start recording: {e}"
                    break
                self.stop_flag.wait(10)
                continue
            if not self.job.get("uploader"):
                self.job.update(title=info["title"], uploader=info["uploader"])
            self.part += 1
            before = self.samples
            try:
                if info.get("frags"):
                    self.mode = "start"
                    self.last_frags = info["frags"]
                    self._fragments(info["frags"])
                else:
                    self.mode = "edge"
                    self._direct(info["urls"])
            except Exception as e:  # noqa: BLE001 - one bad connection is started again, not the end of the recording
                self._note(f"connection {self.part} stopped: {e}")
            finally:
                self._end_kids()
            fails = 0 if self.samples - before > SR * 20 else fails + 1
            if fails >= 3:
                break
            self.stop_flag.wait(3)
        self.ended = True

    # ---------------------------------------------------------------- from the stream's first fragment
    def _fragments(self, frags):
        """Fetch the stream fragment by fragment, from wherever this recording has got to.

        YouTube keeps every two-second fragment of a live stream and hands any of them over by number, which
        is the only way back to the first minute: its live playlist lists the last fifteen minutes and no
        more. The fragments are downloaded here, many at once and always a few pieces ahead, and each few
        seconds of picture and sound are put together into one piece by a short ffmpeg that then exits.
        Nothing long-lived sits between the stream and the disk, so there is no pipe to starve and no
        process to freeze: a fragment that fails is simply asked for again. Returns when the stream stops
        moving or its addresses stop answering; the caller resolves the stream again and comes back to the
        same fragment."""
        from concurrent.futures import ThreadPoolExecutor
        from yt_dlp.utils import update_url_query
        v, a = frags
        td = float(v.get("td") or 2.0)
        n = max(1, round(SEG_SEC / td))
        self.frag_td = td
        head, asked, moved, deaf = -1, 0.0, time.time(), 0
        pool = ThreadPoolExecutor(max_workers=FRAG_WORKERS, thread_name_prefix="frag")
        futs = {}                                    # (track, fragment number) -> its download

        def grab(base, i):
            err = None
            for attempt in range(3):
                if self.stop_flag.is_set():
                    break
                try:
                    data = _fetch(update_url_query(base, {"sq": str(i)}))
                    if data:
                        return data
                except Exception as e:  # noqa: BLE001
                    err = e
                time.sleep(0.4 * (attempt + 1))
            raise err or OSError("empty fragment")

        def want(k, upto):
            """Ask for every fragment from k up to `upto` that has not been asked for yet."""
            for i in range(k, upto):
                if ("v", i) not in futs:
                    futs[("v", i)] = pool.submit(grab, v["base"], i)
                    futs[("a", i)] = pool.submit(grab, a["base"], i)

        try:
            while not self.stop_flag.is_set():
                now = time.time()
                if now - asked >= 5:
                    asked = now
                    h = _head_seq(v["base"])
                    if h is None:
                        deaf += 1
                        if deaf >= 3:
                            self._note("the stream stopped answering; resolving it again")
                            return
                    else:
                        deaf = 0
                        if h > head:
                            head, moved = h, now
                            self.head = h
                if head < 0:
                    self.stop_flag.wait(1)
                    continue
                k = self.frag_next
                ready = (head + 1 - k) // n
                size = n
                if ready <= 0:
                    if now - moved <= 60:
                        self.stop_flag.wait(1)
                        continue
                    size = head + 1 - k              # the stream stopped: take its last few seconds too
                    if size <= 0:
                        self._note("no new fragment for a minute; asking whether the stream is still on")
                        return
                elif self.seg_clock - self.t_done > AHEAD_MAX:
                    self.stop_flag.wait(2)           # far enough ahead of the listening: the rest will still be there
                    continue
                want(k, k + size * max(1, min(ready, FRAG_AHEAD)))
                if self._take_piece(futs, k, size, td):
                    self.frag_bad = 0
                    continue
                self.frag_bad += 1
                if self.frag_bad >= 4:
                    # asked for four times, twice with fresh addresses: this stretch is not coming
                    self._note(f"fragments {k}-{k + size - 1} could not be had; carrying on after them")
                    self.frag_next = k + size
                    self.frag_bad = 0
                elif self.frag_bad == 2:
                    return                            # the addresses may have run out: resolve again
                else:
                    self.stop_flag.wait(2)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

    def _take_piece(self, futs, k, size, td):
        """Wait for fragments k .. k+size-1 of the picture and of the sound, and write them as one piece.
        False when a fragment would not download or the piece could not be written; they are asked for
        afresh next time."""
        ids = range(k, k + size)
        got = [futs.pop((t, i), None) for t in ("v", "a") for i in ids]
        try:
            data = [f.result(timeout=90) for f in got]
        except Exception as e:  # noqa: BLE001 - includes a fragment that was never asked for
            self._note(f"fragments {k}-{k + size - 1} did not download: {str(e)[-160:]}")
            return False
        if not self._mux(b"".join(data[:size]), b"".join(data[size:]), size * td):
            return False
        self.frag_next = k + size
        return True

    def _mux(self, vb, ab, nominal):
        """Put a few seconds of picture and of sound together into one finished piece.

        The stream's own clock is kept (-copyts, and nothing reset), so the pieces carry one continuous
        clock and can be joined end to end without the sound sliding against the picture. The piece is
        written under another name and renamed when ffmpeg is done, so a half-written file is never read."""
        num = self.seg_n
        tv, ta = self.buf / "in_v.mp4", self.buf / "in_a.m4a"
        tmp, out = self.buf / f"seg_{num:06d}.tmp", self.buf / f"seg_{num:06d}.ts"
        try:
            tv.write_bytes(vb)
            ta.write_bytes(ab)
            r = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-copyts",
                                "-i", str(tv), "-i", str(ta), "-c", "copy", "-map", "0:v:0", "-map", "1:a:0",
                                "-f", "mpegts", str(tmp)],
                               capture_output=True, timeout=120, creationflags=media.NO_WINDOW)
            if r.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
                self._note("piece could not be written: " + (r.stderr or b"").decode("utf-8", "replace")[-200:])
                tmp.unlink(missing_ok=True)
                return False
            tmp.replace(out)
        except Exception as e:  # noqa: BLE001
            self._note(f"piece could not be written: {e}")
            return False
        self.seg_n = num + 1
        self._commit(out, nominal)
        return True

    # ---------------------------------------------------------------- from the live edge
    def _direct(self, urls):
        """One ffmpeg reads the stream's own address and writes the pieces.

        For a platform that cannot be walked from its first fragment. ffmpeg is given the resolved address
        (two of them when the picture and the sound are served apart) and nothing sits in between: no pipe
        from another program whose death would starve it. A read that hangs fails after RW_TIMEOUT instead
        of freezing; what ffmpeg prints is always read, because an unread pipe stops it dead; and when no
        piece has been finished for about three pieces' time, it is ended and started again."""
        urls = list(urls)[:2]
        at = self._start_index(urls[0])
        first = self.seg_n
        lst = self.buf / f"list_{first:06d}.csv"
        cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y"]
        if len(urls) > 1:
            cmd.append("-copyts")        # two addresses rarely open on the same moment: keep their real clocks
        for u in urls:
            if at is not None:
                cmd += ["-live_start_index", str(at)]      # before its input, so it applies to this one
            cmd += ["-rw_timeout", str(RW_TIMEOUT * 1_000_000), "-i", u]
        cmd += ["-c", "copy", "-map", "0:v:0", "-map", "1:a:0" if len(urls) > 1 else "0:a:0?",
                "-f", "segment", "-segment_time", str(SEG_SEC), "-segment_start_number", str(first),
                "-segment_list", str(lst), "-segment_list_type", "csv", "-segment_list_flags", "+live",
                "-segment_format", "mpegts", str(self.buf / "seg_%06d.ts")]
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, creationflags=media.NO_WINDOW)
        self.proc, self.kids = proc, [proc]
        _die_with_us(proc)

        def drain():
            try:
                for raw in iter(proc.stderr.readline, b""):
                    line = raw.decode("utf-8", "replace").strip()
                    if line:
                        self._note(line)
            except (OSError, ValueError):
                pass

        threading.Thread(target=drain, daemon=True, name="ffmpeg-says").start()
        seen, last, longest = 0, time.time(), float(SEG_SEC)
        while True:
            dead = proc.poll() is not None
            rows = _list_rows(lst)
            for name, a, b in rows[seen:]:
                seen += 1
                piece = self.buf / Path(name.replace("\\", "/")).name
                try:
                    if piece.stat().st_size <= 0:
                        continue
                except OSError:
                    continue
                self.seg_n = max(self.seg_n, first + seen)
                self._commit(piece, (b - a) if b > a else SEG_SEC)
                last, longest = time.time(), max(longest, b - a)
            if dead:
                break
            if self.stop_flag.is_set():
                proc.terminate()
                break
            limit = 45.0 if not seen else min(90.0, max(3.0 * SEG_SEC, 3.0 * longest))
            if time.time() - last > limit:
                self._note(f"no finished piece for {limit:.0f}s; starting the connection again")
                proc.kill()
                break
            time.sleep(0.5)
        try:
            proc.wait(timeout=10)
        except Exception:  # noqa: BLE001
            pass
        self.seg_n = max(self.seg_n, first + seen + 1)   # the piece that was open when it stopped is not reused

    # ---------------------------------------------------------------- finished pieces
    def _piece_audio(self, piece):
        """One finished piece turned into the mono 16 kHz sound the speech model reads."""
        try:
            out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(piece), "-vn",
                                  "-ac", "1", "-ar", str(SR), "-f", "s16le", "pipe:1"],
                                 capture_output=True, timeout=120, creationflags=media.NO_WINDOW)
            return out.stdout or b""
        except Exception:  # noqa: BLE001
            return b""

    def _commit(self, piece, nominal):
        """Take a finished piece into the recording: its place on the clock, and its sound for the listening.

        The sound that is transcribed is read out of the piece itself, so what is heard and what a clip is
        cut from are the same file and can never drift apart or go missing separately. The recording's clock
        is the length of that sound, added up. A piece with no sound at all counts as silence of its stated
        length, so the picture keeps its place."""
        pcm = self._piece_audio(piece)
        pcm = pcm[: len(pcm) // 2 * 2]
        if not pcm:
            pcm = bytes(int(max(0.0, nominal) * SR) * 2)
        if not pcm:
            return
        dur = len(pcm) / 2 / SR
        with self.lock:
            a = self.seg_clock
            self.segments.append((piece, a, a + dur))
            self.seg_clock = a + dur
            self.pending += pcm
            self.samples += len(pcm) // 2
            self.db_rest += pcm
            while len(self.db_rest) >= SR * 2:           # loudness, one number per second of stream
                x = np.frombuffer(bytes(self.db_rest[: SR * 2]), dtype=np.int16).astype(np.float32) / 32768.0
                self.db.append(float(20 * np.log10(np.sqrt((x ** 2).mean() + 1e-10))))
                del self.db_rest[: SR * 2]
        try:
            with open(self.buf / "index.csv", "a", encoding="utf-8") as f:
                f.write(f"{piece.name},{a:.3f},{a + dur:.3f}\n")
        except OSError:
            pass

    def _scan_segments(self):
        """Throw away the pieces that are no longer needed.

        A piece is only thrown away once the transcript has gone past it. A stream that was already
        running when recording began arrives far faster than it can be listened to, and deleting by age
        alone would lose the first minutes before the AI ever saw them. A hard ceiling stops a very long
        catch-up from filling the disk."""
        with self.lock:
            lag = self.settings["buffer_min"] * 60
            keep_from = min(self.seg_clock - lag, self.t_done - lag)
            # ...nor before the AI has read it: the next check starts a little before where the last one stopped,
            # and one that is running may still choose a moment from anywhere in its stretch
            # (but never more than a check can reach back, so an AI that is not answering cannot fill the disk)
            reach = self.t_done - 2 * CATCHUP_AI - 150
            keep_from = min(keep_from, max(self.judged_to - 90 - PAD - 30, reach))
            if self.ai_busy:
                keep_from = min(keep_from, max(self.reading_from - PAD - 30, reach))
            # ...nor while a clip that needs it is still waiting its turn to be made. A stream being caught up
            # on is listened to thirty times faster than it played, so clips are chosen far faster than they can
            # be rendered; on the first whole-stream run ten of forty-seven clips found their pieces already
            # gone ("That part of the stream is no longer in the buffer").
            waiting = [c.get("start", 0.0) for c in self.job["clips"]
                       if c.get("status") in ("queued", "rendering") and not c.get("src")]
            if waiting:
                keep_from = min(keep_from, min(waiting) - PAD - 30)
            keep_from = max(keep_from, self.seg_clock - CATCHUP_KEEP)
            while self.segments and self.segments[0][2] < keep_from:
                self.segments.pop(0)[0].unlink(missing_ok=True)

    def _behind(self):
        """Seconds between what has been listened to and what the streamer is doing right now."""
        if self.mode == "start" and self.head >= 0:
            live_now = (self.head + 1 - self.frag0) * self.frag_td
            return max(0.0, live_now - self.t_done)
        return max(0.0, self.seg_clock - self.t_done)

    # ---------------------------------------------------------------- chat (Twitch only)
    def _chat(self, channel):
        while not self.stop_flag.is_set() and not self.ended:
            try:
                raw = socket.create_connection(("irc.chat.twitch.tv", 6697), timeout=20)
                s = ssl.create_default_context().wrap_socket(raw, server_hostname="irc.chat.twitch.tv")
                s.sendall(f"NICK justinfan{int(time.time()) % 90000 + 10000}\r\nJOIN #{channel}\r\n".encode())
                s.settimeout(30)
                rest = b""
                self.chat_on = True
                while not self.stop_flag.is_set() and not self.ended:
                    try:
                        data = s.recv(8192)
                    except socket.timeout:
                        continue
                    if not data:
                        break
                    *lines, rest = (rest + data).split(b"\r\n")
                    for line in lines:
                        if line.startswith(b"PING"):
                            s.sendall(b"PONG :tmi.twitch.tv\r\n")
                        elif b" PRIVMSG #" in line:
                            with self.lock:
                                second = int(self.samples / SR)
                                self.chat[second] += 1
                                self.chat_total += 1
                                # how many different people, not how many messages: a wave of the same
                                # emotes is not a crowd getting excited
                                who = _NICK.findall(line.decode("utf-8", "replace"))
                                if who:
                                    self.chat_users.setdefault(second, set()).add(who[0].lower())
                                    self.chat_kept = _trim_names(self.chat_users, second, self.chat_kept)
                s.close()
            except Exception:  # noqa: BLE001
                pass
            self.chat_on = False
            self.stop_flag.wait(5)

    def _chat_spike(self, s, e):
        """True if chat was at least 3x busier than usual during (and just after) these seconds.

        The crowd is counted as people, not messages: ten people saying "GG" is a reaction, one
        person saying "GG" ten times is a bot."""
        elapsed = self.samples / SR
        if not self.chat_total or elapsed < 60:
            return False
        avg = self.chat_total / elapsed
        a, b = int(s), int(e) + 6
        rate = sum(self.chat.get(t, 0) for t in range(a, b + 1)) / (b - a + 1)
        if rate <= max(3 * avg, 1.0):
            return False
        people = self.chat_people()
        if not people:
            return True
        p_avg = sum(len(v) for v in people.values()) / max(1, len(people))
        p_rate = sum(len(people.get(t, ())) for t in range(a, b + 1)) / (b - a + 1)
        return p_rate >= max(2.0, 1.5 * p_avg)

    def chat_people(self):
        """Second -> how many different people were talking, where that is known.

        A copy is taken under the lock: the chat reader thread adds to it as it goes."""
        with self.lock:
            return {t: set(names) for t, names in self.chat_users.items()}

    # ---------------------------------------------------------------- analysis
    def _hear(self, audio, cuts):
        """The words of each stretch of `audio`, in order, on that audio's own clock. A speech service is
        sent the stretches at the same time; the model on this machine takes them one after another."""
        out, errs = [None] * len(cuts), []

        def one(i, a, b):
            try:
                ws = transcribe.transcribe(audio[a:b], quiet_ok=True)
                for w in ws:
                    w["s"], w["e"] = w["s"] + a / SR, w["e"] + a / SR
                out[i] = ws
            except Exception as e:  # noqa: BLE001 - raised again below, on the thread that asked
                errs.append(e)

        if len(cuts) > 1 and transcribe.cloud():
            ts = [threading.Thread(target=ctx.bind(one), args=(i, a, b), daemon=True) for i, (a, b) in enumerate(cuts)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
        else:
            for i, (a, b) in enumerate(cuts):
                one(i, a, b)
        if errs:
            raise errs[0]
        return [w for ws in out for w in (ws or [])]

    def _transcribe_step(self):
        with self.lock:
            n = len(self.pending) // 2
            hurry = self.ended or bool(self.manual)
            if n < (SR if hurry else SR * 7):   # about every 7 s, so "what was just said" really is live
                return False
            # While a stream that was already running is caught up on, the AI must still read all of it:
            # the listening waits rather than run far past the part the AI is on.
            if self.ai_busy and self.t_done - self.judged_to > CATCHUP_AI and not hurry:
                return False
            backlog = n > SR * 90               # a minute and a half waiting is a backlog, not live speech
            take = min(n, SR * (100 if backlog else 30))
            audio = np.frombuffer(bytes(self.pending[: take * 2]), dtype=np.int16)
            base = self.pending_base
        if backlog:
            # Catching up: long stretches, each cut at a quiet moment, three at a time. Every one of the
            # three ends at a quiet moment because the audio taken is longer than three of them can be.
            cuts = []
            for a, b in transcribe._chunks(audio, 20.0, 29.0):
                cuts.append((a, b))
                if len(cuts) == 3:
                    break
            cut = cuts[-1][1]
            words = self._hear(audio, cuts)
        else:
            cut = take
            if not hurry or take > SR * 24:
                # cut at the quietest moment between 4 and 6.5 s, so no word is split; the rest waits for the next pass
                _, cut = next(transcribe._chunks(audio, 4.0, 6.5))
            words = transcribe.transcribe(audio[:cut], quiet_ok=True)
        off = base / SR
        for w in words:
            w["s"], w["e"] = round(w["s"] + off, 2), round(w["e"] + off, 2)
        with self.lock:
            del self.pending[: cut * 2]
            self.pending_base += cut
            self.words += words
            self.t_done = self.pending_base / SR
        self._triggers(words)
        tmp = self.dir / "words.json.tmp"       # written beside it and swapped in, so a crash cannot leave half a file
        tmp.write_text(json.dumps(self.words), encoding="utf-8")
        tmp.replace(self.dir / "words.json")
        return True

    AUTO_BEFORE, AUTO_AFTER, AUTO_GAP = 30, 20, 60   # seconds of stream sent around a jump; least time between jumps
    JUMP = 0.6                                        # 60% louder or busier than the last three minutes

    def _watch_spikes(self):
        """Always on. Keep a running average of loudness and chat over the last three minutes (leaving out the
        last few seconds), and mark a moment when the last five seconds jump a set percentage above it. Nothing is
        sent yet: the AI gets that moment once its transcript is ready, with the half minute before it."""
        if self.spike:
            return                       # one jump at a time: this one is still waiting for its transcript
        with self.lock:
            # Looked at second by second, up to just past what has been listened to. A stream being caught
            # up on arrives minutes at a time, and looking only at its newest seconds would miss the rest.
            limit = min(len(self.db), int(self.t_done) + 12)
        if limit < 60:
            self.base = {"warming": True}
            return
        for n in range(max(self.spike_pos + 1, 60), limit + 1):
            self.spike_pos = n
            self._spike_at(n)
            if self.spike:
                break

    def _spike_at(self, n):
        """Is second `n` of the stream a jump over the three minutes before it?"""
        with self.lock:
            db = np.array(self.db[max(0, n - 190):n], dtype=np.float32)
            people = self.chat_people()
            if people:
                chat = [len(people.get(t, ())) for t in range(max(0, n - 190), n)]
            else:
                chat = [self.chat.get(t, 0) for t in range(max(0, n - 190), n)] if (self.chat_on or self.chat_total) else None
        amp = 10 ** (db / 20)                       # loudness as plain level, so a percentage means something
        base, cur = float(amp[:-10].mean()), float(amp[-5:].mean())
        loud_jump = cur / max(base, 1e-6) - 1
        pct = self.JUMP
        why = []
        if loud_jump >= pct:
            why.append(f"loudness +{round(loud_jump * 100)}%")
        chat_base = chat_now = None
        if chat is not None:
            chat_base = sum(chat[:-10]) / max(1, len(chat) - 10)
            chat_now = sum(chat[-8:]) / 8          # chat is bursty, so look at a slightly longer stretch
            if chat_now >= max(1.5, chat_base * (1 + pct)):
                why.append(f"chat +{round((chat_now / max(chat_base, 0.01) - 1) * 100)}%")
        self.base = {"loud_db": round(20 * np.log10(max(base, 1e-6)), 1), "loud_now": round(loud_jump * 100),
                     "chat": round(chat_base, 2) if chat_base is not None else None,
                     "chat_now": round(chat_now, 2) if chat_now is not None else None, "pct": round(pct * 100)}
        if why and not self.spike and n - self.last_spike >= self.AUTO_GAP:
            self.spike = {"t": float(n - 3), "why": ", ".join(why)}
            self.last_spike = n
            self.spikes += 1

    def _frame_at(self, t):
        """Which buffer piece holds second `t` of the recording, and where in it: (absolute path, second in the
        piece), or None once the piece is gone. The judge takes its frames from here."""
        with self.lock:
            for path, a, b in self.segments:
                if a <= t < b:
                    return (str(Path(path).resolve()), t - a) if Path(path).exists() else None
        return None

    def _story_step(self, upto, out):
        """Read the newest part of the stream into the story (studio/judge_story.py), on its own thread while the
        judge works. Only the part since the story was last written is read, at most fifteen minutes of it."""
        from . import judge_story
        try:
            story = self.job.get("story") or judge_story.empty()
            a = max(float(story.get("upto") or 0.0), upto - 900.0)
            words = [w for w in list(self.words) if a <= w["s"] < upto]
            if len(words) < 20:
                return
            usage.set_context(self.job["creator"], self.job["title"] or "Live stream")
            z = brain.loud_zscore(np.array(self.db, dtype=np.float32))
            new, spent = judge_story.advance(story, words, a, upto, self.job["title"], self.job["uploader"],
                                             self._game(), config.LIVE_AI_TIMEOUT, live=True, z=z)
            out.update(story=new, tokens=spent)
        except Exception:  # noqa: BLE001 - the story is read again with the next check
            pass

    def _ai_check(self, window=None, why=None):
        """Ask the judge (studio/judge.py) about a stretch of the stream.

        A reader works out who is talking and what is going on, with the story of the stream so far in front
        of it; three scouts read the stretch; a few frames of every find are looked at; and critics score
        every find the way a stranger scrolling past would, with the words, the loudness, the chat and the
        picture in front of them. A clip is made when its score reaches the creator's bar; with "both" chosen in
        Setup the critics must also have seen a real reaction, not just good words. While the judge works, the
        story is brought up to date on a thread of its own, and saved in the job so a restart keeps it."""
        from . import judge, judge_look, judge_story
        st = self.settings
        every = int(st.get("ai_every_min", 3)) or 3
        if window:                    # just the stretch around a jump, or around someone saying "clip"
            ws, now = max(0.0, window[0]), window[1]
        else:
            now = self.t_done
            ws = max(0.0, now - max(every, 3) * 60 - 90)  # each check overlaps the last by 90 s, so nothing falls between
            # ...and starts no later than where the last one stopped, so a stream being caught up on, which
            # is listened to far faster than it was played, is still read from end to end
            ws = max(0.0, min(ws, self.judged_to - 90), now - 2 * CATCHUP_AI)
        read_before = self.judged_to          # put back if the AI does not answer, so this stretch is read again
        if not window:
            self.judged_to = now
        self.reading_from = ws                # pieces from here on are kept while this check runs
        self.last_check = self.t_done
        win = [w for w in self.words if ws <= w["s"] <= now]
        # "This hour" and "for a while" are counted on the stream's clock, not the wall's: an hour of stream
        # that is caught up on in two minutes is still an hour of stream.
        recent = [c for c in self.job["clips"] if c.get("score", 0) > 0 and now - c.get("start", 0) < 3600]
        last_clip = max((c.get("end", 0) for c in self.job["clips"]), default=0.0)
        must = st["must_clip_min"] > 0 and now - last_clip >= st["must_clip_min"] * 60
        verdict = {"t": round(now), "transcript": None, "reaction": None, "trigger": why}
        if len(win) < 8:
            self.skipped += 1
            return self._verdict(verdict, "Skipped: nobody talking")
        if len(self.job["clips"]) >= MAX_LIVE_CLIPS:
            self.skipped += 1
            return self._verdict(verdict, f"Skipped: this recording has made its {MAX_LIVE_CLIPS} clips")
        if len(recent) >= st["live_per_hour"] and not must:
            self.skipped += 1
            return self._verdict(verdict, f"Skipped: {st['live_per_hour']} clips this hour already")
        usage.set_context(self.job["creator"], self.job["title"] or "Live stream")
        z = brain.loud_zscore(np.array(self.db, dtype=np.float32))
        has_chat = bool(self.chat_on or self.chat_total)
        counts = (lambda a, b: sum(self.chat.get(t, 0) for t in range(int(a), int(b)))) if has_chat else None
        want = 1 if every <= 2 else 2
        story = self.job.get("story") or {}
        # the story moves on only with the regular checks, which read the whole transcript in order
        told, keeper = {}, None
        if not window and now - float(story.get("upto") or 0.0) >= 60:
            keeper = threading.Thread(target=ctx.bind(self._story_step), args=(now, told), daemon=True,
                                      name="story")
            keeper.start()
        done = {}
        try:
            cands, tok, _model = judge.pick(
                win, z, 0.0, chat=self._chat_spike if has_chat else None, chat_counts=counts, start=ws, end=now,
                title=self.job["title"], uploader=self.job["uploader"], min_len=st["min_len"], max_len=st["max_len"],
                existing=self.job["clips"], n=want, must=must, game=self._game(), timeout=config.LIVE_AI_TIMEOUT,
                hook_words=jobs._hook_words(self.job), live=True, focus=st.get("clip_focus") or "",
                story=judge_story.brief(story, ws, now) if story else "", frames=self._frame_at,
                made=[c for c in self.job["clips"] if c.get("hook")][-14:], creator=self.job.get("creator"),
                info=done)
        except Exception as e:  # noqa: BLE001
            self.job["ai"]["last_error"] = str(e)[-200:]
            # never further back than twenty minutes, so an AI that is down for an hour is not owed the hour
            self.judged_to = max(read_before, now - 2 * CATCHUP_AI)
            return self._verdict(verdict, "AI error: " + str(e)[-80:])
        finally:
            if keeper:
                keeper.join(config.LIVE_AI_TIMEOUT + 10)
                if told.get("story"):
                    self.job["story"] = judge_story.short(told["story"])
                    self.tokens += told.get("tokens", 0)
                    self.checks += 1
        self.checks += int(done.get("calls") or 6)     # a reader, three scouts, two critics, sometimes a third
        self.tokens += tok
        if done.get("look") and done["look"] != "vision":
            self.job["ai"]["note"] = judge_look.note(done["look"])
        best = cands[0] if cands else None
        verdict["transcript"] = best["score"] if best else 0
        verdict["reaction"] = (best.get("rubric") or {}).get("emotion", 0) * 10 if best else None
        bar = 40 if must else st["min_score"]
        keep = [c for c in cands if c["score"] >= bar]
        if not keep:
            if best:
                self.rejected += 1
                return self._verdict(verdict, f"Not clipped: best moment scored {best['score']}, the bar is {bar}"
                                              f" ({(best.get('reason') or '')[:70]})")
            return self._verdict(verdict, "Nothing worth clipping in this stretch")
        added = 0
        for c in keep:
            marks = c.get("rubric") or {}
            reacted = marks.get("emotion", 0) >= 5
            ok = reacted or st["decide_mode"] == "either" or not marks or (must and added == 0)
            if not ok:
                self.rejected += 1
                self._verdict(verdict, "Good words but nobody reacted, not clipped")
                continue
            if any(abs(c["start"] - k["start"]) < st["min_gap_min"] * 60 for k in self.job["clips"]):
                self._verdict(verdict, "Too close to the last clip")
                continue
            how = ("Forced: no clip for a while" if must and c["score"] < st["min_score"] else
                   "More than one scout found it and the critics agreed" if marks.get("scouts", 1) > 1 else
                   "The critics agreed")
            c["judges"] = {"words": c["score"], "reaction": marks.get("emotion", 0) * 10 or None, "why": how}
            c.pop("screen", None)     # what was on screen served the judges; the clip does not keep it
            self._add_clip(c)
            self._verdict(verdict, f"Clipped ({c['score']}): {(c.get('reason') or how)[:80]}")
            added += 1
            must = False
            if added >= want:
                break

    def _verdict(self, v, result):
        self.verdicts.append(dict(v, result=result))
        del self.verdicts[:-6]

    CLIP_WORDS = re.compile(r"\bclip(\s+(it|that|this))?\b", re.I)
    SAID_BEFORE, SAID_AFTER, SAID_GAP = 60, 15, 45

    def _triggers(self, new_words):
        """Built in: when someone says "clip" ("clip it", "clip that"), the AI looks at that moment as soon as its
        transcript is ready; people say it right after something worth clipping. Then the creator's own trigger
        phrases from Setup, which clip straight away with no AI check."""
        for w in new_words or []:
            if self.CLIP_WORDS.search(re.sub(r"[^a-z' ]", "", w["w"].lower())) and w["s"] - self.last_said > self.SAID_GAP \
                    and not self.said:
                self.said = {"t": w["s"], "why": 'Someone said "clip"'}
                self.last_said = w["s"]
        phrases = [p.strip().lower() for p in self.settings.get("trigger_words", "").split(",") if p.strip()]
        if not phrases or not new_words:
            return
        key = [re.sub(r"[^a-z0-9']", "", w["w"].lower()) for w in new_words]
        for p in phrases:
            parts = [re.sub(r"[^a-z0-9']", "", x) for x in p.split()]
            for i in range(len(key) - len(parts) + 1):
                if key[i:i + len(parts)] == parts:
                    t = new_words[i]["s"]
                    if t - self.last_trigger > 45:
                        self.last_trigger = t
                        self.manual.append({"start": max(0.0, t - 30), "end": t + 2, "why": f'Someone said "{p}"'})

    def _manual_step(self):
        for req in [m for m in self.manual if m["end"] <= self.t_done or self.ended]:
            text = " ".join(w["w"] for w in self.words if req["start"] <= w["s"] <= req["end"])
            usage.set_context(self.job["creator"], self.job["title"] or "Live stream")
            try:
                c = brain.describe(text, self.job["title"], self.job["uploader"], game=self._game(),
                                   timeout=config.LIVE_AI_TIMEOUT, hook_words=jobs._hook_words(self.job))
            except Exception as e:  # noqa: BLE001
                # Someone asked for this clip by hand. A slow or broken AI costs it its hook, not the clip.
                self.job["ai"]["last_error"] = str(e)[-200:]
                c = {"score": 0, "category": "other", "hook": "", "title": self.job["title"],
                     "description": "", "hashtags": [], "highlight_words": []}
            self.manual.remove(req)
            c.update(start=round(req["start"], 2), end=round(min(req["end"], self.samples / SR), 2), score=0)
            if req.get("why"):
                c["reason"] = req["why"]
            self._add_clip(c)

    def _add_clip(self, c):
        self.n += 1
        c.update(id=f"clip{self.n:03d}", style=self.settings["style"], layout=self.settings["layout"],
                 captions=self.job["options"].get("captions", True), status="queued", version=0, made_at=time.time())
        with self.lock:
            self.job["clips"].append(c)
        jobs.save(self.job)
        jobs.submit_live(lambda: self._render(c))

    def _render(self, clip):
        """Runs on the render worker: copy the needed buffer pieces, then make the clip."""
        deadline = time.time() + 45
        while time.time() < deadline:
            self._scan_segments()
            if self.ended or (self.segments and self.segments[-1][2] >= clip["end"] + 1):
                break
            time.sleep(1)
        with self.lock:
            segs = [s for s in self.segments if s[2] > clip["start"] - PAD and s[1] < clip["end"] + PAD and s[0].exists()]
        if not segs or segs[0][1] > clip["start"] + 2:
            clip.update(status="error", error="That part of the stream is no longer in the buffer.")
            jobs.save(self.job)
            return
        if "width" not in self.job:
            meta = media.probe(segs[0][0])
            self.job.update(width=meta["width"], height=meta["height"])
        # The pieces carry one continuous clock, so they are simply written one after another and the result
        # is a whole stretch of stream. ffmpeg then rewrites it once, without re-encoding, into the clip's source.
        joined = self.dir / "clips" / f"{clip['id']}.join.ts"
        src = (self.dir / "clips" / f"{clip['id']}.src.ts").resolve()
        try:
            with open(joined, "wb") as out:
                for piece in segs:
                    out.write(piece[0].read_bytes())
            media.run(["ffmpeg", "-y", "-v", "error", "-i", str(joined.resolve()), "-map", "0:v:0", "-map", "0:a:0?",
                       "-c", "copy", str(src)])
        except Exception as e:  # noqa: BLE001
            clip.update(status="error", error=media_safe(e))
            jobs.save(self.job)
            return
        finally:
            joined.unlink(missing_ok=True)
        # The layouts that show the streamer need to know where the webcam is in THIS clip.
        if clip.get("layout") in ("gameplay", "stack"):
            box = self._webcam_for(src)
            if box:
                clip["facecam"] = box
        # The words were heard in these very pieces, so the clip's source starts exactly where its first
        # piece sits on the transcript clock. There is no second clock to line up.
        offset, dur = segs[0][1], segs[-1][2] - segs[0][1]
        clip.update(src=str(src), src_offset=round(offset, 2), src_end=round(offset + dur, 2))
        clip["start"] = max(clip["start"], clip["src_offset"])
        clip["end"] = min(clip["end"], clip["src_end"])
        jobs.render_one(self.job, clip, list(self.words))

    def clip_last(self, seconds):
        end = self.samples / SR
        if end < 5:
            raise ValueError("Nothing has been recorded yet.")
        self.manual.append({"start": max(0.0, end - seconds), "end": end})

    def _publish(self):
        elapsed = self.samples / SR
        lines = brain.make_lines([w for w in self.words if w["s"] >= self.t_done - 45])[-5:]
        with self.lock:
            sec = int(elapsed)
            self.job.update(
                duration=elapsed,
                # how far the listening has got, so the card shows real progress rather than a spinner while
                # a stream that was already running is caught up on (`jobs.public` reads this field)
                heard_to=round(min(self.t_done, elapsed), 1),
                progress=round(min(1.0, self.t_done / elapsed), 4) if elapsed > 0 else 0.0,
                # the stream fragment the listening has reached, so a restart carries on from here
                frag_done=(self.frag0 + int(self.t_done / self.frag_td)) if self.mode == "start" else None,
                live={"elapsed": round(elapsed), "buffer_sec": round(self.segments[-1][2] - self.segments[0][1]) if self.segments else 0,
                      "lines": [l["text"] for l in lines], "level": [round(x) for x in self.db[-60:]],
                      "chat": [self.chat.get(t, 0) for t in range(max(0, sec - 60), sec)] if self.chat_on or self.chat_total else None,
                      "checks": self.checks, "skipped": self.skipped, "tokens": self.tokens, "words": len(self.words),
                      "rejected": self.rejected, "verdicts": list(reversed(self.verdicts)),
                      "every_min": int(self.settings.get("ai_every_min", 3)) or 3,
                      "auto": None,
                      "pending_clips": len(self.manual)})
        jobs.save(self.job)

    def _show_catchup(self):
        """Say on the card how far behind live the recording still is while it catches up.

        A stream that was already running is recorded from its first minute, so for a while the recording
        is behind the live edge and the page would otherwise still say plain "Recording"."""
        behind = self.behind = self._behind()
        was = self.job.get("behind") or 0
        if abs(behind - was) < 5 and self.job.get("stage", "").startswith("Catching up") == (behind > 90):
            return
        self.job["behind"] = round(behind, 1)
        if self.job.get("status") == "live" and not self.user_stopped:
            if behind > 90:
                m = round(behind / 60)
                far = f"{m // 60} h {m % 60} min" if m >= 60 else f"{m} min"
                self.job["stage"] = f"Catching up: {far} behind live"
            elif str(self.job.get("stage", "")).startswith("Catching up"):
                self.job["stage"] = "Recording"
        jobs.save(self.job)

    def _analyze(self):
        cid = self.job["creator"]
        started = False
        trouble = 0                   # listening steps that failed in a row
        while True:
            busy = False
            try:
                if not self.user_stopped and not self.ended:      # a recording cannot run for ever
                    if time.time() - self.started_at > config.MAX_LIVE_HOURS * 3600:
                        self.stop(f"Stopped after {config.MAX_LIVE_HOURS:g} hours, the longest one recording can run")
                self._scan_segments()
                busy = self._transcribe_step()
                if not started and self.samples:
                    started = True
                    self.job.update(status="live", stage="Recording")
                    creators.log(cid, f"Recording started: {self.job['title']}")
                if started and not self.user_stopped:
                    self._show_catchup()
                self._manual_step()
                # Three ways the AI is asked: on the creator's schedule (every N minutes), and always, when the
                # stream suddenly gets louder or chat busier, or when someone says "clip".
                every = int(self.settings.get("ai_every_min", 3)) or 3
                self._watch_spikes()
                sp, said = self.spike, self.said
                # A moment waiting for the AI is only let go of once the AI has really been asked about it:
                # while it is busy with something else the moment waits its turn instead of being dropped.
                # And while a stream is being caught up on, moments arrive one after another; reading the
                # whole transcript must not be starved by them, so it goes first once it has fallen behind.
                overdue = self.t_done - self.judged_to > max(CATCHUP_AI / 2, every * 60 + 120)
                if self.user_stopped:
                    pass
                elif overdue and not self.ai_busy:
                    self._ask_ai()
                elif said and (self.t_done >= said["t"] + self.SAID_AFTER or (self.ended and not busy)):
                    if self._ask_ai((said["t"] - self.SAID_BEFORE, said["t"] + self.SAID_AFTER), said["why"]):
                        self.said = None
                elif sp and (self.t_done >= sp["t"] + self.AUTO_AFTER or (self.ended and not busy)):
                    if self._ask_ai((sp["t"] - self.AUTO_BEFORE, sp["t"] + self.AUTO_AFTER), "Jump: " + sp["why"]):
                        self.spike = None
                elif self.t_done - self.last_check >= every * 60 or (self.ended and not busy and self.t_done > self.last_check):
                    self._ask_ai()
                self._publish()
                trouble = 0
            except Exception as e:  # noqa: BLE001
                self.job["ai"]["last_error"] = str(e)[-200:]
                trouble += 1
                if trouble in (1, 5) or trouble % 30 == 0:
                    self._note(f"listening step failed ({trouble} in a row): {str(e)[-300:]}")
                if not self.user_stopped and not self.ended:
                    self.stop_flag.wait(min(30, 2 * trouble))
            # Leaving here must not happen while an AI check is still running: it may still be adding a
            # clip, and cleanup() deletes the buffer that clip is cut from. That is true after a stop as
            # well as at the end of a stream, so both wait for it. Stopping is still instant on the page:
            # stop() has already written the status.
            if ((self.user_stopped and not self.manual and not self.ai_busy)
                    or (self.ended and not busy and not self.ai_busy
                        and len(self.pending) < SR * 2 and not self.manual)):
                break
            if not busy:
                time.sleep(2)
        failed = bool(self.job.get("error")) and not started
        self.job.update(status="error" if failed else "done", stage="Could not record" if failed else self.end_note)
        jobs.save(self.job)
        creators.log(cid, f"Recording finished ({self.end_note.lower()}): {len(self.job['clips'])} clips, "
                          f"{round(self.samples / SR / 60)} min" if not failed else f"Recording failed: {self.job['error']}")

        if failed:
            alerts.notify(f"recording failed for {self.job['source']['name']}: {self.job['error']}")
        else:
            alerts.notify(f"recording finished for {self.job['source']['name']}: {len(self.job['clips'])} clips, "
                          f"{round(self.samples / SR / 60)} min.")

        def cleanup():  # runs after any queued renders, then frees the buffer
            for f in self.buf.glob("*"):
                f.unlink(missing_ok=True)
            self.finished = True
            SESSIONS.pop(self.job["id"], None)

        jobs.submit_live(cleanup)


def recover(job):
    """After a restart: finish the clips of an interrupted recording from the stream pieces still on disk."""
    c = creators.get(job["creator"]) or dict(creators.DEFAULTS)
    s = Session(job, c)
    s.ended, s.end_note = True, "Recording stopped when the studio closed"
    with s.lock:
        for name, a, b in _list_rows(s.buf / "index.csv"):
            if (s.buf / name).exists():
                s.segments.append((s.buf / name, a, b))
                s.seg_clock = b
    try:
        s.words = json.loads((s.dir / "words.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        s.words = []
    s.n = len(job["clips"])
    todo = [k for k in job["clips"] if k.get("status") == "queued"]
    for k in todo:
        jobs.submit_live(lambda k=k: s._render(k))

    def cleanup():
        for f in s.buf.glob("*"):
            f.unlink(missing_ok=True)
        job.pop("recover", None)
        jobs.save(job)
        creators.log(job["creator"], f"Finished {len(todo)} clip(s) from a recording interrupted by a restart")

    jobs.submit_live(cleanup)


def start_session(creator: dict, url=None, frag_start=0, story=None) -> dict:
    url = normalize(url or creator.get("channel") or "")
    if not re.match(r"^https?://[^/]+\.[^/]+/", url + "/"):
        raise ValueError("Add this creator's channel link first.")
    if active_for(creator["id"]):
        raise ValueError("This creator is already being recorded.")
    if not media.site_allowed(url):
        raise ValueError("Channel links must be from YouTube, Twitch or Kick.")
    if media.is_youtube(url) and media.youtube_paused():
        raise ValueError(media.YT_BLOCKED.replace("download videos", "record YouTube streams")
                         .replace("Upload the video file instead, or use a Twitch or Kick link. YouTube links",
                                  "Twitch and Kick streams still work. YouTube"))
    if len(active_mine()) >= config.MAX_LIVE_PER_USER:
        raise ValueError(f"You're already recording {len(active_mine())} streams, the most this server allows at once. Stop one first.")
    if len(active()) >= config.MAX_LIVE_TOTAL or (active() and load.busy()):
        raise ValueError("PeakCut is recording as many streams as it can right now. Try again in a little while.")
    from . import tools
    if tools.missing():
        raise ValueError(tools.HELP)
    job = jobs.create({"type": "live", "url": url, "name": f"{creator['name']} live"}, {}, enqueue=False,
                      creator=creator["id"], kind="live")
    job.update(status="live", stage="Connecting to the stream")
    if frag_start:
        job["frag_start"] = int(frag_start)     # picked up after a restart: carry on from here, not from the start
    if isinstance(story, dict) and story:
        job["story"] = story                    # ...and with the story of the stream so far, so the judge remembers it
    jobs.save(job)
    Session(job, creator).start()
    return job


def _watch_user(uid):
    """Start recording any of this user's auto-record creators who have gone live."""
    from . import profiles
    with ctx.as_user(uid):
        try:
            todo = [c for c in creators.all_creators() if c["auto_watch"] and c["channel"]]
            if not todo:
                return
        except Exception:  # noqa: BLE001
            return
        for c in todo:
            _watch_one(c)


def check_now(cid):
    """Auto-record was just turned on: look now, on a thread, instead of waiting for the next round."""
    uid = ctx.uid()

    def run():
        from . import profiles
        with ctx.as_user(uid):
            c = creators.get(cid)
            if not c or not c["auto_watch"] or not c["channel"]:
                return
            for url in c.get("channels", {}).values():
                profiles._live.pop(url.rstrip("/").lower(), None)     # a fresh answer, not one from two minutes ago
            _watch_one(c)
            profiles.refresh(cid, force=True)
    threading.Thread(target=run, daemon=True).start()


def _watch_one(c):
    """Start recording this auto-record creator if they are live on any of their channels."""
    from . import profiles
    try:
        if active_for(c["id"]) or len(active_mine()) >= config.MAX_LIVE_PER_USER or len(active()) >= config.MAX_LIVE_TOTAL or (active() and load.busy()):
            return
        # the chosen channel first, then their other platforms
        urls = [c["channel"]] + [u for u in c.get("channels", {}).values() if u != c["channel"]]
        for url in urls:
            # one shared "are they live?" answer per channel, however many people follow it
            if not profiles.live_shared(profiles.platform_of(url), url).get("live"):
                continue
            if media.is_youtube(url):
                # check YouTube will hand over the stream before making a recording that could only fail
                if media.youtube_paused():
                    continue
                try:
                    resolve(normalize(url))
                except NotLive:
                    continue
            start_session(c, url)
            where = creators.platform_key(url).title()
            creators.log(c["id"], f"Went live on {where}: recording started automatically")
            alerts.notify(f"{c['name']} went live on {where}, recording started.")
            break
    except NotLive:
        pass
    except Exception as e:  # noqa: BLE001
        creators.log(c["id"], f"Auto-record check failed: {str(e)[-150:]}")


def watch_loop():
    """Every two minutes, start recording any creator set to auto-record who has gone live. Covers every user,
    several at a time, so the round stays short however many accounts there are."""
    from concurrent.futures import ThreadPoolExecutor
    time.sleep(20)
    pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="watch")
    while True:
        t0 = time.time()
        try:
            list(pool.map(_watch_user, auth.user_ids()))
        except Exception:  # noqa: BLE001
            pass
        time.sleep(max(15, 120 - (time.time() - t0)))


def _restarted(story):
    """The story of a recording, ready for the recording that picks it up after a restart (or None)."""
    try:
        from . import judge_story
        return judge_story.carried(story) if isinstance(story, dict) and story else None
    except Exception:  # noqa: BLE001 - the new recording starts its own story
        return None


def _resume_recordings(paused):
    """Recordings that were running when the server stopped: start recording the same channel again, if the
    stream is still on. Tried for a few minutes, since the server may come back a little before the network."""
    time.sleep(10)
    for _ in range(6):
        left = []
        for uid, cid, url, frag, *rest in paused:
            story = rest[0] if rest else None
            with ctx.as_user(uid):
                try:
                    c = creators.get(cid)
                    if not c or active_for(cid):
                        continue
                    resolve(normalize(url))      # raises NotLive if the stream has ended: no empty recording is made
                    # A recording picked up from a later fragment has its own clock, starting at zero again, so
                    # the story's seconds would point at the wrong moments: it is carried on as words only.
                    start_session(c, url, frag_start=frag or 0, story=_restarted(story))
                    creators.log(cid, "Recording picked up again after a server update")
                except NotLive:
                    continue                  # the stream ended while the server was away
                except Exception:  # noqa: BLE001 - try again shortly
                    left.append((uid, cid, url, frag, story))
        if not left:
            return
        paused = left
        time.sleep(30)


def start():
    paused = []
    # newest first, so a creator with several interrupted recordings is picked up from the latest one
    for j in sorted(jobs.all_jobs(), key=lambda j: str(j.get("id") or ""), reverse=True):
        if j.get("recover"):
            with ctx.as_user(j["user"]):
                recover(j)
        elif j.get("kind") == "live" and j.get("id") not in SESSIONS:
            _sweep(j)            # nothing is recording into it and no clip is waiting on it
        if j.get("was_live") and j.get("creator"):
            paused.append((j["user"], j["creator"], j["source"]["url"], j.get("frag_done"), j.get("story")))
            j.pop("was_live", None)
            jobs.save(j)
    if paused:
        threading.Thread(target=_resume_recordings, args=(paused,), daemon=True).start()
    threading.Thread(target=watch_loop, daemon=True).start()


# ---------------------------------------------------------------- who is live (finding a stream, never recording it)
WATCH_MAX = 40   # creators one watching_now() call may ask the platforms about


def discover(creator: dict) -> dict | None:
    """Is this streamer live right now: {platform, ident, key, live, title, viewers, started, looked_at},
    or None when they are not live or nobody could say.

    The creator is asked for by their platform and handle, which hunt keeps as "twitch:somebody". A
    creator with neither, a platform that cannot be reached and a channel nobody owns all come back
    as None, the same as a streamer who is merely offline: this is a question, not a promise. Never
    raises, so a route can call it without taking the server down."""
    try:
        c = creator or {}
        platform = str(c.get("platform") or "").strip().lower()
        handle = str(c.get("handle") or "").strip()
    except Exception:  # noqa: BLE001 - anything that is not a normal dict is simply not known to be live
        return None
    if not platform or not handle:
        return None
    try:
        from . import hunt
        info = hunt.look(platform, handle)
    except Exception:  # noqa: BLE001 - discovery must never be the reason a page fails
        return None
    if not isinstance(info, dict) or not info.get("live"):
        return None
    return info


def watching_now(creators: list) -> list:
    """The ones of these creators who are live right now, each as {creator, live}.

    At most WATCH_MAX are looked at in one call: a caller with a longer list gets the first 40, in the
    order it gave them. hunt.look keeps every answer for a minute, so a page that asks again straight
    away costs the platforms nothing; nothing here sleeps or waits on anything, and a creator that
    cannot be asked is left out rather than reported. Never raises: a list of the wrong shape is an
    empty answer."""
    try:
        rows = list(creators or [])
    except TypeError:
        return []
    found = []
    for c in rows[:WATCH_MAX]:
        info = discover(c)
        if info:
            found.append({"creator": c, "live": info})
    return found
