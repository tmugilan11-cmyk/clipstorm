# Adding meme SFX on a timeline — how the pros do it, and what a web app should copy

**Scope:** read-only research. Question: for a web app that lets someone drop meme sounds onto a short-form vertical video, what do the established tools actually do, and what is the minimum UX that does not feel broken?

**Method note:** every claim below is followed by the URL I read it from. Claims that are *my inference* (not in a source) are marked **[own reasoning]**. Claims I could not confirm against a primary source are marked **Could not verify**. I did not invent any numbers; where a number appears it is quoted from the cited page.

**Access date:** 2026-11-20.

A note on source quality, because it matters for how much weight to give each section: CapCut, Canva, Blackmagic and the meme-sound sites served real HTML that I could read in full. Adobe's `helpx.adobe.com` pages are client-rendered behind a bot filter — I could confirm pages *exist* and could read their navigation, but not their body text. So the Adobe sections rest on page existence, navigation labels, and search-result snippets rather than quoted instructions, and I say so inline.

---

## 1. What each tool does

### 1.1 CapCut (desktop/web + mobile)

CapCut publishes an explicit numbered workflow for sound effects. From CapCut's own how-to guide ([capcut.com](https://www.capcut.com/resource/how-to-add-or-replace-voiceovers-music-and-sound-effects-in-capcut)):

> 1. In the left sidebar of the online editor, click **Audio**, then open **Sound effects**.
> 2. Browse categories such as **Magic, Laugh, Transition, Fight, and Horror**, or search for a specific effect such as "whoosh" or "click."
> 3. **Click + next to the effect, or drag it onto the timeline.**
> 4. **Move the effect to the moment it belongs to.**
> 5. Adjust its **volume, speed, pitch, fade-in, and fade-out** against the dialogue and music so it does not overpower the mix.

That single list answers most of question 1:

- **Search vs browse:** both. A flat search box *and* curated categories ("Magic, Laugh, Transition, Fight, Horror"). The category names are use-case/mood words, not technical ones — that is a deliberate choice for non-sound-designers.
- **Preview:** the doc does not describe a dedicated preview/audition step for SFX. **Could not verify** whether clicking a result auditions it before placing it. [own reasoning] Given step 3 is "click + or drag", the click-to-add gesture is probably the same click that plays it — a single-click "hear it, and if you like it it's on the timeline" model. Do not take that as sourced.
- **Placement:** *two* gestures are supported — click `+` (append, then move) and drag onto the timeline. CapCut supports drag-to-timeline for sound. That is confirmed for music too, in the same doc: "Drag the track you want from the library onto the timeline, then adjust its level, speed, and noise reduction, and set how long it fades in and out."
- **After placement:** step 4 exists as its own step — you drop it, *then* nudge it to the moment. That tells you the drop position does not have to be precise. [own reasoning] The product expects a two-phase interaction: coarse placement, then fine positioning by dragging the clip.
- **Per-clip controls CapCut exposes on an SFX:** volume, speed, pitch, fade-in, fade-out. Note what is *absent*: no EQ, no compression, no ducking, no per-clip sends. Five controls.

**Mobile vs desktop.** The same doc states "Sound effects can be added online, on a PC, or on a phone," and the voiceover section enumerates platforms ("web, PC/Mac, iOS, Android"). It does not give a separate mobile-only SFX menu path.

The widely-repeated claim that mobile uses "Audio → Sound FX" while desktop/web uses "Audio → Sound effects" appears only in third-party blogs, not in CapCut's docs — **Could not verify**.

**What a placed sound looks like on the track.** I could not get this from CapCut. Every CapCut help-centre URL I tried was dead: `/help/how-to-add-sound-effects` → 404, `/help/audio` → 404, `/help-center` → HTTP 451, `help.capcut.com` → DNS failure. **Could not verify** CapCut's waveform rendering, label, or duration display.

**What happens when the SFX is longer than the clip.** **Could not verify** from CapCut's docs.

**[own reasoning]** In every track-based NLE, an audio clip on its own track simply continues past a video cut — it is not clipped by the video above it, because tracks are independent. CapCut's model (separate audio row under the video row) implies the same. The practical consequence for a web app: do not truncate an SFX to the underlying clip; let it ring out, and only cut it if the user trims it or the sequence ends.

---

### 1.2 Premiere Pro

Premiere's docs are the hardest to read here, because Adobe's `helpx.adobe.com` pages are client-rendered and my fetches returned only navigation chrome. What I *can* verify is that these pages exist and what they are called, by reading the left-hand navigation of the audio-effects section ([helpx.adobe.com/premiere/.../audio-effects-library.html](https://helpx.adobe.com/premiere/desktop/add-audio-effects/apply-audio-effects/audio-effects-library.html)):

- Under audio effects: **"Apply audio transitions"**, **"Add effects to audio tracks"**, **"Copy and paste audio effects in the timeline"**, **"Audio Track Mixer automation modes"**, **"Basic audio editing"**, **"Adjust volume and levels"**.
- Under editing: **"Trim a clip"**, **"Cut clips"**, **"Perform ripple edits"**, **"Perform rolling edit"**, **"Perform slip edits"**, **"Perform slide edits"**, **"Perform J cuts and L cuts"**, **"About Trim mode"**.

That navigation *is* the evidence for the model: Premiere's own table of contents organises audio work around (a) a clip on a track, (b) trimming its two edges, (c) transitions/effects applied *to the clip*, (d) volume and levels, and (e) automation of that volume over time. The individual `.../trim-clips` page 404s when opened directly, so I have no quotable body text. Any specific "how to add an SFX in Premiere" instruction from me would be unsourced — **Could not verify**.

**[own reasoning]** What this means for a short-form creator: Premiere's surface is enormous, but the subset a meme-SFX user touches is tiny and maps one-to-one onto Premiere's own nav: **toolbar trim at either edge** ("Trim a clip"), **delete**, **volume** ("Adjust volume and levels"), **fade** ("Apply audio transitions"), and **move**. Slip/slide/ripple/rolling/J-L cuts are professional trim variants that a person adding a 1.4-second whoosh never opens.

---

### 1.3 DaVinci Resolve

Resolve's product pages are readable in full. The Edit page is described as "the world's most advanced professional non-linear editor. The familiar track layout, dual monitor design and traditional workflow … features **drag and drop editing**, context sensitive automatic trimming tools, fully customizable keyboard shortcuts" ([blackmagicdesign.com/products/davinciresolve/editor](https://www.blackmagicdesign.com/products/davinciresolve/editor)).

The Fairlight page is "completely integrated with picture editing" and lets you "move between sound editing and picture editing with a single click," scaling to "projects with over a thousand tracks," with "dozens of professional tools for recording, editing, mixing … mastering" ([blackmagicdesign.com/products/davinciresolve/fairlight](https://www.blackmagicdesign.com/products/davinciresolve/fairlight)).

The one directly quotable interaction detail, from the same page, is the clip-hit-zone convention: **"Click the lower half of a clip to select or move it, the upper half to set an edit point."** That is Resolve solving the exact ambiguity a web timeline has — *is this drag a move or a trim?* — by splitting the clip into two hit zones vertically.

---

### 1.4 Canva video editor

Canva is the clearest example of "designed for non-professionals" and it is fully documented.

**Placement is one click, at the playhead — not a drag.** From [canva.com/help/stock-music](https://www.canva.com/help/stock-music/):

> From the editor side panel, select the **Audio** tab … Scroll through the categories or use the search bar. Select **See all** next to each to browse all the options. **Select a track to add it to your design. If you're using a video template, it'll go where your playhead (timestamp) is on the timeline** at the bottom of the editor.

Three things worth extracting:

1. The insertion point is **the playhead**, and Canva says so explicitly. The user positions the playhead first, then clicks. No drag required, no precision drop needed.
2. There is a **cap**: "You can add and layer up to **50 audio tracks** to your design." (Effectively unlimited for a short.)
3. Browse-by-category and search coexist, same as CapCut.

**What a placed sound looks like.** "On the timeline at the bottom, select the audio you want to mute or remove. **It's a colored bar below the page thumbnails.**" So: a colored bar in a lane beneath the visual strip. Canva's slip instructions confirm a waveform is drawn inside that bar: "select **Slip** on the audio toolbar. **Drag the audio waves** into the colored section of the sound bar." (Both quotes from the same page.)

**Editing controls**, from [canva.com/help/trim-audio-and-adjust-volume](https://www.canva.com/help/trim-audio-and-adjust-volume/):

- **Trim:** "On the timeline, click to select the added track to edit it. **Hover your mouse cursor over it. Trim handles will appear.** Drag any of the trim handles to adjust." — handles appear on hover, i.e. the trim affordance is hidden until intent is shown. Also: "drag the trim handles to **shorten** the track, or **drag the end of the track to extend** it."
- **Slip (change which part of the sound plays without moving it):** "select **Slip** on the audio toolbar. Drag the audio waves into the colored section of the sound bar. The design will play the part of the track inside this colored section." — this is the "the sound is longer than what I want, give me a different 2 seconds of it" control, presented as a drag of the waveform itself.
- **Volume:** select track → volume icon on toolbar above the editor → slider or textbox. Plus a one-click **"Balance all"** to "automatically balance the volume of all audio and video in your design."
- **Fade:** select track → **Fade** on toolbar → slider/textbox. Canva also now applies fade to *video clips* directly ("Select the video on your canvas. From the toolbar, select **Audio tools**. Drag the **Fade in** or **Fade out** sliders").
- **Delete:** "right-click on the audio and select **Delete track**."
- **Beat Sync:** a separate button above the editor to sync audio to video automatically.

Canva is the best single model to copy for placement UX: *playhead + one click*, with the drop position being exact by construction.

---

### 1.5 Adobe Express

Adobe Express has the right pages but I could not read their bodies — `helpx.adobe.com` returns ~447 bytes to curl and only navigation to a real browser; `adobe.com/express/feature/*` returns an Akamai **"Access Denied"** page. So this section is snippet-level.

- Page exists: [helpx.adobe.com/express/web/audio-and-animation/audio.html](https://helpx.adobe.com/express/web/audio-and-animation/audio.html), titled "Add audio tracks to designs". Its search-result summary reads: "Add multiple audio tracks to your design by uploading files from your device or selecting music and sound effects in Adobe Express. **You can add up to three audio tracks, two for music or sound effects and one for voiceovers.**" (Search snippet, not page body — treat the three-track cap as **provisional**.)
- Page exists: [helpx.adobe.com/express/web/audio-and-animation/sound-effects.html](https://helpx.adobe.com/express/web/audio-and-animation/sound-effects.html), titled "Add sound effects". Snippet: "Select the audio track layer—or a video clip with audio—then choose **Enhance speech** from the Audio panel."
- The product feature page [adobe.com/express/feature/audio/sound-effects](https://www.adobe.com/express/feature/audio/sound-effects) is described in its own search snippet as: "Add texture to your video quickly and easily with the wide variety of Adobe Express sound effects. **Adjust the duration and volume of the effect**."

The pattern Adobe is claiming is a hard **structural** simplification: not "here are 40 controls", but "you get two SFX/music lanes and one voice lane, full stop." Whether the cap is really three, and whether insertion is playhead-based or drag-based, is **Could not verify** from primary page body.

[own reasoning] A 3-lane cap is a *layout* decision that removes a whole class of user error (sounds stacking on top of each other invisibly) without removing any power a short-form creator needs.

---

### 1.6 Meme sound libraries

The interesting finding here is that these sites expose **very different metadata**, and the ones that surface *use-case* and *recency* beat the ones that surface raw play counts.

**MyInstants** ([myinstants.com](https://www.myinstants.com/en/instant/vine-boom-sound-70972/)). Per-sound page exposes: title ("VINE BOOM SOUND"), category breadcrumb ("Sounds > Sound Effects"), favourite count ("590,341 users favorited this sound button"), view count ("12,035,525 views"), and actions Add to my soundboard / Share / Copy link / Report / Download MP3 / Embed.

- **No duration. No mood tags. No use-case tags.** The only quality signals are favourites and views, both shown as big raw integers.
- List pages (e.g. [`/en/search/?name=boom`](https://www.myinstants.com/en/search/?name=boom)) are a **flat grid of round play buttons** — 108 per page in my fetch — with no duration, no sort control, no popularity ordering visible.
- Navigation is **14 fixed categories**: Anime & Manga, Games, Memes, Movies, Music, Politics, Pranks, Reactions, Sound Effects, Sports, Television, Tiktok Trends, Viral, Whatsapp Audios. The home page surfaces "Trending in United States" as a plain list of names.

**101soundboards** ([101soundboards.com](https://www.101soundboards.com/)). Top-level nav exposes: Search, **Funny**, **New**, **Topics** (tags), **Trending**, Lists, and **Live** ("Real-time View of Sounds playing now"), plus editorial rows "Popular — Most Popular boards" and "Viral boards". Crucially its unit is the **board**, not the sound: a board page shows a description, a "Similar Boards" cross-link block, and two unlabelled numbers (21,474 and 189,068 on the board I inspected) that the text extraction cannot attribute to plays vs favourites. **Could not verify** the meaning of those two counters.

**DankMachine** ([dankmachine.com](https://www.dankmachine.com/)). This is the most complete metadata model of the four, and it is worth copying. "38K meme buttons." Its home page is organised into **explicitly-named ranking modes**:

- "**Rising right now** — Blowing up in the last few hours"
- "**Fresh from the community** — New uploads. Vote them up or bury them."
- "**All-time legends** — The most played meme sounds ever. Tap ♡ to pin one to your board."

Each row carries an **inline, labelled stat and rank**: e.g. "smth INFORAMTION **#6** Memes · **9,410,010T** all-time", "VINE BOOM SOUND Memes · **7.5M** all-time", "BRUH Memes · **4.6M** all-time". So: rank, category, and a formatted all-time play count, all on the card.

It also runs **two independent taxonomy axes**:

1. **Categories** with counts — Memes 10195, Gaming 5644, Music 3098, Sound Effects 2580, Reactions 1892, Streamers & Celebs 1703, TV Shows 1595, Anime & Manga 1576, Cartoons 1451, Alerts & Ringtones 1258, Movies 1109, Animals 870, Sports 735, TikTok Trends 721, Scary & Jumpscares 690, Voice Notes 688, Brainrot 602, Farts & Gross 524, Politics 516, Pranks 288, Other 1891.
2. **"Sounds for every moment" / All uses** — a pure *use-case* facet list: TikTok, YouTube, Instagram Reels, CapCut, Discord, Twitch, OBS, Zoom and video calls, Video editing, Group chats, Reactions, Reveals, Transitions, Fails, Wins, Jumpscares, Notifications, **Punchlines**, Intros, Outros, Entrances, Roasts, Pranks, Background, Funny, Dramatic, Awkward, Victory, Fail, Surprise, Angry, Sad, Scary, Hype, Cringe, Wholesome, Chaotic, Suspense.

That second axis is the one worth stealing. It is *editorial ontology about where a sound goes in a video*, which is exactly the retrieval vocabulary an AI that places SFX needs.

**TikTok's built-in library.** From TikTok's own help page ([tiktok.com/support/faq_detail?id=7581821548110125580](https://www.tiktok.com/support/faq_detail?id=7581821548110125580&category=web_account)):

> Tap **Add sound** at the top of the recording screen … **Tap a sound to preview it.** Select a sound from the **For You, Favorites, or Recent** tab. Tap the **Search** button to search for a sound, then tap the **Continue ✓** button to confirm your choice.

So TikTok's ranking axes are literally **For You / Favorites / Recent** — a personalisation axis, a saved axis, and a recency axis, with no category grid at all. Preview is verified as its own tap ("tap a sound to preview it") before a distinct confirm tap.

Trim: "Tap the **Trim** button next to the sound you selected. **Drag the slider to set the starting point** of the sound. Tap the Confirm button ✓."

Placement model is **not a timeline**: "**Tap anywhere on the video to add the sound** to your post." Also verified there: sounds are hidden when unavailable for a given video length, and setting the video length to 15s or 60s restores them; and changing the music replaces any previous background music *and* the recorded voice.

**What makes "popular" meaningful.** [own reasoning, grounded in the above] MyInstants' raw "12,035,525 views" is a bad ranking signal for a sound-effects picker because it is a *lifetime* number — it tells you a sound went viral in 2019, not that it is funny now. The signals that are actually meaningful, in order:

1. **Velocity, not total** — DankMachine's "Rising right now — Blowing up in the last few hours" is the only one of the four that tries to measure *recency-weighted* popularity. "All-time" is a museum.
2. **Rank within a category**, not a global count — "#6 in Memes" is interpretable; "9,410,010 plays" is not.
3. **Use-case fit** — a sound tagged "Punchlines" is usable by the system; one tagged only "Movies" is not.
4. **Favourites** are a stronger signal than views, because they cost the user an action (MyInstants: 590,341 favourites vs 12.0M views on the same sound — about 5%).

---

### 1.7 AI auto sound-effect insertion

I expected this to be the richest section and it is the thinnest, because most of the named tools do not publicly describe auto-SFX placement.

**Descript** — [help.descript.com/generative-media/generate-audio](https://help.descript.com/generative-media/generate-audio.md). Descript has **AI sound-effect *generation*, not context-aware *placement***. Verified flow: AI Tools panel → **Generate audio** → **Music** or **Sound Effects** tab → text prompt (500-character limit for SFX, 1,000 for music) → **More options**: for SFX, "adjust **Duration** and whether the sound should **Loop**" → Generate. And: "Once you add generated audio to your composition, it **behaves like any other audio layer. Move it, trim it, adjust its volume, or apply effects** the same way you would have with imported audio."

Descript's adjacent automation that *does* matter for a timeline: **ducking**. Per its docs index ([help.descript.com/llms.txt](https://help.descript.com/llms.txt)), the page `effects-animations-transitions/lower-other-audio.md` covers a feature that "automatically reduces the volume of other audio layers when sound plays on a selected track." That is the single most valuable automatic behaviour for meme SFX — the meme is loud, everything else dips — and it is a *mixing* automation, not a placement one.

**Opus Clip** — the URL for an auto-SFX feature 404s: `https://www.opus.pro/blog/auto-sound-effects` → "Page not Found". The feature list visible on that 404 page is AI Producer, Animated captions, AI Reframe, ClipAnything, AI B-Roll ("Get relevant AI B-Roll in 1 click, under 1 minute"), Enhance speech, Export to XML — **no auto-SFX item**. **Could not verify** that Opus Clip places sound effects automatically. It does auto-place *b-roll*.

**Klap** — [klap.app](https://www.klap.app/) lists AI topic extraction, Auto Reframing, and AI Editing. No sound-effect auto-placement claim. **Could not verify.**

**Veed** — [veed.io/tools/add-sound-effects-to-video](https://www.veed.io/tools/add-sound-effects-to-video) returned 35 characters of unusable content. **Could not verify.**

**CapCut auto features / Adobe Podcast** — I found no documentation of context-aware SFX auto-placement for either. Adobe Podcast's public positioning is speech enhancement, not SFX. **Could not verify.**

**The one source that publishes actual density numbers** is not one of the named tools. Zella, a Mac/iPhone auto-SFX tool, publishes an editorial rule at [zellahq.com/blog/how-many-sound-effects-is-too-many-in-a-video](https://zellahq.com/blog/how-many-sound-effects-is-too-many-in-a-video/):

> **Quick answer:** about one cut sound every four to five seconds is the most a video can carry, and never two on cuts that sit next to each other.

> **One cut sound every four to five seconds, maximum. Never two on adjacent cuts.**

Its stated mechanism: "Below roughly four seconds of separation, repeated short transients stop being read as individual events and start being read as a pattern, and a pattern is background."

Its arithmetic: "For a sixty second short, that ceiling is about **twelve to fifteen** sounds. Most over-sauced videos have **forty**." And a fatigue claim: "After about fifteen seconds of regular transients, the sounds stop registering."

Its self-test: "Divide the video length in seconds by five. If you have more sounds than that number, you have too many."

Its guidance on where sounds go: "sounds go on the **opening cut**, on **section breaks**, and on **the one reveal that matters**. That is usually **three to six** sounds in a short."

A companion Zella page ([zellahq.com/blog/how-to-add-sound-effects-to-a-video-automatically](https://zellahq.com/blog/how-to-add-sound-effects-to-a-video-automatically/)) gives the three-family taxonomy and, importantly, the timing rule:

- **Whoosh** — "Something moved" — "A transition with motion: a slide, a whip, a zoom punch"
- **Impact** — "Something arrived" — "A hard cut you want to land, a title appearing, a reveal"
- **Riser** — "Something is coming" — "The seconds **BEFORE** a cut, building into it"

> "The riser is the one people get wrong. **It goes before the cut, not on it.**"

And a worked edge case: "If you have a rapid-fire sequence of six cuts, put a sound on the **first and the last**, and let the middle four be silent."

Zella also states the product does the placement: "In Zella, **Auto Sound** on Mac and **Auto sound at cuts** on iPhone place them for you in one tap." It does not publish a precision/recall metric for that placement — **no vendor in this research published one**. That is a real gap: nobody claims "we place the right sound at the right frame X% of the time."

[own reasoning] Two caveats on the Zella numbers: it is a vendor blog, not peer-reviewed research, and its "twelve to fifteen for sixty seconds" is the *ceiling of tolerance*, explicitly framed as "the most a video can carry" — not a recommendation. Its actual recommended practice ("three to six sounds in a short") is 4–5× lower than its ceiling. Any product that reads "12–15" as its target will produce the over-sauced videos the article is complaining about.

---

### 1.8 Drag-and-drop timeline UX on the web

**Native HTML5 drag-and-drop** ([MDN, HTML Drag and Drop API](https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API)) — verified behaviours:

- "HTML drag-and-drop uses the DOM event model and **drag events inherited from mouse events**. During drag operations, several event types are fired, and some events might fire many times, such as the `drag` and `dragover` events."
- "Any element can become a drop target by **canceling the `dragover` event** that fires on it with `preventDefault()`."
- "**The only time to make any modifications to the data store is within the `dragstart` handler** — for the `dataTransfer` of any other drag event, the data store is unmodifiable."
- "You can't transfer JavaScript objects directly … the data must be **serialized to a string** (or as a `File`)."

**Touch:** the MDN page's text contains no occurrence of "touch" at all. [own reasoning from that absence] Native HTML5 DnD is mouse-only in practice; on iOS/Android it does not fire, so a web timeline built on it is dead on tablets and on mobile browsers. For a short-form video app — whose users are overwhelmingly on phones — that alone disqualifies it.

Additional well-known native-DnD problems [own reasoning]: the drag image is a browser-generated ghost of the element, which for a "2.3s whoosh" chip is a useless rectangle with no time offset; you cannot render a live "drop indicator at time 00:12.4" from inside the native drag; and `dragover` firing "many times" means you must throttle your own hit-testing anyway.

**dnd-kit** ([docs.dndkit.com](https://docs.dndkit.com/)) — the relevant verified facts:

- Default collision detection: "By default, `DndContext` uses the **rectangle intersection** collision detection algorithm." ([collision-detection-algorithms](https://docs.dndkit.com/api-documentation/context-provider/collision-detection-algorithms))
- "**Closest center** … finds the droppable container who's center is closest to the center of the bounding rectangle of the active draggable item" — and it is the recommended one for sortable lists.
- All built-in strategies compare **rectangular bounding boxes**; custom strategies are supported.
- On scroll containers: "For most sortable lists, **we recommend you use a `DragOverlay` if your sortable list is scrollable** or if the contents of the scrollable list are taller than the viewport of the window." ([presets/sortable](https://docs.dndkit.com/presets/sortable))
- `useSortable` "composes the `useDroppable` and `useDraggable` hooks."
- Multi-container dragging is done with "the `onDragOver` callback of `DndContext` to detect when a draggable element is moved over a different container", and empty containers need their own droppable zone.

**Pointer events** ([MDN, Pointer events](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events)) are the third option: one unified model for mouse/touch/pen, which is what you fall back to when you need frame-accurate semantics the DnD libraries do not model.

**Which is least painful for a duration-based, snapping timeline?** [own reasoning, synthesised from the above]

The key structural point: **a timeline drop is not a sort.** Sortable libraries answer "which index does this go between?" — a timeline must answer "**at what time, in seconds, does this land, and how long is it?**" The drop target is a continuous axis, not a list of slots. That mismatch is the whole difficulty.

Ranking:

1. **Pointer events + your own coordinate math — best for the timeline canvas itself.** You need the drop x → `(clientX - trackLeft + scrollLeft) / pxPerSecond` conversion, snapping to a grid and to nearby clip edges, plus a live ghost at the snapped time. No DnD library will do that for you, and fighting one to do it is worse than writing it. Pointer events also give you touch for free, and a pointer-capture model that survives the pointer leaving the element.
2. **dnd-kit — good for the *library panel*** (drag a sound card out of a searchable list) and acceptable for the timeline if you use a custom collision strategy. It gives you keyboard accessibility and sensors that already handle touch. But its AABB collision model is designed for rectangles-in-a-list, so for time-position you will be writing a custom strategy that returns a time — at which point you have written the pointer math anyway.
3. **Native HTML5 DnD — avoid.** No touch, unmodifiable `dataTransfer` after `dragstart` (so you cannot carry live time state), no control over the drag image, and no reliable way to draw a snapping indicator.

**Known pitfalls with DnD inside a scrolling container** (this is where most implementations break) [own reasoning, except where cited]:

- **Auto-scroll during drag.** If the user drags toward the edge of a horizontally-scrolling timeline, the container must scroll, and your drop math must include the updated `scrollLeft` on every frame — otherwise the item lands at a time that drifts as the container scrolls. dnd-kit handles its own auto-scroll for its lists, but a custom pointer implementation must do it manually.
- **`scrollLeft` vs page scroll.** Use `getBoundingClientRect()` on every frame rather than a cached offset; the cached-left bug appears the moment the page scrolls under the timeline.
- **Coordinate space.** Fix a `pxPerSecond` zoom factor and derive everything (clip left, clip width, snap grid, ghost) from it in one place. Mixed px/time math is the usual source of "the sound is 200 ms off".
- **Overlay vs in-flow.** Render the dragged item in an overlay (dnd-kit's `DragOverlay`, or a fixed-position ghost) so the source list does not reflow mid-drag — dnd-kit's docs recommend this specifically for scrollable lists.
- **Touch vs scroll conflict.** On touch, a vertical page scroll that begins on a draggable clip will fight the drag. Gate drag start on `touch-action` / a long-press, or the timeline becomes unscrollable on phones.
- **Drop outside the timeline** must cancel cleanly (restore, no orphan state) — `pointercancel` and `Escape` both need handling.

---

## 2. The common pattern distilled

Across CapCut, Canva, Resolve and TikTok, the same five-stage shape appears, and the differences are only in which stage gets automated away:

1. **Find** — search box *and* curated categories, with the categories named after *intent* not acoustics ("Laugh", "Transition", "Fight", "Horror" in CapCut; "Punchlines", "Reveals", "Fails" in DankMachine's use-case facet).
2. **Preview** — hear before commit (TikTok: "Tap a sound to preview it", then a separate Continue tap). CapCut's SFX doc skips this stage explicitly, which is a real UX fork: *preview-then-commit* (TikTok) vs *commit-and-hear* (CapCut).
3. **Place** — either **one-click at the playhead** (Canva, verified verbatim) or **drag onto the track then nudge** (CapCut, verified verbatim: "Click + next to the effect, **or drag it onto the timeline**. **Move the effect to the moment it belongs to.**"). Nobody requires frame-accurate dropping; everyone allows a coarse place followed by a fine move.
4. **Shape** — a deliberately tiny control set: **trim both edges, fade in/out, volume, delete, move**. CapCut adds speed and pitch. Canva adds slip and "Balance all". Nobody makes a short-form user touch EQ, compression, or sends.
5. **See it** — a **coloured bar in a lane beneath the visuals, with a waveform inside it**, labelled and hoverable, whose trim handles appear on hover (Canva, verified).

Two structural invariants:

- **Audio lives on independent tracks.** An SFX does not get clipped by the video above it; it rings out. The lane is its own axis.
- **The sound outlives the cut.** Every tool that models time (CapCut, Premiere, Resolve, Canva) lets an audio clip span across a video edit point. Only TikTok, which has no timeline, replaces audio wholesale instead.

---

## 3. Minimum viable timeline UX for a web app

The smallest set that does not feel broken. Everything here is either directly modelled on a verified behaviour above or is [own reasoning] about how to implement it.

**The library panel**

- One search field over name + tags. Debounced, 150–250 ms.
- Category chips above the results, *intent-named* — at minimum: Reaction, Transition, Punchline, Impact, Riser, Meme, Notification. (CapCut's own set — Magic / Laugh / Transition / Fight / Horror — is the existence proof that intent categories beat "Sound Effects".)
- Each result: **play/pause button, name, duration as `0:01.4`, a favourite count, and a "+" button.** Duration is the single most important missing field on MyInstants and the most important one to add: a user choosing between a 0.4 s click and a 6 s music sting needs to know which is which *before* placing.
- **Preview must not place.** Clicking the play triangle auditions; clicking "+" places. (TikTok's two-tap model, verified.)
- Keyboard: `/` focuses search, `Space` auditions the focused result, `Enter` places at the playhead.

**The track**

- **Lanes**: video strip on top; 2–3 audio lanes below (sfx / music / voice). Adobe Express's 3-lane cap and Canva's 50-track allowance bracket the range; [own reasoning] 3 is right for short-form — it is enough, and it makes overlap impossible rather than merely discouraged.
- **Rendering a placed clip**: rounded coloured bar, **name label left-aligned**, **duration right-aligned**, **waveform drawn inside the bar**, height ~40–48 px. Trim handles appear on hover at both ends.
- **Playhead** is a vertical line across all lanes with a draggable head, and a visible time readout.
- **Ruler** with adaptive ticks (0.5 s at high zoom, 5 s at low).

**Placement interactions**

- **Click `+` → insert at the playhead** on the first free SFX lane. This is the primary path and should be a single click. (Canva's verified model.)
- **Drag from the library → live ghost at the snapped time**, snapping to: 0.1 s grid, clip edges, and other SFX boundaries. On drop, place at snapped time. (CapCut's verified model.)
- **Drag a placed clip → move.** Clamp to ≥0, allow overlap-free sliding on its lane, and *do not* let it straddle into the video lane.
- **Drag either edge → trim in/out.** Show the trimmed-away region ghosted at 30% opacity during the drag.
- **Avoid the move-vs-trim ambiguity** the way Resolve does: Resolve's verified convention is "click the lower half of a clip to select or move it, the upper half to set an edit point" — a 6 px edge hot-zone plus a body grab is the web equivalent.

**Per-clip controls** — a small popover on selection, five items only:

| Control | Range | Why |
|---|---|---|
| Volume | 0–200%, default 100% | CapCut, Canva, Adobe all expose it |
| Fade in | 0–2 s, default 0 | CapCut, Canva |
| Fade out | 0–2 s, default 0 | CapCut, Canva |
| Trim in / out | edges | universal |
| Delete | — | universal |

Optional sixth, only if cheap: **speed/pitch** (CapCut). Skip EQ, skip compression, skip sends.

**Two behaviours worth adding beyond the minimum**, both cheap and both high-value:

- **Auto-duck music under an SFX** for the SFX's duration (Descript's verified "lower other audio" behaviour). This is what makes meme sounds stop sounding like a mistake.
- **"Trim to fit"**: when a placed SFX extends past the end of the video, offer one click to trim its tail. This is my answer to the unanswered "sound longer than the clip" question, and it is [own reasoning] — CapCut's behaviour here could not be verified.

**Don't build**, for a short-form tool: ripple/rolling/slip/slide edits (Premiere nav proves they exist and proves they are separate professional features), multi-cam, automation lanes, track effects racks.

---

## 4. AI auto-placement guidance with numbers

**What the sources actually say.**

| Source | Number | What it is |
|---|---|---|
| Zella ([link](https://zellahq.com/blog/how-many-sound-effects-is-too-many-in-a-video/)) | "one cut sound every **four to five seconds**, maximum" | hard ceiling on density |
| Zella | "For a sixty second short, that ceiling is about **twelve to fifteen** sounds" | ceiling restated |
| Zella | "Most over-sauced videos have **forty**" | anti-pattern |
| Zella | "three to six sounds in a short" — opening cut, section breaks, the one reveal | recommended practice |
| Zella | "After about **fifteen seconds** of regular transients, the sounds stop registering" | fatigue onset |
| Zella | video length ÷ 5 = max count | self-test formula |
| Zella | "never two on adjacent cuts"; in a six-cut rapid sequence, sound the **first and last**, middle four silent | adjacency rule |
| CapCut ([link](https://www.capcut.com/resource/how-to-add-or-replace-voiceovers-music-and-sound-effects-in-capcut)) | **2** sound effects in a 45-second worked example (a pot tap at 0:08, a soil pour at 0:20) | one vendor's own demo density |

That CapCut example is quietly the most useful data point in this whole document: the vendor's own showcase for "how to add sound effects" uses **two** in 45 seconds — roughly **one every 22 seconds**, far below even Zella's recommended 3–6.

**Where they should land relative to the punchline.** From the Zella taxonomy, which is the only sourced statement on this:

- **Riser → before.** "The seconds BEFORE a cut, building into it." Explicitly: "**It goes before the cut, not on it.**"
- **Impact → on.** On "a hard cut you want to land, a title appearing, a reveal."
- **Whoosh → on motion**, i.e. a slide, whip or zoom, not on a static beat.

[own reasoning] Translate to a punchline: the punchline is an *impact* event, so the impact sound sits **on the punchline frame**, and if you want a riser, it starts ~0.5–1.0 s before it and resolves into it. Never put both a riser and an impact within 0.3 s of each other — that is the "two on adjacent cuts" failure in miniature.

**Recommended policy for a 15–60 s vertical short** — [own reasoning], anchored to the sourced bounds above and deliberately *below* Zella's ceiling:

| Duration | Auto-added | Absolute max | Spacing floor |
|---|---|---|---|
| 15 s | **2–3** | 4 | ≥ 4 s |
| 30 s | **3–5** | 6 | ≥ 5 s |
| 60 s | **5–7** | 10 | ≥ 6 s |

Derivation: take Zella's self-test (length ÷ 5) and then *halve it* for an automatic system, because the sourced material only supports ÷5 as a **ceiling** ("the most a video can carry"), Zella's own recommended practice is "three to six", and CapCut's own demo sits at 2-in-45 s. Concretely: `max = clamp(round(duration / 8), 2, 8)`.

**Guard rails for the placer**, each traceable to a sourced rule or a direct consequence of one:

1. **Never two sounds within 4 s of each other** — Zella: "Below roughly four seconds of separation … a pattern is background."
2. **Never two on adjacent cuts** — Zella, verbatim. If cuts are < 1.5 s apart, sound the first and the last only.
3. **One riser per section.** [own reasoning] Risers are the most fatiguing family because they are long and tonal; cap them at 1 per ~15 s.
4. **Keep 1.0–1.5 s of silence immediately before the punchline** and let the impact land on it. [own reasoning] Contrast is the mechanism the whole technique runs on; a sound *into* the punchline steals the impact of the impact.
5. **First sound inside the first 2 s.** [own reasoning] Zella's "opening cut" rule exists because the first two seconds are the retention decision.
6. **Duck music to ~30–40% under each SFX** for its duration (Descript's verified ducking behaviour).
7. **Require confidence > threshold, else place nothing.** [own reasoning] The failure mode of an auto-placer is not a missing whoosh, it is a whoosh on a sincere moment.

**On claimed precision:** no vendor in this research publishes a precision or recall figure for automatic SFX placement. Descript's AI generates sounds on request; Opus Clip, Klap, Veed, CapCut and Adobe Podcast publish no auto-SFX feature doc that I could reach. **Could not verify** any precision claim, because none was found.

---

## 5. What to copy / what to skip

**Copy**

- **One-click insert at the playhead** as the primary path (Canva, verified: "it'll go where your playhead (timestamp) is on the timeline"). It is exact by construction and removes the whole class of "I dropped it 400 ms early" bugs.
- **Drag-to-timeline as the secondary path, with nudge-after-drop** (CapCut, verified: "Click + next to the effect, or drag it onto the timeline. Move the effect to the moment it belongs to.").
- **Intent-named categories, not acoustic ones** — "Laugh / Transition / Fight / Horror" (CapCut), "Punchlines / Reveals / Fails" (DankMachine). Users search for the moment, not the sound.
- **Preview before place, as two distinct taps** (TikTok, verified: "Tap a sound to preview it" … "tap the Continue ✓ button to confirm").
- **A coloured bar with a waveform inside, in its own lane, with trim handles on hover** (Canva, verified: "a colored bar below the page thumbnails"; "Drag the audio waves into the colored section of the sound bar"; "Hover your mouse cursor over it. Trim handles will appear").
- **Slip** — let a user drag *inside* the bar to choose which part of a longer sound plays (Canva's verified "Slip"). Cheapest possible answer to "the sound is too long".
- **A hard lane cap** (Adobe Express's ~3 tracks per its snippet) rather than an unbounded stack.
- **Auto-duck other audio under the SFX** (Descript, verified).
- **Explicit rank + velocity signals** in the library — "#6 in Memes", "Rising right now — Blowing up in the last few hours" (DankMachine, verified). Rank within category, not lifetime play counts.
- **Duration on every library card.** Nobody in the meme-sound set does this well and every one of them should.
- **A use-case facet axis alongside categories** (DankMachine's "Sounds for every moment"). It doubles as the vocabulary for an AI placer.
- **Resolve's two-hit-zone clip** ("lower half to move, upper half to set an edit point") as the solution to move-vs-trim ambiguity.

**Skip**

- **Native HTML5 drag-and-drop.** No touch support in the API, `dataTransfer` frozen after `dragstart`, no controllable drag image. Wrong tool for a timeline on phones.
- **A dnd-kit sortable for the timeline axis.** Its collision model answers "which slot", not "what time". Use it at most for the library panel.
- **Resolve/Premiere trim depth**: ripple, rolling, slip, slide, J/L cuts, Trim mode. Verified to exist as their own nav entries — and verified to be a different product's feature set.
- **Raw lifetime play counts as the popularity signal.** "12,035,525 views" tells you nothing about whether the sound is funny today.
- **Zella's 12–15-per-minute ceiling as a target.** It is explicitly a maximum-tolerance figure; the same source's recommended practice is 3–6.
- **A timeline at all** if the product is single-sound-per-post like TikTok, where the verified model is "tap anywhere on the video to add the sound" and new music *replaces* the old. Pick one model; a half-timeline is worse than either.
- **Auto-placement without a confidence floor.** No vendor publishes precision numbers, which means there is no published evidence anyone has this reliable — so gate it and let silence be the default.

---

## 6. Could not verify (explicit gaps)

1. **CapCut: how a placed SFX is rendered** (waveform? label? duration?) and **what happens when the SFX is longer than the video clip**. All CapCut help-centre URLs are dead (404 / HTTP 451 / DNS failure). Third-party blogs claim mobile uses "Audio → Sound FX"; unconfirmed.
2. **CapCut: whether a search result auditions on click**, or only on placement.
3. **Premiere Pro: any quotable body text.** `helpx.adobe.com` renders client-side and returned navigation only; the `.../trim-clips` page 404s directly. The Premiere section rests on verified navigation labels, not instructions.
4. **Adobe Express: the exact track cap (3?) and whether insertion is playhead-based or drag-based.** `helpx.adobe.com` bodies unreadable; `adobe.com/express/feature/*` returns Akamai "Access Denied". Page existence and search snippets only.
5. **101soundboards: what its two bare board counters (21,474 / 189,068) measure** — plays, favourites, or something else. Unlabelled in the extracted text.
6. **Any AI tool's auto-SFX precision/recall.** Opus Clip's auto-SFX URL 404s and its feature list has no SFX item; Klap, Veed, CapCut auto, and Adobe Podcast publish no reachable auto-placement doc. **No precision figure exists in any source I found.**
7. **dnd-kit's `restrictToHorizontalAxis` modifier** — the modifiers doc pages returned empty/422, so the API could not be citation-verified (it exists in the library, but I am not citing it as sourced here).
8. **TikTok's per-sound metadata** (duration/tags on a sound page) — the help page documents the *flow*, not the card fields.

---

## Appendix — primary URLs used

**CapCut**
- https://www.capcut.com/resource/how-to-add-or-replace-voiceovers-music-and-sound-effects-in-capcut

**Premiere Pro**
- https://helpx.adobe.com/premiere/desktop/add-audio-effects/apply-audio-effects/audio-effects-library.html *(navigation verified; body client-rendered)*

**DaVinci Resolve**
- https://www.blackmagicdesign.com/products/davinciresolve/editor
- https://www.blackmagicdesign.com/products/davinciresolve/fairlight

**Canva**
- https://www.canva.com/help/stock-music/
- https://www.canva.com/help/trim-audio-and-adjust-volume/

**Adobe Express**
- https://helpx.adobe.com/express/web/audio-and-animation/audio.html *(exists; body unreadable)*
- https://helpx.adobe.com/express/web/audio-and-animation/sound-effects.html *(exists; body unreadable)*
- https://www.adobe.com/express/feature/audio/sound-effects *(Akamai "Access Denied")*

**Meme sound libraries**
- https://www.myinstants.com/en/search/?name=boom
- https://www.myinstants.com/en/instant/vine-boom-sound-70972/
- https://www.101soundboards.com/
- https://www.101soundboards.com/sounds/trending
- https://www.dankmachine.com/
- https://www.tiktok.com/support/faq_detail?id=7581821548110125580&category=web_account

**AI / auto-placement**
- https://help.descript.com/generative-media/generate-audio.md
- https://help.descript.com/llms.txt
- https://www.opus.pro/blog/auto-sound-effects *(404 — absence of the feature page is the finding)*
- https://www.klap.app/
- https://zellahq.com/blog/how-many-sound-effects-is-too-many-in-a-video/
- https://zellahq.com/blog/how-to-add-sound-effects-to-a-video-automatically/

**Web drag-and-drop**
- https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API
- https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events
- https://docs.dndkit.com/presets/sortable
- https://docs.dndkit.com/api-documentation/context-provider/collision-detection-algorithms
