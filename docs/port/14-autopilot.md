# 14 — Autopilot scheduling

Port of `gta6-clipper-main/app.py` (`ap_default` / `ap_load` / `ap_status` / `ap_task_exists` / `ap_plan` /
`slots_py` / `autopilot_main`, app.py:538-614) into PeakCut as `peakcut/studio/autopilot.py`.

PeakCut cannot copy it file-for-file: the source writes a machine-wide OS task that shells back into
`app.py --autopilot <workspace>` for **one** workspace owned by **one** person. PeakCut runs one server for
many accounts, usually inside a container where `schtasks`/`crontab` do not exist. The port therefore keeps
**both halves** and makes the second optional:

* **Tier A — the in-process scheduler.** A due-check thread inside the server that fires a user's autopilot at
  their chosen wall-clock minute and calls `jobs.create(...)`. This is the behaviour users actually want and it
  works everywhere, including Docker. It is the part PeakCut genuinely lacks.
* **Tier B — the OS-scheduler export.** `plan()` reproduces the source's schtasks / launchd / crontab generator
  verbatim, retargeted at `python -m studio.autopilot --run` for the whole install. It is offered as copyable
  text plus an "install" button that refuses when the process cannot reach a host scheduler.

---

## 1. What it does

A signed-in user turns on Autopilot, picks the weekdays and the time of day, and chooses which of their creators
should be clipped. At that minute on those days PeakCut starts the normal clip pipeline by itself — downloading,
transcribing, picking and rendering — with nobody at the keyboard, then reports the result (how many clips, their
QC state, how many were queued to post) on the Autopilot tab. Finished clips can be spread across a posting window
instead of all landing at once. The tab also shows the exact OS command that would reproduce the same schedule
outside the server, so a single-user install can keep it running after the server stops; on a multi-user or
containerised install that button is disabled and the in-server scheduler is the only path. Nothing is ever
uploaded or posted without the account's existing autopost settings.

---

## 2. Exact mechanics

### 2.1 Constants

| Name | Value | Where |
|---|---|---|
| `DAYS` | `("MON","TUE","WED","THU","FRI","SAT","SUN")` | app.py:540 |
| weekday mapping | `DAYS.index(x) + 1` → 1 = Monday … 7 = Sunday | app.py:576, app.py:577 |
| task name | `"ClipperAutopilot"` (source), port uses `"PeakCutAutopilot"` | app.py:539 |
| default days | `["MON","WED","FRI"]` | app.py:542 |
| default time | `"09:00"` | app.py:542 |
| default count | `10` | app.py:542 |
| default kind/value | `"newest"` / `""` | app.py:542 |
| default `auto_schedule` | `True` | app.py:542 |
| default `step` | `90` (minutes) | app.py:542 |
| default window | `win_from "08:00"`, `win_to "23:00"` | app.py:542 |
| `TASK_TIMEOUT` | `20` s for the existence probe, `30` s for install/uninstall | app.py:554-558, app.py:901 |
| launchd label | `"io.clipper.autopilot"` | app.py:569 |
| cron marker | `"clipper-autopilot"` | app.py:553-558, app.py:577-581 |
| PATH handed to the OS task | `"/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"` | app.py:567 |

`DAYS.index(x) + 1` is doubly load-bearing: it is the cron **day-of-week field** (`1 = Monday`) *and* the launchd
`Weekday` **integer** (`1 = Monday`). Both agree; do not "fix" one of them to Sunday-based.

### 2.2 Config: `ap_default()` / `ap_load()` / `ap_status()` (app.py:542-552)

```python
def ap_default():
    return dict(days=["MON","WED","FRI"], time="09:00", count=10, kind="newest", value="",
                auto_schedule=True, step=90, win_from="08:00", win_to="23:00", ai=cur_ai())
```

`ap_load()` is `c = ap_default(); c.update(json.loads(WS/"autopilot.json"))` wrapped in
`except Exception: pass` (app.py:543-548). Two consequences the port must keep: a corrupt file silently yields
defaults rather than an error, and **unknown keys survive** (they are not filtered out). `ap_status()` reads
`WS/"autopilot_status.json"` and returns `None` on any exception (app.py:549-552).

### 2.3 `ap_task_exists()` — three-state probe (app.py:553-558)

The whole function is wrapped so that **any** exception returns `None`, which the UI renders as
`Autopilot: managed by you` (the user may have created the task by hand).

* Windows: `subprocess.run(["schtasks","/Query","/TN",TASK], capture_output=True, text=True, timeout=20).returncode == 0`
* macOS: `(Path.home()/"Library"/"LaunchAgents"/"io.clipper.autopilot.plist").exists()`
* Linux/other: `"clipper-autopilot" in subprocess.run(["crontab","-l"], capture_output=True, text=True, timeout=20).stdout`

Return contract: `True` = task present, `False` = absent, `None` = we could not tell (no `crontab` binary, the
command timed out, permissions). `None` must never be rendered as "off".

### 2.4 `ap_plan(c)` — the OS-scheduler generator (app.py:559-581)

Sanitisation first, always:

```python
days = [x for x in c["days"] if x in DAYS] or ["MON"]
hh   = re.fullmatch(r"\d\d:\d\d", c["time"]) and c["time"] or "09:00"
py   = sys.executable
core = f'"{py}" "{HERE / "app.py"}" --autopilot "{WS}"'
```

`days` falls back to `["MON"]` when every entry is invalid. `hh` is validated by regex only — `"99:99"` passes the
regex and is written into the task; the port must additionally clamp to `00:00`–`23:59` (see §4.6).

**Windows** (app.py:562-566). A `.cmd` wrapper is written because `schtasks /TR` cannot express redirection:

```bat
@echo off
cd /d "<WS>"
"{py}" "<HERE>/app.py" --autopilot "<WS>" >> "<WS>/autopilot.log" 2>&1
```
(line endings `\r\n`, written with `newline=""` so they are not doubled).

```python
cmd = ["schtasks","/Create","/TN",TASK,"/TR",
       (f'"{wrapper}"' if " " in str(wrapper) else str(wrapper)),
       "/SC","WEEKLY","/D", ",".join(days), "/ST", hh, "/F"]
off = ["schtasks","/Delete","/TN",TASK,"/F"]
```

`/TR` is wrapped in quotes **only when the path contains a space**. `/D` takes the comma-joined day list.
`/F` makes create idempotent by overwriting. `shown` is `subprocess.list2cmdline(cmd)`.

**macOS** (app.py:568-576). A LaunchAgent plist at `~/Library/LaunchAgents/io.clipper.autopilot.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0"><dict>
  <key>Label</key><string>io.clipper.autopilot</string>
  <key>ProgramArguments</key><array><string>PY</string><string>APP</string><string>--autopilot</string><string>WS</string></array>
  <key>WorkingDirectory</key><string>WS</string>
  <key>EnvironmentVariables</key><dict><key>PATH</key><string>ENVP</string></dict>
  <key>StandardOutPath</key><string>LOG</string>
  <key>StandardErrorPath</key><string>LOG</string>
  <key>StartCalendarInterval</key><array>
    <dict><key>Weekday</key><integer>DAYS.index(x)+1</integer><key>Hour</key><integer>HH</integer><key>Minute</key><integer>MM</integer></dict>
  </array>
</dict></plist>
```

One `<dict>` per selected day. `Hour` is `int(hh[:2])`, `Minute` is `int(hh[3:])` — integers, not strings.
`cmd = ["launchctl","load","-w",str(lp)]`, `off = ["launchctl","unload","-w",str(lp)]`.

**Linux** (app.py:577-581). A single crontab line, **minute field before hour field** (`09:00` → `0 9`):

```
{MM} {HH} * * {"," .join(DAYS.index(x)+1)} PATH={envp}:$PATH cd "{WS}" && {core} >> "{log}" 2>&1 # clipper-autopilot
```

Installed with a strip-then-append idiom so repeated installs do not stack lines:

```python
inst = f'(crontab -l 2>/dev/null | grep -v clipper-autopilot; echo {shlex.quote(cron)}) | crontab -'
off  = ["sh","-c","crontab -l 2>/dev/null | grep -v clipper-autopilot | crontab -"]
```

Note the escaping contract: `WS` is interpolated into the cron text inside `"double quotes"` and the *whole line* is
then passed through `shlex.quote` at install time. Escaping happens at the last step, not during formatting.

The Linux branch also builds, but never installs, a systemd alternative (`systemd` key, unit + timer, app.py:579-580):

```
[Unit] / [Service] Type=oneshot, WorkingDirectory=WS, ExecStart=PY APP --autopilot WS
[Timer] OnCalendar={comma joined Title-case days} *-*-* {hh}:00 / Persistent=true
[Install] WantedBy=timers.target
```

Return shape, identical keys on all three platforms so the UI can be generic:

```python
{"platform": "windows"|"macos"|"linux",
 "wrapper": str|None,        # .cmd text (Windows only)
 "wrapper_path": str|None,   # where the .cmd goes (Windows only)
 "cmd": list[str]|None,      # install command
 "off": list[str]|None,      # uninstall command
 "shown": str,               # human-readable, what the Preview button prints
 "cron": str|None,           # Linux only
 "systemd": str|None}        # Linux only
```

Branch on `pl["cmd"]` (not on `platform`) to decide whether the UI shows the wrapper box or the cron/plist text —
that is exactly what app.html:527 does.

### 2.5 `slots_py(t0, count, step, f, to)` — window-filling slot generator (app.py:582-589)

```python
def slots_py(t0, count, step, f, to):
    fm, tm = [int(x[:2])*60 + int(x[3:]) for x in (f, to)]
    out, t = [], t0
    for _ in range(count):
        m = t.hour*60 + t.minute
        if m < fm:
            t = t.replace(hour=fm//60, minute=fm%60)          # before the window: wait for it to open
        elif m > tm:
            t = (t + timedelta(days=1)).replace(hour=fm//60, minute=fm%60)   # past it: next day's opening
        out.append(t)
        t = t + timedelta(minutes=step)
    return out
```

Exact semantics a reimplementation must preserve:

* The **start time is respected**: if `t0` already sits inside `[from, to]`, the first slot *is* `t0`.
* The window is **inclusive at both ends**: a slot at exactly `to` stays; only `m > tm` rolls over.
* Rollover is to **the next day's `from`**, not to midnight and not by adding `step`.
* `count` drives the loop; the generator is pure and has no clock of its own (the caller supplies `t0`).
* The JS mirror in app.html:398-399 must stay in sync if either side changes.

Callers: `autopilot_main` uses `t0 = now.replace(minute=0, second=0, microsecond=0) + 1 hour` (next whole hour,
app.py:594); the auto-schedule block reuses the same iterator with `count=999` and stops early via `next()`.

### 2.6 `autopilot_main(dry)` — the headless run (app.py:590-614)

1. Load config; `n = int(c["count"])`; resolve the AI provider, falling back to the environment default when the
   stored one is not in `PROV` (app.py:591-592).
2. Build the request from `source_what(kind, value)` (app.py:420-427) and `build_prompt(n, what)` (app.py:428-435).
3. Make a run folder `WS/"runs"/time.strftime("run_%Y%m%d_%H%M%S")` (app.py:593).
4. Print the plan: `t0` = next whole hour, then `n` slots from `slots_py`. `dry` stops here with
   `"DRY RUN: nothing executed"` (app.py:594-596).
5. Write the status file **before** doing any work (app.py:597):
   `{"state":"running","started":"YYYY-MM-DD HH:MM","run":"","shorts":0,"qc":{},"scheduled":0,"notified":False}`
6. Run the AI, capturing stdout+stderr into `folder/"autopilot.log"` with `cwd=folder`; `ok = returncode == 0`,
   and any exception is written into the log with `ok = False` (app.py:598-602).
7. Scan `find_runs(folder)` and finalise (app.py:603-606): `state = "done" if ok and runs else "failed"`,
   `finished`, `shorts = sum(r["n"])`, `run = runs[0]["id"]`, `qc` = summed histogram, `notified = False`.
8. Auto-schedule (app.py:607-613), only `if c["auto_schedule"] and runs`:

```python
t = iter(slots_py(t0, 999, int(c["step"]), c["win_from"], c["win_to"]))
for r in runs:
    for sh in shorts(r["id"]):
        if sh["qc"] == "FAIL" or st["scheduled"] >= n:
            continue
        x = next(t)
        S["schedule"][f"{r['id']}|{sh['file']}"] = {
            "local": x.strftime("%Y-%m-%dT%H:%M"),
            "utc":   x.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        st["scheduled"] += 1
```

Two filters, both exact: **`qc == "FAIL"` clips are skipped**, and the total scheduled count is capped at `n`
(the same `n` as the job count, not the number of clips produced). `local` has no seconds and no timezone suffix;
`utc` is `...Z` with seconds. Both strings are stored; the UI reads `local`, the notifier uses `utc`.

`main()` routes into it before anything else (app.py:926-927):

```python
if "--autopilot" in sys.argv:
    return autopilot_main("--dry" in sys.argv)   # headless entry used by the OS task
```

### 2.7 HTTP surface in the source (for shape only; PeakCut routes are in §4.7)

* `GET /api/autopilot` → `{"ais", "config", "plan", "task", "status", "platform"}` (app.py:742) — `plan` is
  always computed so the tab can show the command without a round-trip, `task` is the three-state probe.
* `POST /api/autopilot/plan` (app.py:895-904): `c = {**ap_default(), **d["config"]}`, then
  `if d.get("dry", True) or d.get("confirm") is not True` → return the preview only. **Installing requires both
  `dry=false` and `confirm=true`**; a missing `confirm` is treated as a no-op preview, never as consent.
  On install: write `autopilot.json` (`indent=1`), write the wrapper if `pl["wrapper_path"]`, run `pl["cmd"]`
  with `timeout=30`; `returncode != 0` → `HTTPException(400, (stdout+stderr).strip())`.
  When there is a `cmd` but no wrapper (Linux) the source does *not* run it — it returns
  `{"dry": false, "output": "config saved; paste the crontab line (or load the plist) yourself", "plan": pl}`.
* `POST /api/autopilot/off` (app.py:905-908) — same dry/confirm gate, then `pl["off"]`.
* `POST /api/autopilot/seen` (app.py:909-912) — sets `notified: true` so the finished banner stops appearing.
* Error convention (app.py:921-922): `HTTPError` → 502, any other exception → 400 `{"error": str(e)}`.

---

## 3. PeakCut today

PeakCut has **no scheduling concept at all** — `grep -ri "cron\|schtasks\|launchd\|scheduler\|autopilot"` over
`studio/` returns nothing but the unrelated word "scheduled" in `posting.py`. What exists that overlaps:

| PeakCut | Where | What it does | Gap |
|---|---|---|---|
| `live.watch_loop()` | studio/live.py:868-874 | 2-minute poll thread, per-user, started by `live.start()` | Polls *creators* for going live; knows nothing about days or times. This is the exact thread pattern `autopilot.loop()` should copy. |
| `live.start()` | studio/live.py:908-920 | resumes state, then spawns the loop daemon | The precedent for `autopilot.start()`. |
| `posting._run()` | studio/posting.py:143-158 | 15 s tick over `due_at`, per user via `ctx.as_user(p["user"])` | Schedules **posts**, not **renders**, and only from a queue that something else filled. |
| `posting._next_slot(account_id, gap_min, cap)` | studio/posting.py:55-64 | spaces posts by `post_gap_min` and a daily cap, rolling to 09:00 the next day via `time.mktime((y,m,d,9,0,0,0,0,-1))` | Pure relative spacing. No window, no weekday, no wall-clock slot list — it cannot express "08:00–23:00 every 90 minutes". `slots_py` is a genuinely different algorithm and must be ported, not aliased. |
| `posting.on_clip_ready(job, clip)` | studio/posting.py:91-100 | gates on `c["autopost"] and c["accounts"]` and `clip["score"] >= c["post_min_score"]` | The correct sink for finished autopilot clips; no `due_at` override, so it cannot honour a window. |
| `jobs.create(source, options, enqueue=True, creator=None, kind="video")` | studio/jobs.py:286-307 | builds the job dict, saves it, pushes it on the fair queue | **This is what autopilot must call.** Nothing calls it on a timer today. |
| `creators.DEFAULTS` / `creators.update()` | studio/creators.py:17-23, :137 | per-creator settings incl. `auto_watch`, `autopost`, `post_min_score` | Per-creator, not per-user-schedule. An autopilot needs user-level fields (days, time, count) that have no home today. |
| `ai.py` settings module | studio/ai.py:39-70 | `_lock` + `_saved` + mtime-checked `_file()` in `config.DATA_DIR` | The exact file-over-defaults shape `autopilot.py` must copy. |
| `server._startup()` | studio/server.py:58-85 | ends with `jobs.start(); live.start(); posting.start(); updates.start()` | **Where `autopilot.start()` is added.** |
| `_tr_saved` / `_tr_public` / transcription routes | studio/server.py:1321-1449 | `_admin()` gate, `_throttle()`, 400 user / 502 upstream, atomic write, `ctx.bump()` | The route template to follow, including never restarting the server on a bad JSON file. |
| `auth.user_ids()` | studio/auth.py:179 | every account id | The multi-user fan-out that the source's single `WS` does not have. |

**The gap, concretely:** nothing in PeakCut can start work at a wall-clock time. A user must press a button.
The only timers are a 2-minute live poll and a 15-second post queue, both of which consume input that a human
already produced. Feature 14 is the missing "start it for me at 09:00 on Monday" capability.

---

## 4. Port plan

New module: **`peakcut/studio/autopilot.py`**. One concern, no new dependency (stdlib `datetime`, `json`,
`shutil`, `subprocess`, `sys`, `pathlib`, `threading` only — matching `requirements.txt`, which has no scheduler
library).

Per-user config lives at `config.user_dir(uid)/"autopilot.json"` and, crucially, is **per account**. A single
OS-level task is installed for the *whole install* and iterates users; it is never one crontab line per account
(§6).

### 4.1 Public API

```python
DAYS: tuple[str, ...] = ("MON","TUE","WED","THU","FRI","SAT","SUN")
TASK: str = "PeakCutAutopilot"
TICK: int = 30                    # seconds between due checks
LEAD: int = 60                    # seconds of slack before a slot counts as missed
RUN_TIMEOUT: int = 3600           # seconds `run_once` waits for its queue before giving up

def defaults() -> dict:
    """The stored-shape config, mirroring ap_default() (app.py:542). Never mutates."""

def _path(uid: str) -> Path:
    """config.user_dir(uid) / 'autopilot.json'."""

def load(uid: str | None = None) -> dict:
    """defaults() merged with the user's JSON file. Corrupt/non-dict file -> defaults, no raise.
    Unknown keys are preserved (same contract as ap_load, app.py:543-548)."""

def save(uid: str, data: dict) -> dict:
    """Validate + clamp + write atomically (tmp then Path.replace) under _lock. Returns the stored dict.
    Raises ValueError with a user-facing message for a bad day/time/count and never with a server path."""

def public(uid: str | None = None) -> dict:
    """Everything the SPA needs and nothing it should not see: the config, task_exists(), status(),
    the plan for the *current* config, and whether install is even possible here."""

def slots(t0: datetime, count: int, step: int, win_from: str, win_to: str) -> list[datetime]:
    """Exact port of slots_py (app.py:582-589). Pure; no clock of its own."""

def plan(cfg: dict) -> dict:
    """Exact port of ap_plan (app.py:559-581), retargeted at `python -m studio.autopilot --run`.
    Reads config.DATA_DIR instead of WS. Returns the dict described in §2.4."""

def task_exists() -> bool | None:
    """Three-state host probe, port of ap_task_exists (app.py:553-558). Never raises."""

def due(cfg: dict, now: datetime | None = None) -> bool:
    """True when this config should fire at `now`. See §4.3 for the exact rule."""

def run_once(uid: str | None = None, dry: bool = False, timeout: int = RUN_TIMEOUT) -> dict:
    """Run every due user (or just `uid`) once, synchronously. The `--run` entry point and the tests' hook."""

def status(uid: str | None = None) -> dict | None:
    """Last run's status for that user, or None. Port of ap_status (app.py:549-552)."""

def start() -> None:
    """Start the due-check daemon thread once. Idempotent; safe to call twice."""
```

Internal helpers, private by convention: `_lock: threading.Lock`, `_saved: dict[str, tuple[int, dict]]` (the
mtime cache, copied from `ai.py:39-60`), `_tick(now)`, `_run_user(uid, cfg)`, `_validate(data)`,
`_install(cmd)`, `_status_path(uid)`, `_write_status(uid, st)`.

### 4.2 Module layout inside `autopilot.py`

| Block | Responsibility | Ported from |
|---|---|---|
| constants + `defaults` | config shape | app.py:539-542 |
| `_path`/`load`/`save`/`status`/`_write_status` | per-user persistence | app.py:543-552 |
| `_validate` | clamp days/time/count/step/window | new (source does not validate, see §6) |
| `slots` | window filler | app.py:582-589 |
| `plan`/`task_exists`/`_install`/`_uninstall` | OS scheduler | app.py:553-581 |
| `due`/`_run_user`/`run_once` | firing | app.py:590-614 |
| `_tick`/`loop`/`start` | the server thread | app.py:926-927 + live.py:868-874 |
| `public` | SPA payload | app.py:742 |

### 4.3 The firing rule — `due()`

The source has no equivalent; the OS scheduler was the clock. In-process, the clock must be explicit and exactly
specified:

```python
def due(cfg: dict, now: datetime | None = None) -> bool:
    now = now or datetime.now().astimezone()
    if not cfg.get("on"):
        return False
    if DAYS[now.weekday()] not in cfg["days"]:      # weekday(): Monday == 0, so index matches DAYS
        return False
    if now.strftime("%H:%M") != cfg["time"]:
        return False
    return cfg.get("last_run") != now.strftime("%Y-%m-%d %H:%M")
```

`last_run` is the dedupe key: with `TICK = 30` the same minute is observed twice, so `_tick` writes
`cfg["last_run"] = now.strftime("%Y-%m-%d %H:%M")` under the lock **before** starting the run. The value is the
full `"YYYY-MM-DD HH:MM"`, so tomorrow's same time fires again. `_tick` iterates `auth.user_ids()`, calls
`ctx.as_user(uid)` per id, and fires a daemon thread per due user — never inline, so one slow download cannot
stall the others.

### 4.4 What `_run_user` does, in PeakCut's terms

The source's step 6 is "spawn an external AI CLI with a prompt". PeakCut has no external CLI: it has
`studio/brain.py` and `jobs._run_job`. So `_run_user(uid, cfg)` replaces `autopilot_main`'s body with the
native pipeline:

```python
with ctx.as_user(uid):
    st = {"state": "running", "started": now.strftime("%Y-%m-%d %H:%M"),
          "run": "", "jobs": [], "shorts": 0, "qc": {}, "scheduled": 0, "notified": False}
    _write_status(uid, st)
    targets = [creators.get(cid) for cid in cfg["creators"]] or \
              [c for c in creators.all_creators() if c.get("auto_watch")]
    for c in [t for t in targets if t][:cfg["count"]]:
        job = jobs.create({"type": "url", "url": c["channel"], "name": c["channel"]},
                          cfg["options"], creator=c["id"])
        st["jobs"].append(job["id"])
        creators.log(c["id"], "Autopilot started a job")
    _write_status(uid, st)          # state stays "running" until the jobs drain
```

Then `run_once` (used by `--run` and by the tests) waits: `jobs.start()`, then poll `jobs.busy_count()` and
`jobs.waiting_total()` every 5 s until both are 0 or `timeout` elapses. The thread version does not wait — it lets
`jobs._run_job` finish on its own and writes the final status from `_run_finished(uid)`, which is where
`shorts`/`qc`/`scheduled` are summed from the job records (the analogue of app.py:603-606).

`count` in the source is "how many Shorts to make"; in PeakCut it is "how many jobs to create per firing", because
`max_clips` per creator already controls Shorts per job. Default it to `1` in `defaults()` — creating `10` jobs at
09:00 every Monday would blow past `MAX_ACTIVE_JOBS_PER_USER` (config.py:184) and is a foot-gun the source can
afford (single user, sequential CLI) and a server cannot.

### 4.5 Auto-scheduling finished clips

The source writes slot timestamps into `app_state.json["schedule"]` and the page reads them back. PeakCut already
has that machinery in `posting.py`; do not duplicate it. The mapping is:

* `auto_schedule` on → after a job's clips are ready, schedule their posts at `slots()` times instead of
  "as soon as the gap allows".
* This needs **one additive change in `posting.py`**, backwards compatible:
  `def enqueue(job, clip, account_ids, now: bool = False, due_at: float | None = None) -> list` — when
  `due_at` is given, store it instead of calling `_next_slot(...)` (posting.py:67-88). Every existing caller
  keeps working because `due_at` defaults to `None`.
* The caller computes `due_at` as `x.timestamp()` for the next unused slot from
  `slots(now, 999, cfg["step"], cfg["win_from"], cfg["win_to"])` — the same `iter(slots(...))` + `next()` loop
  and the same two filters as app.py:607-613: skip a clip when the posting gate in `on_clip_ready`
  (posting.py:91-100) would refuse it, and stop at `cfg["count"]` scheduled items.
* `qc == "FAIL"` has no PeakCut equivalent (PeakCut clips carry `score`, not a QC status). Substitute the
  existing gate: skip a clip whose `score` is below the creator's `post_min_score`. State this in the code
  comment so the substitution is auditable.

### 4.6 Validation added on top of the source

The source trusts its own form. Every one of these is a real value that reaches `subprocess.run` here, so
`_validate` clamps before anything is formatted:

| Field | Rule |
|---|---|
| `days` | keep only members of `DAYS`; if empty → `["MON"]` (same fallback as app.py:560) |
| `time` | must match `^\d{2}:\d{2}$` **and** `00 <= hh <= 23` **and** `00 <= mm <= 59`, else `"09:00"`. The source's regex alone accepts `"99:99"` (app.py:560). |
| `count` | `int`, clamped `1..MAX_ACTIVE_JOBS_PER_USER` (config.py:184; the source clamps nothing and its form says `1..30`) |
| `step` | `int`, clamped `5..1440` |
| `win_from` / `win_to` | `^\d{2}:\d{2}$` and in range, else `"08:00"`/`"23:00"`; if `to <= from` → `to = "23:59"` |
| `creators` | list of ids that `creators.get(cid)` actually resolves for this user; unknown ids dropped |
| `options` | passed through `jobs.clean_options` (jobs.py:117), which already bounds everything |
| `on` | `bool(...)` |

Nothing user-supplied is ever interpolated into a shell string: `plan()` formats `sys.executable`,
`config.DATA_DIR` and the day/time integers, all of which the server itself produced. If a future field ever
does reach the cron text, it must be `shlex.quote`d at the same point the source does it (app.py:578).

### 4.7 Wiring — exact call sites

**Called by `autopilot.py` (must exist, unchanged unless noted):**

| Function | File:line | Purpose |
|---|---|---|
| `config.user_dir(uid) -> Path` | studio/config.py:146 | where `autopilot.json` and `autopilot_status.json` live |
| `config.DATA_DIR` | studio/config.py:119 | whole-install paths in `plan()` (wrapper, log, plist) |
| `config.MAX_ACTIVE_JOBS_PER_USER` | studio/config.py:184 | clamp for `count` |
| `ctx.uid()` / `ctx.uid_or_none()` | studio/ctx.py | who is asking |
| `ctx.as_user(uid)` | studio/ctx.py:34-41 | run a user's pipeline with their identity |
| `ctx.bump(uid=None)` | studio/ctx.py:57-70 | tell the SPA something changed after save/run |
| `auth.user_ids() -> list` | studio/auth.py:179 | fan-out for `_tick` and `--run` |
| `creators.all_creators()` / `creators.get(cid)` | studio/creators.py:114, :118 | which creators to clip |
| `creators.log(cid, msg)` | studio/creators.py:204+ | visible trail in the creator's log card |
| `jobs.create(source, options, enqueue=True, creator=None, kind="video")` | studio/jobs.py:286-307 | **the action** |
| `jobs.clean_options(options)` | studio/jobs.py:117 | bound user options |
| `jobs.job_dir(jid)` | studio/jobs.py:145 | read back finished clips |
| `jobs.start()` / `jobs.busy_count()` / `jobs.waiting_total()` | studio/jobs.py:848, :269, :274 | drain + wait, for `run_once` |
| `posting.enqueue(..., due_at=...)` | studio/posting.py:67 | auto-scheduled posts (one additive param, §4.5) |
| `posting.on_clip_ready(job, clip)` | studio/posting.py:91-100 | the gate for the above |
| `alerts.notify(text, kind="autopilot", link="")` | studio/alerts.py:39-49 | "Autopilot finished: 4 clips, 2 queued" |
| `safe.friendly(e, 160)` | studio/safe.py | any message that escapes to a route |

**Calls into `autopilot.py`, and only these:**

| Caller | Site | Call |
|---|---|---|
| `server._startup()` | studio/server.py:58-85, after `updates.start()` | `autopilot.start()` |
| routes | studio/server.py, appended after the transcription block | `GET /api/autopilot`, `POST /api/autopilot/plan`, `POST /api/autopilot/off`, `POST /api/autopilot/run`, `POST /api/autopilot/seen` |
| `studio/autopilot.py` `__main__` | bottom of the file | `if __name__ == "__main__": run_once(...)` for `--run [--dry] [--uid U]` |
| `web/index.html` | `setTabs()` :2003-2009 | `["autopilot", "Autopilot", "clock", "Runs your creators on a schedule"]` |

**Routes**, following the transcription block exactly (server.py:1350-1449):

```python
@app.get("/api/autopilot")
def autopilot_get(request: Request):
    _admin(request)
    return autopilot.public()

@app.post("/api/autopilot/plan")
def autopilot_plan(body: dict = Body(...)):
    _admin(request); _throttle("ap:" + ctx.uid(), 30, 600)
    ...  # dry unless body["dry"] is False AND body["confirm"] is True  (app.py:899-900)
    # dry -> {"dry": True, "plan": plan(cfg), "config": cfg}
    # install -> save(); if pl["wrapper_path"]: write it; run pl["cmd"] (timeout=30) if present
    #            returncode != 0 -> HTTPException(400, safe.friendly(out, 300))
    # no cmd (cannot reach a host scheduler) -> HTTPException(400,
    #            "This server can't create OS scheduled tasks. Autopilot still runs while PeakCut is running.")

@app.post("/api/autopilot/off")
def autopilot_off(...):     # same gate, then pl["off"]
@app.post("/api/autopilot/run")
def autopilot_run(...):     # _throttle("apr:"+ctx.uid(), 6, 600); thread -> autopilot.run_once(ctx.uid())
@app.post("/api/autopilot/seen")
def autopilot_seen(...):    # clear the finished flag
```

`_admin(request)` (server.py:310-315) matters more here than anywhere else in the codebase: this feature makes the
server **execute commands** and **spend compute unattended**. It is admin-only, no exceptions, no per-user mode.

### 4.8 UI

One settings tab, `"autopilot"`, admin-only (the same `S.status.user?.is_admin` gate as `ai`/`transcribe` at
index.html:2003-2009), icon `"clock"` — already present in the `I` map (index.html:847-903), so no new SVG is
needed. The tab body follows `tab === "transcribe"` (index.html:2048-2055):

* seven day checkboxes bound to `days` (letters `M T W T F S S`, value `MON`…`SUN`);
* `time` (`<input type="time">`), `count` (`min=1`, `max` = the server-reported cap), `on` (a switch);
* a creator multi-select fed from the existing creator list;
* an "Advanced" fold with `step`, `win_from`, `win_to`, `auto_schedule`;
* three buttons matching app.html:527-530: **Preview command** (calls `/api/autopilot/plan` with `dry: true` and
  renders `pl.shown` plus `pl.wrapper` when `pl.cmd` else `pl.cron`/`pl.systemd`), **Turn on** (a confirm, then
  `dry: false, confirm: true`), **Turn off**;
* the status line: `running` / `done` / `failed` with `shorts` and `scheduled` counts, and a **Run now** button
  wired to `/api/autopilot/run` — the source has no such button and it is the single most useful addition for
  someone who cannot install an OS task;
* copy that keeps the source's two warnings, reworded for a server: "Autopilot runs while PeakCut is running."
  and "Nothing is ever uploaded or posted automatically unless the creator's autopost settings say so."
  (app.html:515-525 has the originals: *"Your PC must be on and logged in at that time."* / *"Nothing is ever
  posted automatically."*)
* the finished banner mirrors `apHeader()` (app.html:512-514) and posts `/api/autopilot/seen` when dismissed.

The SPA router regex at index.html:1330 already accepts any `setTabs()` key, so registering the tab is enough —
but the guard must stay `setTabs().some(...)` so a non-admin landing on `#settings/autopilot` falls back to the
first tab rather than rendering an empty page.

---

## 5. Data files

### 5.1 `config.user_dir(uid)/"autopilot.json"` — per account, created lazily on first save

```json
{
  "on": false,
  "days": ["MON", "WED", "FRI"],
  "time": "09:00",
  "count": 1,
  "creators": [],
  "options": {},
  "auto_schedule": true,
  "step": 90,
  "win_from": "08:00",
  "win_to": "23:00",
  "last_run": ""
}
```

| Key | Type | Bounds / meaning |
|---|---|---|
| `on` | bool | master switch; `false` means the tick never fires |
| `days` | list[str] | subset of `DAYS`, never empty after validation |
| `time` | str | `"HH:MM"`, 24-hour, local to the server |
| `count` | int | jobs created per firing, `1..config.MAX_ACTIVE_JOBS_PER_USER` |
| `creators` | list[str] | creator ids; `[]` means "every creator with `auto_watch` true" |
| `options` | dict | passed through `jobs.clean_options`; `{}` means the creator's own defaults |
| `auto_schedule` | bool | schedule the finished clips' posts at `slots()` times |
| `step` | int | minutes between posting slots, `5..1440` |
| `win_from` / `win_to` | str | `"HH:MM"`, the posting window; both ends inclusive |
| `last_run` | str | `"YYYY-MM-DD HH:MM"`, the dedupe key; written before the run, never by the UI |

Read with the `ai.py` discipline (ai.py:47-60): return `defaults()` unless the file parses to a `dict`, cache by
`st_mtime_ns`, and never let a hand-edited file stop the server booting. Write atomically (`tmp` then
`Path.replace`) under `_lock`, exactly like `creators._write` (creators.py:125-134).

### 5.2 `config.user_dir(uid)/"autopilot_status.json"` — per account, written by the runner

```json
{
  "state": "running",
  "started": "2026-11-19 09:00",
  "finished": "2026-11-19 09:14",
  "run": "20261119-090003-a1b2c3d4e5",
  "jobs": ["20261119-090003-a1b2c3d4e5"],
  "shorts": 4,
  "qc": {"PASS": 3, "WARN": 1},
  "scheduled": 2,
  "notified": false
}
```

`state` ∈ `running | done | failed` — `done` only when the jobs drained without error *and* at least one clip
came out, the exact rule at app.py:605. `qc` keeps its histogram shape from the source even though PeakCut's
clips carry `score` rather than a QC label; derive the bucket from the score (`>= 85` PASS, `>= 70` WARN,
else FAIL) and say so in a comment. `notified` is cleared to `false` on every new run and set true by
`/api/autopilot/seen`.

Both files are small, per-user, and inside `config.user_dir`, so they inherit PeakCut's existing backup and delete
semantics; `jobs.delete` and account deletion need no change.

---

## 6. Risks

**The source's single-user assumption, inverted.** In `gta6-clipper-main` there is one person, one workspace and
one crontab, so "the OS task runs `app.py --autopilot`" is obviously correct. On a server that line is a
catastrophe: it would run with the *installing admin's* privileges against *every* account's data, and N accounts
would mean N crontab lines that nobody can audit. The port must therefore (a) keep exactly one install-wide task,
(b) have that task iterate `auth.user_ids()` under `ctx.as_user(uid)` so every job is still scoped to its owner,
and (c) never accept a schedule from a non-admin. This is the single most important deviation and the reason
Tier A exists at all.

**Docker.** `peakcut/deploy/` ships a Caddyfile, an nginx config and `docker-compose.traefik.yml`: the common
deployment is a Linux container. Inside it there is no `schtasks`, no `launchctl`, and `crontab` is almost never
installed — `ap_task_exists` will return `None` and `plan()["cmd"]` will fail with `FileNotFoundError`, which the
source would turn into a 502 via its catch-all. `task_exists()` must therefore check `shutil.which(...)` before
running anything and report `None` early, and the "Turn on" button must be hidden when `public()["can_install"]`
is false. Autopilot must remain fully usable from Tier A in that container.

**`sys.executable` is not the app.** The source writes `sys.executable` into the task. In PeakCut that is the
interpreter running uvicorn, which may be a venv path, a `uv` cache path, or `/usr/local/bin/python` inside a
container that has no `studio` on its `PATH`. `plan()` must emit `sys.executable` *and* a `WorkingDirectory` /
`cd` so `-m studio.autopilot` resolves, and the doc should tell the operator that a container install simply
cannot use Tier B.

**The small `PATH` problem the source already knew about.** app.py:567's comment is the whole story: cron and
launchd start with a minimal `PATH`, so `ffmpeg` (which `render.py` shells out to) is not found and every render
fails with an error that looks like a code bug. The port must carry the same `PATH` injection
(`/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin` plus `$PATH` for cron) and, better, `plan()` should prepend
`shutil.which("ffmpeg")`'s directory when it is known.

**Double firing.** `TICK = 30` observes each minute twice. Without the `last_run` guard a single 09:00 slot starts
two runs and doubles the queue. The write must happen under the same lock as the read, before the thread starts.

**Unvalidated strings reaching `subprocess.run`.** `_install(pl["cmd"])` executes a list built from config. Every
element must come from the server (interpreter path, `DATA_DIR`, validated `HH:MM`, filtered day names) — never
from a request body. The source gets away with `c["time"]` because the only person who can type it is the person
who owns the machine; that is false here.

**Cost.** An autopilot run downloads, transcribes and renders with nobody watching. A mis-set `count` or an
`auto_watch` creator list that grows turns into unbounded spend. Clamp `count`, respect
`MAX_ACTIVE_JOBS_PER_USER` (config.py:184) and `MAX_USER_GB` (config.py:189) through the existing `jobs` path
(which already gates), and log every firing to `creators.log` so there is an audit trail.

**Host change is small but real.** `posting.enqueue(..., due_at=None)` is additive and defaults to today's
behaviour, but it touches the posting queue that `tests/` already exercises; run the existing posting tests before
and after.

**No new dependency.** Do not add APScheduler or croniter. `due()` is four comparisons and `slots()` is ten lines;
a scheduler library would be a heavyweight dependency for a feature that must be off by default.

---

## 7. Verification

**Pure unit checks** (no server, no ffmpeg) — the two ported algorithms:

```bash
cd peakcut && python -c "
from datetime import datetime
from studio import autopilot as a
t0 = datetime(2026, 11, 19, 9, 0)
# window respected, inclusive at the far end, step honoured
print([x.strftime('%d %H:%M') for x in a.slots(t0, 3, 90, '08:00', '23:00')])
# before the window -> waits for it; past it -> next day's opening
print([x.strftime('%d %H:%M') for x in a.slots(datetime(2026,11,19,6,30), 2, 90, '08:00', '23:00')])
print([x.strftime('%d %H:%M') for x in a.slots(datetime(2026,11,19,23,30), 2, 90, '08:00', '23:00')])
c = {'on': True, 'days': ['MON','WED','FRI'], 'time': '09:00', 'last_run': ''}
print(a.due(c, datetime(2026,11,18,9,0)), a.due(c, datetime(2026,11,18,9,1)))   # Wed -> True, then False
"
```

Expected: `['19 09:00','19 10:30','19 12:00']`, then `['19 08:00','19 09:30']`, then
`['20 08:00','20 09:30']`, then `True False`. 2026-11-18 is a Wednesday.

**Plan generation**, all three platforms (force the branch, since only one is ever native):

```bash
cd peakcut && python -c "
from studio import autopilot as a
cfg = {**a.defaults(), 'days': ['MON','WED','FRI'], 'time': '09:00'}
p = a.plan(cfg)
print(p['shown']); print('---'); print(p.get('wrapper') or p.get('cron') or '')
"
```

Assert by eye and in the test: Windows `/D MON,WED,FRI /ST 09:00`, macOS three `<dict>` blocks with `Weekday`
1/3/5 and `Hour` 9 `Minute` 0, Linux `0 9 * * 1,3,5` (minute before hour) ending in `# clipper-autopilot`.

**Route test** — add `peakcut/tests/test_autopilot.py` in the existing style, run by `tests/run.py`, which already
boots a throwaway server on 8799 with a temp `PEAKCUT_DATA`. The test should assert:
`GET /api/autopilot` as a non-admin → 404; as admin → 200 with `config`, `plan`, `task`, `can_install`;
`POST /api/autopilot/plan` with `{dry: true}` → 200 and **no** file written; with `{dry: false}` but no
`confirm` → still 200 preview and no file; with `{dry: false, confirm: true}` on a host with no scheduler →
400 with a sentence, not a traceback, and `autopilot.json` still written so the config is not lost;
`POST /api/autopilot/run` past its throttle → 429.

**End-to-end, the proof the feature works:**

```bash
cd peakcut && python -c "
from studio import autopilot as a, ctx
ctx.set_uid('<any real uid>')
cfg = {**a.defaults(), 'on': True, 'days': [a.DAYS[__import__('datetime').date.today().weekday()]],
       'time': __import__('datetime').datetime.now().strftime('%H:%M'), 'count': 1}
print(a.due(cfg))          # True, right now
a.save('<uid>', cfg)
print(a.run_once('<uid>')['state'])
"
```

Expected: a job appears in that user's job list, `jobs.busy_count()` rises, and
`config.user_dir(uid)/autopilot_status.json` shows `state: running` then `done` with `shorts >= 0`.
