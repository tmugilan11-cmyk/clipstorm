# log

What actually happened when a video failed.

One line of red text is all a failed card said, and the reason was already on disk. This puts the end of that
file behind a "Show log" control on the error line, and adds the key the control reads.

Files I touched, and nothing else:

- `web/feat/log.js` (new, 116 lines)
- `studio/server.py` (one helper block after `_job_or_404`, one new key on the existing route)

Skill loaded: `frontend-design`.

## Where the log is

The pipeline had no logger. `studio/jobs.py:922-928` catches the exception, and line 923 writes the traceback
into the job's own folder:

```python
except Exception as e:
    (Path(job["dir"]) / "error.log").write_text(traceback.format_exc(), encoding="utf-8")
    ...
    _set(job, status="error", error=safe.friendly(e), stage="Stopped")
```

So there is one file, `error.log`, beside `job.json`. A live recording also appends `ffmpeg.log` in the same
folder (`studio/live.py:276`), and that is the whole set. Nothing writes a log for a job that never started.

`job["dir"]` is on the raw job but deliberately not in the answer: `jobs.public()` strips
`("dir", "user", "source_path", "recover")` at `studio/jobs.py:164-190`. That is the right place to keep it.

## Backend

### The route

`studio/server.py:768-773`. The original three-line shape is still the first call; my lines were added around it,
and the call was not changed:

```python
@app.get("/api/jobs/{jid}")
def get_job(jid: str):
    job = _job_or_404(jid)                  # the job itself, so the answer can also carry the end of its log
    out = jobs.public(job)                  # every key this route always sent, unchanged
    out["log_tail"] = _job_log_tail(job)    # plus the log: text only, and nothing at all when there is no log
    return out
```

One call to `_job_or_404`, not two. `jobs.get` (`studio/jobs.py:291-294`) is a dict lookup plus an owner check,
so resolving it once and reusing it cannot cost anything or disagree with itself.

Every existing key is untouched: the answer is the same 19 keys plus `log_tail`, proven by sorted key list
below. No `dir`, no `user`, no `source_path` ever leaves.

### The helper

Sits right after `_job_or_404` in `studio/server.py`. Constants `LOG_TAIL_LINES, LOG_TAIL_CHARS, LOG_TAIL_BYTES
= 80, 400, 64 * 1024`.

```python
def _job_log_tail(job) -> list:
    """The last lines of this job's log, oldest first, 80 at most, capped per line. [] when there is no log."""
    folder = str(job.get("dir") or "").strip()
    d = Path(folder) if folder else None
    if not d or not d.is_dir():
        return []
    lines = []
    for name in ("ffmpeg.log", "error.log"):   # the traceback goes last, so a long recording cannot push it out
        try:
            size = (d / name).stat().st_size
            with (d / name).open("rb") as h:
                h.seek(max(0, size - LOG_TAIL_BYTES))
                raw = h.read()
        except OSError:
            continue                           # no such log for this job: that is not an error, just nothing to show
        part = raw.decode("utf-8", errors="ignore").splitlines()
        if size > LOG_TAIL_BYTES:
            part = part[1:]                    # the first one starts in the middle of a line
        lines.extend(_scrub(x)[:LOG_TAIL_CHARS] for x in part)
    while lines and not lines[-1].strip():
        lines.pop()                            # no empty space at the bottom of the box
    return lines[-LOG_TAIL_LINES:]
```

Four decisions worth naming:

- **Tailing a file, not reading it.** It seeks to the last 64 KB instead of opening the whole thing, which is the
  same pattern the codebase already uses in `creators.read_log` (`studio/creators.py:207-226`). A log that grew
  to a gigabyte costs the same as one of a few lines.
- **80 and 400 are enforced here, not trusted.** `splitlines()` on a 64 KB window can hold thousands of lines;
  `[-80:]` is what leaves. A single line of any length is cut to 400, so one giant traceback argument cannot
  fill the box.
- **Missing means empty, never an error.** No folder, no file, a folder where the file should be, a permission
  problem: all `OSError`, all `[]`, all HTTP 200. That is what the brief asked for and it is also the honest
  answer: "no log" is a fact about the job, not a failure of the request.
- **Decoding cannot throw.** `errors="ignore"` on a byte window that starts mid-character; proof 10 below feeds it
  invalid UTF-8 and it returns text.

### Not returning a server path

The brief says never return a server path, and a raw traceback disagrees: its middle lines are
`File "C:\...\peakcut\studio\jobs.py", line 923`. So the text is scrubbed before it is capped:

```python
def _log_roots() -> tuple:
    """Where this copy of PeakCut lives, in both spellings, longest first, so a folder is gone before its parent."""
    ...
LOG_ROOTS = _log_roots()

def _scrub(text: str) -> str:
    """Take the folders this copy runs in out of a log line: what is left names a file, not somebody's disk."""
```

`config.ROOT` and `config.DATA_DIR`, each as `\`-form and `/`-form, with and without a trailing separator, plus
the system temp folder with a trailing separator only, longest first so a subfolder goes before its parent. The
bare word `tmp` is deliberately not scrubbed; it is an ordinary word in a log line.

`_scrub` runs **before** the 400-character cut, so truncation can never re-expose a path that the scrub would
have removed later.

What a person sees is `File "studio\jobs.py", line 923` and `File "users\u_local\jobs\a\job.json"`: enough to
locate the failure in the code, and no mention of whose disk it is on. `LOG_ROOTS` is computed once at import;
ten entries on this box.

## Front end

`web/feat/log.js`, 116 lines, same shape as `heard.js`: an IIFE, `PeakCut.css("log", ...)`, then
`PeakCut.add("log", { after: { drawJobs(root) }, act: { joblog(b) } })`.

`data-act="joblog"` is mine alone. I grepped all 79 `data-act` values in the frozen `index.html`; `joblog` is not
among them, so `plugins.js` routes the click to my `act` and nothing else fires.

What it does:

- `after.drawJobs(root)` walks `PeakCut.state().jobs` and acts only on a job with `job.error`. It appends
  `<button class="rep joblog-btn" data-act="joblog" data-j="..." aria-controls="logbox-...">Show log</button>`
  to that card's existing `.err` line, so it sits next to "Report this" and inherits the `.err .rep` styling:
  an underlined word, not a new kind of button.
- The box is a `<div class="joblog">` inserted after the error line, empty until opened. `:empty{display:none}`
  keeps a closed card pixel-identical to today's.
- Nothing is fetched until someone asks. The first click sets the button to `Hide log`, shows `Reading the log...`,
  and calls `GET /api/jobs/{jid}`. Later opens reuse the cached lines; a failed read is retried on the next open.
- Every line goes through `esc()`: `lines.map(esc).join("\n")`. The `<pre>` gets its content as text, never as
  markup.
- Empty list: `<p class="joblog-none">This video has no log written for it.</p>`, wording as the brief gives it.
- The read failure case is one quiet line inside the box, `The log could not be read just now. <reason>`. It does
  not toast, and it does not throw into the page.

Two details that took a second pass:

- **The redraw problem.** `drawJobs` calls `put(el, jobHtml(j))`, which rewrites a card's innerHTML whenever the
  markup changed. Any decoration inserted into a card can therefore vanish. It survives here for two reasons: a
  card is only rewritten when its own markup changed, and `paint()` is idempotent, so the next pass puts the
  button and box back. `paint` also guards its DOM write behind `box.dataset.log`, a stamp
  (`closed` / `loading` / `failed` / `lines` / `empty`), so an unchanged repaint does not rebuild the `<pre>` and
  a reader scrolled halfway down a long traceback keeps their place.
- **Keyboard and motion.** The `<pre>` is `tabindex="0"` with a visible focus ring, because a scrolled log you
  cannot reach with a keyboard is not readable; it also has `aria-label="Log for this video"`. `aria-expanded`
  tracks the button. The only animation is a 140 ms fade on open, dropped under
  `@media (prefers-reduced-motion: reduce)`.

Styling uses the existing palette only: `--line`, `--muted`, `--text`, `--dim`, `--line-2`, `--brand`, `--bad`,
`--r-sm`, mono at 12px/1.55 with `pre-wrap` and `overflow-wrap:anywhere` so a long path-like token wraps instead
of scrolling the page sideways. No shadows, hover is colour only, no new colour.

## Verification

Every command was run from `peakcut/`.

**JS parse.**

```
$ node --check web/feat/log.js && echo "JS OK"
JS OK
```

**Server parses.**

```
$ python -c "import ast;ast.parse(open('studio/server.py',encoding='utf-8').read());print('PY AST OK')"
PY AST OK
```

**The served file list already includes it** (the server serves `web/feat/*` by listing the folder, so no restart
needed for the front end):

```
$ curl -s http://127.0.0.1:8798/assets/feat
{"files":["autopilot.js","day.js","filters.js","grid.js","heard.js","log.js","mood.js","peek.js","pill.js","stage.js","stats.js","style-tiles.js"]}
```

**The live route, on the process that is still running the old code.** This is the restart-free check the brief
asked for, and it shows exactly the split the brief predicts: healthz fine, the file served, the route answering
without my new key, because Python was imported before I edited it.

```
$ curl -s http://127.0.0.1:8798/healthz
{"ok":true}

$ curl -s -b "pc_uid=u_local" http://127.0.0.1:8798/api/jobs/20261119-171742-d88fe196d1 -o joblive.json -w "http %{http_code}\n"
http 200

$ python -c "..."
keys: 19
log_tail present: False
dir leaked: False
status: done | error: None
```

**The helper, called directly, since the route cannot serve it yet.** Twelve cases in a throwaway temp folder:

```
1 empty folder        -> []
2 missing folder      -> []
3 no dir key          -> []
4 dir is empty string -> []
5 100 lines           -> 80 lines, 'line 020' -> 'line 099'
6 1000-char line      -> 400 chars
7 traceback           -> ['Traceback (most recent call last):',
                         '  File "studio\\jobs.py", line 923, in _run',
                         '  File "users\\u_local\\jobs\\x\\job.json", line 1',
                         'RuntimeError: ffmpeg said no']
7 no server path      -> True
8 both files          -> 80 lines, 'frame 124' ... 'RuntimeError: ffmpeg said no'
9 trailing blanks     -> ['a', 'b']
10 invalid utf-8      -> ['a', 'b', '', '', '   ', 'good line', ' bad bytes', 'last']
11 log is a folder    -> ['a', 'b']
12 real job folder    -> [] | status: done
```

Case 5 is the cap and the order: 100 lines in, the last 80 out, oldest first. Case 7 is the scrub: the traceback
keeps its shape and loses its folder. Case 8 is the ordering that matters: with 200 ffmpeg lines and a traceback
in the same folder, the traceback is at the bottom of the answer and survives the 80-line cut.

**The same proof as a one-liner**, as the brief asked:

```
$ python -c "..."
none      -> [] [] []
120 lines -> 80 lines L40 .. L119
900 chars -> 400
traceback -> ['File "studio\\jobs.py", line 923', 'RuntimeError: boom']
no path   -> True
OK
```

**The route body itself, run under a user context.** The real job list is empty in a plain process because
`jobs.list_jobs()` is per-user (`ctx.uid()`), so this loads the real on-disk `job.json`, points it at a temp
folder with a log, and calls the actual `get_job` view function:

```
keys: ['ai', 'blocks_done', 'blocks_total', 'clips', 'created', 'creator', 'duration', 'error',
       'heard_to', 'id', 'kind', 'log_tail', 'options', 'progress', 'source', 'stage',
       'status', 'title', 'uploader', 'watched_pct']
log_tail: ['Traceback (most recent call last):', '  File "C:/x/peakcut/studio/jobs.py", line 923', 'RuntimeError: ffmpeg said no']
dir leaked: False
source has no path: True
bad id -> HTTPException 404: No such video
```

20 keys: the 19 that were always there, unchanged, plus `log_tail`. A bad id still 404s the same way.

**In the browser, at `http://127.0.0.1:8798/app`.** `window.PeakCut._order` is
`["heard","filters","grid","log","peek","mood","stage","pill","stats","style-tiles","autopilot","day"]`,
`PeakCut.log.act` is `["joblog"]`, `PeakCut.log.after` is `["drawJobs"]`, and `#pcss_log` is in the document.
With a card seeded to a failed job:

- the button appears inside `.err`, labelled `Show log`, with `aria-expanded="false"` and `aria-controls`
  matching the box id;
- clicking opens the box, fills the `<pre>`, and flips the label to `Hide log`; clicking again closes it;
- the `<pre>` computes to `ui-monospace, SFMono-Regular, ...`, `white-space: pre-wrap`, `max-height: 260px`,
  `overflow: auto`;
- hostile content, `<script>alert('xss')</script><b>bold</b><i>i</i>` plus quotes, ampersands and U+2028, comes
  back as literal text with `querySelectorAll("script,b,i").length === 0`;
- a second open makes no second request; after a forced failure, closing and reopening does ask again, and the
  recovered text shows;
- a card with `error: null` gets neither button nor box;
- an empty `log_tail` shows `This video has no log written for it.`

One browser detail worth passing on, because it will bite anyone testing these features: the `after` hooks fire
from `repaint()`, which `PeakCut.boot` runs on `requestAnimationFrame`, and that is paused in a backgrounded tab.
A hidden tab therefore never shows a freshly inserted control by itself. `document.dispatchEvent(new
Event("peakcut:render"))` runs the identical path and is what I used.

## What I could not test

The one real job on this box is a job that succeeded, so its folder has no log and its answer is `[]` — the empty
state is verified against real data and against the real route body. A **real** traceback was never served end to
end over HTTP, because that needs a job that fails, and the route itself needs a restart to carry the key. Both
were exercised by calling the actual view function and the actual helper instead, which is the same code the
route runs, minus FastAPI's serialisation of a list of strings. There is nothing in that step that can fail.

`HEALTHZ` and the route were checked against the running server; `python tests/run.py` was not run, since it
starts its own copy and my change is additive to one route that the existing tests do not touch. The brief asked
for `node --check`, the AST parse, the restart-free curl, and a direct helper proof; all four are above.

## Needs from files I do not own

- **`studio/server.py` needs a restart** for `GET /api/jobs/{jid}` to start answering with `log_tail`. Until
  then the front end shows `This video has no log written for it.` for every card, because `d.log_tail` is
  `undefined` and the `Array.isArray` guard treats that as empty. That is the correct failure direction for a
  mixed-version window: no crash, no wrong text, just the empty state. Once restarted, the same code shows real
  lines with no front-end change.
- Nothing else. The CSS, the button styling and the `.err` line I decorate all already exist.
