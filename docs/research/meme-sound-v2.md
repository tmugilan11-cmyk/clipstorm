# Meme sounds, version 2: why the old picker chose badly, and what it chooses now

Measured on 2026-11-23 on the owner's stream "Exploring Vice City" (IShowSpeed, GTA 6, live recording
`20261123-031229-2a242e90af`), with the AI this install uses (custom OpenAI-compatible service, model
`qwen3-5-35b-a3b-bf16`). The clips were only read: the old and new picks were mixed onto copies in
`.pctest/meme-demo/` (`clipNNN_old.mp4`, `clipNNN_new.mp4`), never onto the owner's files. Every demo
file was checked with `render.av_gap`: all were under 0.035 s.

## Why the old picker was bad

The old picker (`soundplan.plan`, still in the file for this comparison) asked the AI one question:
"which line, which mood word". Then `soundplan.sounds_for` searched the catalogue for that one word and took
the first row. Run on five real clips, it went wrong in five ways:

1. **The AI never saw a sound.** It chose from 14 mood words. "angry" became "AUGHHHHH... AUGHHHHH" (a
   SpongeBob scream), "shock" became a generic "Shocked sound", "funny" would have become "HAha funny laugh",
   "hype" "NFL Bass Boosted". The AI could not choose "Wasted" for a GTA fail or "Hallelujah" for a
   religious victory, because it never knew they existed.
2. **No sense of the moment.** A deer reveal (anticlimax) got a "shock" sound. A clip of rage at chat got
   three different sounds, ending with crickets, which is a sound for an awkward silence, after a shouted line.
3. **Bad timing.** A time was the first word of a three-word group. Every sound started on top of the
   streamer's voice: "SpongeBob Fail" started in the middle of the voicemail line ("...reach is not
   available"), and "Shocked sound" started on the word "deer", the punchline itself.
4. **No idea of a sound's length.** "Victory Screech" is 7.7 s long. It was put at 3.4 s on a 15 s clip
   and played over "God is good. God is great." The cue had no end.
5. **A small, random shelf.** The shelf held 7 sounds, three of them random foreign-language trending
   clips (Hindi, Indonesian, German). Nothing was known about any of them. The same sound could also go
   on a clip twice (clip015 got "SpongeBob Fail" twice).

## What was built

- **A sound knowledge base** (`studio/sound_kb.py`, kept in `data/memesounds/knowledge.json`, researched
  again after a week). It covers the myinstants best-of-all-time list (6 pages) and trending list
  (3 pages), the catalogue's trending lists, 108 classic meme sounds searched by name, and the owner's own
  shelf. Each sound is researched in several places: its myinstants page (plays and saves), uploads with
  similar names, Know Your Meme's "About" and "Spread" sections, and YouTube search (views and the
  titles of edits that use it). The AI then reads all of that in batches of 8 and writes down:
  - what the sound means;
  - the moments it is used for, from a fixed list of 24;
  - when to use it and when not to;
  - where it goes against speech;
  - energy, how popular it is now, how well it fits stream clips, and whether it has words.

  Each file is downloaded from the catalogue only (dankmachine.com, the same place `memesound.py`
  already uses) into `data/memesounds/kb/`, at most 1.5 MB. Its length, its silent start, how long it
  rings and its loudness are measured from the file.
- **A sound team** (`studio/sound_pick.py`, `studio/sound_moment.py`). It works like the judge:
  - The clip is measured: its words on the clip's own clock, each pause and how long it is, and its
    loudness against the streamer's usual voice.
  - A reader finds the beats. Each beat hangs on a real word, either on it or after it.
  - The frames at those beats are looked at when the AI can see pictures. This install's model answers
    "503 model unavailable" to pictures, so this step is skipped and remembered for an hour.
  - Up to 4 myinstants searches are run for this clip's sounds, and the sounds found are downloaded and
    measured.
  - Three pickers propose sounds: a meme page owner, a trend watcher and a comedy editor.
  - Each proposal is placed for real: the hit lands on the beat, a sound with words waits for the word it
    answers and is dropped if it would cover the next line, the level is set against the voice, and the
    end of the clip is taken into account.
  - Two critics, who never see each other's answers, judge each placed proposal: does it fit, is the
    timing right, will people recognise it, and would a meme page use it here. A proposal needs both
    critics, or one critic and a fit of 7.5 or more.
  - A sound designer signs off at most 1, 2 or 3 sounds, depending on the clip's length. No sound at all
    is a valid answer.
- **The mix** (`memesound.mix`):
  - A sound that is heard for more than 1.5 s is ducked under the clip's own voice (the same
    sidechain music beds use).
  - Every cue fades out over 80 ms when it is cut.
  - The mixed file now ends with the picture. Some finished clips carry 0.5 s more sound than picture
    (clip015: 44.27 s of picture, 44.80 s of sound, `av_gap` 0.53). The old mix kept that gap. The new
    one gives 0.0003.

## Old against new, on the same clips

| Clip | The moment | Old pick | New pick | Why the new one is right |
|---|---|---|---|---|
| clip015 "HE DIDN'T PICK UP" (44 s) | Speed calls the Bigfoot number and gets a voicemail: "not available... goodbye. He didn't pick up." | "SpongeBob Fail" at 39.5 s, on the middle of the voicemail line, and again at 43.4 s on "he didn't pick up". The same sound twice, both on top of words. | "Sad Trombone" with its hit at 40.38 s, right after "available". It is ducked under "please try again later... he didn't pick up". | One sound, on the instant the call fails. The two pickers who chose a horn were split between "Womp Womp" and "Sad Trombone", and the designer kept the better-known one. "BRUH" at the very end was left out because the clip ends before it can be heard. |
| clip023 "ALIEN COME OUT BABY" (15.5 s) | A build-up hunting for a UFO, then "Oh, there you go... that's a damn deer." | "Shocked sound" at 12.55 s, on the word "deer". It is the wrong meaning (shock, not a letdown) and it covers the punchline. | "Sad Trombone" with its hit at 13.44 s, in the 2.1 s of quiet after "deer." | All three pickers chose it. Both critics marked it 8.5 for fit and 8.5 for timing. It says "anticlimax" and lands after the word. |
| clip038 "BYE BYE SATAN" (15.5 s) | The demon is dead: "God is good. God is great. God is good." | "Victory Screech - SpongeBob" (7.7 s) at 3.4 s, screeching over all the "God is good" lines. | "Hallelujah" (1.8 s) with its hit at 11.35 s, in the pause after "God is great", ending before "God is good". | It means the moment (a religious victory), and it is played whole in the quiet. "GTA SA Mission Passed" was also approved, but the designer kept the shorter, stronger one. |
| clip043 "HE DID NOT EXPECT THAT" (16.9 s) | Speed celebrates ("I cannot wait"), then chat shuts him down: "Oh, shit." | "Shocked sound" at 15.87 s, on "shit". | "record scratch" with its hit at 14.56 s, in the quiet after "I cannot wait", just before "Oh, shit". | The classic "the celebration stops here" sound. "Vine boom" on "shit" was turned down because it played over the word and the clip ended before it rang out. |
| clip006 "Y'ALL LIED TO ME" (34.8 s) | Chat sends him through the wrong alien door: "It's the wrong one... you fucking liars." | "SpongeBob Fail" on "wrong", "AUGHHHHH" on "liars" (over his words), and crickets at the end of a rage clip. Three sounds. | "GTA V - Wasted" with its hit on "wrong" (5.03 s), ducked under the rage that follows. | One iconic GTA sound for the fail, on a GTA clip. "Emotional Damage", "AUGHHHHH" and "oh no no no" were refused by the placement because their words would have covered his next line. "Buzzer" and "Fortnite death" were skipped by the critics. |

## Cost

- **Per clip:** 7 AI calls (reader, 3 pickers, 2 critics, designer), about 21,000 tokens, 12 to 22 web
  reads (myinstants searches and sound pages), and 16 to 22 s in total. There are no vision calls on
  this install.
- **The weekly knowledge build:** 30 AI calls, about 125,000 tokens, about 1,040 web reads, and about
  11 minutes. It researched 239 sounds, and 3 songs were left out for being longer than 30 s. The
  copies take 21 MB.

## What I could not do

- `studio/web.py`'s Bing search answers this machine with unrelated pages (dictionary entries for "most",
  physics homework for "bruh sound effect"), so the sound research reads myinstants, Know Your Meme and
  YouTube directly (`studio/sound_web.py`). TikTok cannot be read without signing in.
- The vision step is wired in and tested, but this model does not take pictures.
