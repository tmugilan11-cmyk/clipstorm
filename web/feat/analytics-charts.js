/* Views and watch time, one day at a time. Two hand-drawn SVG charts: this range in currentColor,
 * the range before it thinner and dashed. Hovering a day names the date and both numbers in one
 * floating box. A range with no numbers gets a sentence, never an axis with nothing on it. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function") return;

  (typeof P.css === "function" ? P.css : () => {})("analytics-charts", `
    .ac-wrap{position:relative}
    .ac-chart{padding:15px 18px 12px;border:1px solid var(--line);border-radius:var(--r);background:var(--bg)}
    .ac-chart+.ac-chart{margin-top:14px}
    .ac-head{display:flex;align-items:baseline;justify-content:space-between;gap:12px}
    .ac-title{font-size:14px;font-weight:600;color:var(--text);letter-spacing:-.01em}
    .ac-range{font-size:12px;color:var(--faint);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .ac-svg{display:block;width:100%;height:auto;margin-top:4px;color:var(--brand-deep);touch-action:pan-y}
    .ac-grid{stroke:var(--line-2);stroke-width:1;shape-rendering:crispEdges}
    .ac-tick,.ac-x{font-size:11px;fill:var(--faint);font-variant-numeric:tabular-nums}
    .ac-main{fill:none;stroke:currentColor;stroke-width:2.2;stroke-linejoin:round;stroke-linecap:round}
    .ac-fill{fill:currentColor;stroke:none;opacity:.055}
    .ac-comp{fill:none;stroke:currentColor;stroke-width:1.3;stroke-dasharray:4 4;opacity:.36}
    .ac-cursor{stroke:var(--faint);stroke-width:1;stroke-dasharray:3 3;opacity:0;pointer-events:none}
    .ac-cursor.on{opacity:.8}
    .ac-hit{fill:transparent;cursor:crosshair}
    .ac-legend{display:flex;flex-wrap:wrap;gap:14px;margin:8px 0 1px;font-size:12px;color:var(--dim)}
    .ac-key{display:inline-flex;align-items:center;gap:7px}
    .ac-swatch{display:inline-block;width:17px;border-top:2.2px solid currentColor;color:var(--brand-deep)}
    .ac-swatch.alt{border-top:1.3px dashed currentColor;opacity:.5}
    .ac-empty{margin:16px 0 10px;font-size:13px;color:var(--dim)}
    .ac-tip{position:absolute;z-index:5;min-width:158px;padding:8px 10px 9px;border:1px solid var(--line-2);
      border-radius:var(--r-sm);background:var(--bg);font-size:12px;color:var(--dim);pointer-events:none;opacity:0;
      transform:translateY(2px);transition:opacity .1s,transform .1s}
    .ac-tip.on{opacity:1;transform:none}
    .ac-tip .d{display:block;font-size:11px;font-weight:600;color:var(--text);margin-bottom:5px}
    .ac-tip .r{display:flex;justify-content:space-between;gap:18px;line-height:1.65}
    .ac-tip .r b{font-weight:600;color:var(--text);font-variant-numeric:tabular-nums}
    @media (prefers-reduced-motion:reduce){.ac-tip{transition:none}}
  `);

  const HOLD = "an_charts", PATH = "/api/analytics/timeseries";
  const H = 180, PL = 46, PR = 14, PT = 22, PB = 26, DASH = "-";
  const GROUP = new Intl.NumberFormat("en-US"), obj = v => (v && typeof v === "object" && !Array.isArray(v)) ? v : null;
  const day = v => /^\d{4}-\d{2}-\d{2}/.test(String(v || "")) ? String(v).slice(0, 10) : "";
  function num(v) { if (v === null || v === undefined || v === "") return null; const n = Number(v); return Number.isFinite(n) ? n : null; }
  function pick(o, keys) { for (const k of keys) { const n = num(o[k]); if (n !== null) return n; } return null; }
  const paint = (el, html) => { if (typeof put === "function") put(el, html); else el.innerHTML = html; };
  function date(d, fmt) { const t = d ? new Date(d + "T00:00:00") : null; return t && !isNaN(t.getTime()) ? t.toLocaleDateString(undefined, fmt) : ""; }
  const when = d => date(d, {month: "short", day: "numeric"});
  const long = d => date(d, {weekday: "short", month: "short", day: "numeric"});
  const shortN = n => n >= 1e6 ? (n / 1e6).toFixed(n % 1e6 ? 1 : 0) + "m" : n >= 1000 ? (n / 1000).toFixed(n % 1000 ? 1 : 0) + "k" : String(Math.round(n * 10) / 10);
  const nice = n => { if (!(n > 0)) return 1; const p = Math.pow(10, Math.floor(Math.log10(n))), f = n / p; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p; };

  const VK = ["value", "views", "count", "total", "y", "v", "minutes", "estimatedMinutesWatched"];
  const CK = ["compare", "comparison", "previous", "prior", "prev", "compare_value", "comparison_value"];
  const LK = ["points", "rows", "series", "data", "items", "days", "values"];
  const CHARTS = [
    {key: "views", title: "Views", unit: "views", metric: "views", empty: "No views in this range yet",
      full: n => GROUP.format(Math.round(n))},
    {key: "time", title: "Watch time", unit: "minutes", metric: "estimatedMinutesWatched", alt: "watch_time",
      empty: "No watch time in this range yet", full: n => GROUP.format(n >= 100 ? Math.round(n) : Math.round(n * 10) / 10)},
  ];

  // The shell says which days it is showing, so the charts ask for the same days it does.
  function chosen() {
    const A = obj(window.PeakCutAnalytics) || {};
    const r = obj(A.range) || A, c = obj(A.compare);
    const iso = (o, keys) => { for (const k of keys) { const d = day(o && o[k]); if (d) return d; } return ""; };
    const s = iso(r, ["start", "from", "since"]), e = iso(r, ["end", "to", "until"]);
    const cs = iso(c, ["start", "from", "since"]), ce = iso(c, ["end", "to", "until"]);
    let days = num(r.days) || num(A.days) || 0;
    if (!days && s && e) days = Math.round((new Date(e + "T00:00:00") - new Date(s + "T00:00:00")) / 864e5) + 1;
    const q = [];
    if (days > 0) q.push("days=" + Math.min(3650, days));
    if (s) { q.push("start=" + s); if (e) q.push("end=" + e); }
    if (cs) q.push("compare_start=" + cs);
    if (ce) q.push("compare_end=" + ce);
    return {qs: q.length ? "&" + q.join("&") : "", days,
      label: s && e ? when(s) + " to " + when(e) : days ? "Last " + days + " days" : "Date range not stated"};
  }

  function compareOf(o) {
    for (const k of CK) {
      const v = o[k], n = v === undefined || v === null ? null : obj(v) ? pick(obj(v), VK) : num(v);
      if (n !== null) return n;
    }
    return null;
  }
  // One metric's series, from a bare list or from a wrapper with the comparison beside it.
  function series(got) {
    const b = obj(got), at = o => day(o.date || o.day || o.start || o.from || o.x);
    const list = Array.isArray(got) ? got : b ? (LK.map(k => b[k]).find(Array.isArray) || []) : [];
    const before = b ? [b.compare, b.comparison, b.previous, b.prior, b.prev].find(Array.isArray) : null;
    const rows = list.map(raw => { const o = obj(raw);
      return o ? {d: at(o), v: pick(o, VK), c: compareOf(o)} : {d: "", v: num(raw), c: null}; });
    // A previous period is a different set of dates, so its numbers line up by position, not by day.
    if (before && before.length) before.forEach((raw, i) => {
      const o = obj(raw), n = o ? pick(o, VK) : num(raw), r = rows[i];
      if (r && n !== null && r.c === null) r.c = n; });
    if (rows.length > 1 && rows.every(r => r.d)) rows.sort((x, y) => x.d < y.d ? -1 : x.d > y.d ? 1 : 0);
    return rows;
  }

  const head = (c, sub) => `<div class="ac-head"><span class="ac-title">${esc(c.title)}</span>`
    + `<span class="ac-range">${esc(sub)}</span></div>`;

  function chart(c, rows, w, sub) {
    const n = rows.length, span = w - PL - PR, unit = c.unit;
    let max = 0, sum = 0, first = -1, last = -1;
    rows.forEach((r, i) => {
      if (r.v !== null) { max = Math.max(max, r.v); sum += r.v; if (first < 0) first = i; last = i; }
      if (r.c !== null) max = Math.max(max, r.c);
    });
    const top = nice(max), base = (H - PB).toFixed(1);
    const x = i => n <= 1 ? PL + span / 2 : PL + i * span / (n - 1);
    const y = v => PT + (1 - v / top) * (H - PT - PB);
    const line = k => { let d = "", on = false;
      rows.forEach((r, i) => { if (r[k] === null) return;
        d += (on ? "L" : "M") + x(i).toFixed(1) + " " + y(r[k]).toFixed(1) + " "; on = true; });
      return d.trim(); };
    const main = line("v"), comp = line("c");
    const area = first < 0 || last <= first ? ""
      : main + " L " + x(last).toFixed(1) + " " + base + " L " + x(first).toFixed(1) + " " + base + " Z";
    const grid = [1, 0.5, 0].map(t => { const gy = y(top * t).toFixed(1);
      return `<line class="ac-grid" x1="${PL}" y1="${gy}" x2="${w - PR}" y2="${gy}"/>`
        + `<text class="ac-tick" x="${PL - 8}" y="${(Number(gy) + 3.5).toFixed(1)}" text-anchor="end">`
        + `${esc(shortN(top * t))}</text>`; }).join("");
    const every = Math.max(1, Math.ceil(n / 6)), ticks = rows.map((r, i) => {
      if (!r.d || (i !== n - 1 && (i % every || n - 1 - i < every))) return "";
      const lx = Math.min(Math.max(x(i), PL + 9), w - PR - 9);
      return `<text class="ac-x" x="${lx.toFixed(1)}" y="${H - 8}" text-anchor="middle">${esc(when(r.d))}</text>`;
    }).join("");
    const said = `${c.title} per day across ${n} days. ${c.full(sum)} ${unit} in total. Highest ${c.full(max)} ${unit} in one day.`;
    const legend = `<span class="ac-key"><i class="ac-swatch"></i>This range</span>`
      + (rows.some(r => r.c !== null) ? `<span class="ac-key"><i class="ac-swatch alt"></i>Previous range</span>` : "");
    return `<div class="ac-chart">${head(c, sub)}`
      + `<svg class="ac-svg" data-k="${esc(c.key)}" viewBox="0 0 ${w} ${H}" width="100%" role="img" aria-label="${esc(said)}">`
      + `${grid}${area ? `<path class="ac-fill" d="${area}"/>` : ""}${comp ? `<path class="ac-comp" d="${comp}"/>` : ""}`
      + `<path class="ac-main" d="${main}"/>`
      + `${ticks}<text class="ac-tick" x="${PL - 8}" y="${PT - 12}" text-anchor="end">${esc(unit)}</text>`
      + `<line class="ac-cursor" x1="0" y1="${PT}" x2="0" y2="${base}"/>`
      + `<rect class="ac-hit" x="${PL}" y="${PT}" width="${span}" height="${H - PT - PB}"/></svg>`
      + `<div class="ac-legend">${legend}</div></div>`;
  }

  function empty(c, sub, why) {
    const said = why ? "The numbers could not be read. " + why + ". Reload this page to try again." : c.empty + ".";
    return `<div class="ac-chart">${head(c, sub)}<p class="ac-empty">${esc(said)}</p></div>`;
  }
  // One floating box for both charts, placed inside the frame so it travels with the page.
  function wire(svg, c, rows, w, wrap, tip) {
    const n = rows.length, span = w - PL - PR, hasComp = rows.some(r => r.c !== null);
    const at = i => n <= 1 ? PL + span / 2 : PL + i * span / (n - 1);
    const cursor = svg.querySelector(".ac-cursor"), hit = svg.querySelector(".ac-hit");
    let seen = -1;
    const hide = () => { seen = -1; tip.classList.remove("on"); cursor.classList.remove("on"); };
    function show(i) {
      const r = rows[i]; if (!r || i === seen) return;
      seen = i;
      cursor.setAttribute("x1", at(i).toFixed(1)); cursor.setAttribute("x2", at(i).toFixed(1));
      cursor.classList.add("on");
      const cell = k => r[k] === null ? DASH : c.full(r[k]) + " " + c.unit;
      tip.innerHTML = `<span class="d">${esc(long(r.d) || "Day " + (i + 1))}</span>`
        + `<span class="r"><span>This range</span><b>${esc(cell("v"))}</b></span>`
        + (hasComp ? `<span class="r"><span>Previous range</span><b>${esc(cell("c"))}</b></span>` : "");
      tip.classList.add("on");
      const box = svg.getBoundingClientRect(), frame = wrap.getBoundingClientRect();
      const left = (box.left - frame.left) + at(i) * (box.width / w) - tip.offsetWidth / 2;
      tip.style.left = Math.max(4, Math.min(left, wrap.clientWidth - tip.offsetWidth - 4)) + "px";
      tip.style.top = Math.max(2, box.top - frame.top + 6) + "px";
    }
    function seek(ev) {
      const box = svg.getBoundingClientRect();
      if (!box.width) return;
      const ux = (ev.clientX - box.left) * (w / box.width);
      show(n <= 1 ? 0 : Math.max(0, Math.min(n - 1, Math.round(((ux - PL) / span) * (n - 1)))));
    }
    hit.addEventListener("pointermove", seek);
    hit.addEventListener("pointerdown", seek);
    hit.addEventListener("pointerleave", hide);
    svg.addEventListener("pointerleave", hide);
  }

  let held = null, sig = "", wide = 0, later = 0;

  function render(box) {
    if (!box || !held) return;
    const w = Math.max(320, Math.round((box.clientWidth || 720) - 38));
    wide = w;
    const body = CHARTS.map(c => {
      const got = held[c.key] || {}, rows = got.rows || [];
      const alive = rows.some(r => (r.v || 0) > 0 || (r.c || 0) > 0);
      const shape = {key: c.key, title: c.title, unit: got.unit || c.unit, full: c.full, empty: c.empty};
      const sub = got.label || chosen().label;
      if (!alive) return empty(shape, sub, got.why);
      c.unit = shape.unit;
      return chart(shape, rows, w, sub);
    }).join("");
    paint(box, `<div class="ac-wrap">${body}<div class="ac-tip" aria-live="polite"></div></div>`);
    const wrap = box.firstElementChild, tip = wrap && wrap.querySelector(".ac-tip");
    if (!tip) return;
    CHARTS.forEach(c => {
      const got = held[c.key] || {}, svg = wrap.querySelector(`.ac-svg[data-k="${c.key}"]`);
      if (svg && got.rows && got.rows.length) wire(svg, c, got.rows, w, wrap, tip);
    });
  }

  /** Ask for one metric, falling back to the name the route knows when it refuses the first. */
  async function ask(call, c, q) {
    let got;
    try { got = await call(`${PATH}?metric=${c.metric}${q}`); }
    catch (err) { if (!c.alt) throw err; got = await call(`${PATH}?metric=${c.alt}${q}`); }
    const b = obj(got) || {};
    return {rows: series(got), unit: String(b.unit || c.unit), why: "",
      label: b.start && b.end ? when(day(b.start)) + " to " + when(day(b.end)) : ""};
  }

  async function fill() {
    const box = document.getElementById(HOLD);
    if (!box) return;
    const q = chosen().qs;
    if (sig === q && held) return render(box);
    sig = q;
    const call = (typeof P.api === "function" ? P.api : null) || (typeof api === "function" ? api : null);
    if (!call) return;
    if (!held) paint(box, `<div class="ac-wrap"><div class="ac-chart"><p class="ac-empty">${
      esc("Reading views and watch time for " + chosen().label + ".")}</p></div></div>`);
    const out = {};
    await Promise.all(CHARTS.map(async c => {
      try { out[c.key] = await ask(call, c, q); }
      catch (err) { out[c.key] = {rows: [], why: String((err && err.message) || err || "").trim().replace(/\.$/, "")
        || "The route did not answer"}; }
    }));
    held = out;
    const now = document.getElementById(HOLD);
    if (now) render(now);
  }

  // The shell draws #an_charts after this file loads, and again on every range change.
  function watch() {
    const view = document.getElementById("view");
    if (view && typeof MutationObserver === "function") new MutationObserver(() => {
      if (document.getElementById(HOLD)) fill();
    }).observe(view, {childList: true, subtree: true});
  }

  // The drawing asks for a width, so a much wider frame gets a fresh one.
  window.addEventListener("resize", () => {
    clearTimeout(later);
    later = setTimeout(() => {
      const box = document.getElementById(HOLD);
      if (box && held && Math.abs((box.clientWidth || 720) - 38 - wide) >= 12) render(box);
    }, 120);
  });

  P.add("analytics-charts", {load() { fill(); }});
  fill();
  watch();
})();
