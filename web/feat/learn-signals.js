/* What the retention curve says about the hook and the length, drawn on the Improve page.
 *
 * Reads GET /api/learn/signals?days=N, which the wave 3 route answers with kept points and a sentence
 * about the hook and one about the length. Nothing here makes up a point or a claim: with no points the
 * card says what would put something there, and when the request fails it says one short line and stops. */
(() => {
  const P = window.PeakCut;

  P.css("learn-signals", `
    .lrn .lsig .spark{display:block;width:100%;height:64px;margin:2px 0 12px}
    .lrn .lsig .spark polyline{fill:none;stroke:var(--brand);stroke-width:1.8;stroke-linejoin:round;stroke-linecap:round}
    .lrn .lsig .spark circle{fill:var(--brand);stroke:none}
    .lrn .lsig .spark line{stroke:var(--line);stroke-width:1}
    .lrn .lsig .say{margin:0 0 6px}
    .lrn .lsig .say:last-child{margin:0}
    .lrn .lsig .say b{color:var(--ink);font-weight:600}
  `);

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // The one line this card shows when the server has no curve and sent no sentence of its own.
  // It says what would put something there, and claims nothing about the numbers.
  const EMPTY = (days) => `A curve appears here once a clip from the last ${days} days has watching numbers.`;
  const FAILED = "The retention curve could not be read just now.";

  const SIG = { days: 0, data: null, err: "", busy: false };

  /** The first value that is a real number, or null. The route may name one field more than one way. */
  function num(...vals) {
    for (const v of vals) {
      if (v === null || v === undefined || v === "") continue;
      const n = Number(v);
      if (Number.isFinite(n)) return n;
    }
    return null;
  }

  /** The kept points the server sent, cleaned into {at, kept} with kept between 0 and 1. Never throws. */
  function pointsOf(payload) {
    const body = payload && typeof payload === "object" ? payload : {};
    // `points` may be a count rather than the curve itself, so the first ARRAY wins, not the first
    // truthy value. A number here used to hide a perfectly good curve under another name.
    const raw = [body.points, body.curve, body.series, body.retention].find(Array.isArray);
    if (!raw || !raw.length) return [];
    const out = [];
    for (let i = 0; i < raw.length; i++) {
      const p = raw[i];
      if (!p || typeof p !== "object") continue;
      const kept = num(p.kept, p.y, p.value, p.share, p.pct, p.retention_pct);
      if (kept === null) continue;
      out.push({ at: num(p.at, p.t, p.second, p.seconds, p.x, p.time), kept, i });
    }
    if (!out.length) return [];
    // A curve is read along the clip, so keep the server's order when it gave a time for every point.
    if (out.every((p) => p.at !== null)) out.sort((a, b) => a.at - b.at);
    // Kept may arrive as a fraction or as a percentage. The shape is the same either way, so the
    // largest value picks the scale rather than six guesses in a row.
    const top = Math.max(...out.map((p) => p.kept));
    const scale = top > 1.0001 ? 100 : 1;
    return out.map((p) => ({ at: p.at, i: p.i, kept: Math.max(0, Math.min(1, p.kept / scale)) }));
  }

  /** One sentence field, if the server actually sent one. An absent sentence stays absent. */
  function sentence(payload, keys) {
    const body = payload && typeof payload === "object" ? payload : {};
    for (const k of keys) {
      const v = body[k];
      if (typeof v === "string" && v.trim()) return v.trim();
    }
    return "";
  }

  /** The plain SVG sparkline: one polyline of kept over at, in a viewBox that stretches to the card. */
  function spark(pts, days) {
    const W = 100, H = 36, PAD = 3;
    const xs = pts.map((p, i) => (p.at === null ? i : p.at));
    const x0 = Math.min(...xs), x1 = Math.max(...xs);
    const span = (x1 - x0) || 1;
    const pos = pts.map((p, i) => ({
      x: pts.length === 1 ? W / 2 : ((xs[i] - x0) / span) * W,
      y: PAD + (1 - p.kept) * (H - PAD * 2),
    }));
    const line = pts.length > 1
      ? `<polyline vector-effect="non-scaling-stroke" points="${pos
          .map((q) => q.x.toFixed(2) + "," + q.y.toFixed(2)).join(" ")}"></polyline>`
      : `<circle cx="${W / 2}" cy="${pos[0].y.toFixed(2)}" r="1.8"></circle>`;
    const label = "Kept watching across the clip, " + pts.length + " points, last " + days + " days.";
    return `<svg class="spark" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img"
        aria-label="${esc(label)}">
        <line x1="0" y1="${H - PAD}" x2="${W}" y2="${H - PAD}" vector-effect="non-scaling-stroke"></line>
        ${line}
      </svg>`;
  }

  /** The inside of the card. Every sentence comes from the server or from the two constants above. */
  function inner() {
    const days = SIG.days || 28;
    const head = `<h3>Where people stop watching</h3>`;
    if (SIG.busy && !SIG.data && !SIG.err) {
      return `${head}<p class="sub">Reading the curve for the last ${esc(days)} days.</p>`;
    }
    if (SIG.err) return `${head}<p class="err">${esc(SIG.err)}</p>`;
    const pts = pointsOf(SIG.data);
    if (!pts.length) {
      // One sentence and nothing else: the brief asks for exactly one, and an empty box that also
      // repeats the range above it reads like two apologies for the same thing.
      const said = sentence(SIG.data, ["empty", "note", "missing", "why_not"]) || EMPTY(days);
      return `${head}<p class="empty">${esc(said)}</p>`;
    }
    // The server may send the sentences on their own keys, or as a list in reading order. A list is
    // shown unlabelled, because guessing which line is the hook would put a label on the wrong sentence.
    let hook = sentence(SIG.data, ["hook", "hook_sentence", "hook_line"]);
    let len = sentence(SIG.data, ["length", "length_sentence", "length_line"]);
    let rest = [];
    if (!hook && !len) {
      const lines = (SIG.data && Array.isArray(SIG.data.lines)) ? SIG.data.lines : [];
      rest = lines.filter((s) => typeof s === "string" && s.trim()).map((s) => s.trim());
    }
    return `${head}
      <p class="sub">Kept watching over the clip, last ${esc(days)} days.</p>
      ${spark(pts, days)}
      ${hook ? `<p class="say"><b>Hook:</b> ${esc(hook)}</p>` : ""}
      ${len ? `<p class="say"><b>Length:</b> ${esc(len)}</p>` : ""}
      ${rest.map((s) => `<p class="say">${esc(s)}</p>`).join("")}`;
  }

  /** The Improve page's own container, or null when some other page is on screen. */
  function lrnOf(scope) {
    try {
      const from = scope && scope.querySelector ? scope : document;
      return from.querySelector(".lrn") || document.querySelector(".lrn");
    } catch {
      return null;
    }
  }

  /** The range the page itself is set to, so this card reads the same days the rest of the page does. */
  function daysOf(lrn) {
    const sel = lrn && lrn.querySelector("#lrn_days");
    return Number(sel && sel.value) || 28;
  }

  /** Draws the card inside the Improve page. Does nothing anywhere else. */
  function paint(scope) {
    const lrn = lrnOf(scope);
    if (!lrn) return;
    let host = lrn.querySelector(".lsig");
    if (!host) {
      host = document.createElement("div");
      host.className = "box lsig";
      // Under the run box, above the facts and the rounds, which is where the curve belongs.
      const first = lrn.querySelector(".box");
      if (first) first.insertAdjacentElement("afterend", host);
      else lrn.appendChild(host);
    }
    host.innerHTML = inner();
  }

  /** Asks the route for one range. A failure becomes one short line in the card, never a thrown error. */
  async function ensure(days) {
    SIG.busy = true;
    paint(document);
    try {
      const got = await P.api("/api/learn/signals?days=" + encodeURIComponent(days));
      SIG.data = (got && typeof got === "object" && got.signals) ? got.signals : (got || null);
      SIG.err = "";
    } catch {
      SIG.data = null;
      SIG.err = FAILED;
    } finally {
      SIG.busy = false;
      paint(document);
    }
  }

  /**
   * Runs on every draw that may have produced the Improve page. Mounts the card when the page is on
   * screen and returns quietly when it is not, the same way heard.js skips a missing job card.
   */
  function mount(scope) {
    const lrn = lrnOf(scope);
    if (!lrn) return;
    const days = daysOf(lrn);
    paint(lrn);
    if (SIG.busy || SIG.days === days) return;
    SIG.days = days;
    SIG.data = null;
    SIG.err = "";
    paint(lrn);
    ensure(days);
  }

  // The page redraws itself when a round starts or a range changes, which throws the card away.
  // Watching the view puts it back without a timer and without touching any other page.
  try {
    const view = document.getElementById("view");
    if (view && typeof MutationObserver === "function") {
      new MutationObserver(() => {
        try {
          if (view.querySelector(".lrn") && !view.querySelector(".lsig")) mount(view);
        } catch { /* the next draw tries again; the page keeps working */ }
      }).observe(view, { childList: true, subtree: true });
    }
  } catch { /* no observer: the page still draws the card on the next visit */ }

  // The range select is the page's own control. Changing it changes what this card asks for.
  document.addEventListener("change", (e) => {
    const t = e.target;
    if (!t || t.id !== "lrn_days") return;
    const days = Number(t.value) || 28;
    if (days === SIG.days) return;
    SIG.days = days;
    SIG.data = null;
    SIG.err = "";
    paint(document);
    if (!SIG.busy) ensure(days);
  });

  window.PeakCut.add("learn-signals", {
    after: {
      /** Rewrites nothing: it only appends the curve card to the Improve page when that page is up. */
      drawSettings(scope) {
        try { mount(scope); } catch { /* fail soft: a card that cannot draw never breaks the page */ }
      },
    },
  });
})();
