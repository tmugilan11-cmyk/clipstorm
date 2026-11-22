# The menu

The left rail is the map of PeakCut: one feature is one row, and a row opens a page with its own
address, so every page can be linked to, bookmarked and reloaded on its own. Settings is not a
drawer of features, it is the page for the things a person changes once.

This file is the per-row reference. Each section below says what the page is for, which routes it
really reads (checked against `studio/`), and which file draws it. A route named here is a route
that exists today; a page that cannot do its whole job yet says so in its own section.

## How a row gets its place

- `drawShell()` in `web/index.html:1293` draws Home, All videos and Review, then calls
  `PeakCut.navHtml()` for the rows that feature files registered, then the Creators heading and
  its rows, then the Owner heading and Admin.
- A file under `web/feat/` adds a row with `PeakCut.page(name, {nav, icon, tip, path, group, order})`.
  `PeakCut.pageRows()` returns every row sorted by heading, then by that page's `order`, then by
  the order the file loaded.
- The headings and their numbers live in `web/feat/menu.js:16`: Make 10, Understand 20,
  Look and sound 30, Set up 35, Connect 40, Account 60, Help 90. A heading with no pages prints
  nothing, which is why nothing says "Look and sound" today.
- One wobble is real and this file cannot settle it: Brand and Creators both claim Make order 10,
  so which one prints first depends on which file loaded first. The fix is one "10" changed in one
  of those two files, not here.

The whole rail can be checked in the browser console on `/app`:

```js
PeakCut.pageRows().map(r => [r.group, r.nav, "/app/" + r.path])
```

If a row there is missing below, or a heading or address differs, the running page is right and
this file is stale.

## The rows at a glance

"Arrived" is the wave the row was added. The rail order is the order above, not this table's
order, because a heading gathers its rows before the next heading starts.

| Row | Heading | Address | Order | Arrived | Drawn by |
|---|---|---|---|---|---|
| Home | none | `/app` | built in | wave 1 | `web/index.html` + `web/feat/day.js` |
| All videos | none | `/app/videos` | built in | wave 1 | `web/index.html` + `web/feat/filters.js` |
| Review | none | `/app/review` | built in | wave 1 | `web/index.html` |
| Brand | Make | `/app/brand` | 10 | wave 3 | `web/feat/menu-pages.js`, `web/feat/style-tiles.js` |
| Creators | Make | `/app/creators` | 10 | wave 4 | `web/feat/creators.js` |
| Improve | Make | `/app/improve` | 30 | wave 3 | `web/feat/learn.js` |
| Clip formats | Make | `/app/formats` | 32 | wave 4 | `web/feat/formats.js` |
| Sounds | Make | `/app/sounds` | 33 | wave 4 | `web/feat/sounds.js` |
| Live | Make | `/app/live` | 35 | wave 4 | `web/feat/live.js` |
| Insights | Understand | `/app/analytics` | 20 | wave 3 | `web/feat/analytics.js` |
| Transcription | Understand | `/app/transcribe` | 25 | wave 3, owner only | `web/feat/menu-pages.js` |
| Tools | Set up | `/app/tools` | 30 | wave 3 | `web/feat/menu-pages.js`, `web/feat/grid.js` |
| Connected apps | Set up | `/app/apps` | 40 | wave 3 | `web/feat/menu-pages.js` |
| Schedule | Set up | `/app/schedule` | 45 | wave 4 | `web/feat/schedule.js` |
| AI | Set up | `/app/ai` | 50 | wave 3, owner only | `web/feat/menu-pages.js` |
| Usage | Set up | `/app/ai-usage` | 55 | wave 4 | `web/feat/usage.js` |
| Storage | Set up | `/app/storage` | 60 | wave 3, owner only | `web/feat/menu-pages.js` |
| Account | Set up | `/app/account` | 70 | wave 3 | `web/feat/menu-pages.js` |
| Help | Set up | `/app/help` | 80 | wave 4 | `web/feat/help.js` |

The seven rows this wave added are Creators, Live, Schedule, Help, Usage, Clip formats and Sounds.

## Home

The page you land on: what PeakCut is doing right now, anything recording, and the one box where a
link is pasted or a video is dropped. It is the only page that also offers the ten-clip button,
which makes ten shorts from the newest video of the creator in front of you.

- Drawn by: `web/index.html`, `drawShell()` row and `drawView()` into `#ov`, then
  `drawAdd("hero")`; the ten-clip button is `web/feat/day.js`.
- Reads: `GET /api/overview` (index.html:2012), `GET /api/jobs`, `GET /api/status` (index.html:3219 on load, then every 15 seconds at index.html:3250,
  for the greeting, the role and anything recording), `POST /api/upload` (and the chunked
  `/api/upload/start`, `PUT /api/upload/{id}/{n}`, `POST /api/upload/{id}/finish`),
  `POST /api/preview` then `POST /api/jobs` (day.js:148, 163).
- Not yet: the ten-clip button cannot list a channel's uploads, because the only route that would
  (`GET /api/stats/channel`) needs a personal YouTube API key. It asks for one video address and
  confirms the real title before it queues anything.

## All videos

Every recording and every clip from every creator in one list, each row a video with its clips
folded underneath. The bar above the list narrows it by status and searches titles, source names
and clip hooks entirely in the page.

- Drawn by: `web/index.html`, `drawView()` into `#add` and `#jobs`; the search and status pills are
  `web/feat/filters.js` (it reads nothing).
- Reads: `GET /api/sync` (index.html:2718), which carries the whole list back and answers from
  memory when nothing of yours has changed; `GET /api/overview` for the week card
  (grid.js:164); `GET /api/jobs` only as the fallback when Review opens on an empty list
  (index.html:2128).
  Row actions: `PATCH /api/jobs/{jid}/clips/{cid}` (index.html:2177), `POST /api/bulk/delete`
  (index.html:3044), `GET /api/clips.zip?ids=` (index.html:1899), `POST /api/jobs/{jid}/peek`.
- Not yet: pagination. The page holds the whole job list in one answer and filters it in the page.

## Review

The queue of clips that are waiting for a yes or a no, one video at a time, so nothing goes out
before it has been seen. A, X and S key a card, and approving or rejecting writes that decision
back to the clip immediately.

- Drawn by: `web/index.html`, `drawView()` into `#rvroot` then `loadReview()`, with the video
  picker and the cards in `drawReview()`.
- Reads: `GET /api/jobs` (index.html:2128), `GET /api/jobs/{jid}/review` (index.html:2133, route in
  `studio/api_review.py:89`), `PATCH /api/jobs/{jid}/clips/{cid}` (index.html:2177, route in
  `studio/api_review.py:98`), `POST /api/jobs/{jid}/peek` and `GET /api/jobs/{jid}/peek/{cid}`.
- Not yet: approved clips do not post from here. They wait in All videos until they are posted
  there, and the page says so under the list.

## Brand

The look every new clip inherits: palette, caption style, the hook at the top, the watermark and
the closing card, all on one page. It is the page to open when clips look wrong before anything is
cut, not after.

- Drawn by: `web/feat/menu-pages.js` page "brand" (`/app/brand`), which calls `drawSettingTab`
  in `web/index.html:2595`, so the form is the same code Settings uses. `web/feat/style-tiles.js`
  draws the preview tiles inside that form.
- Reads: `GET /api/brand` (index.html:2600), `GET /api/captions/styles`, `PUT /api/brand`
  (index.html:2955, routes in `studio/api_brand.py:42,48`); the tiles also read
  `GET /api/captions/styles` and `GET /api/style/preview?style=` (`studio/api_style.py:44,182`).
- Routes that exist but nothing calls yet: `POST /api/brand/reset` and `GET /api/brand/themes`
  (`studio/api_brand.py:76,83`). The theme list on the form is read from the saved brand document
  itself (index.html:2360), so a reset button is not on the page.
- Not yet: the page saves through the Settings route (`PUT /api/brand`), not through a route of
  its own.

## Creators

One page for the people this install clips for: each creator with their channel, avatar, posting
switch and score bar, and a New creator button that makes a workspace. It is where a channel is
added, corrected or removed, and where the live flag for that creator is set.

- Drawn by: `web/feat/creators.js`, page "creators" (`/app/creators`).
- Reads: `GET /api/creators`, `GET /api/overview`, `GET /api/accounts` (creators.js:227-229, one
  `Promise.all`), the avatar picture at `GET /api/creators/{cid}/avatar` (creators.js:100), all
  served by `studio/server.py:1291,1582,1601,1278`;
  `POST /api/creators`, `PUT /api/creators/{cid}`, `DELETE /api/creators/{cid}`,
  `POST /api/creators/{cid}/live`.
- Not yet: the avatar on the rail row and on this page is the creator's own upload; there is no
  route that fetches a channel picture from YouTube.

## Improve

A learning round: it reads how the clips have done, proposes changes to five settings, and shows
every change it made so one can be undone. "What would it change" asks for the same answer without
touching a setting.

- Drawn by: `web/feat/learn.js`, page "improve" (`/app/improve`).
- Reads: `GET /api/learn/state`, `POST /api/learn/run`, `POST /api/learn/undo`,
  `GET /api/learn/cost`, `GET /api/learn/signals`, and `GET`, `POST`, `DELETE` on
  `/api/learn/arms` (`studio/api_learn.py:57,72,103,188,224,239,275,288`).
- Not yet: a round reports calls and tokens, never a price; the bill belongs to the AI service that
  owns the key.

## Clip formats

The shapes a clip can come out in, with a live preview of each: the vertical short, the square, and
the wide cut. Picking one changes what the cutter renders next, not the clips already on disk.

- Drawn by: `web/feat/formats.js`, page "formats" (`/app/formats`).
- Reads: `GET /api/formats`, `GET /api/captions/styles`, `GET /api/style/preview?style=`
  (`studio/api_style.py:73,44,182`).
- Not yet: there is no route that re-renders existing clips in a new format; the choice applies to
  the next render.

## Sounds

The bed of music under a clip: one row per mood, each with a preview button, and a prime button
that asks the machine to build the missing files. The chosen mood is what the cutter mixes under
the speech.

- Drawn by: `web/feat/sounds.js`, page "sounds" (`/app/sounds`).
- Reads: `GET /api/moods`, `POST /api/moods/prime` (`studio/api_sound.py:55,96`); the preview
  points one `<audio>` element at `/media/<key>.wav`, or `/media/bed_<key>.wav` for a music bed
  (sounds.js:131).
- Not yet, and this is a real gap: `/media/{jid}/{name}` in `studio/server.py:1152` only serves
  `.mp4` and `.jpg` inside one job's clips folder, so the `/media/<mood>.wav` address the page
  builds has no route behind it today. The page plays the sound through one `<audio>` element and
  shows that element's own error sentence, so a missing file is a visible sentence rather than a
  silent failure.

## Live

The channels that are on air right now, one row per platform, with a watch button that adds a
channel to the list PeakCut polls. Watched channels stay in one short list so the same stream is
not added twice.

- Drawn by: `web/feat/live.js`, page "live" (`/app/live`).
- Reads: `GET /api/hunt/live?platform=`, `GET /api/hunt/watching`, `POST /api/hunt/watch`,
  `POST /api/hunt/unwatch` (live.js:200,221,259,289; `studio/api_preview.py:121,134,143,157`).
- Not yet: there is no auto-cut route. `POST /api/live/{jid}/clip` and `POST /api/live/{jid}/stop`
  exist on the server, but this page does not call them, so watching a channel does not clip it.

## Insights

What the videos did, in tabs for the summary, the videos, the audience and the traffic, each
answering for a date range from the last seven days up to lifetime. The same page carries the trend
panels that search what is already working on a platform and keep the ones worth copying.

- Drawn by: `web/feat/analytics.js`, page "analytics" (`/app/analytics`).
- Reads: `GET /api/analytics/status`, `/summary`, `/timeseries`, `/videos`, `/audience`, `/traffic`,
  `/retention` (`studio/api_analytics.py:149,176,237,271,327,374,402`), and
  `GET /api/trends/status`, `/searches`, `/videos`, `/saved`, plus `POST /api/trends/saved` and
  `DELETE /api/trends/saved?term=` (`studio/api_trends.py:189,218,265,320,328,364`).
- Not yet: every panel is empty for a creator with no published clips, and the page says which
  route answered with nothing rather than drawing a zero.

## Transcription

How speech becomes text: on this machine with a local model, or through a cloud service with a
key, and which model to use. Every clip's captions and every moment score are built on this
answer, so it is set once and then watched.

- Drawn by: `web/feat/menu-pages.js` page "transcribe" (`/app/transcribe`), which calls
  `drawSettingTab` in `web/index.html:2448`.
- Reads: `GET /api/transcribe`, `POST /api/transcribe/models`, `POST /api/transcribe/test`,
  `PUT /api/transcribe` (`studio/server.py:1472,1528,1547`).
- Not yet: owner only. A non-owner who opens the address sees an "Owner only" card instead of a
  form, and no fetch is made.

## Tools

Four checks on a channel before it is clipped: the clip rules a platform allows, who is on air, a
schedule you can paste into a caption, and the numbers for one video. The same page holds the week
card that shows clips made and posts sent, day by day.

- Drawn by: `web/feat/menu-pages.js` page "tools" (`/app/tools`), which calls `drawSettingTab` in
  `web/index.html:2615`; the week card is `web/feat/grid.js`.
- Reads: `GET /api/rules?platform=&handle=` (`studio/api_preview.py:46`), `GET /api/hunt/watching`
  and `POST /api/hunt/watch` / `unwatch` (`134,143,157`), `GET /api/schedule/preview?times=&os=`
  (`173`), `GET /api/stats/video?url=&key=` (`studio/api_stats.py:71`), and `GET /api/overview`
  for the week card. Four boxes and one card; the watch list loads itself, the other three wait for
  their button.
- Not yet: the box says "a video or a channel", but only `GET /api/stats/video` is wired. A channel
  answer would come from `GET /api/stats/channel` (`studio/api_stats.py:87`), which exists and
  nothing in `web/` calls. Both stats routes need a personal YouTube key typed into the box on the
  page, because the key is not stored.

## Connected apps

The platform accounts PeakCut may post to, which creator each account belongs to, and the button
that starts signing one in. Nothing can be posted until an account is added here.

- Drawn by: `web/feat/menu-pages.js` page "apps" (`/app/apps`), which calls `drawSettingTab` in
  `web/index.html:2521`. The page is visible to every role.
- Reads: `GET /api/apps` (owner only), `GET /api/zernio`, `GET /api/accounts` (only when Zernio
  has a key), `DELETE /api/accounts/{aid}`, `PUT /api/apps`, `POST /api/zernio/test`
  (`studio/server.py:1714,1730,1601,1606,1720,1748`); signing in is a link to
  `GET /oauth/{platform}/start`, which returns to `GET /oauth/{platform}/callback`
  (`studio/server.py:1620,1630`).
- Not yet: an account that was never finished signing in stays in the list saying so; there is no
  retry route, so the fix is to start the link again.

## Schedule

The posting plan as a schedule you can read and install: how many clips a day, which hours, and
which days, checked against the times the machine is on. Install writes the plan, remove takes it
away, and preview shows the times it would use without saving anything.

- Drawn by: `web/feat/schedule.js`, page "schedule" (`/app/schedule`).
- Reads: `GET /api/autopilot/spec?times=`, `GET /api/autopilot/preview?times=`,
  `GET /api/schedule/preview?times=`, `POST /api/autopilot/install`, `POST /api/autopilot/remove`
  (schedule.js:103,152,182,238; `studio/api_auto.py:97,117,135,161`, `studio/api_preview.py:173`).
- Not yet: only the operator account can install or remove. Everyone else still gets the three
  text blocks to copy, and the page says that instead of showing a button that the server would
  refuse. Every card draws the plan by reading a route; nothing here writes to the machine until
  Install is pressed twice.

## AI

The key, the provider and the model the whole install uses, with a test button that spends one
small call to prove the key works. Owner only, because it is one key for the machine rather than a
choice per person.

- Drawn by: `web/feat/menu-pages.js` page "ai" (`/app/ai`), which calls `drawSettingTab` in
  `web/index.html:2448`.
- Reads: `GET /api/ai`, `POST /api/ai/models`, `POST /api/ai/test`, `PUT /api/ai`
  (`studio/server.py:1385,1405,1419`).
- Not yet: owner only. Spending is shown on Usage; no price is invented anywhere on this page.

## Usage

What the AI has been used for and how many calls it made, by day, with no price guessed. It is the
page you come back to after the key is set, to see whether the install is being expensive.

- Drawn by: `web/feat/usage.js`, page "ai-usage" (`/app/ai-usage`).
- Reads: `GET /api/usage` (usage.js:238; `studio/server.py:1374`).
- Not yet: it counts calls and tokens, never money. The AI service that owns the key bills at its
  own rates, so a dollar figure here would be a guess.

## Storage

Where the videos and clips are kept and how much room is left, with buttons that open that folder
or ask for a different one. Owner only, because it is a fact about the machine PeakCut runs on.

- Drawn by: `web/feat/menu-pages.js` page "storage" (`/app/storage`), which calls
  `drawSettingTab` in `web/index.html:2448`.
- Reads: `GET /api/storage`, `POST /api/storage/open`, `POST /api/storage/pick`, `PUT /api/storage`
  (`studio/server.py:1671,1678,1691,1700`).
- Not yet, on purpose: saving a new folder does not move anything at that moment. The address is
  written down and the switch happens at the next start, when nothing is being rendered. The
  "Move everything that is in the current folder there too" box (checked by default) makes
  `studio/config.py:60 _move_folder` copy the old files across first; anything it cannot move stays
  where it was and is tried again next start. When `PEAKCUT_DATA` is set in `.env`, the form says
  the folder is fixed there instead of offering a button the server would refuse.

## Account

Your own name, email and password, and the two things that end a session: signing out, and
deleting the account. It draws two tabs, Profile and Security, and it fetches nothing of its own.

- Drawn by: `web/feat/menu-pages.js` page "account" (`/app/account`, two tabs), which calls
  `drawSettingTab("profile"|"security")` in `web/index.html:2448`.
- Reads: nothing new. Both tabs read the user details already in `S.status.user`, which came from
  `GET /api/status` (index.html:3219). Actions go to `POST /api/auth/password` (index.html:3023),
  `POST /api/auth/logout` (index.html:3021) and `POST /api/account/delete` (index.html:3060).
- Not yet: when sign-in is off there is no profile and no password, so both tabs say so and offer
  nothing. The row still opens, because the route exists either way.

## Help

The questions a first-run person actually asks, each folded away so the page stays short, and each
answer ending with the address where the thing really lives. It reads nothing and prints no
numbers, which is why it cannot drift out of date with this machine.

- Drawn by: `web/feat/help.js`, page "help" (`/app/help`).
- Reads: no route. Each answer ends in a plain anchor to one of six addresses: `/app/videos`,
  `/app/apps`, `/app/improve`, `/app/ai-usage`, `/app/storage`, `/app/schedule`. The anchor carries
  the real `href`, and a click is taken over only when `fromPath()` names a page that is actually
  registered, so an older build still navigates normally.
- Not yet: there is no search over the answers, and no box on this page to ask for a question that
  is missing. The app's own Report button is the way to send one; it goes through `openFeedback()`
  in `web/index.html:1259`, which opens the server's external feedback link rather than calling
  `POST /api/feedback` (`studio/server.py:1205`).

## Where the moved settings went

Wave 3 put four things that used to be Settings tabs into the main menu, and wave 4 finished the
job by having each page draw the same form Settings draws, through `drawSettingTab(tab, box)` in
`web/index.html:2448`. The old addresses still resolve, so a bookmark or a link in a message keeps
working.

| Was a Settings tab | Now a row at | Drawn by |
|---|---|---|
| Brand | `/app/brand` | `web/feat/menu-pages.js` |
| Transcription | `/app/transcribe` | `web/feat/menu-pages.js` |
| Tools | `/app/tools` | `web/feat/menu-pages.js` |
| Connected apps | `/app/apps` | `web/feat/menu-pages.js` |

The Settings page itself is still reached from the account menu at `/app/settings`, and a banner
can open one tab directly when the AI or the drive needs attention.

## What is still missing

- `web/feat/help.js` is the only file in this list with no fetch at all, which is correct for a
  page of sentences, but it means Help cannot report a broken link.
- The Sounds preview address has no route behind it (see Sounds above).
- Live can list and watch a channel but cannot cut from it yet (see Live above).
- Brand and Creators tie on Make order 10, so their order in the rail can swap between reloads
  (see "How a row gets its place").
- The headings Connect and Account are declared in `web/feat/menu.js` and no page uses them today,
  so nothing prints under either one.
