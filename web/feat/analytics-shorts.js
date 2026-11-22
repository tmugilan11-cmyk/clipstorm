/* Shorts. The Content tab lists every video in the range; this block keeps the ones that run
 * 60 seconds or less and says what the numbers about them mean.
 *
 * It asks the videos route itself instead of reading the table below it: that file drops the length
 * of each video while it tidies the rows, and a length is the only thing that makes a Short a Short.
 * The block sits after #an_table inside the Content panel, so neither file rewrites the other. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function") return;

  (typeof P.css === "function" ? P.css : () => {})("analytics-shorts", `
    .ast{margin-top:24px}
    .ast-head{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:4px}
    .ast-head h2{margin:0;font-size:17px}
    .ast-count{margin:10px 0 0;font-size:14px;line-height:1.5;color:var(--text)}
    .ast-count b{font-weight:600;color:var(--text);font-variant-numeric:tabular-nums}
    .ast-list{list-style:none;margin:12px 0 0;padding:0;border-top:1px solid var(--line)}
    .ast-row{display:grid;grid-template-columns:minmax(90px,1fr) 60px 104px;gap:12px;align-items:center;padding:8px 0;border-bottom:1px solid var(--line)}
    .ast-name{min-width:0;font-size:14px;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .ast-name a{color:inherit;text-decoration:none;border-bottom:1px solid transparent}
    .ast-name a:hover,.ast-name a:focus-visible{border-bottom-color:var(--brand-line)}
    .ast-dur{font-size:13px;color:var(--dim);font-variant-numeric:tabular-nums;white-space:nowrap}
    .ast-n{font-size:13px;color:var(--dim);text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
    .ast-n b{font-size:14px;font-weight:600;color:var(--text)}
    .ast-say{margin:12px 0 0;max-width:64ch;font-size:13px;line-height:1.55;color:var(--dim)}
    .ast-say a{color:var(--brand-deep);font-weight:600;text-decoration:none;border-bottom:1px solid var(--brand-line)}
    @media (max-width:700px){.ast-row{grid-template-columns:1fr auto;gap:4px 12px}.ast-name{grid-column:1 / -1}.ast-n{text-align:right}}
  `);

  const APPS = "/app/apps", DASH = "-", SHOW = 10;
  const NUM = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
  const GROUP = new Intl.NumberFormat("en-US");
  const SHORT = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });
  const DAY = { day: "numeric", month: "short" };

  const object = (v) => (v && typeof v === "object" && !Array.isArray(v)) ? v : null;
  const text = (v) => (typeof v === "string" && v.trim()) ? v.trim() : "";
  const num = (v) => (v === null || v === undefined || v === "" || !Number.isFinite(Number(v))) ? null : Number(v);
  const pick = (o, ks) => { for (const k of ks) { const v = num(o && o[k]); if (v !== null) return v; } return null; };
  const any = (o, ks) => { for (const k of ks) { const v = text(o && o[k]); if (v) return v; } return ""; };

  /** A length in seconds. A number as sent, or a mm:ss string, or nothing at all. */
  function secs(v) {
    if (typeof v === "number") return Number.isFinite(v) ? v : null;
    const s = String(v === null || v === undefined ? "" : v).trim();
    if (!s) return null;
    if (/^\d+(\.\d+)?$/.test(s)) return Number(s);
    const m = /^(\d{1,2}):(\d{2})(?::(\d{2}))?$/.exec(s);
    if (!m) return null;
    return m[3] ? Number(m[1]) * 3600 + Number(m[2]) * 60 + Number(m[3]) : Number(m[1]) * 60 + Number(m[2]);
  }
  /* Minutes and seconds, rounded down so a length is never stated as longer than it is. */
  const mmss = (s) => { const t = Math.max(0, Math.floor(s)); return Math.floor(t / 60) + ":" + String(t % 60).padStart(2, "0"); };
  const views = (n) => n === null ? DASH : (n >= 10000 ? SHORT.format(n) : GROUP.format(Math.round(n)));

  const iso = (v) => { const s = String(v || "").slice(0, 10); return /^\d{4}-\d{2}-\d{2}$/.test(s) ? s : ""; };
  const day = (v) => {                       // noon, so no time zone moves the day
    const d = new Date(String(v || "").slice(0, 10) + "T12:00:00");
    return isNaN(d.getTime()) ? "" : d.toLocaleDateString(undefined, DAY);
  };
  function rangeOf(r) {
    const o = object(r) || {}, a = day(iso(o.start)), b = day(iso(o.end));
    return (a && b) ? a + " to " + b : text(o.label);
  }

  /* Where the numbers live. Only names a server could plausibly use, and only ones that mean the
     same thing on every row. Per row percentages are not summed, because an average of averages
     is not the average. */
  const LIST = ["videos", "rows", "items", "data"];
  const DUR = ["seconds", "duration_seconds", "length_seconds", "duration", "length"];
  const VIEWS = ["views", "view_count", "viewCount"];
  const VIEWED = ["viewed", "viewed_count", "stayed", "stayed_count"];
  const SWIPED = ["swiped_away", "swiped", "swiped_count", "swiped_away_count", "dismissed"];
  const PCT = ["chose_to_view", "viewed_pct", "viewed_percentage", "stayed_percentage", "stayed_pct", "viewed_share"];
  const AGGS = ["shorts", "split", "viewed_vs_swiped"];

  /** The answer as the rows this block needs: the Shorts, how many videos were checked, and the
   *  viewed versus swiped away totals when the server sent them. */
  function read(got) {
    const b = object(got) || {};
    const list = Array.isArray(got) ? got : (LIST.map((k) => b[k]).find(Array.isArray) || []);
    const rows = [];
    let checked = 0, noDur = 0, viewed = null, swiped = null, pct = null;
    for (const raw of list) {
      const o = object(raw);
      if (!o) continue;
      checked += 1;
      let sec = null;
      for (const k of DUR) { const len = secs(o[k]); if (len !== null) { sec = len; break; } }
      if (sec === null || !(sec > 0)) { noDur += 1; continue; }
      if (sec > 60) continue;
      const v = pick(o, VIEWED), s = pick(o, SWIPED);
      if (v !== null) viewed = (viewed || 0) + v;
      if (s !== null) swiped = (swiped || 0) + s;
      const url = any(o, ["url", "link", "watch_url"]);
      rows.push({ title: any(o, ["title", "name", "clip"]) || "Untitled video", url: /^https:\/\//i.test(url) ? url : "",
        sec, views: pick(o, VIEWS) });
    }
    const agg = AGGS.map((k) => object(b[k])).find(Boolean) || null;
    if (agg) {
      const v = pick(agg, VIEWED), s = pick(agg, SWIPED), p = pick(agg, PCT);
      if (v !== null) viewed = v;
      if (s !== null) swiped = s;
      if (p !== null) pct = p;
    }
    if (pct === null) {
      const p = pick(b, ["chose_to_view", "viewed_vs_swiped", "viewed_pct", "viewed_percentage"]);
      if (p !== null) pct = p;
    }
    if (pct !== null) pct = pct <= 1 ? pct * 100 : pct;          // a share sent as 0..1 becomes a percent
    if (viewed !== null && swiped !== null) {
      pct = (viewed + swiped) > 0 ? (viewed / (viewed + swiped)) * 100 : pct;
    }
    const told = num(b.total);
    const total = told !== null && told > checked ? told : checked;
    rows.sort((x, y) => x.views === null ? 1 : y.views === null ? -1 : y.views - x.views);
    return { rows, checked, noDur, total, viewed, swiped, pct, range: rangeOf(b.range) };
  }

  /** The range on screen, and the address that answers for it. Lifetime asks for 0, which the
   *  route reads as all of its data. */
  function asked() {
    const A = object(window.PeakCutAnalytics) || {};
    let r = {};
    try { r = object(typeof A.range === "function" ? A.range() : A.range) || {}; } catch { r = {}; }
    if (!iso(r.start) && !iso(r.end) && num(r.days) === null) {
      r = { start: A.start, end: A.end, days: A.days, label: A.label };
    }
    const alive = /lifetime/i.test(text(r.label));
    const raw = num(r.days);
    const days = alive ? 0 : Math.min(3650, Math.max(0, Math.round(raw === null ? 28 : raw)));
    return { path: "/api/analytics/videos?days=" + days, days, range: rangeOf(r) };
  }

  /** Only the Content tab owns this block. No shell, no answer, or another tab means hands off. */
  function mine() {
    const A = window.PeakCutAnalytics;
    try {
      const name = String((typeof A.tab === "function" ? A.tab() : A.tab) || "").toLowerCase();
      if (name) return name === "content";
    } catch { /* the shell answered badly; the panel below is the same question, asked directly */ }
    const panel = document.querySelector('[data-an-panel="content"]');
    return !!panel && !panel.hidden;
  }
  function host() {
    const panel = document.querySelector('[data-an-panel="content"]');
    if (panel) return panel;
    const table = document.getElementById("an_table");
    return table && table.parentElement ? table.parentElement : null;
  }
  /** The block after the table, made once. The table may be redrawn under it and the panel may be
   *  drawn again from scratch, so this is asked every time instead of remembered. */
  function seat() {
    const panel = host();
    if (!panel) return null;
    const found = panel.querySelector(".ast");
    if (found) return found;
    const table = panel.querySelector("#an_table");
    const box = document.createElement("section");
    box.className = "set-sec ast";
    if (table && table.parentElement === panel) table.insertAdjacentElement("afterend", box);
    else panel.appendChild(box);
    return box;
  }

  /** True only when the server sent enough to say what happened to the views. */
  const has = (v) => (v.viewed !== null && v.swiped !== null) || v.pct !== null;
  /** Value, unit, and the exact figure behind it. A view count that was not sent is a dash. */
  function cell(r) {
    if (r.views === null) return `<span class="ast-n" title="Views were not sent for this video">${DASH}</span>`;
    const exact = GROUP.format(Math.round(r.views)) + " views";
    return `<span class="ast-n" title="${esc(exact)}"><b>${esc(views(r.views))}</b> views</span>`;
  }

  function paint(box, v, q) {
    const band = v.range || q.range || "Range not stated";
    const head = `<div class="ast-head"><h2>Shorts</h2><span class="pill">${esc(band)}</span></div>
      <p class="help">The videos in this range that run 60 seconds or less.</p>`;
    let body = "";
    if (v.busy) {
      body = `<p class="ast-say" aria-busy="true">Reading the videos...</p>`;
    } else if (v.fail) {
      body = `<p class="ast-say">The Shorts could not be counted.${v.note ? " " + esc(v.note) + "." : ""} Reload the page to try again.</p>`;
    } else if (!v.checked) {
      body = `<p class="ast-say">No videos in this range yet. Publish a clip, or pick a wider date range above.</p>`;
    } else if (!v.rows.length && v.noDur === v.checked) {
      body = `<p class="ast-say">The server sent ${esc(GROUP.format(v.checked))} videos but not how long they run, so Clipstorm cannot tell which ones are Shorts. Length comes from YouTube, and <a href="${APPS}">Connected apps</a> shows whether a channel is connected.</p>`;
    } else {
      const scope = (v.total > v.checked ? "of the first " : "of ") + GROUP.format(v.checked)
        + (v.checked === 1 ? " video" : " videos");
      const n = v.rows.length, top = v.rows.slice(0, SHOW);
      const partial = n > SHOW;
      const dashed = top.some((r) => r.views === null);
      const rows = top.map((r) => {
        const name = r.url
          ? `<a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.title)}</a>`
          : esc(r.title);
        return `<li class="ast-row"><span class="ast-name" title="${esc(r.title)}">${name}</span>
          <span class="ast-dur" title="${esc(GROUP.format(Math.round(r.sec)) + " seconds")}">${esc(mmss(r.sec))}</span>
          ${cell(r)}</li>`;
      }).join("");
      let say;
      if (has(v)) {
        const stayed = v.viewed !== null && v.swiped !== null
          ? GROUP.format(Math.round(v.viewed)) + " of " + GROUP.format(Math.round(v.viewed + v.swiped)) + " looks stayed and "
            + GROUP.format(Math.round(v.swiped)) + " swiped away"
          : NUM.format(v.pct) + " percent of looks stayed";
        say = `<p class="ast-say">YouTube counts a Short as viewed when someone stays with it and as swiped away when they move on: ${esc(stayed)}.</p>`;
      } else {
        say = `<p class="ast-say">The server did not send the viewed versus swiped away numbers, so this is a plain count of Shorts.</p>`;
      }
      /* The count sentence has to read well at one, at many, and when the server sent more videos
         than it listed. "of the first" is said only when there really are more behind the list. */
      const lead = (v.checked === 1 && n === 1)
        ? `<b>1</b> Short: the only video in this range runs 60 seconds or less.`
        : `<b>${esc(GROUP.format(n))}</b> ${esc(scope)} in this range ${n === 1 ? "is a Short" : "are Shorts"}, meaning 60 seconds or less.`;
      body = `<p class="ast-count">${lead}</p>`
        + (partial ? `<p class="help">The ${esc(String(top.length))} with the most views, out of ${esc(GROUP.format(n))} Shorts.</p>` : "")
        + `<ol class="ast-list" aria-label="Shorts in this range, most views first">${rows}</ol>`
        + (dashed ? `<p class="help">A dash means the server did not send views for that video.</p>` : "")
        + say;
    }
    const html = head + body;
    if (typeof put === "function") put(box, html); else box.innerHTML = html;
  }

  const CACHE = new Map(), BUSY = new Set();   // one answer per range, one request at a time

  async function fill() {
    if (!mine()) return;                                        // not my tab: leave the DOM alone
    const box = seat();
    if (!box) return;                                           // the shell has not drawn the panel yet
    const q = asked();
    if (box.dataset.sig === q.path) return;                     // this range is already on screen
    if (BUSY.has(q.path)) return;
    const hit = CACHE.get(q.path);
    if (hit) { paint(box, hit, q); box.dataset.sig = q.path; return; }
    BUSY.add(q.path);
    paint(box, { rows: [], checked: 0, busy: true, range: q.range }, q);   // the frame first, then the numbers
    let v;
    try {
      const call = typeof P.api === "function" ? P.api : (typeof api === "function" ? api : null);
      if (!call) throw new Error("The page is still starting");
      v = read(await call(q.path));
      if (!v.range) v.range = q.range;
      if (CACHE.size > 6) CACHE.clear();
      CACHE.set(q.path, v);
    } catch (err) {
      const why = String((err && err.message) || err || "").trim().replace(/\.$/, "");
      v = { rows: [], checked: 0, fail: true, note: why ? why.charAt(0).toUpperCase() + why.slice(1) : "" };
    } finally { BUSY.delete(q.path); }
    const now = mine() ? seat() : null;
    if (!now) return;
    paint(now, v, q);
    /* A failure is marked too. The panel is watched for changes, and repainting the same failure
       would wake the watcher again: one failing range would ask forever. The failure sentence tells
       the person to reload, which is the retry. */
    now.dataset.sig = q.path;
  }

  // The panel is drawn by the shell, which may draw it again at any time. When it appears, fill it once.
  function watch() {
    const view = document.getElementById("view");
    if (!view || typeof MutationObserver !== "function") return;
    new MutationObserver(() => { if (mine() && document.getElementById("an_table")) fill(); })
      .observe(view, { childList: true, subtree: true });
  }

  P.add("analytics-shorts", { load() { fill(); } });
  fill();
  watch();
})();
