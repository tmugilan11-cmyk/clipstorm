# Waves 2 to 10 — 18 agents each, 162 agents

Wave 1 built the menu frame and the Insights shell. Waves 2-10 finish the product.
Every wave: build -> review -> fix -> prove. Every agent loads a skill first.
Every agent reads `docs/swarm4/CONTRACT.md` and `web/feat/heard.js` before writing.
Nobody edits `web/index.html`. One file per agent, owned for the whole wave.

## Wave 2 — Insights completeness (18)
trends-shell, trends-backend, trends-cards, revenue-tab, realtime-card,
retention-tab, export-csv, insights-filters, insights-empty, shorts-tab,
compare-view, kpi-tooltips, insights-tests, api-tests, docs-insights,
reviewer, fixer, prover.

## Wave 3 — the AI reads deeper (18)
retention-signals, hook-testing, prompt-v3, learn-two-arms, learn-report,
learn-guard, learn-tests, learn-ui-polish, learn-docs, pipeline-copy,
schedule-ai, brand-ai, cost-guard, undo-all, reviewer, fixer, prover,
signal-tests.

## Wave 4 — the rest of the menu (18)
creators-page, live-page, schedule-page, help-page, admin-page, usage-page,
review-page, clips-page, formats-page, sounds-page, languages-page,
tasks-page, zernio-page, youtube-page, old-links, docs-pages, reviewer,
fixer.

## Wave 5 — polish (18)
type-scale, spacing, colour, icons, empty-states, errors, loading, motion,
keyboard, focus, contrast, mobile, wide, dark, copy-pass, a11y-tests,
reviewer, fixer.

## Wave 6 — AI into the pipeline (18)
pick-format, pick-mood, pick-length, pick-style, hook-score, title-score,
post-time, caption-lang, plan-store, plan-explain, plan-ui, plan-tests,
plan-guard, plan-docs, reviewer, fixer, prover, plan-api.

## Wave 7 — tests and evidence (18)
menu-tests, page-tests, route-tests, form-tests, api-tests, job-tests,
render-tests, audio-tests, ai-tests, learn-tests, transcribe-tests,
posting-tests, storage-tests, auth-tests, regression, reviewer, fixer,
prover.

## Wave 8 — documents (18)
readme, agents-rules, deploy, env, api-doc, page-doc, ai-doc, learn-doc,
troubleshooting, upgrading, privacy, licence, changelog, screenshots,
glossary, reviewer, fixer, prover.

## Wave 9 — run everything (18)
boot, upload, transcribe, clip, render, sound, post, stats, learn,
menu, pages, forms, api, storage, second-user, restart, reviewer, prover.

## Wave 10 — final audit (18)
every-page, every-button, every-route, every-test, every-frame, console,
network, contrast, keyboard, mobile, first-run, second-user, errors,
copy, perf, reviewer, fixer, signoff.

## Status (2026-11-21)

All ten waves are closed. Waves 1-5 and 7-10 ran as agent swarms; waves 6 and 10 were finished by the
lead by hand after their workflow engines dropped agent replies to the transport. Every wave has a
folder under `docs/swarm4/waveN/` with its review, fixes and proof, and the final audit is
`docs/swarm4/wave10/AUDIT.md` (20 checks, verdict SHIP).
