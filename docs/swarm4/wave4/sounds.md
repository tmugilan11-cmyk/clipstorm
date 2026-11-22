# sounds — the Sounds page

**File I own:** `web/feat/sounds.js` (the only file I created or changed).

**Skill loaded first:** `frontend-design`.

## What I built

A main-menu page, `Sounds`, registered with `PeakCut.page("sounds", {...})`:

| key | value |
|---|---|
| `nav` | `Sounds` |
| `icon` | `radio` |
| `tip` | The noises and music beds a clip can be given, and which are built |
| `path` | `sounds` |
| `group` | `Make` |
| `order` | `33` |

The page draws two lists, **Meme noises** (9) and **Music beds** (4), from `GET /api/moods`. Each row shows the
name, one plain sentence about what the sound is like, a `Ready` / `Not built` pill, a Play button, and a small
line under it saying why it is or is not playable. A section header counts what is built, e.g. `2 of 3 built`.

- **Play is disabled when `ready` is false**, with `aria-disabled="true"` and an `aria-label` saying the sound is
  not built yet. The row text says "Not built yet. Use the button below this list to make it." It does not fail.
- **One `<audio>` element** does the playing, created lazily and reused. A second press is a stop, not a restart.
  Leaving the page (`hashchange`) pauses it, so a sound does not keep playing under the next screen.
- **Build the missing sounds** calls the existing `POST /api/moods/prime`, then re-reads and redraws. It reports
  how many noises and beds were made, and repeats per-file errors from `built.errors` in a `.err`-style note plus
  a `P.toast(..., "bad")`. It never claims a build it did not see.
- One `.hint` under each control, written for someone who has never used the app.

Design notes, per the loaded skill: the naming is the subject (`embarrassing`, `cringe`, `suspense`), so each row
carries the sound it actually is ("A record scratch. Everything stops for a beat.") rather than a generic label.
The pill is the only status device, the row is a hairline-separated list rather than a grid of cards, and the
"say" line sits under the row so a button press always has somewhere to answer. No new design language: the page
uses `set-sec`, `row`, `pill`, `hint`, `err`, `set-load`, `btn sm`.

## Routes it reads

| Route | How | Verified |
|---|---|---|
| `GET /api/moods` | `PeakCut.api("/api/moods")` | `studio/api_sound.py:55` |
| `POST /api/moods/prime` | `PeakCut.send("/api/moods/prime", {}, "POST")` | `studio/api_sound.py:96` |

Both are registered by `app.include_router(api_sound.router)` at `studio/server.py:248`. Nothing else is fetched,
and no path outside `/api/` is requested.

Answer shape used, from `studio/api_sound.py:84`:

```
{"moods": [{"name": str, "kind": "meme"|"music", "note": str, "ready": bool}, ...],
 "count": int, "meme": [names], "music": [names]}
```

The real names were read out of `studio/meme.py` and `studio/music.py`, not guessed:
memes `embarrassing, fail, shock, hype, win, awkward, cringe, funny, suspense`;
beds `hype, chill, tense, funny`. Every one of those 13 names has a line in the page's `BY_NAME` map, and the
meme order in the page matches the real order. `hype` and `funny` exist as both a noise and a bed, so rows are
keyed `<kind>:<name>`; a name alone would have collided.

## What it cannot do yet

**There is no route that serves a wav.** This is the one real gap and it is not my file to fix.

`data/sounds/airhorn.wav` and `data/music/bed_hype.wav` exist on disk, `GET /api/moods` correctly reports
`ready: true` for the ones that are built, and the page draws them correctly. But nothing in `studio/` hands
those bytes back over HTTP:

```
grep -rn '@app.get\|@router.get' studio/*.py | grep -iE 'media|audio|wav|sound|music'
  studio/api_sound.py:55:@router.get("/api/moods")
  studio/server.py:1152:@app.get("/media/{jid}/{name}")     # clips only: <jid> then mp4|jpg

grep -rn 'mount(' studio/*.py      # no StaticFiles mount anywhere in the repo
```

`/media/{jid}/{name}` (`studio/server.py:1152`) only serves `mp4` and `jpg` out of a job's own folder, so it
cannot reach `data/sounds`. There is no `/assets` route that reaches the data folder either.

So Play does the only thing that is honest: it points a plain `<audio>` at `/media/<name>.wav`
(`/media/bed_<name>.wav` for a bed) and reports what the browser says. Today that is one sentence under the row,
"The browser could not play that file.", not a silent nothing and not a fake success. **The moment one route
lands on those paths, the button starts working with no change to this file** — `urlFor()` is the only place the
address is built.

**The route that is needed** (written here rather than applied, because `studio/*.py` is not mine):

```python
# studio/server.py, beside media_file()

@app.get("/media/{name}.wav")
def sound_file(name: str):
    """One synthesised sound or music bed, for the Sounds page and the clip dialog to audition."""
    import re
    from pathlib import Path
    from . import meme, music
    if not re.fullmatch(r"bed_[a-z_]{1,20}|[A-Za-z0-9_-]{1,60}", name):
        raise HTTPException(404)
    for root in (Path(config.DATA_DIR) / "music", Path(config.DATA_DIR) / "sounds"):
        f = root / f"{name}.wav"
        if f.is_file():
            return FileResponse(f, media_type="audio/wav", headers={"Cache-Control": "private, max-age=300"})
    raise HTTPException(404)
```

It must be registered **before** `@app.get("/media/{jid}/{name}")` at `studio/server.py:1152`, or that route
answers first and 404s (it rejects a `.wav` name). Two other things follow from it:

- `meme.sound_names(mood)` can return a sub-folder name such as `mine/hello_darkness`, and `urlFor()` deliberately
  refuses those to avoid building a path the server would have to guess at. Those rows say so in one sentence.
- A mood can name two sounds (`hype` is `airhorn` then `bass_drop`), so one Play press plays one file, not a pair.
  Playing the pair would need the server to resolve the mood to a list, which is a bigger change than one route.

Nothing else is outstanding: the lists, the counts, the readiness, the empty state, the build button and the
failure states are all real and were exercised.

## Commands I ran, and what they printed

```
$ node --check web/feat/sounds.js
$ echo $?
0
```

```
$ python tests/test_feat_files.py
...
ok   sounds.js parses
ok   sounds.js declares one plug-in
ok   sounds.js is named after itself
ok   sounds.js is the only owner of sounds
ok   sounds.js does not write into index.html
ok   sounds.js escapes what it draws
ok   sounds.js uses no absolute origin
ok   sounds.js invents no clashing id
ok   loader keeps the documented folder
{"files": 47, "checks": 382}
All checks passed.
```

(The counts move as other agents land files; the first run of the same command printed `{"files": 46, "checks": 374}`
with the same verdict. Every `sounds.js` line was `ok` in both runs.)

```
$ python tests/test_menu_pages.py
ok   sounds says what to call it
ok   sounds says where it lives
ok   sounds has a one-line tip
ok   sounds has a group
ok   sounds has an icon the page knows   radio
ok   sounds does not take a built-in address   sounds
ok   sounds sits under a known heading   Make
ok   sounds does not shadow a feature file   sounds
ok   sounds has a label a menu row fits
ok   sounds has a label of its own
ok   sounds.js draws its page
1 check(s) failed        <-- NOT mine
```

The one failure in that run is another agent's file, and I did not touch it:

```
FAIL creators sits under a known heading   'Creators' is not one of: Make, Understand, Look and sound,
                                            Connect, Account, Help, Set up
```

`web/feat/creators.js:232` registers `group: "Creators"`, which is not in `ALLOWED_GROUPS` in
`tests/test_menu_pages.py:31`. That is for the creators agent, or for whoever adds `"Creators"` to the allowed
list. My own page passes every check.

I also ran a throwaway harness in `%TEMP%` (not in the repo, not shipped) that stubs `PeakCut`, `esc`, `Audio`
and `document`, calls `view()` and `load()`, and prints what was drawn:

```
$ node %TEMP%/sounds_smoke.js             # 5 moods, mixed ready/not ready
api read: ["/api/moods"]
rows drawn: 5
meme heading: true music heading: true
disabled buttons: 2
ready pills: 3
counts: [ '2 of 3 built', '1 of 2 built' ]
note shown for hype: true
no NaN: true

$ node %TEMP%/sounds_edge.js empty
[empty] body: <p class="snd-none">The server answered, and the list of moods was empty, so there is
nothing to show yet.</p> ... has err: false has hint: true NaN: false

$ node %TEMP%/sounds_edge.js fail
[fail] body: <p class="err">The sound list could not be read: Not signed in.</p>
<p class="hint">This list comes from the server. Reload the page; if it stays empty, the server log says why.</p>
[fail] has err: true has hint: true NaN: false
```

And the name check against the real mood files:

```
$ PEAKCUT_DATA=data python -c "from studio import meme, music; ..."
memes: ['embarrassing', 'fail', 'shock', 'hype', 'win', 'awkward', 'cringe', 'funny', 'suspense']
music: ['hype', 'chill', 'tense', 'funny']
missing from BY_NAME: []
```

## Things I need from someone else

1. **`studio/server.py`**: add the one `/media/{name}.wav` route above, registered before line 1152. Until then
   Play is disabled in effect: the button is drawn and honest, but no sound comes out.
2. **`web/feat/creators.js`**: `group: "Creators"` fails `tests/test_menu_pages.py`. Not mine to change.
