# Fix report: studio/api_igcaption.py (agent-201)

Owner: `studio/api_igcaption.py` (the only file edited). Read-only cross-checks:
`studio/igcaption.py`, `web/feat/igcaption.js`, `tests/test_igcaption.py`,
`tests/test_post_caption.py`, `docs/qa/audit/api-igcaption.md`,
`docs/qa/FINDINGS.md` (section `## studio/api_igcaption.py`).

## Fixes

### 1. `GET /api/igcaption/looks` skipped the `_me(request)` disabled-account gate — FIXED

- Where: `studio/api_igcaption.py:53-57` (finding 1, minor)
- What: Every other route in this router (`igcaption_for` :62, `igcaption_write` :70,
  `igcaption_generate` :91) starts with `user = _me(request)`; `igcaption_looks`
  did not, so a disabled account could still read the endpoint. Impact was nil
  today (constants only, no user data), but the router gate was not uniform.
- Fix applied: The route now takes `request: Request` and calls `_me(request)`
  first, exactly like the other three routes. A plain-English comment says why.
- Proof:
  - `python -m py_compile studio/api_igcaption.py` → `COMPILE_OK`
  - In-process TestClient (middleware sets `request.state.user`, same pattern as
    `tests/test_post_caption.py:33-38`): disabled account →
    `disabled status 403 {'detail': 'This account is switched off.'}`
  - Live server curl still answers 200 (old process); the 403 gate takes effect
    after the lead's final restart.

### 2. `/api/igcaption/looks` returned languages as bare IDs without labels — FIXED

- Where: `studio/api_igcaption.py:55-56` (finding 2, minor)
- What: `"langs": list(igcaption.LANGS)` answered `"langs":["original","ja","zh"]`
  next to `"formats":[{"id":"natural","label":"Natural"},…]`. A consumer reading
  this endpoint alone would show "ja"/"zh", which a beginner would not understand.
  `LANG_NAMES` (`studio/igcaption.py:19`) already held the plain names but was
  unused by this route.
- Fix applied: `langs` now returns `[{"id","label"}]` built from
  `igcaption.LANG_NAMES` (with a `.get(k, k)` fallback so a language ID missing a
  name can never 500 the route), preserving the `LANGS` order to match the UI's
  select order. `formats`, `limit` and `note` are unchanged.
- Consumer safety verified before changing the shape:
  - No JS file fetches `/api/igcaption/looks` (repo-wide grep: only docs mention it).
  - `web/feat/igcaption.js` never calls the endpoint — `mount()` fetches the
    per-clip view only and hardcodes its own labels at :52, so nothing breaks.
  - Neither test file asserts the old `langs` shape.
- Proof:
  - `python -m py_compile studio/api_igcaption.py` → `COMPILE_OK`
  - In-process TestClient: `status 200` with
    `langs: [{'id': 'original', 'label': 'the same language as the source'},
    {'id': 'ja', 'label': 'Japanese'}, {'id': 'zh', 'label': 'Simplified Chinese'}]`
    — same `{id,label}` shape as `formats`.
  - Live server curl (READ-ONLY) still shows the old bare-ID shape; the new shape
    takes effect after the lead's final restart.

## Skips

None. Both findings under `## studio/api_igcaption.py` held when verified against
the source and the audit report.

## Gates run

| Gate | Result |
|---|---|
| `python -m py_compile studio/api_igcaption.py` | `COMPILE_OK`, exit 0 |
| `python tests/test_igcaption.py` | `All checks passed.` |
| `python tests/test_post_caption.py` | 6 checks ok, `All checks passed.` |
| In-process TestClient of the fixed route (new shape + disabled gate) | 200 with labelled langs; 403 for a disabled account |
| `curl -s http://127.0.0.1:8798/api/igcaption/looks` (READ-ONLY) | 200, old shape — route fixes land after the lead's final restart |

## Notes for the lead

- The only edited file is `studio/api_igcaption.py`; no JS was touched, so no
  `node --check` is needed.
- The live server on :8798 still runs the old code; both fixes take effect after
  the final restart.
