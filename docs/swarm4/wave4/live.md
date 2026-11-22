# Live (slug `live`)

Skill loaded: **frontend-design**.

## What I built

`web/feat/live.js` — one main-menu page, "Live" (group **Make**, icon **video**, order **35**, address
`/app/live`), registered with `PeakCut.page("live", ...)`. The click handlers are on the plug-in object
registered with `PeakCut.add("live", { act: {...} })`, because `web/plugins.js` routes every `[data-act]`
click through the objects in `P._order` and never reads an `act` map off a page object. Two halves:

**1. The watch list.** On load it asks `GET /api/hunt/watching` and draws one row per streamer: the name, the
platform pill, the handle, and either the answer that channel already carries or the server's own sentence
when the server could not check it (`error`). Each row has **Check now** and **Remove**. Above the rows a count
says `N of M on air` and, when some rows went unchecked this call, how many. The empty state is a dashed box
that says nobody is on the watch list yet and what adding a channel gets you — no zeros, no fake rows.

The add form is a platform picker (**Twitch / Kick / YouTube** — the only three keys `hunt._LOOK` accepts, so
the picker cannot offer a platform that comes back a 400) plus a channel-name box and **Add to the watch list**,
which POSTs `POST /api/hunt/watch` with `{platform, ident}`. Enter in the name box does the same thing.

**2. The live check.** **Check now** on a row calls
`GET /api/hunt/live?platform=...&ident=...` — both query parameters are always sent, `encodeURIComponent`-ed
from the row's own stored values, because the route declares both with `Query(...)` and a missing one is a 422.
The answer replaces that row's line: an **On air** pill with the stream title in bold, then viewers and the
start time when the platform sent them; or an **Off air** pill with the server's `note`; or, on a failure, one
sentence in `.err`. A timestamp line ("Asked at 10:11") appears only for an answer this page actually fetched.

## Routes it reads (all verified present)

| Route | Where it is declared | Used for |
|---|---|---|
| `GET /api/hunt/watching` | `studio/api_preview.py:134` | the watch list, one row per streamer |
| `GET /api/hunt/live?platform=&ident=` | `studio/api_preview.py:121` | one channel, on air or not |
| `POST /api/hunt/watch` | `studio/api_preview.py:143` | adding a channel |
| `POST /api/hunt/unwatch` | `studio/api_preview.py:157` | removing a channel |

Row shapes come from `studio/hunt.py`: `watching()` returns `{key, platform, ident, name, live, title, viewers,
started, checked, error}`, and `look()` returns `{platform, ident, key, live, title, viewers, started, looked_at}`
or, when the platform would not answer, `{live: false, ..., note: "Not on air, or the platform would not say."}`.
Both are read as-is; nothing is added to them.

## Honesty rules I followed

- Every server string goes through `esc(...)`. Numbers go through a local `num()` first (`null` when the value
  is missing or not finite), so a missing viewer count is left out of the sentence rather than printed as `NaN`
  or `0` — "0 watching" would be a claim the platform did not make.
- `started` is shown as local time only when `new Date(...)` parses it; otherwise the raw string is shown cut to
  40 characters. Nothing is reformatted into a time it might not be.
- The count line counts what is on screen (`rows`) and says so; it never claims a total the server did not send.
- A failed fetch is one sentence in `.err` (and, for add/remove, a `PeakCut.toast`). There is no silent catch.
  The handler stores the failure against that one channel and redraws, so the sentence sits beside the channel
  it is about instead of at the top of the page.
- The one unavoidable caveat: `hunt.watching()` uses a time budget and puts `checked: false` on a row it had no
  time to ask about. That row reads "Not checked yet. Press Look again and this fills in." — the server's own
  fact, not a guess.

## What it cannot do yet

- **No auto-cut switch.** The wave 4 table lists one for this page, but nothing in `studio/` mentions an
  autocut setting (`grep -rn 'autocut\|auto_cut\|auto-cut' studio/` finds nothing), and a switch that saves
  nowhere would be a lie. It belongs on this page once a route exists; I did not invent one.
- The page does not start, stop or schedule a recording. `studio/live.py` has the recording side, but the brief
  scoped this page to the watch list and the live check, and no `/api/live/*` route is named in it.
- Answers are kept in memory for the visit only. Reloading asks the server again (which itself caches a live
  answer for `LIVE_FOR` = 60 s and a failure for `FAIL_FOR` = 30 s, so a reload is cheap).
- There is no per-row spinner beyond the button's own disabled state; a long list refreshes whole.

## Commands I ran, with results

```
$ node --check web/feat/live.js
JS OK                                   # exit 0

$ python tests/test_feat_files.py
{"files": 44, "checks": 358}
All checks passed.                      # exit 0

$ python tests/test_menu_pages.py       # not required by the brief, run because a page must sit in a known group
All checks passed. 193 ok               # exit 0; includes "ok   live.js draws its page"
```

Live server (`http://127.0.0.1:8798`, the shared test server; I did not restart it):

```
GET  /assets/feat                                  -> "live.js" in files: True
GET  /api/hunt/watching                            -> 200 {"watching": []}
GET  /api/hunt/live?platform=twitch&ident=shroud   -> 200 {"platform":"twitch","ident":"shroud","key":"twitch:shroud",
                                                           "live":false,"title":"","viewers":0,"started":"",
                                                           "looked_at":1795149614}
GET  /api/hunt/live?platform=twitch                -> 422      (confirms both parameters are required)
POST /api/hunt/watch    {"platform":"twitch","ident":"pc_wave4_probe"}  -> 200 {"key":"twitch:pc_wave4_probe",...}
POST /api/hunt/unwatch  {"platform":"twitch","ident":"pc_wave4_probe"}  -> 200 {"ok":true,"removed":true}
GET  /api/hunt/watching  afterwards                -> []        (the probe is gone; the server is as I found it)
```

Browser, on `/app/live` (tab opened to that address; the loader boots at ~1.4 s):

```
window.PeakCut._order contains "live"                        -> true
window.PeakCut._pages has a "live" page                      -> true
a .nav-item with data-v="live" is in the sidebar             -> true
#pclive_list on arrival                                      -> "Nobody is on the watch list yet. ..."
type pc_wave4_probe, press Add                                -> 1 .pclive-row;
                                                               count "0 of 1 on air. 1 not checked yet.";
                                                               row sentence "No Twitch channel with that name."
press Check now                                              -> count "0 of 1 on air."; row "Off air
                                                               Not on air, or the platform would not say."
press Remove                                                 -> 0 rows, count cleared, empty state back
server /api/hunt/watching afterwards                         -> [] (clean)
```

That trace proves all four handlers are wired and reachable: add, check, remove, and the load. The Twitch
lookup failed because the probe handle does not exist, which is exactly what the failure line should show.

## For the reviewer

- The `act` map must stay on `PeakCut.add`, not on `PeakCut.page` (see the comment above it). Moving it back
  silently kills every button.
- Ids used: `pclive_list`, `pclive_count`, `pclive_err`, `pclive_platform`, `pclive_ident`, `pclive_addbtn`.
  All prefixed and distinct from anything in `index.html`; `tests/test_feat_files.py` checks the clash rule.
- No changes were needed in files I do not own.
