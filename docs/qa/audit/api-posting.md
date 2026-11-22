# API audit: posting / Zernio routes

Slug: `api-posting`. Auditor: agent-154 of the QA swarm. Date: 2026-11-22.

## Pages / files owned

- `GET /api/overview` (studio/server.py:1606-1608 → posting.overview())
- `GET /api/zernio` (studio/server.py:1754-1757 → zernio.saved())
- `PUT /api/zernio` (studio/server.py:1760-1769 → zernio.save(body))
- `POST /api/zernio/test` (studio/server.py:1772-1779 → zernio.test())
- `GET /api/zernio/accounts` (studio/server.py:1782-1791 → zernio.accounts(), read-only)

Files read before testing: `docs/qa/CONTRACT.md`, `studio/posting.py` (317 lines), `studio/zernio.py` (374 lines), `studio/server.py` (zernio + overview routes), `studio/config.py:236-242`, and the consumer side of `web/index.html` (settings load :2626-2629, Zernio card :2660-2676, handlers :3379-3400, outer catch :3462).

## Method

Every owned route was curled against the live server (http://127.0.0.1:8798) with realistic params and at least one invalid input. Mutating calls that would change real saved data (a valid-format key PUT, `forget_key`) were deliberately not sent: `data/zernio.json` holds a real key and the audit must not clobber it. The no-key behaviour of `zernio.test()` was instead reproduced in an isolated Python process with `PEAKCUT_DATA=/tmp/pc-audit154-nokey` and both key env vars empty, which touches no real data. Consumers in `web/feat/*.js` were grepped for the routes they call (`creators.js`, `day.js`, `grid.js` use `/api/overview`; no feat file mentions zernio — the UI lives only in `web/index.html`).

## Checks run (all with results)

| # | Check | Result |
|---|---|---|
| 1 | `GET /api/overview` | 200, 808 bytes: `{paused, creators, posts, daily[14 days oldest-first], alerts, recording}`; daily carried real data (5 clips in the window), posts `[]` honestly empty |
| 2 | `GET /api/overview?bogus=1` | 200, unknown param ignored |
| 3 | `GET /api/zernio` | 200: `{ready:true, has_key:true, key_hint:"724b", base, platforms(16)}` — the key itself never leaks, only last 4 chars (zernio.py:115) |
| 4 | `PUT /api/zernio` body `{}` | 200, state unchanged (docstring zernio.py:120 "An empty key keeps the one already saved") |
| 5 | `PUT /api/zernio` body `{"key":""}` | 200, kept saved key, `has_key` still true |
| 6 | `PUT /api/zernio` body `{"key":"short"}` | 400 `{"detail":"That does not look like a Zernio key. Copy it whole from the dashboard."}` (raised before any write, zernio.py:128-129) |
| 7 | `PUT /api/zernio` body `[1,2]` | 422 standard FastAPI `dict_type` validation error |
| 8 | `POST /api/zernio/test` body `{}` (key saved) | 200 `{"ok":true,"accounts":2,"platforms":["instagram","youtube"]}`, 0.009 s (60 s account cache) |
| 9 | `POST /api/zernio/test` body `{"key":"zk-invalid-test-key-0123456789"}` | 400 `{"detail":"Zernio rejected the key. Copy a current one from Zernio, under API keys, and paste it here."}`, 0.33 s (real Zernio round-trip) |
| 10 | `POST /api/zernio/test` body `{"key":"   "}` | 200, whitespace strips to empty → falls back to the saved key (zernio.py:121), same 2 accounts |
| 11 | `zernio.test()` isolated, no key anywhere | **`{'ok': True, 'accounts': 0, 'platforms': []}`** — see finding 1 |
| 12 | `GET /api/zernio/accounts` | 200 `{"accounts":[2 rows], "count":2}`, ids `zernio:…`, `account_id` stripped, `followers:null` |
| 13 | `GET /api/zernio/accounts?refresh=true` | 200, fresh Zernio round-trip 0.57 s, same 2 rows |
| 14 | `GET /api/zernio/accounts?refresh=notabool` | 422 standard FastAPI `bool_parsing` error |
| 15 | UI render of `followers:null` | Guarded: `index.html:2664` `a.followers != null ? … : ""` — no "null" text reaches the page |
| 16 | `posting.py:255` local `_posts = _mine()` | Intentional shadow, confined to `overview()`; module-level `_posts` untouched outside — no bug |

## Findings

| Severity | Where | What | Evidence | Fix |
|---|---|---|---|---|
| important | studio/zernio.py:256-262 (+ 213-214, 149-150) | `POST /api/zernio/test` answers `{"ok": true, "accounts": 0}` when no key is saved anywhere: a success answer from the endpoint whose docstring says it "proves the key works". `accounts()` short-circuits `if not k: return []` (zernio.py:213-214) before `_call` can raise its correct no-key message "Paste a Zernio key in Settings, Connected apps first." (zernio.py:149-150), so `test()` computes `ok:True` from an empty list (zernio.py:262). The dashboard is guarded client-side (`index.html:3381` "Paste the key first."), but any direct API caller gets a wrong `ok:true` instead of the error the rest of the module writes carefully. | Measured in isolation: `PEAKCUT_DATA=/tmp/pc-audit154-nokey`, `PEAKCUT_ZERNIO_KEY`/`PEAKCUT_ZERNIO_KEY_FILE` unset → `test(): {'ok': True, 'accounts': 0, 'platforms': []}`; same `saved(): has_key False`. Code: zernio.py:213-214, 256-262. | In `test()` (or the server route), raise the existing no-key sentence when `key_override` is empty and `key()` returns nothing: `if not (key_override or key()): raise ZernioError("Paste a Zernio key in Settings, Connected apps first.")`, so `ok:true` only ever means a real Zernio answer came back. |
| minor | web/index.html:3382-3386 | `zsave` PUTs the key, then runs `send("/api/zernio/test", …)` with no try/catch. If the test fails after the PUT succeeded, the exception jumps to the outer catch (`index.html:3462`), skipping `S.zOpen = false` and the `S.zernio`/`S.accounts` refresh; the user sees only the raw Zernio error and no word that the key was saved — though a failing new key is now the one in use. The AI flow solves this exact shape one screen away (`index.html:3122-3126`: `let ok = null, why = ""; try { ok = await send("/api/ai/test"); } catch (err) { why = err.message; }` → toasts `Saved, but the test failed. ${why}`). | Code: `index.html:3383` `const got = await send("/api/zernio/test", {}, "POST");` with no try/catch; contrast `index.html:3123` and the toast at `:3386` only reached when the test succeeds. Not reproduced live (would need to overwrite the real saved key; refused). | Wrap the test call the way the AI flow does: `let got = null, why = ""; try { got = await send("/api/zernio/test", {}, "POST"); } catch (err) { why = err.message; }`, then always run the `S.zernio`/`S.accounts` refresh and toast `got ? "Saved. …" : `Saved, but the test failed. ${why}`` with kind `got ? "ok" : "bad"`. |
| minor | studio/server.py:1773 | Dead code: `body: dict = Body(default={}) or {}` — the `or {}` can never run because a `FieldInfo` default is truthy, so the expression is just `Body(default={})`. No behaviour impact; it suggests the author thought an absent body could arrive as `None`. | Reading `studio/server.py:1772-1779`; FastAPI injects `{}` for an absent JSON body under `Body(default={})`. | Drop the `or {}` so the line reads `body: dict = Body(default={})`, or if the intent was None-safety, do it where it can fire: `body = body or {}` inside the function. |

No critical findings: no 500s, no crashes, no 404s on any owned route; every invalid input produced either the module's own plain-language sentence (400) or a standard FastAPI 422; no unreadable text (the one `null` value the API can emit, `followers`, is guarded before render).

## What passed and is worth keeping

- Error sentences are written for people, not logs: "That does not look like a Zernio key. Copy it whole from the dashboard." and "Zernio rejected the key. Copy a current one from Zernio, under API keys, and paste it here." — both measured verbatim over HTTP.
- `GET /api/zernio` never returns the key, only `key_hint` (last 4 chars, zernio.py:115) — the deliberate "never the key itself" contract holds over the wire.
- Empty states are honest: `posts: []` and `daily` with zeros rather than missing fields; consumers (`creators.js:228`, `grid.js:164`) already `.catch(() => null)`.
- Key validation runs before any file write (zernio.py:128-129), and key writes go through a lock, a `.tmp` file and `chmod 0o600`.
- The consumer side keeps working when the server is older than the page: `index.html:3385` and `:3397` both `.catch(() => S.accounts || [])`.

## JSON

```json
{
  "slug": "api-posting",
  "bugs": [
    {
      "severity": "important",
      "where": "studio/zernio.py:256-262 (with 213-214, 149-150)",
      "what": "POST /api/zernio/test returns {\"ok\": true, \"accounts\": 0} when no key is saved anywhere, because accounts() short-circuits to [] before _call can raise the correct no-key message; a success answer from an endpoint that is supposed to prove the key works. UI is guarded (index.html:3381), direct API callers are not.",
      "evidence": "Isolated reproduction: PEAKCUT_DATA=/tmp/pc-audit154-nokey with both key env vars empty -> test(): {'ok': True, 'accounts': 0, 'platforms': []}; code zernio.py:213-214 short-circuit, :256-262 ok computed from empty rows, :149-150 holds the correct sentence.",
      "fix": "In test(), raise ZernioError('Paste a Zernio key in Settings, Connected apps first.') when key_override is empty and key() returns nothing, so ok:true only ever follows a real Zernio answer."
    },
    {
      "severity": "minor",
      "where": "web/index.html:3382-3386",
      "what": "zsave runs the test call with no try/catch; a test failure after a successful PUT jumps to the outer catch (3462), skips the S.zernio/S.accounts refresh and the dialog close, and shows no word that the key was saved. The AI flow (3122-3126) handles the same shape with 'Saved, but the test failed.'",
      "evidence": "index.html:3383 const got = await send(\"/api/zernio/test\", {}, \"POST\"); no try/catch; contrast index.html:3123-3126; not reproduced live to avoid overwriting the real saved key.",
      "fix": "Wrap the test call: let got = null, why = \"\"; try { got = await send(\"/api/zernio/test\", {}, \"POST\"); } catch (err) { why = err.message; }, always refresh state, and toast got ? 'Saved. …' : `Saved, but the test failed. ${why}`."
    },
    {
      "severity": "minor",
      "where": "studio/server.py:1773",
      "what": "Dead code: Body(default={}) or {} — the or {} can never run because a FieldInfo default is truthy. No behaviour impact.",
      "evidence": "Reading studio/server.py:1772-1779; FastAPI injects {} for an absent body under Body(default={}).",
      "fix": "Drop the or {} so the line reads body: dict = Body(default={})."
    }
  ],
  "usability": [
    {
      "where": "web/index.html:3382-3386",
      "what": "After pasting a bad new key, the user gets only the raw Zernio error and no confirmation the key was saved (it was), unlike the AI flow's 'Saved, but the test failed.' wording one screen away.",
      "fix": "Reuse the AI flow's two-part message and the try/catch around the test call."
    }
  ],
  "summary": "All five owned routes answered correctly over the wire with plain-language 400s and honest empty states; one important contract bug found (zernio.test() says ok:true with 0 accounts when no key is saved) plus two minor polish findings.",
  "checked": [
    "GET /api/overview (200, full shape, 14-day daily with real data)",
    "GET /api/overview?bogus=1 (200, param ignored)",
    "GET /api/zernio (200, has_key/key_hint last-4 only, 16 platforms, key never leaks)",
    "PUT /api/zernio bodies {} / {\"key\":\"\"} / {\"key\":\"   \"}-equivalent (200, keep saved key)",
    "PUT /api/zernio {\"key\":\"short\"} (400, own sentence, no write)",
    "PUT /api/zernio [1,2] (422 dict_type)",
    "POST /api/zernio/test {} with saved key (200, ok:true, 2 accounts, cached 0.009s)",
    "POST /api/zernio/test invalid key (400 'Zernio rejected the key…', real round-trip 0.33s)",
    "POST /api/zernio/test whitespace key (200, strips to saved key)",
    "zernio.test()/accounts()/saved() isolated with no key (ok:true accounts:0 bug reproduced; accounts(): [] honest)",
    "GET /api/zernio/accounts (200, 2 rows, zernio: ids, account_id stripped, followers:null)",
    "GET /api/zernio/accounts?refresh=true (200, fresh 0.57s)",
    "GET /api/zernio/accounts?refresh=notabool (422 bool_parsing)",
    "web/index.html consumer side: settings load :2626-2629, Zernio card :2660-2676, zsave/zforget/zrefresh :3379-3400, outer catch :3462, followers-null guard :2664",
    "web/feat consumers grepped: creators.js/day.js/grid.js use /api/overview; no feat file mentions zernio",
    "posting.py:255 _posts shadow reviewed (intentional, confined to overview())",
    "Mutating calls (valid-format key PUT, forget_key) deliberately not sent to protect the real saved key in data/zernio.json"
  ]
}
```
