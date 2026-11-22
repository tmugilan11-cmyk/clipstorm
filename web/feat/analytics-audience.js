/* Audience tab for the analytics page. Fills #an_body.
   One request, three blocks. Each block keeps its own empty state and its own
   failure line, so one bad block cannot empty the page. Every number carries
   the range the server reported, or says the range is missing. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function") return;

  const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const STEP = ["#FFE6D3", "#FFBE8C", "#FF9448", "#D9691A"];
  const RV = ["returning", "returning_viewers", "returningViewers", "returning_views"];
  const NV = ["new", "new_viewers", "newViewers", "new_views", "first_time", "first_time_viewers"];
  const APPS = "/app/apps";   // the Connected apps page, where a channel is connected

  /* The "new viewers" series needs its own hue. The old fill, var(--brand-ink), is the dark ink that
     sits on the orange button and measured 1.02:1 on the #111111 track, so the bars were invisible.
     #22D3EE measured 10.45:1 on that track and 10.96:1 on the page background, so the series reads. */
  if (typeof P.css === "function") P.css("aa", `
.aa-top{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap}.aa-range{color:var(--faint);font-size:12px}
.aa-note{margin:0 0 18px;padding:9px 12px;border-radius:var(--r-sm);background:var(--muted);color:var(--dim);font-size:13px;line-height:1.5}.aa-note a{color:var(--brand-deep);font-weight:600;text-decoration:none;border-bottom:1px solid var(--brand-line)}
.aa-line{border-left:3px solid var(--bad);background:var(--bad-soft);color:var(--text);padding:10px 12px;border-radius:0 var(--r-sm) var(--r-sm) 0;font-size:13px;line-height:1.5}
.aa-empty{border:1px dashed var(--line-2);border-radius:var(--r);padding:22px 16px;color:var(--dim);font-size:13px;text-align:center}
.aa-split{display:grid;gap:14px;margin-top:14px}.aa-bar{display:grid;grid-template-columns:104px minmax(0,1fr) 92px;gap:12px;align-items:center;font-size:13px}
.aa-key{display:flex;align-items:center;gap:7px;color:var(--text)}.aa-dot{width:9px;height:9px;border-radius:3px;display:inline-block;background:var(--brand)}.aa-dot.new{background:#22D3EE}
.aa-track{height:30px;border-radius:var(--r-sm);background:var(--muted);overflow:hidden;display:block}.aa-fill{display:block;height:100%;border-radius:var(--r-sm);background:var(--brand);transition:width .45s ease}.aa-fill.new{background:#22D3EE}
.aa-val{text-align:right;font-variant-numeric:tabular-nums;line-height:1.25}.aa-val b{font-weight:600}.aa-val span{display:block;color:var(--dim);font-size:12px}
.aa-list{display:grid;gap:2px;margin-top:10px}.aa-row{display:grid;grid-template-columns:minmax(0,148px) minmax(0,1fr) 54px;gap:12px;align-items:center;padding:5px 0;font-size:13px}
.aa-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.aa-mini{display:block;height:9px;border-radius:999px;background:var(--muted);overflow:hidden}.aa-mini i{display:block;height:100%;border-radius:999px;background:var(--brand)}.aa-pct{text-align:right;font-variant-numeric:tabular-nums;color:var(--dim)}
.aa-scroll{overflow-x:auto;padding-bottom:2px}.aa-map{min-width:520px}.aa-grid{display:grid;grid-template-columns:40px repeat(24,minmax(0,1fr));gap:3px;align-items:center}
.aa-h{font-size:11px;color:var(--faint);line-height:1}.aa-d{font-size:11px;color:var(--dim)}.aa-c{aspect-ratio:1;border-radius:3px;background:var(--muted);display:block}
.aa-legend{display:flex;align-items:center;gap:6px;margin-top:12px;font-size:12px;color:var(--dim);flex-wrap:wrap}.aa-legend i{width:16px;height:11px;border-radius:3px;display:inline-block}.aa-legend .aa-off{background:var(--muted);border:1px solid var(--line-2)}
.aa-best{font-size:13px;margin-top:10px;color:var(--text)}.aa-best b{font-weight:600}
.aa-swipe{margin:7px 0 0;font-size:11px;color:var(--faint)}
@media (prefers-reduced-motion:reduce){.aa-fill{transition:none}}
`);

  const DASH = "-";   // a dash, never a zero: nothing was received
  const nz = (v) => (v === null || typeof v === "undefined" || typeof v === "boolean" || String(v).trim() === "" || !isFinite(Number(v)) ? null : Number(v));
  const fmt = new Intl.NumberFormat("en-US");
  const show = (v) => (nz(v) === null ? DASH : fmt.format(Math.round(nz(v))));
  const one = (v) => (v >= 10 ? Math.round(v) : Math.round(v * 10) / 10) + "%";
  const pad = (h) => String(h).padStart(2, "0");
  const cut = (s) => (String(s || "").length > 150 ? String(s).slice(0, 147) + "..." : String(s || ""));
  const day = (v) => {
    const d = v ? new Date(String(v)) : null;
    return !d || isNaN(d.getTime()) ? String(v || "") : d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  };

  function pickN(o, keys) {
    if (!o || typeof o !== "object") return null;
    for (const k of keys) { const v = nz(o[k]); if (v !== null) return v; }
    return null;
  }

  function rangeText(d) {
    const r = (d && d.range) || {};
    const a = r.start || d.start || d.start_date || d.from || d.since;
    const b = r.end || d.end || d.end_date || d.to || d.until;
    const n = nz(d.days);
    if (!a && !b) return "Date range not reported by the server.";
    return "Range " + (day(a) || "start not given") + " to " + (day(b) || "end not given") + (n === null ? "" : ", " + n + " days");
  }

  const empty = (t) => `<p class="aa-empty">${esc(t)}</p>`;
  const fail = (what, why) => `<div class="aa-line">${esc(what)} did not load. ${esc(cut(why))} Refresh the page to try again.</div>`;
  function guard(title, fn, d) {
    try { return fn(d || {}) || empty("Nothing to show for this block yet."); }
    catch (e) { return fail(title, (e && e.message) || "The answer did not have the shape this block expects."); }
  }

  function blockSplit(d) {
    const s = d.split || d.returning_vs_new || d.audience || {};
    const back = pickN(s, RV) !== null ? pickN(s, RV) : pickN(d, RV);
    const fresh = pickN(s, NV) !== null ? pickN(s, NV) : pickN(d, NV);
    if (back === null && fresh === null) return empty("No viewer split yet. It appears when the server can tell a returning viewer from a new one.");
    const total = (back || 0) + (fresh || 0);
    if (!total) return empty("No viewers counted in this range yet. The split fills in with the first views.");
    const pc = (v) => (v === null || !total ? DASH : one((v / total) * 100));
    const wide = (v) => (v === null ? "0%" : Math.max(2, (v / total) * 100).toFixed(1) + "%");
    const missing = (back === null ? "Returning viewers were not reported. " : "") + (fresh === null ? "New viewers were not reported. " : "");
    const rows = [["ret", "Returning", back], ["new", "New", fresh]];
    return `<p class="help">Viewers in this range. ${show(total)} in total. ${esc(missing)}</p>
      <div class="aa-split">${rows.map(([k, label, v]) => `
        <div class="aa-bar">
          <span class="aa-key"><i class="aa-dot ${k}"></i>${label}</span>
          <span class="aa-track" role="img" aria-label="${label}: ${show(v)} viewers, ${pc(v)}"><i class="aa-fill ${k}" style="width:${wide(v)}"></i></span>
          <span class="aa-val"><b>${show(v)}</b><span>${pc(v)}</span></span>
        </div>`).join("")}</div>`;
  }

  function blockGeo(d) {
    const raw = d.countries || d.geo || d.locations || d.regions || d.country;
    if (!Array.isArray(raw) || !raw.length) return empty("No country data yet. It appears once views come from a country the server can name.");
    const rows = [];
    let given = false;
    for (const c of raw) {
      if (!c || typeof c !== "object") continue;
      const name = c.name || c.country || c.country_name || c.label || c.code;
      const share = pickN(c, ["percent", "percentage", "share", "share_pct"]);
      const count = pickN(c, ["views", "viewers", "value", "count", "total"]);
      if (!name || (share === null && count === null)) continue;
      if (share !== null) given = true;
      rows.push({ name: String(name), share, count });
    }
    if (!rows.length) return empty("Country rows came back without names or counts. The list fills in when the server sends both.");
    const sum = rows.reduce((a, b) => a + (b.count || 0), 0);
    const rated = rows.map((r) => ({ name: r.name, pct: r.share !== null ? r.share : (sum && r.count !== null ? (r.count / sum) * 100 : null) }))
      .sort((a, b) => (b.pct || 0) - (a.pct || 0)).slice(0, 8);
    const top = Math.max(...rated.map((r) => r.pct || 0), 0.0001);
    return `<p class="help">${given ? "Share of all viewers by country." : "Share within these countries, from the counts the server sent."} Top ${rated.length}.</p>
      <div class="aa-list">${rated.map((r) => `
        <div class="aa-row">
          <span class="aa-name" title="${esc(r.name)}">${esc(r.name)}</span>
          <span class="aa-mini"><i style="width:${(((r.pct || 0) / top) * 100).toFixed(1)}%"></i></span>
          <span class="aa-pct">${r.pct === null ? DASH : one(r.pct)}</span>
        </div>`).join("")}</div>`;
  }

  function readGrid(d) {
    const g = d.hours || d.grid || d.heatmap || d.by_hour || d.schedule;
    if (!g) return null;
    let rows = null;
    if (Array.isArray(g) && g.length && g[0] && typeof g[0] === "object" && !Array.isArray(g[0])) {
      rows = Array.from({ length: 7 }, () => Array(24).fill(0));
      for (const c of g) {
        const i = nz(c.day !== undefined ? c.day : c.weekday);
        const j = nz(c.hour);
        if (i === null || j === null || i < 0 || i > 6 || j < 0 || j > 23) continue;
        rows[i][j] += nz(c.value !== undefined ? c.value : (c.views !== undefined ? c.views : c.count)) || 0;
      }
    } else {
      rows = Array.isArray(g) ? g : (g.grid || g.cells || g.rows);
      if (Array.isArray(rows) && rows.length === 24 && Array.isArray(rows[0]) && rows[0].length === 7) {
        rows = Array.from({ length: 7 }, (_, i) => rows.map((col) => col[i]));
      }
    }
    if (!Array.isArray(rows) || rows.length !== 7) return null;
    const cells = rows.map((row) => (Array.isArray(row) && row.length >= 24 ? row.slice(0, 24).map((v) => nz(v) || 0) : null));
    if (cells.some((row) => !row)) return null;
    const names = d.day_names || (Array.isArray(g) ? null : g.day_names) || (Array.isArray(g) ? null : g.days);
    const named = Array.isArray(names) && names.length === 7;
    return { cells, labels: named ? names.map(String) : DAYS, named };
  }

  function blockHours(d) {
    const g = readGrid(d);
    if (!g) return empty("No hour data yet. This grid fills in once views cover a full week.");
    const flat = g.cells.reduce((a, row) => a.concat(row), []);
    const sum = flat.reduce((a, b) => a + b, 0);
    if (!sum) return empty("The week is empty. Cells fill in as views arrive, so check again after a few days of traffic.");
    const max = Math.max(...flat, 0);
    let bi = 0, bj = 0;
    g.cells.forEach((row, i) => row.forEach((v, j) => { if (v > g.cells[bi][bj]) { bi = i; bj = j; } }));
    const tone = (v) => (v <= 0 ? "var(--muted)" : STEP[Math.min(3, Math.max(0, Math.ceil((v / max) * 4) - 1))]);
    const head = `<div class="aa-grid"><span></span>${Array.from({ length: 24 }, (_, h) => `<span class="aa-h">${h % 3 === 0 ? h : ""}</span>`).join("")}</div>`;
    const body = g.cells.map((row, i) => `<div class="aa-grid"><span class="aa-d">${esc(g.labels[i])}</span>${row.map((v, j) => `<span class="aa-c" style="background:${tone(v)}" title="${esc(g.labels[i])} ${pad(j)}:00, ${show(v)}"></span>`).join("")}</div>`).join("");
    const legend = `<div class="aa-legend"><i class="aa-off"></i><span>none</span>${STEP.map((c) => `<i style="background:${c}"></i>`).join("")}<span>more</span><span>Peak ${show(max)}</span></div>`;
    const note = g.named ? "" : " Days run Monday to Sunday.";
    return `<p class="help">Viewers by hour of the week. Each cell is one hour.${esc(note)}</p>
      <div class="aa-scroll"><div class="aa-map">${head}${body}</div></div>
      <p class="aa-swipe" hidden>Swipe to see the whole day</p>
      ${legend}
      <p class="aa-best">Busiest slot: <b>${esc(g.labels[bi])} ${pad(bj)}:00</b>, with ${show(max)} viewers.</p>`;
  }

  const frame = () => [["Returning and new viewers", "Reading the audience answer."], ["Where viewers are", "Reading the country rows."], ["When viewers are on", "Reading the hour grid."]]
    .map(([t, m]) => `<section class="set-sec"><div class="aa-top"><h2>${t}</h2><span class="aa-range">Loading</span></div><div class="set-load">${m}</div></section>`).join("");

  /* The hour grid is wider than a phone, so the scroll region can hide part of it. The swipe line
     only shows when part of the grid is really off-screen; on a wide screen the whole day fits. */
  function markSwipe(root) {
    const scrolls = root.querySelectorAll(".aa-scroll");
    for (const s of scrolls) {
      const hint = s.nextElementSibling;
      if (hint && hint.classList.contains("aa-swipe")) hint.hidden = !(s.scrollWidth > s.clientWidth + 1);
    }
  }

  function paint(root, d, err) {
    const rt = err ? "Request failed" : rangeText(d);
    let noteText = typeof d.note === "string" && d.note.trim() ? esc(cut(d.note)) : "";
    /* The connect sentence used to be plain copy with no way there, so the words get a link,
       the way the Traffic tab does it. */
    if (noteText && /connect a channel/i.test(noteText)) noteText += ' Check <a href="' + APPS + '">Connected apps</a>.';
    const note = noteText ? `<p class="aa-note">${noteText}</p>` : "";
    const blocks = [["Returning and new viewers", blockSplit], ["Where viewers are", blockGeo], ["When viewers are on", blockHours]];
    root.removeAttribute("aria-busy");
    root.innerHTML = note + blocks.map(([title, fn]) => `<section class="set-sec">
      <div class="aa-top"><h2>${title}</h2><span class="aa-range">${esc(rt)}</span></div>
      <div class="set-body">${err ? fail(title, err) : guard(title, fn, d)}</div>
    </section>`).join("");
    markSwipe(root);
    const now = host();
    if (now && now !== root) { now.dataset.aa = root.dataset.aa; draw(now); }
  }

  let busy = false;
  async function draw(root) {
    if (busy) return;
    busy = true;
    root.setAttribute("aria-busy", "true");
    root.innerHTML = frame();
    let data = {}, err = "";
    try {
      const get = typeof P.api === "function" ? P.api : (typeof api === "function" ? api : null);
      if (!get) throw new Error("This page has no request helper loaded.");
      const n = days();
      const out = await get("/api/analytics/audience" + (n ? "?days=" + n : ""));
      data = out && typeof out === "object" ? out : {};
      if (!Object.keys(data).length) err = "The server answered with an empty body.";
    } catch (e) {
      err = (e && (e.detail || e.message)) || "The request failed.";
    } finally {
      busy = false;
    }
    paint(root, data, err);
  }

  const host = () => document.getElementById("an_body");
  const shell = () => window.PeakCutAnalytics;

  /* The Traffic tab has its own file and writes the same box, so only paint when the
     shell says the Audience tab is open. */
  function mine() {
    const A = shell();
    if (!A) return true;
    try { return String((typeof A.tab === "function" ? A.tab() : A.tab) || "audience").toLowerCase() === "audience"; }
    catch { return false; }
  }

  /* The range the shell is showing, so the numbers match the range on screen.
     The route takes at most 3650 days, and Lifetime is longer than that, so the count is capped. */
  function days() {
    try {
      const A = shell() || {}, r = (typeof A.range === "function" ? A.range() : A.range) || {};
      const n = nz(typeof r === "object" ? r.days : r);
      return n && n > 0 ? Math.min(3650, Math.round(n)) : null;
    } catch { return null; }
  }

  function mount() {
    if (!mine()) return;
    const root = host();
    if (!root) return;
    const sig = "d" + days();
    if (root.dataset.aa === sig) return;
    root.dataset.aa = sig;
    draw(root);
  }

  let tick = 0;
  const ping = () => { clearTimeout(tick); tick = setTimeout(mount, 120); };

  P.add("analytics-audience", { after: { drawShell: ping } });

  if (typeof MutationObserver !== "undefined") {
    new MutationObserver(ping).observe(document.documentElement, { childList: true, subtree: true });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();
