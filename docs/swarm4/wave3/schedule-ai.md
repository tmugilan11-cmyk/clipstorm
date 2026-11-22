# schedule-ai

## What I built

`studio/schedule_ai.py` works out the schedule that makes PeakCut run one AI round by
itself, and returns it as text. It never installs anything and never raises.

Public functions, all with plain-English docstrings:

- `TIMES = ("06:00",)` with the reason written above it: early enough to finish before the
  person starts work, and before autopilot's own 08:00 to 23:00 window so the two schedules
  never ask for the same moment.
- `spec(user_id, times=TIMES) -> dict`, in the same shape `autopilot.spec` returns, so a
  reader written for one serves the other. Checked mechanically: the key set is identical,
  with `user_id` as the one extra key.
- `cmd_windows(spec) -> list[str]`, one `schtasks /Create` line per run time, quoted with
  `subprocess.list2cmdline` like autopilot does.
- `cmd_linux(spec) -> list[str]`, the cron lines, each ending in the marker `peakcut-round`.
- `due(spec, now=None) -> bool`, using `time.time()` by default, matching on the local clock.
- `note(spec) -> str`, one sentence for the page, ending in the promise that nothing is
  installed until the person says so.

Two decisions worth knowing:

- The schedule is kept separate from autopilot's, with its own task name `PeakCutRound`,
  its own crontab marker `peakcut-round`, and its own log `data/schedule-ai.log`, so
  removing one schedule never removes the other.
- `studio/learn.py` has no `if __name__ == "__main__"` block, so `python -m studio.learn`
  would import and exit without running a round. The command calls `learn.run()` instead.
  It is written without spaces, because the whole line has to sit inside a quoted `/TR`
  value and every inner space would need another layer of quotes.

## The file I own

`studio/schedule_ai.py` (one file, nothing else edited).

## The command and its output

    $ cd C:/Users/Asus/Documents/deepseek-harness/default-workspace/peakcut && python -m py_compile studio/schedule_ai.py && echo "py_compile: OK (exit 0)"
    py_compile: OK (exit 0)

Behaviour check, run the same way, printed:

    WIN  : schtasks /Create /TN PeakCutRound /TR "cmd /c cd /d C:\Users\Asus\Documents\deepseek-harness\default-workspace\peakcut && C:\Users\Asus\AppData\Local\Programs\Python\Python315\python.exe -c __import__('studio.learn',fromlist=['x']).run()" /SC WEEKLY /D MON,TUE,WED,THU,FRI,SAT,SUN /ST 06:00 /F
    LINUX: 0 6 * * 1,2,3,4,5,6,7 cd <folder> && PATH=/usr/local/bin:/usr/bin:/bin:$PATH python3 -c '__import__('"'"'studio.learn'"'"',fromlist=['"'"'x'"'"']).run()' >> <folder>/data/schedule-ai.log 2>&1 # peakcut-round
    NOTE : On Mon, Tue, Wed, Thu, Fri, Sat and Sun at 06:00 PeakCut would run one AI round by itself and apply at most two settings, and nothing is installed on this machine until you say so.
    MISSING KEYS: []
    due 06:00 wed True, 06:01 False, 05:59 False
    failsoft [False, False, False, False] True True

## What I could not do

- I did not run `python tests/run.py`. It starts a server and the wave brief puts it in the
  hands of the review agents; only `py_compile` and the behaviour checks above were run.
- The cron line, when this module is read on Windows, cannot know a real Linux folder, so
  it prints the Windows path and appends a note saying that folder needs changing. On a
  Linux machine it prints the true path. I chose an honest note over a guessed path.
- `cmd_windows` was never executed against a real Task Scheduler: the text is built, not
  installed, which is the rule for this module. Whether `schtasks` accepts the quoting can
  only be proven on a Windows machine that actually runs it.
- No page wiring and no route: this module only returns text. Whoever owns the page needs
  to call `spec`, `cmd_windows`, `cmd_linux`, `due` and `note`.
