# 03 - Chat-spike detection without login

## 1. What it does

Finds the seconds where a stream's chat suddenly went much busier than *that same stream* normally is, and says what the chat was shouting ("KEKW", "W", "clip it"), all without a Twitch, YouTube or Kick account, an API key, or any third-party "hype score" service. For a recorded video it fetches the chat history around the part being clipped, cuts it into 10-second bins, and marks a bin as a spike only when it beats the stream's own median by a factor, sits in the top few percent of all bins, and contains a minimum number of messages — so a quiet stream and a hyperactive one both get sensible results. Each spike bin carries a ratio (how many times the normal message rate) and up to three top phrases, and those tags attach to the transcript lines they overlap. When chat is huge all the time the absolute thresholds stop working, so it falls back to comparing each bin against the five minutes immediately around it; on a live recording the same idea runs as a short rolling window instead. If no chat can be fetched — not a VOD, chat disabled, wrong window, network down — the clip is made exactly as it is today, with no chat signal at all.

## 2. Exact mechanics

Source: `gta6-clipper-main/chat.py` (420 lines). Everything below is the real algorithm; after reading it a build agent should not need the file open. The live variant is `gta6-clipper-main/live.py:11-29` and is described separately in 2.9 because it is a *different* algorithm with a different constant (3x, not 1.6x).

### 2.1 Global constants (chat.py:13-16)

```python
BIN = 10                                    # one bin = 10 seconds
CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"  # public web-player id, no login
HASH = "b70a3591ff0f4e0313d126c6a1502d79a1c02baebb288227c582044aa76adf6a"
                                            # shortcut: persisted-query hash can rotate;
                                            # re-read it from the twitch.tv network tab
```

`BIN = 10` is load-bearing everywhere: bin index `i`, bin start `start + i * BIN`, `tag_for`'s walk, `nb`'s ceiling division. Nothing else in the module may assume a different width.

`CLIENT_ID` is Twitch's public web-player client id — the same string every browser sends. `HASH` is a sha256 of the persisted GQL query text; it is not a secret and it is not stable across Twitch deploys (see 6).

### 2.2 Time parsing (chat.py:19-30)

```python
def hms(s):
    n = 0
    for p in str(s).split(":"):
        n = n * 60 + float(p)
    return int(n)

def parse_win(w):
    if not w:
        return 0, None
    a, b = w.split("-")
    return hms(a), hms(b)
```

- `hms("2:00:00") == 7200`; `hms("90") == 90`; `hms("1:30") == 90`. Parts are folded base-60 left to right, so `hms` accepts `SS`, `MM:SS` and `HH:MM:SS`. The `float` is only there so `"1.5"` works; `int()` truncates at the end, so `"0:00:01.9"` → `1`.
- `parse_win(None)` / `parse_win("")` → `(0, None)` — "the whole thing", which is only legal for YouTube, never for a Twitch VOD.
- `parse_win("2:00:00-2:20:00")` → `(7200, 8400)` (asserted in `selftest`, chat.py:402).
- `parse_win` splits on a single `-` and will raise `ValueError` on `"1:00"` alone. In PeakCut this must become a validated user error, not an exception that escapes a worker.

### 2.3 Fetching a Twitch VOD's chat with no login (chat.py:33-62)

The docstring states the constraint: *"One request at a time. The cursor path needs an integrity token, so page by offset instead: each reply is ~30 s of chat, next offset = last message second, dedupe by id."*

Request — a persisted-query POST to the public GQL endpoint:

```
POST https://gql.twitch.tv/gql
Client-ID: kimne78kx3ncx6brgo4mv6wki5h1ko
Content-Type: application/json

[{"operationName": "VideoCommentsByOffsetOrCursor",
  "variables": {"videoID": vid, "contentOffsetSeconds": off},
  "extensions": {"persistedQuery": {"version": 1, "sha256Hash": HASH}}}]
```

The reply is a **list** whose first element holds the data: `json[...][0]["data"]["video"]["comments"]`. Each comment is `{"id": ..., "_offsetSeconds": ..., "message": {"fragments": [{"text": ...}, ...]}}`.

The loop, verbatim in shape (chat.py:44-62):

```python
out, seen, off = [], set(), start
while off < end:
    for t in range(4):
        try:
            ... urlopen(req, timeout=30) ...
            break
        except Exception:
            time.sleep(2 ** t)
            if t == 3:
                raise
    for n in c:
        if n["id"] in seen:
            continue
        seen.add(n["id"])
        s = int(n["_offsetSeconds"])
        last = max(last, s)
        if start <= s < end:
            out.append((s, "".join(f["text"] or "" for f in n["message"]["fragments"]).strip()))
            new = True
    off = last if new else off + 1   # a page that is all one second repeats; skip ahead 1 s (loses a few msgs)
    time.sleep(delay)                # delay = 0.15 default
```

Load-bearing numbers and properties:

| Thing | Value | Why it matters |
|---|---|---|
| retries | 4 (`range(4)`) | the 4th failure re-raises |
| backoff | `time.sleep(2 ** t)` → 1, 2, 4 s before attempts 2, 3, 4 | not exponential-from-zero |
| HTTP timeout | `30` s per request | |
| page size | ~30 s of chat per reply | so a 20-minute window is ~40 requests |
| inter-page delay | `0.15` s | keeps it under Twitch's burst limit |
| dedupe key | `n["id"]` | pages overlap; the same message appears in two replies |
| advance rule | `off = last if new else off + 1` | if a whole page was already seen (`new` stays falsy) step forward one second, otherwise jump to the newest second seen |
| window filter | `start <= s < end` | half-open; the last second is excluded |
| text join | `"".join(fragment["text"] or "")` | emotes arrive as fragments with `text` present; an emote-only message can yield `""` after `.strip()` |

The `off + 1` fallback is a deliberate bug-avoidance shortcut, not a bug: without it, a video whose chat is silent for 40 minutes would re-request the same page forever. It skips at most a second of messages each time it fires.

`fetch_twitch` requires `end` to be a real integer — the whole-video case is rejected upstream in `fetch`.

### 2.4 Fetching a YouTube live-chat replay (chat.py:65-90)

yt-dlp can write the `live_chat` subtitle track of a *finished* livestream. It has no window option, so the entire chat is downloaded and then cut.

```python
d = tempfile.mkdtemp(prefix="chat_")
r = subprocess.run([sys.executable, "-m", "yt_dlp", "-q", "--skip-download", "--write-subs",
                    "--sub-langs", "live_chat", "--no-warnings",
                    "-o", d + "/c.%(ext)s", url], capture_output=True, timeout=300)
```

- `timeout=300`. On `subprocess.TimeoutExpired` it raises `RuntimeError("chat download stalled for 300 s, stopped (yt-dlp live_chat); Short continues without chat")`.
- It then looks for `Path(d).glob("*live_chat.json")`. Missing → `RuntimeError("no live_chat for this video (not a live replay, or chat off): " + r.stderr[-300:])`.
- Each line of that file is one JSON object. The parser (chat.py:78-90):

```python
act = json.loads(line)["replayChatItemAction"]
ms = int(act["videoOffsetTimeMsec"])
for a in act["actions"]:
    m = a.get("addChatItemAction", {}).get("item", {}).get("liveChatTextMessageRenderer")
    if not m:
        continue
    txt = "".join(x.get("text") or (x.get("emoji", {}).get("shortcuts") or [x.get("emoji", {}).get("emojiId", "")])[0]
                  for x in m["message"].get("runs", []))
    if ms / 1000 >= start and (end is None or ms / 1000 < end):
        out.append((ms // 1000, txt.strip()))
except (KeyError, ValueError):
    continue
```

Two conversions must not be confused: the **filter** divides (`ms / 1000 >= start`, float compare), the **stored second** floors (`ms // 1000`). An emote run has no `text`; it falls back to `emoji.shortcuts[0]`, then `emoji.emojiId`. Any line that is not a `replayChatItemAction` (banners, `liveChatViewerEngagementMessageRenderer`, removed-message actions) is skipped by the `m` test or the `except`.

Note the whole file is materialised on disk before parsing: a 6-hour stream's live chat is routinely hundreds of MB. `tempfile.mkdtemp` here is never removed — the source leaks it. PeakCut must not.

### 2.5 Dispatch (chat.py:93-99)

```python
m = re.search(r"twitch\.tv/videos/(\d+)", url)
if m:
    if end is None:
        raise SystemExit("Twitch VODs can be 35 h: give a START-END window")
    return fetch_twitch(m.group(1), start, end)
return fetch_youtube(url, start, end)
```

Anything that is not a `/videos/<digits>` Twitch URL is handed to yt-dlp. That covers YouTube, and also Twitch *clips* and Kick — which yt-dlp will fail to give `live_chat` for, producing the "no live_chat" `RuntimeError`. `SystemExit` is the single worst thing in the file for a server (see 6).

### 2.6 `top_phrases` (chat.py:106-120)

Signature: `top_phrases(msgs, n=3, min_count=3) -> [(phrase, count)]`. A phrase counts **once per message**, not once per occurrence — 61 messages containing `KEKW` is `61`, and one message containing it three times is still `1` (the selftest asserts exactly `61`).

```python
c, shown = Counter(), {}
for s, t in msgs:
    w, hit = t.split(), set()
    for x in w:
        k = x.lower().strip(".,!?")
        if k in HYPE:
            hit.add(k)
    if "clip it" in t.lower() or "clip that" in t.lower():
        hit.add("clip it")
    if w and len(t) <= 25 and len(w) <= 4:
        hit.add(w[0].lower() if len(set(x.lower() for x in w)) == 1 else t.lower())
    for k in hit:
        c[k] += 1
        shown.setdefault(k, next((x for x in w if x.lower().strip(".,!?") == k), t.upper() if k == "clip it" else k))
return [(shown[k].upper() if shown[k].lower() in HYPE else shown[k], v) for k, v in c.most_common(n) if v >= min_count]
```

Rules, spelled out:

1. **Hype words.** A whitespace token, lowercased, with `.,!?` stripped from the ends, is a hit if it is in `HYPE`. Stripping is `strip`, not `lstrip`, so `"KEKW!!"` → `"kekw"` hits, but `"..."` alone → `""` misses.
2. **Clip demands.** Any message whose lowercase text contains `clip it` or `clip that` (including inside a longer sentence) scores the phrase `clip it` once.
3. **Short messages are their own phrase.** If the message is at most **25 characters** and at most **4 words**, it contributes a phrase: if every word is the same when lowercased, that word (`w[0].lower()`); otherwise the **whole lowercased message** (`t.lower()`). This is how `LETSGO`, `GG`, `CLIP IT` and `LMAO` get counted without being in `HYPE`, and why `"KEKW KEKW KEKW"` still lands on the single key `kekw`. A message longer than 25 chars or 5+ words contributes nothing here — that is the noise filter the selftest checks with `top_phrases(["a long sentence that should be ignored by the filter"] * 9) == []`.
4. **Display casing.** `shown` keeps the first original spelling seen for a key: it searches the same message's tokens for the one that normalises to the key, else `"clip it"` → `t.upper()`, else the key itself. The final pass upper-cases any phrase whose lowercase form is in `HYPE`, so `kekw` is displayed `KEKW`, while `"clip it"` (which is *not* in `HYPE` — `clipit` is) keeps whatever `shown` recorded, normally the uppercased message text.
5. **`min_count=3`** drops anything seen fewer than three times; `n=3` keeps at most the three commonest. Empty chat → `[]`.

The `HYPE` table in full (chat.py:102-103), 33 entries, verbatim — reproduce it exactly, including the two odd ones:

```python
HYPE = set("""
kekw lul lulw lol lmao lmfao omegalul icant omg wtf pog poggers pogchamp pogu
w ww www l ll d: monkas widepeepohappy clipit letsgo nooo noooo no? holy bruh
sheesh insane cinema cooked
""".split())
```

| Group | Entries |
|---|---|
| laughing | `kekw`, `lul`, `lulw`, `lol`, `lmao`, `lmfao`, `omegalul`, `icant` |
| shock | `omg`, `wtf`, `monkas`, `sheesh`, `insane`, `holy`, `bruh` |
| hype | `pog`, `poggers`, `pogchamp`, `pogu`, `letsgo`, `widepeepohappy`, `cinema`, `cooked` |
| elongation | `w`, `ww`, `www`, `l`, `ll`, `nooo`, `noooo` |
| demand | `clipit` |
| puzzling | `d:`, `no?` |

`d:` survives token normalisation because `:` is not stripped. `no?` **cannot** be reached through rule 1 — `strip(".,!?")` removes the question mark first, so the token becomes `no`, which is not in the table. It only ever matches through rule 3, where the raw lowercased message is used (`"no?"` → `"no?"` → in `HYPE`). Port it as-is, or drop it; do not "fix" it into `no`, which would make every negation in chat a hype word.

### 2.7 `find_spikes` — the core (chat.py:123-145)

Signature: `find_spikes(msgs, start, end, pct=97, mult=1.6, min_msgs=5, local=True) -> ([(bin_start, count, ratio, top_phrases)], global_median)`.

Docstring, verbatim: *"Spike = bin >= max(mult\*median, pct-percentile, min_msgs). Median over ALL bins incl. empty ones (ratio = to that median). Huge chats (global median >= 20 msgs per bin, ~2/s) are busy all the time: a bin that is the top 2 % of ALL bins when measured against the median of the 5 minutes around it (>= 1.25x and beyond Poisson noise) also counts (ratio = to that LOCAL median). Slow chats stay strict."*

Step by step:

```python
nb = max(1, -(-(end - start) // BIN))          # ceiling division: number of bins
for s, t in msgs:
    i = int((s - start) // BIN)
    if 0 <= i < nb:
        counts[i] += 1
        texts[i].append(t)
med = statistics.median(counts)                 # over ALL nb bins, empty ones included
p = sorted(counts)[min(nb - 1, int(nb * pct / 100))]
thr = max(mult * max(med, 1), p, min_msgs)
hit = {i: c / max(med, 1) for i, c in enumerate(counts) if c >= thr}
if local and med >= 20:
    loc = {}
    for i, c in enumerate(counts):
        lm = statistics.median(counts[max(0, i - 30):i] + counts[i + 1:i + 31] or [c])
        if i not in hit and c >= 1.25 * lm and c >= lm + 3 * lm ** .5:
            loc[i] = c / max(lm, 1)
    for i in sorted(loc, key=loc.get, reverse=True)[:max(3, nb // 50)]:
        hit[i] = loc[i]
return [(start + i * BIN, counts[i], r, top_phrases(texts[i])) for i, r in sorted(hit.items())], med
```

The numbers that matter, with the reason each is what it is:

| Symbol | Value | Meaning |
|---|---|---|
| `BIN` | 10 s | bin width; a spike marks a 10-second stretch |
| `nb` | `ceil((end-start)/10)`, min 1 | bins are pre-created as zeros, so **empty bins count in the median** |
| `pct` | 97 | take the bin count at position `int(nb*97/100)` in the sorted array |
| `p` index clamp | `min(nb-1, ...)` | never index past the end |
| `mult` | 1.6 | a spike must be at least 1.6× the stream's own median |
| `min_msgs` | 5 | a spike bin must hold at least five messages, full stop |
| `thr` | `max(1.6*max(med,1), p, 5)` | all three gates must pass simultaneously |
| `ratio` | `count / max(med, 1)` | the "xN" shown to the user and to the AI |
| local gate | `med >= 20` | only huge chats (≈2 msgs/s per 10 s bin) get the local rule |
| local window | 30 bins either side = ±5 min | `counts[i-30:i] + counts[i+1:i+31]` — 60 bins, the current bin excluded |
| local multiplier | `1.25` | only 1.25× the local median, because the global gates are unreachable there |
| Poisson floor | `lm + 3*sqrt(lm)` | with `lm > 0`, so quiet neighbourhoods cannot fire on a rounding artefact |
| local cap | `max(3, nb // 50)` | keep only the strongest few local bins; `nb // 50` is one per 500 s |

Consequences a build agent must preserve:

- **The median is the baseline, not the mean.** One 300-message raid cannot drag the threshold up the way a mean would.
- **`max(med, 1)`** means a stream whose median is 0 (mostly silent chat) is measured against 1, so the ratio for a bin of 3 is `3.0`, and `thr` is at least `max(1.6, p, 5)`.
- **The percentile makes it relative.** `p` is the 97th-percentile bin count, so on a busy video at most ~3 % of bins clear that gate anyway; `mult` then filters within them. Both are needed: `mult` alone fires constantly on spiky chat, `p` alone fires on every video regardless of how dead it is.
- **`local` never loosens a slow chat.** With `med < 20` the block is skipped entirely, so `local=True` and `local=False` return byte-identical results. The selftest asserts this (`chat.py:396-398`).
- **The local rule is additive, not a replacement.** `i not in hit` keeps the strict hits and adds at most `max(3, nb // 50)` more.
- **Returned order is by bin start** (`sorted(hit.items())`), not by strength.
- **The returned `med` is the global median in messages per 10 s bin**, and it is the number that decides whether the local rule applies at all. Callers use it for the "how busy is this stream" readout.

Worked example, the one the selftest plants (chat.py:372-380): 600 s → 60 bins; a baseline of up to two messages per second puts `med ≈ 10` messages per bin; 60 `KEKW` messages land on seconds 300-309 (all of bin 30), plus one `KEKW KEKW KEKW` and eight `W`s, so bin 30 holds roughly 70 chat messages on top of the baseline chatter — about 78 in a seeded run. `p97` is in the mid-teens for that shape, so `thr = max(1.6*10, p97, 5) ≈ 16`, bin 30 fires with `ratio ≈ 7.8`, and `top_phrases` starts with `("KEKW", 61)` — 61 because 60 messages plus the one triple, counted **once per message**. The numbers move with the random baseline; the assertion that matters is that bin 30 is the *only* hit and that `ratio >= 3`.

### 2.8 `chat_tags` and `tag_for` (chat.py:148-160)

```python
def chat_tags(url, window=None, msgs=None):
    start, end = parse_win(window)
    end = end if end is not None else (max((s for s, _ in msgs), default=start) + 1)
    sp, med = find_spikes(msgs, start, end)
    return {b: f" [CHAT x{r:.1f}" + (": " + ", ".join(f'"{p}" x{n}' for p, n in tp) if tp else "") + "]"
            for b, c, r, tp in sp}
```

The tag string is a **fixed format** other code parses, so it must not be restyled:

| Case | Result |
|---|---|
| spike, ratio 4.0, phrases | ` [CHAT x4.0: "KEKW" x40, "W" x12]` |
| spike, ratio 4.0, no qualifying phrases (< 3 repeats) | ` [CHAT x4.0]` |
| not a spike | key absent |

Note the **leading space** and the `x{r:.1f}` — one decimal, always. `tag_for` regex-parses that decimal back out, so a changed format silently breaks every tag lookup.

```python
hit = [tags[b] for b in range(int(s // BIN) * BIN, int(e) + 1, BIN) if b in tags]
return max(hit, key=lambda t: float(re.search(r"x([\d.]+)", t).group(1))) if hit else ""
```

A transcript line `[s, e]` takes the **strongest** (largest ratio) spike bin it overlaps, not the first. The walk starts at `int(s // BIN) * BIN` — the bin containing the line's start, by absolute video time, **not** by offset from the window start. So `chat_tags`' keys are absolute seconds (because `find_spikes` adds `start + i * BIN`), and a caller that passes a window must keep the same origin for both.

### 2.9 The live variant — different algorithm, 3x (live.py:11-29)

This is the code the brief's "3x the stream's own baseline" refers to, and it is **not** `find_spikes`:

```python
BIN, KEEP, PRE, POST, WIN, COOL = 10, 600, 25, 10, 10, 60   # live.py:11
# bin s, seconds of video kept, clip s before/after a spike, spike window s, cooldown s
```

`class Detector` (live.py:13-26), docstring verbatim: *"Spike = different chatters in the last WIN s >= ratio x median of the previous 5 min's WIN-s counts, and >= min_n. Needs 2 min of history. People, not messages: one spammer or a bot can't fake a spike."*

```python
def __init__(s, ratio=3.0, min_n=15): ...

def check(s, now):
    while s.ts and s.ts[0][0] < now - 330:
        s.ts.popleft()
    cnt = lambda a, b: len({n for t, n in s.ts if a < t <= b})
    cur = cnt(now - WIN, now)
    hist = [cnt(now - WIN * (i + 2), now - WIN * (i + 1)) for i in range(30) if now - WIN * (i + 2) >= s.ts[0][0]]
    if len(hist) < 12:
        return None
    base = statistics.median(hist)
    if cur >= s.min_n and cur >= s.ratio * max(base, 1) and now - s.last > COOL:
        s.last = now
        return cur, base
```

| Constant | Value | Meaning |
|---|---|---|
| `WIN` | 10 s | one counting window |
| `ratio` | 3.0 | three times the median of the preceding five minutes |
| `min_n` | 15 | at least fifteen **distinct people** |
| history | 30 windows back, needs 12 | 12 windows = 120 s = "2 min of history" |
| retention | `now - 330` | 5.5 min, the 5-minute baseline plus slack |
| `COOL` | 60 s | one spike per minute at most |

Two tunings worth carrying: a spam-flooded chat wants `ratio=2, min_n=40` (`SKILL-REFERENCE.md:74`), and under about 30 messages/minute spikes simply will not come (`SKILL-REFERENCE.md:72`). People, not messages, is the whole point: `cnt` counts a *set* of nicknames.

Bot filtering (live.py:28-29), to be applied before counting:

```python
BOTS = {"nightbot", "streamelements", "streamlabs", "moobot", "fossabot", "wizebot",
        "botrixoficial", "sery_bot", "kofistreambot", "pokemoncommunitygame"}

def is_bot(nick, text):
    return nick.lower() in BOTS or "http" in text or ".com/" in text or text.startswith("!")
```

### 2.10 Reference assertions (chat.py:369-403)

`selftest()` is the specification in executable form. These exact assertions must pass after the port, and they are what section 7 ports:

```python
msgs = [(s, "hello there") for s in range(0, 600) for _ in range(random.choice([0, 1, 1, 2]))]
msgs += [(300 + i % 10, "KEKW") for i in range(60)] + [(301, "KEKW KEKW KEKW")] + [(305, "W")] * 8
sp, med = find_spikes(msgs, 0, 600)
assert [b for b, *_ in sp] == [300]
assert sp[0][3][0][0] == "KEKW" and sp[0][3][0][1] == 61 and sp[0][2] >= 3

assert top_phrases(["a long sentence that should be ignored by the filter"] * 9) == []
assert top_phrases(["KEKW that was wild", "kekw", "KEKW KEKW KEKW", "clip it", "CLIP IT bro",
                    "clip it now", "nothing special here at all"]) == [("KEKW", 3), ("CLIP IT", 3)]
assert tag_for({300: " [CHAT x5 KEKW]"}, 296, 304) == " [CHAT x5 KEKW]"
assert tag_for({300: "x"}, 0, 10) == ""
assert parse_win("2:00:00-2:20:00") == (7200, 8400)

big = [(s, "x") for s in range(0, 1200) for _ in range(random.choice([6, 8, 8, 10]))] + \
      [(600 + i % 10, "LOL") for i in range(45)]
assert find_spikes(big, 0, 1200, local=False)[0] == []            # strict gates: nothing
assert [b for b, *_ in find_spikes(big, 0, 1200)[0]] == [600]     # local gates: the planted bin

slow = [(s, "x") for s in range(0, 1200)] + [(600 + i % 10, "x") for i in range(9)]
assert find_spikes(slow, 0, 1200)[0] == find_spikes(slow, 0, 1200, local=False)[0]
```

Read them as four guarantees: (a) a planted spike in a normal chat is found and nothing else is; (b) phrases are counted per message and filtered by length; (c) a huge chat yields **nothing** without the local rule and exactly the planted bin with it; (d) a slow chat is unaffected by the local rule.

## 3. PeakCut today

There is chat plumbing, but only for a **live Twitch recording**, only as a running count, and none of it is a spike detector a job can use.

- **`peakcut/studio/live.py:318-353` `Session._chat(channel)`** already reads Twitch chat anonymously — TLS to `irc.chat.twitch.tv:6697`, `NICK justinfan{int(time.time()) % 90000 + 10000}`, `JOIN #channel`, no token. Same no-login trick as the port, for the *live* case only. It fills `self.chat[second] += 1` (`live.py:133`) and `self.chat_users[second] = {nicks}` (`live.py:134`) with nickname regex `_NICK = re.compile(r"(?m)^:([A-Za-z0-9_]{2,25})!")` (`live.py:26`), pruning at `CHAT_KEEP = 600` s (`live.py:27`, `_trim_names` `live.py:33-40`). `Session.start()` only starts this thread for a URL matching `^https?://(?:www\.)?twitch\.tv/([A-Za-z0-9_]+)` (`live.py:218-221`) — **Twitch only, live only**.
- **`peakcut/studio/live.py:355-373` `Session._chat_spike(self, s, e) -> bool`** is a real 3×-of-baseline check, top-to-bottom the same idea as `live.py` in the source: `avg = self.chat_total / elapsed`, `rate = sum(self.chat.get(t,0) for t in range(a, b+1)) / (b-a+1)`, `if rate <= max(3 * avg, 1.0): return False`, then a people check `p_rate >= max(2.0, 1.5 * p_avg)`. **It is never called** — grep across `studio/` finds only the definition. Dead code.
- **`peakcut/studio/live.py:437`** is the only chat threshold actually live in production: `if chat_now >= max(1.5, chat_base * (1 + pct))` with `chat_base = sum(chat[:-10]) / max(1, len(chat) - 10)` (`live.py:435`), `chat_now = sum(chat[-8:]) / 8` (`live.py:436`, comment *"chat is bursty, so look at a slightly longer stretch"*), and `pct = self.JUMP = 0.6` (`live.py:408`) — i.e. **1.6× the last ~3 minutes**, the same multiplier as `find_spikes`' `mult`, but computed on a 190-second rolling window with no percentile, no minimum count, no phrase extraction and no per-bin output. It only ever produces the string `why.append(f"chat +{round((chat_now / max(chat_base, 0.01) - 1) * 100)}%")` (`live.py:438`).
- **`peakcut/studio/brain.py:153` `make_lines(words, loud=None, chat=None)`** already has the seam: `live.py` line dicts carry `"chat": bool(chat and chat(s, e))` (`brain.py:165`). But it is **only consumed as one boolean marker** in `_fmt` (`brain.py:116-118`: `{'(CHAT) ' if l.get('chat') else ''}`), and on the VOD path it is never supplied — `brain.py:275` calls `make_lines(words, z)` with no `chat`. No phrase text ever reaches the model.
- **`peakcut/studio/jobs.py:738-739`** is the VOD call site: `brain.find_clips(bw, db[s0:...], (b-a)/16000, job["title"], job["uploader"], quota, min_len, max_len, notes.append, game=game)`. No chat argument, no chat fetch, nothing in `job["ai"]` about chat.
- **`peakcut/studio/brain.py:454` `judge_signals(z, chat, start, now, unit="messages")`** does use chat counts — but only from the live path (`live.py:494`), only as 2-second sums in a text table, no phrases, and `unit` merely chooses the words "people talking" vs "chat messages" (`brain.py:468`).
- **Nothing anywhere extracts phrases.** No `HYPE`, no `KEKW`, no `top_phrases`, no `pct`/percentile helper in `peakcut/studio/`.
- **No VOD chat backfill of any kind.** Twitch GQL is never contacted; `media.py` only knows yt-dlp, and its `info()` (`media.py:118`) returns title/uploader/duration/is_live/thumbnail/kind — no chat.
- **Host allow-list already admits the sites:** `config.py:191-192 ALLOWED_SITES` defaults to `"youtube.com,youtu.be,twitch.tv,kick.com"`, so no validation change is needed for a chat URL.

Summary of the gap: PeakCut can count live Twitch messages per second and shout when the last eight seconds are 1.6× the last three minutes. It cannot read chat from a *finished* video, has no baseline that is stable enough to compare a quiet stream with a busy one, produces no phrase text, and puts nothing chat-derived into the picking prompt beyond a flag that the VOD path never sets.

## 4. Port plan

New module: **`peakcut/studio/chat.py`**, one concern, no new dependency (`httpx` and `yt-dlp` are already pinned). Docstring style follows `quality.py` / `facecam.py`: state the metric, then the numbers. Pure functions first, I/O last, so `tests/run.py` (which blanks every key and contacts nothing) can exercise all of the algorithm.

### 4.1 Module constants

```python
BIN = 10
CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"
HASH = "b70a3591ff0f4e0313d126c6a1502d79a1c02baebb288227c582044aa76adf6a"
HYPE = frozenset("...".split())        # all 33 entries from 2.6, verbatim
BOTS = frozenset({...})                # all 10 entries from 2.9
MAX_MINUTES = 30                       # hard cap on any window we will page through (see 6)
PAGE_DELAY = 0.15
RATIO = 3.0                            # live people/10 s ratio, source live.py:13
MIN_PEOPLE = 15
```

`HYPE` as a `frozenset` (not `set`) so no caller can mutate the module's table. Keep the two broken-looking entries (`d:`, `no?`) exactly as they are and add a comment saying why, or every future reader will "fix" them.

### 4.2 Time parsing

```python
def hms(s: str | int | float) -> int: ...
def parse_win(w: str | None) -> tuple[int, int | None]: ...
```

`hms` keeps the base-60 fold and the trailing `int()`. `parse_win` keeps `(0, None)` for empty input but **must raise `ValueError("Give a window like 2:00:00-2:20:00.")`** instead of letting `w.split("-")` blow up with a one-value unpack, and must reject `b <= a`. The route converts that `ValueError` to `HTTPException(400)`.

### 4.3 The pure core

```python
Msg = tuple[int, str]          # (absolute second, message text)

def spike_bins(counts: Sequence[int], start: int, *, pct: float = 97, mult: float = 1.6,
               min_msgs: int = 5, local: bool = True) -> tuple[dict[int, float], float]:
    """{bin_index: ratio} plus the global median, for an already-binned chat.

    counts[i] is how many messages landed in the 10 s bin beginning start + i*BIN.
    Empty bins are real bins and count towards the median and the percentile.
    """

def find_spikes(msgs: Sequence[Msg], start: int, end: int, pct: float = 97, mult: float = 1.6,
                min_msgs: int = 5, local: bool = True
                ) -> tuple[list[tuple[int, int, float, list[tuple[str, int]]]], float]:
    """[(bin_start_second, count, ratio, top_phrases)] by time, plus the global median."""

def top_phrases(msgs: Iterable[Msg], n: int = 3, min_count: int = 3) -> list[tuple[str, int]]: ...

def chat_tags(msgs: Sequence[Msg], start: int = 0, end: int | None = None) -> dict[int, str]:
    """{bin_start_second: ' [CHAT x4.0: "KEKW" x40]'}"""

def tag_for(tags: dict[int, str], s: float, e: float) -> str: ...

def selftest() -> int:
    """Run the reference assertions; return the number that passed, raise AssertionError on the first failure."""
```

Two deliberate changes from the source, both required for testability and for the live path:

- **`chat_tags` takes `msgs`, not a URL.** The source's `chat_tags(url, window, msgs)` mixes fetching into the pure layer, so it can never run in a test that forbids network. Splitting it means `tests/test_chat.py` covers 100 % of the algorithm with zero I/O, and the fetcher becomes a separate, individually-callable function.
- **`spike_bins` is extracted** from `find_spikes` and is public. `find_spikes` becomes binning + `spike_bins` + `top_phrases`. The live path (`peakcut/studio/live.py`) can then call `spike_bins` over its `[chat.get(t, 0) for t in range(n - window, n)]` slice and get the same thresholds instead of reimplementing them.

`tag_for` keeps the regex exactly: `re.search(r"x([\d.]+)", t)`, and returns `""` when nothing overlaps. Its bin walk keeps `int(s // BIN) * BIN` and `int(e) + 1` — this is the only place where absolute-time binning meets a float transcript timestamp.

### 4.4 Fetchers (the only I/O)

```python
def fetch_twitch(vid: str, start: int, end: int, *, delay: float = PAGE_DELAY,
                 timeout: float = 30.0, log: Callable[[str], None] = print) -> list[Msg]: ...

def fetch_youtube(url: str, start: int = 0, end: int | None = None, *,
                  timeout: float = 300.0) -> list[Msg]: ...

def fetch(url: str, start: int = 0, end: int | None = None, *,
          log: Callable[[str], None] = print) -> list[Msg]:
    """Twitch VOD chat, or a YouTube live-chat replay. Raises ChatError when there is none."""
```

Hard requirements on the port:

1. **Use `httpx`, not `urllib.request`.** Every other outbound call in the app is httpx (`ai.py:20`, `transcribe.py:57`, `server.py:1407`), and the pinned `httpx==0.28.1` is already installed. Same headers, same JSON body, `httpx.post(...)` inside a bare `except httpx.HTTPError`.
2. **Cap the work.** Clamp `end - start` to `MAX_MINUTES * 60` and raise `ChatError(f"That is more than {MAX_MINUTES} minutes of chat; narrow the range.")` beyond it. Also stop after a page budget (`(end - start) // 25 + 40` requests) so a pathological video cannot spin forever.
3. **`ChatError(Exception)`** replaces every `RuntimeError`, `SystemExit` and bare raise on the "there is no chat here" path. `SystemExit` must never escape: a worker thread swallowing it kills the job's whole process (`jobs.py` runs in threads, but the test runner and any in-process call do not).
4. **`fetch` must not raise for a non-Twitch, non-YouTube URL** — raise `ChatError("Chat is only available for Twitch VODs and YouTube replays.")`, so a Kick or Twitch-clip job degrades instead of failing.
5. **Temp files go to `config.TMP_DIR`, not `tempfile.mkdtemp()`**, and are removed in a `finally`. Use `tempfile.mkdtemp(dir=config.TMP_DIR, prefix="chat_")` + `shutil.rmtree(..., ignore_errors=True)`.
6. **Call yt-dlp in-process** via `media._ydl({...})` (`media.py:98`) with `{"skip_download": True, "writesubtitles": True, "subtitleslangs": ["live_chat"], "outtmpl": ..., "quiet": True}`, exactly as `media.youtube_words` (`media.py:127`) already does — rather than `subprocess [sys.executable, "-m", "yt_dlp"]`, which re-resolves the interpreter and bypasses `NO_WINDOW` on Windows. Keep a wall-clock guard (`timeout=300` equivalent) around it.
7. **Twitch paging keeps `off = last if new else off + 1` and the `seen` id set verbatim.** Both are load-bearing; without the `+1` a silent stretch loops forever.

### 4.5 The adapter a job calls

```python
@dataclasses.dataclass(frozen=True)
class ChatMap:
    bins: dict[int, str]      # absolute bin start -> " [CHAT x4.0: "KEKW" x40]"
    ratios: dict[int, float]  # absolute bin start -> ratio
    med: float                # messages per 10 s bin, the stream's own baseline
    total: int                # messages read
    seconds: int              # window length actually read

    def between(self, s: float, e: float) -> str:
        """The strongest spike tag overlapping [s, e], or ''."""

    def flag(self, s: float, e: float) -> bool:
        """True when a spike bin overlaps [s, e]. Matches brain.make_lines' chat= contract."""


def for_job(url: str, start: float, end: float, *, log: Callable[[str], None] = print) -> ChatMap | None:
    """Chat spikes for one job window. Never raises: returns None when chat is off, unsupported,
    too short, or the fetch failed - the job then behaves exactly as it does today."""
```

`for_job` is the only function `jobs.py` needs to know about. Its contract, in order:

1. `if not settings()["enabled"]: return None` (see 4.6) — off by default.
2. `if not url: return None` — an uploaded file has no chat.
3. `if end - start < 120: return None` — under two minutes there is no baseline; the median would be one bin.
4. `msgs = fetch(url, int(start), int(end), log=log)` inside `try/except ChatError/Exception`, logging `log(f"No chat for this part: {e}")` and returning `None`. **A chat failure must never fail a job.**
5. `sp, med = find_spikes(msgs, int(start), int(end), pct=..., mult=..., min_msgs=..., local=...)` with the thresholds from `settings()`.
6. Return `ChatMap(bins=chat_tags(msgs, int(start), int(end)), ratios=..., med=med, total=len(msgs), seconds=int(end - start))`.

`flag(s, e)` = `self.between(s, e) != ""`, and `between` = `tag_for(self.bins, s, e)`.

### 4.6 Settings module (in `chat.py`, mirroring `ai.py`)

```python
def _file() -> Path:            # config.DATA_DIR / "chat.json"
def saved() -> dict:            # file over env, always a full dict, never raises
def public() -> dict:           # what the settings page may see; there is no secret here
def save(body: dict) -> dict:   # validate, clamp, write under _lock, return public()
```

Follow `ai.py:45-70` exactly in shape: module-level `_lock = threading.Lock()`, a `{"at": None, "data": {}}` cache keyed on `st_mtime_ns`, and a `saved()` that coerces a non-dict JSON to `{}` — the comment at `server.py:1334` (*"a hand-edited tr.json holding null, [], 3 or "text" must not stop the server booting"*) applies here too. `save()` validates and raises `ValueError` with user-readable text; the route turns it into `HTTPException(400, str(e))`. Because nothing here is a credential, `public()` needs no `key_hint`/`has_key` discipline — but it still must not echo the raw body back.

### 4.7 Config flags (`peakcut/studio/config.py`)

Add, next to `SKIP_STATIC` (`config.py:135`) and in the same idiom:

```python
CHAT_SPIKES = env("PEAKCUT_CHAT_SPIKES", "0") == "1"   # 0 = never touch chat; the job behaves exactly as before
CHAT_MAX_MINUTES = float(env("PEAKCUT_CHAT_MAX_MINUTES", "30"))
```

`config.CHAT_SPIKES` is the env-level kill switch; `chat.json`'s `enabled` is the per-server setting. **Both must be true** for a fetch to happen — an operator who exported `PEAKCUT_CHAT_SPIKES=0` must be able to stop it regardless of what a user saved. Read the flag once per job, not per bin.

### 4.8 Pipeline wiring — the exact edits

Three call sites, all additive, all defaulting to today's behaviour.

**a) `peakcut/studio/brain.py:273` — give `find_clips` a chat argument.**

```python
def find_clips(words, db, duration, title="", uploader="", max_clips=6, min_len=15, max_len=60,
               log=print, game=None, chat=None, chat_tag=None):
    z = loud_zscore(db)
    lines = make_lines(words, z, chat, chat_tag)      # brain.py:275
```

with `make_lines` extended (`brain.py:153-174`) to

```python
def make_lines(words, loud=None, chat=None, chat_tag=None):
    ...
    lines.append({"s": s, "e": e, "text": " ".join(w["w"] for w in cur), "loud": is_loud,
                  "chat": bool(chat and chat(s, e)),
                  "chat_tag": (chat_tag(s, e) if chat_tag else "")})
```

and `_fmt` (`brain.py:116-118`) appending the tag after the flag:

```python
f"[{l['s']:.1f}] {'(LOUD) ' if l['loud'] else ''}{'(CHAT) ' if l.get('chat') else ''}"
f"{(l.get('chat_tag') or '') + ' ' if l.get('chat_tag') else ''}{_safe(l['text'], 2000)}"
```

With `chat=None` and `chat_tag=None` the line dict gains `"chat_tag": ""` and `_fmt` emits byte-identical text — the ground rule that an unconfigured server produces exactly the same prompt. `judge_transcript` (`brain.py:437`) and `find_live_clips` (`brain.py:317`) call `make_lines` positionally with only `words`, so they keep working untouched.

**b) `peakcut/studio/jobs.py` — build the map once, pass it into every block.**

Above `for bi, (a, b) in enumerate(blocks):` (`jobs.py:713`), i.e. next to the `statics = ...` line at `jobs.py:712`:

```python
cm = None
if config.CHAT_SPIKES and o.get("chat_spikes") and not job.get("done_blocks"):
    cm = chat.for_job(src.get("url") or "", lo / 16000, hi / 16000, log=notes.append)   # never raises
```

and at the existing call site (`jobs.py:738-739`):

```python
found, ai = brain.find_clips(bw, db[s0: s0 + int((b - a) / 16000) + 1], (b - a) / 16000, job["title"],
                             job["uploader"], quota, int(o["min_len"]), int(o["max_len"]), notes.append,
                             game=game, chat=cm.flag if cm else None,
                             chat_tag=cm.between if cm else None)
```

The map must be built **once per job**, not per block: the same GQL pages would otherwise be re-fetched for every 10-minute block of a 40-minute video. Use the whole job range (`lo/16000` to `hi/16000` — the same `lo`/`hi` that `jobs.py:614` and `jobs.py:617` already use) so one fetch serves every block; `find_spikes` is then called with absolute seconds, which is exactly what `tag_for`'s `int(s // BIN) * BIN` walk expects. The `not job.get("done_blocks")` guard keeps a restarted job from re-fetching a window it already paid for; if `cm` is `None` after a restart the job simply runs without chat, which is the documented degradation.

Record the result on the job so the UI can show it: after the loop, `job["ai"]["chat"] = {"bins": len(cm.ratios), "median": cm.med, "messages": cm.total}` when `cm` else `None`. Do not put the whole `bins` dict in `job.json` — it is regenerated from `words.json` on a restart.

**c) `peakcut/studio/live.py` — reuse `spike_bins`, do not reimplement.**

Leave `_chat` and the state exactly as they are. Two changes only:

- In `_watch_spikes` (`live.py:411-444`), replace the hand-rolled 1.6× comparison at `live.py:435-438` with the shared thresholds once there is enough history, keeping the same output shape:
  ```python
  bins, base = chatmod.spike_bins([int(x) for x in chat], 0, pct=97, mult=1 + pct, min_msgs=5, local=False)
  # chat_now / chat_base remain the numbers reported in `why`
  ```
  Gate it on `len(chat) >= 120` (the source's "needs 2 min of history", live.py:19) and fall through to the current comparison below that, so a stream that just started behaves exactly as it does today.
- Call the dead `_chat_spike` (`live.py:355-373`) from `_ai_check` where a candidate clip is being judged, so the existing people-based 3× test finally does something: `if self._chat_spike(c["start"], c["end"]): why.append("chat burst")`. Leave its body unchanged; it is already correct and already tested by eye.

Do **not** replace `_chat_spike` with `find_spikes`: the live path counts *people* in rolling windows and cannot afford to re-bin a whole hour on every check, while `find_spikes` needs absolute bins and full history. Two algorithms, one shared constant.

**d) `peakcut/studio/jobs.py:110-143` — the per-job option.**

`DEFAULTS` (`jobs.py:110-111`) gains `"chat_spikes": False`. `clean_options` (`jobs.py:117-142`) needs its **own bool branch**, exactly like `captions` (`jobs.py:121-125`) — the final `else` branch would otherwise run `float(False)` and raise:

```python
if k == "chat_spikes":
    if not isinstance(v, bool):
        raise ValueError("Chat spikes must be on or off.")
    out[k] = v
```

The creator form field is optional; the value must also be accepted by `server.py:849` (`jobs.clean_options(opts)`, the pre-flight check) or an upload carrying the option is refused before the file is sent.

### 4.9 Server routes (`peakcut/studio/server.py`)

Copy the transcription block's shape (`server.py:1317-1448`), placed immediately after it:

```python
# ---------------------------------------------------------------- chat spikes
# Read / save chat-spike settings, kept in chat.json in the data folder.

@app.get("/api/chat")
def chat_get(request: Request):
    _admin(request)
    return chat.public()

@app.put("/api/chat")
def chat_put(request: Request, body: dict = Body(...)):
    _admin(request)
    try:
        return chat.save(body)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except OSError as e:
        raise HTTPException(507, "Could not save the chat settings: " + safe.friendly(e, 120))

@app.post("/api/chat/test")
def chat_test(request: Request, body: dict = Body(default={})):
    _admin(request)
    _throttle("chat-test", 6, 60)
    ...
```

Rules for these three:

- `_admin(request)` (`server.py:310-315`) on all of them — this is a server-wide setting that causes outbound requests to third parties.
- `chat.save()` writes under its own lock with `tmp.write_text` + `tmp.replace(f)`; **no `os.chmod(0o600)` is needed** — there is no key in this file — but copying the pattern does no harm.
- `chat_test` takes `{"url": ..., "window": "..."}`, calls `chat.fetch(...)`, and returns `{"messages": n, "median": med, "bins": len(sp), "spikes": [{"at": b, "count": c, "ratio": round(r, 1), "phrases": tp} for b, c, r, tp in sp[:20]]}`. It must `_throttle` (a user could otherwise make the server hammer Twitch), and it must convert `ChatError` → `HTTPException(400, str(e))`, anything else → `HTTPException(502, "Chat did not answer: " + safe.friendly(e, 160))`. Both idioms are already the house style (`server.py:1449-1450`).
- **Never** return the raw URL with credentials, a cookie jar, or a full backtrace. `safe.friendly(e, 160)` already strips server paths (`safe.py:7-11`).

### 4.10 Settings tab (`peakcut/web/index.html`)

- `setTabs()` (`index.html:2003-2009`) gains one admin-gated row, in the same form as its neighbours:
  ```js
  ...(S.status.user?.is_admin ? [["chat", "Chat spikes", "chat", "Find the moments chat went wild"]] : []),
  ```
  The icon `"chat"` **already exists** in the `I` map (`index.html:850`, a speech bubble), so no new glyph is needed — this is the one thing that must not be re-added.
- `drawSettings()` (`index.html:2026`) gains `if (tab === "chat") { const k = S.chat = await api("/api/chat"); body.innerHTML = ... }` alongside the `"ai"` and `"transcribe"` branches.
- Fields, all bound by id and read back in the click handler: `#ch_on` (checkbox, `enabled`), `#ch_mult` (number, `1.0`–`4.0`, step `0.1`), `#ch_min` (number, `1`–`50`), `#ch_pct` (number, `80`–`99.9`), `#ch_local` (checkbox). Two buttons: `data-act="chsave"` (PUT `/api/chat`) and `data-act="chtest"` (POST `/api/chat/test` with the URL from `#ch_url` and the window from `#ch_win`).
- The click handler mirrors the transcription one verbatim in shape — collect only the fields on screen into `body`, `await send(...)`, `toast(...)`, `await drawSettings()`.
- The creator/composer form gains `<label class="f">Find moments chat went wild<input data-k="chat_spikes" type="checkbox"></label>` next to the caption controls, and — only when the box is ticked — the job's `options.chat_spikes` is sent.

Nothing here needs a new endpoint beyond `/api/chat*`, and nothing needs `ctx` beyond what `_admin` already does.

## 5. Data files

One new file: **`<DATA_DIR>/chat.json`** (`config.DATA_DIR / "chat.json"`), created lazily on first save, never required to exist. Read it the way `ai.py:49-62` reads `ai.json` (`_file()` + mtime-keyed cache), write it the way `server.py:1377-1390` writes `tr.json` (tmp file, lock, `tmp.replace(f)`).

Schema — every key optional, missing means the default:

```json
{
  "enabled": false,
  "mult": 1.6,
  "min_msgs": 5,
  "pct": 97,
  "local": true,
  "min_seconds": 120,
  "max_minutes": 30
}
```

| Key | Default | Range | Meaning |
|---|---|---|---|
| `enabled` | `false` | bool | the master switch, **off by default** |
| `mult` | `1.6` | 1.0–4.0 | the global multiple of the stream's own median |
| `min_msgs` | `5` | 1–50 | a spike bin must hold at least this many messages |
| `pct` | `97` | 80–99.9 | the percentile of all bins a spike must also beat |
| `local` | `true` | bool | allow the big-chat local rule (`med >= 20`) |
| `min_seconds` | `120` | 60–`max_minutes`×60 | below this, `for_job` returns `None` (no baseline) |
| `max_minutes` | `30` | 1–180 | hard cap, also clamped by `config.CHAT_MAX_MINUTES` |

Validation: clamp each number to its range, coerce `enabled`/`local` to bool, drop unknown keys, and raise `ValueError` with a readable sentence for a value that cannot be clamped (e.g. `mult: "lots"`). `save()` returns `public()`.

Per-job output goes into the existing `job.json` — **no new side file**: `job["ai"]["chat"] = {"bins": int, "median": float, "messages": int}` or `None`. The `ChatMap` itself must never be serialised into `job["dir"]`: it is cheap to rebuild from the source URL and would otherwise be a stale copy of somebody else's chat sitting in a user's folder.

**Nothing is written next to the user's video.** The source writes a `<src>.chat.json` side file into the source's folder; PeakCut's source path can be a shared download directory or a read-only upload, and a second user must never be able to read a file another user's job dropped there.

## 6. Risks

- **`HASH` rotates.** It is a persisted-query sha256; Twitch invalidates it periodically and the endpoint then answers `400` with `{"errors":[{"message":"PersistedQueryNotFound"}]}`. Treat any non-200 *or* any reply without `data.video.comments` as "no chat" and return `None` — never crash a job. Log a note the operator can act on, and keep the constant in one place with the comment from `chat.py:16` so it can be refreshed from a browser's network tab.
- **`SystemExit` kills a workspace.** `fetch` raises it today (`chat.py:97`) for a Twitch URL without a window. In PeakCut a job runs on a thread but the test runner and any in-process caller run in the main process; an escaping `SystemExit` takes the server or the test suite down. Every "you asked for something impossible" path must be `ChatError` → a note on the job, or `HTTPException(400)` at a route.
- **Single-user assumptions that do not hold.** (a) Writes into the source folder — forbidden (section 5). (b) A module-level cache keyed by URL — two users submitting the same popular stream would share a `ChatMap` and one user's `ctx` would serve the other's job; keep every value inside the job call, nothing global but the immutable constants. (c) `tempfile.mkdtemp()` that is never removed — the source leaks a directory per call; use `config.TMP_DIR` and `finally`-clean it, or a long-running server fills the drive (`_disk` guards in `server.py` only count *users'* folders, not the system temp dir). (d) Unbounded paging — one user can ask for 35 hours of chat and hold a worker thread for an hour; the `max_minutes` cap and the page budget are both required, not optional.
- **Cost per job, multiplied by users.** A 40-minute window is ~80 GQL requests at 0.15 s spacing plus latency — tens of seconds, serialised inside `_run_job`, competing with transcription and renders for `JOB_WORKERS` (`config.py:183`). Cap with `max_minutes`, default the per-job option to off, and never fetch chat for a job whose source is a local upload (no URL).
- **Twitch rate-limits by IP, not by user.** On a shared server every job's chat paging leaves from one address. Keep `PAGE_DELAY` at 0.15 s, keep the 4-try backoff, and treat a 429 as a soft failure with the note "Twitch is limiting chat requests right now" rather than retrying harder.
- **yt-dlp write volume.** A six-hour livestream's `live_chat.json` can be hundreds of MB, and `--write-subs` writes it before any parsing starts. The 300-second guard is the only thing between a user and a filled disk. Prefer the in-process `media._ydl` route so `NO_WINDOW` (`media.py:14`) applies on Windows and the same `socket_timeout`/retry settings do too.
- **The `pct` gate is a *relative* gate, so it can produce zero spikes on a truly flat chat** and can produce eight on a video whose 3 % is one burst. That is the intended behaviour (a spike must be unusual *for that stream*), but it means a reviewer who sees no spikes on a boring video must not "fix" it by lowering `pct` to 50.
- **A 10-second bin is narrower than a 15-second clip.** A spike bin flags one line of transcript; do not let it gate a whole clip. Use `flag(s, e)` as a hint to the model (as `brain.py:165` already does) and never as a filter that removes a clip.
- **`med >= 20` is a magic gate.** Lowering it makes the local rule fire on ordinary chats and destroys the selftest's big-chat assertion; raising it makes huge chats produce nothing. Keep it a module constant, not a setting.
- **The live path counts people; `spike_bins` counts whatever it is given.** Passing message counts into a threshold tuned for people triples the false-positive rate. `live.py:423` already prefers `len(people[t])` when `chat_users` is populated — keep that preference, and pass `unit` honestly to `judge_signals` (`brain.py:468`).
- **No new dependency is needed — do not add one.** `httpx==0.28.1` is pinned and used everywhere; `yt-dlp==2026.10.21` is pinned. The Kick live-chat half of the source needs `websockets`, which is **not** installed: leave Kick out of this port entirely, or it becomes a new dependency plus a Pusher handshake (`chat.py:244-278`) that cannot be tested in the no-network suite.
- **Regex fragility in `tag_for`.** `float(re.search(r"x([\d.]+)", t).group(1))` returns `AttributeError` on a formatted tag. Any future change to the tag string must keep the `x<number>` shape or `tag_for` silently starts raising inside `make_lines`, which is inside the prompt loop.

## 7. Verification

1. **Unit, no network, no media** — port the reference assertions as `chat.selftest()` and as `peakcut/tests/test_chat.py` (same `PASS <name>` / `sys.exit(1)` style as `tests/test_static.py`):

   ```bash
   cd peakcut && python -c "from studio import chat; print(chat.selftest(), 'checks')"
   python tests/test_chat.py
   ```

   `test_chat.py` must cover, at minimum: every assertion from 2.10 verbatim; `parse_win` accepting `hms` forms and rejecting `"1:00"` and an inverted window; `spike_bins` returning an empty dict plus the median for a flat `[10]*60`; the big-chat pair (nothing with `local=False`, exactly bin 600 with `local=True`); the slow-chat identity; `chat_tags` producing exactly ` [CHAT x4.0: "KEKW" x40]` for a planted bin and ` [CHAT x4.0]` when the phrases fall under `min_count`; `tag_for` picking the *larger* of two overlapping ratios; and `ChatMap.for_job` returning `None` (not raising) for `url=""`, a window under `min_seconds`, and a fetch that raises `ChatError` — patch `chat.fetch` for the last one so nothing is dialled.

2. **Register it in the suite** — one new tuple in the `runs` list in `tests/run.py`:

   ```python
   ("chat spikes: baseline, phrases, huge and slow chats", ["tests/test_chat.py"]),
   ```

   then run the whole thing, which also proves nothing else moved:

   ```bash
   cd peakcut && python tests/run.py
   ```

   It must end `All tests passed.` — in particular `tests/test_captions.py` (which renders) and `tests/test_transcribe_logfare.py` (which owns the settings-block pattern this one copies).

3. **Off by default, byte-identical** — with no `chat.json` and no `PEAKCUT_CHAT_SPIKES`, `_fmt(make_lines(words, z))` must equal the string produced by the unmodified code for the same `words`, and `brain.find_clips(words, db, dur)` must return the same `(found, ai)`. Assert it directly:

   ```bash
   cd peakcut && python -c "
   from studio import brain, chat
   w=[{'w':'hello','s':0.0,'e':0.4},{'w':'there','s':0.5,'e':0.9}]
   a=brain.make_lines(w, [0.0,0.0]); b=brain.make_lines(w, [0.0,0.0], None, None)
   assert a==b and all(l['chat_tag']=='' and l['chat'] is False for l in b), (a,b)
   assert chat.for_job('', 0, 600) is None
   print('identical, and no chat is off by default')"
   ```

4. **One real fetch, manually** (the only step that needs the internet; run it once, by hand, not in CI):

   ```bash
   cd peakcut && python -c "
   from studio import chat
   m = chat.fetch('https://www.twitch.tv/videos/000000000', 3600, 4200)
   sp, med = chat.find_spikes(m, 3600, 4200)
   print(len(m), 'messages, median', med, 'per 10 s')
   for b, c, r, tp in sp[:5]: print(b, c, round(r,2), tp)
   print(chat.chat_tags(m, 3600, 4200))"
   ```

   A working VOD shows a non-zero median and at least one spike with phrases; a broken `HASH` shows only the logged note and an empty list, which is the correct degradation.

5. **In the app** — with `chat.json` `{"enabled": true}` and a YouTube livestream replay, run one job with the chat box ticked: `job["ai"]["chat"]` is non-empty, the prompt sent to the model contains ` (CHAT)  [CHAT x4.0: "KEKW" x40] ` on the spike lines (log the prompt, or assert `l["chat_tag"]` on `make_lines` output), and `why`-style notes mention chat. Then untick the box on the same video and confirm `job["ai"]["chat"] is None` and the prompt is byte-identical to a run before the change — that is ground rule 4, measured rather than asserted.
