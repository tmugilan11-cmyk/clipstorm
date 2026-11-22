/* The full report of the learning rounds, on the Improve page.
 *
 * The card sits at the end of the Improve page as one disclosure. Opening it the first time asks
 * GET /api/learn/report once and shows the plain text the server sent, in a pre block, with every
 * character it came back as. An empty report is not hidden: the card says plainly that nothing is
 * saved yet. A request that fails costs one sentence, and the next open asks again, so a route that
 * arrives later starts working without a reload of the file.
 *
 * It owns nothing on the page: it appends one box into the Improve page root when that page is on
 * screen, and does nothing anywhere else. */
(() => {
  const P = window.PeakCut;

  P.css("learn-report", `
    .lrn .lrep{margin-top:12px}
    .lrn .lrep .lrephead{display:flex;align-items:center;justify-content:space-between;gap:10px;
      width:100%;background:none;border:0;padding:0;margin:0;color:var(--ink);font:inherit;
      font-size:15px;font-weight:600;cursor:pointer;text-align:left}
    .lrn .lrep .lrephead:focus-visible{outline:2px solid var(--brand);outline-offset:3px;border-radius:6px}
    .lrn .lrep .chev{flex:none;width:0;height:0;border-left:5px solid transparent;
      border-right:5px solid transparent;border-top:6px solid var(--dim);transition:transform .15s ease}
    .lrn .lrep.open .chev{transform:rotate(180deg)}
    .lrn .lrep .lrepbody.off{display:none}
    .lrn .lrep .lreptext{margin:10px 0 0;padding:10px 12px;background:var(--panel2);
      border:1px solid var(--line);border-radius:10px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
      font-size:12.5px;line-height:1.55;color:var(--ink);white-space:pre-wrap;word-break:break-word;
      max-height:320px;overflow:auto}
    .lrn .lrep .lrepnote{margin:10px 0 0;font-size:13px;line-height:1.55;color:var(--dim)}
  `);

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // One line each, said only when true. No report and a failed read are different things and the
  // card keeps them apart, because "not saved yet" and "could not be read" ask for different next steps.
  const EMPTY_NOTE = "No report is saved yet. Run a learning round and its report will be written here.";
  const SHAPE_NOTE = "The report arrived without plain text this card can show.";
  const FAILED = "The report could not be read just now.";

  const REP = { shown: false, busy: false, loaded: false, err: "", text: null, drew: null };

  /** One sentence for a thrown request, folding the server's short words into it.
   *
   * A bare status phrase like "Not Found" alone leaves out what failed, so a short phrase is put in
   * brackets after the fallback, and a longer one is used as it stands. The card stays one sentence. */
  const one = (e, fallback) => {
    const said = String((e && e.message) || e || "").replace(/\s+/g, " ").trim();
    if (!said) return fallback;
    if (said.split(" ").length <= 5) {
      const stem = fallback.replace(/[.!?]+$/, "");
      return `${stem} (${said.replace(/[.!?]+$/, "")}).`;
    }
    return /[.!?]$/.test(said) ? said : `${said}.`;
  };

  /** The report as plain text, or null when the answer carries no text at all.
   *
   * Three outcomes, kept apart on purpose: a non-empty string is the report, an empty string is a
   * report that says nothing yet, and null means the answer had no text field this card reads. A
   * missing body, a bare value, and an object with no text key are all null too, so the card never
   * claims the report is empty when the shape simply did not match. The
   * keys are the names a report route would plausibly use; a join of an all-string list is still the
   * server's own words, only stacked. Nothing here is written by this card. */
  function textOf(payload) {
    if (typeof payload === "string") return payload.trim();
    if (Array.isArray(payload)) {
      return payload.every((x) => typeof x === "string") ? payload.join("\n").trim() : null;
    }
    const body = payload && typeof payload === "object" ? payload : null;
    if (!body) return null;
    const KEYS = ["report", "text", "body", "content", "saying", "said"];
    for (const k of KEYS) {
      const v = body[k];
      if (typeof v === "string") return v.trim();
      if (Array.isArray(v) && v.length && v.every((x) => typeof x === "string")) {
        return v.join("\n").trim();
      }
    }
    // No text key anywhere in the object, even an empty one: the shape did not match.
    return null;
  }

  /** The inside of the card body, from the two constants above or the server's own words. */
  function inner() {
    if (REP.busy && REP.text === null && !REP.err) {
      return `<p class="lrepnote">Reading the report.</p>`;
    }
    if (REP.err) return `<p class="lrepnote">${esc(REP.err)}</p>`;
    if (REP.text === null) return `<p class="lrepnote">${esc(SHAPE_NOTE)}</p>`;
    if (!REP.text) return `<p class="lrepnote">${esc(EMPTY_NOTE)}</p>`;
    return `<pre class="lreptext">${esc(REP.text)}</pre>`;
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

  /** Draws the card at the end of the Improve page. Does nothing anywhere else. */
  function paint(scope) {
    const lrn = lrnOf(scope);
    if (!lrn) return;
    let host = lrn.querySelector(".lrep");
    if (!host) {
      host = document.createElement("div");
      host.className = "box lrep";
      lrn.appendChild(host);
    }
    if (!host.querySelector(".lrephead")) {
      // Fixed markup only: the words are this file's own, so nothing here needs the server escaped.
      host.innerHTML = `
        <button type="button" class="lrephead" data-act="lrepopen" aria-expanded="false">
          The full report
          <span class="chev" aria-hidden="true"></span>
        </button>
        <div class="lrepbody off"></div>`;
      REP.drew = null;
    }
    const head = host.querySelector(".lrephead");
    const bodyEl = host.querySelector(".lrepbody");
    if (head) head.setAttribute("aria-expanded", REP.shown ? "true" : "false");
    if (bodyEl) {
      const got = inner();
      if (got !== REP.drew) {
        REP.drew = got;
        bodyEl.innerHTML = got;
      }
      bodyEl.classList.toggle("off", !REP.shown);
    }
    host.classList.toggle("open", REP.shown);
  }

  /** Asks the route once. A failure becomes one line in the card and the next open asks again. */
  async function ensure() {
    REP.busy = true;
    REP.err = "";
    REP.text = null;
    paint(document);
    try {
      const got = await P.api("/api/learn/report");
      REP.text = textOf(got);
      REP.loaded = true;
      REP.err = "";
    } catch (e) {
      REP.loaded = false;
      REP.err = one(e, FAILED);
    } finally {
      REP.busy = false;
      paint(document);
    }
  }

  /** Mounts the card when the Improve page is on screen and returns quietly when it is not. */
  function mount(scope) {
    const lrn = lrnOf(scope);
    if (!lrn) return;
    paint(lrn);
  }

  // The page redraws itself when a round runs, which throws the card away. Watching the view puts it
  // back without a timer and without touching any other page.
  try {
    const view = document.getElementById("view");
    if (view && typeof MutationObserver === "function") {
      new MutationObserver(() => {
        try {
          if (view.querySelector(".lrn") && !view.querySelector(".lrep")) mount(view);
        } catch { /* the next draw tries again; the page keeps working */ }
      }).observe(view, { childList: true, subtree: true });
    }
  } catch { /* no observer: the card still mounts on the next visit */ }

  window.PeakCut.add("learn-report", {
    act: {
      /** [data-act="lrepopen"] on the card header. First open reads the report, once. */
      lrepopen() {
        REP.shown = !REP.shown;
        if (REP.shown && !REP.loaded && !REP.busy) ensure();
        else paint(document);
      },
    },
    after: {
      /** Appends the report card to the Improve page when that page is up. Rewrites nothing else. */
      drawSettings(scope) {
        try { mount(scope); } catch { /* fail soft: a card that cannot draw never breaks the page */ }
      },
    },
  });
})();
