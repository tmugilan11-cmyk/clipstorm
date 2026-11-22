# day

Slug: `day`. One file owned: `peakcut/web/feat/day.js`. Skill loaded: **frontend-design**.

## What was built

A warm strip across the top of the home view with one button, `Make my day`.

- It registers through `PeakCut.add("day", { after: { drawOverview(root) } })` and its styles through
  `PeakCut.css("day", ...)`, so no other file was touched.
- It only appears when at least one creator in `PeakCut.state().creators` has a channel. On a server with
  no creators it removes itself; when a channel comes back it returns. Verified both ways.
- Content: a small sun mark, one help line ("Ten clips from the newest video of `<creator>`."), a creator
  picker that exists only when two or more creators have a channel, one primary button, and a note line
  that carries either progress or the server's own error sentence.
- Ten clips is the whole point of the feature, so the job is started with `max_clips: 10` and nothing
  else in `options`: the creator's own style, layout, captions and length limits are inherited from
  `creators.py` defaults rather than being overridden by a guess.

## The one honest limitation, and what the button does about it

**There is no route that lists a channel's videos.** The brief said to use one if it exists and otherwise
ask for a link in a small inline input, and say so here. It does not exist. What I checked:

| Place | What it returns |
| --- | --- |
| `GET /api/channel-preview?url=` (`studio/server.py:1220`) | `{platform, name, followers, pic}`. No videos. Probed live against `https://www.youtube.com/@MrBeast`: 200, exactly those keys. |
| `GET /api/stats/channel?handle=&key=` (`studio/api_stats.py:87`) | Needs the operator's own YouTube Data API key. Live without a key: 400. The dev server stores no key (`/api/settings` has none). |
| `GET /api/preview?url=` (`studio/server.py:776`) | Single video only. A channel link is refused by `media.preview` (`studio/media.py:200`): "That link is a channel or playlist, not a single video." |
| `studio/media.py:101` | `_ydl` sets `noplaylist` and `playlistend: 1`, so the server deliberately never walks a channel. |

So the button asks for one link, in a single line inside the strip, and says which creator it wants it
for: "Paste the newest video link from Nova Clips. Ten clips are made from it." It never guesses an
endpoint and never fabricates a video title. Pressing the button with an empty line reveals and focuses
that input and stops; it does not fall through to a request.

If a channel-videos route is added later, the change is local: replace the input read in `run()` with a
fetch of that route and keep everything below the confirm.

## Endpoints used

1. `GET /api/preview?url=<link>` before the confirm, to name the real video in the dialog. Returns
   `{title, uploader, duration, is_live, thumb}`. Verified live:
   `{"title": "Rick Astley - Never Gonna Give You Up (Official Video) (4K Remaster)", "uploader": "Rick Astley", "duration": 213.0, "is_live": false}`.
2. `POST /api/jobs` after the confirm, with exactly the body the route reads
   (`studio/server.py:797`, `def create_from_link(body: dict = Body(...))`):

```json
{ "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "options": { "max_clips": 10 }, "creator": "t1" }
```

`creator` is the id string. The route also accepts it missing (the job is then not attached to a
creator), which is why the band only ever shows creators that have a channel: those always have an id.

## Confirm gate

`POST /api/jobs` is never reached without an answer. The page's own dialog is used when it is reachable
(it is: `index.html` is one classic script, so `window.ask` exists) and a real `window.confirm` otherwise:

```js
async function confirm2(title, text) {
  const own = window.ask;
  if (typeof own === "function") {
    try { return await own(title, text, "Make them"); } catch { /* fall through */ }
  }
  return window.confirm(title + " " + text);
}
```

The dialog names the real title and the real length: `Ten clips from "<title>" for Nova Clips. The video
is 1:02:05 long.` Answering no prints "Nothing was started." and keeps the typed link.

## Exact commands and output

```
cd peakcut && node --check web/feat/day.js
JS OK
```

```
python - <<'PY'
import httpx
r = httpx.get("http://127.0.0.1:8798/assets/feat").json()
print("served files:", r["files"])
PY
served files: ['autopilot.js', 'day.js', 'filters.js', 'grid.js', 'heard.js', 'log.js', 'mood.js',
               'peek.js', 'pill.js', 'stage.js', 'stats.js', 'style-tiles.js']
```

Live page (`http://127.0.0.1:8798/app`, real browser tools):

- `window.PeakCut._order` contains `"day"`, and `PeakCut.day` is an object, both before and after a
  full page refresh, so the module registers on load.
- With the dev server's real state (`creators: []`), `#ov .day` is null while `#ov .tiles` is present:
  the strip hides itself when no creator has a channel.
- With a stubbed state holding one creator with a channel, the hook inserts the strip as `#ov`'s first
  child.

Behaviour, all with `/api/preview` and `/api/jobs` stubbed so nothing real was created:

| Case | Result |
| --- | --- |
| Press with empty line | Input opens and focuses; note "Paste the newest video link from Nova Clips."; zero requests |
| Answer no in the dialog | `sends: []`, note "Nothing was started.", button enabled again |
| Answer yes | Exactly one send: `/api/jobs` with `{url, options:{max_clips:10}, creator:"t1"}`, then toast "Making ten clips from ..." |
| Two creators with channels | `<select>` with both names; picking Beam sends `creator:"t2"` |
| Server refuses the link | Server's own sentence shown, class `day-note bad`, zero sends |
| Link is live | "That link is live right now. Add the creator and press Start recording to clip a stream." |
| Send fails | `e.message` shown ("No such creator"), button re-enabled, nothing thrown into the page |
| Title `<img src=x onerror=alert(1)>` | Appears only inside the dialog string; `card.querySelector("img")` is null |
| Repaint | Typing then wiping `#ov` and re-running the hook keeps the typed value, the open input and the note |

Contract checks on the real server, with bodies the route rejects before creating anything:

```
POST /api/jobs {"url":"https://example.com/nope","options":{"max_clips":10}}
400 {"detail": "Paste a full link to a YouTube, Twitch or Kick video."}

POST /api/jobs {"url":"https://www.youtube.com/watch?v=x","creator":"nobody"}
404 {"detail": "No such creator"}
```

## What I could not test

- A real job start. `POST /api/jobs` was never sent a body that would create one, because that would
  leave a queued download in the dev environment. The contract is proven by the two rejected bodies
  above plus reading `server.py:797-820`.
- The happy path on a server that actually has creators with channels: the dev server has none, so every
  creator-bearing case above used a stubbed `PeakCut.state()`. The hook, the DOM, the confirm and the
  request shape were exercised for real; only the data was synthetic.
- Picking the newest video automatically, since no route lists a channel's videos (see above).

## Anything a reviewer should look at

1. **The one real product gap.** As shipped, "Make my day" needs one paste. That is the brief's stated
   fallback, but it is worth being explicit: the button cannot know what "newest" is without either a
   channel-videos route or a stored per-creator API key. A follow-up could extend
   `/api/channel-preview` to return the latest few uploads from the channel page it already fetches.
2. `options` deliberately carries only `max_clips: 10`. Sending style, layout or length here would
   silently override the creator's saved preferences (`studio/jobs.py:319` merges creator defaults first,
   then `clean_options`).
3. The strip is inserted with `insertAdjacentHTML` from `markup()`, and every server string in it goes
   through the page's `esc()`. The note line is written with `textContent`, never markup.
4. Repaint safety relies on a signature (`id:name|...|multi|one`) stored in `dataset.day`; the strip is
   only rebuilt when the set of creators changes, so typing is never disturbed by the animation-frame
   repaint loop in `plugins.js`.
