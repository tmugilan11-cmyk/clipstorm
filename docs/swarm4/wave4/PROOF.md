# Wave 4 proof

Written by hand. The prover slot's answer was lost to the transport ("giving up after 10 retries"), so this file
records what was measured after the wave, on the running server, by running the thing rather than reading the claim.

## What wave 4 was for

Wave 4 was "the rest of the menu": seven new main-menu rows, each drawing a real page with a real form, replacing
the old shape where a feature could only be reached by digging into Settings.

## The seven pages, measured on the running server

`curl` for the address, then the browser for the drawing. "Drawn" is the byte length of `#view`'s markup after the
page settled, which is what a person actually sees.

| Address | HTTP | Drawn (bytes) | What it says |
|---|---|---|---|
| `/app/creators` | 200 | 2428 | Every streamer, their channels and the accounts they post to |
| `/app/live` | 200 | 2423 | Who is streaming now |
| `/app/schedule` | 200 | 9098 | Paste-ready schedule text and the commands behind it |
| `/app/formats` | 200 | 12028 | "This PeakCut offers 8 clip shapes and 35 captions" |
| `/app/sounds` | 200 | 6547 | 13 rows, each with a Play button and a Ready / Not built pill |
| `/app/help` | 200 | 7063 | 6 `<details>` questions, reads nothing from the server |
| `/app/ai-usage` | 200 | — | "Service Logfare. Model deepseek-v4.1-flash-1017. AI calls 0." |

No console lines were produced by any of them.

The first measurement attempt was wrong and is worth recording: opening the seven addresses in one batch showed
10583 bytes for every single one, which is the previous page still on screen. The page needs about four seconds
after load before a feature file has registered and drawn, and a batch that sleeps 1.2 s measures the page before
it. Re-measured with a 4 s settle, the numbers above are stable.

## The sound list is real audio, not just a row

A Play button that reports success while serving nothing would be the worst kind of quiet failure, so the bytes
were pulled and probed rather than trusted:

```
curl -o snd_emb.wav   /api/sounds/meme/embarrassing   -> 360044 bytes
curl -o snd_chill.wav /api/sounds/music/chill          -> 1152044 bytes
ffprobe snd_emb.wav    -> pcm_s16le, 48000 Hz, 1 channel, 3.75 s
ffprobe snd_chill.wav  -> pcm_s16le, 48000 Hz, 1 channel, 12.00 s
```

Both decode as real mono wav files at the length their mood file says.

## The bug this proof found

Proving the page by pressing it found a real fault the review had already fixed once and that came back in a new
place: pressing Play said **"The server could not hand over the Embarrassing sound (answered 405)."**

The cause, measured directly:

```
curl -I /api/sounds/meme/embarrassing   -> HTTP/1.1 405 Method Not Allowed
curl    /api/sounds/meme/embarrassing   -> 200
```

`web/feat/sounds.js:177` asks the address with `fetch(src, {method: "HEAD"})` before it points an `<audio>` at it,
and for a good reason written in its own comment: a missing file and a file this browser cannot decode arrive at an
`<audio>` element as the same error event, so the only way to tell "not made yet" from "cannot play" is to ask the
address first. The route was declared `@router.get(...)`, so HEAD was never answered and the page had to report a
file that was sitting on disk as unreachable.

Fixed in `studio/api_sound.py`: the route is now
`@router.api_route("/api/sounds/{kind}/{mood}", methods=["GET", "HEAD"])`, with the reason in the docstring.

Verified after the fix:

```
curl -I /api/sounds/meme/embarrassing   -> 200
curl -I /api/sounds/meme/nope           -> 404   (a missing sound still says so)
```

And a regression check was added to `tests/test_mood_sound.py` so it cannot come back:
"the sound route answers the HEAD the page probes with". It was proved to be a real check, not a decoration: with
the fix removed by hand the check fails with "the sound route does not answer HEAD, so the page's probe gets 405 and
a sound that exists looks missing", and with the fix restored the suite reports "All checks passed. 11 ok".

One honest limit: pressing Play in this session's browser tab still ends in "The browser could not play that file."
That is the tab being hidden (`document.hidden === true`), not the page: this browser suspends audio decoding and
animation for a tab nobody is looking at. The audio itself was proved above by pulling the bytes and probing them.

## Gates after wave 4

```
python tests/test_feat_files.py    {"files": 47, "checks": 382}   All checks passed.
python tests/test_menu_pages.py    All checks passed. 313 ok
python tests/test_insights_pages.py All checks passed. 83 ok
python tests/test_mood_sound.py    All checks passed. 11 ok
```

47 served feature files, every one parses under `node --check`. `docs/MENU.md` records 25 main-menu rows with the
file that draws each one and the routes each page calls.

## What wave 4 did not finish

- **I5, the two Usage screens, could not be fixed inside a feature file.** The fixer recorded it instead of reaching
  into the frozen page. It was later fixed by hand: the legacy `usage` view was removed from `ROUTES`, its draw
  branch was deleted, and three entry buttons were repointed to `ai-usage`. See `docs/swarm4/wave5/` for that pass.
- **Minor 6** (dash characters) and the Content half of **Minor 3** (a panel labelled a window the server did not
  use) are still open, both explained in `FIXES.md` as not-small changes.
- `/app/usage` is now an unknown address and shows a "no page at that address" note above the home page. That is
  correct after the rename, but an old bookmark to it lands oddly.
