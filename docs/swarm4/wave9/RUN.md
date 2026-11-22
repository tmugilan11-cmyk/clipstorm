# Wave 9 — run everything (the lead's live end-to-end pass)

Against the running server with every fix from this session in place:

- **Boot**: `/healthz` → `{"ok":true}`.
- **Upload → transcribe → pick → render**: `POST /api/upload` with the real speech video
  (`.pctest/media/speech_video.mp4`) → job `20261120-200119-5fdd2d8f89` → `done` in ~70 s, 1 clip,
  `watched_pct` hit 100.0 (the progress fields work), and the clip carries **22 real nova-3 word timings**
  (`words.json`: `and 0.00-0.64`, `so 0.64-0.96`, …). The public job view hides `fixed_words` by design —
  the truth was checked in `job.json` on disk.
- **Review**: `GET /api/jobs/…/review` → 1 row, remaining 1, `review: null` — the clip waits for a person,
  exactly as review-first says.
- **Sound**: the meme-sound chain was proven earlier this session with spectral analysis (sub-bass spike at
  the dragged position), and the regression tests cover the routes.
- **Learn**: `POST /api/learn/run {"days":28,"dry":true}` → 6 facts, source "peakcut" — the honest
  no-channel path.
- **Pages**: all 19 addresses under `/app/` serve 200 (`/`, `videos`, `review`, `brand`, `improve`,
  `analytics`, `transcribe`, `tools`, `apps`, `ai`, `storage`, `account`, `help`, `creators`, `live`,
  `schedule`, `formats`, `sounds`, `ai-usage`).
- **Routes**: `/api/transcribe`, `/api/ai`, `/api/learn/state`, `/api/learn/hooks`, `/api/learn/report`,
  `/api/posttime`, `/api/analytics/summary`, `/api/trends/status`, `/api/style/preview`,
  `/api/captions/styles`, `/api/memesounds/library` — all 200.
- **Posting**: the Zernio round trip (upload → post → status → analytics with the real key) was proven
  earlier this session; the review-first gate has 9+ regression checks.
