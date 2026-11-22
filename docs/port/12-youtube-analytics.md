# 12 — YouTube analytics for a published Short

## 1. What it does

Once a clip has been posted to YouTube, the user opens it and asks "how is this doing, and why not better". PeakCut reads the video's public statistics (views, likes, comments, duration) from the YouTube Data API, compares them against the channel's own recent Shorts, and — when the user has signed in with Google — adds the private Analytics numbers: average view percentage, average view duration, subscribers gained, and how much of the audience is still watching at second 3. A fixed rule set then turns those numbers into a ranked list of plain-English findings ("like rate 1.4%, typical Shorts 3-6%", "only 61% are still watching at second 3", "title is 74 characters, the feed cuts it off") plus a one-line verdict on whether the clip is too new to judge. Optionally the findings are handed to the AI service to produce five replacement titles, three on-screen hooks and one re-cut idea. Everything is read-only against the user's own channel: no writing, no other channel's data, no third-party service.

## 2. Exact mechanics

Source: `gta6-clipper-main/ytstats.py` (283 lines). Everything below is the real algorithm; a build agent should not need that file open afterwards.

### 2.1 Endpoints and scopes

`ytstats.py:9-10`:

```python
DATA, ANA = "https://www.googleapis.com/youtube/v3", "https://youtubeanalytics.googleapis.com/v2/reports"
SCOPES = "https://www.googleapis.com/auth/yt-analytics.readonly https://www.googleapis.com/auth/youtube.readonly"
```

Two distinct APIs are in play and they authorise differently:

| Call | Base | Auth |
|---|---|---|
| `videos`, `channels`, `playlistItems` | `DATA` | API key as `key=` query param, **or** an OAuth bearer token |
| `reports` (retention, average view %) | `ANA` | OAuth bearer token only — an API key cannot reach it |

`deep()` is the only caller of `ANA`, and it is the only path that needs the `yt-analytics.readonly` scope.

### 2.2 HTTP wrapper, `ytstats.py:15-24`

```python
def http(url, headers=None, data=None):
    if _get and data is None: return _get(url, headers or {})
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=20) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "ignore")[:300]
        try: msg = json.loads(msg)["error"]["message"]
        except Exception: pass
        raise RuntimeError(f"YouTube said {e.code}: {msg}")
```

Load-bearing details:

- **Timeout is 20 s** on every call, including the Analytics report.
- `data` (a dict) makes it a **POST with `application/x-www-form-urlencoded`**; that is only used for the two OAuth token exchanges. Every read is a GET.
- Failures are re-raised as `RuntimeError("YouTube said {code}: {message}")`, with the Google error body unwrapped to its `error.message` and truncated to 300 chars. **One exception type for every upstream failure** — the route layer maps it to 502 wholesale (see 2.10).
- `_get` (`ytstats.py:12`) is a module-global test hook that replaces the HTTP GET entirely. The selftest swaps it for a fake. **This is the seam a pytest suite should reuse**; it is the only reason the module is testable without network.

### 2.3 Parsing helpers

`vid_id(s)` — `ytstats.py:27-29`:

```python
m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([\w-]{11})", s or "") or re.fullmatch(r"([\w-]{11})", (s or "").strip())
return m.group(1) if m else None
```

Accepts a full watch URL, a `youtu.be` short link, a `/shorts/` link, an `/embed/` link, or the bare 11-character id. Returns `None` for anything else. The `[\w-]{11}` class is what makes it a valid id: 11 characters of `[A-Za-z0-9_-]`.

`dur(iso)` — `ytstats.py:32-35`: parses an ISO-8601 duration with only the `PT` form:

```python
m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
h, mi, s = (int(x or 0) for x in m.groups()) if m else (0, 0, 0)
return h * 3600 + mi * 60 + s
```

No days component, no fractional seconds; a non-match yields `0`.

`norm(it)` — `ytstats.py:41-44` — flattens one API video object into the internal shape every other function uses:

```python
return dict(id=it["id"], title=s["title"], published=s["publishedAt"],
            seconds=dur(it.get("contentDetails", {}).get("duration")),
            views=int(st.get("viewCount", 0)), likes=int(st.get("likeCount", 0)),
            comments=int(st.get("commentCount", 0)))
```

Missing statistics default to `0` (`int(...)` on `None` is guarded by `.get(..., 0)`; note `likeCount` is genuinely absent on videos with likes hidden, in which case it reads `0` and the like-rate rule silently stops firing).

### 2.4 Data API calls

`data_api(path, key, **p)` — `ytstats.py:38` — is just `http(f"{DATA}/{path}?" + urlencode(dict(p, key=key)))`.

`videos(key, ids)` — `ytstats.py:47-51`: **chunks ids by 50** (the Data API maximum), `part="snippet,statistics,contentDetails"`, concatenates `norm()` over `items`. Returns a list.

`channel_id(key, ch)` — `ytstats.py:54-58`:

```python
if re.fullmatch(r"UC[\w-]{22}", ch or ""): return ch
r = data_api("channels", key, part="id", forHandle=(ch or "").lstrip("@")).get("items")
if not r: raise RuntimeError("channel not found: use the UC... id or the @handle")
return r[0]["id"]
```

A raw `UC…` id (24 chars total: `UC` + 22) is passed through without a network call; otherwise the value is treated as a handle with any leading `@` stripped and resolved via `forHandle`.

`latest_shorts(key, ch, n=20)` — `ytstats.py:61-64`:

```python
up = "UU" + channel_id(key, ch)[2:]
ids = [i["contentDetails"]["videoId"] for i in data_api("playlistItems", key, part="contentDetails", playlistId=up, maxResults=50).get("items", [])]
return [v for v in videos(key, ids) if 0 < v["seconds"] <= 180][:n]
```

The uploads playlist id is derived by swapping the channel's `UC` prefix for `UU` — this is how YouTube exposes every upload without a search quota. One page of 50, then filtered to **Shorts, defined here purely as `0 < seconds <= 180`**, then truncated to `n`. This "Shorts" definition is the module's own convention, not an API fact.

### 2.5 OAuth: the user's own desktop client, loopback flow

This is the part that does **not** survive a port unchanged; PeakCut already has a different, better flow (see §3 and §6).

`tok_path(ws)` — `ytstats.py:68` — `Path(ws) / "yt" / "token.json"`.

`check_client(c)` — `ytstats.py:71-76` — a security check that must be preserved in spirit. The uploaded OAuth client JSON is normalised through `c.get("installed") or c.get("web") or c`, then both URIs are validated:

```python
for k, host in (("auth_uri", "accounts.google.com"), ("token_uri", "oauth2.googleapis.com")):
    u = urllib.parse.urlparse(str(c.get(k) or ""))
    if u.scheme != "https" or u.hostname != host or u.port not in (None, 443) or u.username:
        raise ValueError(f"OAuth client JSON rejected: {k} must be https://{host}/...")
```

The rationale is in the comment at `ytstats.py:71`: **the authorisation code and the `client_secret` are POSTed to `token_uri`**, so a hostile client JSON would exfiltrate both. Rejecting a non-`https` scheme, a wrong host, a non-default port and any embedded username closes the obvious redirects (`https://oauth2.googleapis.com.evil.io/t`, `https://x@evil.io/t`, `http://…`). A port must be absent or exactly 443 — a suffix-match bug (`hostname.endswith("googleapis.com")`) would have accepted `evil-googleapis.com`.

`oauth_start(ws, client_json)` — `ytstats.py:77-95` — starts a throwaway `HTTPServer` on `("127.0.0.1", 0)` (ephemeral port), computes `redirect_uri = f"http://127.0.0.1:{srv.server_port}"`, generates `state = secrets.token_urlsafe(16)`, and returns the consent URL:

```python
return c["auth_uri"] + "?" + urllib.parse.urlencode(dict(
    client_id=c["client_id"], redirect_uri=box["redir"], response_type="code",
    scope=SCOPES, access_type="offline", prompt="consent", state=box["state"]))
```

- `access_type="offline"` + `prompt="consent"` is what guarantees a **refresh token** is issued.
- The callback handler accepts only `state == box["state"]` **and** a present `code`; anything else answers `200` with `"Wrong or missing code."` and still shuts the server down.
- On success it POSTs `code`, `client_id`, `client_secret`, `redirect_uri`, `grant_type="authorization_code"` to `token_uri`, stamps `t["at"] = time.time()`, and writes `token.json`.
- A `threading.Timer(300, srv.shutdown)` bounds the wait to **5 minutes**.
- `log_message` is silenced so the terminal stays clean.

`access_token(ws)` — `ytstats.py:98-106`:

```python
tp, cp = tok_path(ws), Path(ws) / "yt" / "client.json"
if not tp.exists() or not cp.exists(): return None
t = json.loads(tp.read_text()); c = check_client(json.loads(cp.read_text()))
if time.time() - t.get("at", 0) > t.get("expires_in", 0) - 60:
    if not t.get("refresh_token"): return None
    t.update(http(c["token_uri"], data=dict(client_id=c["client_id"], client_secret=c["client_secret"],
             refresh_token=t["refresh_token"], grant_type="refresh_token")), at=time.time())
    tp.write_text(json.dumps(t))
return t["access_token"]
```

The expiry test is **`age > expires_in - 60`** — a hard-coded 60-second safety margin, not a stored absolute deadline. **`expires_in` is only present on a fresh token exchange; a token written by the refresh path above keeps the old `expires_in` and gains a new `at`, which is consistent.** Note the refresh response's own `expires_in` would be merged in by `t.update(...)` — it is, because the response body is a dict merged into `t`. Returns `None` (never raises) when not signed in, which is what makes `deep()` degrade quietly.

### 2.6 The Analytics report call

`analytics(tok, start, end, metrics, dims=None, filters=None, sort=None, n=None)` — `ytstats.py:109-115`:

```python
p = dict(ids="channel==MINE", startDate=start, endDate=end, metrics=metrics)
for k, v in (("dimensions", dims), ("filters", filters), ("sort", sort), ("maxResults", n)):
    if v: p[k] = v
r = http(ANA + "?" + urllib.parse.urlencode(p), {"Authorization": "Bearer " + tok})
cols = [h["name"] for h in r.get("columnHeaders", [])]
return [dict(zip(cols, row)) for row in r.get("rows", [])]
```

- **`ids="channel==MINE"`** — the report is always the signed-in account's own channel. There is no channel-id parameter anywhere in this module, which is exactly the property the port must keep.
- Optional params are omitted when falsy, so `maxResults=0` and `sort=""` never travel.
- The reply is column-oriented (`columnHeaders` + positional `rows`); it is zipped into a list of dicts keyed by header name. No `rows` → `[]`, which every caller treats as "no data yet" rather than an error.

### 2.7 `deep()` — the per-video analytics bundle, `ytstats.py:118-132`

Returns `{}` when not signed in or when every call failed. Otherwise:

```python
s, e = v["published"][:10], datetime.now(timezone.utc).strftime("%Y-%m-%d")
M = "views,averageViewDuration,averageViewPercentage,subscribersGained"
r = analytics(tok, s, e, M, filters="video==" + v["id"])
if r: out.update(r[0])
rt = analytics(tok, s, e, "audienceWatchRatio", dims="elapsedVideoTimeRatio", filters="video==" + v["id"])
if rt and v["seconds"]: out["kept_at_3s"] = min(rt, key=lambda x: abs(x["elapsedVideoTimeRatio"] - 3 / v["seconds"]))["audienceWatchRatio"]
st = datetime.fromordinal(datetime.now(timezone.utc).date().toordinal() - 90).strftime("%Y-%m-%d")
rows = analytics(tok, st, e, M, dims="video", sort="-views", n=20)
if rows: out["median"] = {k: statistics.median(x[k] for x in rows) for k in ("averageViewDuration", "averageViewPercentage", "subscribersGained")}
```

Three separate reports, all wrapped in one `try` whose `except Exception` writes `out["error"] = str(ex)[:200]`:

1. **This video, lifetime.** `startDate` is the first 10 characters of the video's `publishedAt` (`"2026-11-01T14:22:31Z"` → `"2026-11-01"`), `endDate` is today in UTC. Metrics: `views,averageViewDuration,averageViewPercentage,subscribersGained`. Filter `video==<id>`. One row; merged into the result. Note `views` from Analytics will differ slightly from the Data API's `viewCount` (Analytics lags and counts differently) — both are kept, under the same key `views`, with Analytics winning because it is applied later.
2. **Retention curve.** Metrics `audienceWatchRatio`, dimension `elapsedVideoTimeRatio`, same filter. The API returns the curve as **fractions of total duration** (0.0 → 1.0), not seconds. The "kept at 3 s" point is found by nearest-neighbour: `min(rows, key=|elapsedVideoTimeRatio - 3/seconds|)`. So for a 30 s Short it picks the row closest to `0.1`, and for a 180 s Short the row closest to `0.0167`. **`kept_at_3s` is therefore only ever an approximation** — the curve's resolution is decided by YouTube. Guarded by `if rt and v["seconds"]`, so a zero duration cannot divide by zero.
3. **Channel median over 90 days.** Start = today minus 90 days computed via `datetime.fromordinal(date.toordinal() - 90)` (avoids `timedelta` import). Metrics `M`, dimension `video`, `sort="-views"`, `maxResults=20`. The median is computed over `averageViewDuration`, `averageViewPercentage`, `subscribersGained` — **not** over `views` (views get their median from the Data API side instead; see 2.9). `statistics.median` of a 20-row set averages the 10th and 11th values.

The whole bundle is best-effort: a signed-in user with a brand-new unlisted video gets `{}` plus possibly an `error` key, and every downstream rule simply finds `None` and stays silent.

### 2.8 `diagnose()` — the rule engine, `ytstats.py:139-161`

Signature: `diagnose(v, others=(), deep_=None, hook="")`. `others` is the channel's `latest_shorts` list; `deep_` is the `deep()` dict; `hook` is the on-screen hook text.

Setup: `peers = [o for o in others if o["id"] != v["id"]]`, `mv = statistics.median(o["views"] for o in peers) if peers else None`, `a = age_h(v)` where `age_h` (`ytstats.py:136`) is `max(1, hours since published)` — so a just-published video reports 1 h, never 0.

Every rule appends `dict(key=…, level=…, text=…)` where `level` is one of `"bad"`, `"warn"`, `"info"`. The complete table:

| # | key | level | condition | threshold / constant |
|---|---|---|---|---|
| 1 | `views` | `bad` | `mv is not None and a >= 24 and v["views"] < 0.5 * mv` | **< 50 % of the peers' median views, after 24 h** |
| 1b | `views` | `info` | `a < 24` (the `elif` of the above) | **under 24 h old → do not judge yet** |
| 2 | `likes` | `warn` | `v["views"] >= 50 and v["likes"] / v["views"] < 0.02` | **like rate < 2 % on ≥ 50 views** (text cites "typical Shorts 3-6 %") |
| 3 | `avp` | `bad` | `avp is not None and (avp < 60 or (med and avp < 0.8 * med))` | **average viewed < 60 %**, or **< 80 % of the user's own median** |
| 4 | `hook3` | `bad` | `k3 is not None and k3 < 0.7` | **< 70 % still watching at second 3** |
| 5 | `title_len` | `warn` | `len(t) > 60` | **title longer than 60 characters** |
| 6 | `verb` | `warn` | `w and w[0].lower() not in VERBS` | first word not in the verb list |
| 7 | `name` | `warn` | `not any(x[0].isupper() or x.isdigit() for x in w[1:])` | no capitalised word and no digit after the first |
| 8 | `mismatch` | `warn` | `hw and tw and len(hw & tw) / len(hw \| tw) < 0.1` | **Jaccard overlap of 4+ letter words < 0.10** |
| 9 | `hour` | `info` | `len(peers) >= 6 and hr(v) not in hs` | needs ≥ 6 peers; "best hours" = posting hours of the **top `len(peers)//3`** by views |

Rule-by-rule detail the table cannot hold:

- **Rule 3** reads `deep_.get("averageViewPercentage")` and `(deep_.get("median") or {}).get("averageViewPercentage")`. Either branch alone fires it; `med` being `0` is falsy and disables the relative branch.
- **Rules 5-8** operate on `t = v["title"]`: `w = re.findall(r"[\w']+", t)` (words including apostrophes). Rule 7 skips index 0, i.e. the verb from rule 6.
- **Rule 8** builds `hw = {x.lower() for x in re.findall(r"\w{4,}", hook)}` and `tw` the same over the title — **only words of 4 or more characters count**, so short hooks produce an empty `hw` and the rule is skipped entirely (`if hw and tw`). This is deliberate: a two-letter hook carries no meaning to compare.
- **Rule 9** computes `hr(o) = datetime.fromisoformat(o["published"].replace("Z", "+00:00")).hour` — the **UTC** hour, stated as such in the message text ("Posted at 14:00 UTC").
- **Rule 1 vs 1b** are an `if/elif`, so an old low-view video never also gets the "too new" note.

Return value (`ytstats.py:161`):

```python
return dict(reasons=R, median_views=mv, age_hours=round(a, 1),
            level="analytics" if deep_.get("averageViewPercentage") is not None else "key")
```

`level` is the UI's capability badge: `"analytics"` means the private numbers arrived, `"key"` means only the public Data API numbers are available. **The report is never empty-by-error** — `reasons` may legitimately be `[]`.

### 2.9 The route layer, `ytstats.py:192-235`

`handle(method, path, query, body, ws, env, save_env) -> (status, dict)`. `P = path.rstrip("/")`.

| Method | Path | Behaviour |
|---|---|---|
| GET | `/api/yt/status` | `{has_key, channel, has_oauth, signed_in, network}` — booleans only, never the key |
| POST | `/api/yt/key` | validates and saves `api_key` + `channel` |
| POST | `/api/yt/oauth` | stores the client JSON, returns `{ok, auth_url}` |
| POST | `/api/yt/link` | binds `run|file` → a video id |
| GET | `/api/yt/channel` | `{shorts: latest_shorts(...)}` |
| GET | `/api/yt/stats`, `/api/yt/diagnose` | the report; `diagnose` adds the rule output |

Details that matter:

- **Key validation** (`ytstats.py:203-205`): `re.fullmatch(r"[\w-]{20,60}", k)` then a **real cheap read** — `data_api("videos", k, part="id", id="dQw4w9WgXcQ")` — so a syntactically valid but wrong key is caught at save time rather than on first use. `dQw4w9WgXcQ` is a well-known always-public video used purely as a liveness probe.
- **`POST /api/yt/oauth`** accepts either a JSON string or an already-parsed object (`json.loads(cj) if isinstance(cj, str) else cj`), requires `installed` or `web`, runs `check_client`, then calls `oauth_start` and returns the URL for the browser to open.
- **Not-signed-in** short-circuit at `ytstats.py:214`: `if not key: return 400, dict(error="Add your YouTube API key in Settings first.")` — this sits **after** the key/oauth routes so those still work.
- **Auto-link** in `_find` (`ytstats.py:183-189`): an explicit link wins; otherwise, if a `.txt` sits beside the clip with a first line, and a channel is configured, it scans `latest_shorts(..., 20)` for a **case-insensitive, whitespace-stripped exact title match** and persists the match to `links.json`. This is the single-user convenience that must be replaced by an explicit `remote_id` in the port.
- **Stats assembly** (`ytstats.py:228-232`):
  ```python
  d = deep(ws, v); med = dict(d.get("median") or {})
  if others: med.update(views=statistics.median(o["views"] for o in others),
                        likes=statistics.median(o["likes"] for o in others))
  out = dict(linked=True, id=vi, video=v, median=med,
             analytics={k: x for k, x in d.items() if k != "median"}, title=_title(...))
  ```
  So the **public** medians (`views`, `likes`, computed from up to 20 recent Shorts) and the **private** medians (`averageViewDuration`, `averageViewPercentage`, `subscribersGained`, from the 90-day Analytics report) are merged into one `median` dict, and `median` itself is stripped out of the `analytics` sub-object.
- **Error mapping** (`ytstats.py:233-235`): `RuntimeError → 502`, `(KeyError, ValueError) → 400` with `"bad request: {ex}"`, else `404 {"error": "unknown route"}`. Note the module returns tuples and lets the caller `send()`; it never raises HTTP errors itself.

### 2.10 The AI follow-up prompt, `ytstats.py:164-169`

Exact text, because the schema is the contract:

```
A YouTube Short about GTA 6 is underperforming. Give fresh packaging.
Current title: {v['title']}
On-screen hook: {hook or '(none)'}
Stats: {v['views']} views, {v['likes']} likes, {v['comments']} comments, {v['seconds']} s, posted {v['published']}
Problems found:
- {each reason text}

Transcript of the Short:
{transcript[:3000]}

Return ONLY JSON: {"titles":[5 titles, each starts with a verb, under 60 chars, contains a name or number],
"hooks":[3 on-screen hooks, max 7 words, same promise the clip delivers],
"recut":"one idea to re-cut the clip (where to start, what to remove)"}
```

The transcript is capped at **3000 characters**, the findings are passed as bullet lines, and the three output keys are `titles` (exactly 5), `hooks` (exactly 3) and `recut` (one string). The GTA 6 wording is the only game-specific string in the module and must become the job's actual subject in the port.

## 3. PeakCut today

More of this feature already exists than the inventory suggests. **A naive port would duplicate a working OAuth stack and fail at the Analytics API.**

**Already present — reuse, do not rebuild:**

| What | Where | Note |
|---|---|---|
| YouTube OAuth (web redirect, not loopback) | `peakcut/studio/accounts.py:178-182` `_youtube_finish` / `connect_start` | `redirect_for("youtube")` = `f"{config.PUBLIC_URL}/oauth/youtube/callback"` (`accounts.py:112`) |
| Token refresh + persistence | `peakcut/studio/accounts.py:328-338` `_yt_token(acc)` | uses an absolute `acc["expires"]` deadline, refreshes via `_put(acc)`; **sharper than the source's `expires_in - 60` age test** |
| Per-user account storage | `peakcut/studio/accounts.py:38-66` `_dir()`/`_read`/`_write` | `config.user_dir(ctx.uid())/accounts/accounts.json`, `chmod 0o600` at `accounts.py:60` |
| View counts | `peakcut/studio/accounts.py:358-366` `youtube_views(acc, ids) -> dict` | **`part="statistics"` only** — viewCount, nothing else |
| Channel identity | `peakcut/studio/accounts.py:316-321` | `acc["id"] = f"yt_{item['id']}"`, `name = snippet.title`; the `UC…` id is recoverable as `acc["id"][3:]` |
| Stats polling loop | `peakcut/studio/posting.py:161-186` `_stats_for` / `_stats()` | every **1800 s**, only posts younger than **14 days** (`posting.py:182`) |
| Post record holding the video id | `peakcut/studio/posting.py:79-82` | `remote_id`, `url`, `views`, `job`, `clip`, `account`, `creator` |
| Aggregated views + earnings | `peakcut/studio/posting.py:209-227` `overview()` | `earnings = round(views / 1000 * c["rate_per_1k"], 2)`; `rate_per_1k` is `creators.py:23` |
| Settings file pattern | `peakcut/studio/server.py:1324-1347` `_tr_saved`/`_tr_public` | file-over-env merge, `key_hint` = last 4 chars when `len >= 12` |
| Route gate + throttle | `peakcut/studio/server.py:310` `_admin`, `633` `_throttle` | `_admin` raises `404`, not 403 |
| Status surface | `peakcut/studio/server.py:581-589` | already exposes `"youtube": accounts.youtube_ready()` and per-platform `connect` |

**The gaps, precisely:**

1. **No Analytics scope.** `accounts.py:29` is `YT_SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"`. The `yt-analytics.readonly` scope is absent, so **every call to `ANA` returns 403 for an existing user**. Because tokens are already stored, adding the scope requires a re-consent — see §6.
2. **No Analytics API client at all.** Nothing in `peakcut/studio/` references `youtubeanalytics.googleapis.com`; `youtube_views` stops at `part="statistics"`.
3. **No retention, average-view or subscriber numbers.** `averageViewPercentage`, `averageViewDuration`, `subscribersGained` and `audienceWatchRatio` appear nowhere.
4. **No rule engine, no findings, no AI re-packaging.** `brain.py`'s `describe()` (`brain.py:336`) writes a hook/title *for a new clip*; nothing reads a published video's performance.
5. **No per-video report surface.** `overview()` aggregates `views` per creator for a 14-day graph; there is no drill-down on one `remote_id`.
6. **No `@handle` / channel-id setting.** `channel_id` resolution from §2.4 has no equivalent; PeakCut gets the channel implicitly at connect time.

## 4. Port plan

### 4.1 New module: `peakcut/studio/ytstats.py`

The name collides with the source file but lives in a different package and follows PeakCut's module-per-concern rule from the brief. It imports `httpx` (already a dependency, `requirements.txt:2`) — **no new dependency, no `google-api-python-client`**, matching the source's stdlib-only posture.

Module docstring must state: read-only, own channel only, no key required when an account is connected.

### 4.2 Public API

```python
DATA = "https://www.googleapis.com/youtube/v3"
ANA = "https://youtubeanalytics.googleapis.com/v2/reports"
SHORTS_MAX_S = 180
_PEER_WINDOW = 20          # latest_shorts(n)
_MEDIAN_DAYS = 90          # Analytics median window
_MEDIAN_ROWS = 20          # maxResults for the 90-day report
_HOOK_AT_S = 3.0           # the retention probe point
```

```python
def video_id(s: str) -> str | None:
    """11-char YouTube id from a watch/shorts/embed/youtu.be URL, or the bare id itself."""

def duration_s(iso: str) -> int:
    """Seconds from an ISO-8601 'PT#H#M#S' duration; 0 when unparseable."""

def _get(path: str, params: dict, token: str | None = None, key: str | None = None,
         base: str = DATA) -> dict:
    """One authenticated GET. Raises YouTubeError on a non-2xx reply."""

class YouTubeError(RuntimeError):
    """Upstream failure, already phrased for the user."""

def videos(acc: dict, ids: list[str]) -> list[dict]:
    """Public stats for up to 50 ids per call. Each: {id, title, published, seconds,
    views, likes, comments}. Missing ids are simply absent."""

def channel_of(acc: dict) -> str:
    """The UC... channel id, taken from acc['id'] ('yt_' + UC...) without a network call."""

def latest_shorts(acc: dict, n: int = _PEER_WINDOW) -> list[dict]:
    """The channel's own uploads, filtered to 0 < seconds <= 180, newest first, at most n."""

def analytics(token: str, start: str, end: str, metrics: str, dimensions: str = "",
              filters: str = "", sort: str = "", max_results: int = 0) -> list[dict]:
    """One YouTube Analytics report for ids='channel==MINE'. Rows as dicts keyed by
    columnHeaders. Empty list when the report has no rows yet."""

def deep_video(acc: dict, v: dict) -> dict:
    """The private bundle for one video, or {} when the account has no analytics scope.
    Keys when present: views, averageViewDuration, averageViewPercentage,
    subscribersGained, kept_at_3s, median{averageViewDuration, averageViewPercentage,
    subscribersGained}, error. Never raises."""

def diagnose(v: dict, peers: list[dict], deep: dict | None = None,
             hook: str = "") -> dict:
    """The rule engine. Returns {reasons: [{key, level, text}], median_views,
    age_hours, level: 'analytics'|'key'}. Pure — no network, no I/O."""

def report(acc: dict, vid: str, hook: str = "", peers: int = _PEER_WINDOW) -> dict:
    """The whole answer for one published video: link -> video -> peers -> deep -> diagnose."""

def ai_prompt(v: dict, reasons: list[dict], subject: str, transcript: str = "",
              hook: str = "") -> str:
    """The re-packaging prompt, with the game/streamer name substituted for 'GTA 6'."""
```

`report()` is the one function the HTTP layer calls. Its return shape:

```python
{
  "id": "dQw4w9WgXcQ",
  "video": {id, title, published, seconds, views, likes, comments},
  "median": {"views": …, "likes": …, "averageViewDuration": …,    # private keys only
             "averageViewPercentage": …, "subscribersGained": …}, # when signed in
  "analytics": {views, averageViewDuration, averageViewPercentage, subscribersGained,
                kept_at_3s, error?},   # median stripped out, as in ytstats.py:230
  "reasons": [ {key, level, text}, … ],
  "age_hours": 26.4,
  "level": "analytics" | "key",
}
```

### 4.3 What it calls, and what calls it

**`ytstats.py` must call:**

- `accounts._yt_token(acc)` (`accounts.py:328`) for every authenticated request — never build a second token cache.
- `accounts.get(aid)` (`accounts.py:278`) to load the account dict by id.

**`ytstats.py` must be called by:**

- **`server.py`** — a new block modelled on the transcription routes (`server.py:1324-1447`):
  ```python
  @app.get("/api/yt/report")                      # ?post=<pid>  (defaults to the newest posted post)
  def yt_report(request: Request): _admin(request); _throttle("ytrep:" + ctx.uid(), 30, 600)
  ```
  Gate with `_admin` only if the report should be admin-only; a creator's own numbers are theirs, so the correct gate is **the post's owner** — check `p["user"] == ctx.uid()` and raise `HTTPException(404)` otherwise, following `_admin`'s "not found" convention at `server.py:314`.
  Map `YouTubeError → HTTPException(502, safe.friendly(e, 160))`, `ValueError → HTTPException(400, …)`.
- **`posting.py:161` `_stats_for()`** — extend it to also store `averageViewPercentage` / `kept_at_3s` on the post, so `overview()` can show them without a live call. Keep the existing `views` write intact.
- **`web/index.html`** — a "Performance" section on the clip card; see 4.5.

**Do not** put a polling loop inside `ytstats.py`. The existing cadence (`posting.py:177-186`, 1800 s, ≤14 days old) is the right place for background refresh; `report()` is for the on-demand open-the-clip case.

### 4.4 Scope change

`accounts.py:29` must become:

```python
YT_SCOPES = ("https://www.googleapis.com/auth/youtube.upload "
             "https://www.googleapis.com/auth/youtube.readonly "
             "https://www.googleapis.com/auth/yt-analytics.readonly")
```

`accounts.py:182` already sends `access_type="offline", prompt="consent"`, so a reconnect does yield a fresh refresh token with the new scope.

### 4.5 UI

- `setTabs()` at `web/index.html:2003` — no new tab is needed; the report belongs on the clip card, not in settings. If a settings row is wanted for "which account's channel", it follows the `transcribe` shape at `web/index.html:2048`.
- Any new sidebar icon must exist in the `I` map at `web/index.html:847`.
- The SPA route regex at `web/index.html:1317` (`/^\/app\/settings(?:\/(ai|profile|security|apps|storage|transcribe))?\/?$/`) only needs a new alternative if a settings pane is added.
- Render `reasons` grouped by `level` (`bad` → error tone, `warn` → warning, `info` → neutral) and show `level == "key"` as a small "connect Google for retention" prompt rather than an error.

### 4.6 Degradation contract

Per ground rule 4 of the brief, a user who never opens this sees no change:

- No YouTube account connected → `/api/yt/report` raises `404`; the clip card shows nothing.
- Connected without the analytics scope → `deep_video` returns `{}`, `level == "key"`, and only the public rules run. This is the **expected** state for every account connected before this change.
- No API key configured → everything still works, because PeakCut uses the **OAuth bearer token** for the Data API too; `key=` is not needed on this path (unlike the source, which is key-first).

## 5. Data files

Almost nothing new. Deliberately.

| File | Owner | Change |
|---|---|---|
| `DATA_DIR/users/<uid>/accounts/accounts.json` | `accounts.py:38` | **no schema change**; the existing `refresh_token`, `access_token`, `expires`, `id`, `name` are enough |
| `DATA_DIR/posts.json` | `posting.py:12` | additive: `avg_view_pct`, `kept_at_3s`, `subs_gained`, `stats_at` on a post. Never remove or rename `views`/`remote_id`/`url` |
| `DATA_DIR/yt.json` | **new** | optional per-user overrides; see below |

`yt.json` schema — only needed if defaults must be tunable, and it should be created lazily:

```json
{
  "hook_second": 3.0,
  "peer_window": 20,
  "median_days": 90,
  "median_rows": 20,
  "shorts_max_s": 180,
  "rules": {
    "min_age_hours": 24,
    "low_views_ratio": 0.5,
    "like_rate": 0.02,
    "like_rate_min_views": 50,
    "avp_floor": 60,
    "avp_vs_median": 0.8,
    "hook3_floor": 0.7,
    "title_max": 60,
    "hook_overlap": 0.1,
    "hour_needs_peers": 6
  }
}
```

Rules for it, mirroring `ai.py`:

- `_file() -> Path` returns `config.user_dir(ctx.uid()) / "yt.json"`, so **each user gets their own thresholds** — a channel with a 6 % like rate should not be told 2 %.
- `public()` returns the dict with every key present (defaults merged in, `{**_DEFAULTS, **saved}`), never raising on a corrupt file — the `_tr_saved` pattern at `server.py:1329-1334` (a hand-edited `null`, `[]` or `3` must not stop the server booting) is the model.
- `save()` validates each numeric into a sane range and writes under a `threading.Lock` with `tmp.replace()` + `chmod(0o600)`, exactly like `accounts.py:54-63`.
- Nothing in it is secret, so `public()` needs no `key_hint` treatment.

**No new fonts, no new ffmpeg strings, no new binary assets.** This feature renders nothing.

## 6. Risks

**The scope upgrade is the real trap.** Every existing connected account holds a refresh token issued for `youtube.upload + youtube.readonly`. Adding `yt-analytics.readonly` does not retroactively grant it: the Analytics call returns **403 `Forbidden`**, and it will read as a bug rather than as "reconnect". The port must (a) detect 403 specifically and surface "Reconnect your YouTube account to see retention" rather than the raw Google message, and (b) not treat that 403 as a reason to delete the account. Also note the consent screen must have the Analytics scope added in the Google Cloud console, or the request fails with `invalid_scope` at connect time.

**A refresh_token is not re-issued silently.** `prompt="consent"` (`accounts.py:182`) forces the consent screen, which is what makes reconnect work. Do not "optimise" it away.

**Multi-user assumptions that do not hold:**

- The source's global workspace `ws` becomes `config.user_dir(ctx.uid())`; `ctx.uid()` raises `NoUser` (`ctx.py:14-22`) outside a request or an `as_user` block — a background refresh **must** wrap in `ctx.as_user(uid)` exactly as `posting.py:181` and `posting.py:149` do.
- `ids="channel==MINE"` is per **token**, so the report is automatically the right channel — but `latest_shorts` in the source derives the uploads playlist from a configured `YT_CHANNEL`. In PeakCut that value comes from `acc["id"][3:]`. **Never** accept a `channel` id from the request; that would let one user read another's channel.
- The source's `links.json` maps `run|file` → video id, keyed by clip path. PeakCut already owns that mapping in `posts.json` as `remote_id` (`posting.py:82`). Do not port `_links`/`_find`/`_title`; the auto-match-by-title heuristic (`ytstats.py:183-189`) is both unnecessary and dangerous (titles are not unique).
- The source's throttling is none; PeakCut has `_throttle` (`server.py:633`) and **must** use it. The Analytics API has a per-project daily quota; one user hammering `/api/yt/report` on every clip card would exhaust it for everyone on the instance.

**API-key-first does not apply.** The source is key-first (`YT_API_KEY` env) because it has no signed-in session. PeakCut is token-first. Do not add a key setting; do not send `key=` alongside the bearer token (Google accepts it but it is a second credential to leak).

**Quota and cost.** `report()` costs **three** Analytics report calls plus one `playlistItems` plus one `videos` — five round trips. On a 20-clip grid that is 100 calls if rendered eagerly. Cache the result on the post (`stats_at`) with a TTL (10 minutes is sensible) and render lazily.

**`kept_at_3s` is an approximation.** It is the nearest sample on a curve whose resolution Google controls; for a short Short the nearest point may be at 2 s or 5 s. Label it "around second 3" in the UI, never as an exact figure. Same for the privacy-hostile inference: a low `kept_at_3s` is a *hint*, and rule 4's text already says "the hook is not working" — keep that hedge.

**`views` collides.** `deep()`'s Analytics `views` overwrite the Data API `viewCount` in the same dict (`ytstats.py:125`). Two sources, two numbers, one key. In the port, keep them apart: `video["views"]` (public) versus `analytics["views"]` (private, lagging) — otherwise a user watching the number jump between two refreshes will report it as a bug.

**Statistic absence is not zero.** `likeCount` is missing when a creator hides likes, and `commentCount` is missing when comments are off. The source coerces both to `0`, which makes rule 2 fire ("like rate 0 %") on a video whose likes are simply hidden. The port must distinguish `None` (absent) from `0` and skip the rule on `None`.

**Dependency concerns: none new.** `httpx==0.28.1` is present (`requirements.txt:2`). Do not add `google-api-python-client` or `google-auth` — the source proves two `urllib`/`httpx` calls suffice, and both would drag in a large tree for one endpoint. Do not add `pandas`; the median is `statistics.median` over ≤ 20 rows.

**Do not copy the loopback OAuth server.** `oauth_start` (`ytstats.py:77-95`) binds a local socket and blocks a thread for 300 s — impossible to reason about behind a reverse proxy and wrong for a hosted app. PeakCut's redirect flow (`accounts.py:178-195`) already works; only the scope string changes.

## 7. Verification

**Unit-level, no network** — the source's `_get` seam becomes a monkeypatched `httpx.get`. New `peakcut/tests/test_ytstats.py`, in the shape of `tests/test_transcribe_logfare.py` (a `check(name, got, want)` helper, a `FakeResponse` with `.json()`/`.status_code`, `sys.path.insert` to the repo root, run as `python tests/test_ytstats.py`). It must prove, with no key and no network:

1. `video_id("https://youtube.com/shorts/zzzzzzzzzzz?x=1") == "zzzzzzzzzzz"`, `video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"`, `video_id("nope") is None`.
2. `duration_s("PT1M5S") == 65`, `duration_s("PT30S") == 30`, `duration_s("") == 0`.
3. `latest_shorts` drops a 181-second upload and keeps a 180-second one (the `0 < seconds <= 180` boundary, in both directions).
4. `deep_video` on a 30 s video picks the row nearest `elapsedVideoTimeRatio == 0.1` for `kept_at_3s`.
5. `diagnose` fires exactly the expected key set on a crafted fixture: a 30 h-old video at 40 % of peer median with a 74-character title, a non-verb opener and a mismatched hook yields `{"views", "title_len", "verb", "mismatch"}`; `level == "key"` without analytics and `"analytics"` with `averageViewPercentage`.
6. A 3-hour-old video yields `{"views"}` at level `info` and **no** `likes` rule even at 0 likes / 1000 views only if likes are `None`, not `0`.

**Integration, against the throwaway server** — `python tests/run.py` must still pass untouched, and a new check confirms `GET /api/yt/report` for a post that has no `remote_id` returns `404`, while a user who is not the post's owner also gets `404` (not `403`), matching `_admin`'s convention at `server.py:314`.

**Manual, one real video** — the only proof the scope and the report actually work:

```bash
python -m studio.server
# connect a YouTube account in Settings > Connected apps, then:
curl -s "http://127.0.0.1:8765/api/yt/report?post=<pid>" | python -m json.tool
```

Expected: `level == "analytics"`, `analytics.averageViewPercentage` between 0 and 100, `analytics.kept_at_3s` between 0 and 1, and `reasons` containing at least one entry for a video older than 24 h. If `level == "key"` instead, the scope was not granted — reconnect the account.

A one-line smoke that needs no server and no token:

```bash
python -c "from studio import ytstats; print(ytstats.diagnose({'id':'a','title':'Watch this GTA 6 clip','published':'2026-11-18T10:00:00Z','seconds':30,'views':40,'likes':1,'comments':0}, [{'id':'b','title':'x','published':'2026-11-01T10:00:00Z','seconds':20,'views':1000,'likes':40,'comments':2}]))"
```

must print `reasons` containing `views` (40 < 0.5 × 1000, age > 24 h) and `level == 'key'`.
