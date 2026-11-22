# 18 · Clipper UI reference

How modern AI video-clipping web apps arrange their UI, what features they expose, and what PeakCut should borrow. Written as build input for `peakcut/web/index.html` + the FastAPI backend in `peakcut/studio/`.

Evidence rules: every external claim below came from pages fetched this session (landing pages + the Opus help center). gta6-clipper-main is covered from its code with `path:line` citations. Where only a marketing page was fetchable, layout claims are limited to what that page shows and the limitation is stated.

Sources fetched this session:

- `https://www.opus.pro/` (landing, 200)
- `https://help.opus.pro/en/` (help-center index, returned full docs nav)
- `https://help.opus.pro/docs/article/introduction-to-opusclip` (workflow doc, 200)
- `https://klap.app/` (landing, 200)
- `https://vizard.ai/` (landing, 200)
- `https://www.submagic.co/` (landing, 200; `submagic.com` is parked "domain for sale")
- `https://www.capcut.com/` (landing, 200)
- `https://www.descript.com/` (landing, 200)

Local sources:

- gta6-clipper-main: `gta6-clipper-main/app.html` (868 lines, single-file UI), `gta6-clipper-main/app.py` (948 lines, stdlib http.server backend).
- PeakCut: `peakcut/web/index.html` (2961 lines), `peakcut/studio/server.py`, `peakcut/studio/api_*.py`.

---

## 1. Layout and navigation

### 1.1 gta6-clipper-main (primary source, from code)

Single-page app, one HTML file. Dark warm theme (`--bg:#16140F`, cream text `--t:#FFF4E6`), neo-brutal style: 2px borders, hard offset shadows (`app.html:4`, `app.html:10`). 44px minimum touch targets (`app.html:18`), visible kbd chips on nav buttons (`app.html:50`).

Skeleton (`app.html:44-54`):

- `#app` = flex row: fixed left icon rail `#nav` (88px, sticky) + main column `#col`.
- Rail: logo, then one button per view with icon + label + kbd number; active view gets `.on` (`app.html:45-49`, `119-125`).
- Main column: per-view header `<h1>` + `<small>` subtitle + autopilot status pill `#ap` on the right (`app.html:126`), a day-filter chip row `#runs` (`app.html:127`), then the view body `#main`.
- Fixed bottom toast (`app.html:128`).
- Mobile ≤640px: the rail becomes a 64px bottom bar (`app.html:84-86`). RTL layout supported for Arabic (`app.html:107`).

Nav order (`app.html:119-125`): Home (1), Shorts/library (2), Streamers (3), Make (4, plus icon), Schedule (5), Brand (6); spacer; utility buttons: "Update ready" (hidden until an update exists, `app.html:97`), "Auto-post" → Blotato, "Propose a change" (GitHub proposal dialog), Settings (gear dialog).

Views, in flow order:

1. **Home** — one decision per visit. If a job is running: "Making Shorts" stat + "Show progress". If first run: big CTA "Make my day" with a 3-step explainer (find → cut → review) and a paste-link row. Otherwise a contextual row: review N first, else schedule N, else make new (`app.html:782-799`). Stat tiles for review/approved/scheduled/published counts; a compact hunt card (max 3 live streams); a confirm ask before any AI run: "10 Shorts, full permissions, spread across the day, nothing is posted" (`app.html:782-799`).
2. **Shorts (library)** — grouped By day or By stream; filter pills with live counts (All / Pass / Warn / Fail / Approved / Scheduled / Edited / Not checked), moment-type select with counts, search across titles/files/hashtags/channel, fold/unfold groups, "Review N" button per group, "Copy all post text" per group, max 120 cards + "Show older days" (`app.html:240-267`). Cards are 9:16 covers with overlay chips (QC result, review state, schedule time, version count), length chip, 2-line title, time/run label, moment-type chip (`app.html:245-248`).
3. **Review player** — a full-screen day player that walks one day's shorts: review progress bar ("x of N reviewed · y approved"), video with ‹ › arrows, big Approve (A) / Reject (X) buttons, "Schedule now" (S) with datetime pre-filled to the next free slot, "Ask <AI> to change" (E), auto-advance after each decision, keyboard: arrows, A/X/S/E, space, Esc (`app.html:272-293`, keydown handler `app.html:504`).
4. **One Short drawer** — full-height overlay next to the rail (`app.html:77-82`). Left sticky column: version selector (Original + V1..Vn with QC labels), the video, a moment timeline strip, Open file / Export zip / Change the look / YouTube stats buttons. Right stack: "Ask <AI> to change it" panel (free-text note + quick chips like "End 2 s earlier", "Bigger captions", "Add meme sound"; job status with spinner + elapsed mm:ss + last log line + Show log; Ctrl+Enter submits), "What changed" version history (each row: instruction, result, Try again, click to show that version), and a tabbed panel Post text | Look | YouTube | Schedule & send (`app.html:296-351`).
5. **Streamers** — hunt panel with one master watch toggle; per-streamer rows: platform chip, clip-permission rule chip ("Clipping allowed / Has clip tips / No clipping / Rules unknown", `app.html:604-607`), live/offline chip, "n Shorts made", "Watch live" checkbox, "Past" expander listing VODs each with its own "Make Shorts" button (`app.html:760-780`).
6. **Make** — one form: source (link or "Newest GTA 6" pill), count stepper (default 10, max 30), optional time window, "Make Shorts" + "Preview command", a confirm ask, then a spinner with elapsed time; jobs list below; right side "What happens" 5-step explainer ("Nothing is posted.") (`app.html:440-454`).
7. **Schedule** — 7-day × hour grid (06:00–23:00), week navigation, HTML5 drag-and-drop of shorts onto slots, "Spread unscheduled N from [datetime] every [90] min between 08:00 and 23:00", a "N approved, not scheduled" highlight panel with auto-schedule, a ghost "Suggested plan" at peak hours (12:00/18:00/21:00) you can accept, CSV export, and a Blotato send preview that never sends by itself (`app.html:377-395`).
8. **Brand** — global brand.json editor: caption colors/font/style/position, hook text + box colors, watermark (handle or PNG, position, opacity, size), theme select, ending card, clean-up toggles; sticky 9:16 mock preview that restyles the sample caption on every input (`app.html:456-475`).
9. **Autopilot** — page + a global header pill ("Autopilot running now / Autopilot on · mon wed fri 09:00 / Autopilot off"): day checkboxes, time, count, source select, auto-schedule-after-run options, "Preview command" showing the exact OS scheduled-task command + the AI prompt, Turn on/off with confirmations, "Nothing is ever posted automatically" (`app.html:511-530`).
10. **Settings** (dialog) — language (8 languages, RTL), updates (version, check now, auto-check every 5h), AI pick-mode (smart/deep/free + live mode + hourly cap, `app.html:858-865`), AI provider list with custom-command escape hatch and "Reply with the single word OK" test, connections with per-platform test, YouTube settings, Blotato key stored locally (`app.html:129-131`).
11. **Onboarding** (first run dialog) — 3 steps: language grid → streamer checkboxes (pre-checked suggestions, can't continue with 0) → AI provider choice with a "none" fallback ("picks come from chat spikes and loudness… weaker, no AI titles") (`app.html:821-845`).

Backend shape (`app.py`): stdlib `http.server`, GET routes for runs/shorts/library/schedule/jobs/media (`/m` with HTTP Range streaming, `app.py:717-731`), POST routes guarded by an `X-App` token (`app.py:786`) and localhost origin checks (`app.py:707-709`). Notable endpoints: `/api/shorts` returns everything a view needs in one payload (shorts + styles + layouts + formats + style_info + memes + providers, `app.py:732-783`); `/api/rerender` re-renders one Short with new look settings (`app.py:836-844`); `/api/edit` makes a NEW version, never touching the original (`app.py:845-856`); `/api/newrun` enforces per-streamer clip-permission gates with a 403 `{"clip":"no"}` (`app.py:857-862`, `clip_block` at `app.py:634`); `/api/export` zips mp4 + post text + cover (`app.py:783` area); `/api/schedule.csv` (`app.py:783` area); `/api/propose` sends a change proposal to GitHub (`app.py:657`).

### 1.2 OpusClip

From the help center index + "Introduction to OpusClip" (fetched 200) and the landing page (fetched 200).

Arrangement (as documented by their own help flow, not from screenshots of the app):

- Setup first: Brand Kit, social accounts, team workspace ("Getting Started", help article).
- Main flow: paste a link or upload → optional "Recipe" (saved editing setup) → customize (logo/fonts, aspect ratio, clip length, specific timeframe, prompts) → "Get clips with one click!" → results page shows all clips → per-clip editor → save as projects → publish/schedule → optional XML export to Premiere/Resolve (help article "Introduction to OpusClip").
- Feature nav groups documented in their help index: ClipAnything (multimodal clipping), editing (Adjust Layout, Manual Reframe, Subject Tracking, captions, AI Emojis/Keywords, Trim/Extend, Text Overlays, Transitions, Speech Cleanup, B-roll, AI Voiceover, Intro/Outro Cards, Music, keyboard shortcuts, timeline scene rearranging, censor words, Snap Editing, Auto headline, Viral Hook, motion graphics, auto color correction, duplicate, upscale, clone & dubbing, Auto SFX, Eye Contact), management (projects, collections, collaborators, bulk download, 4K, cloud storage), publishing (social accounts, scheduler, custom thumbnail, bulk scheduler, per-platform connect guides), Virality Score, Export to XML, Team Workspace.
- Landing page adds: AI Producer, Animated captions, AI Reframe, ClipAnything, Social scheduler ("schedule a month's posts to all platforms in 10 minutes"), Brand template, AI B-Roll, Export to XML, Team workspace, Editor, Thumbnail generator, Enhance speech, AI video dubbing, API + MCP.

App-internal layout (sidebar vs topbar) could not be verified from fetched pages — only their documented workflow and feature set. Included above is what the fetched pages support.

### 1.3 Klap

From `klap.app` (fetched 200). Marketing page only.

Documented feature set: upload or paste a YouTube link → AI picks topics and reframes ("Auto Reframing… focus on the most important subject") → designed captions + a recommended post caption → clips scored for "viral potential" → customize fonts/colors/logos/framing → Publish & Schedule to TikTok, YouTube, Instagram, LinkedIn, Facebook. "AI Reframe 2" applies scene-aware layouts (Split Screen, Screencasts, Gaming). Pricing FAQ: free preview of 1 video; paid plans unlock download/posting; 99+ transcription languages. Rule of thumb stated on page: a 1-minute video ≈ 5 clips.

Internal layout could not be verified (login-gated; marketing page only).

### 1.4 Vizard

From `vizard.ai` (fetched 200). Marketing page only.

Documented feature set: upload → transcribe + cut speakers → "Get AI clips" one click → clips designed per platform; editor: **Edit by text** (delete transcript text to trim), **Caption translation** (100+ languages), **Change ratio** (one-click resize), **Timeline editing** ("seconds-level" fine-tuning), **Brand template**, **Link share**; publish by download, share-as-link, or direct publish. 22+ "Agent" templates (product ad, talking head, podcast clips, localize…). Team workspace with client previews.

Internal layout could not be verified (login-gated; marketing page only).

### 1.5 Submagic

From `submagic.co` (fetched 200). `submagic.com` is parked ("domain for sale") — the product lives on `.co`. Marketing page only.

Documented feature set: 4-step flow (pick a viral-style template → upload raw video → AI adds captions/cuts/B-roll/zooms/music → open editor and adjust any element from a control panel). Editor control panel shows: Style (template names Paprika/Velvet/Cinnabar/Matinee), Highlight color, Caption size, Music tracks with mood + duration (Upbeat Pop / Lo-fi Chill / Cinematic Rise). Feature list: AI Captions (118 languages, 99% accuracy claim), Magic Clips (auto repurpose), AI Actors, Studio B-Roll, Auto-Zoom, AI Eye Contact, Video Translator, Images & GIFs, Transitions, Sound Effects, Background Music, Auto Description, Publishing Automation ("Pick a date, choose platforms, and publish directly from the editor"), Video Editing API, team workspace.

Internal layout could not be verified (marketing page only).

### 1.6 CapCut Web

From `capcut.com` (fetched 200). Marketing page only.

Documented feature set: timeline video editor ("Cut, arrange, and polish video on a timeline"), auto captions + caption templates, text-to-speech, voice enhancement/noise removal, video converter/trimmer/background remover, AI image/design tools, meme generator, template library, "Video Studio" (chat-driven video generation). Export HD without watermark claim.

The actual web editor is login-gated; its panel layout could not be verified from fetched pages.

### 1.7 Descript

From `descript.com` (fetched 200). Marketing page only.

Documented workflow (their own 5-step model): Record → Edit (edit the transcript text to edit the video; "The timeline's there if you need it") → Refine (Studio Sound, filler-word removal, retake removal, eye contact, regenerating audio/video) → Share (link + comments, captions, thumbnail, YouTube description, export) → Multiply (translate to dozens of languages, reformat per platform, Create Clips). Underlord = AI co-editor assistant. Feature nav: video editing, podcasting (multitrack), screen recording, Rooms, templates, captions, AI speech, transcription, AI avatars, brand studio, API + MCP.

Internal layout could not be verified (marketing page only).

### 1.8 Pattern summary (fetched evidence only)

- Everyone's funnel is the same three screens: a **paste/upload screen**, a **results grid of clips**, a **per-clip editor**. gta6-clipper and PeakCut already follow it.
- Externals converge on: caption style presets, reframe/aspect control, auto-zoom/subject tracking, hook/title text, template/brand kit, scheduler + direct publishing, a virality score, and translate/dub.
- gta6-clipper differs from all of them in two ways that matter for PeakCut: it is **local-first** (nothing is posted without explicit confirmations) and it has a **review-first workflow** (approve → schedule → post) instead of post-everything autopilot.

---

## 2. Feature inventory: gta6-clipper vs PeakCut

PeakCut baseline (from code, `peakcut/web/index.html` + `peakcut/studio/`): 35 caption styles (`api_style.py:44`), 8 export formats (`api_style.py:73`), 13 meme moods (`api_sound.py:55`), chat-spike moment picking (`studio/live.py`), vision tagging (`studio/vision.py`), music beds (`studio/music.py`), translation (`api_text.py:111-242`), brand kit page (`index.html:2381-2398`, `api_brand.py`), autopilot endpoints (`api_auto.py:97-161`), watch list (`api_preview.py:134-157`, UI `index.html:2109-2139`), clip rules check (`api_preview.py:46`, UI `index.html:2104-2107`), YouTube stats (`api_stats.py:71-106`), upload YouTube/Instagram/TikTok via OAuth + Zernio (`server.py:1529-1539`, `studio/zernio.py`), transcription settings with Logfare cloud or local (`server.py:1381-1490`), tools page (`index.html:2100-2123`), live activity feed (creator Activity tab, `index.html:1296-1297`).

| # | gta6-clipper feature | Evidence | PeakCut today |
|---|---|---|---|
| 1 | Left icon rail with numbered views + kbd chips | `app.html:45-50,119-125` | Left sidebar exists (`index.html:829-835`) but no kbd numbers/shortcuts |
| 2 | One-click "Make my day" (newest videos → 10 shorts → auto-spread) | `app.html:477-482,782-799` | Composer exists (URL + upload, `index.html:1383-1385`); no one-CTA preset |
| 3 | Library filter pills with live counts (QC/approved/scheduled/edited) | `app.html:242,259` | Missing; clips listed per job with statuses but no filter row |
| 4 | Search across titles/files/hashtags/channel | `app.html:244` | Missing |
| 5 | By-day / By-stream grouping + fold + "Show older days" cap 120 | `app.html:250-256` | Grouped by job/creator only |
| 6 | QC pass/warn/fail chips + per-clip reasons | `app.html:23-25`, `qc.py` | Score + words/reaction judges badge + reason on clip card (`index.html:1703-1721`, `index.html:2421-2422`) — equivalent info, no pass/warn/fail triage |
| 7 | Review player: approve/reject/schedule/ask, keyboard, auto-advance, progress bar | `app.html:272-293` | Missing entirely (no approve/reject concept) |
| 8 | Version selector Original/V1..Vn per clip | `app.html:296-351` | Single render per clip + `version` counter (`index.html:2414`); no version list |
| 9 | "What changed" history with Try again | `app.html:365-372` | Missing |
| 10 | AI ask-in-words edit with quick chips + job progress | `app.html:303-306` | Has it: note input + Apply (`index.html:2434-2437`), `api_text.py:195`; no quick chips, no per-job log tail UI |
| 11 | Timeline strip of moments, color-coded by type, clickable to re-cut | `app.html:809-819` | Missing |
| 12 | Caption style grid with live-styled sample text (CSS from style_info) | `app.html:72,225,315`, `app.py:68` | Style `<select>` only (`index.html:2426`); `/api/style/preview` endpoint exists (`api_style.py:183`) but is not used for a picker |
| 13 | Format radio grid with "when to use" descriptions | `app.html:312` | Formats exist (`api_style.py:73`, `formats/plan` at `api_style.py:83`); no in-UI format picker grid |
| 14 | Aspect extras: also export 4:5 / 1:1, layout select, flip | `app.html:313-314` | Layout select exists (`index.html:2427`); multi-aspect export handled by formats/plan API, not exposed per-clip |
| 15 | Meme sound select per clip | `app.html:314` | Moods API + prime (`api_sound.py:55-96`); no per-clip mood picker in UI |
| 16 | Caption position + size + watermark controls per clip | `app.html:316-317` | In Brand page (`index.html:2178+`); not per-clip |
| 17 | Theme swatches with 5-color strips | `app.html:318,339-340` | Brand themes API (`api_brand.py:76`); UI shows theme select on brand page |
| 18 | Brand editor with sticky live 9:16 mock preview | `app.html:456-475` | Brand page exists (`index.html:2381-2398`) but no live mock preview; demo videos exist (`web/brand/demo-*.mp4`) |
| 19 | Post text tab: title/hashtags/credit + AI title ideas + preview | `app.html:308,332-334` | Title/description inputs + AI note (`index.html:2430-2437`); no separate post-text tab or idea buttons |
| 20 | YouTube stats panel per short: views vs your median, kept-at-3s, why-not-doing-well, title/hook ideas | `app.html:142-178` | Stats API (`api_stats.py:71-106`) surfaced only via Tools "Read the numbers" (`index.html:2121-2122`); no per-clip panel, no median comparison UI |
| 21 | Schedule week grid + drag-drop + spread + ghost plan + CSV | `app.html:377-406` | Schedule exists as a paste-able cron command via `/api/schedule/preview` (`index.html:2115-2122`, `api_preview.py:173`); posting queue table on overview (`index.html:1964-1967`) |
| 22 | Approved → auto-schedule panel with live slot preview + send | `app.html:408-434` | Autopost per creator toggle with confirm (`index.html:1886,2553`) + queue cancel/retry (`index.html:1967`) |
| 23 | Publish via Blotato with preview-then-confirm JSON | `app.html:321-323,422-434`, `app.py:516-520` | Direct OAuth per platform + Post now / Add to queue (`index.html:2446-2450`) — PeakCut's model is stronger |
| 24 | Connections page with per-platform test | `app.html:436-438` | Connected apps settings tab + OAuth (`index.html:2025`, `server.py:1529-1539`) |
| 25 | Watch list / live hunt with clip-permission rules gate (403) | `app.html:760-780`, `app.py:625-652` | Watch list + rules in Tools (`index.html:2104-2139`, `api_preview.py:46-157`); creator-level "Record this stream" (`index.html:1133`); no per-streamer permission gate |
| 26 | Onboarding: language → streamers → AI provider | `app.html:821-845` | Interactive tour instead (`index.html:962-964`); creator setup tab |
| 27 | 8-language UI + RTL | `app.html:532+` | UI is English-only (caption translation exists, `api_text.py:111-242`) |
| 28 | Update check + "Update ready" rail button + apply | `app.html:97,847-853` | Update banner + Later/hide (`index.html:1309-1312`) |
| 29 | "Propose a change" → GitHub | `app.html:125`, `app.py:657` | Feedback form (`server.py:1114`) + Send feedback menu item (`index.html:1186`) |
| 30 | Keyboard shortcuts (arrows, A/X/S/E, space, Esc) | `app.html:272-293,504` | Missing |
| 31 | Jobs: progress % + stage string + adaptive polling | n/a (PeakCut's own) | PeakCut HAS this and gta6 does not: `index.html:1759`, poll loop `index.html:2502-2507` |
| 32 | Peek: still frames before spending a render | n/a (PeakCut's own) | PeakCut HAS this and gta6 does not: `index.html:2442-2445`, `api_preview.py:63-119` |
| 33 | Per-clip render endpoint | `app.py:449` | Has it: `server.py:966` |
| 34 | Export zip of clip + post text + cover | `app.py` `/api/export` | Has zip of clips: `server.py:1019` |
| 35 | Media HTTP Range streaming + path containment | `app.py:717-731,772-773` | Has media route: `server.py:1061` |
| 36 | Live recording with "Clip last 30s/60s" quick buttons | gta6 has watch-mode clipping | PeakCut HAS Clip last 30s/60s + Stop (`index.html:1732-1734`), live record/stop/clip endpoints (`server.py:1239-1283`) |
| 37 | AI usage transparency (what the AI spent) | gta6: none in UI | PeakCut HAS a whole Usage page (`index.html:1996-2013`) |
| 38 | Multi-account OAuth posting + posting queue | gta6: Blotato only | PeakCut HAS accounts + queue + autopost + earnings table (`index.html:1961-1967`) |

Summary: PeakCut already owns the pipeline features (styles, formats, moods, stats, posting, usage). What it lacks is almost entirely **workflow UI**: review flow, filters/search, live style preview, version history, per-clip panels for stats/mood/format, schedule grid, keyboard support, and the autopilot page its backend already serves.

---

## 3. Editor UX patterns

### 3.1 What gta6-clipper does

- **Clip detail is a drawer, not a page.** The library stays visible; the drawer overlays from the rail edge (`app.html:77-82`). Two columns: sticky media left, scrolling actions right.
- **Version-first mindset.** Every AI change or look change creates a new version; the original is immutable; the version selector labels each with QC state; history rows let you jump back and "Try again" a failed instruction (`app.html:296-372`, `app.py:845-856`).
- **Ask-in-words editing.** One textarea + six quick chips + Ctrl+Enter. Disabled with an explainer when prerequisites are missing (no pick file / no AI) instead of hiding (`app.html:303-306`).
- **Caption picker with live preview.** `/api/shorts` ships `style_info` (font, stroke, colors per style parsed from clip.py, `app.py:68`); the client injects `@font-face` and renders each style's sample text so the grid *is* the preview (`app.html:72,225,315`).
- **Look controls grouped as one "Look" tab**: format grid → aspect checkboxes → layout/flip/meme → caption grid → position/size → watermark → theme → one "Make a version with this look" button that posts every field at once (`app.html:312-320`).
- **Hook/title editing is inline post-text work**, with AI idea buttons that apply on click (`app.html:332-334`).
- **Timeline strip** with color-coded moment markers; clicking a marker re-opens that short or offers a 1-clip re-cut of that window (`app.html:809-819`).
- **Re-render always shows its cost**: "Takes a few minutes · the original is kept · nothing is posted" plus a live log tail with restart detection ("Interrupted: the app was restarted.") (`app.html:303-306,358-375`).

### 3.2 What PeakCut already does (and should keep)

- Clip dialog with media stage left + one scrolling panel right (`index.html:2409-2458`) — same shape as gta6's drawer.
- Score/judges badge + pick reason at the top of the panel (`index.html:2421-2422`).
- Hook input, captions toggle, style + layout selects, start/end seconds (`index.html:2424-2429`).
- "Save and re-make clip" (`index.html:2433`), AI note apply (`index.html:2434-2437`), translate (`index.html:2438-2441`), peek stills before render (`index.html:2442-2445`), post accounts + Post now / Add to queue (`index.html:2446-2450`).
- Adaptive polling keeps the dialog's media fresh by `status+version` signature (`index.html:2455-2456,2469-2507`).

### 3.3 Gaps vs gta6

1. Style picker is a bare `<select>` — no visual samples, though `/api/style/preview` already exists (`api_style.py:183`).
2. No version history: "Save and re-make" replaces; gta6 appends and lets you compare.
3. No timeline strip, no moment context on the clip dialog.
4. No YouTube-stats panel or title-idea buttons inside the clip dialog (stats are Tools-page only).
5. No mood/format/aspect controls on the clip dialog (they exist in the backend).

---

## 4. Live progress visualization

### 4.1 gta6-clipper patterns

- **Stage-list explainer instead of percent bars** on the Make page: 5 numbered steps (find → transcribe → pick → render → QC) with "Nothing is posted" reassurance (`app.html:440-454`).
- **Elapsed-time spinner**: "Run in progress · mm:ss" ticking every second (`app.html:440-454`).
- **Job banner**: while any newrun is active the app shows "A run is making Shorts now" + "Show progress" on every view; on completion a toast + auto-reload (`app.html:263-265`).
- **Log tail as the detail view**: job polling prints the last 60 log lines + `[status]`, with restart detection (`app.html:374-375`, `app.py:408-413` JOBS dict).
- **Edit-jobs show**: status stat + spinner + elapsed + last log line + expandable full log (`app.html:303-306`).
- **Stream-watched feedback** is qualitative: per-streamer "Live now / Offline", "n Shorts made", Watch live toggle (`app.html:604-607`, `760-780`). No numeric "watched %" display exists.

### 4.2 PeakCut patterns today

- Numeric progress: `<div class="bar"><i style="width:N%"></i>` + "stage · N%" per job (`index.html:1759`); stage string also in job header (`index.html:1731`).
- Clip-level statuses: queued / rendering ("Making this clip…" / "Waiting its turn…") / done / error, reflected live in the open dialog (`index.html:2414-2417`).
- Adaptive polling: 2s while work is active, 4s idle, 20s hidden tab; instant refetch on tab focus (`index.html:2502-2507`).
- Sidebar "N working" badge on All videos (`index.html:1268-1269`); per-creator "Rec" / "Live" tags (`index.html:1271-1273`).
- Live job card: "Clip last 30s / 60s / Stop" plus "recording, <stage>" line (`index.html:1731-1734`).
- Activity feed per creator (tab with count, `index.html:1296-1297`) + notification bell with unread count (`index.html:1280-1282`).

### 4.3 What's missing

- A **stage checklist** (download → transcribe → pick → render) rendered as steps with done/active/pending states. PeakCut has the stage string but renders it as text, not a step list; gta6 renders steps but no percent. Combine both.
- **Per-clip ETA / count done** ("4 of 10 clips") — neither app shows it; trivial from existing job data.
- A **global "something is running" pill** in the topbar (gta6 uses a home banner + rail badge; PeakCut's badge is only on the library item).
- **Stream-watched %**: for live jobs PeakCut could show "watching for 1h 12m · 6 spikes · 4 clips" from live.py data; neither product shows this today.

---

## 5. Recommendations for PeakCut

Keep the user's constraint in view: PeakCut stays a simple local-first app. Borrow gta6's *workflow*, not the industry's feature sprawl.

### (a) UI arrangement changes

1. **Add the review step before posting.** gta6's whole advantage is approve-then-schedule. PeakCut posts straight from the card ("Post" button, `index.html:1715`) or via autopost. Insert a per-creator "Review (n)" queue — reuse the clip dialog in a player-like loop with Approve / Reject / Schedule-now / Post-now and auto-advance.
2. **Give All videos a filter row.** Status pills with counts (Done / Rendering / Failed / Queued) + a search box over hook/title/source. This is gta6's `filter pills` pattern (`app.html:242-259`) mapped to PeakCut's job model.
3. **Promote peek into the job card.** Show 3 peek stills per clip on the card grid after picking, before render completes — it sells the "look before you spend a minute rendering" idea PeakCut already built (`index.html:2442-2445`).
4. **Add a global status pill** to the topbar when any job/live-job is active ("Making clips · 2 jobs · Show progress") so the running state follows you across views (gta6: `app.html:263-265`).
5. **Split the clip dialog's panel into tabs** (Look / Post text / Stats / Post) once more controls land, instead of one long scroll — mirrors gta6's Post text | Look | YouTube | Schedule & send (`app.html:308`).
6. **Keep the sidebar + topbar shell as is.** It is already closer to Opus/Descript's documented model (setup → projects → per-item editor) than gta6's rail, and it supports the creator grouping gta6 lacks.

### (b) Features to add (all have backend support or a small endpoint)

1. **Caption style picker with live preview** — render the 35 styles as sample-text tiles using `/api/style/preview` (`api_style.py:183`) + `/api/captions/styles` (`api_style.py:44`); replace the `<select>` in the clip dialog and addform.
2. **Version history per clip** — keep each remake as `clip_vN` files + a history JSON (instruction, job id, result); UI = version chips + "What changed" list + Try again. Follows gta6 `app.py:845-856` exactly.
3. **Autopilot page** — `/api/autopilot/spec|preview|install|remove` already exist (`api_auto.py:97-161`) but nothing in `index.html` calls them. Add a settings card: schedule spec → preview text → Install/Remove button.
4. **Mood (meme sound) picker** — `/api/moods` + prime exist (`api_sound.py:55-96`); add a mood select to the clip dialog Look tab and the composer options.
5. **Per-clip YouTube panel** — `/api/stats/video` exists (`api_stats.py:71`); add a Stats tab in the clip dialog: views/likes/comments, retention line, and "AI title ideas" reuse of the text endpoint.
6. **Timeline strip on the clip dialog** — moments.py already computes moments; include the job's moment list in the job payload and render the color-coded strip (gta6 `app.html:809-819`).
7. **Schedule grid view** — upgrade Tools' paste-command scheduler into a simple week grid backed by `/api/schedule/preview` + the posting queue; drag optional, click-to-place enough.
8. **Job log viewer** — "Show log" per job with tail + the restart-detection message (gta6 `app.html:374-375`); `GET /api/jobs/{jid}` exists (`server.py:719`), add `log_tail` to its response.
9. **Bulk post-text copy** — "Copy all post text" per job/creator group (gta6 `app.html:266-267`).
10. **Keyboard shortcuts + kbd chips** — arrows/space/Esc in the review loop; render kbd chips like gta6 `app.html:50`.
11. **"Make my day" preset** — one primary action: newest video for creator X → 10 clips → queue. Pure frontend composition of existing endpoints.

### (c) What NOT to add

- **Timeline drag editing / scene rearranging.** PeakCut's value is "pick + render + post"; a Descript-style timeline is a different product. The start/end number inputs stay.
- **B-roll generation, AI avatars, eye contact, dubbing/voice clones.** Heavy cloud features the externals market; none fit local-first ffmpeg pipelines.
- **Virality-score gamification.** PeakCut already has words/reaction judges; adding a 0-100 "virality score" invites fake precision.
- **Team workspaces / multi-seat.** Single-owner app with an admin flag is enough.
- **118-language UI translation.** English UI + caption translation covers the real need.
- **XML/Premiere export, MCP/API surface.** No user asked; adds surface area.
- **Blotato-style third-party posters.** PeakCut's direct OAuth + queue is cleaner than gta6's Blotato bolt-on.
- **More caption styles, formats, or moods.** 35/8/13 is plenty; the gap is showing them, not counting them.

---

## 6. Ready-to-build list

Ordered by impact. Each item names the file and the endpoint it needs.

1. **Review queue.** New per-creator view state (reuse tab pattern `index.html:1296-1297`): list of `done` clips, Approve/Reject/Skip with `data-act`, auto-advance, progress "x of N". Backend: add `PATCH /api/jobs/{jid}/clips/{cid}` accepting `review: approved|rejected` (extend `studio/server.py:966` area or new `api_review.py` router).
2. **Style picker with live preview.** Replace `index.html:2426` `<select>` with a tile grid; tiles fetch `/api/style/preview?name=…` (`api_style.py:183`) and render sample text with returned CSS. Cache per style in `S.captionStyles`.
3. **Version history.** Render endpoint `server.py:966` already bumps `c.version` (`index.html:2414`): keep old files as `*_v{n}.mp4` + append history JSON per clip; new GET `/api/jobs/{jid}/clips/{cid}/history`; clip dialog gets version chips + list + Try again.
4. **Autopilot card.** Settings tab card calling `GET /api/autopilot/spec` → `preview` → `install`/`remove` (`api_auto.py:97-161`). Show preview text exactly like `tlschedule` does (`index.html:2615-2622`).
5. **Mood picker.** `GET /api/moods` (`api_sound.py:55`) → select in clip dialog Look tab + composer options; include `mood` in the remake payload.
6. **Clip Stats tab.** Clip dialog tab calling `/api/stats/video` (`api_stats.py:71`); render tiles + reasons; "Suggest titles" button reusing the AI text endpoint (`api_text.py`).
7. **Timeline strip.** Extend `GET /api/jobs` (`server.py:714`) job payload with `moments` (from `studio/moments.py`); render `.tl` strip on clip dialog with type-colored markers; click = seek preview or re-cut via new job.
8. **Filter + search row on All videos.** Client-side over `S.jobs` (statuses exist): pills with counts + text search over hook/title/source name; no backend needed.
9. **Stage checklist.** In the job card (`index.html:1759` area): map known stage strings to steps download → transcribe → pick → render, render done/active/pending dots + keep the % bar and stage text.
10. **Global running pill.** Topbar slot showing active job/live count + "Show progress" link, driven by the existing `S.jobs` poll (`index.html:2502-2507`).
11. **Job log viewer.** `GET /api/jobs/{jid}` (`server.py:719`) gains `log_tail` (last ~80 lines + restart-detection flag); "Show log" toggles a `<pre>` in the job card.
12. **Peek on cards.** After pick, auto-call `/api/jobs/{jid}/peek/{cid}` (`api_preview.py:100`) for the first 3 clips and show stills on cards; keep the manual "Take a look" in the dialog.
13. **Copy all post text.** Button per job group: joins clip title/description/hashtags → clipboard (gta6 `app.html:266-267`).
14. **Keyboard shortcuts.** Global keydown when the review queue or clip dialog is open: ←/→ navigate, space play/pause, Esc close, A approve, X reject; show a kbd hint line.
15. **Schedule grid.** New Tools sub-view: 7-day × hours grid fed by the posting queue + `/api/schedule/preview` (`api_preview.py:173`); click a slot to move a queued post; keep the paste-command as the "advanced" escape hatch.
16. **"Make my day".** Primary button on overview: picks the creator's newest channel video → `POST /api/jobs` with count 10 → after done, enqueue posting; one confirm dialog before starting.

Items 1-3 change behavior most (review-first workflow, visual styles, versioning). Items 4-6 are pure wiring of existing endpoints. Items 7-10 are polish on existing surfaces.
