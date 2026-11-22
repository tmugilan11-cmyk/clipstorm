# Wave 6 — completed by the lead after the swarm lost its builders

The swarm (`swarm9-wave6-ai-pipeline`) lost 11 of its 13 build slots to the same transport failures that
have eaten single slots in every earlier wave — this time nearly all at once. Two build slots landed
(`web/feat/learn-report.js`, `web/feat/review-hooks.js`), and the reviewer/fixer/prover trio worked and
did real, verified work (REVIEW.md, FIXES.md, PROOF.md — including one CRITICAL fix: a fabricated
"Hook 0" pill from `Number(null)`; the fixer's `num()` now rejects null, undefined, booleans and blanks
before converting, proven over eight bad shapes).

The lead rebuilt every missing piece by hand:

## Backend (all four routes registered in `studio/server.py` and verified live)

| File | Route | Proven by |
|------|-------|-----------|
| `studio/api_hooks.py` | `GET /api/learn/hooks` | live: real clips scored 100 strong, counts + reasons |
| `studio/api_learnreport.py` | `GET /api/learn/report` | live: the real round rendered (`15 h 31 min ago`) |
| `studio/api_brandai.py` | `POST /api/brandai/suggest` | live: honest empty-changes answer; the provider's own 503s are reported in words |
| `studio/api_posttime.py` | `GET /api/posttime` | live: "Not enough posts yet…" under 5 posts; mean-vs-sum ranking proven in tests |
| `studio/prompt_text.py` | deleted | zero references in studio/, tests/, web/ |

Two API facts the swarm's prompts got wrong, corrected in the code: the throttle pattern is a local
`_throttle` over `auth.throttle` (`ctx.throttle` does not exist), and the AI entry point is
`ai.call(model, prompt, schema, timeout)` (`ai.ask` does not exist).

## UI (four cards on the Improve page, all live-verified in the browser)

`web/feat/learn-hooks.js` ("How the hooks read" — 3 score pills on the real clips),
`web/feat/post-time.js` ("When to post" — honest note on this account),
`web/feat/brand-ai.js` ("Ask for a brand" — suggests, shows from→to, applies only on the explicit press;
provider 503s surface as readable sentences),
`web/feat/learn-arrows.js` ("Every round, before and after" — the real round drawn as from → to).

## Gate

`tests/test_wiring.py` — 23 checks, all passing, registered in `tests/run.py`: the orphan is gone, every
route file declares its path and uses the right module, `brand_ai.apply` is never called by the route,
the server imports and includes all four routers, and `hours_for()` ranks by mean and skips rows without
a number. Plus `tests/test_feat_files.py` green at 68 served files.
