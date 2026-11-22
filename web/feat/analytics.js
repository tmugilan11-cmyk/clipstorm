/* Analytics. This file draws the frame only: a title row, four tabs, one date range, and four boxes
   that other files fill. It asks for nothing, and it never shows a number it was not given. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.page !== "function") return;

  (typeof P.css === "function" ? P.css : () => {})("analytics", `
    .an-head{display:flex;align-items:flex-end;justify-content:space-between;gap:14px;flex-wrap:wrap;margin-bottom:18px}
    .an-name{margin:0;font-size:23px;line-height:1.2;font-weight:600;letter-spacing:-.025em;color:var(--text)}
    .an-meta{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:7px;font-size:13px;color:var(--dim)}
    .an-dot{width:4px;height:4px;border-radius:50%;background:var(--line-2);flex:none}
    .an-bar{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:20px}
    .an-bar select{width:auto;min-width:158px;height:36px;font-size:13px;font-weight:600;color:var(--text);cursor:pointer}
    .an-bar label.sw{gap:10px;font-size:13px}.an-bar label.sw input:disabled{cursor:default;opacity:.45}
    .an-hint{margin:0 0 14px;font-size:13px;color:var(--dim)}
    .an-stack{display:flex;flex-direction:column;gap:16px}.an-panel[hidden]{display:none}
    @media (max-width:640px){.an-name{font-size:20px}.an-bar select{width:100%}}
  `);

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const icon = (n) => { try { return typeof ic === "function" ? ic(n) : ""; } catch { return ""; } };
  const TABS = [{ k: "overview", l: "Overview", i: "chart", p: "overview" }, { k: "content", l: "Content", i: "film", p: "content" },
    { k: "audience", l: "Audience", i: "users", p: "body" }, { k: "trends", l: "Trends", i: "chart", p: "body" },
    { k: "traffic", l: "Traffic", i: "globe", p: "body" }];
  const RANGES = [{ v: "7", l: "Last 7 days" }, { v: "28", l: "Last 28 days" }, { v: "90", l: "Last 90 days" },
    { v: "365", l: "Last 365 days" }, { v: "life", l: "Lifetime" }];
  const BOXES = ["an_kpi", "an_charts", "an_table", "an_body"];
  let tabName = "overview", choice = "28", withCompare = false;
  const pad = (n) => String(n).padStart(2, "0");
  const iso = (d) => d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
  const addDays = (d, n) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);
  const at = (s) => new Date(Number(String(s).slice(0, 4)), Number(String(s).slice(5, 7)) - 1, Number(String(s).slice(8, 10)));
  const today = () => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), d.getDate()); };
  const DF = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" });
  const shown = (s) => { try { return DF.format(at(s)); } catch { return String(s || ""); } };

  /** The range on screen, as real dates. Lifetime starts at the first day YouTube could hold data. */
  function range() {
    const end = today();
    if (choice === "life") {
      const start = new Date(2005, 0, 1);
      return { start: iso(start), end: iso(end), days: Math.round((end - start) / 86400000) + 1, label: "Lifetime" };
    }
    const n = Number(choice) || 28;
    return { start: iso(addDays(end, 1 - n)), end: iso(end), days: n, label: "Last " + n + " days" };
  }

  /** The window before this one, of the same length. Nothing when the toggle is off, or for Lifetime. */
  function compare() {
    if (!withCompare || choice === "life") return null;
    const r = range(), last = addDays(at(r.start), -1);
    return { start: iso(addDays(last, 1 - r.days)), end: iso(last), days: r.days };
  }

  function channel() {
    let s = null;
    try { s = (typeof P.state === "function" ? P.state() : null) || null; } catch { s = null; }
    const acc = (s && Array.isArray(s.accounts) ? s.accounts : [])
      .find((a) => a && String(a.platform || "").toLowerCase() === "youtube");
    const name = (acc && (acc.name || acc.label)) ||
      (s && Array.isArray(s.creators) && s.creators[0] ? s.creators[0].name : "");
    return String(name || "").trim() || "Your channel";
  }

  const rangeLine = () => {
    const r = range();
    if (choice === "life") return "Lifetime, up to " + shown(r.end);
    return r.label + ", ending " + shown(r.end) + (withCompare ? ", compared with the " + r.days + " days before" : "");
  };
  const compareNote = () => {
    if (choice === "life") return "Off for Lifetime";
    const c = compare();
    return c ? shown(c.start) + " to " + shown(c.end) : "Off";
  };
  const hintFor = (k) => k === "audience" ? "Who is watching this channel."
    : k === "trends" ? "How these numbers moved over the range on screen."
      : k === "traffic" ? "Where the views came from." : "";

  window.PeakCutAnalytics = {
    range, compare,
    tab: () => tabName,
    mount: (id) => {
      const k = String(id || "").replace(/^#/, "");
      return BOXES.indexOf(k) < 0 ? null : document.getElementById(k);
    },
    reload
  };

  /** The same choice again as plain values. Two of the files in this folder read values instead of
   *  asking for them, so the shell publishes both shapes and they always agree. */
  function agree() {
    const A = window.PeakCutAnalytics, r = range(), c = compare();
    A.start = r.start; A.end = r.end; A.days = r.days; A.label = r.label;
    A.compare_start = c ? c.start : ""; A.compare_end = c ? c.end : "";
  }
  const panels = () => ["overview", "content", "body"].map((p) => {
    const on = (TABS.find((t) => t.k === tabName) || TABS[0]).p === p;
    const inside = p === "overview" ? `<p class="an-hint">Views, watch time, and how the numbers moved against the period before.</p>
        <div id="an_kpi"></div><div id="an_charts"></div>`
      : p === "content" ? `<p class="an-hint">Every video in this range, with what people did with it.</p><div id="an_table"></div>`
      : `<p class="an-hint" data-an="bodyhint">${esc(hintFor(tabName))}</p><div id="an_body"></div>`;
    return `<section class="an-panel${p === "overview" ? " an-stack" : ""}" data-an-panel="${p}"${on ? "" : " hidden"}>${inside}</section>`;
  }).join("");

  function layout() {
    return `<div class="anpg">
      <header class="an-head"><div>
        <h1 class="an-name" data-an="channel">${esc(channel())}</h1>
        <p class="an-meta"><span data-an="updated">Not loaded yet</span><i class="an-dot" aria-hidden="true"></i>
          <span data-an="range-line">${esc(rangeLine())}</span></p>
      </div></header>
      <div class="tabs" role="tablist" aria-label="Analytics views">${TABS.map((t) =>
        `<button class="tabbtn${t.k === tabName ? " on" : ""}" type="button" role="tab" aria-selected="${t.k === tabName}" data-an-tab="${t.k}">${icon(t.i)}<span>${t.l}</span></button>`).join("")}</div>
      <div class="an-bar">
        <select data-an-range aria-label="Date range" title="Date range">${RANGES.map((r) =>
          `<option value="${r.v}"${r.v === choice ? " selected" : ""}>${r.l}</option>`).join("")}</select>
        <label class="sw" title="Also show the same numbers for the period before this one">
          <input type="checkbox" data-an-compare${withCompare ? " checked" : ""}${choice === "life" ? " disabled" : ""}>
          <span>Compare<small data-an="compnote">${esc(compareNote())}</small></span>
        </label>
      </div>
      <div class="an-panels" data-an-panels>${panels()}</div>
    </div>`;
  }

  function paint() {
    const on = (TABS.find((t) => t.k === tabName) || TABS[0]).p;
    document.querySelectorAll("[data-an-tab]").forEach((b) => {
      const here = b.dataset.anTab === tabName;
      b.classList.toggle("on", here);
      b.setAttribute("aria-selected", here ? "true" : "false");
    });
    document.querySelectorAll("[data-an-panel]").forEach((s) => { s.hidden = s.dataset.anPanel !== on; });
    const h = document.querySelector('[data-an="bodyhint"]');
    if (h) h.textContent = hintFor(tabName);
  }

  /** The title row and the two control labels, redrawn from the current choice. */
  function head(when) {
    agree();
    const set = (sel, text) => {
      const el = document.querySelector(sel);
      if (el && el.textContent !== text) el.textContent = text;
    };
    set('[data-an="channel"]', channel());
    set('[data-an="range-line"]', rangeLine());
    set('[data-an="compnote"]', compareNote());
    if (when) set('[data-an="updated"]', "Last updated " + when);
    const box = document.querySelector("[data-an-compare]");
    if (box) { box.checked = withCompare; box.disabled = choice === "life"; }
  }
  /** Tell every analytics file that is already loaded to fill its boxes again. */
  function ask() {
    try { document.dispatchEvent(new CustomEvent("peakcut:render")); } catch {}
    for (const n of (P && Array.isArray(P._order) ? P._order : [])) {
      if (n === "analytics" || String(n).indexOf("analytics-") !== 0) continue;
      const d = P[n];
      if (!d || typeof d.load !== "function") continue;
      try { const run = d.load(); if (run && typeof run.catch === "function") run.catch(() => {}); } catch {}
    }
  }

  /** A new range means new numbers. Drop what the boxes hold, then let the files ask again. */
  function reload() {
    head();
    for (const id of BOXES) {
      const el = document.getElementById(id);
      if (!el) continue;
      delete el.dataset.sig;
      delete el.dataset.aa;
      el.innerHTML = "";
    }
    ask();
  }

  function switchTab(k) {
    if (!k || k === tabName) return;
    tabName = k;
    paint();
    const body = document.getElementById("an_body");   // Audience, Trends and Traffic share this one box
    if (body && (k === "audience" || k === "trends" || k === "traffic")) { delete body.dataset.aa; body.innerHTML = ""; }
    head();
    ask();
  }

  /** Nothing is drawn until a file puts something in a box, so only then is the time stamped. */
  function watch() {
    const box = document.querySelector("[data-an-panels]");
    if (!box || box.dataset.watched === "1" || typeof MutationObserver !== "function") return;
    box.dataset.watched = "1";
    new MutationObserver(() => {
      if (!box.querySelector("#an_kpi > *, #an_charts > *, #an_table > *, #an_body > *")) return;
      head(new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit" }).format(new Date()));
    }).observe(box, { childList: true, subtree: true });
  }
  document.addEventListener("click", (e) => {
    const b = e.target && e.target.closest ? e.target.closest("[data-an-tab]") : null;
    if (!b) return;
    e.preventDefault();
    switchTab(b.dataset.anTab);
  });

  document.addEventListener("change", (e) => {
    const t = e.target;
    if (!t || !t.matches) return;
    if (t.matches("[data-an-range]")) { choice = t.value; reload(); }
    else if (t.matches("[data-an-compare]")) { withCompare = !!t.checked; reload(); }
  });

  P.page("analytics", {
    nav: "Insights", icon: "chart", tip: "Views, watch time and what people did with each video",
    path: "analytics", group: "Understand", order: 20,
    view() { return layout(); },
    load() { head(); paint(); watch(); }
  });

  // A later shell repaint can change the account list, so the title row follows it.
  P.add("analytics", { after: { drawShell() { if (document.querySelector('[data-an="channel"]')) head(); } } });
  agree();
})();
