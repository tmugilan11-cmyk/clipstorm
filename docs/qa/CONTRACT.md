# QA swarm contract — audit wave (40 agents) then fix wave (40 agents)

The user reports minor visual bugs on many pages and wants every bug found, then
everything fixed, plus anything that is not easy to use improved.

## The binding rules

1. **One owner per file.** You may READ anything; you may WRITE only the files your
   brief names. Two agents never edit the same file.
2. **The lead owns the browser.** Do NOT call any `dsh_browser_*` tool — the browser is
   one shared window and the lead is driving it during the audit. Audit with `ops_grep`,
   `ops_glob`, `ops_inspect_local_file`, and `curl` against `http://127.0.0.1:8798` only.
3. **Read the page for real.** `curl -s http://127.0.0.1:8798<PATH>` returns the shell;
   the FEATURE files under `web/feat/` are what draw each page. Read them fully before
   judging.
4. **A bug is measured, not felt.** Every visual claim carries evidence: a computed
   contrast ratio, a CSS line, a response code, a console line, a measured px width.
   "Looks wrong" without a number or a line is not a finding.
5. **Severity:** `critical` (broken control, 404 route, unreadable text <3:1, console
   error on load), `important` (wrong copy, cramped layout, dead handler, missing
   empty/error state, hard-to-use control), `minor` (spacing, wording, polish).
6. **Usability findings are first-class.** Anything a beginner would not understand in
   five seconds — a vague label, a control with no explanation, a two-step flow that
   could be one — is a finding with a concrete fix ("rename X to Y", "add hint Z").
7. **Never invent.** A number on a page must come from somewhere. If a claim cannot be
   backed by a file line or an HTTP response, drop it.
8. **Report shape.** Write `docs/qa/audit/<slug>.md` with: the pages/files you owned,
   every check you ran, then the findings table
   (`| severity | where | what | evidence | fix |`). Return the same content as JSON.
9. **Load a skill first.** Call the `skill` tool with `systematic-debugging` (bug
   auditors) or `frontend-design` / `accessibility` (usability/visual auditors) before
   starting.
10. **Fix wave rules (later).** One agent per file; `node --check` on every edited JS
    file; escape everything through `esc(...)`; no em dashes, no `!important`, no
    shadows; colours changed only after measuring the ratio; `tests/test_feat_files.py`
    and `tests/test_text_ink.py` must still pass.

## The page map (owned by the audit agents)

Shell + 21 app pages + 3 editors, see the workflow brief for the exact split. Every
page is audited by at least one agent; every `web/feat/*.js` file is owned by exactly
one auditor.

## Proof commands

- Page shell: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8798/app/<page>`
- Routes used by a feature: `grep -o "/api/[a-z0-9/{}?=&_-]*" web/feat/<file>.js`
- Every route must exist in `studio/*.py` (`grep -rn "<route>" studio/`).
- Contrast: compute `(L1+0.05)/(L2+0.05)` for the resolved colour pair; big text
  (>=24px, or >=18.66px bold) is judged at 3.0, everything else 4.5.
