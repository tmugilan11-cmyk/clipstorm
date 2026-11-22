/* Revenue for the Overview tab of Analytics. The summary the page already asks for is the only source: this
   file adds no route and works nothing out from an empty answer. A key whose name starts with revenue,
   estimatedRevenue, rpm or cpm is read wherever it sits in that answer, including inside a card list. When
   the answer holds none of them the card says why in one sentence and shows no figures at all, because a
   revenue of zero would be a claim the server never made. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function") return;

  (typeof P.css === "function" ? P.css : () => {})("analytics-revenue", `
    .arv{padding:15px 18px 16px;border:1px solid var(--line);border-radius:var(--r);background:var(--bg);min-width:0}
    .arv-head{display:flex;align-items:baseline;justify-content:space-between;gap:8px 12px;flex-wrap:wrap}
    .arv-t{display:flex;align-items:center;gap:8px;margin:0;font-size:14px;font-weight:600;color:var(--text);letter-spacing:-.01em}
    .arv-t svg{width:15px;height:15px;flex:none;color:var(--brand-deep)}
    .arv-range{font-size:12px;color:var(--faint);white-space:nowrap}
    .arv .pill{padding:1px 6px;gap:3px;font-size:11px;font-variant-numeric:tabular-nums}
    .arv .pill svg{width:10px;height:10px}
    .arv-cells{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));margin-top:12px;border-top:1px solid var(--line)}
    .arv-cell{min-width:0;padding:12px 14px 0;border-left:1px solid var(--line)}
    .arv-cell:first-child{border-left:0;padding-left:0}
    .arv-l{display:block;font-size:12px;font-weight:600;color:var(--dim)}
    .arv-n{display:block;margin-top:5px;font-size:22px;font-weight:600;line-height:1.15;letter-spacing:-.03em;color:var(--text);font-variant-numeric:tabular-nums}
    .arv-n.none{color:var(--faint);font-weight:500}
    .arv-u{display:block;margin-top:3px;font-size:12px;color:var(--faint)}
    .arv-quiet{display:flex;align-items:flex-start;gap:9px;margin-top:9px}
    .arv-quiet svg{width:15px;height:15px;flex:none;margin-top:1px;color:var(--faint)}
    .arv-quiet p{margin:0;font-size:13px;line-height:1.55;color:var(--dim)}
    .arv-note{margin:12px 0 0;font-size:12px;line-height:1.5;color:var(--faint)}
    @media (max-width:640px){.arv-cell{border-left:0;padding-left:0}.arv-cells{grid-template-columns:1fr}.arv-cell+.arv-cell{border-top:1px solid var(--line);padding-top:12px}}
  `);

  const DASH = "-", MARK = "data-arv", DAY = {day: "numeric", month: "short"};
  const WANT = [
    {k: "revenue", l: "Revenue", heads: ["revenue", "estimatedrevenue"]},
    {k: "rpm", l: "RPM", heads: ["rpm"]},
    {k: "cpm", l: "CPM", heads: ["cpm"]}
  ];
  // A key may end in a currency or a word for the amount. Anything else on the end is a different number:
  // revenue_change and rpm_percent are not the amount, so they are never shown as one.
  const TAILS = ["amount", "total", "value", "estimate", "estimated", "gross", "net", "money", "earned", "earnings"];
  // The period before this one arrives under one of these names and is read on its own.
  const SKIP = ["compare", "comparison", "previous", "prev", "prior", "lastperiod", "previousperiod", "priorperiod"];
  const object = v => (v && typeof v === "object" && !Array.isArray(v)) ? v : null;
  const text = v => (typeof v === "string" && v.trim()) ? v.trim() : "";
  const norm = k => String(k == null ? "" : k).toLowerCase().replace(/[^a-z0-9]/g, "");
  const icon = n => { try { return typeof ic === "function" ? ic(n) : ""; } catch { return ""; } };
  const paint = (el, html) => { if (!el) return; if (typeof put === "function") put(el, html); else el.innerHTML = html; };
  const pctOf = n => (Math.abs(n) >= 10 ? Math.round(n) : Math.round(n * 10) / 10) + "%";
  function num(v) {
    if (typeof v === "number") return Number.isFinite(v) ? v : null;
    if (typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v))) return Number(v);
    return null;
  }

  /** A key that names the figure itself. `head` arrives already reduced to letters and digits. */
  function names(key, head) {
    const nk = norm(key);
    if (nk === head) return true;
    if (nk.indexOf(head) !== 0) return false;
    const tail = nk.slice(head.length);
    return /^[a-z]{3}$/.test(tail) || TAILS.indexOf(tail) >= 0;
  }

  /** Every revenue figure in the answer, at any depth, and the currency when one is stated. */
  function harvest(input) {
    const figures = {}, seen = new Set();
    let currency = "";
    const keep = (nk, n, holder) => {
      for (const w of WANT) {
        if (figures[w.k] !== undefined) continue;
        if (!w.heads.some(h => names(nk, h))) continue;
        figures[w.k] = n;
        const said = text(holder && (holder.unit || holder.currency));
        if (!currency && /^[A-Za-z]{3}$/.test(said)) currency = said;
        return;
      }
    };
    const walk = (v, depth) => {
      if (!v || typeof v !== "object" || depth > 8 || seen.has(v)) return;
      seen.add(v);
      if (Array.isArray(v)) { for (const x of v) walk(x, depth + 1); return; }
      const named = norm(v.key || v.metric || v.name), card = num(v.value);
      if (named && card !== null) keep(named, card, v);          // a card names its own number
      for (const k of Object.keys(v)) {
        const raw = v[k], nk = norm(k);
        if (nk === "currency" || nk === "currencycode" || nk === "revenuecurrency") {
          const said = text(raw);
          if (!currency && /^[A-Za-z]{3}$/.test(said)) currency = said;
          continue;
        }
        if (SKIP.indexOf(nk) >= 0) continue;
        const n = num(raw);
        if (n !== null) keep(nk, n, v); else walk(raw, depth + 1);
      }
    };
    walk(input, 0);
    return {figures, currency};
  }

  const iso = v => { const s = String(v == null ? "" : v).slice(0, 10); return /^\d{4}-\d{2}-\d{2}$/.test(s) ? s : ""; };
  /** A range as words: "24 Oct to 20 Nov", or the label it came with. */
  function spell(o) {
    const b = object(o) || {}, said = text(b.label);
    const a = iso(b.start) || iso(b.from) || iso(b.since), z = iso(b.end) || iso(b.to) || iso(b.until);
    if (!a || !z) return said;
    const d1 = new Date(a + "T12:00:00"), d2 = new Date(z + "T12:00:00");   // noon, so a zone cannot move a day
    if (isNaN(d1) || isNaN(d2)) return said;
    return d1.toLocaleDateString(undefined, DAY) + " to " + d2.toLocaleDateString(undefined, DAY);
  }

  /** An amount in the currency the answer stated, and a plain number when it stated none. */
  function cash(v, currency) {
    const n = num(v);
    if (n === null) return DASH;
    const code = String(currency || "").toUpperCase();
    if (/^[A-Z]{3}$/.test(code)) {
      try { return new Intl.NumberFormat(undefined, {style: "currency", currency: code, maximumFractionDigits: 2}).format(n); } catch {}
    }
    return new Intl.NumberFormat(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}).format(n);
  }

  /** The shell hands over getters, not values, so call them. */
  const val = v => { try { return typeof v === "function" ? v() : v; } catch { return null; } };
  /** What the shell is asking for, and the address to read it from. The route reads days and compare. */
  function asked() {
    const A = object(val(window.PeakCutAnalytics)) || {};
    const r = object(val(A.range)) || A, c = object(val(A.compare));
    const qs = [], add = (k, v) => { if (v !== null && v !== undefined && v !== "") qs.push(k + "=" + encodeURIComponent(v)); };
    add("start", iso(r.start) || iso(r.from));
    add("end", iso(r.end) || iso(r.to));
    const days = num(r.days);
    add("days", days === null ? null : Math.min(3650, Math.max(0, Math.round(days))));   // the route's own limit
    if (c) add("compare", 1);
    return {path: "/api/analytics/summary" + (qs.length ? "?" + qs.join("&") : ""), label: spell(r), clabel: spell(c)};
  }

  /** How far revenue moved, only when this period and the one before both sent a figure. */
  function moved(now, prev, q) {
    const a = now.figures.revenue, b = prev.figures.revenue;
    if (a === undefined || b === undefined || !(b > 0)) return "";      // no base means no percentage
    const pct = ((a - b) / b) * 100;
    if (!Number.isFinite(pct)) return "";
    const up = pct > 0.05, down = pct < -0.05;
    const said = (up ? "Up " : down ? "Down " : "No change, ") + pctOf(Math.abs(pct)) +
      (q.clabel ? " against " + q.clabel : " against the period before");
    return `<span class="pill${up ? " ok" : down ? " bad" : ""}" title="${esc(said)}" aria-label="${esc(said)}">${
      icon(up ? "up" : down ? "down" : "minus")}${esc(pctOf(Math.abs(pct)))}</span>`;
  }

  function draw(box, got, why, q) {
    const b = object(got) || {};
    const span = spell(b) || q.label || "";
    const found = why ? {figures: {}, currency: ""} : harvest(b);
    const prev = why ? {figures: {}, currency: ""} : harvest(object(b.compare));
    const have = WANT.filter(w => found.figures[w.k] !== undefined);
    let html;
    if (!have.length) {
      // Nothing was sent. One sentence, no numbers, and no zero standing in for an answer.
      const said = why
        ? "The summary could not be read." + (why ? " " + why + "." : "") + " Reload this page to try again."
        : "Revenue needs a YouTube Partner Program channel, so there is nothing to show for this range yet.";
      html = `<div class="arv-head"><h2 class="arv-t">${icon("money")}Revenue</h2>${
        span ? `<span class="arv-range">${esc(span)}</span>` : ""}</div>
        <div class="arv-quiet">${icon(why ? "warn" : "bulb")}<p>${esc(said)}</p></div>`;
    } else {
      const cells = WANT.map(w => {
        const v = found.figures[w.k], has = v !== undefined;
        const unit = !has ? "not sent" : w.k === "revenue" ? (found.currency || "currency not stated") : "per 1,000 views";
        return `<div class="arv-cell"><span class="arv-l">${esc(w.l)}</span>
          <b class="arv-n${has ? "" : " none"}">${esc(has ? cash(v, found.currency) : DASH)}</b>
          <span class="arv-u">${esc(unit)}</span></div>`;
      }).join("");
      const gone = WANT.filter(w => found.figures[w.k] === undefined).map(w => w.l);
      const note = gone.length
        ? `<p class="arv-note">Not in this answer yet: ${esc(gone.join(", "))}. A dash means the summary did not send that number, not that it was zero.</p>` : "";
      html = `<div class="arv-head"><h2 class="arv-t">${icon("money")}Revenue</h2>${
        span ? `<span class="arv-range">${esc(span)}</span>` : ""}${moved(found, prev, q)}</div>
        <div class="arv-cells">${cells}</div>${note}`;
    }
    box.setAttribute("aria-label", "Revenue" + (span ? ", " + span : ""));
    paint(box, html);
  }

  /** The Overview panel belongs to another file, so this waits for it and puts one card at its end. */
  function host() {
    const panel = document.querySelector('[data-an-panel="overview"]');
    if (!panel) return null;
    let el = panel.querySelector("[" + MARK + "]");
    if (!el) {
      el = document.createElement("section");
      el.className = "arv";
      el.setAttribute("role", "group");
      el.setAttribute(MARK, "1");
      panel.append(el);
    }
    return el;
  }

  /** Read the same summary the rest of the tab reads, then draw what it actually sent. */
  async function fill() {
    const box = host();
    if (!box) return;                                    // not on the Analytics page right now
    const q = asked();
    if (box.dataset.sig === q.path) return;              // this range is already on screen
    box.dataset.sig = q.path;
    let got = null, why = "";
    try {
      const call = (typeof P.api === "function" ? P.api : null) || (typeof api === "function" ? api : null);
      if (!call) throw new Error("The page is still starting.");
      got = await call(q.path);
    } catch (err) {
      why = String((err && err.message) || err || "").trim().replace(/\.$/, "");
    }
    const now = host();
    if (!now || now.dataset.sig !== q.path) return;      // the page moved on while the answer was coming
    draw(now, got, why, q);
  }

  // The card lives inside the Analytics page, which is drawn by another file: when that markup appears or is
  // drawn again, fill the card. One observer, one job.
  function watch() {
    const view = document.getElementById("view");
    if (view && typeof MutationObserver === "function")
      new MutationObserver(() => { if (document.querySelector('[data-an-panel="overview"]')) fill(); })
        .observe(view, {childList: true, subtree: true});
  }
  P.add("analytics-revenue", {load() { fill(); }});
  fill(); watch();
})();
