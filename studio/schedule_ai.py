"""Write, as text only, the schedule that makes PeakCut run one AI round by itself.

This module never installs anything. It builds the same spec shape `studio/autopilot.py`
builds, and prints the same kind of command text its preview prints, so one reader on the
page serves both. A person copies the text and runs it themselves; that is the whole feature.

`studio/autopilot.py` already owns the older "run the autopilot tick" schedule, with its own
task name and its own crontab marker. This is a second, separate schedule, so both can live
on one machine and removing one never removes the other.
"""

from __future__ import annotations

import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

# 06:00 is chosen because it is early enough that a round has finished before the person
# starts work, and because it sits before the autopilot window of 08:00 to 23:00, so the two
# schedules never ask for the same moment. One time is enough: a round reads the last 28 days
# and the six hour cooldown inside a round is what stops it repeating, not a longer list.
TIMES = ("06:00",)

LABEL = "PeakCutRound"              # the Windows task name, kept apart from PeakCutAutopilot
MARK = "peakcut-round"              # the text that marks our own crontab line, kept apart too
DAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")   # 1 = Monday, as Windows and cron agree
LINUX_PATH = "/usr/local/bin:/usr/bin:/bin"                 # cron runs with a bare environment
LOG_NAME = "schedule-ai.log"                                # our own log, so two schedules never interleave
Times = Union[str, Sequence[str], Dict[str, Any], None]


def spec(user_id: str = "", times: Times = TIMES) -> Dict[str, Any]:
    """Describe the round-by-itself schedule as plain data, without creating or writing anything.

    The keys, and the type of each, are the ones `autopilot.spec` returns, so a reader written
    for one works on the other. `user_id` is the one extra key. It is recorded so the page
    knows whose round this is; it is not baked into the command, because a round reads the
    signed-in owner when it runs.
    """
    try:
        at, days = _times(times)
        argv = _payload(user_id)
        plan: Dict[str, Any] = {
            "ok": True,
            "platform": _platform(),
            "label": LABEL,
            "user_id": str(user_id or ""),
            "days": list(days),
            "times": list(at),
            "argv": list(argv),
            "cmds": [],
            "off": [],
            "file": "",          # this schedule writes no file of its own on any platform
            "body": "",
            "text": "",
            "warn": "",
            "error": "",
        }
        # Same split as autopilot: cmds and off are argv lists for a machine to run, the text
        # is the same thing written out for a person to read and paste.
        plan["cmds"] = _win_argv(argv, at, days)
        plan["off"] = _win_off(at)
        plan["text"] = _paste("#", days, at,
                              cmd_windows(plan) + ["# on a Linux machine instead:"] + cmd_linux(plan))
        plan["warn"] = ("Windows keeps no log of its own, so the log line is part of the command. "
                        "The task name has to match again when you remove it.")
        return plan
    except Exception as exc:   # noqa: BLE001 - a schedule that cannot be described is still a sentence
        return _empty("could not work out a schedule: %s: %s" % (type(exc).__name__, exc))


def cmd_windows(spec: Dict[str, Any]) -> List[str]:
    """Return the schtasks lines for this spec, one command per string, ready to paste.

    One line per run time, because a weekly Windows task holds a single start time. Each
    line first changes into the PeakCut folder, because a scheduled task starts in a Windows
    system folder and `python -c` only imports `studio` from the folder it stands in. The
    whole thing goes through cmd /c, so no quoting rule of schtasks has to be guessed at.
    """
    try:
        times = _at(spec)
        days = _days(spec)
        argv = _argv(spec)
        root = str(_root())
        core = _win_line(argv)
        out: List[str] = []
        for index, when in enumerate(times):
            out.append(_win_line(["schtasks", "/Create", "/TN", _task(index), "/TR",
                                  "cmd /c cd /d " + root + " && " + core,
                                  "/SC", "WEEKLY", "/D", ",".join(days), "/ST", when, "/F"]))
        return out
    except Exception:          # noqa: BLE001
        return []


def cmd_linux(spec: Dict[str, Any]) -> List[str]:
    """Return the cron lines for this spec, one line per run time, ending in our own marker.

    The paths are written in Linux form, because the line runs on a Linux machine. The folder
    is found by asking the standard library where `studio` lives, so this module never has to
    guess where PeakCut was unpacked.
    """
    try:
        times = _at(spec)
        days = _days(spec)
        argv = _at_argv(_argv(spec), "linux")
        dows = ",".join(str(DAYS.index(d) + 1) for d in days)
        core = _sh_line(argv)
        root, folder_note = _linux_root()
        log = _linux_log(root)
        out: List[str] = []
        for when in times:
            out.append("%d %d * * %s cd %s && PATH=%s:$PATH %s >> %s 2>&1 # %s%s"
                       % (int(when[3:]), int(when[:2]), dows, root, LINUX_PATH, core, log, MARK, folder_note))
        return out
    except Exception:          # noqa: BLE001
        return []


def due(spec: Dict[str, Any], now: Optional[float] = None) -> bool:
    """Say whether this spec wants a run at this moment, read on this machine's local clock.

    `now` is a `time.time()` stamp and defaults to right now. A run is due when the minute
    matches one of the spec's times and the weekday matches one of its days. Anything odd in
    the spec answers False, because a schedule that cannot be read must not start work.
    """
    try:
        stamp = time.time() if now is None else float(now)
        clock = time.localtime(stamp)
        if "%02d:%02d" % (clock.tm_hour, clock.tm_min) not in _at(spec):
            return False
        days = _days(spec)
        return bool(days) and DAYS[clock.tm_wday] in days
    except Exception:          # noqa: BLE001
        return False


def note(spec: Dict[str, Any]) -> str:
    """Return one sentence for the page saying what the schedule would do and that nothing is installed."""
    try:
        at = _at(spec)
        days = _days(spec)
        if not at or not days:
            return "There is no schedule to describe yet, and nothing is installed on this machine."
        return ("On %s at %s PeakCut would run one AI round by itself and apply at most two settings, "
                "and nothing is installed on this machine until you say so."
                % (_spoken_days(days), _spoken_times(at)))
    except Exception:          # noqa: BLE001
        return "Nothing is installed on this machine."


def _payload(user_id: str = "") -> List[str]:
    """Return the command a scheduled run should execute, which is one learning round.

    `studio/learn.py` has no `if __name__ == "__main__"` block, so `python -m studio.learn`
    would load the module and exit without running a round. Calling its one public round
    function is the only form that actually runs, and it needs no new file from this module.

    A scheduled task has no signed-in web session, and `learn.run` reads the owner with
    `ctx.uid()`, which raises `NoUser` outside a request. Measured on 2026-11-20: the plain
    `run()` form died with `studio.ctx.NoUser: No signed-in user in this context` on the very
    first tick, so every morning would have failed silently. The payload therefore sets the
    owner before calling `run`. The id is the one the page recorded when it wrote the spec;
    an empty id falls back to `auth.local_user()`, which is the single owner when accounts
    are switched off.

    The code is written with no spaces on purpose. A scheduled task must hand this whole
    line to Windows inside a /TR value that is already quoted, and every inner space would
    need another layer of quotes that cmd and schtasks disagree about.
    """
    who = _owner_expression(str(user_id or "").strip())
    # A scheduled command must be ONE line: a real newline inside /TR breaks both cmd and
    # schtasks. So the work lives in `tick()` in this module and the payload only names it. That
    # also keeps the quoted string short enough to read in a task list, which matters when
    # somebody has to check what they installed a year later.
    code = (
        "__import__('studio.ctx',fromlist=['x']).set_uid(" + who + ")"
        ";__import__('studio.schedule_ai',fromlist=['x']).tick()"
    )
    return [sys.executable or "python", "-c", code]


def tick() -> int:
    """Run one learning round the way a scheduled task does, and return a shell exit code.

    A round refuses politely when it is too soon or when the numbers are not there, with a
    ValueError carrying the sentence a person should read. A scheduled task that grows a
    traceback every morning for a refusal that is the designed answer trains a person to ignore
    the log, so the reason is printed and the run still exits 0. Only a genuine crash exits 1.
    """
    try:
        from . import learn
        got = learn.run()
    except ValueError as e:
        print(str(e) or "A round could not start just now.")
        return 0
    except Exception as e:  # noqa: BLE001 - a scheduled task must not fail silently
        print("The round did not finish: " + str(e)[:300])
        return 1
    changed = [c.get("setting") for c in (got.get("applied") or []) if c.get("ok")]
    print("Round finished. " + ("Changed: " + ", ".join(str(c) for c in changed) if changed
                               else "Nothing was changed."))
    return 0


def _owner_expression(user_id: str) -> str:
    """Return a one-line Python expression that names whose round this is, with no spaces in it.

    A recorded id is used when it looks like one, because with accounts switched on there can be
    several people and the schedule belongs to the one who wrote it. Otherwise the single local
    owner is asked for, which is what a machine with accounts off has. Written without spaces so
    the whole payload survives being quoted once by schtasks or once by a shell.
    """
    if user_id and re.fullmatch(r"[A-Za-z0-9_]{1,40}", user_id):
        return repr(user_id)
    return "__import__('studio.auth',fromlist=['x']).local_user().id"


def _times(times: Times) -> Tuple[List[str], List[str]]:
    """Turn whatever the caller passed into sorted clock times and weekday names, falling back to our default."""
    days = list(DAYS)          # every day: the cooldown inside a round limits it, not the calendar
    raw: Any = times
    if isinstance(times, dict):
        asked = times.get("days")
        if isinstance(asked, str):
            asked = _split(asked)
        if isinstance(asked, (list, tuple)):
            picked = [str(x).strip().upper()[:3] for x in asked]
            picked = list(dict.fromkeys([x for x in picked if x in DAYS]))
            if picked:
                picked.sort(key=DAYS.index)
                days = picked
        raw = []
        for key in ("times", "time", "at", "slots"):
            if key in times:
                raw = times[key]
                break
    if isinstance(raw, str):
        raw = _split(raw)
    elif not isinstance(raw, (list, tuple)):
        raw = []
    at: List[str] = []
    for item in raw:
        got = _clock(item)
        if got and got not in at:
            at.append(got)
    if not at:
        at = list(TIMES)
    at.sort()
    return at, days


def _split(text: str) -> List[str]:
    """Break a hand-written list of times into pieces, on commas, semicolons or spaces."""
    out: List[str] = []
    for chunk in str(text or "").replace(";", ",").replace(" ", ",").split(","):
        piece = chunk.strip()
        if piece:
            out.append(piece)
    return out


def _clock(text: Any) -> str:
    """Return text as a real HH:MM clock time, or an empty string when it is not one."""
    got = str(text or "").strip()
    if len(got) != 5 or got[2] != ":":
        return ""
    if not (got[:2].isdigit() and got[3:].isdigit()):
        return ""
    hour, minute = int(got[:2]), int(got[3:])
    if hour > 23 or minute > 59:
        return ""
    return got


def _at(spec: Any) -> List[str]:
    """Return the clock times out of a spec, as valid times only."""
    if not isinstance(spec, dict):
        return []
    out: List[str] = []
    for item in spec.get("times") or []:
        got = _clock(item)
        if got:
            out.append(got)
    return out


def _days(spec: Any) -> List[str]:
    """Return the weekday names out of a spec, as names we know only."""
    if not isinstance(spec, dict):
        return []
    out: List[str] = []
    for item in spec.get("days") or []:
        name = str(item or "").strip().upper()[:3]
        if name in DAYS and name not in out:
            out.append(name)
    return out


def _argv(spec: Any) -> List[str]:
    """Return the command a spec wants to run, falling back to our own payload so text always prints."""
    if isinstance(spec, dict):
        asked = spec.get("argv")
        if isinstance(asked, (list, tuple)) and asked:
            return [str(x) for x in asked]
    return _payload()


def _win_argv(argv: List[str], at: List[str], days: List[str]) -> List[List[str]]:
    """Return one schtasks argument list per run time, in the form autopilot uses for cmds."""
    root = str(_root())
    out: List[List[str]] = []
    for index, when in enumerate(at):
        out.append(["schtasks", "/Create", "/TN", _task(index),
                    "/TR", "cmd /c cd /d " + root + " && " + _win_line(argv),
                    "/SC", "WEEKLY", "/D", ",".join(days), "/ST", when, "/F"])
    return out


def _win_off(at: List[str]) -> List[List[str]]:
    """Return the schtasks argument lists that delete the tasks this spec would create."""
    return [["schtasks", "/Delete", "/TN", _task(i), "/F"] for i in range(max(1, len(at)))]


def _task(index: int) -> str:
    """Return the task name for the n-th run time, so several times a day never share one name."""
    return LABEL if index == 0 else "%s-%d" % (LABEL, index + 1)


def _paste(comment: str, days: List[str], at: List[str], blocks: Sequence[str]) -> str:
    """Lay the commands out as one block of text, with a plain heading above them."""
    title = "%s PeakCut round, %s at %s" % (comment, ", ".join(days), ", ".join(at))
    out = [title, comment + " Nothing here runs until an operator pastes it.", ""]
    for block in blocks:
        out.append(str(block))
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def _spoken_days(days: List[str]) -> str:
    """Say the days the way a sentence wants them, with "and" before the last one."""
    names = [d.capitalize() for d in days]
    if len(names) <= 1:
        return names[0] if names else "no day"
    return ", ".join(names[:-1]) + " and " + names[-1]


def _spoken_times(at: List[str]) -> str:
    """Say the clock times the way a sentence wants them."""
    return ", ".join(at) if at else "no time"


def _win_line(argv: Sequence[str]) -> str:
    """Quote a command the way Windows expects it, the same call autopilot makes."""
    return subprocess.list2cmdline([str(x) for x in argv])


def _sh_line(argv: Sequence[str]) -> str:
    """Quote a command the way a Unix shell expects it, the same call autopilot makes."""
    return " ".join(shlex.quote(str(x)) for x in argv)


def _platform() -> str:
    """Return windows, macos or linux for this machine, so a spec says which scheduler it describes."""
    asked = (sys.platform or "").lower()
    if asked.startswith(("win", "cygwin", "msys")):
        return "windows"
    if asked.startswith(("mac", "darwin", "osx")):
        return "macos"
    if asked.startswith(("linux", "unix", "bsd", "freebsd", "sunos")):
        return "linux"
    return ""


def _root() -> Path:
    """Return the folder PeakCut runs from, which is where a scheduled command should start."""
    return Path(__file__).resolve().parents[1]


def _linux_root() -> Tuple[str, str]:
    """Return the PeakCut folder in Linux form, and a note to append when that form had to be guessed.

    Found by asking where `studio` was imported from, so nothing is hard-coded. On Windows that
    answer is a drive letter, which is not a path any Linux machine has, so the text says the
    line was written on Windows instead of printing a path that would silently fail there.
    """
    try:
        import studio
        text = Path(getattr(studio, "__file__", "") or "").resolve().parent.parent.as_posix()
    except Exception:          # noqa: BLE001
        text = ""
    if not text:
        return "/opt/peakcut", "  (the folder was not found, so /opt/peakcut is a placeholder)"
    if len(text) > 1 and text[1] == ":":
        return text, "  (written on Windows, so this folder is a Windows path and needs changing)"
    return text, ""


def _linux_log(root: str) -> str:
    """Return the log path a cron line writes to, inside the PeakCut folder so no home folder is assumed."""
    return shlex.quote(str(root).rstrip("/") + "/data/" + LOG_NAME)


def _at_argv(argv: Sequence[str], platform: str) -> List[str]:
    """Return the command with the interpreter swapped for the one that platform would use.

    The interpreter this module runs under is the Windows one when read on Windows, and that
    path is meaningless in a cron line, so the Linux form says `python3` and lets the PATH in
    the line find it. Everything else in the command is already the same on both.
    """
    out = [str(x) for x in argv]
    if platform == "linux" and out and _is_python(out[0]):
        out[0] = "python3"
    return out


def _is_python(text: str) -> bool:
    """Say whether a path looks like a Python interpreter, so only that one is rewritten."""
    name = str(text or "").replace("\\", "/").rstrip("/").split("/")[-1].lower()
    return name.startswith("python")


def _log() -> Path:
    """Return the folder and file a scheduled run writes its output to, for callers that want the real path."""
    try:
        from . import config
        return Path(config.DATA_DIR) / LOG_NAME
    except Exception:          # noqa: BLE001 - the text must still print when settings cannot be read
        return _root() / LOG_NAME


def _empty(error: str) -> Dict[str, Any]:
    """Return the empty spec shape, used whenever a schedule cannot be worked out."""
    text = str(error or "cannot build a schedule here")
    return {
        "ok": False,
        "platform": "",
        "label": LABEL,
        "user_id": "",
        "days": [],
        "times": [],
        "argv": [],
        "cmds": [],
        "off": [],
        "file": "",
        "body": "",
        "text": "# " + text + "\n",
        "warn": "",
        "error": text,
    }
