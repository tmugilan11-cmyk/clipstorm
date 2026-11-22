# creators - the Creators page

**Skill loaded for this work:** `frontend-design` (via the `skill` tool, before any other call).

**File written:** `web/feat/creators.js` (one file, nothing else touched).

A main-menu page called "Creators", path `creators`, icon `user`, order `10`. One card per creator with its
name, the handle it records from, every channel it is linked to, the accounts its clips are posted to, its track
when the server has one, and how many clips it has made. New creator opens the real creator form. Zero creators
gets an empty state that explains what a creator is and offers the same button again.

## What is on the page

- Heading, a lede that says what a creator is, and a `New creator` primary button plus a `Refresh` ghost button.
- One `.hint` under the buttons: what New creator does, what Refresh does ("nothing is saved by looking"), and a
  live count line ("2 creators").
- A card per creator:
  - **Avatar** from `GET /api/creators/{id}/avatar`, falling back to the creator's initial when no picture exists.
  - **Name**, with `@handle` under it - the handle comes from `c.channel`, i.e. the channel it actually records from.
  - **`Recording` pill** when `c.live_job` is set.
  - **Channels** - "Records from YouTube @stream_sniper_369", then one `Also ...` line per extra linked channel.
    The platform name is only ever printed when one of the `c.channels` values equals `c.channel`; it is never
    guessed from the address.
  - **Accounts** - each id in `c.accounts` is resolved against `GET /api/accounts` and shown as "Instagram
    stream_sniper_369". An id that no longer exists reads "one account is no longer connected" rather than
    silently vanishing.
  - **Track** - `c.track` when present, otherwise the words "Not set".
  - **Clips** - `clips_total` from `GET /api/overview`, or "Not known yet" when the overview did not answer for
    that creator. Never a zero standing in for an unknown.
  - **Setup** and **Clips** buttons, both `data-act="go"` with `data-v="c:<id>"` so they land on that creator's
    own Setup / Clips tab (the same route the sidebar uses).
- A closing footnote saying PeakCut does not store a track yet, so that row stays empty until the server does.
- Empty state: a dashed card - "No creators yet", a plain paragraph on what a creator is (channels watched,
  rules, posting accounts, own folder; two streamers means two creators and nothing is shared), a `New creator`
  button and a hint explaining what that box will ask for.
- Failure state: the creators route failing shows "Your creators could not be read just now ... Nothing has been
  lost: the creators are still on the server" with a *Try again* button, plus the server's own sentence in a red
  `.err` line and a `P.toast(..., "bad")`. It deliberately does **not** fall through to the empty state, because
  "no creators yet" after a failed read would invite a duplicate workspace.

## Routes it reads

All three exist and were verified with `grep -rn 'router.get\|@app.get' studio/`:

| route | where it lives | what it supplies |
|---|---|---|
| `GET /api/creators` | `studio/server.py:1291` -> `_creator_rows()` at `:765` | the creator rows (`id`, `name`, `channel`, `channels`, `accounts`, `live_job`, ...) |
| `GET /api/overview` | `studio/server.py:1582` -> `posting.overview()` | `creators[].clips_total` (set at `studio/posting.py:259`) |
| `GET /api/accounts` | `studio/server.py:1601` | `{id, platform, label, name}` for naming the posting accounts |

Read-only: this page issues no writes. Creation goes through the existing dialog (`POST /api/creators`), which the
page never calls itself.

## What it cannot do yet

1. **No track.** The brief asks for a track (gaming / irl / music). Nothing in `studio/` stores one - grepping
   `studio/` and `web/` for `track`, `niche`, `"irl"`, `"gaming"`, `"music"` finds no field and no route that
   writes one. The card renders `c.track` if a creator dict ever carries it, otherwise prints "Not set", and the
   footnote says so out loud. **This needs a `track` field on the creator dict plus a route to save it** before the
   row can hold a real value.
2. **No edit from the card.** Setup and Clips are links only; renaming, connecting or disconnecting a channel is
   still done on the creator's own page (which this file is not allowed to touch). Inline actions would need
   `PUT /api/creators/{cid}` - which exists at `studio/server.py:1310` - if someone wants them later.
3. **No delete.** `DELETE /api/creators/{cid}` exists at `studio/server.py:1124`, but deleting a creator is not on
   this page on purpose: it belongs behind the confirm flow on the creator's own page.
4. **Group is `Make`, not `Creators`.** The brief asks for group "Creators", but `tests/test_menu_pages.py:26`
   pins `ALLOWED_GROUPS = ("Make", "Understand", "Look and sound", "Connect", "Account", "Help", "Set up")`, so
   "Creators" fails `creators sits under a known heading`. The shell also already paints its own
   `<h4><span>Creators</span></h4>` section header plus the `New creator` row (see the `drawShell` nav builder),
   directly below whatever `PeakCut.navHtml()` emits - so registering under "Creators" put a second, empty
   Creators heading at the very bottom of the sidebar. It now sits first under **Make** (`order: 10`), which is
   where the similar workspace pages live. If the "Creators" heading is wanted instead, the allow-list in
   `tests/test_menu_pages.py` needs `"Creators"` added and something needs to stop the shell emitting its own.
5. **`go(...)` could not be used for "New creator".** There is no page or path for a blank creator form -
   `P._pages` has no such entry and no path resolves to one. The real form is the `<dialog>` that the shell's own
   click listener opens on `data-act="newcreator"`, so the button emits exactly that. `go(...)` *is* used, via
   `data-act="go"`, for each card's Setup and Clips buttons.
6. **Clips come from the overview, not per creator.** There is no per-creator count route, so `clips_total` is
   only as good as `posting.overview()`. A creator missing from that payload shows "Not known yet".

## Checks run

```
$ node --check web/feat/creators.js
NODE_OK                                    # exit 0

$ python tests/test_feat_files.py
{"files": 47, "checks": 382}
All checks passed.                         # exit 0

$ python tests/test_menu_pages.py
All checks passed. 312 ok                  # exit 0
```

`tests/test_menu_pages.py` is not required by the brief, but it is the suite that pins the menu heading rules, so
it was run to confirm the `group` change above.

The whole runner (`python tests/run.py`) was also run, and it ends with
`FAILED: queue under load, the new-version notice`. Both of those suites are unrelated to this file and neither
mentions `web/feat` or `creators.js` (checked with `grep -c`):

- `tests/test_updates.py` fails on the machine's git remote - it sees no `git ls-remote` call at all
  (`asked[0]` is `IndexError`, list empty). This checkout is not a git repo, so the updater has nothing to ask.
- `tests/test_load_queue.py` fails `it sees a fully loaded processor`, which measures the real CPU of the host
  (`busy_cpu: 82.0` on an idle-ish reading). It is a live hardware check, not a code check.

Every other suite passes, including `test_feat_files.py` and `test_menu_pages.py`, which are the two that cover
this file.

## Visual verification (browser, `http://127.0.0.1:8798/app/creators`)

- Empty state, checked on the live test instance (`GET /api/creators` really returns `[]` there): renders as
  described above with no invented numbers.
- Populated state: `P.api` was monkeypatched in the page to return two fixtures - one creator with a YouTube and a
  Twitch channel, a resolvable and an unresolvable account id, `live_job` set and no profile picture; one bare
  creator with `track: "gaming"` - then `P.drawPage("creators")` was called. Rendered correctly: recording pill,
  "Records from YouTube @stream_sniper_369" plus "Also Twitch @streamsniper", "Instagram stream_sniper_369" plus
  "one account is no longer connected", "Track: Not set" / "Track: gaming", "42 clips made" / "Not known yet",
  and "No accounts picked, so nothing is posted for them" on the bare one.
- Failure state: `P.api` was stubbed to reject `/api/creators`; the page showed the could-not-be-read card with
  *Try again*, the server sentence in red, and a bad toast - not the empty state.

Escape discipline: every interpolated value goes through `esc(...)`; clip counts go through `num(...)` first and
the helper returns `null` (never `0`) for a missing or non-numeric value. No `id="..."` in the file collides with
one in the shell - the invented ids are `cr_list`, `cr_err`, `cr_count`.
