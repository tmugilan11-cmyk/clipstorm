/* The change since the period before, in words, on one line under each key number.
   Nothing is drawn unless the Compare box in the Insights header is ticked: with it off,
   or on Lifetime, there is no previous period and this file stays out of the way.
   The numbers come from the summary route itself, read with compare=1, so the line and the
   pill above it always agree. A card the server did not send a value for gets a dash, never a zero. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function") return;

  (typeof P.css === "function" ? P.css : () => {})("analytics-compare", `
    .akcmp{display:flex;gap:4px;align-items:baseline;margin-top:2px;font-size:12px;line-height:1.45;
      color:var(--faint);overflow-wrap:anywhere}
    .akcmp>span{min-width:0}
    .akcmp svg{width:10px;height:10px;flex:none;align-self:center}
    .akcmp.up{color:var(--good)}.akcmp.down{color:var(--bad)}
    .akcmp-note{margin:8px 2px 0;font-size:13px;line-height:1.55;color:var(--dim)}
    @media (max-width:640px){.akcmp{font-size:11px}}
  `);

  const BOX = "an_kpi", DASH = "-";            // the same dash the key numbers use for "nothing arrived"
  const NF1 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
  const DAY = { day: "numeric", month: "short" };
  const object = v => (v && typeof v === "object" && !Array.isArray(v)) ? v : null;
  const icon = n => { try { return typeof ic === "function" ? ic(n) : ""; } catch { return ""; } };
  /** The shell hands over getters, not values, so call them. */
  const val = v => { try { return typeof v === "function" ? v() : v; } catch { return null; } };
  const caller = () => (typeof P.api === "function" ? P.api : (typeof api === "function" ? api : null));

  function pick(o, keys) {
    for (const k of keys) {
      const raw = o && o[k];
      if (raw !== null && raw !== undefined && raw !== "" && Number.isFinite(Number(raw))) return Number(raw);
    }
    return null;
  }

  // The six cards the key number row draws, in its order, with every name the route may use for each.
  // The row carries no key of its own, so a card is matched by the label it shows.
  const CARDS = [
    { l: "views", a: ["views"] },
    { l: "watch time", a: ["watch_time", "watch_hours", "watch_time_hours"] },
    { l: "impressions", a: ["impressions"] },
    { l: "click-through rate", a: ["ctr", "click_through_rate"] },
    { l: "average view duration", a: ["average_view_duration", "avg_view_seconds"] },
    { l: "subscribers gained", a: ["subscribers", "subscribers_gained"] },
  ];
  const plain = t => String(t || "").toLowerCase().replace(/\s+/g, " ").trim();
  function keysFor(label) {
    const t = plain(label);
    if (!t) return [];
    const exact = CARDS.find(c => c.l === t);
    if (exact) return exact.a;
    const loose = CARDS.find(c => t.indexOf(c.l) === 0 || c.l.indexOf(t) === 0);
    return loose ? loose.a : [];                 // an unknown card gets a dash, never a guessed number
  }

  /** The numbers the answer carried, by the name the route used. */
  function bag(got) {
    const b = object(got) || {}, out = {}, list = Array.isArray(b.cards) ? b.cards : [];
    for (const c of list) {
      const o = object(c);
      if (!o || !o.key) continue;
      const v = pick(o, ["value"]);
      if (v !== null) out[String(o.key)] = v;
    }
    const m = object(b.metrics);
    if (m) for (const k of Object.keys(m)) {
      const o = object(m[k]);
      const v = o ? pick(o, ["value", "v", "count", "total"]) : pick(m, [k]);
      if (v !== null && out[k] === undefined) out[k] = v;
    }
    return out;
  }

  function day(s) {
    const t = String(s || "").slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(t)) return "";
    const d = new Date(t + "T12:00:00");         // noon, so a time zone cannot move the day
    return isNaN(d) ? "" : d.toLocaleDateString(undefined, DAY);
  }
  function span(v) {
    const o = object(v);
    if (!o) return "";
    const a = day(o.start || o.compare_start), b = day(o.end || o.compare_end);
    return a && b ? a + " to " + b : "";
  }

  const per = n => n > 0 ? "the " + n + " days before" : "the period before";
  /** What the header is asking for, or null when Compare is off or the range is Lifetime. */
  function where() {
    const A = object(window.PeakCutAnalytics);
    if (!A) return null;
    const cmp = object(val(A.compare));
    if (!cmp) return null;
    const rng = object(val(A.range)) || A;
    const days = pick(rng, ["days"]) || pick(cmp, ["days"]);
    return { cmp, days: days || 0, span: span(cmp) };
  }

  /** One card's line: which way it moved, by how much, and the period it is measured against.
      The rounding is the one the pill above the card uses, so the two never disagree. */
  function line(now, was, period) {
    if (now === null || was === null)
      return { c: "none", i: "", t: DASH + " Not sent for " + period, miss: true };
    if (was > 0) {
      const raw = ((now - was) / was) * 100;
      const size = Math.abs(raw) >= 10 ? Math.round(raw) : Math.round(raw * 10) / 10;
      if (!size) return { c: "", i: icon("minus"), t: "No change on " + period };
      const up = size > 0;
      return { c: up ? "up" : "down", i: icon(up ? "up" : "down"),
        t: (up ? "Up " : "Down ") + NF1.format(Math.abs(size)) + " percent on " + period };
    }
    // No base to take a percentage of, so say what the previous period held instead.
    if (was === 0 && now === 0) return { c: "", i: icon("minus"), t: "No change on " + period };
    if (was === 0) {
      const up = now > 0;
      return { c: up ? "up" : "down", i: icon(up ? "up" : "down"),
        t: (up ? "Up" : "Down") + " from zero on " + period };
    }
    return { c: "", i: "", t: "Was " + NF1.format(was) + " in " + period };
  }

  /** The one sentence under the row. It explains a dash, and it never claims a number. */
  function say(s) {
    const lead = s.when ? "The previous period was " + s.when + "." : "";
    if (s.error) return "The previous period could not be read. " + (s.error || "")
      + " Reload this page to try again.";
    if (!s.hasCompare) {
      // With no channel there is nothing to compare against, and the note under the row already asks for one.
      const why = s.own
        ? "A dash means there is nothing to compare yet."
        : "A dash means the previous period could not be read. The numbers above are for this period only.";
      return lead ? lead + " " + why : why;
    }
    if (s.missing) return (lead ? lead + " " : "") + "A dash means the server did not send that card for "
      + s.period + ".";
    return lead || "Compared with " + s.period + ".";
  }

  function clear(box) {
    if (!box) return;
    box.querySelectorAll(".akcmp, .akcmp-note").forEach(n => n.remove());
    try { delete box.dataset.cmp; delete box.dataset.cmpSig; } catch {}
  }

  function draw(box, s) {
    const cards = Array.from(box.querySelectorAll(".akpi-c"));
    if (!cards.length) return;                   // the key number row has not drawn yet
    const got = object(s.got) || {};
    const cur = bag(got), was = object(object(got.compare) && object(got.compare).cards) || {};
    const when = span(got.compare) || (s.w && s.w.span) || "";
    // The key says what range the lines describe and which figures stood above them; the sig also
    // carries what the lines say, so a repaint of the same numbers with the same words is not done twice.
    const key = s.path + "|" + when + "|" + cards.length + "|" + figures(box);
    const sig = key + "|" + JSON.stringify(cur) + "|" + JSON.stringify(was) + "|" + (s.error || "");
    const drawn = cards.every(c => c.querySelector(".akcmp")) && !!box.querySelector(".akcmp-note");
    box.dataset.cmp = key;
    if (box.dataset.cmpSig === sig && drawn) return;
    box.dataset.cmpSig = sig;

    let missing = 0;
    cards.forEach(card => {
      card.querySelectorAll(".akcmp").forEach(n => n.remove());
      const label = card.querySelector(".akpi-l");
      const keys = keysFor(label && label.textContent);
      const L = s.error ? { c: "none", i: "", t: DASH + " Not read", miss: true }
        : line(pick(cur, keys), pick(was, keys), s.period);
      if (L.miss) missing++;
      const tip = L.t + (when ? ", " + when : "") + ".";
      card.insertAdjacentHTML("beforeend",
        `<div class="akcmp${L.c ? " " + L.c : ""}" title="${esc(tip)}">${L.i}<span>${esc(L.t)}</span></div>`);
    });

    box.querySelectorAll(".akcmp-note").forEach(n => n.remove());
    const grid = box.querySelector(".akpi");
    const said = say({ when, period: s.period, error: s.error, missing,
      hasCompare: !!object(got.compare), own: String(got.source || "") === "peakcut" });
    if (grid && said) grid.insertAdjacentHTML("afterend", `<p class="akcmp-note">${esc(said)}</p>`);
  }

  const flight = {};
  let last = { path: "", at: 0, got: null };
  /** One address is read once while it is in flight, and its answer stands for a moment afterwards, so the
      key number row repainting under this one does not become a second request. A new range asks afresh. */
  function asked(path) {
    if (last.path === path && last.got && Date.now() - last.at < 2000) return Promise.resolve(last.got);
    if (flight[path]) return flight[path];
    const call = caller();
    if (!call) return Promise.reject(new Error("The page is still starting."));
    flight[path] = Promise.resolve().then(() => call(path)).then(
      got => { delete flight[path]; last = { path, at: Date.now(), got }; return got; },
      err => { delete flight[path]; throw err; });
    return flight[path];
  }

  /** True when the row already carries a line from this file for exactly this range and these numbers. */
  const settled = (box, key) => box.dataset.cmp === key &&
    Array.from(box.querySelectorAll(".akpi-c")).every(c => c.querySelector(".akcmp")) &&
    !!box.querySelector(".akcmp-note");

  /** What the row says right now. When those figures move, this file reads the route again. */
  const figures = box => Array.from(box.querySelectorAll(".akpi-n")).map(n => n.textContent).join(",");

  async function fill() {
    try {
      const box = document.getElementById(BOX);
      if (!box) return;
      const w = where();
      if (!w || !w.days) { clear(box); return; }  // Compare is off, Lifetime, or no range yet
      const cards = box.querySelectorAll(".akpi-c").length;
      if (!cards) return;                         // the key number row has not drawn yet
      const path = "/api/analytics/summary?days=" + encodeURIComponent(w.days) + "&compare=1";
      if (settled(box, path + "|" + (w.span || "") + "|" + cards + "|" + figures(box))) return;
      const base = { w, path, period: per(w.days) };
      let got;
      try { got = await asked(path); }
      catch (err) {
        const why = String((err && err.message) || err || "").trim().replace(/\.$/, "");
        draw(box, Object.assign({ error: why ? why + "." : "" }, base));
        return;
      }
      const now = document.getElementById(BOX);   // the row may have been redrawn while waiting
      if (now) draw(now, Object.assign({ got }, base));
    } catch { /* one quiet line is the rule, never a throw */ }
  }

  /** The row is drawn and repainted by another file, so follow its container instead of owning it. */
  function watch() {
    const view = document.getElementById("view");
    if (!view || typeof MutationObserver !== "function") return;
    if (view.dataset && view.dataset.cmpOn === "1") return;
    try { view.dataset.cmpOn = "1"; } catch {}
    let soon = 0;
    new MutationObserver(() => {
      if (soon) return;                          // one pass for a burst of changes
      soon = setTimeout(() => { soon = 0; fill(); }, 80);
    }).observe(view, { childList: true, subtree: true });
  }

  document.addEventListener("peakcut:render", () => { fill(); });
  P.add("analytics-compare", {
    label: "The change since the period before",
    load() { fill(); }
  });
  fill(); watch();
})();
