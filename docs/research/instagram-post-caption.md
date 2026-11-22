# Instagram Reel caption — what the publish path actually takes

Written 2026-11-22. The research subagent owed this file and its answer was lost to the
transport, so it is written from the lead's live read of Meta's own documentation
(checked in the browser on 2026-11-21). The knowledge was already applied in
`docs/IGCAPTION.md`; this file records the source facts in one place.

## The one fact that changed the feature

Instagram's `caption` is **plain text under the post**. It is not a styling surface:
the font, colour and animation of a Reel's caption are controlled by Instagram, not by
the uploader. An earlier version of PeakCut burned Japanese/Chinese caption *styles*
into the video itself — that was wrong and was removed. What a person can control is
the text that appears under the Reel after upload.

## The publishing contract (verified live)

1. **Create a container** — `POST /<IG_ID>/media`
   - Reels: `?media_type=REELS &video_url=<REEL_URL> &caption=<IMAGE_CAPTION> &share_to_feed=…`
   - `caption` is a separate parameter on the container. It can include hashtags.
2. **Publish the container** — `POST /<IG_ID>/media_publish` with `creation_id`.
3. **Resumable uploads** (alternative to a public `video_url`) —
   `POST https://rupload.facebook.com/ig-api-upload/<IG_MEDIA_CONTAINER_ID>`.

## Limits Meta states on the `caption` parameter

Verbatim from the `ig-user/media` reference, query-string parameters:

> A caption for the image, video, or carousel. Can include hashtags…
> Maximum 2200 characters, 30 hashtags, and 20 @ tags.
> Not supported on images or videos in carousels.

- **2,200 characters** — PeakCut validates against this (`studio/igcaption.py`
  `MAX_LENGTH = 2200`); the editor counts codepoints, not words.
- **30 hashtags, 20 @ tags** — the builder keeps the creator's footer and the clip's
  hashtags; it does not invent more.
- **JPEG-only images** — relevant to cover thumbnails, not to the caption.

## Rate limits worth knowing

- **100 API-published posts per 24 h** per account. PeakCut's post queue (`studio/posting.py`)
  already spaces posts per account, so a queue that runs faster than this is a queue bug.

## How PeakCut uses this

- `studio/igcaption.py` builds the caption: `default()` (title-or-hook + description +
  cleaned hashtags + creator footer), `for_post()` (the saved caption verbatim only when
  `ig_caption_enabled` is true; an explicit empty override is intentional), and
  `generate()` (an optional AI draft in the chosen language, never persisted until saved).
- `studio/posting.py` `_ig_caption()` is used **only on the instagram branch** — YouTube
  and TikTok present no Reel caption and would show a wall of text with no styling.
- The editor control lives in the clip dialog's Text tab
  (`web/feat/igcaption.js` → `#ed_igbox`).

## Sources checked live 2026-11-21

- `https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-user-media#query-string-parameters`
- Instagram content publishing guide (create container → publish container flow)
