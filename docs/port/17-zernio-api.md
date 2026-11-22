# 17 — Zernio publishing API (implementation spec)

Source: the live docs at `https://docs.zernio.com`, rendered from the OpenAPI document
at `https://docs.zernio.com/api/openapi` (`info.title "Zernio API"`, version 1.688.0) —
pages `/api-reference` (accounts, posts, queue, media, analytics, profiles, connect),
`/webhooks`, and the guides on rate limits, error handling and the post lifecycle.
Nothing below is inferred.

## 0. Transport, auth, rate limits, errors

`Base URL` `https://zernio.com/api/v1` · `Authorization: Bearer <API_KEY>` on every
request · `application/json` on every body, both ways. Paths below are written with the
`/v1` prefix for readability: `GET /v1/accounts` means `https://zernio.com/api/v1/accounts`.

Rate limits per API key: **60 rpm** with 0–2 accounts, **600 rpm** with 3–2000, **1200
rpm** with 2001+. Analytics endpoints use a 1-second window (6/10/20 per sec per tier).
Every response carries `X-RateLimit-Limit` / `-Remaining` / `-Reset`; a 429 carries
`Retry-After` in seconds. Publishing caps are separate, per account: **25
posts/hour/account**, then per day Instagram 100, Facebook 250, Threads 250, X 50,
Pinterest 25, TikTok 15 video + 15 photo, 50 elsewhere. Zernio retries an upstream
platform 429/5xx three times before reporting a platform failure.

**Error envelope** — flat at the top level, not nested under `error`. `error` is a human
sentence and must never be branched on; branch on `code`.

```python
{"error": "scheduledFor must be in the future",     # human text — never branch on it
 "type": "invalid_request_error",   # invalid_request_error | authentication_error
                                    # | permission_error | not_found | rate_limit_error
                                    # | platform_error | api_error
 "code": "invalid_field_value",     # stable machine code — branch on this
 "param": "scheduledFor",           # offending field, when applicable
 "docUrl": "https://docs.zernio.com/...",
 "platform": "meta",                # only when type == "platform_error"
 "platformError": {...},            # upstream payload passed through verbatim
 "retryable": False, "requestId": "req_...",
 "details": {...}}                  # endpoint-specific structured context
```

`code` values met in practice: `missing_required_field`, `invalid_field_value`,
`missing_credentials`, `invalid_credentials`, `insufficient_permissions`,
`rate_limited`, `platform_api_error`, `internal_error`, `temporarily_unavailable`, plus
the uppercase state codes `ACCOUNT_DISCONNECTED`, `ACCOUNT_NOT_ENABLED_FOR_POSTING`,
`PROFILE_OVER_LIMIT`, `ACCOUNT_NOTIFICATION_ONLY`, `idempotency_conflict`. Statuses
seen: 200/201/202/207, 400, 401, 402, 403, 404, 409, 424, 429, 500, 503.

## (a) List connected accounts — `GET /v1/accounts`

```python
{
    "accounts": [
        {"_id": "64e1f0a9e2b5af0012ab34de",   # str — this is the accountId you post to
         "platform": "twitter",               # str
         "profileId": {"_id": "64f0...", "name": "My Brand", "slug": "my-brand"},
         "username": "@acme", "displayName": "Acme",
         "profileUrl": "https://x.com/acme",
         "isActive": True},                   # bool
        # optional per account: profilePicture, platformUserId, followersCount,
        # needsReconnection, enabled, rateLimitedUntil, tiktokAccountType,
        # parentAccountId, scopeAreas, oauthAppId, metadata
    ],
    "hasAnalyticsAccess": False,   # bool — analytics (e) needs this true
    "pagination": {"page": 1, "limit": 10, "total": 1, "pages": 1},  # or {limit, nextCursor}
    # "warning", "profileTotals", "statusCounts" only for the matching params
}
```

Required per account: `_id`, `platform`, `profileId`, `isActive`; `hasAnalyticsAccess`
is a required top-level field. All query params are optional: `profileId`, `platform`,
`platforms` (CSV ≤50), `status` (`connected`|`disconnected`), `search` (≤100 chars),
`category`, `sort`, `order`, `includeOverLimit`, `excludeHidden`, `includeStatusCounts`,
`perProfile` + `profileIds`, `includeCreatorAccounts`, `includeSandbox`; page with
`page`+`limit` or `cursor`. An unpaged call is cut at 500 accounts and returns a `warning`
plus `pagination.nextCursor` (and `X-Result-Truncated`). Errors 400, 401, 503.
`needsReconnection: true` means the stored OAuth token is dead — re-run the connect
flow; `rateLimitedUntil` is the ISO end of that account's publish cooldown.

Supporting calls: `GET /v1/profiles` → `{"profiles": [{"_id", "name", "color",
"isDefault", "accountCount", "isOverLimit", ...}]}` (params `name`, `externalId`,
`limit` 1–1000, `skip`, `includeOverLimit`). `GET /v1/connect/{platform}?profileId=...`
→ 200 with the OAuth URL to redirect the user to (also `reconnectAccountId`,
`redirect_url`, `scopes`, `headless`; errors 400/401/402/403/404). The two health
endpoints `GET /v1/accounts/health` and `/v1/accounts/{accountId}/health` report tokens.

## (b) Upload a local video — `POST /v1/media/presign`, then `PUT`

```python
# request: {"filename": "clip.mp4",          # str, required
#           "contentType": "video/mp4",      # required, enum below
#           "size": 48213004}                # int, optional, max 5 GB
```

`contentType` enum: `image/jpeg`, `image/jpg`, `image/png`, `image/webp`, `image/gif`,
`video/mp4`, `video/mpeg`, `video/quicktime`, `video/avi`, `video/x-msvideo`,
`video/webm`, `video/x-m4v`, `application/pdf`, `audio/mpeg`, `audio/mp4`, `audio/aac`,
`audio/ogg`, `audio/wav`, `audio/webm`, `audio/x-m4a`, `application/x-subrip`,
`text/vtt`. `application/octet-stream` is rejected with 400 `INVALID_FIELD_VALUE`, so
send the real MIME type.

```python
# 200 response
{
    "uploadUrl": "https://storage.../presigned?...",   # PUT the bytes here
    "publicUrl": "https://media.zernio.com/temp/1234567890_abc123_clip.mp4",
    "key": "temp/1234567890_abc123_clip.mp4",
    "expiresIn": 3600,                                 # seconds; uploadUrl dies after
}
```

**Step 2** is a plain S3-style presigned `PUT` of the raw bytes to `uploadUrl`: send the
same `Content-Type` you presigned with, and **no** `Authorization` header and no JSON
wrapper. A non-2xx there is the bucket's error, not Zernio's envelope. Then use
`publicUrl` (never `key`) as `mediaItems[].url` in (c). Optional normalisation, only
when a platform rejects the raw file — `POST /v1/media/prepare` `{"url": publicUrl,
"target": "tiktok"}` → `{"target", "url", "changed", "mediaType", "originalSize",
"outputSize"}`, where `target` ∈ `instagram`, `instagram_story`, `facebook`,
`facebook_reel`, `facebook_story`, `threads`, `tiktok`, `linkedin`, `twitter`,
`bluesky`, `pinterest`, `reddit`, `snapchat`, `telegram`, `googlebusiness`,
`youtube_thumbnail`.

## (c) Create a post — `POST /v1/posts`

Optional headers: `Idempotency-Key` (≤255 chars, honoured 24 h — a replay returns
**200** with the original post; a duplicate still in flight returns 409
`idempotency_conflict` + `Retry-After`) and `x-request-id` (a UUID).

```python
{
    "content": "We just launched!",   # str; optional if every target has customContent
    "mediaItems": [                   # array, optional
        {"type": "video",             # image|video|gif|document
         "url": "https://media.zernio.com/temp/...mp4",   # the presign publicUrl
         "title": "...", "altText": "...", "filename": "clip.mp4",
         "size": 48213004, "mimeType": "video/mp4",
         "thumbnail": "https://...", "instagramThumbnail": "https://...",
         "subtitles": []}
    ],
    "platforms": [                    # required for every non-draft post
        {"platform": "twitter",       # required
         "accountId": "64e1f0a9e2b5af0012ab34de",   # required — a str, NOT an object
         "customContent": "...", "customMedia": [...],
         "scheduledFor": "2026-11-20T10:00:00Z", "platformSpecificData": {...}}
    ],
    "scheduledFor": "2026-11-20T10:00:00Z",   # ISO-8601
    "publishNow": False,                      # bool, default False
    "timezone": "Europe/Madrid",              # IANA name; interprets a naive scheduledFor
    "title": "...", "tags": ["launch"], "hashtags": ["#launch"], "mentions": ["@acme"],
    "isDraft": False, "requiresApproval": False, "dryRun": False,
    "metadata": {"peakcut_job": "j_123"},     # free-form, echoed back on reads
    "queuedFromProfile": "64f0...",           # schedule into that profile's queue instead
    "queueId": "64f0a1b2...",                 # a specific queue, with queuedFromProfile
    "profileId": "64f0...",                   # only to file a platform-less draft
}
```

`platform` enum: `twitter`, `threads`, `instagram`, `youtube`, `facebook`, `linkedin`,
`pinterest`, `reddit`, `tiktok`, `bluesky`, `googlebusiness`, `telegram`. **Scheduling
contract — exactly one of three, or the post is a draft:** `publishNow: true` · a future
`scheduledFor` · `queuedFromProfile` (next free queue slot). With none of them the post
is stored as `status: "draft"` and nothing publishes. A `scheduledFor` in the past
publishes synchronously inside the same request.

```python
# 201 response
{"post": {                                    # the full Post object, see (d)
    "_id": "65f1c0a9e2b5af0012ab34cd", "content": "We just launched!",
    "status": "scheduled",                    # or "published" with publishNow
    "scheduledFor": "2026-11-20T10:00:00Z", "timezone": "UTC",
    "platforms": [
        {"platform": "twitter",
         "accountId": {"_id": "64e1f0...", "platform": "twitter",   # expanded on output
                       "username": "@acme", "displayName": "Acme Corp", "isActive": True},
         "status": "pending"}]},
 "message": "Post scheduled successfully",
 "warnings": []}                              # present when something was downgraded
```

**201** created · **200** idempotent replay or `dryRun` · **202** accepted · **207**
partial success — *a 2xx, so always inspect a 2xx*: some platforms failed and
`post.status` is `partial` or `failed`. Then 400, 401, 402 (X prepaid balance:
`$0.015`/post, `$0.20` with a link; body carries `funding_url`), 403
(`ACCOUNT_DISCONNECTED`, `ACCOUNT_NOT_ENABLED_FOR_POSTING`, `PROFILE_OVER_LIMIT`), 409
(same content already queued — `details` carries `accountId`, `platform`,
`existingPostId`), 429, 503.

## (d) Read post status — `GET /v1/posts/{postId}`

```python
{
    "post": {
        "_id": "65f1c0a9e2b5af0012ab34cd", "title": "Launch post",
        "content": "We just launched!", "mediaItems": [...],
        "scheduledFor": "2026-11-20T10:00:00Z", "timezone": "UTC",
        "status": "published",     # draft | pending_approval | scheduled | publishing
                                   # | published | partial | failed | cancelled
        "platforms": [
            {"platform": "twitter", "accountId": {...},
             "status": "published",        # pending|processing|uploading|published
                                           # |failed|cancelled
             "platformPostId": "1852634789012345678",
             "platformPostUrl": "https://twitter.com/acmecorp/status/1852634789012345678",
             "publishedAt": "2026-11-20T10:00:05Z", "publishAttempts": 1,
             "errorMessage": None,
             "errorCategory": None,        # auth_expired | user_content | user_abuse
                                           # | platform_rate_limit | quota_exhausted
                                           # | account_issue | platform_rejected
                                           # | platform_error | system_error | unknown
             "errorSource": None,          # user | platform | system
             "platformError": None}
        ],
        "tags": ["launch"], "createdAt": "2026-11-19T12:00:00Z",
        "updatedAt": "2026-11-20T10:00:06Z",
    }
}
```

Codes 200/400/401/403/404. **Prefer `GET /v1/posts` for monitoring** over one call per
post: `?status=scheduled&updatedSince=<ISO>` returns only posts whose `updatedAt` moved
(any post or platform change bumps it), and `?fields=_id,status,scheduledFor` trims the
payload. It also takes `platform`, `profileId`, `accountId`, `source`
(`zernio`|`external`), `fromDate`/`toDate`, `tags` (CSV ≤20), `view` (`full`|`summary`),
`sortBy`, `limit`, `page`/`offset`/`cursor`; an unknown query param is a 400 naming it.
It answers `{"posts": [<Post objects>], "pagination": {"page", "limit", "total",
"pages"}}`. Retry only the failed targets of a `failed`/`partial` post with `POST
/v1/posts/{postId}/retry`. `DELETE /v1/posts/{postId}` → **200** deleted; **400**
`"Cannot delete published posts"` (unpublish first); 401/403/404.

Push beats polling: `POST /v1/webhooks/settings` `{name, url, events, secret?,
isActive?, customHeaders?, profileIds?, accountIds?}` registers an endpoint receiving
`post.published`, `post.partial`, `post.failed`, `post.scheduled`, `post.cancelled` and
the per-platform `post.platform.published` / `post.platform.failed`. Requests carry
`X-Zernio-Event`, `X-Zernio-Event-Id`, `X-Zernio-Signature` (HMAC-SHA256 of the raw body
keyed with your `secret`). Answer 2xx within 5 s, dedupe on the event id; retries run 7
times over ~51 h. `POST /v1/webhooks/test` sends a sample; `GET /v1/webhooks/logs` and
`POST /v1/webhooks/logs/redeliver` inspect and replay. **Queue slots** —
`GET /v1/queue/slots?profileId=...` (required `profileId`; optional `queueId`,
`all=true`; with no queue, `exists` is `false` and `schedule` is absent):

```python
{"exists": True,
 "schedule": {"_id": "64f0a1b2c3d4e5f6a7b8c9d1", "profileId": "64f0a1b2...",
              "name": "Morning Posts", "timezone": "America/New_York",
              "slots": [{"dayOfWeek": 1, "time": "09:00"}],  # 0 = Sunday .. 6 = Saturday
              "active": True, "isDefault": True},
 "nextSlots": ["2026-11-23T09:00:00-05:00"]}

{"queues": [{...}, {...}], "count": 2}          # with all=true
```

`GET /v1/queue/next-slot?profileId=` → `{profileId, nextSlot, timezone, queueId, queueName}`;
`GET /v1/queue/preview?profileId=&count=` (1–100, default 20) → `{profileId, queueId,
queueName, count, slots: [...]}`. Codes 200/400/401/404.

## (e) Per-post analytics — `GET /v1/analytics`

`postId` accepts a Zernio post id, an external id, or the native platform post id. Other
params: `platform` (default `all`), `profileId`, `accountId`, `source`
(`all`|`late`|`external`), `fromDate`/`toDate` (default last 90 days, max 366), `limit`
(1–100, default 50), `page`, `sortBy`, `order`, `tags`, `view`.

```python
# one post — 200
{"postId": "65f1c0a9e2b5af0012ab34cd", "status": "published",
 "content": "Check out our new product launch!",
 "scheduledFor": "2026-11-20T10:00:00Z", "publishedAt": "2026-11-20T10:00:05Z",
 "analytics": {                    # aggregated across platforms
     "impressions": 15420, "reach": 12350, "likes": 342, "comments": 28,
     "shares": 45, "saves": 0, "clicks": 189, "views": 0,
     "engagementRate": 2.78, "lastUpdated": "2026-11-21T08:30:00Z"},
     # optional: follows, profileViews, websiteClicks, totalViews, totalLikes,
     # totalComments, videoDurationSeconds, completionRate, replays,
     # igReelsAvgWatchTime, igReelsVideoViewTotalTime, reelsSkipRate,
     # impressionSources, audienceTypes, audienceCountries, retentionCurve
 "platformAnalytics": [
     {"platform": "twitter", "status": "published", "platformPostId": "123456789",
      "accountId": "64e1f0a9...", "accountUsername": "@acmecorp", "analytics": {...},
      "syncStatus": "synced", "platformPostUrl": "https://twitter.com/...",
      "errorMessage": None}],
 "platform": "twitter", "platformPostUrl": "https://twitter.com/acmecorp/status/1",
 "isExternal": False,
 "syncStatus": "synced",           # "pending" while the first pull is still running
 "mediaType": "video", "thumbnailUrl": "https://..."}
```

Without `postId` the same endpoint lists everything: `{"overview": {"totalPosts",
"publishedPosts", "scheduledPosts", "lastSync", "dataStaleness":
{"staleAccountCount", "syncTriggered"}}, "posts": [...]}`, each row carrying `_id`,
`content`, `publishedAt`, `status`, `analytics` and per-platform rows with
`accountUsername`, `analytics`, `platformPostUrl`. The list view keys posts by external
id and reports `isExternal: true` even for posts scheduled through Zernio, so correlate
on `platformPostUrl`, not on `_id`. **202 means "still syncing"** (`syncStatus:
"pending"`, `message` explains) — not an error, just call again later. Other codes:
400, 401, 402 (analytics add-on missing — check `hasAnalyticsAccess` from (a)), 404,
424, 429, 500.

## Python client sketch

Needs only `httpx`. The key comes from `ZERNIO_API_KEY`; never hard-code it.

```python
import os, time, httpx

BASE = "https://zernio.com/api/v1"
KEY = os.environ["ZERNIO_API_KEY"]

class ZernioError(RuntimeError):
    def __init__(self, status: int, body: dict):
        self.status, self.body, self.code = status, body, body.get("code")
        super().__init__(f"zernio {status} {self.code}: {body.get('error')}")

def api() -> httpx.Client:
    return httpx.Client(base_url=BASE, timeout=60.0,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})

def _check(r: httpx.Response) -> dict:
    if r.status_code >= 300:
        raise ZernioError(r.status_code, r.json() if r.content else {})
    return r.json()

# (a) which platforms does this user have connected?
def list_accounts(c: httpx.Client, profile_id: str | None = None) -> list[dict]:
    params = {"profileId": profile_id} if profile_id else {}
    return [a for a in _check(c.get("/accounts", params=params))["accounts"]
            if a["isActive"]]

# (b) local video file -> public URL (presign, then PUT the bytes)
def upload_video(c: httpx.Client, path: str, content_type: str = "video/mp4") -> str:
    slot = _check(c.post("/media/presign", json={
        "filename": os.path.basename(path),
        "contentType": content_type,
        "size": os.path.getsize(path)}))
    with open(path, "rb") as fh:          # no bearer token, no JSON, on the bucket PUT
        put = httpx.put(slot["uploadUrl"], content=fh, timeout=httpx.Timeout(600.0),
                        headers={"Content-Type": content_type})
    put.raise_for_status()
    return slot["publicUrl"]              # valid until slot["expiresIn"] seconds pass

# (c) create a post for specific accounts, immediate or scheduled
def create_post(c: httpx.Client, *, caption: str, accounts: list[dict],
                video_url: str | None = None,
                scheduled_for: str | None = None,        # "2026-11-20T10:00:00Z"
                publish_now: bool = False,
                idempotency_key: str | None = None) -> dict:
    body = {"content": caption,
            "platforms": [{"platform": a["platform"], "accountId": a["_id"]}
                          for a in accounts]}
    if video_url:
        body["mediaItems"] = [{"type": "video", "url": video_url}]
    if publish_now:
        body["publishNow"] = True
    elif scheduled_for:
        body["scheduledFor"], body["timezone"] = scheduled_for, "UTC"
    headers = {"Idempotency-Key": idempotency_key} if idempotency_key else {}
    post = _check(c.post("/posts", json=body, headers=headers))["post"]
    if post["status"] in ("partial", "failed"):   # 207 is a 2xx: inspect it
        failed = [p for p in post["platforms"] if p["status"] == "failed"]
        raise ZernioError(207, {"code": "partial_failure", "details": failed,
                                "error": f"{len(failed)} platform(s) failed"})
    return post

# (d) monitor: poll everything that changed since the last check
def posts_since(c: httpx.Client, iso_ts: str) -> list[dict]:
    return _check(c.get("/posts", params={"updatedSince": iso_ts, "view": "summary",
        "fields": "_id,status,scheduledFor,updatedAt"}))["posts"]

def post_status(c: httpx.Client, post_id: str) -> dict:
    return _check(c.get(f"/posts/{post_id}"))["post"]

def retry_failed(c: httpx.Client, post_id: str) -> dict:   # failed/partial only
    return _check(c.post(f"/posts/{post_id}/retry"))

# (e) per-post analytics; 202 == still syncing, so poll again
def post_analytics(c: httpx.Client, post_id: str, tries: int = 5) -> dict:
    for attempt in range(tries):
        r = c.get("/analytics", params={"postId": post_id})
        if r.status_code == 202:
            time.sleep(10 * (attempt + 1))
            continue
        return _check(r)
    return {"postId": post_id, "syncStatus": "pending", "analytics": {}}

if __name__ == "__main__":
    with api() as c:
        accounts = list_accounts(c)
        if not accounts:
            raise SystemExit("no connected accounts")
        post = create_post(c, caption="PeakCut test", accounts=accounts[:1],
                           video_url=upload_video(c, "out/clip.mp4"), publish_now=True)
        while post["status"] in ("publishing", "scheduled"):
            time.sleep(5)
            post = post_status(c, post["_id"])
        print(post["status"], post_analytics(c, post["_id"]).get("analytics"))
```

Two traps for the implementing agent: `accountId` is a plain **string** on the way in and
an expanded object on the way out, so never round-trip a response's `platforms[]` back
into a create call; and `POST /v1/posts` can answer 207, so inspect `post.status` after
any 2xx. Keep the presign → PUT → create window under `expiresIn` (3600 s).
