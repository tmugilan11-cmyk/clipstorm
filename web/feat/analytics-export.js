/* The Export button on the Insights header. It writes one CSV out of what is already on the page:
 * the key numbers and the video rows. Nothing is asked of the server and nothing is added up here,
 * so a dash in the page stays a dash in the file.
 *
 * The button is drawn on a tab that holds rows of its own. Trends holds none, so the header there
 * carries no Export button. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function") return;

  (typeof P.css === "function" ? P.css : () => {})("analytics-export", `
    .an-head .aex{flex:none}
    .an-head .aex svg{width:16px;height:16px}
  `);

  const object = (v) => (v && typeof v === "object" && !Array.isArray(v)) ? v : null;
  const text = (v) => (typeof v === "string" && v.trim()) ? v.trim() : "";
  const val = (v) => { try { return typeof v === "function" ? v() : v; } catch { return null; } };
  const txt = (el) => el ? text(String(el.textContent || "").replace(/\s+/g, " ")) : "";
  const icon = (n) => { try { return typeof ic === "function" ? ic(n) : ""; } catch { return ""; } };
  const isoOf = (v) => { const s = String(v || "").slice(0, 10); return /^\d{4}-\d{2}-\d{2}$/.test(s) ? s : ""; };
  const STAMP = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

  /* The tabs whose rows this file can write. A tab added later is not on this list, so it has to
     show numbers the file can read before it earns a button. */
  const OWN = ["overview", "content"];
  const LABEL = { overview: "Overview", content: "Content", audience: "Audience", traffic: "Traffic", trends: "Trends" };

  /** The tab the shell is on, in lowercase. It reads the shell first and the pressed button second. */
  function tabName() {
    const A = object(window.PeakCutAnalytics);
    if (A) {
      const t = val(A.tab);
      if (typeof t === "string" && t.trim()) return t.trim().toLowerCase();
    }
    const on = document.querySelector("[data-an-tab].on");
    return on ? text(String(on.dataset.anTab || "")).toLowerCase() : "";
  }

  const labelOf = (k) => {
    const shown = txt(document.querySelector("[data-an-tab].on"));
    if (shown) return shown;
    return LABEL[k] || (k ? k.charAt(0).toUpperCase() + k.slice(1) : "");
  };

  /** The panel the person is looking at, or the page itself when no panels are drawn. */
  function panel() {
    const list = document.querySelectorAll("[data-an-panel]");
    for (const p of list) if (!p.hidden) return p;
    return list.length ? null : document.getElementById("view");
  }

  /** The rows this file can write, if any of them are on the page. */
  const hasRows = (scope) => !!scope && !!scope.querySelector(".akpi-c, table tbody tr");

  function allowed() {
    const k = tabName();
    if (!k) return true;                     // the shell has not said which tab yet, so the button waits
    if (/trend/.test(k)) return false;       // Trends has no rows of its own
    if (OWN.indexOf(k) >= 0) return true;
    return hasRows(panel());                 // an unknown tab earns a button by holding rows
  }

  /** The tooltip: what the button writes, and for which dates. */
  function tipFor() {
    const band = txt(document.querySelector('[data-an="range-line"]'));
    return "Save the numbers on this screen as a CSV file." + (band ? " " + band + "." : "");
  }

  /* ---- reading the screen ------------------------------------------------ */

  /** The six cards, read as they are printed: a label, a value, its unit, the change pill, the dates. */
  function cardsIn(scope) {
    const out = [];
    if (!scope) return out;
    for (const c of scope.querySelectorAll(".akpi-c")) {
      const label = txt(c.querySelector(".akpi-l")), value = txt(c.querySelector(".akpi-n"));
      if (!label && !value) continue;
      const pill = c.querySelector(".pill");   // the arrow says the direction, the title says it in words
      out.push({
        label, value,
        unit: txt(c.querySelector(".akpi-u")),
        change: pill ? (text(pill.getAttribute("title")) || txt(pill)) : "",
        band: txt(c.querySelector(".akpi-r")),
      });
    }
    return out;
  }

  /** The video table, columns and rows, read from the table itself. A dash cell is exported as a dash. */
  function videosIn(scope) {
    const none = { head: [], rows: [] };
    const table = scope ? scope.querySelector("table.ant-t, table") : null;
    if (!table) return none;
    const ths = Array.from(table.querySelectorAll("thead tr:first-child th"));
    const head = ths.map((th) => {
      const unit = txt(th.querySelector(".ant-u"));
      const copy = th.cloneNode(true);
      copy.querySelectorAll("svg, .ant-u").forEach((n) => n.remove());
      const label = text(String(copy.textContent || "").replace(/\s+/g, " ")) || "Column";
      return unit ? label + " (" + unit + ")" : label;
    });
    if (!head.length) return none;
    const rows = [];
    for (const tr of table.querySelectorAll("tbody tr")) {
      const tds = Array.from(tr.children);
      if (!tds.length) continue;
      const first = tds[0], badge = txt(first.querySelector(".ant-short"));
      const title = txt(first.querySelector(".ant-name")) || txt(first);
      const line = [badge ? title + " (" + badge + ")" : title];
      for (let i = 1; i < head.length; i++) line.push(tds[i] ? txt(tds[i]) : "");
      rows.push(line);
    }
    return { head, rows };
  }

  function read() {
    const scope = panel();
    return {
      channel: txt(document.querySelector('[data-an="channel"]')),
      band: txt(document.querySelector('[data-an="range-line"]')),
      updated: txt(document.querySelector('[data-an="updated"]')).replace(/^Last updated\s+/i, ""),
      stamp: STAMP.format(new Date()),
      view: labelOf(tabName()),
      count: scope ? txt(scope.querySelector('[data-ant="count"]')) : "",
      note: scope ? txt(scope.querySelector(".akpi-note")) : "",
      cards: cardsIn(scope),
      videos: videosIn(scope),
    };
  }

  /* ---- writing the file -------------------------------------------------- */

  /** One CSV cell. Needing quotes is decided here, and a title that starts with a formula character
   *  is written as text so a spreadsheet reads it instead of running it. */
  function cell(v) {
    let s = String(v === null || v === undefined ? "" : v).replace(/\s+/g, " ").trim();
    if (/^[=+@-]/.test(s)) s = "'" + s;
    return /[",]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }
  const row = (a) => a.map(cell).join(",");

  function build(r) {
    const out = ["Clipstorm Insights"];
    const meta = [["Channel", r.channel], ["Date range", r.band], ["View", r.view], ["Updated", r.updated],
      ["Exported", r.stamp], ["Videos on screen", r.count]];
    for (const [k, v] of meta) if (v) out.push(row([k, v]));
    if (r.note) out.push(row(["Note", r.note]));
    if (r.cards.length) {
      out.push("");
      out.push("Key numbers");
      out.push(row(["Label", "Value", "Unit", "Change", "Range"]));
      for (const c of r.cards) out.push(row([c.label, c.value, c.unit, c.change, c.band]));
    }
    if (r.videos.rows.length) {
      out.push("");
      out.push("Videos");
      out.push(row(r.videos.head));
      for (const line of r.videos.rows) out.push(row(line));
    }
    return out.length > 1 ? out.join("\r\n") + "\r\n" : "";
  }

  /** The range, as the file name spells it: last-28-days, lifetime, or the two dates. */
  function slug() {
    const A = object(window.PeakCutAnalytics) || {};
    const r = object(val(A.range)) || {};
    const label = text(r.label) || text(A.label);
    const days = Number(r.days !== undefined && r.days !== null ? r.days : A.days);
    if (/lifetime/i.test(label)) return "lifetime";
    if (Number.isFinite(days) && days > 0 && days <= 3660)
      return "last-" + Math.round(days) + (Math.round(days) === 1 ? "-day" : "-days");
    const s = isoOf(r.start) || isoOf(A.start), e = isoOf(r.end) || isoOf(A.end);
    if (s && e) return s + "-to-" + e;
    const words = txt(document.querySelector('[data-an="range-line"]')).toLowerCase()
      .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60);
    return words || "range-not-stated";
  }

  function say(msg, kind) {
    try {
      const fn = (P && typeof P.toast === "function") ? P.toast : (typeof toast === "function" ? toast : null);
      if (fn) fn(msg, kind || "ok");
    } catch { /* a message that cannot be shown is not worth losing the file over */ }
  }

  /* ---- the button -------------------------------------------------------- */

  function sync() {
    const head = document.querySelector(".an-head");
    const here = head ? head.querySelector('[data-ae="export"]') : null;
    if (!head || !allowed()) { if (here) here.remove(); return; }
    let el = here;
    if (!el) {
      head.insertAdjacentHTML("beforeend", `<button class="btn aex" type="button" data-ae="export"`
        + ` title="${esc(tipFor())}">${icon("down")}<span>Export</span></button>`);
      el = head.querySelector('[data-ae="export"]');
      if (!el) return;
    }
    const ready = hasRows(panel());
    if (el.disabled !== !ready) el.disabled = !ready;
    const tip = ready ? tipFor() : "Nothing on this screen has arrived yet. The button turns on when it does.";
    if (el.title !== tip) el.title = tip;
  }

  /* Many changes arrive in one burst, so the button is placed once at the end of it rather than once
     per change. A timer is used instead of a frame because a frame is not drawn while the tab is in
     the background, and the button has to be there when the person comes back to it. */
  let queued = false;
  function look() {
    if (queued) return;
    queued = true;
    setTimeout(() => {
      queued = false;
      try { sync(); } catch (err) { console.warn("[PeakCut] analytics export:", err); }
    }, 0);
  }

  function save() {
    const r = read(), body = build(r);
    if (!body) { say("There is nothing on this screen to save yet.", "bad"); return; }
    if (typeof Blob !== "function" || !window.URL || typeof URL.createObjectURL !== "function") {
      say("This browser cannot build a file from the page.", "bad");
      return;
    }
    const name = "peakcut-insights-" + slug() + ".csv";
    const blob = new Blob(["\uFEFF" + body], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = name; a.rel = "noopener"; a.style.display = "none";
    document.body.appendChild(a);
    a.click();
    try { a.remove(); } catch { /* a link left in the page is harmless */ }
    /* The address is released a moment after the click, so the download has taken its copy first. */
    setTimeout(() => { try { URL.revokeObjectURL(url); } catch {} }, 1000);
    say("Saved " + name + ".", "ok");
  }

  document.addEventListener("click", (e) => {
    const b = e.target && e.target.closest ? e.target.closest('[data-ae="export"]') : null;
    if (!b) return;
    e.preventDefault();
    save();
  });

  try {
    new MutationObserver(look).observe(document.getElementById("view") || document.body, { childList: true, subtree: true });
  } catch (err) { /* without an observer the button is drawn by the look below */ }
  document.addEventListener("peakcut:render", look);
  P.add("analytics-export", { load() { look(); } });
  look();
})();
