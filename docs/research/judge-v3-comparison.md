# Judge v3: old and new on the overnight Speed stream

Measured on 2026-11-23 with the real AI in use (custom OpenAI-compatible service, `qwen3-5-35b-a3b-bf16`) on the
5 h 45 min recording "EXPLORING VICE CITY - GTA 6 STREAM (EASTER EGGS)" (IShowSpeed), transcript
`words.json` of that job (with the "chad" -> "chat" fix applied to both judges). Nothing in the job was changed;
the scripts only read it.

## How it was run

- **Old** = `studio/judge.py` as it was at HEAD (`git show HEAD:studio/judge.py`, loaded as its own module):
  reader -> three scouts -> two critics.
- **New** = this version: rolling story -> screen text read across the stretch -> reader -> three scouts ->
  frames of every candidate -> two critics (each in a different order, 75 s of setup shown) -> the clip-page
  admin on the contenders only.
- Both judged the same four 8-minute stretches as a live check would (`live=True`, n=2, 15-60 s clips, no
  overlap exclusion). Loudness is known only where a clip's `.src.ts` covers the stream (the buffer is gone),
  identically for both.
- The new judge got the story the way a recording builds it: `judge_story.advance` every 270 s of transcript
  from the start of the stream (52 reads, about 14 s and 2.8k tokens each, done in parallel with the judge in a
  real recording), snapshotted at each stretch. "Clips already made" = the recording's clips that start before
  the stretch.
- Frames came from the clips' `.src.ts` files (the only video left), so only part of each stretch could be
  looked at.

### Looking at the picture

The model does **not** accept images: the service lists it with `"vision": false` and answers a picture with
HTTP 503 `model_unavailable` (text calls work). `judge_look.can_see()` asked once, stored the "no" in
`data/judge_vision.json`, and the judge fell back to reading the text on the frames with Windows' own OCR
(`Windows.Media.Ocr` through PowerShell, about 0.5 s per frame including the keyframe decode). That still gives the
game's subtitles with the speaker's name, mission names ("UFO ABDUCTION", "BIGFOOT SIGHTING"), donations and
chat. Facial expression and anything purely visual are **not** seen. With a vision model the same step sends a
contact sheet per candidate instead (built and unit-tested, not exercised on real data here).

## Results, live mode (same stretches, same AI)

Score / cut / hook. "What" is the new judge's own one-sentence account of who does what to whom (new field).

### 3420-3900 (the door trap; the recording made "Y'ALL LIED TO ME" 3642-3677 and "Y'ALL LIED BRO" 3468-3484)

| | old | new |
|---|---|---|
| best | 93 · 3644-3692 · CHAT LIED TO SPEED | 94 · 3606-3666 · Y'ALL LIED BRO |
| 2nd | 59 · WAIT DO I MILK THEM? | 59 · MILK THE COWS? |
| 3rd | 57 · CALL ME EINSTEIN | 54 · CALL ME EINSTEIN |

New "what": *Speed blindly trusts chat to pick a door, enters the wrong one, and immediately explodes in rage at
the audience for lying to him.* The new cut starts 38 s earlier, on "come on chat please don't lie to me ... I'm
gonna go in the middle": the setup a stranger needs for "you liars" to land. The old cut starts mid-scream.

### 4500-4980 (the alien; the recording made "HE FOUND THE ALIEN" 4607 and "I CAN'T DIE WITH THIS ALIEN" 4778)

| | old | new |
|---|---|---|
| best | 87 · 4607-4662 · WE FOUND THE ALIEN | 93 · 4604-4646 · HE FOUND THE ALIEN |
| 2nd | 59 · 4770-4811 · ALIEN SAVES SPEED | 84 · 4766-4823 · EVACUATE WITH ALIEN |
| 3rd | 45 · ALIEN SAVED ME | 35 · W ALIEN EASTER EGG |

The second pick is where the story shows: the new judge knows he is escaping the facility *with* the alien
("Speed triggers an evacuation protocol, panics while running to the elevator with the alien in his hand") and
scores it 84, close to the recording's own 89; the old judge read it as "the alien saves Speed" and gave 59. In
an earlier run of the same stretch the new judge named the joke exactly ("discovering ... KSI hidden as an alien",
Speed: "it was you the whole time, you fat forehead"), and titled the escape "Speed Escapes Security With KSI
Alien"; the rerun lost the KSI detail, so this is run-to-run variance, not a guarantee.

### 6700-7180 (Bigfoot and the robocall; the recording made "HE WILL HURT YOU" and "AI CALLED HIM KINKY BITCH")

| | old | new |
|---|---|---|
| best | 82 · 6796-6845 · NATIONAL GEOGRAPHY NEWS | 95 · 6928-6956 · NPC CALLED HIM A KINKY BITCH |
| 2nd | 81 · 6928-6956 · KINKY BITCH ROAST | 74 · 6781-6838 · HE FOUND BIGFOOT THEN LOST IT |
| 3rd | 50 · STAND IN MIST UNTIL PASS OUT | 37 · STAND IN MIST UNTIL YOU PASS OUT |

"NATIONAL GEOGRAPHY NEWS" is a random quote a stranger cannot read; the new hook names the event (he spots
Bigfoot, screams about National Geographic, and it vanishes). On the robocall, the old title says *Speed* called
Lucia a kinky bitch; the screen text (game subtitles "...burning down a data center could be considered
terrorism ... federal investigation") let the new judge see that the line belongs to a game character. It is
still not fully right: it is the player character insulting an insurance robocaller and Speed telling her to
shut up, while the new judge says the NPC insulted Speed.

### 13700-14180 (the Ghost Woman search; the recording made "YOU TWO ARE FREAKS" 13806)

| | old | new |
|---|---|---|
| best | 78 · 14107-14138 · DO NOT CALL ME BLIND | 59 · 13992-14010 · HE GOT EXPOSED LIVE |
| 2nd | 59 · HE MISREAD THE MAP | 59 · 13779-13839 · IT'S TOO LATE BRO |
| 3rd | 44 · IT'S TOO LATE NOW | 59 · 14050-14102 · DO NOT CALL ME BLIND |

New "what" for the first: *Speed confidently directs chat to "Washington Bay" for the Dexter easter egg, but
chat corrects him that the map says "Watson Bay".* More specific than the old "he misread the map", but the
three critics said "skip" to everything here, so nothing would be clipped at the live bar (80) by either judge.
Neither found the game character's "you two are freaks" roast the recording clipped.

### Hooks, old -> new (same moment)

- CHAT LIED TO SPEED -> Y'ALL LIED BRO (title "Speed Screams At Chat For Lying About The Door")
- ALIEN SAVES SPEED (59) -> EVACUATE WITH ALIEN (84)
- NATIONAL GEOGRAPHY NEWS -> HE FOUND BIGFOOT THEN LOST IT
- KINKY BITCH ROAST ("Speed calls Lucia...") -> NPC CALLED HIM A KINKY BITCH
- HE MISREAD THE MAP -> HE GOT EXPOSED LIVE ("Washington Bay" vs "Watson Bay")

### Repeats

The first new run let the final desk name a made clip by number ("M4") and it called two unrelated moments
repeats, capping the KSI find at 59. Fixed before the numbers above: the desk must copy the made clip's hook, and
the claim only counts when the two clips share at least two telling words (`judge.repeat_of`, `same_story`). In
the rerun no false repeat was raised. The showrunner's drops go through the same check.

## Cost per stretch (live check, 8 minutes, same AI, averaged over the four stretches)

| | calls | tokens | wall time |
|---|---|---|---|
| old | 6 | 27.0k | 31.6 s (19.6-61.4) |
| new, the judge | 7 | 46.3k | 41.3 s (38.0-44.3) |
| new, story read (parallel, every check) | +1 | +2.8k | +0 (about 14 s on its own thread) |
| new, frames + screen text | 0 | 0 | +3-5 s (local) |

The first new run had one critic answer take 83 s (service latency), giving a 126 s check; still inside a
three-minute check interval, and `LIVE_AI_TIMEOUT` bounds every call.

## Finished-video mode (one 20-minute block, 3300-4500, through `brain.find_clips`)

The same stream treated as a finished video: the whole transcript is known, so the story is read once in 35
ten-minute parts at the same time and joined (36 calls, 128k tokens, about 1.5 min of wall time; kept in the
job's `story.json` and reused by every later block). The block's three 8-minute stretches (90 s overlap) are
judged two at a time, then the showrunner compares the finalists with each other and with the clips already
made. Whole block: 58 calls, 277k tokens (149k without the one-off story), 203 s including the story.

| score | cut | hook | the judge's "what happens" |
|---|---|---|---|
| 97 | 3623-3666 | CHAT LIED TO ME | follows chat's advice to enter the middle door, gets trapped, screams that chat lied |
| 95 | 3917-3941 | BRINGING MY HUSBAND | loudly declares he is bringing his "husband" Jason to fight aliens |
| 91 | 4308-4326 | SCARED DADDY | enters a creepy basement, calls Jason "daddy" for comfort and admits he is scared |
| 86 | 3460-3488 | Y'ALL LIED BRO | screams at chat for the wrong code, corrects himself, "call me Albert Einstein" |
| 78 | 4419-4436 | ALIENS DRINK MILK | an in-game tape reveals aliens drink raw cow's milk "like a drug" |

The showrunner dropped two repeats: "DO I MILK THE COWS?" (same joke as "WHAT ARE THESE COWS") and "Y'ALL LOVE
ME" (same as "BRINGING MY HUSBAND"). The joined story got the arc right (UFO hunt, dream code, Bigfoot, demon,
crab, Dexter room, Satan) and linked setups to payoffs ("604 Find the UFO at 2 AM -> 1093 UFO found"), but it
also calls Jason "a friend on call" when he is the second playable character, and that mistake reaches the
"SCARED DADDY" description. For a 2-hour video this mode costs about one story read per 10 minutes (in
parallel) plus roughly a minute per 10-minute block, so a 2-hour video is judged in about 15 minutes.

## Where the new judge is not better

- **It is harsher.** On the quiet Ghost Woman stretch it said "skip" to everything (old: one 78). At the
  live bar both would make nothing there, but on a lower bar the old judge would clip more.
- **Attribution is better, not solved.** The kinky-bitch robocall is still told as "the NPC insulted Speed".
  Without a vision model it cannot see faces; the OCR reads subtitles, chat and overlays, with misspellings.
- **Variance.** The same stretch gave "KSI" in one run and plain "the alien" in the next.
- **Cuts can be long.** Pulling in the setup made the door clip 60 s (the old one was 48 s); the critics are
  told a long setup costs the hook, and a setup that would push the payoff out is cut from the front.
- **It costs about 1.7x the tokens and 1.3x the time** of the old judge per live check, plus one story read.
- **The live comparison is partial on loudness and frames**: both come only from the clips' source files.
