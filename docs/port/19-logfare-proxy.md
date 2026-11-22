# 19 — Optional Logfare proxy for transcription

**The repository you asked me to read does not exist.** `https://github.com/tmugilan11-cmyk/logfare-proxy`
returns GitHub's 404 page, and `GET https://api.github.com/repos/tmugilan11-cmyk/logfare-proxy` returns
`{"message":"Not Found","status":"404"}`. The owner **does** exist (`tmugilan11-cmyk`, id 226133944,
created 2025-08-12) but has exactly one public repo, `simple-proxy` — a TypeScript/MIT HLS·m3u8 video
stream proxy with `m3u8-proxy.ts`, `ts-proxy.ts` and Turnstile. It has nothing to do with Logfare, audio,
or transcription, so it is not a stand-in.

A repo named `logfare-proxy` does exist under another owner: **`notBlubbll/logfare-proxy`** (the only hit
for a GitHub-wide search `q=logfare-proxy`). Sections 1–7 below document that repo as the closest real
match, and every claim in them is read from its actual source, not assumed. **Assumption A1:** the URL in
the brief was a typo for this repo. If it was not, only the generic guidance in §8 applies.

## 1. What it actually is

- **Language / deps:** one ES-module file, `index.js`, 2 112 lines / 102 281 bytes. No `package.json` in
  the tree, zero npm dependencies — imports only `node:http`, `node:https`, `node:crypto`, `node:fs`,
  `node:path`, `node:url`.
- **Two entry modes, same file.** Exports `export default { id: "logfare-proxy", async setup(ctx) }` for the
  OpenCode V2 plugin host, and runs standalone via `if (import.meta.main) { startServer(...) }`.
- **Port / bind:** `LISTEN_HOST = "127.0.0.1"` and `PORT_DEFAULT = 17330` (hard-coded). Loopback only, never
  exposed. On `EADDRINUSE` it retries binding every 5 s instead of exiting.
- **Routes it exposes** — only two are special-cased; everything else is proxied verbatim:
  | Route | Behaviour |
  |---|---|
  | `GET /healthz` | `200 text/plain` → `logfare-proxy OK` |
  | `GET /status` | `200 application/json` → `{active, streams, retries, attempts, model, updated, sessions}`, CORS `*`, `no-store` |
  | anything else | forwarded to `<upstream base><path+query>` |
- **What it forwards where:** target = upstream base (default `https://logfare.ai/v1`) concatenated with the
  inbound path *after stripping the base's own path prefix exactly once*. This exists because
  `baseURL http://127.0.0.1:17330/v1` + base `…/v1` previously produced `/v1/v1/…` and a 404 from Logfare.
  Method and body are preserved; the body is buffered so retries can replay it.
- **What it is for:** repairing and retrying **streaming SSE chat completions**. Its entire feature set —
  pre-commit buffering, post-commit continuation, `finish_reason` injection, null-field repair, DSML
  tool-call conversion, vision handoff — is chat-stream specific.

## 2. Configuration

No config file, no CLI flags. Environment only:

| Env var | Default | Meaning |
|---|---|---|
| `LOGFARE_PROXY_PORT` | `17330` | listen port (`127.0.0.1` only) |
| `LOGFARE_PROXY_UPSTREAM` | `https://logfare.ai/v1` | upstream base URL |
| `LOGFARE_PROXY_KEY` | — | **fallback** bearer, used only when the request carries no `authorization` |
| `LOGFARE_PROXY_DEBUG` | off | log every upstream chunk |
| `LOGFARE_PROXY_BUFFER` | `1` | buffer whole SSE before flush; `0` = stream |
| `LOGFARE_PROXY_NEVER_FORWARD` | `service temporarily unavailable` | JS regex of errors never shown to the client |
| `LOGFARE_PROXY_RL_BUDGET_MS` | `1500000` (25 min) | patient-retry wall-clock budget |
| `LOGFARE_PROXY_RL_BACKOFF_MS` | `5000,7000,10000,15000,20000,30000` | patient ladder |
| `LOGFARE_PROXY_BACKOFF_MS` | `300,600,1000,2000,3000` | hard-failure ladder |

Upstream base is overridable **per request** by the `x-lf-upstream` header (stripped before forwarding).
The API key is supplied by the caller (§4), or as `LOGFARE_PROXY_KEY`, or per request by `x-lf-key`.

## 3. Does it support `/v1/audio/transcriptions` multipart uploads?

**No audio-specific support exists.** Grepping all 2 112 lines for `audio`, `transcription`, `multipart`,
`form-data`, `formData` returns **zero hits**. It is a chat relay.

Structurally a multipart POST survives, via the generic non-stream branch:

- The request body is read with `req.on("data")` into an array and `Buffer.concat`ed with **no size cap
  whatsoever**. There is no `MAX_BODY`, no `413` of its own. (It does buffer the whole upload in RAM.)
- The JSON parse is wrapped in a bare `try {} catch {}`, so a multipart body simply leaves `reqJson = null`,
  `wantsStream = false`, `model = "?"` — it does not throw.
- `wantsStream === false` takes the passthrough branch: `res.writeHead(lastStatus, pickResponseHeaders(...))`
  then raw chunk copy. Status and bytes are preserved.
- `buildForwardHeaders` strips `host, connection, content-length, accept-encoding, expect, keep-alive,
  transfer-encoding, upgrade, proxy-connection, x-lf-key, x-lf-upstream` — **`content-type` is not stripped**,
  so the multipart boundary is forwarded intact, and `content-length` is recomputed from the buffered byte
  count (identical to what was received).

**What would actually break it:** size/rate-limit class errors are *patient-retried, not failed fast*.
`413` and any body matching `PATIENT_SIZE_RE` (`exceeds the maximum supported size`, `8006`, `payload too
large`) are retried with the same body on a 5/7/10/15/20/30 s ladder for up to **25 minutes** by default.
If Logfare rejects an oversized or malformed audio upload that way, the caller sees a hang, not an error —
the single most important caveat here. `ATTEMPT_TIMEOUT_MS` is 30 min and `FIRST_BYTE_MS` 2 min, both far
longer than a sane transcription timeout, so the caller's own timeout fires first.

## 4. Auth, both directions

- **The client keeps sending its Bearer key.** `authorization` is not on the strip list; line 1028 reads
  `req.headers["authorization"]` and forwards it unchanged. The README is explicit: the proxy stores no
  credentials and forwards whatever `Authorization` the client sends.
- **The proxy does not inject its own key.** `LOGFARE_PROXY_KEY` is a *fallback only*, applied solely when
  the inbound request has no `authorization` header.
- `x-lf-key` overrides the inbound bearer per request; `x-lf-upstream` overrides the base; both are stripped
  before forwarding.
- **There is no proxy-side shared secret and no inbound auth of any kind.** Anyone who can open
  `127.0.0.1:17330` can spend the key it forwards. The loopback bind is the entire security model.

## 5. Run it locally

```sh
# no install step: zero dependencies, no package.json
node index.js                  # verified on Node v24.22.2 (import.meta.main supported)
# or: bun index.js

curl http://127.0.0.1:17330/healthz     # -> logfare-proxy OK
```

Default port **17330**, bound to `127.0.0.1`. Optional: `LOGFARE_PROXY_UPSTREAM=… LOGFARE_PROXY_PORT=…`.
`bun test/run-tests.mjs` runs 67 scenarios — **but bun is not installed on this machine**, and the suite
covers only the chat-stream paths, so it would prove nothing about transcription anyway.

**Assumption A2:** Node ≥ 22 is required for `import.meta.main`; on Node 20 the standalone block would never
fire and the process would exit silently. Verified working on v24.22.2.

## 6. What a caller must change

**Only the base URL.** Path, method, multipart body and `Authorization` header stay byte-identical:

```
https://logfare.ai/v1/audio/transcriptions   →   http://127.0.0.1:17330/v1/audio/transcriptions
```

The `/v1` must be kept on the caller's side — the proxy strips the *base's* prefix, so pointing at
`http://127.0.0.1:17330` without `/v1` would send `/audio/transcriptions` upstream and 404.

In PeakCut the whole surface is four sites, one of them a definition:

- `peakcut/studio/transcribe.py:43` — `LOGFARE_BASE_URL = "https://logfare.ai/v1"`
- `peakcut/studio/transcribe.py:128` — `f"{LOGFARE_BASE_URL}/audio/transcriptions"`
- `peakcut/studio/server.py:1435` — `f"{tr_mod.LOGFARE_BASE_URL}/models"`
- `peakcut/studio/server.py:1463` — `f"{transcribe.LOGFARE_BASE_URL}/audio/transcriptions"`

## 7. Health signals — is it maintained?

| Signal | Value |
|---|---|
| Stars / forks / watchers | **0 / 0 / 0** |
| Open issues / PRs | 0 / 0 |
| Created | 2026-10-30 |
| Last push | 2026-11-15 (4 days before this review) |
| Commit shape | ~10 commits, all inside one evening (17:01→19:34), revisions 2.17→2.26 |
| Licence | **none** — no `LICENSE` file. All rights reserved by default. (The owner's *other* repo is MIT; this one is not.) |
| CI / releases / package.json | none |

**Verdict: a thin personal script.** Single author, ~two weeks old, zero adoption, no licence, no versioning
contract, no audio path, and rapid unreviewed churn. It should not become a dependency of PeakCut.

## 8. What PeakCut would need (spec)

Because §3 shows the real proxy has no transcription path and §7 shows it is unmaintained and unlicensed,
the recommended implementation is the **toggle only**, with a proxy URL the operator supplies — working
against this repo by luck of its generic passthrough, or against any equivalent relay.

**Config** (`studio/config.py`, beside the existing block at 200–204):

```python
LOGFARE_PROXY_ENABLED = env("PEAKCUT_LOGFARE_PROXY", "").strip().lower() in ("1", "true", "on", "yes")
LOGFARE_PROXY_URL = env("PEAKCUT_LOGFARE_PROXY_URL", "http://127.0.0.1:17330/v1").rstrip("/")

def logfare_base_url() -> str:
    """The Logfare base URL: through the local proxy when the toggle is on, else direct."""
    return LOGFARE_PROXY_URL if LOGFARE_PROXY_ENABLED else "https://logfare.ai/v1"
```

`transcribe.LOGFARE_BASE_URL` becomes a module global refreshed from `config.logfare_base_url()` at boot and
whenever settings save — exactly how `LOGFARE_KEY` / `LOGFARE_MODEL` are already pushed at
`server.py:1415–1419`.

**Settings toggle.** `tr.json` already holds `{provider, model, key}`. Add `"proxy": bool`:
`_tr_saved()` gains the key with a default from env; `_tr_public()` exposes it plus a `ready` term; the
`PUT /api/transcribe` handler validates it as a bool and pushes it into `transcribe`/`config` alongside the
key. UI: one checkbox under Settings → Transcription, shown only when provider is `logfare`.

**Scope containment — "only Logfare traffic".** This is satisfied structurally, not by filtering:
`LOGFARE_BASE_URL` is read only at the three sites in §6. `AI_BASE_URL` (`config.py:198`) is a separate
constant feeding `studio/ai.py`, and the toggle must not touch it. A test should assert that with the toggle
on, `ai` request URLs are unchanged.

**Do not** send `x-lf-key` or `x-lf-upstream`: PeakCut already sends `Authorization: Bearer <key>` at
`transcribe.py:125`, which the proxy forwards verbatim. Leave auth alone.

**Risks to encode in the UI, not just the docs:**

1. A `413`/`8006` rejection is retried for up to 25 minutes — surface a "proxy may be retrying" hint, and
   keep PeakCut's `httpx.Timeout(120, connect=10)` as the hard stop.
2. `ready` currently means "provider is local, or logfare with a key". With the toggle on it must also mean
   "proxy answered `/healthz`" — probe it on save, exactly as `server.py:1435` already probes `/models`.
3. No licence, no audio support, zero stars: default the toggle **off** and label it experimental.

**Tests** (`tests/test_transcribe_logfare.py`, the settings-block pattern already referenced by
`docs/port/03-chat-spikes.md:738`): toggle off → direct URL; toggle on → proxy URL; `/audio/transcriptions`
path unchanged in both; non-Logfare URLs unchanged in both; `tr.json` round-trips the new key; a hand-edited
`tr.json` with a non-bool `proxy` degrades to `False` rather than raising (mirroring the existing
`provider` coercion at `server.py:1363`).

## 9. Assumptions, listed

- **A1** — the brief's URL was a typo for `notBlubbll/logfare-proxy`; all of §1–7 describes that repo.
- **A2** — Node ≥ 22 is needed for `import.meta.main`; verified on Node v24.22.2.
- **A3** — a proxy instance is reachable at `127.0.0.1:17330`; nothing starts it for PeakCut.
- **A4** — Logfare's endpoint is `POST /v1/audio/transcriptions` with a multipart `file` field, matching what `transcribe.py:127–133` already sends.
- **A5** — recomputing `content-length` is safe for multipart because PeakCut sends a buffered `io.BytesIO` body, never a chunked upload.
- **A6** — no audio handling exists in the proxy, so §3 is an inference from the generic passthrough, not a tested run.
