/* Top searches, the videos that gained the most views, and the searches this person kept: the three
 * blocks on the Trends tab of the Insights page.
 *
 * Fills #an_body, which the Audience and Traffic files also write, so this asks the shell which tab is
 * open and returns without touching the DOM when the answer is another tab. The date range is read
 * from the shell's own select, which is why this page has no second range control.
 *
 * Every block draws its frame first and fills in when its own answer arrives, so one slow route leaves
 * the other two on screen. A route that fails leaves a sentence in that block, never a blank page. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function") return;

  const LIMIT = 25, CAP = 50, DASH = "-";
  const GROUP = new Intl.NumberFormat("en-US");
  const ROWS = ["rows", "items", "data", "searches", "results"];

  (typeof P.css === "function" ? P.css : () => {})("analytics-trends", `
    .atr-range{margin:0 0 18px;font-size:13px;line-height:1.55;color:var(--dim)}
    .atr-top{display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap}
    .atr-note{margin:0 0 12px;padding:9px 12px;border-radius:var(--r-sm);background:var(--muted);color:var(--dim);font-size:13px;line-height:1.5}
    .atr-empty{border:1px dashed var(--line-2);border-radius:var(--r);padding:22px 16px;color:var(--dim);font-size:13px;line-height:1.55;text-align:center}
    .atr-fail{border-left:3px solid var(--bad);background:var(--bad-soft);color:var(--text);padding:10px 12px;border-radius:0 var(--r-sm) var(--r-sm) 0;font-size:13px;line-height:1.5}
    .atr-miss{margin:10px 0 0;font-size:12px;color:var(--faint)}
    .atr-list,.atr-vlist{list-style:none;margin:12px 0 0;padding:0;border-top:1px solid var(--line)}
    .atr-row{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(60px,1.5fr) 96px 84px 88px;gap:12px;align-items:center;padding:8px 0;border-bottom:1px solid var(--line)}
    .atr-term{min-width:0;font-size:14px;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .atr-track{display:block;height:9px;border-radius:99px;background:var(--muted);overflow:hidden}
    .atr-track i{display:block;height:100%;min-width:2px;border-radius:99px;background:var(--brand-line)}
    .atr-n{font-size:13px;color:var(--dim);text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
    .atr-n b{font-size:14px;font-weight:600;color:var(--text)}
    .atr-interest{font-size:12px;color:var(--dim);white-space:nowrap;text-align:right}
    .atr-save,.atr-done{justify-self:end}
    .atr-done{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--good);white-space:nowrap}
    .atr-done svg{width:15px;height:15px}
    .atr-vid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,150px) 96px;gap:12px;align-items:center;padding:9px 0;border-bottom:1px solid var(--line);font-size:14px}
    .atr-vtitle{min-width:0;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .atr-vtitle a{color:inherit;text-decoration:none;border-bottom:1px solid var(--brand-line)}
    .atr-vtitle a:hover{color:var(--brand-deep)}
    .atr-vmeta{min-width:0;font-size:13px;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .atr-chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
    .atr-chip{display:inline-flex;align-items:center;gap:6px;max-width:100%;min-height:32px;padding:0 4px 0 12px;border:1px solid var(--line-2);border-radius:999px;background:var(--bg);font-size:13px;color:var(--text)}
    .atr-cterm{min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .atr-x{display:grid;place-items:center;width:26px;height:26px;padding:0;border:0;border-radius:999px;background:transparent;color:var(--faint);cursor:pointer}
    .atr-x:hover{background:var(--bad-soft);color:var(--bad)}
    .atr-x:focus-visible{outline:2px solid var(--brand);outline-offset:1px}
    .atr-x svg{width:15px;height:15px}
    @media (max-width:700px){
      .atr-row{grid-template-columns:minmax(0,1fr) auto;gap:8px 12px}
      .atr-track{grid-column:1 / -1}
      .atr-term{white-space:normal}
      .atr-n,.atr-interest{text-align:left}
      .atr-save,.atr-done{justify-self:start}
      .atr-vid{grid-template-columns:minmax(0,1fr) auto}
      .atr-vmeta{grid-column:1 / -1}
    }
    /* Phone-sized screens: the saved-search chip and its close button each get a 44 px tap target,
     * the size a thumb presses reliably. The close glyph stays 15 px; only the box grows. */
    @media (max-width:640px){
      .atr-chip{min-height:44px}
      .atr-x{width:44px;height:44px}
    }
  `);

  const object = (v) => (v && typeof v === "object" && !Array.isArray(v)) ? v : null;
  const text = (v) => (typeof v === "string" && v.trim()) ? v.trim() : "";
  const num = (v) => (v === null || typeof v === "undefined" || v === "" || !isFinite(Number(v))) ? null : Number(v);
  const pick = (o, ks) => { for (const k of ks) { const v = num(o && o[k]); if (v !== null) return v; } return null; };
  const held = (o, ks) => { for (const k of ks) { const v = text(o && o[k]); if (v) return v; } return ""; };
  const cut = (s) => { const t = String(s || "").replace(/\s+/g, " ").trim(); return t.length > 220 ? t.slice(0, 217) + "..." : t; };
  const views = (n) => n === null ? DASH : GROUP.format(Math.round(n));
  /** A day as words at noon local time, so no time zone moves it to the day before. */
  function day(v) {
    const s = String(v || "").slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return "";
    const d = new Date(s + "T12:00:00");
    return isNaN(d.getTime()) ? "" : d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  }
  function isoOf(o, ks) {
    for (const k of ks) { const s = String((o && o[k]) || "").slice(0, 10); if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s; }
    return "";
  }

  const emptyLine = (t) => `<p class="atr-empty">${esc(t)}</p>`;
  const noteLine = (t) => `<p class="atr-note">${esc(cut(t))}</p>`;
  const loading = (t) => `<p class="set-load" aria-busy="true">${esc(t)}</p>`;
  const failLine = (what, why) => `<p class="atr-fail">${esc(what)} could not be read. ${esc(cut(why) || "The server did not say why.")} Reload the page to try again.</p>`;

  /* ---------------------------------------------------------------- the state
   * One small record per block. A block that has not answered yet is null, which draws its loading
   * line, so the frame can be painted before any request is sent. */
  const board = { sig: "", q: null, searches: null, videos: null, saved: null };
  const busy = new Set();
  const host = () => document.getElementById("an_body");
  const shell = () => window.PeakCutAnalytics;

  /* ---------------------------------------------------------------- the range
   * The shell's own select decides the range. Lifetime arrives as about eleven thousand days, which
   * the routes refuse, so it is sent as zero, the value they read as "everything". */
  function asked() {
    const A = shell() || {};
    let r = {};
    try { r = (typeof A.range === "function" ? A.range() : A.range) || {}; } catch { r = {}; }
    const n = num(typeof r === "object" ? r.days : r);
    const days = n === null ? 28 : (n > 3650 ? 0 : Math.max(0, Math.round(n)));
    const label = text(r.label) || (days ? "Last " + days + " days" : "Lifetime");
    const start = isoOf(r, ["start", "from", "since"]), end = isoOf(r, ["end", "to", "until"]);
    return { days: days, label: label, start: start, end: end, sig: "d" + days + "|" + start + "|" + end };
  }

  /** The line above the blocks: the exact days every number below covers, or a sentence saying why not. */
  function rangeLine(q) {
    if (q.start && q.end) return "Showing " + day(q.start) + " to " + day(q.end) + ". The page is set to " + q.label + ".";
    return "The page is set to " + q.label + ". The server did not send the exact dates, so the span on screen is the only range these numbers have.";
  }

  /* ---------------------------------------------------------------- reading answers */
  function readSearches(got) {
    const b = object(got) || {};
    const list = Array.isArray(got) ? got : ROWS.map((k) => b[k]).find(Array.isArray) || [];
    const rows = [];
    for (const raw of list) {
      const o = object(raw);
      if (!o) continue;
      const term = held(o, ["term", "query", "search_term", "search", "text", "name"]);
      if (!term) continue;
      rows.push({ term: term.slice(0, 200),
        interest: held(o, ["interest", "level", "band", "word", "score_word"]),
        views: pick(o, ["views", "view_count", "viewCount", "estimated_views"]) });
    }
    rows.sort((x, y) => x.views === null ? 1 : y.views === null ? -1 : y.views - x.views);
    return { rows: rows.slice(0, LIMIT), note: cut(held(b, ["note", "message", "detail"])),
      start: isoOf(b, ["start", "from"]), end: isoOf(b, ["end", "to"]) };
  }

  function readVideos(got) {
    const b = object(got) || {};
    const list = Array.isArray(got) ? got : ["rows", "items", "data", "videos", "results"].map((k) => b[k]).find(Array.isArray) || [];
    const rows = [];
    list.forEach((raw, i) => {
      const o = object(raw);
      if (!o) return;
      const title = held(o, ["title", "name", "video_title"]) || "Video " + (i + 1);
      const link = held(o, ["url", "link", "watch_url"]);
      rows.push({ title: title.slice(0, 300), channel: held(o, ["channel", "channel_title", "author", "creator"]),
        views: pick(o, ["views", "view_count", "viewCount"]),
        url: /^https:\/\/[^\s]+$/.test(link) ? link : "" });
    });
    rows.sort((x, y) => x.views === null ? 1 : y.views === null ? -1 : y.views - x.views);
    return { rows: rows.slice(0, LIMIT), note: cut(held(b, ["note", "message", "detail"])),
      start: isoOf(b, ["start", "from"]), end: isoOf(b, ["end", "to"]) };
  }

  function readTerms(got) {
    const b = object(got) || {};
    const list = Array.isArray(got) ? got
      : Array.isArray(b.terms) ? b.terms : Array.isArray(b.saved) ? b.saved : Array.isArray(b.rows) ? b.rows : [];
    const out = [];
    for (const raw of list) {
      const t = typeof raw === "string" ? raw : held(raw, ["term", "query", "text", "name"]);
      const s = String(t || "").trim().slice(0, 120);
      if (s && out.indexOf(s) < 0) out.push(s);
    }
    return out;
  }

  const whyOf = (e) => {
    const s = String((e && (e.detail || e.message)) || e || "").trim().replace(/\.$/, "");
    return s || "The request failed";
  };

  /* ---------------------------------------------------------------- the blocks */
  function section(key, title, body, pill) {
    return `<section class="set-sec atr" data-atr="${esc(key)}">
      <div class="atr-top"><h2>${esc(title)}</h2>${pill ? `<span class="pill">${esc(pill)}</span>` : ""}</div>
      ${body}
    </section>`;
  }

  function kept(term) {
    const d = board.saved;
    if (!d || d.fail || !d.terms || !d.terms.length) return false;
    const want = String(term || "").toLowerCase();
    return d.terms.some((t) => String(t).toLowerCase() === want);
  }

  function rowSearches(r, top) {
    const w = top > 0 && r.views !== null ? Math.max(2, Math.min(100, (r.views / top) * 100)) : 0;
    const tip = r.views === null ? "The server did not send a view count for this term" : GROUP.format(Math.round(r.views)) + " views came from this search";
    const action = kept(r.term)
      ? `<span class="atr-done" title="This search is already in your saved list">${ic("check")}Saved</span>`
      : `<button class="btn sm atr-save" type="button" data-atr-save="${esc(r.term)}" title="Keep this search term in your list">${ic("plus")}Save</button>`;
    return `<li class="atr-row">
      <span class="atr-term" title="${esc(r.term)}">${esc(r.term)}</span>
      <span class="atr-track" aria-hidden="true"><i style="width:${w.toFixed(1)}%"></i></span>
      <span class="atr-n" title="${esc(tip)}"><b>${esc(views(r.views))}</b> views</span>
      <span class="atr-interest" title="The words the server used for this term's share of search views">${esc(r.interest || DASH)}</span>
      ${action}
    </li>`;
  }

  function blockSearches(q) {
    const d = board.searches;
    const help = `<p class="help">The words people typed into YouTube before they found this channel, and how much of the search traffic each one brought.</p>`;
    let body;
    if (!d) body = loading("Reading the search terms.");
    else if (d.fail) body = failLine("The search terms", d.why);
    else if (!d.rows.length) body = emptyLine(d.note || "No search terms in this range yet. A channel with search traffic fills this list, and a longer range can bring more of them in.");
    else {
      const top = d.rows.reduce((a, r) => Math.max(a, r.views === null ? 0 : r.views), 0);
      const missing = d.rows.some((r) => r.views === null) ? `<p class="atr-miss">A dash in the count means the server did not send a number for that row.</p>` : "";
      body = (d.note ? noteLine(d.note) : "") + `<ol class="atr-list">${d.rows.map((r) => rowSearches(r, top)).join("")}</ol>` + missing;
    }
    return section("searches", "Top searches", help + body, q.label);
  }

  function blockVideos(q) {
    const d = board.videos;
    const help = `<p class="help">This channel's own videos in this range, most views first, with the link to each one. It is not YouTube's public trending chart: other channels' videos are not shown here.</p>`;
    let body;
    if (!d) body = loading("Reading your videos this range.");
    else if (d.fail) body = failLine("Your videos", d.why);
    else if (!d.rows.length) body = emptyLine(d.note || "No videos in this range yet. A channel with published clips fills this list.");
    else {
      const rows = d.rows.map((r) => {
        const title = r.url
          ? `<a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.title)}</a>`
          : esc(r.title);
        return `<li class="atr-vid">
          <span class="atr-vtitle" title="${esc(r.title)}">${title}</span>
          <span class="atr-vmeta" title="${esc(r.channel || "The server did not say which channel this came from")}">${esc(r.channel || "Channel not sent")}</span>
          <span class="atr-n" title="${esc(r.views === null ? "The server did not send a view count for this video" : GROUP.format(Math.round(r.views)) + " views in this range")}"><b>${esc(views(r.views))}</b> views</span>
        </li>`;
      }).join("");
      const missing = d.rows.some((r) => r.views === null) ? `<p class="atr-miss">A dash in the count means the server did not send a number for that video.</p>` : "";
      body = (d.note ? noteLine(d.note) : "") + `<ul class="atr-vlist">${rows}</ul>` + missing;
    }
    return section("videos", "Your videos this range", help + body, q.label);
  }

  function chip(t) {
    return `<span class="atr-chip"><span class="atr-cterm" title="${esc(t)}">${esc(t)}</span>
      <button class="atr-x" type="button" data-atr-drop="${esc(t)}" title="Remove this search term" aria-label="Remove ${esc(t)}">${ic("x")}</button></span>`;
  }

  function blockSaved() {
    const d = board.saved;
    const help = `<p class="help">The search terms you kept. A kept term stays here after the page is closed, up to ${CAP} of them.</p>`;
    let body;
    if (!d) body = loading("Reading your saved searches.");
    else if (d.fail) body = failLine("Your saved searches", d.why);
    else if (!d.terms.length) body = emptyLine("No saved searches yet. Press Save beside a search term above and it is kept here for the next time.");
    else body = `<div class="atr-chips">${d.terms.map(chip).join("")}</div>`;
    const pill = d && !d.fail && d.terms ? d.terms.length + " of " + CAP : "";
    return section("saved", "Saved searches", help + body, pill);
  }

  /* ---------------------------------------------------------------- painting */
  const ready = () => !!(board.searches && board.videos && board.saved);

  function paint(root) {
    const q = board.q || asked();
    const html = `<div class="atr-wrap" data-sig="${esc(board.sig)}">
      <p class="atr-range">${esc(rangeLine(q))}</p>
      ${blockSearches(q)}${blockVideos(q)}${blockSaved()}
    </div>`;
    if (typeof put === "function") put(root, html); else root.innerHTML = html;
    if (ready()) root.removeAttribute("aria-busy");
  }

  /* ---------------------------------------------------------------- the requests */
  async function get(path, opt) {
    const call = typeof P.api === "function" ? P.api : (typeof api === "function" ? api : null);
    if (!call) throw new Error("This page has no request helper loaded");
    return await call(path, opt);
  }

  async function askSearches(q, sig) {
    try {
      const got = await get("/api/trends/searches?days=" + q.days + "&limit=" + LIMIT);
      if (board.sig !== sig) return;
      board.searches = readSearches(got);
    } catch (e) {
      if (board.sig !== sig) return;
      board.searches = { rows: [], fail: true, why: whyOf(e) };
    }
    const now = host();
    if (now && board.sig === sig && mine()) paint(now);
  }

  async function askVideos(q, sig) {
    try {
      const got = await get("/api/trends/videos?days=" + q.days + "&limit=" + LIMIT);
      if (board.sig !== sig) return;
      board.videos = readVideos(got);
    } catch (e) {
      if (board.sig !== sig) return;
      board.videos = { rows: [], fail: true, why: whyOf(e) };
    }
    const now = host();
    if (now && board.sig === sig && mine()) paint(now);
  }

  async function askSaved(sig) {
    try {
      const got = await get("/api/trends/saved");
      board.saved = { terms: readTerms(got) };
    } catch (e) {
      board.saved = { terms: [], fail: true, why: whyOf(e) };
    }
    const now = host();
    if (now && board.sig === sig && mine()) paint(now);
  }

  /* ---------------------------------------------------------------- the driver */
  /** Only the Trends tab may draw this box. No shell, no tab name, or another tab means hands off. */
  function mine() {
    const A = shell();
    if (!A) return false;
    try { return String((typeof A.tab === "function" ? A.tab() : A.tab) || "").toLowerCase() === "trends"; }
    catch { return false; }
  }

  function fill() {
    if (!mine()) return;
    const root = host();
    if (!root) return;
    const q = asked();
    const drawn = root.querySelector(".atr-wrap");
    if (drawn && drawn.dataset.sig === q.sig) return;      // this range is already on screen
    if (busy.has(q.sig)) return;
    busy.add(q.sig);
    board.sig = q.sig; board.q = q;
    board.searches = board.videos = board.saved = null;
    root.setAttribute("aria-busy", "true");
    paint(root);                                            // the frame first, then the numbers
    Promise.all([askSearches(q, q.sig), askVideos(q, q.sig), askSaved(q.sig)])
      .then(() => {
        busy.delete(q.sig);
        const now = host();
        if (now && board.sig === q.sig && ready()) now.removeAttribute("aria-busy");
      })
      .catch(() => { busy.delete(q.sig); });
  }

  /* ---------------------------------------------------------------- the two buttons */
  async function save(btn) {
    const term = btn.getAttribute("data-atr-save") || "";
    if (!term || btn.disabled) return;
    btn.disabled = true;
    try {
      const call = typeof P.send === "function" ? P.send : (typeof send === "function" ? send : null);
      if (!call) throw new Error("This page has no request helper loaded");
      const got = await call("/api/trends/saved", { term: term });
      board.saved = { terms: readTerms(got) };
      if (typeof P.toast === "function") P.toast("Saved " + term + " to your searches.", "ok");
    } catch (e) {
      if (typeof P.toast === "function") P.toast("That search was not saved. " + whyOf(e) + ".", "bad");
      btn.disabled = false;
    }
    const root = host();
    if (root && mine()) paint(root);
  }

  async function drop(btn) {
    const term = btn.getAttribute("data-atr-drop") || "";
    if (!term || btn.disabled) return;
    btn.disabled = true;
    try {
      const got = await get("/api/trends/saved?term=" + encodeURIComponent(term), { method: "DELETE" });
      board.saved = { terms: readTerms(got) };
    } catch (e) {
      if (typeof P.toast === "function") P.toast("That search was not removed. " + whyOf(e) + ".", "bad");
      btn.disabled = false;
    }
    const root = host();
    if (root && mine()) paint(root);
  }

  document.addEventListener("click", (e) => {
    const el = e.target && e.target.closest ? e.target : null;
    if (!el || !el.closest("#an_body")) return;
    const s = el.closest("[data-atr-save]");
    if (s) { e.preventDefault(); save(s); return; }
    const d = el.closest("[data-atr-drop]");
    if (d) { e.preventDefault(); drop(d); }
  });

  /* The Insights page belongs to another file, so the body is drawn later than this script runs. */
  P.add("analytics-trends", { load() { fill(); } });

  const view = document.getElementById("view");
  if (view && typeof MutationObserver === "function") {
    new MutationObserver(() => { if (document.getElementById("an_body")) fill(); })
      .observe(view, { childList: true, subtree: true });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fill);
  else fill();
})();
