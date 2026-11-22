# Usage (wave 4, slug `usage`)

Skill loaded: **frontend-design**.

## What I built

`web/feat/usage.js` — one file, one plug-in. It puts a **Usage** row in the main menu under **Set up**, order 55,
icon `chart`, and draws the AI spend on its own page.

The page shows, in this order:

- **Who answered.** The service and the model straight from the route: `Service Logfare. Model <name>.` When
  `ready` is false it says no AI key is saved and points at AI in Settings instead of pretending to have numbers.
- **Three figures.** AI calls, tokens, and *What it cost*. The first two come from `calls_total` and `tokens_total`,
  with a "today" line under the call count. The cost cell reads **Not known**, with the reason printed beneath it:
  PeakCut measures tokens, not money, and the AI service bills whoever owns the key on its own rates, so any
  figure printed here would be a guess.
- **Tokens per day.** A bar per day of the `daily` array the route returns, drawn as inline SVG with the date under
  each bar, a tooltip per bar, and one aria-label sentence for the whole chart. Days with zero tokens get a 2px
  tick rather than nothing, so the row of days never reads short. Below it, one line naming the busiest day.
- **What the AI worked on.** A bar per purpose from `by_purpose` (top 8), so the tokens are attributed to work.

The empty history is a first-class state, not a blank page: a counted zero is a fact, so the three figures stay
(0 calls, 0 tokens, cost not known) and the chart and split are replaced by the sentence **No AI call has been
made yet.** plus what will make one appear.

A failure is one sentence in the page: `Could not read the AI usage: <reason>` inside `class="err"`, with a line
saying the rest of PeakCut keeps working and to press Refresh. There is no silent catch anywhere.

One control, one plain-English `.hint`: the Refresh button, "Asks the server again. Nothing is charged by pressing
this."

## Routes it reads

Only one, and it exists:

- `GET /api/usage` — declared at `studio/server.py:1374`, served by `studio/usage.py` `summary()`.

Fields used: `ready`, `provider`, `model`, `calls_total`, `tokens_total`, `today_calls`, `today_tokens`, `problem`,
`daily[]` (`day`, `tokens`, `calls`), `by_purpose[]`.

**There is no cost field on this route.** I checked the live payload: the keys are `by_creator`, `by_purpose`,
`calls_total`, `daily`, `model`, `problem`, `provider`, `ready`, `recent`, `today_calls`, `today_tokens`,
`tokens_total` — nothing about money. So the page says the cost is not known and never multiplies tokens by a
price it was not given.

## The one deviation from the brief: the page slug

The brief asked for path `usage`. I registered the page as **`ai-usage`**, keeping the label "Usage", group
"Set up", icon "chart" and order 55 exactly as asked.

Two independent reasons, both inside the frozen shell I am not allowed to edit:

1. `web/index.html:1354` maps `usage` in `ROUTES`, and `web/index.html:1404` handles `v === "usage"` and calls
   `loadUsage()` **before** the `PeakCut.hasPage(v)` branch. A page named `usage` would therefore never paint — the
   built-in view always wins.
2. `tests/test_menu_pages.py:109` lists `usage` in `CLASH` ("a page may not live where a built-in page lives"), so
   path `usage` fails the repo gate outright.

The **file** is still `web/feat/usage.js` with plug-in id `usage`, because `tests/test_feat_files.py` requires the
plug-in name to equal the file stem. So: file `usage.js`, plug-in `usage`, menu page `ai-usage`.

If the lead wants the address to read `/app/usage`, that needs a change in `web/index.html` (remove the built-in
usage view's precedence) and in `tests/test_menu_pages.py`'s `CLASH` set — neither is mine to edit.

## What it cannot do yet

- **No money figure, by design.** Until `studio/usage.py` returns a cost (or the per-token price it was charged
  at), the page cannot show a spend in dollars and will keep saying Not known.
- **No date range control.** It draws the 30 days the route sends; there is no way to ask for a different window
  because the route takes no parameters.
- **No per-creator or per-purpose detail view.** `by_creator` and `recent` arrive on the route but I do not render
  them; the page answers "what did the AI cost" rather than "which video ate it". A follow-up could add a table
  from `recent`.
- **The refresh re-reads the route only.** There is no live push; the page redraws when opened or when Refresh is
  pressed.

## Commands I ran, and what they said

All from `C:\Users\Asus\Documents\deepseek-harness\default-workspace`, workdir `peakcut`.

| Command | Result |
|---|---|
| `node --check web/feat/usage.js` | `JS OK` |
| `python tests/test_feat_files.py` | `{"files": 46, "checks": 374}` → **All checks passed.** |
| `python tests/test_menu_pages.py` | `All checks passed. 192 ok` (at the time all ten `ai-usage` checks passed) |
| `GET http://127.0.0.1:8798/api/usage` | `200`, keys as listed above, `calls_total 0`, `model deepseek-v4.1-flash-1017`, `provider Logfare`, `ready True` |
| `GET http://127.0.0.1:8798/assets/feat/usage.js` | `200`, `14419` bytes |

`grep` on the route rather than a guess: `studio/server.py:1374` `@app.get("/api/usage")`.

### Headless render checks (node, stubbing window/document/PeakCut)

- Empty payload: rendered, showed the model, showed "No AI call has been made yet.", no `NaN`/`undefined`.
- Populated synthetic payload (1234 calls, 987654 tokens, 3 days, a purpose named `caption fix <b>`):
  - ledger read `AI calls 1,234` / `Tokens 988k` / `What it cost Not known`;
  - 2 bars plus 1 zero-day tick, aria-label `Tokens per day over 3 days. Highest day 42,000 tokens.`;
  - the injected `<b>` came out as `&lt;b&gt;` — escaping holds on server strings;
  - `NaN`/`undefined` absent.
- Failing api throwing `route said 500`: page showed `Could not read the AI usage: route said 500` in `class="err"`.

### Live browser check

Opened `http://127.0.0.1:8798/app/ai-usage` and read the real DOM:

- the sidebar row renders as **Usage**, sitting between **AI** (50) and **Storage** (60), i.e. order 55;
- `PeakCut.hasPage("ai-usage")` is true; the page definition carries `nav Usage`, `group Set up`, `icon chart`,
  `order 55`;
- `#usg_body` painted the three figures (`AI calls 0 · None today`, `Tokens 0`, `What it cost Not known`) above the
  sentence "No AI call has been made yet.";
- the Refresh button is present, the `.hint` is present, `data-act="usgload"` resolves to the `usage` plug-in only,
  and there is no `.err` on the page and nothing in the console.

## One failure that is not mine

`python tests/test_menu_pages.py` now reports one failing check:

```
FAIL creators sits under a known heading   'Creators' is not one of: Make, Understand, Look and sound, Connect, Account, Help, Set up
```

That is `web/feat/creators.js`, another agent's file in this wave. I did not touch it. My own checks
(`ok ai-usage ...`, all ten) pass. Whoever owns `creators.js` needs to move it under one of the allowed headings —
likely "Make" or "Understand".
