/* Where the views came from: one bar per traffic source, biggest first.
 *
 * Fills #an_body on the Traffic tab only. The Audience tab has its own file, so this asks the shell
 * which tab is open and returns without touching the DOM when the answer is another tab. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function") return;
  (typeof P.css === "function" ? P.css : () => {})("analytics-traffic", `
    .atf-head{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:4px}.atf-head h2{margin:0}
    .atf-list{list-style:none;margin:12px 0 0;padding:0;border-top:1px solid var(--line)}
    .atf-row{display:grid;grid-template-columns:minmax(96px,1.1fr) minmax(70px,2fr) 76px 84px 52px;gap:12px;align-items:center;padding:8px 0;border-bottom:1px solid var(--line)}
    .atf-name{font-size:14px;font-weight:600;color:var(--text);min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .atf-track{height:9px;border-radius:99px;background:var(--muted);overflow:hidden}
    .atf-bar{display:block;height:100%;min-width:2px;border-radius:99px;background:var(--brand-line)}
    .atf-n{font-size:13px;color:var(--dim);text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}.atf-n b{font-size:14px;font-weight:600;color:var(--text)}
    .atf-say{margin:12px 0 0;max-width:64ch;font-size:13px;line-height:1.55;color:var(--dim)}.atf-say a{color:var(--brand-deep);font-weight:600;text-decoration:none;border-bottom:1px solid var(--brand-line)}
    @media (max-width:700px){.atf-row{grid-template-columns:repeat(3,auto);justify-content:start;gap:6px 14px}.atf-name,.atf-track{grid-column:1 / -1}.atf-n{text-align:left}}
  `);

  const APPS = "/app/apps", DASH = "-", LIST = ["sources", "traffic", "rows", "items", "data"];
  const NUM = new Intl.NumberFormat("en-US", {maximumFractionDigits: 1}), GROUP = new Intl.NumberFormat("en-US");
  const SHORT = new Intl.NumberFormat("en-US", {notation: "compact", maximumFractionDigits: 1});
  const object = v => (v && typeof v === "object" && !Array.isArray(v)) ? v : null;
  const text = v => (typeof v === "string" && v.trim()) ? v.trim() : "";
  const num = v => (v === null || v === undefined || v === "" || !Number.isFinite(Number(v))) ? null : Number(v);
  const pick = (o, ks) => { for (const k of ks) { const v = num(o && o[k]); if (v !== null) return v; } return null; };
  const held = (o, ks) => { for (const k of ks) { const v = text(o && o[k]); if (v) return v; } return ""; };
  const key = s => String(s || "").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
  /* The names YouTube uses for itself, in the words a person uses. Anything else is printed as sent. */
  const NAMES = {shorts_feed: "Shorts feed", shorts: "Shorts feed", browse: "Browse features", home: "Browse features",
    suggested_video: "Suggested videos", suggested: "Suggested videos", yt_search: "YouTube search", search: "YouTube search",
    external: "External", playlist: "Playlists", playlists: "Playlists", channel: "Channel pages",
    channel_pages: "Channel pages", notification: "Notifications", notifications: "Notifications"};
  /* What the biggest source means for the next clip, not what it is. */
  const SAY = {"Shorts feed": "a vertical clip has to hold people in its first two seconds", "Browse features": "the title and the thumbnail are what people see first",
    "Suggested videos": "the video playing next to yours decides whether someone taps", "YouTube search": "the words in your titles are what pull people in",
    "External": "where you share the link is what counts", "Playlists": "the order of the playlist is what keeps people watching",
    "Channel pages": "people who already follow you are the reason", "Notifications": "subscribers are opening what you post"};
  const MINS = {watch_minutes: 1, watch_time_minutes: 1, minutes_watched: 1, estimated_minutes_watched: 1, watch_hours: 60, watch_time_hours: 60, watch_seconds: 1 / 60, watch_time_seconds: 1 / 60};

  function name(o, i) {
    const raw = held(o, ["source", "traffic_source", "name", "label", "title", "id", "insightTrafficSourceType"]);
    const plain = /^[A-Z0-9_ ]+$/.test(raw) ? raw.toLowerCase().replace(/[_-]+/g, " ").replace(/\b[a-z]/g, c => c.toUpperCase()) : raw;
    return NAMES[key(raw)] || text(plain) || "Source " + (i + 1);
  }
  const iso = (o, ks) => { for (const k of ks) { const s = String((o && o[k]) || "").slice(0, 10); if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s; } return ""; };
  const day = v => {   // noon, so no time zone moves the day
    const d = new Date(String(v || "").slice(0, 10) + "T12:00:00");
    return isNaN(d.getTime()) ? "" : d.toLocaleDateString(undefined, {day: "numeric", month: "short"});
  };
  /** A range as words. `o` may be the range itself or the whole answer. */
  function rangeOf(o) {
    const r = object(o) || {}, a = day(iso(r, ["start", "from", "since"])), b = day(iso(r, ["end", "to", "until"]));
    return (a && b) ? a + " to " + b : text(r.label);
  }
  /** The range the shell is showing, and the address that answers for it.
   *
   * The route takes one number, `days`, and nothing else: `start` and `end` are dropped by the server, which would
   * answer every range with the default 28 days while the card still printed the range the person picked. So the
   * shell's range is turned into a day count here, and the answer is labelled from what the server sent back. */
  function asked() {
    const A = object(window.PeakCutAnalytics) || {}, r = object(A.range) || A, qs = [];
    const s = iso(r, ["start", "from", "since"]), e = iso(r, ["end", "to", "until"]);
    const at = v => { const t = new Date(String(v || "") + "T12:00:00").getTime(); return isNaN(t) ? null : t; };
    const a = s ? at(s) : null, b = e ? at(e) : null;
    const span = (a !== null && b !== null) ? Math.round((b - a) / 86400000) + 1 : null;
    const n = pick(r, ["days"]) ?? span;
    if (n !== null) qs.push("days=" + encodeURIComponent(Math.min(3650, Math.max(0, Math.round(n)))));
    return {path: "/api/analytics/traffic" + (qs.length ? "?" + qs.join("&") : ""), range: rangeOf(A.range)};
  }
  /** Only the Traffic tab may redraw the body. No shell, no answer, or another tab means hands off. */
  function mine() {
    const A = window.PeakCutAnalytics;
    try { return String((typeof A.tab === "function" ? A.tab() : A.tab) || "").toLowerCase() === "traffic"; } catch { return false; }
  }

  /** A share as a percent. A route sending fractions and one sending percents both fit: the column has to
   *  add up to about 100, so its sum says which was meant. Views fill any gap. */
  function shares(rows) {
    const sent = rows.filter(r => r.pct !== null), sum = sent.reduce((a, r) => a + r.pct, 0);
    const scale = sent.length > 1 ? (sum <= 1.6 ? 100 : 1) : sent.length ? (Math.abs(sum) <= 1.5 ? 100 : 1) : 1;
    const views = rows.reduce((a, r) => a + (r.views || 0), 0);
    for (const r of rows) {
      if (r.pct !== null) r.pct = Math.max(0, r.pct * scale);
      else if (views > 0 && r.views !== null) r.pct = (r.views / views) * 100;
    }
  }
  function read(got) {
    const b = object(got) || {};
    const list = Array.isArray(got) ? got : LIST.map(k => b[k]).find(Array.isArray) || [];
    const rows = [];
    list.forEach((raw, i) => {
      const o = object(raw);
      if (!o) return;
      const at = Object.keys(MINS).find(k => num(o[k]) !== null);
      rows.push({name: name(o, i), views: pick(o, ["views", "view_count", "viewCount", "estimated_views"]), mins: at ? num(o[at]) * MINS[at] : null,
        pct: pick(o, ["pct", "percent", "percentage", "share", "views_pct", "views_percent"])});
    });
    shares(rows);
    rows.sort((x, y) => x.views === null ? 1 : y.views === null ? -1 : y.views - x.views);
    const out = {rows, range: rangeOf(b.range || b)};   // the route answers a day count, so read its own dates
    if (rows.length) return out;
    out.note = (text(b.error) || text(b.detail) || text(b.note) || text(b.message)).replace(/\.$/, "");
    if (b.connected === false) out.note = "No channel is connected yet";
    return out;
  }

  const views = n => n === null ? "" : (n >= 10000 ? SHORT.format(n) : GROUP.format(Math.round(n)));
  const pctText = p => p === null ? DASH : p === 0 ? "0" : (p >= 0.05 ? NUM.format(p) : "<0.1");
  /** Value, unit, and the exact figure behind it. A missing count is a dash, never a zero. */
  function timing(min) {
    if (min === null) return {v: "", u: "", tip: "Watch time was not sent for this source"};
    const exact = GROUP.format(Math.round(min)) + " minutes";
    return min >= 60 ? {v: NUM.format(Math.round(min / 6) / 10), u: "h", tip: exact} : {v: GROUP.format(Math.round(min)), u: "min", tip: exact};
  }
  const cell = (v, u, tip) => `<span class="atf-n" title="${esc(tip)}"><b>${esc(v || DASH)}</b>${v && u ? " " + esc(u) : ""}</span>`;
  /** One sentence: the biggest source, then what it means in plain words. */
  function say(top) {
    const share = top.pct === null ? " the most views" : " " + pctText(top.pct) + " percent of your views";
    const tail = SAY[top.name] || "which is where YouTube showed your clips most often";
    return `<p class="atf-say">${esc(top.name)} brought${esc(share)}, so ${esc(tail)}.</p>`;
  }

  function paint(box, v, q) {
    const band = v.range || q.range || "Range not stated";
    const head = `<div class="atf-head"><h2>Traffic sources</h2><span class="pill">${esc(band)}</span></div>
      <p class="help">Where the views came from, biggest source first.</p>`;
    let list = "";
    if (v.rows && v.rows.length) {
      const rows = v.rows.map((r, i) => {
        const t = timing(r.mins), p = pctText(r.pct), n = views(r.views);
        return `<li class="atf-row"><span class="atf-name" title="${esc(r.name)}">${esc(r.name)}</span>
          <span class="atf-track" aria-hidden="true"><span class="atf-bar${i ? "" : " top"}" style="width:${Math.min(100, r.pct || 0).toFixed(1)}%"></span></span>
          ${cell(n, "views", n ? GROUP.format(Math.round(r.views)) + " views" : "No view count")}
          ${cell(t.v, t.u, t.tip)}${cell(p, "%", p + " percent of views")}</li>`;
      }).join("");
      list = `<ol class="atf-list" aria-label="Traffic sources, biggest first">${rows}</ol>${say(v.rows[0])}`;
    }
    const line = v.busy ? `<p class="atf-say" aria-busy="true">Reading the traffic sources...</p>`
      : v.fail ? `<p class="atf-say">The traffic sources could not be read.${v.note ? " " + esc(v.note) + "." : ""} Reload the page to try again.</p>`
      : v.note ? `<p class="atf-say">${esc(v.note)}. Check <a href="${APPS}">Connected apps</a>, then reload this page.</p>`
      : `<p class="atf-say">No traffic sources in this range yet. A channel with at least one published clip fills this list, and <a href="${APPS}">Connected apps</a> shows whether one is connected.</p>`;
    const html = `<section class="set-sec atf" data-sig="${esc(q.path)}">${head}${list || line}</section>`;
    if (typeof put === "function") put(box, html); else box.innerHTML = html;
  }

  const cache = new Map(), busy = new Set();   // one answer per range, and one request at a time
  async function fill() {
    if (!mine()) return;                                          // not my tab: leave the DOM alone
    const box = document.getElementById("an_body");
    if (!box) return;                                             // the shell has not drawn its body yet
    const q = asked();
    if (busy.has(q.path)) return;
    const drawn = box.querySelector(".atf");
    if (drawn && drawn.dataset.sig === q.path) return;             // this range is already on screen
    if (cache.has(q.path)) return paint(box, cache.get(q.path), q);
    busy.add(q.path);
    paint(box, {rows: [], busy: true, range: q.range}, q);         // the frame first, then the numbers
    let v;
    try {
      const call = (typeof P.api === "function" ? P.api : null) || (typeof api === "function" ? api : null);
      if (!call) throw new Error("The page is still starting");
      v = read(await call(q.path));
      if (cache.size > 6) cache.clear();
      cache.set(q.path, v);
    } catch (err) {
      const why = String((err && err.message) || err || "").trim().replace(/\.$/, "");
      v = {rows: [], fail: true, note: why ? why.charAt(0).toUpperCase() + why.slice(1) : ""};
    } finally { busy.delete(q.path); }
    const now = document.getElementById("an_body");
    if (now && mine()) paint(now, v, q);
  }

  // The Analytics page belongs to another file, so its body is not here yet. When it appears, fill it once.
  function watch() {
    const view = document.getElementById("view");
    if (!view || typeof MutationObserver !== "function") return;
    new MutationObserver(() => { if (document.getElementById("an_body")) fill(); })
      .observe(view, {childList: true, subtree: true});
  }

  P.add("analytics-traffic", {load() { fill(); }});
  fill();
  watch();
})();
