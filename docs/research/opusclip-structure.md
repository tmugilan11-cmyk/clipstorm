# OpusClip structure, and where Clipstorm falls short

Written 2026-11-23. Sources: all 98 pages of the OpusClip help centre in `opus-md/` (read; the billing, login,
affiliate and payment pages are skimmed because they describe a paid service, not a screen), 84 screenshots from
`opus-ui/` looked at on contact sheets (result page, score badge, brand kit, submit page, calendar, bulk scheduler,
auto import, editor, B-roll, music, speech cleanup, team, social accounts, project menus), and
`opusforge/INVENTORY.md` (that file is about face tracking code, not screens, so it only informs the reframing row).
"Clipstorm has" was checked in `web/index.html`, `web/feat/*.js` and the running app on 127.0.0.1:8798.

## OpusClip's skeleton in one paragraph

A left sidebar: Home (Quick Start), My projects (collections + project cards), Brand kit, Asset library, then
Post: Calendar, Analytics, Social accounts, then Subscription, API, Help. **Home is the submit page**: a link box (or
Upload / Google Drive), a Recipe picker plus Brand kit picker, the recipe's settings (Clipping: model, genre chips,
clip length, "include specific moments" prompt, processing timeframe; Essentials: Captions with style tiles, Auto hook,
Motion graphics, AI emojis, B-roll...), and a right-hand **Summary** with the cost and one **Create** button.
**A project page** lists clips best first, one row per clip: rank and title, like/dislike, a big score with four letter
grades (Hook, Flow, Value, Trend), the preview, the transcript with a scene analysis, and a column of actions (Edit clip,
AI tools, 9:16, Duplicate, Publish on social, Download HD, Export XML). A toolbar above has Select, Filter, Sort (score or
chronological) and a Grid/List switch; Select turns on checkboxes and a bar with Bulk schedule and Bulk download.
**The editor** has three zones: the transcript on the left (click a word to edit, select text to delete, "Add a section"
to pull in more of the source), the preview in the centre with a toolbar (9:16, Layout, Tracker, Crop), and a vertical
icon rail on the right (AI enhance, Captions, Media, Brand kit, B-roll, Transitions, Text, Music, AI hook) opening one
panel at a time, with a timeline underneath. **Calendar** is a month grid of scheduled and posted clips; clicking one
opens "Edit scheduled post".

## Area by area

Value is for a solo streamer who turns long VODs and live streams into shorts (5 = most useful).

| # | Area | What OpusClip does and how it is laid out | What Clipstorm had | Gap | Value |
|---|------|-------------------------------------------|--------------------|-----|-------|
| 1 | Project page / clip list | Rank + title, score with Hook/Flow/Value/Trend grades, like/dislike, transcript + scene analysis, action column; Filter, Sort (score / chronological), Grid/List, Select with bulk bar; each project is its own page; project cards on "My projects" with collections and expiry. | One long page listing every video with all its clips under it (filters.js adds status pills and a text search). Clips sorted best first with a score badge and the "why" line. Bulk bar: delete, download. No project page, no list view, no filter by score/length/kind, no grades, no chronological order. | Whole structure. A project is not a place you go to; 14 videos with 72 clips is one scroll. | 5 |
| 2 | Home / upload flow | Link box; Recipe + Brand kit pickers; clipping settings with genre chips, clip length presets, a "what to look for" prompt, processing timeframe; caption style tiles; Summary + Create. | Link box and file drop, creator picker, hidden "Options" with counts (how many, shortest, longest), caption tiles, layout tiles, quality, part of the video. No prompt, no length presets, no clip type, no way to save a setup, no summary. | The settings a clipper reaches for most (what to look for, how long, what kind) were missing or buried. | 5 |
| 3 | Clip editor arrangement | Transcript left, preview centre, icon rail right, one panel at a time, timeline below; delete words to cut; Add a section. | A dialog: video left, five-tab panel right (Look, Cut, Sound, Post, Captions). The words sit at the bottom of the Captions tab and only jump the video. No transcript beside the video. | Transcript is hidden three clicks deep; tabs are a strip, not a rail. | 4 |
| 4 | Score and why | 0-99 with four grades per clip, "Scene analysis" text, Trending tag. | One number badge and a one-line reason. The judge already returns five marks per clip (hook, payoff, emotion, share, standalone) but the page showed only two of them, in the editor. | The page did not use data the server already sends. | 4 |
| 5 | Scheduling / calendar | Month calendar of posts; click a post to edit; Bulk schedule (order, start time, frequency); thumbnails; hashtags. | Post queue per account spaced by the server; posts show as pills on clips. The menu row called "Calendar" actually opens the timer page (Windows Task Scheduler text). No calendar, no bulk post. | A real calendar and a bulk post from the clip list. | 4 |
| 6 | Brand kit | One kit, four aspect ratios, live preview with safe zones, logo drag, caption + headline style, layouts, intro/outro, music; Recipes bundle the kit with feature toggles. | Brand page with a rendered preview, saved brand feeds every new clip (`_brand_prefs`); Asset library for pictures. No named, switchable kits or recipes. | Saved setups. Partly closed by the setups in the new upload flow. | 3 |
| 7 | Captions | Preset tiles, size/colour/stroke/shadow, position drag, edit words, bulk apply, custom fonts, brand vocabulary. | 35+ caption looks drawn as real frames, editor quick looks, per-clip caption toggle, word-fix table (chad = chat). No drag position, no per-word editing beyond re-make. | Word editing in the transcript column. | 3 |
| 8 | Reframing / layouts | Fill, Fit, Split, Three, Four, ScreenShare, Gameplay; Subject tracking; manual crop. | Five layouts including stacked game + facecam with person tracking; webcam found by stillness. | Manual crop and per-scene layout. Not a structure problem. | 2 |
| 9 | AI hook / title | Auto headline on top clips, Viral hook templates, AI voiceover hook. | Hook text on every clip, title and description, hook learning, live heading preview. | Templates for hooks (judge/clip-type owners). | 2 |
| 10 | ClipAnything prompt | "Include specific moments" box on submit and again on the results page ("re-prompt"), with suggested prompts. | A creator-level "What should it look for?" field, read by the judge; nothing on the submit box or the results page. | Prompt at the place you start; re-prompt a finished video (needs a server change). | 5 |
| 11 | B-roll / assets | AI B-roll, stock, media library, intro/outro cards. | Pictures on clips (poster, logo, sticker), meme sounds and music bed, Audio page. | AI B-roll is out of scope for a local tool. | 1 |
| 12 | Analytics | Per-clip views across platforms. | Insights section: many pages, own results, learning loop. | Ahead of OpusClip. | 0 |
| 13 | Social accounts | Connect YouTube, TikTok, IG, FB, LinkedIn, X, Pinterest, Threads, Bluesky. | Connected apps, native posting + Zernio for sixteen platforms. | Equal. | 0 |
| 14 | Team / credits / settings | Team workspace with invite link; credits per minute; storage and project expiry. | Optional multi-user accounts, AI usage page, storage page. No credits (local). | Not needed for one owner. | 0 |
| 15 | Library features | Collections, Favorites, Duplicate clip, Share project, Auto Import of new channel videos, Zapier/API. | Creators with auto recording; autopilot; nothing for collections, favourites or duplicates. | Favourites and duplicate; auto import already exists for live. | 2 |

## Ranked gaps (top 10)

1. No project page: all videos and all clips are one scroll (row 1).
2. No "what to look for" prompt where a video is submitted (row 10, row 2).
3. No filter by score, length or kind; no Grid/List switch; no chronological sort (row 1).
4. The score is a number with no reasons on the card; four of the five judge marks were unused (row 4).
5. No clip length presets, no clip type on the submit box, no saved setup (row 2, row 6).
6. Transcript is not beside the video in the editor (row 3).
7. The "Calendar" menu row is not a calendar; scheduled posts cannot be seen by day (row 5).
8. No bulk post from a selection; bulk bar offered only download and delete (row 5).
9. No Keep / Skip decision on the clip list itself (it lived only on the Review page) (row 1).
10. No favourites, duplicate or share link (row 15).

## What was rebuilt (see the final report for screenshots)

Items 1, 3, 4, 5, 6, 7, 8 and 9 are built. Item 2 is built as far as the server allows: the box saves to the chosen
creator's "What should it look for?" because `studio/jobs.py` accepts no per-video focus; the lead can add one
(`clean_options` would need a `focus` key and `find_clips(focus=...)` would read the job first). Item 10 is not built.
