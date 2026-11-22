"""Build the schedule text that makes PeakCut run autopilot on a timer, and only ever install it when a human confirms."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from . import config


DAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")   # 1 = Monday, on every platform we write for
LABEL = "PeakCutAutopilot"                                  # the name of the job we create
CRON_MARK = "peakcut-autopilot"                             # the text that marks our own crontab line
DEFAULT_DAYS = ["MON", "WED", "FRI"]
DEFAULT_TIME = "09:00"
WIN_FROM = "08:00"                                          # first moment of the day autopilot may run
WIN_TO = "23:00"                                            # last moment of the day autopilot may run
MAC_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
LINUX_PATH = "/usr/local/bin:/usr/bin:/bin"
TIMEOUT = 30                                                # seconds any scheduler command may take
MAX_SLOTS = 96                                              # more runs than this in one day is a mistake
Times = Union[str, Sequence[str], Dict[str, Any], None]


def spec(platform: str, times: Times = None, command: str = "") -> Dict[str, Any]:
    """Describe the schedule PeakCut would create on one platform, without creating it."""
    return _plan(platform, times, command)


def preview(platform: str, times: Times = None, command: str = "") -> str:
    """Return the exact text an operator reads and pastes to put autopilot on a timer."""
    plan = _plan(platform, times, command)
    if not plan.get("ok"):
        return "# " + str(plan.get("error") or "cannot build a schedule here") + "\n"
    return str(plan["text"])


def install(platform: str, times: Times = None, command: str = "", confirm: bool = False) -> Dict[str, Any]:
    """Create the schedule for real, but only when the caller passes confirm=True."""
    plan = _plan(platform, times, command)
    if not plan.get("ok"):
        return plan
    if not confirm:
        return {
            "ok": False,
            "done": False,
            "platform": plan["platform"],
            "error": "install needs confirm=True, so nothing was changed on this machine.",
            "text": plan["text"],
            "cmds": plan["cmds"],
            "off": plan["off"],
            "ran": [],
        }
    wrote = ""
    if plan.get("file") and plan.get("body"):
        wrote = _write(plan["file"], str(plan["body"]))
        if wrote:
            return {"ok": False, "done": False, "platform": plan["platform"], "error": wrote,
                    "text": plan["text"], "ran": []}
    ran: List[Dict[str, Any]] = []
    for argv in plan["cmds"]:
        got = _run(argv)
        ran.append({"cmd": _shown(argv, plan["platform"]), "ok": got["ok"],
                    "code": got.get("code", 0), "out": got.get("out", ""), "error": got.get("error", "")})
        if not got["ok"]:
            break
    done = bool(ran) and all(x["ok"] for x in ran)
    first = "" if done else next((x["error"] or "the scheduler refused the change" for x in ran if not x["ok"]),
                                 "there was nothing to install")
    return {"ok": done, "done": done, "platform": plan["platform"], "error": first,
            "text": plan["text"], "ran": ran, "warn": plan.get("warn", "")}


def remove(platform: str, times: Times = None, confirm: bool = False) -> Dict[str, Any]:
    """Take the schedule off this machine again, but only when the caller passes confirm=True."""
    plan = _plan(platform, times, "")
    if not plan.get("ok"):
        return plan
    if not confirm:
        return {
            "ok": False,
            "done": False,
            "platform": plan["platform"],
            "error": "remove needs confirm=True, so nothing was changed on this machine.",
            "text": plan["text"],
            "off": plan["off"],
            "ran": [],
        }
    ran: List[Dict[str, Any]] = []
    for argv in plan["off"]:
        got = _run(argv)
        ran.append({"cmd": _shown(argv, plan["platform"]), "ok": got["ok"],
                    "code": got.get("code", 0), "out": got.get("out", ""), "error": got.get("error", "")})
    done = bool(ran) and all(x["ok"] for x in ran)
    first = "" if done else next((x["error"] or "the scheduler refused the change" for x in ran if not x["ok"]),
                                 "there was nothing to remove")
    return {"ok": done, "done": done, "platform": plan["platform"], "error": first, "ran": ran}


def slots(start: datetime, count: int = 1, step: int = 90,
          win_from: str = WIN_FROM, win_to: str = WIN_TO) -> List[str]:
    """Return the run times autopilot picks from start, kept inside one daily window and rolling to tomorrow."""
    first = _clock(win_from) or WIN_FROM
    last = _clock(win_to) or WIN_TO
    if last <= first:
        last = "23:59"
    low = int(first[:2]) * 60 + int(first[3:])
    high = int(last[:2]) * 60 + int(last[3:])
    runs = max(1, min(int(count or 1), MAX_SLOTS))
    gap = max(5, min(int(step or 90), 1440))
    at = start
    out: List[str] = []
    for _ in range(runs):
        minute = at.hour * 60 + at.minute
        if minute < low:
            at = at.replace(hour=low // 60, minute=low % 60)
        elif minute > high:
            at = (at + timedelta(days=1)).replace(hour=low // 60, minute=low % 60)
        out.append(at.strftime("%d %H:%M"))
        at = at + timedelta(minutes=gap)
    return out


def _plan(platform: Optional[str], times: Times, command: str) -> Dict[str, Any]:
    """Work out one platform's schedule; this reads nothing and changes nothing."""
    name = _platform(platform)
    at, days = _times(times)
    argv = _payload(command)
    plan: Dict[str, Any] = {
        "ok": False,
        "platform": name or str(platform or ""),
        "label": LABEL,
        "days": list(days),
        "times": list(at),
        "argv": list(argv),
        "cmds": [],
        "off": [],
        "file": "",
        "body": "",
        "text": "",
        "warn": "",
        "error": "",
    }
    if not name:
        plan["error"] = "unknown platform " + repr(platform) + ", use windows, macos or linux"
        plan["text"] = "# " + plan["error"] + "\n"
        return plan
    log = str(_log())
    if name == "windows":
        cmds = _win_cmds(argv, days, at)
        off = _win_off(len(at))
        plan["text"] = _paste("rem", days, at, [_shown(c, name) for c in cmds]
                              + ["rem to remove it again:"] + [_shown(c, name) for c in off])
        plan["warn"] = ("Windows keeps no log of its own, so a wrapper .cmd is the only way to keep output; "
                        "the task name has to match again when you remove it.")
    elif name == "macos":
        plan["file"] = str(_dir() / "io.peakcut.autopilot.plist")
        plan["body"] = _plist(argv, days, at)
        cmds = [["launchctl", "load", "-w", plan["file"]]]
        off = [["launchctl", "unload", "-w", plan["file"]]]
        plan["text"] = _paste("#", days, at, [
            _heredoc(plan["file"], plan["body"]),
            _shown(cmds[0], name),
            "# to remove it again:",
            _shown(off[0], name),
        ])
        plan["warn"] = ("A launch agent normally lives in ~/Library/LaunchAgents; keep the file where install put it "
                        "or launchd will forget the job.")
    else:
        lines = _cron_lines(argv, days, at)
        plan["file"] = str(_dir() / "crontab.txt")
        plan["body"] = "\n".join(lines) + "\n"
        shell = "(crontab -l 2>/dev/null | grep -v " + CRON_MARK + "; " \
                + "; ".join("echo " + shlex.quote(x) for x in lines) + ") | crontab -"
        cmds = [["sh", "-c", shell]]
        off = [["sh", "-c", "(crontab -l 2>/dev/null | grep -v " + CRON_MARK + ") | crontab -"]]
        plan["text"] = _paste("#", days, at, [
            "# the crontab line this adds:\n" + "\n".join("# " + x for x in lines),
            _shown(cmds[0], name),
            "# to remove it again:",
            _shown(off[0], name),
        ])
        plan["warn"] = ("Cron runs with a bare environment, so the line sets PATH itself; "
                        "the crontab of the account running PeakCut is the one that changes.")
    plan["cmds"] = cmds
    plan["off"] = off
    plan["ok"] = True
    return plan


def _paste(comment: str, days: List[str], at: List[str], blocks: Sequence[str]) -> str:
    """Lay the commands out as one block of text, with a plain heading above them."""
    title = "%s PeakCut autopilot, %s at %s" % (comment, ", ".join(days), ", ".join(at))
    out = [title, comment + " Nothing here runs until an operator pastes it.", ""]
    for block in blocks:
        out.append(str(block))
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def _times(times: Times) -> Tuple[List[str], List[str]]:
    """Turn whatever the caller passed into a sorted list of clock times and a list of weekdays."""
    days = list(DEFAULT_DAYS)
    raw: Any = times
    if isinstance(times, dict):
        asked = times.get("days")
        if isinstance(asked, str):
            asked = [x for x in re.split(r"[,;\s]+", asked) if x]
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
        raw = [x for x in re.split(r"[,;\s]+", raw) if x]
    elif not isinstance(raw, (list, tuple)):
        raw = []
    at: List[str] = []
    for item in raw:
        got = _clock(item)
        if got and got not in at:
            at.append(got)
    if not at:
        at = [DEFAULT_TIME]
    at.sort()
    return at, days


def _clock(text: Any) -> str:
    """Return text as a real HH:MM clock time, or an empty string when it is not one."""
    got = str(text or "").strip()
    if not re.match(r"^\d{2}:\d{2}$", got):
        return ""
    hour, minute = int(got[:2]), int(got[3:])
    if hour > 23 or minute > 59:
        return ""
    return got


def _payload(command: str) -> List[str]:
    """Return the command a schedule should run, falling back to our own tick when none was given."""
    text = str(command or "").strip()
    if text:
        try:
            argv = shlex.split(text, posix=True)
        except ValueError:
            argv = text.split()
        if argv:
            return [str(x) for x in argv]
    return [sys.executable, "-m", "studio.autopilot", "--run"]


def _win_cmds(argv: List[str], days: List[str], at: List[str]) -> List[List[str]]:
    """Return one schtasks line per run time, because a weekly Windows task holds a single start time."""
    line = _win_line(argv)
    out = []
    for index, when in enumerate(at):
        out.append(["schtasks", "/Create", "/TN", _task(index), "/TR", line, "/SC", "WEEKLY",
                    "/D", ",".join(days), "/ST", when, "/F"])
    return out


def _win_off(count: int) -> List[List[str]]:
    """Return the schtasks lines that delete the tasks we created."""
    return [["schtasks", "/Delete", "/TN", _task(i), "/F"] for i in range(max(1, count))]


def _task(index: int) -> str:
    """Return the task name for the n-th run time, so several times a day never share one name."""
    return LABEL if index == 0 else "%s-%d" % (LABEL, index + 1)


def _plist(argv: List[str], days: List[str], at: List[str]) -> str:
    """Return a launch agent that starts the command on each chosen day and time."""
    rows = [(DAYS.index(d) + 1, int(t[:2]), int(t[3:])) for d in days for t in at]
    rows.sort()
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">',
        '<plist version="1.0">',
        "<dict>",
        "  <key>Label</key>",
        "  <string>%s</string>" % _xml(LABEL),
        "  <key>ProgramArguments</key>",
        "  <array>",
    ]
    out += ["    <string>%s</string>" % _xml(a) for a in argv]
    out += [
        "  </array>",
        "  <key>WorkingDirectory</key>",
        "  <string>%s</string>" % _xml(str(_root())),
        "  <key>EnvironmentVariables</key>",
        "  <dict>",
        "    <key>PATH</key>",
        "    <string>%s:/usr/sbin:/sbin</string>" % MAC_PATH,
        "  </dict>",
        "  <key>StandardOutPath</key>",
        "  <string>%s</string>" % _xml(str(_log())),
        "  <key>StandardErrorPath</key>",
        "  <string>%s</string>" % _xml(str(_log())),
        "  <key>StartCalendarInterval</key>",
        "  <array>",
    ]
    for weekday, hour, minute in rows:
        out += ["    <dict>",
                "      <key>Weekday</key>",
                "      <integer>%d</integer>" % weekday,
                "      <key>Hour</key>",
                "      <integer>%d</integer>" % hour,
                "      <key>Minute</key>",
                "      <integer>%d</integer>" % minute,
                "    </dict>"]
    out += ["  </array>", "</dict>", "</plist>"]
    return "\n".join(out) + "\n"


def _cron_lines(argv: List[str], days: List[str], at: List[str]) -> List[str]:
    """Return one crontab line per run time, each ending in the marker we look for later."""
    dows = ",".join(str(DAYS.index(d) + 1) for d in days)
    core = _sh_line(argv)
    root = shlex.quote(str(_root()))
    log = shlex.quote(str(_log()))
    out = []
    for when in at:
        out.append("%d %d * * %s cd %s && PATH=%s:$PATH %s >> %s 2>&1 # %s"
                   % (int(when[3:]), int(when[:2]), dows, root, LINUX_PATH, core, log, CRON_MARK))
    return out


def _heredoc(path: str, body: str) -> str:
    """Return the two commands that put a block of text into a file, exactly as written."""
    return "mkdir -p %s\ncat > %s <<'PLIST'\n%sPLIST" % (
        shlex.quote(str(Path(path).parent)), shlex.quote(path), body)


def _shown(argv: Sequence[str], platform: str) -> str:
    """Return a command as one line of text an operator can paste into their own shell."""
    return _win_line(argv) if platform == "windows" else _sh_line(argv)


def _win_line(argv: Sequence[str]) -> str:
    """Quote a command the way Windows expects it."""
    return subprocess.list2cmdline([str(x) for x in argv])


def _sh_line(argv: Sequence[str]) -> str:
    """Quote a command the way a Unix shell expects it."""
    return " ".join(shlex.quote(str(x)) for x in argv)


def _xml(text: str) -> str:
    """Make text safe to sit inside an XML file."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _platform(name: Optional[str]) -> str:
    """Return windows, macos or linux, from the name given or from this machine, or an empty string."""
    asked = str(name or "").strip().lower()
    if not asked:
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


def _dir() -> Path:
    """Return the folder where we keep schedule files, inside the data folder and never in a home folder."""
    return Path(config.DATA_DIR) / "autopilot"


def _log() -> Path:
    """Return the log file a scheduled run writes to."""
    return Path(config.DATA_DIR) / "autopilot.log"


def _write(path: str, body: str) -> str:
    """Save one schedule file and return a message, or an empty string when it was written."""
    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        newline = "" if os.name == "nt" else None
        with open(str(target), "w", encoding="utf-8", newline=newline) as handle:
            handle.write(body)
        return ""
    except Exception as exc:
        return "could not write %s: %s: %s" % (path, type(exc).__name__, exc)[:300]


def _run(argv: Sequence[str]) -> Dict[str, Any]:
    """Run one scheduler command and report what happened instead of raising anything."""
    steps = [str(x) for x in argv]
    if not steps:
        return {"ok": False, "code": 0, "out": "", "error": "no command to run"}
    found = shutil.which(steps[0])
    if not found:
        return {"ok": False, "code": 0, "out": "", "error": "%s is not on this machine" % steps[0]}
    cwd = str(_root()) if _root().is_dir() else None
    try:
        done = subprocess.run([found] + steps[1:], capture_output=True, text=True,
                              timeout=TIMEOUT, cwd=cwd)
    except subprocess.TimeoutExpired:
        return {"ok": False, "code": 0, "out": "", "error": "%s took longer than %d seconds" % (steps[0], TIMEOUT)}
    except Exception as exc:
        return {"ok": False, "code": 0, "out": "", "error": "%s: %s" % (type(exc).__name__, exc)[:300]}
    text = ((done.stdout or "") + (done.stderr or "")).strip()
    if done.returncode == 0:
        return {"ok": True, "code": 0, "out": text[:600], "error": ""}
    return {"ok": False, "code": done.returncode, "out": text[:600],
            "error": (text[:300] or "%s exited with %d" % (steps[0], done.returncode))}


def _status() -> Dict[str, Any]:
    """Return the schedule this machine would get, as plain data for a scheduled run to print."""
    name = _platform(None)
    plan = _plan(name, None, "")
    return {
        "ok": bool(plan.get("ok")),
        "platform": name or "unknown",
        "label": LABEL,
        "days": plan.get("days", []),
        "times": plan.get("times", []),
        "command": plan.get("argv", []),
        "note": "This command only reports the schedule; PeakCut itself decides what to run.",
    }


if __name__ == "__main__":
    print(json.dumps(_status(), indent=2))
