# Swarm 3 contract

Read this before writing anything. It is short and every line is a rule.

## How the UI now works

`web/index.html` is one 7,000-line file and is **frozen** — do not edit it.
Every new UI feature lives in **its own file** in `web/feat/<slug>.js`.
`web/plugins.js` loads every file in that folder and wires it into the page.

A feature file looks like this:

```js
/* what it does, in one sentence */
window.PeakCut.add("slug", {
  tools() { return `<h2>Title</h2><p class="help">One line.</p><div id="myslug"></div>`; },
  load()  { /* called when Settings > Tools opens */ },
  act:    { myslugbtn(el) { /* [data-act="myslugbtn"] */ } },
  keys(e) { /* return true if you handled the key */ },
  after:  { drawJobs(el) { /* rewrite markup another drawer produced */ } },
});
```

Supported keys: `tools()`, `load()`, `act{}`, `keys(e)`, `after{}`.

`after` hooks fire when these change: `drawJobs` (#jobs), `drawOverview` (#ov),
`drawCreator` (#cbody), `drawClipDlg` (#clipdlg), `drawSettings` (#sform),
`drawShell` (.topbar). Keep them cheap and idempotent — they run on every frame
the markup changes.

Helpers available from `window.PeakCut`:
- `PeakCut.api(path, opt)` — same as the page's own fetch wrapper (throws on error)
- `PeakCut.send(path, body, method)` — JSON POST
- `PeakCut.toast(msg, kind)` — `kind` is `"ok"` or `"bad"`
- `PeakCut.state()` — the page state `S` (jobs, creators, accounts, status, view...)
- `PeakCut.css(id, text)` — add your stylesheet once

And global helpers from the page: `$ (querySelector)`, `$$`, `esc()`, `ic(name)`,
`put(el, html)`, `api()`, `send()`, `toast()`.

## Rules (all of them are enforced by a reviewer)

1. **Edit only your own file(s).** One file per feature: `web/feat/<slug>.js`.
   Backend agents own the Python file named in their brief.
2. **`node --check` must pass** on every file you wrote. Run it, and paste the result.
3. **Escape every server string** with `esc()` before putting it in HTML.
4. **Never `innerHTML` from a value you have not escaped.** Same rule, stated twice on purpose.
5. **Plain English, short sentences, no emoji, no em dash.** Say what will happen.
6. **Fail soft.** If a request fails, show one quiet line; never throw into the page.
7. **No new dependencies.** ffmpeg, httpx, Pillow and the browser are enough.
8. **Load a skill first** (`frontend-design`, `ui-design-guide`, `python-patterns`,
   `fastapi-patterns`, `python-testing`, `api-design`). Name it in your report.
9. **Test server is live on `http://127.0.0.1:8798`.** Use it. Do not restart it.
10. **Do not run `git`.** This is not a repo.

## Proving it works

Static check (a file that exists but is never called is a lie):
```bash
cd peakcut && node --check web/feat/<slug>.js && echo "JS OK"
```

Live check — prove the page really runs your code:
```bash
cd peakcut && python - <<'PY'
import httpx
r = httpx.get("http://127.0.0.1:8798/assets/feat").json()
print("served files:", r["files"])
PY
```
and, if you have browser tools, load `/app` and check `window.PeakCut._order`
contains your slug. If you have no browser tools, prove it by static reasoning
plus the served-file check, and say so.

## Report

Write `peakcut/docs/swarm3/<slug>.md` with: what you built, the endpoints you
used, the exact commands you ran and their output, what you could not test, and
anything a reviewer should look at. Return only:

```
status: DONE | DONE_WITH_CONCERNS | BLOCKED
skill: <name>
files: <paths>
gate: JS OK | n/a | FAILED: <why>
live: <what you ran and what it printed>
needs: <changes needed in files you do not own, or "none">
concerns: <or "none">
```
