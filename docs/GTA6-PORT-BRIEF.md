# PeakCut ← gta6-clipper: port brief

Two codebases, one goal: PeakCut keeps its multi-user web app, and gains every feature
`gta6-clipper` has that it lacks.

- **PeakCut** = `peakcut/` — FastAPI + SQLAlchemy + vanilla-JS SPA. Multi-user (accounts, admins,
  creators, profiles), job pipeline (`studio/jobs.py`), AI picking (`studio/brain.py`), posting
  (`studio/posting.py`), live (`studio/live.py`), render (`studio/render.py`), local + Logfare
  transcription (`studio/transcribe.py`).
- **gta6-clipper** = `gta6-clipper-main/` — single-user local skill. `app.py` + `app.html` UI,
  ffmpeg render engine, 32 caption styles, 8 clip formats, chat-spike detection, meme sounds,
  OCR game-event detection, offline caption translation.

The source of truth for what gta6-clipper does is `gta6-clipper-main/SKILL.md` and
`gta6-clipper-main/SKILL-REFERENCE.md`. Read those before porting anything.

## Ground rules for every agent

1. **PeakCut is the host.** New behaviour lands in `peakcut/studio/*.py` + `peakcut/web/index.html`,
   following PeakCut's existing patterns (see `studio/ai.py` for settings, `studio/jobs.py` for
   pipeline stages, `studio/server.py` for routes). Do not copy gta6-clipper's stdlib HTTP server,
   its `app.html`, or its single-tenant assumptions.
2. **Port the algorithm, not the file.** gta6-clipper is single-user and CLI-shaped. PeakCut is
   multi-user and request-shaped. Code that assumes a global workspace, a cwd, or one user must be
   reworked, not pasted.
3. **No new heavyweight dependencies without checking `peakcut/requirements.txt` first.** ffmpeg via
   subprocess is already how PeakCut renders — keep that. Do not add a package that is not already
   there unless the feature cannot work without it, and if so say so explicitly.
4. **Every feature must be off by default or degrade to today's behaviour.** A user who never opens
   the new UI must get exactly the clips they got before.
5. **Tests.** `peakcut/tests/` holds the suite. Add tests next to the existing style; do not break
   `tests/test_transcribe_logfare.py`.
6. **Read before you write.** The editor tools require it, and concurrent edits from other agents
   in this swarm are expected — re-read a file you are about to edit if it may have changed.
7. **Report precisely.** "Done" without a file path, a line reference, and the command you ran to
   verify it is not done.

## Feature inventory

Status of each gta6-clipper capability against PeakCut today.

### Already present in PeakCut (do not rebuild; verify and report gaps)
| Capability | gta6-clipper | PeakCut today |
|---|---|---|
| Local transcription | `transcribe.py` (faster-whisper) | `studio/transcribe.py` (sherpa-onnx Parakeet) + Logfare cloud |
| AI moment picking | prompt-driven, `SKILL.md` step 2 | `studio/brain.py` (structured JSON picks) |
| Face-aware reframing | `reframe.py` (58 KB) | `studio/facecam.py` (16 KB) |
| Render | `clip.py` (74 KB) + `batch.py` | `studio/render.py` (16 KB) |
| Quality check | `qc.py` PASS/WARN/FAIL | `studio/quality.py` |
| Live clipping | `live.py`, `hunt.py` | `studio/live.py` (44 KB) |
| Posting | none (Blotato MCP) | `studio/posting.py`, post queue |
| Learning from a channel | `learn.py` | `studio/feedback.py` |

### Missing from PeakCut (the port)
| # | Capability | Source | What it is |
|---|---|---|---|
| 1 | **Caption styles** | `clip.py` | 32 named styles: classic, word, hormozi, beast, karaoke, minimal, mozi, pill, lemon, bubble, sweep, stamp, neon, ember, retro, crimson, glow, twotone, hollow, comic, whisper, pop, typewriter, slide, shake, punch, drop, duo, emoji, lower, meme, tiktok |
| 2 | **Clip formats** | `formats.py` | 8 non-`moment` formats: callback, compilation, escalation, thenvsnow, reveal, chat, waitforit (+ plain moment) |
| 3 | **Chat-spike detection** | `chat.py` | Twitch/Kick/YouTube chat with no login; spike = 3× the stream's own baseline; top phrases |
| 4 | **Moment types (no AI)** | `moments.py` | Labels stretches chase / crash / fight / stunt / reaction / funny from audio+video features |
| 5 | **Game-event OCR** | `vision.py` | Detects WASTED / BUSTED / MISSION PASSED banners, wanted stars, hard cuts |
| 6 | **Meme sounds** | `meme.py` | 9 moods (embarrassing, fail, shock, hype, win, awkward, cringe, funny, suspense) + freeze/vignette/shake per mood |
| 7 | **Music beds** | `meme.py` | hype / chill / tense / funny, ducked under speech, −14 LUFS |
| 8 | **Offline caption translation** | `translate.py` | es fr pt de ar hi — captions and hook |
| 9 | **Peek (frame preview)** | `peek.py` | 4 frames per pick saved as jpg before rendering |
| 10 | **Streamer clip rules** | `clip_rules.json` | Per-handle badge: clipping allowed / no / ask / unknown, with source link |
| 11 | **Live hunt** | `hunt.py` | Watches many streamers at once, auto-cuts on chat spikes |
| 12 | **YouTube analytics** | `ytstats.py` | Read-only views/retention for a published Short |
| 13 | **Voice-over** | `voice.py` | User's line over a finished Short, game ducked 18 dB |
| 14 | **Autopilot scheduling** | `app.py` | OS-level scheduled runs (Task Scheduler / launchd / cron) |
| 15 | **Brand config** | `brand.example.json` | One `brand.json` sets watermark, position, style, layout, music for every Short |
| 16 | **Prompt-to-edit** | `app.py` | "end 2 s earlier", "bigger captions" — natural-language re-cut, original kept |

## Architecture decisions already made

- **New modules, one concern each**, in `peakcut/studio/`: `captions.py`, `formats.py`, `chat.py`,
  `moments.py`, `vision.py`, `meme.py`, `translate.py`, `peek.py`, `rules.py`, `hunt.py`,
  `voice.py`, `brand.py`. Follow the existing naming and docstring style.
- **Settings** follow `studio/ai.py`: a JSON file in `DATA_DIR`, a `public()` that never leaks
  secrets, a `save()` under a lock, `_file()` helper. Transcription settings
  (`tr.json`, `studio/server.py` `_tr_*`) are the most recent example of the pattern.
- **Routes** follow `studio/server.py`'s transcription block: `_admin()` gate, `_throttle()`,
  `HTTPException(400)` for user errors, `HTTPException(502)` for upstream, `safe.friendly()` for
  messages.
- **UI** goes in `web/index.html`. Settings tabs live in `setTabs()`; every new sidebar icon must
  exist in the `I` icon map (`const ic = n =>`). The SPA router regex must learn any new route.
