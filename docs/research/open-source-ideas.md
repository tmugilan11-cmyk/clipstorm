# Open-source auto-clipping projects: ideas for Clipstorm

Searched 2026-11-23. Features come from each project's own README (fetched, not run); star counts were not
verified. Nothing was installed or executed. "Have" = Clipstorm already does it; "Built" = added in this pass.

## Projects

| Project | Link | Notes |
|---|---|---|
| SupoClip | https://github.com/FujiwaraChoki/supoclip | AGPL-3.0. LLM picks 3-7 clips, hook/engagement/value/share scores, face-centred 9:16, caption templates, hook titles, trim/split/merge editor, platform presets, post/schedule from the task page, platform view counts feed back into picking. |
| OpenShorts | https://github.com/mutonby/openshorts | MIT. 3-15 clips of 15-60 s with scores, editor with source/program monitors beside the full transcript (click a word to cut), AI layout per video or forced, hook overlay editable, YouTube Studio tools (titles with refine chat, thumbnails, chapters), dubbing, autopilot on new uploads. |
| VibeClip | https://github.com/oktaydbk54/vibeclip | AGPL-3.0. Chat panel edits ("remove filler words", "add zooms"), one-step undo for a whole multi-step edit, caption/pacing style presets as JSON files, live 9:16 preview, bring-your-own LLM key. |
| ClipsAI | https://github.com/ClipsAI/clipsai | MIT Python library: WhisperX transcript, clip finder from topic shifts in the transcript, resize to 9:16. Speech only. |
| ClippedAI | https://github.com/Shaarav4795/ClippedAI | OpusClip alternative built on clipsai. |
| autoclip | https://www.opensourcealternatives.to/item/autoclip | Highlights from YouTube, Bilibili or local files, runs locally. |
| OpenClipper | https://sourceforge.net/projects/openclipper/ | Windows, local or cloud transcription, smart reframing, styled captions, direct publishing. |
| ShortGPT | https://github.com/SolvAI/ShortGPT (fork; the original is RayVentura/ShortGPT) | Framework for generated shorts (voiceover plus stock footage). Different goal; little to take. |
| OpenClip | https://github.com/aionixos/openclip | Local-first: URL, download, auto-clip, export. |
| AI-Youtube-Shorts-Generator | https://github.com/SamurAIGPT/AI-Youtube-Shorts-Generator | Whisper plus LLM highlight finder. |
| yt-heatmap-clipper | not found by search | Idea only: YouTube "most replayed" graph. Clipstorm already reads it (`studio/signals.py`). |

## Ideas, and where Clipstorm stands

| Idea | From | Status |
|---|---|---|
| Score broken into hook / payoff / emotion / share | SupoClip, OpusClip | Built: letter marks on every clip card and in the editor. |
| Transcript beside the preview, click a word to jump | OpenShorts | Built: left column of the clip editor, current word lit as it plays. |
| Keep / skip on the clip list | OpusClip like/dislike | Built (uses the existing review gate). |
| Post or schedule many selected clips at once | SupoClip, OpusClip bulk scheduler | Built: Post button in the selection bar; the queue spaces them. |
| Saved settings reused on the next video | OpusClip Recipes | Built: Saved setups in the upload settings (kept in the browser). |
| "What to look for" prompt on the submit box | OpusClip ClipAnything | Built, kept on the creator (server has no per-video focus). |
| Clip length presets | OpusClip | Built. |
| Calendar of posts | OpusClip | Built (`calendar.js`). |
| Performance feedback into clip picking | SupoClip | Have (learn.js, own results). |
| Hook text over the opening | SupoClip, OpenShorts | Have. |
| Face-centred 9:16, stacked layouts, blurred fill | all | Have. |
| Platform views back into scoring | SupoClip | Have. |
| Autopilot on every new upload | OpenShorts Cloud | Have (creators auto recording, autopilot). |
| Chat-style edit ("end 2 seconds earlier") | VibeClip | Have ("Change it in words" under Cut > More options). |
| One-step undo of a whole edit | VibeClip | Have in part (clip versions in history.js). |

## For the lead: judge, clip types, analytics (not built here)

- **Judge**: a per-video "what to look for" (`clean_options` accepts `focus`, `find_clips(focus=...)` reads the job before the creator). Topic-shift boundaries from ClipsAI so a cut never lands mid-thought. Scene-boundary snapping from OpenShorts.
- **Clip types**: "stack two speakers" layout chosen per scene (OpenShorts); caption/pacing presets as JSON files users can drop in (VibeClip); platform export presets (SupoClip).
- **Analytics**: YouTube Studio style helper, titles with a refine chat, chapter timestamps in descriptions (OpenShorts); per-platform numbers feeding the next pick, already present.

## Agent skills found (search only, nothing installed)

Run `npx skills add <owner/repo@skill>` to install.

- video editing: `affaan-m/ecc@video-editing` (18.9K), `curiositech/some_claude_skills@video-processing-editing`, `ecliptic-ai/skills@beat-sync-video-editing`, `heygen-com/hyperframes@hyperframes` (1.6M)
- ffmpeg: `digitalsamba/claude-code-video-toolkit@ffmpeg` (16.6K), `kajisho5/ffmpeg-skill@ffmpeg-skill`, `fabriqaai/ffmpeg-analyse-video-skill@ffmpeg-analyse-video`, `josiahsiegel/claude-plugin-marketplace@ffmpeg-captions-subtitles` (useful for the caption step)
- ui design: `vercel-labs/agent-skills@web-design-guidelines` (894K), `nextlevelbuilder/ui-ux-pro-max-skill@design-system`, `github/awesome-copilot@penpot-uiux-design`
- youtube: `op7418/youtube-clipper-skill@youtube-clipper` (4.9K, closest to this app), `jimliu/baoyu-skills@baoyu-youtube-transcript`, `composiohq/awesome-claude-skills@youtube-downloader`, `fetcher-sh/fetcher-skills@youtube-api`
