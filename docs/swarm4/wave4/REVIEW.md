# Wave 4 review

Reviewer read the brief, every report in `docs/swarm4/wave4/`, every file those reports describe, and the
`studio/` modules and tests the new pages call. Nothing was edited except this file.

**Verdict: 1 critical, 5 important, 4 minor.** The critical is real and user-visible: the Sounds page
advertises 13 playable files and can play none of them, because the address it plays does not exist on the
server. Three of the five Importants are defects inside new wave-4 files, one is the wave-2 window bug that the
wave was asked to carry, and one is a second Usage screen the wave added beside the one already there.

## The eight checks, in order

| # | Check | Result |
|---|---|---|
| 1 | Each new file parses and registers one plug-in named after itself | Pass. `node --check` clean on all seven (creators, live, schedule, help, usage, formats, sounds). Each registers exactly one `P.page` and one `P.add`. `usage.js` is the one deliberate rename (plug-in `usage`, page `ai-usage`) and that is required, see note 1 below. |
| 2 | Interpolated markup goes through `esc(` | Pass. Every server-supplied string in the seven pages is wrapped. Verified against the server field names each page reads, not just by eyeballing the templates. |
| 3 | No `id="..."` clash with `web/index.html` | Pass. All 115 unique ids in `index.html` compared against every static id in the ten changed files: no overlap. |
| 4 | Every `data-act` has a handler branch | Pass. All 12 act names bound in wave-4 markup resolve, either to an act map on a `P.add` object (the only place `plugins.js:160` looks) or to one of `index.html`'s own 87 names (`go`, `newcreator`). Two pages wire listeners instead of using `data-act` (`sounds.js`, `help.js`); both work, and neither leaves a dead button. |
| 5 | Every fetched URL exists in `studio/*.py` | **Fail once.** Every `/api/...` address exists. `sounds.js` also points an `<audio>` at `/media/<name>.wav`, which is not a route for a wav. C1. |
| 6 | Every failure is surfaced | Mostly. Two silent `catch {}` blocks (M2) and one swallowed state read that is reported as a permission fact (I4). |
| 7 | No absolute origin in a page file | Pass. No `http://127.0.0.1` or `http://localhost` in any `web/feat/*.js`. The only absolute URLs are the `http://www.w3.org/2000/svg` namespace in `icons-extra.js`, which must be absolute. |
| 8 | A page must not print a number it did not receive | Fails twice: `formats.js:74` invents a zero (I3), `analytics-traffic.js` labels a window it did not ask for (I2). Note the near miss in `usage.js:129` (M4). |

Gates run, all green: `node --check` on the seven files; `python tests/test_feat_files.py` -> 47 files, 382
checks, all passed; `python tests/test_menu_pages.py` -> 312 ok; `python tests/test_insights_pages.py` -> 83 ok.
Green tests do not cover any of the findings below, which is why they are worth writing down.

---

## Critical

### C1. Sounds page: every Play button points at an address the server cannot serve

`web/feat/sounds.js:131`

```js
return row.kind === MUSIC ? `/media/bed_${key}.wav` : `/media/${key}.wav`;
```

There is no route for that. `studio/server.py:1152` is the only thing under `/media`:

```python
@app.get("/media/{jid}/{name}")
def media_file(jid: str, name: str, download: int = 0):
    if not re.fullmatch(r"[\w\-]+\.(mp4|jpg)", name): raise HTTPException(404)
```

It needs a job id in the path and it only accepts `mp4` or `jpg`. `studio/api_sound.py` has exactly one GET,
`@router.get("/api/moods")` at line 55, plus `@router.post("/api/moods/prime")` at line 96. So a wav has no
address anywhere in the app.

Confirmed against the running server on 8798: `/api/moods` answers 200 and lists 13 moods all with
`"ready": true`; `/media/airhorn.wav` answers 404; `/media/bed_hype.wav` answers 404.

Why this is critical rather than a broken link: the page's own count says "13 of 13 sound files ready", every
row therefore draws an enabled Play button, and pressing any of them sets `el.src`, lets the browser 404, and
prints "That file could not be played by this browser." Thirteen times. The page cannot do the one thing it
exists to do, and it says it can. The file header (`sounds.js:11-15`) records the gap honestly in a comment,
and `docs/swarm4/wave4/sounds.md` proposes the missing route, but neither makes the button work.

There is a second fault underneath the first, and it would still be there after a naive `/media` mount: the page
assumes the mood word is the file name. It is not. A mood names its sounds
(`studio/meme.py:51` `"hype": {"sound": ["airhorn", "bass_drop"], ...}`, `studio/meme.py:45`
`"embarrassing": {"sound": ["mine/hello_darkness", "sad_trombone"], ...}`), and `meme.sound_ready()` exists
precisely because "asking for `<mood>.wav` would report every gag as unbuilt while its files sit right there"
(`studio/meme.py:386-390`).
Measured on this checkout - `data/sounds/` holds `airhorn.wav`, `bass_drop.wav`, `sad_trombone.wav` and seven
more, and there is no `hype.wav`, `embarrassing.wav` or `funny.wav` at all:

| row the page draws | file the page asks for | file that actually exists |
|---|---|---|
| hype (meme) | `hype.wav` | `airhorn.wav`, `bass_drop.wav` |
| embarrassing (meme) | `embarrassing.wav` | `sad_trombone.wav` (or your own `mine/hello_darkness.wav`) |
| funny (meme) | `funny.wav` | `rimshot.wav`, `ding.wav` |
| chill (music) | `bed_chill.wav` | `bed_chill.wav` - correct |
| hype (music) | `bed_hype.wav` | `bed_hype.wav` - correct |

So 9 of the 13 buttons are wrong twice over: wrong prefix and wrong name. The four music rows are right about
the name and still have no route. That is why the fix below resolves the mood on the server, where the mapping
already exists, instead of teaching the page the mapping.

**Exact fix.** Two changes, both small.

1. `studio/api_sound.py` - a route that answers for a mood, using the resolver that already exists
   (`meme._resolve_sound`, `studio/meme.py:406`, which checks `wav`/`m4a`/`mp3` under `data/sounds/` and falls
   back to making the shipped sounds). Note the leading underscore: it is private today, so either promote it to
   `meme.sound_path(spec)` with the same body or call it as-is and add the public name in the same commit.

```python
from fastapi.responses import FileResponse

@router.get("/api/sounds/{kind}/{mood}")
def sound_file(kind: str, mood: str, request: Request) -> FileResponse:
    """The wav for one mood, addressed by the word the page shows, not by the file's name."""
    _me(request)
    key = str(mood or "").strip().lower()
    if kind == "music":
        if key not in music.MOODS:
            raise HTTPException(404, "No music bed is called that.")
        path = music.bed_path(key)
    elif kind == "meme":
        row = meme.load_moods().get(key)
        if not row:
            raise HTTPException(404, "No noise is called that.")
        try:
            path = meme._resolve_sound(row.get("sound"))
        except RuntimeError as e:
            raise HTTPException(404, str(e))
    else:
        raise HTTPException(404, "A sound is either a meme or a music bed.")
    if not path or not path.is_file():
        raise HTTPException(404, "That sound has not been made yet.")
    return FileResponse(path)
```

2. `web/feat/sounds.js:120-132` - put the mood word in the address and let the server resolve it:

```js
function urlFor(row) {
  const key = String(row.key || "");
  if (!/^[A-Za-z0-9_-]{1,60}$/.test(key)) return "";
  return `/api/sounds/${row.kind === MUSIC ? "music" : "meme"}/${key}`;
}
```

Then distinguish the two failures in `play()` (`sounds.js:112-118`, `:160-167`): a 404 means "that sound has not
been made yet, press Build", and only a browser that cannot decode the wav gets "could not be played". If the
route cannot land in this wave, delete the Play button and the "ready" pill together, so the page stops claiming
13 playable files.

---

## Important

### I1. Help page promises a control that does not exist

`web/feat/help.js:96`

> "For a channel nobody is watching by hand, the Live page holds the watch list and the auto-cut switch."

There is no auto-cut switch. `grep -rn -i "auto.cut\|autocut\|auto_cut" web/` returns that one help line and
nothing else. `live.js` has no such control, and `docs/swarm4/wave4/live.md` records that the switch was left
out on purpose because no route backs it. The Help page therefore sends the reader to a page for a control it
will not find. On the one page whose entire job is being plain and true, a false sentence is worse than a
missing one.

**Exact fix.** Delete the clause at `help.js:96`: end the sentence at "the Live page holds the watch list."
If the intent was to mention the thing that is missing, say so plainly: "the Live page holds the watch list.
PeakCut cannot switch auto-cut on for a channel yet." Either way, do not name a control nobody wrote.

### I2. Traffic panel asks for a window the route does not read, then labels the answer with it

Wave 2 raised this as Important; the carry-over was not fixed. `web/feat/analytics-traffic.js:61-63`:

```js
const s = iso(r, ["start", "from", "since"]), e = iso(r, ["end", "to", "until"]);
add("start", s); add("end", e);
if (!s && !e) add("days", pick(r, ["days"]));
```

The route takes a day count and nothing else, `studio/api_analytics.py:374-375`:

```python
@router.get("/api/analytics/traffic")
async def traffic(request: Request, days: int = Query(28, ge=0, le=3650)) -> dict:
```

FastAPI drops the unknown `start`/`end` and the default 28 applies. `web/feat/analytics.js:38-46` always
publishes a real `start`/`end`/`days` triple and `agree()` (analytics.js:88-93) copies it onto the exported
object, so `iso()` always finds dates, the `days` line never runs, and every tab selection is answered with the
default 28-day window. Then `analytics-traffic.js:119`

```js
const band = v.range || q.range || "Range not stated";
```

labels those 28-day figures with whatever the user picked. Pick 90 days, read 28 days of traffic under a
90-day heading. The route is honest, the label is not.

**Exact fix.** Ask only in days. Replace the three lines with:

```js
const s = iso(r, ["start", "from", "since"]), e = iso(r, ["end", "to", "until"]);
const n = pick(r, ["days"]) ?? (s && e ? Math.round((at(e) - at(s)) / 86400000) + 1 : null);
add("days", n);
```

with `at = (v) => new Date(v).getTime()` clamped to 0..3650 the way `analytics-table.js:77-82` already does,
and drop the `start`/`end` query strings. `read()` at `analytics-traffic.js:95` already prefers the server's
own `b.start`/`b.end`, so the pill will then describe the window actually fetched.

### I3. `formats.js` invents a zero when a number is missing, and prints it

`web/feat/formats.js:74`

```js
const num = (v) => { const n = Number(v); return Number.isFinite(n) ? n : 0; };
```

The honest version in this same wave is `live.js:52-56`, which returns `null` for anything absent. Here every
absent value becomes `0`, and it is printed at four places:

- `formats.js:200` - `${num(f.needs)} ${f.needs === 1 ? "piece" : "pieces"}` -> "0 pieces"
- `formats.js:177-178` - `${num(shapeCount)} clip shapes` / `${num(lookCount)} caption looks`
- `formats.js:107` - `needs: Math.max(0, Math.round(num(f.needs_parts)))`
- `formats.js:110`, `:127` - `Number.isFinite(Number(j.count)) ? num(j.count) : out.length` (this one is fine:
  it falls back to a count the page itself has)

Today's server always sends the fields (`studio/formats.py:69-71` returns `id`, `label`, `needs_parts`, `hint`
for all 8 formats; `api_style.py:73-80` adds `count`), so nothing is wrong on screen right now. That is exactly
why it needs fixing now: the day a field is renamed, the page says "0 pieces" beside a card for a format that
needs two, and says "0 clip shapes" above a list of eight shapes. A zero is a claim, and this zero is not one
the server made.

**Exact fix.** Match `live.js`:

```js
const num = (v) => {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};
```

then at `formats.js:200` render `f.needs == null ? "pieces" : `${num(f.needs)} ${...}``, and at `:177-178`
push the count only when it is not null - the list length is already there as a fallback the page owns.

### I4. `schedule.js` reports a swallowed failure as a permission fact

`web/feat/schedule.js:57-62`

```js
const isOwner = () => {
  try { const s = P.state(); return !!(s && s.status && s.status.user && s.status.user.is_admin); }
  catch { return false; }
};
```

A non-admin and a throw from `P.state()` land on the same `false`, and `schedule.js:130-133` paints

> "Only the operator account can write a task into this computer's scheduler. You can still copy the text and
> run it yourself."

So if the state read ever breaks, an operator who owns the machine is told they are not the operator, and the
real error is never mentioned. That is a failure silently converted into a fact about the user - both halves of
rule 6 broken in four lines.

**Exact fix.** Return three states instead of two:

```js
const isOwner = () => {
  try { const s = P.state(); return !!(s && s.status && s.status.user && s.status.user.is_admin); }
  catch (err) { return null; }
};
```

and in the paint step treat `null` as its own case: "PeakCut could not tell whether you are the operator, so
Install is hidden. <reason>". Keep the non-admin paragraph for a plain `false`.

### I5. Wave 4 adds a second Usage screen instead of replacing the first

The wave was asked to add a Usage row reading `/api/usage`. It could not take the `/app/usage` address, because
`web/index.html:1404` handles it first:

```js
else if (v === "usage") { view.innerHTML = `<div id="usage"></div>`; loadUsage(); }
```

so `usage.js:257` registers page `ai-usage` and the menu row "Usage" now opens `/app/ai-usage`. That rename is
the only reachable option and is not itself a defect (note 1). The defect is what is left behind: the old
screen still owns `/app/usage` and is still reachable, from `index.html:1213` ("AI usage" in the top bar) and
`index.html:1114` ("View usage"), while the nav row sends the reader to a different screen for the same data.
Two usage screens, both live, both calling `/api/usage`, and the older one is what most existing buttons open.
They do not even agree on how to format the same field: `index.html:1126` `fmtK` writes token counts as `12.3K`
and reads a missing value as `0`, while `usage.js:85-88` `tokens` writes `12.3k` and writes `not known` for a
missing one. Same route, two answers to "how many tokens", depending on which button the person pressed.

**Exact fix.** One screen, one address. In a follow-up that may touch `web/index.html`: delete the
`v === "usage"` branch at `index.html:1404` and the legacy `drawUsage()` at `:2098`, and let `PeakCut.hasPage`
route `/app/usage` to the new page - or keep the legacy screen and point the new page's nav at a distinct name.
Ship one, not both. If this wave must not touch `index.html`, record the overlap as a required follow-up in
`docs/swarm4/PUNCHLIST` style rather than leaving it unmentioned. (`index.html:2074` `loadUsage` also writes back
into `S.status.ai` at `:2076`, so whichever screen goes, check that nothing still needs that side effect.)

---

## Minor

### M1. Em dashes and an ellipsis in `creators.js` copy

`web/feat/creators.js:267`, `:268`, `:275` put a U+2014 em dash into visible page copy, against CONTRACT
"no em dash". `:223` ends the loading sentence with a U+2026 ellipsis instead of a full stop, and `:5` has
another em dash in the header comment. These five lines are the only non-ASCII in the whole wave - the other
nine changed files are clean.

**Exact fix.** `:267` "Everything PeakCut makes for them - the clips, the rules, the accounts they are posted
to - belongs to that creator"; `:275` "list again - nothing is saved by looking."; `:223` "Reading your
creators."; `:5` hyphen in the comment.

### M2. Two silent `catch {}` blocks

`web/feat/menu-icons.js:47`

```js
try { page[name] = `<path d="${d}"/>`; } catch {}
```

and `web/feat/icons-extra.js:139`

```js
const ping = () => { try { document.dispatchEvent(new Event("peakcut:render")); } catch {} };
```

Neither can throw in practice (assigning a key on a mutable object, `dispatchEvent` with a plain `Event`), so
nothing is hidden today. But rule 6 says a failure is surfaced, and the good pattern already exists three
lines up in `icons-extra.js:73`, which collects refused names on a `report` object and shows them.

**Exact fix.** `menu-icons.js:40-49` already returns `true`/`false` to the caller, so make the write part of
that answer instead of losing it:

```js
if (page && box === BOX && !page[name]) {
  try { page[name] = `<path d="${d}"/>`; } catch (err) { return false; }
}
```

The caller can then report the name it could not place. `icons-extra.js:139` should lose the `try`/`catch`
entirely - `ping` has nothing to recover from, and an empty `catch` only teaches the next reader that failure
is expected here.

### M3. Counts written into copy that the server supplies

`web/feat/sounds.js:337` - "Nine meme noises and four music beds"; `web/feat/sounds.js:1` and
`web/feat/formats.js:1`, `:327`, `:356` - "the eight shapes" / "The eight shapes". Both catalogues are
data-driven (`/api/moods` returns `meme` and `music` lists; `studio/formats.py` returns a dict of 8), so the
prose is a number the page did not receive this run.

**Exact fix.** In `sounds.js:337` write "Meme noises and music beds" and let the `x of y built` pills carry the
counts, which they already do. In `formats.js:356` "The shapes" and at `:327` "The clip shapes and the caption
looks".

### M4. `usage.js` turns a missing daily count into a zero bar

`web/feat/usage.js:129` - `tokens: num(d && d.tokens) || 0`, and the same shape at `:171-172` and `:185`. The
`|| 0` converts "the server did not send this day" into "this day was zero", which is a claim about the data.
`studio/usage.py:93-97` always sends integers over a pre-seeded 30-day window, so today this never fires, and
`usage.js:205-206` shows the author did think about real zeros ("a counted zero is a fact"). Distinguishing a
counted zero from a missing one is the same fix as I3.

**Exact fix.** Drop the `|| 0` and have `plot()` skip a `null` token instead of drawing a zero-height bar, or
render that day as a gap with one sentence under the chart saying how many days the route left out.

---

## Not defects, checked and cleared

These looked wrong on first read and are correct. Recording them so the next reviewer does not re-open them.

- **Note 1 - `usage.js` page name.** Plug-in `usage` registering page `ai-usage` is required, not sloppy.
  `index.html:1404` handles `v === "usage"` before the `PeakCut.hasPage` branch at `:1406`, so a page named
  `usage` could never be drawn. The plug-in name staying `usage` is right too: the act map must match the file
  name and `tests/test_menu_pages.py`'s CLASH list expects it.
- **`creators.js` reads three routes and survives two failures.** Only `/api/creators` is fatal; it paints a
  failure card with a Try again button (`:204-213`, `:233`) instead of an empty state. `/api/overview` and
  `/api/accounts` degrade to a sentence (`:243-249`). This is the pattern the contract asks for.
- **Avatar addresses.** `creators.js:101` builds `/api/creators/<id>/avatar`, which is
  `studio/server.py:1278`. Exists.
- **`live.js` numbers.** `num()` returns `null` (`:52-56`), per-row summary counts are computed in the page and
  labelled as such (`:146-156`), a failed check keeps the server's own sentence per row (`:236-243`), and
  add/remove toast the server's field (`:259-296`). Nothing invented.
- **`formats.js` list readers.** `readShapes` (`:99-112`) and `readLooks` (`:115-128`) keep "not asked" and
  "asked, empty" apart and paint them differently. The frame queue is bounded at 4 (`:231-256`) with a 20 s net
  (`:245`) and per-tile error handling (`:281-287`). `/api/style/preview` (`studio/api_style.py:182`) exists
  and 400s on an unknown look.
- **`schedule.js` two-press arming.** ARM map plus an 8 s timer (`:50`, `:136-142`, `:211-247`), disarmed by
  pressing the other button, posts to `/api/autopilot/install` and `/api/autopilot/remove`
  (`studio/api_auto.py:135`, `:161`). Both exist and the POST body matches.
- **`sounds.js` and `help.js` do not use `data-act`.** `sounds.js` binds a delegated listener over
  `[data-snd]` inside `load()` (`:356-367`); `help.js` binds `data-hlp-go` on real anchors (`:103-118`) and
  only takes the click when `P.hasPage(name)` is true, so the link still works before the plug-in loads. Both
  work. `sounds.js` does register a listener on `body` per visit, but the node it reads is rebuilt each draw,
  so nothing accumulates.
- **`data-act="go"` and `data-act="newcreator"` in `creators.js`** (`:175`, `:176`, `:189`, `:270`) are
  `index.html`'s own handlers, not orphans. `plugins.js` ignores names it does not own and `index.html` ignores
  names it does not own; the two listeners coexist.

## Carried-over fixes from wave 2

| Fix | State |
|---|---|
| `analytics-table.js` must send `days`, not from/to | **Fixed.** `:238` asks `/api/analytics/videos?days=<n>`, `:77-82` computes a bounded whole-day count (`MOST = 3650`), `:191-192` prints the server's own sentence. Good. |
| `analytics-traffic.js` must stop labelling a window the server did not use | **Not fixed.** I2 above. |
| Two dash characters in analytics copy must both be ASCII | **Fixed.** All 14 `web/feat/analytics-*.js` files are non-ASCII-free. |
| `tests/test_insights_pages.py:25` regex must see `@router.delete(` | **Fixed.** `:29` is `@(?:router|app)\.(get\|post\|put\|patch\|delete)\(`, `route_paths()` returns `(routes, verbs)`, and the suite reports 83 ok. |
