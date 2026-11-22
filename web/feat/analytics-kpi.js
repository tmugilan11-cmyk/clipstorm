/* The six numbers at the top of Analytics. A number appears only when /api/analytics/summary sends one. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function") return;

  (typeof P.css === "function" ? P.css : () => {})("analytics-kpi", `
    .akpi{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));border:1px solid var(--line);border-radius:var(--r);background:var(--bg);overflow:hidden}
    .akpi-c{padding:13px 14px 14px;min-width:0;border-left:1px solid var(--line)}.akpi-c:first-child{border-left:0}
    .akpi-t{display:flex;align-items:center;justify-content:space-between;gap:6px;min-height:21px}
    .akpi-l{flex:1;min-width:0;font-size:12px;font-weight:600;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .akpi .pill{padding:1px 6px;gap:3px;font-size:11px;font-variant-numeric:tabular-nums}.akpi .pill svg{width:10px;height:10px}
    .akpi-v{display:flex;align-items:baseline;gap:4px;margin-top:7px}
    .akpi-n{font-size:24px;font-weight:600;line-height:1.15;letter-spacing:-.03em;color:var(--text);font-variant-numeric:tabular-nums}
    .akpi-n.none{color:var(--faint);font-weight:500}.akpi-u{font-size:12px;color:var(--faint);white-space:nowrap}
    .akpi-r{margin-top:3px;font-size:12px;color:var(--faint);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .akpi-note{margin:10px 2px 0;font-size:13px;line-height:1.5;color:var(--dim)}
    .akpi-note a{color:var(--brand-deep);font-weight:600;text-decoration:none;border-bottom:1px solid var(--brand-line)}
    .akpi-note a:hover{color:var(--text)}
    @media (max-width:1180px){.akpi{grid-template-columns:repeat(3,minmax(0,1fr))}.akpi-c{border-top:1px solid var(--line)}.akpi-c:nth-child(-n+3){border-top:0}.akpi-c:nth-child(3n+1){border-left:0}}
    @media (max-width:640px){.akpi{grid-template-columns:repeat(2,minmax(0,1fr))}.akpi-c{border-left:1px solid var(--line)}.akpi-c:nth-child(2n+1){border-left:0}.akpi-c:nth-child(-n+2){border-top:0}.akpi-n{font-size:21px}}
    @media (max-width:430px){.akpi{grid-template-columns:1fr}.akpi-c{border-left:0;border-top:1px solid var(--line)}.akpi-c:first-child{border-top:0}}
  `);

  const NUM = new Intl.NumberFormat("en-US", {maximumFractionDigits: 1});
  const DASH = "-", APPS = "/app/apps", DAY = {day: "numeric", month: "short"}, IC = typeof ic === "function";
  // A dash, never a zero: nothing was received. `a` lists every name the route may use for a metric.
  const CARDS = [
    {k: "views", l: "Views", u: "views", a: ["views"]},
    {k: "watch", l: "Watch time", u: "hours", a: ["watch_time", "watch_hours", "watch_time_hours"]},
    {k: "impr", l: "Impressions", u: "impressions", a: ["impressions"]},
    {k: "ctr", l: "Click-through rate", u: "%", a: ["ctr", "click_through_rate"], rate: 1},
    {k: "avd", l: "Average view duration", u: "min:sec", secs: 1, a: ["average_view_duration", "avg_view_seconds"]},
    {k: "subs", l: "Subscribers gained", u: "people", a: ["subscribers", "subscribers_gained"]},
  ];
  const object = v => (v && typeof v === "object" && !Array.isArray(v)) ? v : null;
  const text = v => (typeof v === "string" && v.trim()) ? v.trim() : "";   // a label, never a number
  function pick(o, keys) {
    for (const k of keys) { const raw = o && o[k];
      if (raw !== null && raw !== undefined && raw !== "" && Number.isFinite(Number(raw))) return Number(raw); }
    return null;
  }
  /** One metric, and how far it moved: the change if one was sent, else worked out from last time. */
  function grab(bag, m, prev) {
    for (const key of m.a) {
      const o = object(bag[key]);
      const v = o ? pick(o, ["value", "v", "count", "total"]) : pick(bag, [key]);
      if (v === null) continue;
      const sent = o ? pick(o, ["change", "delta", "change_pct", "pct_change"])
        : pick(bag, [key + "_change", key + "_delta", "change_" + key]);
      if (sent !== null) return {v, c: Math.abs(sent) <= 1.5 ? sent * 100 : sent};
      const was = pick(prev, [key]);                 // last period's number for the same metric
      return {v, c: was ? ((v - was) / was) * 100 : null};   // no base means no percentage
    }
    return null;
  }

  const mmss = s => { s = Math.max(0, Math.round(Number(s) || 0));
    return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); };
  // A rate arrives as 0.042, so it needs the hundred. A duration arrives in seconds.
  const shown = (m, v) => m.secs ? mmss(v) : NUM.format(m.rate && Math.abs(v) <= 1 ? v * 100 : v);
  const pct = n => (Math.abs(n) >= 10 ? Math.round(n) : Math.round(n * 10) / 10) + "%";

  function change(c, cmp) {
    if (c === null || c === undefined || !Number.isFinite(c))
      return `<span class="pill" title="No comparison for this period">${DASH}</span>`;
    const up = c > 0, down = c < 0, tip = (up ? "Up " : down ? "Down " : "No change, ") + pct(Math.abs(c))
      + (cmp ? " against " + cmp : " against the period before");
    // The arrow says which way it went, so the pill shows the size alone; without an arrow, keep the sign.
    const face = IC ? pct(Math.abs(c)) : pct(c);
    return `<span class="pill${up ? " ok" : down ? " bad" : ""}" title="${esc(tip)}" aria-label="${esc(tip)}">${
      IC ? ic(up ? "up" : down ? "down" : "minus") : ""}${esc(face)}</span>`;
  }

  const iso = (o, keys) => {
    for (const k of keys) { const s = String((o && o[k]) || "").slice(0, 10);
      if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s; }
    return "";
  };
  /** A range as words: "24 Oct to 20 Nov", or whatever label it came with. */
  function range(v) {
    const o = object(v);
    if (!o) return text(v);
    const a = iso(o, ["start", "from", "since"]), b = iso(o, ["end", "to", "until"]);
    if (!a || !b) return text(o.label);
    const d = new Date(a + "T12:00:00"), e = new Date(b + "T12:00:00");   // noon, so a zone cannot move the day
    return isNaN(d) || isNaN(e) ? "" : d.toLocaleDateString(undefined, DAY) + " to " + e.toLocaleDateString(undefined, DAY);
  }

  /** The shell hands over getters, not values, so call them. */
  const val = v => { try { return typeof v === "function" ? v() : v; } catch { return null; } };
  /** What the shell is asking for, and the address to read it from. The route reads days and compare. */
  function asked() {
    const A = object(window.PeakCutAnalytics) || {};
    const r = object(val(A.range)) || A, c = object(val(A.compare));
    const d = pick(r, ["days"]) || pick(A, ["days"]);      // Lifetime is longer than the route takes, so it is capped
    const q = {s: iso(r, ["start", "from", "since"]), e: iso(r, ["end", "to", "until"]),
      days: d === null ? null : Math.min(3650, Math.round(d)), label: range(r), clabel: range(c)};
    const qs = [], add = (k, v) => { if (v !== null && v !== "" && v !== undefined) qs.push(k + "=" + encodeURIComponent(v)); };
    add("start", q.s); add("end", q.e); add("days", q.days); if (c) add("compare", 1);
    q.path = "/api/analytics/summary" + (qs.length ? "?" + qs.join("&") : "");
    return q;
  }

  /** What the route sent. It answers with a list of cards, a start and an end, and last period's cards. */
  function read(got) {
    const b = object(got) || {}, marks = {}, bag = object(b.metrics) || {};
    // Without a channel the route sends PeakCut's own counters, whose views are not YouTube views.
    const mine = text(b.source) !== "peakcut";
    if (mine && Array.isArray(b.cards))
      for (const c of b.cards) if (object(c) && c.key && bag[c.key] === undefined) bag[c.key] = c.value;
    // With the comparison off the route sends no previous cards, so no percentage is worked out either.
    const prev = object(object(b.compare) && b.compare.cards) || {};
    const gone = [];
    for (const m of CARDS) { const hit = grab(Object.keys(bag).length ? bag : b, m, prev);
      if (hit) marks[m.k] = hit; else gone.push(m.l); }
    const span = object(b.range) || (b.start && b.end ? {start: b.start, end: b.end} : null);
    const out = {marks, range: range(span), compare: range(b.compare)};
    if (!gone.length) return out;                    // all six arrived
    const said = text(b.error) || text(b.detail) || text(b.note);
    if (!Object.keys(marks).length) {
      out.note = said;                               // empty means "nothing arrived", said by note()
      out.link = true;
    } else out.note = "Not in this answer yet: " + gone.join(", ") + ".";
    return out;
  }

  function note(v) {
    const apps = `<a href="${APPS}">Connected apps</a>`, fill = `Connect a channel in ${apps} to fill these in.`;
    if (!v) return `<p class="akpi-note">Not connected yet. ${fill}</p>`;
    if (!v.note && !v.link) return "";
    const said = v.note || "Not connected yet.";
    return `<p class="akpi-note">${esc(said)} ${v.link ? fill : (v.tail || "")}</p>`;
  }

  function paint(box, v, q) {
    const marks = (v && v.marks) || {};
    const band = (v && v.range) || q.label || "Range not stated";
    const cells = CARDS.map(m => {
      const got = marks[m.k], has = !!got && Number.isFinite(got.v);
      const line = !has && band === "Range not stated" ? "No range yet" : band;
      return `<div class="akpi-c"><div class="akpi-t"><span class="akpi-l">${esc(m.l)}</span>${
        change(has ? got.c : null, (v && v.compare) || q.clabel)}</div>
        <div class="akpi-v"><b class="akpi-n${has ? "" : " none"}">${esc(has ? shown(m, got.v) : DASH)}</b>${
        m.u ? `<span class="akpi-u">${esc(m.u)}</span>` : ""}</div>
        <div class="akpi-r" title="${esc(line)}">${esc(line)}</div></div>`;
    }).join("");
    const html = `<div class="akpi" role="group" aria-label="${esc("Key numbers, " + band)}">${cells}</div>${note(v)}`;
    if (typeof put === "function") put(box, html); else box.innerHTML = html;
  }
  /** Draw the frame, then fill it. The same range is never drawn or asked for twice. */
  async function fill() {
    const box = document.getElementById("an_kpi");
    if (!box) return;
    const q = asked();
    if (box.dataset.sig === q.path) return;
    box.dataset.sig = q.path;
    paint(box, null, q);                              // dashes, the reason, the link
    let v;
    try {
      const call = (typeof P.api === "function" ? P.api : null) || (typeof api === "function" ? api : null);
      if (!call) throw new Error("The page is still starting.");
      v = read(await call(q.path));
    } catch (err) {
      const why = String((err && err.message) || err || "").trim().replace(/\.$/, "");
      v = {marks: {}, note: "The summary could not be read." + (why ? " " + why + "." : ""),
        tail: "Reload this page to try again."};
    }
    const now = document.getElementById("an_kpi");
    if (now && now.dataset.sig === q.path) paint(now, v, q);
  }

  // The Analytics page belongs to another file, so its container is not here yet. One observer, one
  // job: when #an_kpi appears or the page is drawn again, fill it.
  function watch() {
    const view = document.getElementById("view");
    if (view && typeof MutationObserver === "function")
      new MutationObserver(() => { if (document.getElementById("an_kpi")) fill(); })
        .observe(view, {childList: true, subtree: true});
  }
  P.add("analytics-kpi", {load() { fill(); }}); fill(); watch();
})();
