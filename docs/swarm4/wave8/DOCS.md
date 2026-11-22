# Wave 8 — documents (what was checked and corrected)

Every document was read against the build, and the ones that had drifted from the code were corrected.
This wave has no agent folder because the work is the documents themselves.

## README.md
- "one of three styles" → **35 looks**, which is what `captions.style_names()` plus the three house
  looks actually offers.
- Posting now says a **Zernio key** covers YouTube, Instagram, TikTok and 14 more platforms.
- New bullets for **Review before posting**, **Meme sounds**, **Improve**, and **Insights**.
- The AI table gained **logfare**, and the model paragraph now says the app reads the service's real
  list and turns the field into a dropdown, instead of telling the person to hunt for ids.
- Settings table gained `PEAKCUT_ZERNIO_KEY` / `PEAKCUT_ZERNIO_KEY_FILE`.
- "AI usage" → **Usage**, which is where that page now lives.

## DEPLOY.md
- "Good to know" gained a **Review before posting** entry naming `PEAKCUT_REVIEW_FIRST`, including the
  fact that the rejection ban stays on even when the wait is off.

## .env.example
- Gained `PEAKCUT_REVIEW_FIRST` next to the Zernio block, with the plain-English reason.

## AGENTS.md
- Rules now cover: a clip's look, length, sound and hook words come from the brand document; a menu page
  is also a feature file; Logfare is both the speech service and an AI provider through one shared key;
  YouTube's page is called Insights.

## docs/
- `MENU.md` — all 19 main-menu rows, what each is for, which file draws it, and the routes each reaches.
- `INSIGHTS.md` — the Insights page's tabs, ranges and the honest-notice rule.
- `swarm4/*` — the plan, the per-wave briefs, and each wave's review/fixes/proof.
- `swarm4/wave10/AUDIT.md` — the final 20-check audit.

## Environment variables
All 64 declared in `.env.example` resolve: 56 are read in `studio/*.py`, 8 are consumed by
`docker-compose.yml`. Verified by script, not by eye.
