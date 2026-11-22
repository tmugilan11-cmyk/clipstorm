# Lead pass on the audio page: what I changed after the agent's file landed

The agent's own report is beside this one (`audio-page.md`). This records the changes made after it, each one after
seeing the page in a browser, and the proof for each.

## 1. "Edit audio" opens the clip the person was looking at

The clip dialog's `Edit audio` button closes the dialog and goes to `/app/audio`. The agent's `load()` always opened
the newest finished clip, so a person editing an old clip landed on a different one. The button now writes
`S.audioFrom = {jid, cid}` before navigating (and a copy on `D`, because the dialog is thrown away), and the page
reads it:

```js
const from = stateOf().audioFrom;
...
const want = A.clips.findIndex(c => c.jid === String(from.jid) && c.cid === String(from.cid));
if (want >= 0) first = want;
```

Proven: `Edit audio` on `demo.mp4 · c0` opens `demo.mp4 · c0 · 6.0s · Nov 19`, which is the last option, not the first.

## 2. Four clips of one file no longer look like twins

`allClips()` labelled every row `[file, clip id, length, day]`, and a video handed to PeakCut twice produces
identical rows. The day was added first; a group of duplicates then gets a `· #tail` of the job id.

The first version added the tail only to the second and later rows of a group, which still left one unnamed row in
a pair. It now adds it to **every** row of a duplicate group, computed from a count map before the loop.

Proven live: the picker reads
`["speech_video.mp4 · clip01 · 7.0s · Nov 20", "… 11.0s · Nov 20 · #bf42", "… 11.0s · Nov 20 · #aff9", "demo.mp4 · c0 · 6.0s · Nov 19"]`
— four rows, all different.

## 3. The AI really does place a sound, and the track really does carry it

This is the part that took the longest, because three separate things were wrong in the route rather than the page:

1. `ai.ask` does not exist. `ai.call(model, prompt, schema, timeout)` is the only entry point.
2. Passing `schema=None` still appended a sentence telling the model to answer under a key called `items`, so the
   plan prompt was contradicted and the model answered the JSON word `null`, which the caller read as "the AI
   deliberately chose nothing". `ai._wrapped` and `ai._parse` were fixed, and `_parse` now raises on `null`.
3. The same prompt took 8.9 s with no schema and 38.3 s with one, so the route's 60 s timeout (and later 90 s)
   turned the slower half of real answers into "PeakCut couldn't reach Logfare". The timeout is now 150 s, with the
   measurement written next to it, and a second attempt per model because this service also drops the slowest
   answers now and then (measured on one clip: 48 s, 85 s, 121 s, then a drop, same prompt).

Proven through the page, not by curl: pressing **Ask the AI to place them** on
`speech_video.mp4 · clip01 · 11.0s` returned one cue, `dun-dun-dunnnnnnnn at 10.08`, mood `dramatic`, why "final
quote reveal lands"; the shelf kept it (`dun-dun-dunnnnnnnn-68584 is kept on this machine now.`), the track drew a
chip labelled `AI 0:01 0.0 dun dun dunnnnnnnn`, and **Save sounds** stored it:

```json
{"cues":[{"slug":"dun-dun-dunnnnnnnn-68584","at":9.95,"volume":-2.0}],
 "sounds_line":"1 meme sound: dun-dun-dunnnnnnnn-68584 at 9.9s","version":1}
```

Then **Mix** wrote it into the picture file: `clip01.mp4` went `a2726d34809f → 2ebb3e26e0eb`, 7 799 544 → 7 818 410
bytes, still **11.000000 s**.

Where it landed, measured rather than assumed — the 20–120 Hz band, which is where a dun-dun lives and the speech
does not, per second of the mixed file:

```
 0s 365087   1s 433381   2s 256299   3s  91133   4s 124290
 5s 275210   6s 361327   7s 267841   8s 338743   9s 243058
10s 2413484   <-- 6x to 27x the loudest second of speech, at the cue's 9.95 s
```

## 4. What is deliberately not claimed

The page is not the only way to hear a cue: this browser tab is `document.hidden`, and a hidden page plays no audio
at all, so pressing **Play** here ends in "The browser could not play that file." The bytes are served and are real
(`/api/memesounds/play/…` answers 200 with an mp3, and the mix above proves the same file reaches a rendered clip),
so the honest statement is: playback needs a visible tab; mixing does not.
