/* The "Right now" card on Analytics. One number: the views on the newest day, said only when the
   server sent a number for today. `/api/analytics/summary` carries the source and the window but no
   per-day point, so this file also reads `/api/analytics/timeseries`, which is the one route that
   sends a value per day. Without a number for today the card says what it needs instead of guessing.

   Refresh runs on one timer just past the 60 second floor, skips every tick while the tab is
   hidden or the Overview panel is off screen, and is cleared as soon as the card leaves the
   document. */
(() => {
  const P = window.PeakCut;
  if (!P || typeof P.add !== "function") return;

  (typeof P.css === "function" ? P.css : () => {})("analytics-realtime", `
    .annow{display:flex;align-items:center;gap:18px;flex-wrap:wrap;padding:14px 16px;border:1px solid var(--line);border-radius:var(--r);background:var(--bg)}
    .annow-dot{width:8px;height:8px;border-radius:50%;background:var(--line-2);flex:none}
    .annow.live .annow-dot{background:var(--good)}
    .annow-top{min-width:132px}
    .annow-l{font-size:12px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--dim)}
    .annow-v{display:flex;align-items:baseline;gap:6px;margin-top:5px}
    .annow-n{font-size:26px;font-weight:600;line-height:1.1;letter-spacing:-.03em;color:var(--text);font-variant-numeric:tabular-nums}
    .annow-n.none{color:var(--faint);font-weight:500}
    .annow-u{font-size:12px;color:var(--faint);white-space:nowrap}
    .annow-s{flex:1 1 220px;min-width:200px;margin:0;font-size:13px;line-height:1.5;color:var(--dim)}
    .annow-m{flex:1 1 100%;display:flex;align-items:center;gap:5px;margin:0;font-size:12px;color:var(--faint)}
    .annow-m svg{width:11px;height:11px;flex:none;opacity:.7}
    .annow-note{flex:1 1 100%;margin:0;font-size:13px;line-height:1.5;color:var(--dim)}
    .annow-note a{color:var(--brand-deep);font-weight:600;text-decoration:none;border-bottom:1px solid var(--brand-line)}
    @media (prefers-reduced-motion: no-preference){
      .annow.live .annow-dot{animation:annow-pulse 2.4s ease-in-out infinite}
      @keyframes annow-pulse{0%,100%{opacity:1}50%{opacity:.4}}
    }
    @media (max-width:640px){.annow{padding:12px 13px;gap:12px}.annow-n{font-size:22px}.annow-top{min-width:0}}
  `);

  const DASH = "-";                       // a dash, never a zero: nothing was received
  const GAP = 60000;                           // the refresh floor, in milliseconds
  // The timer runs a little past the floor. Fired at exactly GAP it can land a millisecond early,
  // be refused by the floor, and so skip a whole turn; one second of slack keeps every turn while
  // still never asking twice inside the floor.
  const TICK = GAP + 1000;
  const SUMMARY = "/api/analytics/summary?days=7";
  const SERIES = "/api/analytics/timeseries?metric=views&days=7";
  const APPS = "/app/apps";
  const NUM = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
  const HHMM = new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" });
  const IC = typeof ic === "function";

  const text = (v) => (typeof v === "string" && v.trim()) ? v.trim() : "";
  const object = (v) => (v && typeof v === "object" && !Array.isArray(v)) ? v : null;
  const num = (v) => (v === null || v === undefined || v === "" || !Number.isFinite(Number(v))) ? null : Number(v);
  const isoDay = (v) => { const s = String(v || "").slice(0, 10); return /^\d{4}-\d{2}-\d{2}$/.test(s) ? s : ""; };
  const pad = (n) => String(n).padStart(2, "0");
  const localDay = () => { const d = new Date(); return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); };
  /** A day as words, in the reader's own voice: "20 Nov". */
  const word = (s) => !s ? "" : new Date(Number(s.slice(0, 4)), Number(s.slice(5, 7)) - 1, Number(s.slice(8, 10)))
    .toLocaleDateString(undefined, { day: "numeric", month: "short" });
  const whyOf = (e) => String((e && e.message) || e || "").trim().replace(/\.$/, "");
  const sourceWord = (s) => s === "youtube" ? "YouTube's own numbers"
    : s === "peakcut" ? "Clipstorm's own records" : "";

  /** The overview panel, then the card inside it. The card makes its own node: the shell owns
   *  its four boxes and this file must not write into one of them. */
  function panel() { return document.querySelector('[data-an-panel="overview"]'); }
  function host() {
    const p = panel();
    if (!p) return null;
    let card = p.querySelector(".annow");
    if (!card) {
      card = document.createElement("div");
      card.className = "annow";
      const kpi = p.querySelector("#an_kpi");
      if (kpi && kpi.parentNode === p) kpi.insertAdjacentElement("afterend", card);
      else p.appendChild(card);
    }
    return card;
  }

  let held = { kind: "wait" };   // what the last answer said; kept so a redraw says something at once
  let last = 0, busy = false, seq = 0, timer = 0;

  function call(path) {
    const f = (typeof P.api === "function" ? P.api : null) || (typeof api === "function" ? api : null);
    if (!f) throw new Error("The page is still starting.");
    return f(path);
  }

  /** What arrived, in the shape the card draws. `why` is set only when a request failed. */
  function read(sum, ser, why) {
    const s = object(sum), r = object(ser);
    const source = text((s && s.source) || (r && r.source));
    const note = text((s && s.note) || (r && r.note));
    const unit = text(r && r.unit) || "views";
    const stamp = isoDay(r && r.end) || isoDay(s && s.end);
    const rows = Array.isArray(r && r.rows) ? r.rows : [];
    let best = null;                            // the newest day, whatever order the rows came in
    for (const row of rows) {
      const o = object(row); if (!o) continue;
      const day = isoDay(o.day); if (!day) continue;
      if (!best || day > best.day) best = { day, value: num(o.value) };
    }
    // "Today" is the newest day the server sent, and only while that day is today on the reader's
    // own clock. The server counts a day in its local time but stamps the window end in UTC, so
    // those two disagree by one day here; the reader's clock is the one the words "last 24 hours"
    // belong to. A newest day that is older says what the card needs instead of claiming it.
    const today = !!best && best.value !== null && best.day === localDay();
    if (today) return { kind: "num", v: best.value, unit, day: best.day, source, at: new Date() };
    if (!s && !r) return { kind: "fail", why: why || "", at: new Date() };
    return { kind: "none", why, note, day: best ? best.day : stamp, source, at: new Date() };
  }

  function paint(card, v) {
    const state = object(v) || { kind: "wait" };
    // A number kept from an earlier visit stops counting as today's the moment the day turns over,
    // so the kept answer is replaced by a sentence naming the day, not by a claim about today.
    const stale = state.kind === "num" && !!state.day && state.day !== localDay();
    const has = state.kind === "num" && Number.isFinite(state.v) && !stale;
    const unit = text(state.unit) || "views";
    // The one sentence that may only appear with a number the server sent.
    const said = has ? "Views in the last 24 hours"
      : stale ? "The day turned over, so yesterday's count is not shown as today's. This card fills in on its next check."
        : state.kind === "fail"
          ? "Today's views could not be read." + (state.why ? " " + state.why + "." : " Reload the page to try again.")
          : state.kind === "none"
            ? "The server sent no number for today, so none is shown here. This card fills in when it does."
            : "Reading today's views.";
    const when = (state.kind === "wait" || stale) ? "" : "checked " + HHMM.format(state.at || new Date());
    const meta = [sourceWord(text(state.source)), (state.day && !stale) ? "for " + word(state.day) : "", when]
      .filter(Boolean).join(", ");
    const note = (!has && state.kind === "none" && text(state.note)) ? text(state.note) : "";
    const link = note && /connect/i.test(note) ? ` <a href="${APPS}">Connected apps</a>` : "";
    const html = `<span class="annow-dot" aria-hidden="true"></span>
      <div class="annow-top">
        <div class="annow-l">Right now</div>
        <div class="annow-v"><b class="annow-n${has ? "" : " none"}">${esc(has ? NUM.format(state.v) : DASH)}</b>${
          has ? `<span class="annow-u">${esc(unit)}</span>` : ""}</div>
      </div>
      <p class="annow-s">${esc(said)}</p>
      ${meta ? `<p class="annow-m">${IC ? ic("clock") : ""}<span>${esc(meta)}</span></p>` : ""}
      ${note ? `<p class="annow-note">${esc(note)}${link}</p>` : ""}`;
    card.className = "annow" + (has ? " live" : "");
    card.setAttribute("role", "group");
    card.setAttribute("aria-label", "Right now, " + said);
    if (typeof put === "function") put(card, html); else card.innerHTML = html;
  }

  /** Draw at once from what is already known, then ask, at most once every 60 seconds. */
  async function fill() {
    const card = host();
    if (!card) { stop(); return; }
    start();
    paint(card, held);
    if (busy) return;
    const now = Date.now();
    if (last && now - last < GAP) return;
    busy = true; last = now;
    const mine = ++seq;
    let sum = null, ser = null, why = "";
    try {
      try { sum = await call(SUMMARY); } catch (e) { why = whyOf(e); }
      try { ser = await call(SERIES); } catch (e) { why = why || whyOf(e); }
      if (mine === seq) held = read(sum, ser, why);
    } finally {
      busy = false;
    }
    const now2 = host();
    if (now2 && mine === seq) paint(now2, held);
  }

  function tick() {
    if (document.hidden) return;                       // never while the tab is in the background
    const card = document.querySelector(".annow");
    if (!card || !card.isConnected) { stop(); return; } // the card left the document
    const p = card.closest("[data-an-panel]");
    if (p && p.hidden) return;                         // the Overview tab is not the one on screen
    fill();
  }
  function start() { if (!timer) timer = setInterval(tick, TICK); }
  function stop() { if (timer) { clearInterval(timer); timer = 0; } }

  // A redrawn Analytics page brings a new panel and no card. Put the card back, and drop the timer
  // as soon as the view no longer holds one.
  function watch() {
    const view = document.getElementById("view");
    if (!view || typeof MutationObserver !== "function") return;
    new MutationObserver(() => {
      if (document.querySelector(".annow")) { if (!timer) fill(); return; }
      stop();
      if (panel()) fill();
    }).observe(view, { childList: true, subtree: true });
  }

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) return;
    if (document.querySelector(".annow")) fill(); else stop();
  });
  window.addEventListener("pagehide", stop);

  P.add("analytics-realtime", { load() { fill(); } });
  fill(); watch();
})();
