# Instagram post captions

The Instagram caption is plain text under the uploaded Reel. It is saved separately from the subtitles drawn on the video.

In the clip editor, open **Text → Instagram post caption**. Turn on **Use a separate caption for Instagram**, type the complete caption and hashtags, and press **Save Instagram caption**. Original language, Japanese and Chinese are available for optional AI drafts. Choose a wording style, press **Generate draft**, review the result, then save it. Generating a draft never saves or publishes it.

**Use regular post text** disables the override and uses the title, description, hashtags and creator footer. An enabled empty caption deliberately sends no caption. Saved custom text is sent verbatim: the publisher does not add another title, footer or duplicate hashtags.

## Publishing contract

Meta's [IG User Media reference](https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-user/media#query-string-parameters) lists `caption` as a separate parameter for Reel containers, alongside `video_url` and `media_type=REELS`. It accepts a maximum of 2,200 characters, including hashtags and mentions. The [content publishing guide](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/content-publishing/) describes creating the container, uploading the video and publishing the container. Checked against the live primary documentation on 2026-11-21.

The API accepts caption text, not a font, text color or animation. Instagram controls its display. The previous Japanese/Chinese video-effect styles and their fabricated visual rankings were removed. Multilingual fonts remain installed for actual speech subtitles. Previously rendered videos are not rewritten when post text changes.

Both native Instagram publishing and the Zernio Instagram route use `igcaption.for_post()`. YouTube and TikTok continue to use their regular metadata.

## API

- `GET /api/igcaption/looks`: wording choices, languages and length limit. The historical URL is kept for compatibility; the response contains no visual looks or rankings.
- `GET /api/jobs/{jid}/clips/{cid}/igcaption`: current saved/default caption.
- `PUT /api/jobs/{jid}/clips/{cid}/igcaption`: validate and save `{enabled, caption, lang, format}`.
- `POST /api/jobs/{jid}/clips/{cid}/igcaption/generate`: draft only, using the selected AI model; never modifies the clip.

The routes use the signed-in owner, preserve Unicode and paragraph breaks, reject invalid input and enforce the character limit. AI failures preserve saved text and the editor's current draft.

## Verification

`tests/test_igcaption.py` checks text, language and length handling. `tests/test_post_caption.py` exercises real HTTP routes, ownership, persistence, draft-only generation and exact outgoing text through both publishers with network publishing mocked. No test publishes to a social account.
