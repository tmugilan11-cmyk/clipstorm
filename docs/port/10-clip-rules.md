# 10 — Streamer clip rules with permission badges

Port of `gta6-clipper-main/clip_rules.json` + `app.py`'s `clip_rule` / `clip_block` / `src_streamer`
into PeakCut as `peakcut/studio/rules.py`.

---

## 1. What it does

Every streamer PeakCut knows about carries a small badge saying whether clipping them is publicly
allowed, forbidden, "ask first", or simply not known. Hovering or clicking the badge shows the
streamer's own conditions and a link to the statement the verdict is based on. A streamer marked
"no clipping" cannot be queued for a job until the person explicitly confirms they have permission;
the other three states are advisory only and never block anything. The table ships with the app, is
replaced wholesale on update, and any account can add or override entries for the streamers it
follows.

---

## 2. Exact mechanics

### 2.1 The lookup table

`gta6-clipper-main/clip_rules.json` is 447 lines / 7541 bytes, a **flat** JSON object: no `_note`,
no version key, no nesting. 89 entries. Key = `"platform:handle"` with the platform lowercase
(`twitch` / `kick` / `youtube`) and the handle lowercased **including its leading `@` for YouTube**.
Value = exactly three keys: `rule`, `note`, `source`.

Distribution across the 89 shipped rows:

| rule | rows |
|---|---|
| `unknown` | 85 |
| `ask` | 2 |
| `allowed` | 2 |
| `no` | **0** |

There is no `"no"` row in the shipped data. The hard block is therefore latent code that only fires
once a rule is added (by an update or by a user override). Port it anyway — it is the whole point of
the policy, and `SKILL.md:16` defines it.

The four rows that carry content, verbatim (these are the only rows whose `note`/`source` is not
empty; every other row is exactly `{"rule": "unknown", "note": "", "source": ""}`):

```json
"twitch:xqc": {
  "rule": "ask",
  "note": "Clip away, just skip reposting a stream his editors already posted in the last 24 h.",
  "source": "https://prsek.substack.com/p/the-editor-manifesto"
},
"youtube:@ishowspeed": {
  "rule": "allowed",
  "note": "Works with a paid clipping company (Clipping) and sponsor clip campaigns; his agency claimed some clip channels in 2023-24, so credit him and do not reupload whole streams.",
  "source": "https://www.thewrap.com/media-platforms/tv/creators-rise-of-clipping-explained/"
},
"twitch:asmongold": {
  "rule": "allowed",
  "note": "Said publicly he will not DMCA clip channels re-uploading his streams (2019 statement); credit the channel.",
  "source": "https://kotaku.com/popular-wow-streamer-hires-youtubers-who-leeched-off-hi-1840377137"
},
"kick:adinross": {
  "rule": "ask",
  "note": "Pays clippers through Kick’s Clipping Program and his own campaigns: join one and you get paid to clip him.",
  "source": "https://win.gg/kick-clipping-program/"
}
```

The complete key set, in file order (all 89, all `"rule": "unknown"` unless listed above):

```
twitch:xqc, twitch:kaicenat, youtube:@ishowspeed, twitch:asmongold, kick:adinross,
twitch:shroud, twitch:summit1g, twitch:sodapoppin, twitch:timthetatman, twitch:ninja,
youtube:@valkyrae, youtube:@penguinz0, twitch:jynxzi, twitch:esfandtv, twitch:gotaga,
youtube:@squeezie, youtube:@michou, youtube:@inoxtag, twitch:ponce, twitch:domingo,
twitch:locklear, twitch:kamet0, twitch:zerator, twitch:maghla, twitch:doigby, twitch:ibai,
twitch:thegrefg, twitch:auronplay, twitch:rubius, twitch:elxokas, twitch:illojuan,
twitch:knekro, kick:spreen, twitch:westcol, twitch:quackity, twitch:juanguarnizo,
youtube:@vegetta777, youtube:@willyrex, twitch:rivers_gg, twitch:gaules, twitch:alanzoka,
twitch:baiano, twitch:loud_coringa, twitch:cellbit, twitch:jazzghost,
youtube:@authenticgames, youtube:@flakespower, twitch:casimito, youtube:@nobru,
twitch:papaplatte, twitch:trymacs, twitch:montanablack88, twitch:gronkh, twitch:ungespielt,
twitch:knossi, twitch:handofblood, twitch:eliasn97, twitch:tanzverbot, twitch:pietsmiet,
youtube:@rewinside, twitch:reevtv, youtube:@aboflah, youtube:@movlogs,
youtube:@khalidalameri, youtube:@baderalawadhi, youtube:@spacetoongaming, kick:aburayyan,
kick:saudgaming, youtube:@joegamingarabia, twitch:dariomocciatwitch, twitch:pow3rtv,
youtube:@favij, youtube:@sabakunomaiku, youtube:@mecontrote, twitch:mikeshowsha,
twitch:tumblurr, twitch:cydonia, twitch:vegas, twitch:zanoxd, twitch:wtcn, twitch:jahrein,
twitch:elraenn, twitch:unlostv, twitch:pqueen, twitch:mithrain, twitch:evonmoss,
twitch:rraenee, twitch:pintipanda, twitch:kendinemuzisyen
```

### 2.2 The normative policy

`gta6-clipper-main/SKILL.md:16`, verbatim — this is the wording the feature implements, and the
wording the help text must carry over:

> Clip rules: before clipping a named streamer, look them up in `SKILL\clip_rules.json`
> (`platform:handle`, lowercase). `no` = stop and tell the user they said no to clipping (go on only
> if the user says they have permission); `ask` = tell the user the note; `unknown` = remind them to
> check the channel's rules before posting.

### 2.3 `clip_rule` — the resolver and its only validation

`gta6-clipper-main/app.py:625-629`, four statements, no dependencies:

```python
def clip_rule(p, h):  # shipped clip_rules.json (updates refresh it): allowed | ask | no | unknown, with a note and a source link
    try: R = json.loads((HERE / "clip_rules.json").read_text(encoding="utf-8"))
    except Exception: R = {}
    r = R.get(f"{p}:{str(h).lower()}") or {}
    return dict(rule=r.get("rule") if r.get("rule") in ("allowed", "ask", "no") else "unknown", note=r.get("note", ""), source=r.get("source", ""))
```

Four behaviours a port must keep exactly:

1. **Re-read from disk on every call.** No cache at all (`app.py:626`). Bounded by the fact that
   gta6-clipper is one user; see §6 for why PeakCut must cache.
2. **A broken file is not an error.** `except Exception: R = {}` (`app.py:627`) — missing, unreadable,
   or invalid JSON degrades to "everything is unknown", never raises.
3. **Only the handle is lowercased** (`app.py:628`). The platform is interpolated as given; every
   caller passes a lowercase literal.
4. **Whitelist normalisation** (`app.py:629`). The output `rule` is `r["rule"]` if and only if it is
   one of `"allowed"`, `"ask"`, `"no"`; anything else — the literal string `"unknown"`, a typo,
   `null`, a number, a bool — collapses to `"unknown"`. `note` and `source` default to `""` but are
   **not** type-checked or length-capped in the source. That whitelist is the only validation.

Return shape, always: `{"rule": str, "note": str, "source": str}`.

### 2.4 `clip_block` — the one place a rule stops work

`gta6-clipper-main/app.py:634-637`:

```python
def clip_block(p, h, d):  # -> error text when the streamer said no and the user did not confirm permission
    r = clip_rule(p, h)
    if r["rule"] == "no" and not d.get("permission"):
        return f"{h} does not allow clipping ({r['note'] or 'public statement'}{' ' + r['source'] if r['source'] else ''}). Only go on if you have their permission."
```

- Only `"no"` blocks. `"ask"` and `"unknown"` are advisory.
- The escape hatch is `d["permission"]` — any truthy value. `ask`/`false`/absent all keep the block.
- `note` falls back to the literal `public statement` when empty; `source` is appended with a leading
  space only when non-empty, so the rendered message always reads either
  `(note). Only go on…` or `(note). https://… Only go on…`.
- Returns `None` when there is nothing to say, and callers test truthiness.

### 2.5 `src_streamer` — getting `(platform, handle)` out of a link

`gta6-clipper-main/app.py:630-633`:

```python
def src_streamer(url):  # (platform, handle) for a channel/live link, else None (VOD ids carry no handle)
    m = re.search(r"(?:twitch\.tv/(?!videos/)|kick\.com/|^kick:)([\w.\-]+)", url or "", re.I) or re.search(r"youtube\.com/(@[\w.\-]+)", url or "", re.I)
    if not m: return None
    return ("twitch" if "twitch" in m[0].lower() else "kick" if "kick" in m[0].lower() else "youtube", m[1])
```

- The Twitch branch has a negative lookahead `(?!videos/)` so `/videos/123` (a VOD) does not yield
  the handle `"videos"`.
- YouTube only matches the `@handle` form; `/channel/UC…` and `/c/name` yield `None`.
- The `^kick:` alternative lets a bare `kick:handle` string through.
- `m[1]` is the handle **exactly as typed in the URL**, so YouTube keeps its `@`. Platform is decided
  by substring test on the whole match text, so `kick.com` wins over the trailing handle.
- `None` means "no named streamer" (a VOD, an aggregate page) — callers skip the rule check entirely.

### 2.6 The four call sites, and what each does with the result

| Site | Source line | Behaviour |
|---|---|---|
| List rows | `app.py:641` `for s in L: s["clip"] = clip_rule(s["platform"], s["handle"])` | Every streamer row in `/api/streamers` carries its badge; nothing blocks. |
| Hunt rows | `app.py:689-690` `for r in rows: r["clip"] = clip_rule(r["platform"], r["handle"])` | Same badge on everything currently live. |
| Start hunting | `app.py:695-697` `e = clip_block(...)` → `(403, {"error": e, "clip": "no"}) if e else (200, hunt.start(...))` | The only server-side hard stop. |
| New run | `app.py:857-862` `e = ps and clip_block(ps[0], ps[1], d)`; `if e: return self.send(403, {"error": e, "clip": "no"})` | Second hard stop. `ps` is `(platform, handle)` from `d["streamer"]` when it has a handle, else `src_streamer(d["source"])`; `ps` may be `None`, hence the `ps and` guard. |

`edit_streamers` (`app.py:643-648`) validates a user-added handle as
`re.fullmatch(r"@?[\w.\-]{1,60}", h)` — max 60 characters, letters/digits/`_`/`.`/`-`, optional
leading `@`. Only add/remove, no editing of a row's rule.

### 2.7 The presentation mapping (source UI)

`gta6-clipper-main/app.html:747-749`:

```js
const CLIPC={allowed:['PASS','clip.allowed'],ask:['len','clip.ask'],no:['FAIL','clip.no'],unknown:['na','clip.unknown']};
const clipChip=c=>{c=c||{rule:'unknown'};const [k,l]=CLIPC[c.rule]||CLIPC.unknown,tip=esc(c.note||(c.rule=='unknown'?t('clip.unknown_tip'):''));return c.source?`<a class="chip ${k}" href="${esc(c.source)}" target=_blank rel=noopener title="${tip}">${te(l)}</a>`:`<span class="chip ${k}" title="${tip}">${te(l)}</span>`};
const clipOk=async c=>!(c&&c.rule=='no')||await ask(t('clip.no_ask')+(c.note?'\n'+c.note:''),{ok:t('clip.have_perm')});
```

Load-bearing details: a missing badge is treated as `unknown`; an unrecognised rule falls back to
the `unknown` chip; the tooltip is the note, and for `unknown` only it is replaced by
`clip.unknown_tip`; the chip is an `<a target="_blank" rel="noopener">` when a source exists and a
plain `<span>` otherwise. `clipOk` asks a confirm dialog for `"no"` only, and the note is appended on
a second line.

The English strings (`app.html:604-610`) that the port reuses verbatim:

| key | English |
|---|---|
| `clip.allowed` | Clipping allowed |
| `clip.ask` | Has clip tips |
| `clip.no` | No clipping |
| `clip.unknown` | Rules unknown |
| `clip.unknown_tip` | We found no public clipping rule. Check their channel rules before you post. |
| `clip.no_ask` | This streamer has said no to clipping. Clips of them can get your channel copyright strikes. Only go on if you have their permission. |
| `clip.have_perm` | I have permission |

Permission plumbing on the client: `app.html:759` auto-start skips `r.clip && r.clip.rule=='no'`;
`app.html:773` sends `permission: c.checked && s.clip && s.clip.rule=='no'` after re-running
`clipOk`; `app.html:777` sends `permission: !!(s.clip && s.clip.rule=='no')` for past-stream runs.

`README.md:104`, verbatim — the user-facing promise: "**Clip rules.** Each streamer gets a badge:
**Clipping allowed**, **Has clip tips**, **No clipping** or **Rules unknown**. Click it to see the
source. The app will not clip a streamer who said no unless you confirm you have their permission."

---

## 3. PeakCut today

Nothing in PeakCut reads, stores, or displays a clipping rule. Verified gaps:

- **No table, no resolver.** `grep -rn "handle\|clip_rule" studio/*.py` returns only two hits, both
  prose in `peakcut/studio/brain.py:73` ("Never put links, `@handles`, …") and `brain.py:103`. There
  is no module, no JSON asset, no route, no field on any model.
- **`creators.DEFAULTS` (peakcut/studio/creators.py:17-23) has 30 keys** — `name`, `channel`,
  `style`, `layout`, `captions`, `min_len`, `max_len`, `max_clips`, `min_score`, `auto_watch`,
  `buffer_min`, `live_per_hour`, `ai_every_min`, `ai_only_on_spike`, `auto_jump_pct`, `plan`,
  `decide_mode`, `must_clip_min`, `min_gap_min`, `game`, `trigger_words`, `autopost`, `accounts`,
  `post_min_score`, `post_gap_min`, `daily_cap`, `privacy`, `post_footer`, `rate_per_1k`,
  `channels`. None of them is a rule, a permission, or a source link. `_clean()` (creators.py:54-86)
  drops unknown keys silently, so a rule field would be discarded on write unless `DEFAULTS` and
  `_clean` learn it.
- **`creators.platform_key(url)` (creators.py:27-30) already returns `"youtube"` / `"twitch"` /
  `"kick"` / `""`** — the exact platform vocabulary the rule table is keyed by. What it does *not*
  do is extract the handle; the whole URL is kept. This is the single most useful existing helper
  and it makes `handle_of` a ~10-line addition rather than a rewrite.
- **The job entry point has no gate.** `create_from_link` (server.py:718-745) validates
  `media.site_allowed(url)` and `media.check_youtube(url)`, resolves the creator, then calls
  `jobs.create(...)`. There is no permission check, and no `permission` field is read from the body.
  `/api/upload` (server.py:748) has no URL at all, so it can never be gated by handle.
- **The badge has nowhere to render.** `_creator_rows()` (server.py:650-657) builds each row as
  `{**c, "live_job": …, "log": …}`; `jobs.public(job)` (jobs.py:152-166) builds each job as the job
  dict minus `HIDDEN`, with `source` stripped of `path`. Both are plain dicts, so adding a `clip` key
  is additive and breaks no consumer.
- **The pill CSS already exists** — `web/index.html:250-255` defines `.pill`, `.pill.ok`,
  `.pill.bad`, `.pill.warn`, `.pill.live`, `.pill.brand`. A badge needs no new CSS.
- **Where the UI would attach**, in `web/index.html`: `const PLAT = {` at :1074 (per-platform name,
  colours, svg) and `channelRows(c)` at :1822, which already renders each connected channel as
  `${platLogo(k)}<div class="who"><b>name</b><span>platform · followers</span></div>`. That `.who`
  block is the natural home for the chip.

The gap, stated in one line: PeakCut can name a creator and their channels, and it has a job entry
point, but it has no rule table, no handle extractor, no gate on the entry point, and no badge on
any row.

---

## 4. Port plan

### 4.1 New files

| Path | Contents |
|---|---|
| `peakcut/studio/clip_rules.json` | Shipped table — the 89 rows above, byte-for-byte from `gta6-clipper-main/clip_rules.json`. Code, not user data: replaced on update. |
| `peakcut/studio/rules.py` | The whole feature: table loading, normalisation, handle extraction, the block message, per-user overrides, `public()`. |
| `peakcut/tests/test_clip_rules.py` | Standalone test (§7). |

### 4.2 Module skeleton and public surface

Follow `peakcut/studio/ai.py` for shape (`_lock`, a `_file()` helper, `public()` that leaks nothing)
and `peakcut/studio/creators.py` for the per-user path convention.

```python
"""Who allows their streams to be clipped. A table ships with PeakCut (clip_rules.json, one entry per
'platform:handle'), any account can add or override an entry, and a streamer marked "no" cannot be
queued until the person confirms they have permission.

    allowed | ask | no | unknown   — 'no' is the only state that stops work.
"""
import json
import re
import threading
from typing import Literal, Optional, Tuple

from . import config, ctx

Rule = Literal["allowed", "ask", "no", "unknown"]

RULE_VALUES: Tuple[str, ...] = ("allowed", "ask", "no", "unknown")
PLATFORMS: Tuple[str, ...] = ("youtube", "twitch", "kick")
HANDLE_RE = re.compile(r"@?[\w.\-]{1,60}")          # same shape gta6-clipper accepts in edit_streamers
MAX_NOTE, MAX_SOURCE = 400, 500                     # PeakCut caps user strings; the source does not

_lock = threading.Lock()
_saved: dict = {"at": None, "data": {}}
```

Signatures, in the order a caller meets them:

```python
def handle_of(url: str) -> Optional[Tuple[str, str]]:
    """(platform, handle) for a channel or live link, else None. Platform is 'youtube'|'twitch'|'kick';
    the handle is lowercased and keeps YouTube's leading '@'. A VOD id yields None."""

def rule(platform: str, handle: str) -> dict:
    """{"rule": Rule, "note": str, "source": str}. Never raises: a missing or broken table, an unknown
    key, or a rule value outside RULE_VALUES all return the 'unknown' row. The user's own file wins
    over the shipped table, key by key."""

def badge(platform: str, handle: str) -> dict:
    """What the page draws: rule() plus {"label": str, "tone": str, "can_clip": bool, "blocked": bool}.
    tone is one of '', 'ok', 'warn', 'bad' — the existing .pill classes. can_clip is False only for 'no'."""

def block(platform: str, handle: str, permission: bool = False) -> Optional[str]:
    """The sentence to show instead of starting work, or None. 'no' + no permission is the only case
    that returns text; 'ask' and 'unknown' never do."""

def table() -> dict:
    """The merged, normalised {key: {"rule","note","source"}} — shipped table overlaid with this user's
    file. Read through a mtime check, never a full parse per call."""

def public() -> dict:
    """For the settings page: {"rules": table(), "values": list(RULE_VALUES), "platforms": list(PLATFORMS),
    "counts": {rule: n}, "editable": True}. No paths, no owner id."""

def save_local(entries: dict) -> dict:
    """Merge the given {key: {"rule","note","source"}} into this user's clip_rules.json and return
    public(). Raises ValueError('...') on a bad key, platform, handle or rule value; writes tmp +
    os.replace under _lock; bumps ctx."""

def forget_local(key: str) -> dict:
    """Drop one key from this user's file (falling back to the shipped row) and return public()."""
```

State that must not float: the shipped table lives on the classpath (`Path(__file__).with_name("clip_rules.json")`),
this user's overrides live at `config.user_dir(ctx.uid()) / "clip_rules.json"` — matching
`creators._root()` (`creators.py:12-13`). Never a module-level global keyed by user.

### 4.3 The algorithms, exactly

`handle_of` — port `src_streamer` onto PeakCut's own platform vocabulary:

```python
def handle_of(url: str) -> Optional[Tuple[str, str]]:
    from . import creators
    url = str(url or "").strip()
    plat = creators.platform_key(url)              # creators.py:27 — 'youtube'|'twitch'|'kick'|''
    if not plat:
        return None
    path = urlparse(url if "://" in url else "https://" + url).path.strip("/")
    if plat == "youtube":
        m = re.match(r"(@[\w.\-]+)", path)         # @handle only: /channel/UC… and /c/name are not covered
        return ("youtube", m.group(1).lower()) if m else None
    seg = path.split("/")[0]
    if plat == "twitch" and seg in ("videos", "directory", "search"):
        return None                                # the source's (?!videos/) lookahead, widened
    return (plat, seg.lower()) if re.fullmatch(r"[\w.\-]{1,60}", seg) else None
```

`rule` — the normalisation, unchanged from `app.py:629`:

```python
def rule(platform: str, handle: str) -> dict:
    key = f"{str(platform).lower()}:{str(handle).lower()}"
    raw = table().get(key) or {}
    rule_ = raw.get("rule") if raw.get("rule") in ("allowed", "ask", "no") else "unknown"
    return {"rule": rule_, "note": str(raw.get("note") or "")[:MAX_NOTE],
            "source": str(raw.get("source") or "")[:MAX_SOURCE]}
```

`block` — the message, with PeakCut's voice and the source's structure:

```python
def block(platform: str, handle: str, permission: bool = False) -> Optional[str]:
    r = rule(platform, handle)
    if r["rule"] != "no" or permission:
        return None
    why = r["note"] or "public statement"
    return (f"{handle} does not allow clipping ({why})" +
            (f". {r['source']}" if r["source"] else "") +
            ". Only go on if you have their permission.")
```

`table` — cached, unlike the source, and merged:

```python
def table() -> dict:
    mine = _local()                                  # this user's file, re-read only when its mtime moves
    out = dict(_shipped())                           # shipped table, re-read only when its mtime moves
    out.update(mine)                                 # the user's row wins whole, per key
    return out
```

Both `_shipped()` and `_local()` use the `ai.py:47-60` idiom — `f.stat().st_mtime_ns` compared against
a cached stamp, `json.loads` only on change, `except (OSError, ValueError): {}`, and
`if not isinstance(data, dict): data = {}` so a hand-edited file holding `null`/`[]`/`3` cannot take
the server down (same guard as `_tr_saved`, server.py:1333-1334).

### 4.4 Server wiring — exact existing functions

**A. The gate, in `create_from_link` (server.py:718-745).** Insert between the `creator` resolution
and `jobs.create`, i.e. after server.py:732 and before the `with _create_lock:` at :734:

```python
found = rules.handle_of(url)
if found:
    denied = rules.block(found[0], found[1], bool(body.get("permission")))
    if denied:
        raise HTTPException(403, denied)
```

That mirrors `app.py:857-862` exactly: resolve `(platform, handle)` from the URL, block only when the
rule is `"no"` and `permission` is falsy, answer 403 with the sentence as `detail` — which is what
`web/index.html:911-915`'s `api()` already surfaces as `e.message` and the SPA shows through
`toast(e.message, "bad")`. No new error shape.

`/api/upload` (server.py:748) needs no gate: a file has no streamer. If a later pass wants one, take
optional `platform`/`handle` form fields and call the same two functions.

**B. The badge, in `_creator_rows()` (server.py:650-657).** Add one line inside the loop, before
`out.append`:

```python
row = {**c, "live_job": s.job["id"] if s else None, "log": creators.read_log(c["id"], 30)}
found = rules.handle_of(c.get("channel") or "")
row["clip"] = rules.badge(*found) if found else None
out.append(row)
```

Channel → handle is the right source of truth: `creators._fix` (creators.py:33-43) guarantees
`c["channel"]` is one of `c["channels"].values()` and `_channel_ok` (server.py:1045-1057) has already
refused any link that is not YouTube/Twitch/Kick, so `handle_of` gets a URL it can parse.

**C. The badge, in `jobs.public(job)` (jobs.py:152-166).** After the existing `out["ai"] = …` line,
before the `if job.get("status") == "queued":` block:

```python
found = rules.handle_of((job.get("source") or {}).get("url") or "")
out["clip"] = rules.badge(*found) if found else None
```

`jobs.py` already imports `creators`, `config`, `ctx`; add `rules` to that import list. This is the
only import cycle risk in the port — see §6.

**D. Live, advisory only.** `live.start_session` (live.py:779) must not be blocked: recording is
not publishing, and refusing to record would break `auto_watch`. Instead `POST /api/creators/{cid}/live`
(server.py:1212) may return the badge alongside the job, and `live._watch_one` (live.py:837) should
log one line through `creators.log(cid, ...)` when it starts recording a `"no"` streamer, so the
creator's activity feed shows why nothing was posted. Do not gate `jobs.create` itself — the gate
belongs on the user-facing entry point, exactly as in the source.

**E. Routes, following the transcription block.** New block in server.py, placed with the other
settings routes, `_admin()` gated like `transcribe_get`/`transcribe_put` (server.py:1350-1358):

```python
@app.get("/api/rules")
def rules_get(request: Request):
    _admin(request)                      # server.py:310
    return rules.public()

@app.put("/api/rules")
def rules_put(request: Request, body: dict = Body(...)):
    _admin(request)
    _throttle("rules:" + ctx.uid(), 60, 600)          # server.py:633
    entries = body.get("rules")
    if not isinstance(entries, dict) or len(entries) > 500:
        raise HTTPException(400, "Send the rules as an object, one per streamer.")
    try:
        return rules.save_local(entries)
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.delete("/api/rules/{key}")
def rules_delete(request: Request, key: str):
    _admin(request)
    return rules.forget_local(key)
```

`save_local` validates each key with `re.fullmatch(r"(youtube|twitch|kick):(@?[\w.\-]{1,60})", key.lower())`,
each `rule` against `RULE_VALUES`, and caps `note`/`source`, raising `ValueError` with a sentence —
which the route turns into the `HTTPException(400)` the brief mandates. `os.chmod(tmp, 0o600)` is
**not** needed here (no secret), but use `tmp.write_text(...)` + `tmp.replace(f)` under `_lock` so a
torn write cannot lose the file.

**F. SPA.** Four edits in `web/index.html`:

1. `const I = {` at :847 — add a `"shield"` path (Phosphor/Iconify 256-viewBox, matching the existing
   entries' style) before it can be referenced.
2. `const setTabs = () => [` at :2003 — append
   `...(S.status.user?.is_admin ? [["rules", "Clip rules", "shield", "Who allows clipping, and who does not"]] : [])`.
3. The settings route regex at :1317 — change `(ai|profile|security|apps|storage|transcribe)` to
   include `rules`, or the deep link silently falls back to the first tab.
4. `channelRows(c)` at :1822 — after the `pr.followers` span, insert
   `${c.clip ? `<span class="pill ${c.clip.tone}" title="${esc(c.clip.note || (c.clip.rule === "unknown" ? "We found no public clipping rule. Check their channel rules before you post." : ""))}">${esc(c.clip.label)}</span>` : ""}`,
   wrapped in an `<a href="${esc(c.clip.source)}" target="_blank" rel="noopener">` when a source exists —
   the same `<a>`-or-`<span>` fork as `app.html:748`. `.pill` and its modifiers already exist
   (:250-255); map `allowed→ok`, `ask→warn`, `no→bad`, `unknown→''`.
5. The permission confirm belongs next to the existing "Start recording" action, not in a settings
   form: before any `POST /api/jobs`, if `c.clip && c.clip.rule === "no"`, show a confirm with the
   note and send `permission: true` on yes — `clipOk` from `app.html:749` ported to the SPA's own
   `ask()`/`toast()` helpers.

### 4.5 Order of work

1. `rules.py` + `clip_rules.json` + `test_clip_rules.py` (no server, no UI — provable alone).
2. Gate in `create_from_link` (one call site, four lines).
3. Badge in `_creator_rows` and `jobs.public`.
4. Routes.
5. SPA chip + permission confirm.
6. Settings tab + editor.

Steps 1-3 deliver the whole promise; 4-6 are the editing surface.

---

## 5. Data files

**Shipped table — `peakcut/studio/clip_rules.json`.** Identical shape and content to
`gta6-clipper-main/clip_rules.json`: a flat object, keys `"<platform>:<handle>"` lowercase, values
`{"rule": "allowed"|"ask"|"no"|"unknown", "note": str, "source": str}`. 89 rows. Lives next to the
module so `Path(__file__).with_name(...)` finds it, ships in the package, and is replaced wholesale by
an update — matching the source comment "shipped clip_rules.json (updates refresh it)".

**Per-user overrides — `<DATA_DIR>/users/<uid>/clip_rules.json`.** Same schema, same key format,
written only by `rules.save_local`/`forget_local`. Sparse: only the keys that account has touched.
This path is chosen because `config.user_dir()` (config.py:146) already enforces
`[A-Za-z0-9_]{6,40}` on the uid, so a hostile key cannot escape the folder, and because
`creators._root()` (creators.py:12-13) uses the same `users/<uid>/…` layout. Do **not** put it in
`DATA_DIR` root — that is shared across accounts and would leak one person's overrides to everyone.

Validation rules for a written entry, all enforced in `save_local`:

| Field | Rule |
|---|---|
| key | `re.fullmatch(r"(youtube\|twitch\|kick):(@?[\w.\-]{1,60})", key.lower())`, ≤ 87 chars |
| `rule` | one of `RULE_VALUES`; anything else is a `ValueError`, not a silent `unknown` |
| `note` | `str`, trimmed, ≤ 400 chars |
| `source` | `str`, trimmed, must be `""` or start `http://`/`https://`, ≤ 500 chars |
| entries per call | ≤ 500 |
| entries per user file | ≤ 500 (reject the write, do not truncate silently) |

**No config key, no env var, no migration.** `DEFAULTS` in `creators.py` is not extended: the badge
is derived from the channel every time, so a creator row gains no stored field and no old
`creator.json` becomes invalid.

---

## 6. Risks

- **Reading the table per call.** The source reparses 7.5 KB from disk on every lookup
  (`app.py:626`). `_creator_rows` runs on every `/api/sync` (server.py:675-685), which the SPA polls
  every couple of seconds per open tab — that is O(users × polls) file reads. The mtime cache is not
  an optimisation, it is the port.
- **`table()` must be per-user.** A module-level `_RULES` global keyed by nothing would serve one
  account's overrides to another. Cache keyed by `ctx.uid()`, and drop the entry in `forget`/`save`.
- **A missing `ctx.uid()`.** Background threads (`jobs._worker`, `live.watch_loop`) have no request;
  `ctx.uid()` raises `NoUser`. `badge()`/`rule()` called from `jobs.public` run under the job's user
  context in practice, but a defensive `ctx.uid_or_none()` fallback to the shipped table only is
  cheaper than a `NoUser` escaping into a job's error field.
- **Import cycle.** `rules` imports `creators` (for `platform_key`), and `creators` imports only
  `config` and `ctx`. `jobs` imports `creators` already, so `jobs → rules → creators` is fine; but do
  not have `creators` import `rules` (that would close the loop). Import `creators` inside
  `handle_of`, as sketched in §4.3, if any cycle appears.
- **`platform_key` accepts subdomains.** It tests `"youtube" in h`, so `evil-youtube.com` and
  `notwitch.tv` parse as platforms. `handle_of` must not be reachable from an unvalidated URL: always
  call it after `media.site_allowed(url)` (server.py:724) or on a value that already went through
  `_channel_ok` (server.py:1045). An override key must be built from the validated pair only.
- **`"no"` is dead code today.** Zero shipped rows use it, so no test that only exercises the shipped
  table will ever hit `block()`. The block path must be tested against a written override, or it is
  unreviewed until the first update ships a `"no"` row.
- **`/api/upload` is ungateable.** A person can upload a streamer's VOD and clip it with no rule
  check. Accept that (the source has the same hole — `src_streamer` needs a URL) and say so in the
  help text rather than inventing a handle field nobody fills in.
- **Auto-watch keeps recording a `"no"` streamer.** Correct behaviour (recording ≠ publishing), but
  it must be visible: log it in the creator's activity feed, or the person will wonder why clips
  stop.
- **The message text is a legal-ish claim.** "Clips of them can get your channel copyright strikes"
  is the source's wording, not advice PeakCut can stand behind. Keep the block sentence factual
  ("X does not allow clipping … Only go on if you have their permission.") and let the note carry the
  streamer's own words.
- **Staleness.** The shipped table is a snapshot; a streamer can change their mind a day later. The
  `source` link is the mitigation and must always render when present — a badge with no source and a
  real note is worse than no badge.
- **No new dependencies.** `json`, `re`, `threading`, `pathlib`, `urllib.parse` — all already used in
  `studio/`. Nothing to add to `requirements.txt`.

---

## 7. Verification

**Unit, no server, no network** — `peakcut/tests/test_clip_rules.py`, in the shape of
`tests/test_ai.py` (set `PEAKCUT_DATA` to a temp dir, `sys.path.insert(0, ".")`, import
`studio.rules`, print `PASS`/`FAIL` lines, exit non-zero on failure):

```bash
cd peakcut && python tests/test_clip_rules.py
```

It must assert:

1. `rules.rule("twitch", "xQc")` → `{"rule": "ask", "note": "Clip away, just skip reposting …", "source": "https://prsek.substack.com/p/the-editor-manifesto"}` — the handle is lowercased and the note/source survive.
2. `rules.rule("twitch", "nobody-here")` → the `unknown` triple with `note == "" and source == ""`.
3. `rules.rule("twitch", "xqc")["rule"] == "ask"` after a 3-line table with `"rule": "yes"` written to the user file — proves the whitelist collapses junk to `unknown`.
4. `rules.block("twitch", "xqc") is None` (ask never blocks) and `rules.block("twitch", "nobody") is None`.
5. With an override `{"twitch:testno": {"rule": "no", "note": "N", "source": ""}}`:
   `rules.block("twitch", "testno")` returns `"testno does not allow clipping (N). Only go on if you have their permission."`
   and `rules.block("twitch", "testno", True) is None`.
6. `rules.handle_of("https://www.twitch.tv/xQc")` → `("twitch", "xqc")`;
   `rules.handle_of("https://www.twitch.tv/videos/123456")` → `None`;
   `rules.handle_of("https://kick.com/adinross")` → `("kick", "adinross")`;
   `rules.handle_of("https://www.youtube.com/@IShowSpeed")` → `("youtube", "@ishowspeed")` (the `@` is kept);
   `rules.handle_of("https://youtu.be/dQw4w9WgXcQ")` → `None`.
7. Corrupt the shipped file's sibling by writing `"[]"` to the user file, then `rules.table()` returns
   the shipped rows rather than raising.
8. `rules.save_local({"Twitch:XQC": {"rule": "allowed"}})` raises `ValueError` (the key must already be
   lowercase and the platform in the whitelist), and no file is left half-written (`tmp` gone).

**End to end against a throwaway server** — add to the `runs` list in `tests/run.py:49`:

```python
("streamer clip rules", ["tests/test_clip_rules_http.py", BASE, str(ROOT), sys.executable]),
```

with the HTTP test asserting: `PUT /api/rules` as admin with a `"no"` row for the signed-in account,
then `POST /api/jobs` with that streamer's channel URL and no `permission` → **403** whose `detail`
contains `"does not allow clipping"`; the same request with `"permission": true` → **200**;
`GET /api/creators` → the creator row carries `clip.rule == "no"` and `clip.can_clip is False`.

**Manual proof in the running app:**

```bash
cd peakcut && python -m studio.server
# open http://127.0.0.1:8765, Settings → Clip rules, add "no" for your own channel,
# then paste that channel's link on the Library page and confirm it refuses to queue.
```
