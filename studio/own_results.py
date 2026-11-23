"""How this person's own posted clips really did, and what the AI judge is told about it.

The judge picks moments from a transcript. Without this file it never learns whether the moments it picked
were watched. This reads every clip that was posted (PeakCut's post records), joins it to the clip's own record
(hook, title, kind, the critics' marks, length, the score the judge gave, layout, look) and to its numbers:

* views, likes and comments, from YouTube when a channel is connected (and from Zernio for posts that went
  through it, or from the views PeakCut already tracks on each post);
* when YouTube is connected: how much of the clip people watched on average, and how many were still
  watching at the third second (the hook).

`taste_lines()` then turns that into a few plain sentences for the judge: which clips did well and badly
compared with this channel's OWN median (never against other people's), and whether the judge's own scores
have been predicting reality.

Rules this file keeps:
* Everything works with no posts and with no YouTube connection: the answer is simply empty.
* The numbers are cached in the user's folder and fetched in one pass at most every six hours, never inside a
  render and never more often than five minutes even when asked. A failed pass keeps the old numbers.
* `taste_lines()` reads the cache only. It is fast and it never raises.
* A video can be posted just now and have 40 views because it is an hour old. Clips younger than two days are
  listed but never judged good or bad.
"""
from __future__ import annotations

import json
import math
import re
import statistics
import threading
import time

from . import config, ctx

REFRESH_S = 6 * 3600          # a pass over the network at most this often...
MIN_GAP_S = 300               # ...and even a press of "Refresh" waits this long after the last one
MATURE_S = 2 * 86400          # a clip younger than this has not had its audience yet
MIN_CLIPS = 3                 # fewer measured clips than this and there is no "usual" to compare with
MIN_FOR_JUDGE = 6             # and this many to say anything about the judge's own scores
GOOD_X, BAD_X = 1.5, 0.5      # times the channel's median that counts as "did well" / "did badly"
RETENTION_FOR = 20            # the 3-second curve costs one call per video: only the newest this many
ZERNIO_FOR = 40               # one call per Zernio post: only the newest this many
AUTO_REFRESH = True           # tests switch this off so nothing starts a thread

_lock = threading.RLock()
_busy: dict = {}              # uid -> True while a pass is running
_last_try: dict = {}          # uid -> when the last pass started (this run of the program)


# ---------------------------------------------------------------- the cache
def _uid(uid=None) -> str:
    """Who this is for: the one asked for, the one this code runs as, or the single owner. "" when unknown."""
    for u in (uid, ctx.uid_or_none()):
        if u:
            return str(u) if re.fullmatch(r"[A-Za-z0-9_]{6,40}", str(u)) else ""
    try:
        from . import auth
        return str(auth.local_user().id)
    except Exception:  # noqa: BLE001  - no owner is no answer, not a crash
        return ""


def _file(uid: str):
    return config.user_dir(uid) / "own_results.json"


def _read(uid: str) -> dict:
    """The saved pass: {"at", "rows", "error", "youtube"}; an empty one when there is none or it is unreadable."""
    blank = {"at": 0.0, "rows": [], "error": "", "youtube": False}
    try:
        data = json.loads(_file(uid).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return blank
    if not isinstance(data, dict):
        return blank
    rows = [r for r in (data.get("rows") or []) if isinstance(r, dict)]
    return {"at": _num(data.get("at")) or 0.0, "rows": rows, "error": str(data.get("error") or "")[:300],
            "youtube": bool(data.get("youtube"))}


def _write(uid: str, data: dict) -> None:
    try:
        f = _file(uid)
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
        tmp.replace(f)
    except (OSError, ValueError):
        pass                      # the numbers are rebuilt next time; a full disk must not stop a clip


# ---------------------------------------------------------------- small helpers
def _num(v):
    """A finite number or None. Booleans are not numbers here."""
    if isinstance(v, bool):
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def _count(v):
    """A whole count of at least zero, or None when it is missing (0 and "not known" are different things)."""
    x = _num(v)
    return int(x) if x is not None and x >= 0 else None


def _words(v, limit=60) -> str:
    """Text that came from a video, on its way into a sentence the AI reads: one line, no quotes or tags."""
    t = re.sub(r"[\x00-\x1f\x7f]+", " ", str(v or ""))
    t = re.sub(r"[\"<>`]", "", t)
    return re.sub(r"\s+", " ", t).strip()[:limit]


def _short_count(n) -> str:
    x = _num(n)
    if x is None:
        return "?"
    if x >= 1_000_000:
        return f"{x / 1_000_000:.1f}M".replace(".0M", "M")
    if x >= 10_000:
        return f"{round(x / 1000)}k"
    if x >= 1000:
        return f"{x / 1000:.1f}k".replace(".0k", "k")
    return str(int(x))


# ---------------------------------------------------------------- joining posts to clips
def _posted(uid: str) -> list:
    """One base row per posted clip, with the clip's own facts and no numbers yet. Runs as that user."""
    from . import jobs, posting
    rows = []
    with ctx.as_user(uid):
        for p in posting._mine():
            if p.get("status") != "posted":
                continue
            job = jobs.get(p.get("job"))
            clip = next((c for c in (job or {}).get("clips") or [] if c.get("id") == p.get("clip")), None) or {}
            rub = clip.get("rubric") if isinstance(clip.get("rubric"), dict) else {}
            length = max(0.0, (_num(clip.get("end")) or 0.0) - (_num(clip.get("start")) or 0.0))
            rows.append({
                "post": str(p.get("id") or ""), "job": str(p.get("job") or ""), "clip": str(p.get("clip") or ""),
                "creator": str(p.get("creator") or ""), "platform": str(p.get("platform") or ""),
                "account": str(p.get("account_name") or ""), "url": str(p.get("url") or ""),
                "remote_id": str(p.get("remote_id") or ""), "zernio_post": str(p.get("zernio_post") or ""),
                "posted_at": _num(p.get("posted_at")) or _num(p.get("due_at")) or 0.0,
                "title": _words(clip.get("title") or p.get("title") or clip.get("hook"), 80),
                "hook": _words(clip.get("hook"), 80),
                "kind": _words(rub.get("kind") or clip.get("category"), 20).lower(),
                "length": round(length, 1),
                "judge_score": int(_num(clip.get("score")) or _num(p.get("score")) or 0),
                "marks": {k: int(_num(rub.get(k)) or 0) for k in ("hook_score", "payoff", "emotion", "share", "standalone")
                          if _num(rub.get(k)) is not None},
                "verdict": _words(rub.get("verdict"), 8).lower(),
                "layout": _words(clip.get("layout"), 20), "format": _words(clip.get("format"), 20),
                "style": _words(clip.get("style"), 20), "mood": _words(clip.get("mood"), 20),
                # what PeakCut already tracks on the post itself: the fallback when nothing newer is fetched
                "views": _count(p.get("views")),
                "likes": _count((p.get("zernio_numbers") or {}).get("likes")),
                "comments": _count((p.get("zernio_numbers") or {}).get("comments")),
                "source": "peakcut"})
    return rows


# ---------------------------------------------------------------- fetching numbers (the only network code)
def _numbers_youtube(rows: list, uid: str) -> bool:
    """Fill in views, likes, comments, average watched and 3-second hold for rows posted to the connected
    channel. True when YouTube answered. Never raises."""
    from . import accounts, ytstats
    mine = [r for r in rows if r.get("platform") == "youtube" and r.get("remote_id")]
    if not mine:
        return False
    with ctx.as_user(uid):
        token = accounts.youtube_token()
    if not token:
        return False
    mine.sort(key=lambda r: -(r.get("posted_at") or 0))
    first = min((r.get("posted_at") or time.time()) for r in mine)
    since = time.strftime("%Y-%m-%d", time.gmtime(first - 2 * 86400))
    got = ytstats.bulk(token, [r["remote_id"] for r in mine], since=since, retention_for=RETENTION_FOR)
    vids = got.get("videos") or {}
    for r in mine:
        v = vids.get(r["remote_id"])
        if not v:
            continue
        for k_row, k_yt in (("views", "views"), ("likes", "likes"), ("comments", "comments")):
            if _count(v.get(k_yt)) is not None:
                r[k_row] = _count(v.get(k_yt))
        if _num(v.get("averageViewPercentage")) is not None:
            r["avg_view_pct"] = round(_num(v["averageViewPercentage"]), 1)
        if _num(v.get("averageViewDuration")) is not None:
            r["avg_view_s"] = round(_num(v["averageViewDuration"]), 1)
        if _num(v.get("kept_at_3s")) is not None:
            r["kept_3s"] = round(_num(v["kept_at_3s"]), 3)
        r["source"] = "youtube"
    return bool(vids)


def _numbers_zernio(rows: list) -> None:
    """Views, likes and comments from Zernio for posts that went through it. A post it cannot answer for keeps
    the numbers PeakCut already had. Never raises."""
    mine = [r for r in rows if r.get("zernio_post")]
    if not mine:
        return
    try:
        from . import zernio
    except Exception:  # noqa: BLE001
        return
    mine.sort(key=lambda r: -(r.get("posted_at") or 0))
    for r in mine[:ZERNIO_FOR]:
        try:
            got = zernio.analytics(r["zernio_post"])
        except Exception:  # noqa: BLE001  - one post it cannot answer for is not worth a failed pass
            continue
        for k in ("views", "likes", "comments"):
            if _count(got.get(k)) is not None:
                r[k] = _count(got[k])
        r["source"] = "zernio"


# ---------------------------------------------------------------- one pass
def collect(uid=None, force: bool = False, now: float | None = None) -> list:
    """Every posted clip that can be measured, with its numbers: a list of dicts, newest first.

    Fresh numbers are fetched in one pass when the saved ones are older than six hours (or `force`, which still
    waits five minutes after the last pass). Otherwise, and whenever a pass fails, the saved ones are returned.
    Never raises."""
    try:
        u = _uid(uid)
        if not u:
            return []
        at = time.time() if now is None else float(now)
        saved = _read(u)
        stale = at - saved["at"] >= REFRESH_S
        if not (stale or force) or at - _last_try.get(u, 0.0) < MIN_GAP_S:
            return _measured(saved["rows"])
        with _lock:
            if _busy.get(u):
                return _measured(saved["rows"])
            _busy[u] = True
            _last_try[u] = at
        try:
            return _measured(_pass(u, saved, at))
        finally:
            with _lock:
                _busy.pop(u, None)
    except Exception:  # noqa: BLE001
        return []


def _pass(u: str, saved: dict, at: float) -> list:
    """The network pass itself. On any failure the old numbers stay and the reason is saved beside them."""
    try:
        rows = _posted(u)
        yt = _numbers_youtube(rows, u)
        _numbers_zernio(rows)
    except Exception as e:  # noqa: BLE001
        _write(u, {**saved, "error": ("Could not read the results: " + str(e))[:300]})
        return saved["rows"]
    rows.sort(key=lambda r: -(r.get("posted_at") or 0))
    err = ""
    try:
        from . import ytstats
        err = ytstats.problem.get("text", "") if yt or any(r.get("platform") == "youtube" for r in rows) else ""
    except Exception:  # noqa: BLE001
        pass
    _write(u, {"at": at, "rows": rows, "error": err, "youtube": yt})
    return rows


def refresh_async(uid=None, force: bool = True) -> bool:
    """Start a pass on its own thread and return at once. False when one is already running or none is due."""
    u = _uid(uid)
    if not u:
        return False
    with _lock:
        if _busy.get(u):
            return False
    t = threading.Thread(target=lambda: collect(u, force=force), daemon=True, name="own-results")
    t.start()
    return True


def refreshing(uid=None) -> bool:
    return bool(_busy.get(_uid(uid)))


def _measured(rows: list) -> list:
    """Only rows with a view count, newest first."""
    keep = [r for r in (rows or []) if isinstance(r, dict) and _count(r.get("views")) is not None]
    return sorted(keep, key=lambda r: -(_num(r.get("posted_at")) or 0))


# ---------------------------------------------------------------- comparing with the channel's own median
def _mature(r: dict, now: float) -> bool:
    return now - (_num(r.get("posted_at")) or 0) >= MATURE_S


def analyse(rows: list, now: float | None = None) -> list:
    """The rows with `vs_median` added (views divided by the median views of this channel), best first.

    The median is taken per platform when that platform has at least three grown-up clips, else over all of
    them, because a clip on one network and a clip on another are not read by the same crowd. A clip that is too
    young gets `young: True` and no `vs_median`; it is listed but not judged."""
    at = time.time() if now is None else float(now)
    rows = [dict(r) for r in rows if isinstance(r, dict) and _count(r.get("views")) is not None]
    grown = [r for r in rows if _mature(r, at)]
    allmed = statistics.median([r["views"] for r in grown]) if grown else 0
    meds = {}
    for plat in {r.get("platform") for r in grown}:
        vs = [r["views"] for r in grown if r.get("platform") == plat]
        if len(vs) >= MIN_CLIPS:
            meds[plat] = statistics.median(vs)
    for r in rows:
        if not _mature(r, at):
            r["young"] = True
            continue
        med = meds.get(r.get("platform"), allmed)
        r["median"] = med
        r["vs_median"] = round(r["views"] / med, 2) if med else None
    rows.sort(key=lambda r: (-1 if r.get("vs_median") is None else r["vs_median"]), reverse=True)
    return rows


def _kind_bit(r: dict) -> str:
    bits = []
    if _words(r.get("kind"), 20):
        bits.append(_words(r.get("kind"), 20))
    if _num(r.get("length")):
        bits.append(f"{round(r['length'])} s")
    if r.get("judge_score"):
        bits.append(f"judge gave {int(r['judge_score'])}")
    return f" ({', '.join(bits)})" if bits else ""


def _numbers_bit(r: dict) -> str:
    bits = [f"{_short_count(r.get('views'))} views"]
    if _num(r.get("avg_view_pct")) is not None:
        bits.append(f"{round(r['avg_view_pct'])}% watched")
    if _num(r.get("kept_3s")) is not None:
        bits.append(f"{round(r['kept_3s'] * 100)}% still there at 3 s")
    return ", ".join(bits)


def _line(verdict: str, r: dict) -> str:
    name = _words(r.get("title") or r.get("hook") or "a clip")        # cleaned again here: the cache is a file
    x = r.get("vs_median")
    tail = f" ({x:g}x the channel's median)" if x is not None else ""
    return f'{verdict}: "{name}"{_kind_bit(r)} - {_numbers_bit(r)}{tail}.'


def _ranks(vals: list) -> list:
    """Rank of each value, ties sharing their average rank (what a rank correlation needs)."""
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    out = [0.0] * len(vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return out


def _spearman(xs: list, ys: list):
    """Rank correlation between two lists, or None when it cannot be told (too few, or one never changes)."""
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    rx, ry = _ranks(xs), _ranks(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    if not dx or not dy:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / (dx * dy)


def judge_lines(rows: list) -> list:
    """One or two sentences comparing the judge's scores with what really happened. [] when there are too few
    grown-up clips with a score to say anything honest."""
    graded = [r for r in rows if r.get("vs_median") is not None and (r.get("judge_score") or 0) > 0]
    if len(graded) < MIN_FOR_JUDGE:
        return []
    rho = _spearman([r["judge_score"] for r in graded], [r["vs_median"] for r in graded])
    out = []
    if rho is not None:
        if rho >= 0.3:
            out.append(f"The judge's scores have been predicting results so far (clips it scored higher got more views, "
                       f"over {len(graded)} clips).")
        elif rho <= -0.3:
            out.append(f"The judge's scores have been predicting results backwards: over {len(graded)} clips the ones it "
                       f"scored highest got fewer views than the ones it scored lowest. Do not trust a high score on its own.")
        else:
            out.append(f"The judge's scores have not been predicting results (over {len(graded)} clips, a high score did "
                       f"not mean more views). Trust the real results above over the score.")
    overall = statistics.mean(r["judge_score"] for r in graded)
    worst = None
    for kind in {r.get("kind") for r in graded if r.get("kind")}:
        group = [r for r in graded if r.get("kind") == kind]
        if len(group) < MIN_CLIPS:
            continue
        mean_score = statistics.mean(r["judge_score"] for r in group)
        typical = statistics.median(r["vs_median"] for r in group)
        # over-rated: the judge likes this kind at least as much as its average, yet people watch it less
        if mean_score >= overall - 2 and typical <= 0.7 and (worst is None or typical < worst[1]):
            worst = (kind, typical, mean_score, len(group))
    if worst:
        out.append(f"The judge over-rates {worst[0]} clips: it scores them {round(worst[2])} on average over {worst[3]} "
                   f"clips, but they get only {round(worst[1] * 100)}% of the channel's median views.")
    return out


# ---------------------------------------------------------------- what the judge is told
def _for_creator(rows: list, creator) -> list:
    """The rows of one creator when there are enough of them to compare, otherwise all of the owner's clips."""
    cid = ""
    if isinstance(creator, dict):
        cid = str(creator.get("id") or "")
    elif creator:
        cid = str(creator)
    if not cid:
        return rows
    own = [r for r in rows if r.get("creator") == cid]
    return own if len([r for r in own if _count(r.get("views")) is not None]) >= MIN_CLIPS else rows


def taste_lines(creator=None, n: int = 12) -> list:
    """Short plain sentences for the AI judge about how this person's own posted clips performed. [] when
    nothing is measured yet. Reads the saved numbers only: fast, no network, never raises. When the saved
    numbers are old a refresh is started on the side, so the next call is better informed."""
    try:
        n = max(0, int(n))
        if not n:
            return []
        u = _uid()
        if not u:
            return []
        saved = _read(u)
        if AUTO_REFRESH and time.time() - saved["at"] >= REFRESH_S:
            _kick(u)
        return _compose(analyse(_for_creator(_measured(saved["rows"]), creator)), n)
    except Exception:  # noqa: BLE001  - the judge must still run when this cannot answer
        return []


def _compose(rows: list, n: int) -> list:
    """The sentences for rows already put through `analyse`: best, worst, then the judge comparison."""
    grown = [r for r in rows if r.get("vs_median") is not None]
    if len(grown) < MIN_CLIPS or n <= 0:
        return []
    extra = judge_lines(grown)[:2]
    room = max(0, n - len(extra))
    good = [r for r in grown if r["vs_median"] >= GOOD_X]
    bad = [r for r in reversed(grown) if r["vs_median"] <= BAD_X]
    k_good, k_bad = (room + 1) // 2, room // 2
    if not bad:
        k_good = room
    if not good:
        k_bad = room
    lines = [_line("Did well", r) for r in good[:k_good]] + [_line("Did badly", r) for r in bad[:k_bad]]
    return (lines + extra)[:n]


def _kick(u: str) -> None:
    """Start a background refresh if there is anything posted and the last try was not just now. Never raises."""
    try:
        if time.time() - _last_try.get(u, 0.0) < MIN_GAP_S or _busy.get(u):
            return
        from . import posting
        with ctx.as_user(u):
            if not any(p.get("status") == "posted" for p in posting._mine()):
                return
        refresh_async(u, force=False)
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------- for the page
def report(uid=None) -> dict:
    """Everything the "What worked on your channel" panel draws, from the saved numbers (no network)."""
    u = _uid(uid)
    saved = _read(u) if u else {"at": 0.0, "rows": [], "error": "", "youtube": False}
    rows = analyse(_measured(saved["rows"]))
    return {"rows": rows, "lines": _compose(rows, 12), "measured": len(rows), "updated": saved["at"] or None,
            "youtube": saved["youtube"], "error": saved["error"], "refreshing": bool(_busy.get(u)),
            "median": (statistics.median([r["views"] for r in rows]) if rows else None)}


# ---------------------------------------------------------------- "does the connection really work?"
def check_youtube(uid=None) -> dict:
    """A real, tiny read against both YouTube APIs, answered in plain words: {"ok": bool, "message": str}.
    It is what the "Test the connection" button runs. Never raises."""
    try:
        from . import accounts, ytstats
        u = _uid(uid)
        with ctx.as_user(u):
            st = accounts.youtube_status()
            if not st["app_ready"]:
                return {"ok": False, "message": "Paste the Client ID and Client secret from Google first, then press Save."}
            if not st["connected"]:
                return {"ok": False, "message": "No YouTube channel is connected yet. Press Connect YouTube."}
            if st["token_ok"] is False:
                return {"ok": False, "message": ytstats.explain(RuntimeError(st["error"])) or st["error"]}
            if st["analytics_scope"] is False:
                return {"ok": False, "message": "Google did not give PeakCut permission to read your numbers. Press "
                                                "Connect YouTube again and leave every tick box ticked."}
            token = accounts.youtube_token()
        end = time.strftime("%Y-%m-%d", time.gmtime())
        start = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 7 * 86400))
        ytstats._get("channels", {"part": "id", "mine": "true"}, token=token)
        ytstats.analytics(token, start, end, "views")
        return {"ok": True, "message": f"Connected to {st['name'] or 'your channel'}. PeakCut can read your views and "
                                       f"watch time."}
    except Exception as e:  # noqa: BLE001
        try:
            from . import ytstats
            return {"ok": False, "message": ytstats.explain(e) or ("YouTube did not answer: " + str(e)[:160])}
        except Exception:  # noqa: BLE001
            return {"ok": False, "message": "YouTube did not answer."}
