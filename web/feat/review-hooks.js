/* Hook scores on the review cards: one fetch to /api/learn/hooks, one small
   pill per card that has a score for its job+clip. A clip without a score
   gets no pill: no dashes, no zeros, nothing invented. */
(() => {
  const P = window.PeakCut || (window.PeakCut = {});

  // Local esc, the same helper every sibling feature carries: the failure line
  // is escaped here and does not lean on the page's own global esc.
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  P.css("rvhook", `
    .pc-hscore{margin-left:8px;flex-shrink:0;font-variant-numeric:tabular-nums}
    #pc-rvhook-note{opacity:.75;margin-top:6px;font-size:12px}
  `);

  let cache = null;     // Map "job\0clip" -> score, filled once per page load
  let pending = null;   // the one in-flight request, shared by every redraw
  let failure = "";     // why there are no scores, when the request itself failed

  function call(path) {
    if (typeof P.api === "function") return P.api(path);
    if (typeof api === "function") return api(path);
    throw new Error("the page fetch helper is not ready yet");
  }

  /* The learn slot serves this endpoint. Accept the payload shapes a job+clip
     map can honestly take (a list of entries, or a nested map). A value that
     is null, an empty or blank string, a boolean, or anything else Number
     would coerce into a fake 0 is dropped, so the page can never show a
     score the server did not send. */
  function normalize(got) {
    const m = new Map();
    const num = v => {
      if (v == null || typeof v === "boolean") return null;
      if (typeof v === "string" && v.trim() === "") return null;
      const n = Number(v);
      return Number.isFinite(n) ? n : null;
    };
    const keep = (j, c, s) => {
      const n = num(s);
      if (n === null || j == null || c == null || j === "" || c === "") return;
      m.set(String(j) + "\u0000" + String(c), n);
    };
    if (Array.isArray(got)) {
      for (const e of got) {
        if (!e || typeof e !== "object") continue;
        const j = e.job != null ? e.job : (e.job_id != null ? e.job_id : e.jid);
        const c = e.clip != null ? e.clip : (e.clip_id != null ? e.clip_id : e.cid);
        keep(j, c, e.score != null ? e.score : e.value);
      }
    } else if (got && typeof got === "object") {
      for (const j of Object.keys(got)) {
        const v = got[j];
        if (!v || typeof v !== "object") continue;
        for (const c of Object.keys(v)) {
          const s = v[c];
          keep(j, c, s && typeof s === "object" ? (s.score != null ? s.score : s.value) : s);
        }
      }
    }
    return m;
  }

  /* Fetched once. On failure the empty cache stands for this page load, and
     the reason is kept for the one quiet line. A reload tries again. */
  function hooks() {
    if (pending) return pending;
    pending = call("/api/learn/hooks")
      .then(got => { cache = normalize(got); return cache; })
      .catch(err => { failure = String((err && err.message) || err); cache = new Map(); return cache; });
    return pending;
  }

  function pill(n) {
    const s = document.createElement("span");
    s.className = "pill pc-hscore";
    s.title = "Hook score from Clipstorm's own hook rules, not from views.";
    s.textContent = "Hook " + (Number.isInteger(n) ? String(n) : n.toFixed(1));
    return s;
  }

  function quietLine() {
    const p = document.createElement("p");
    p.className = "sub";
    p.id = "pc-rvhook-note";
    p.innerHTML = "Hook scores could not be loaded: " + esc(failure) + ".";
    return p;
  }

  /* Runs after every review redraw. Adds each missing pill at most once, so
     it stays cheap and idempotent. */
  function sync() {
    const root = document.getElementById("rvroot");
    if (!root || !root.getClientRects().length) return;
    for (const card of root.querySelectorAll(".rv-card")) {
      if (card.querySelector(".pc-hscore")) continue;
      const b = card.querySelector("[data-jid][data-cid]");
      const top = card.querySelector(".rv-top");
      if (!b || !top || !cache) continue;
      const n = cache.get(String(b.dataset.jid) + "\u0000" + String(b.dataset.cid));
      if (n == null) continue;          // no score in the data: no pill at all
      top.appendChild(pill(n));
    }
    if (failure && !document.getElementById("pc-rvhook-note")) {
      const list = root.querySelector(".rv-list");
      (list && list.parentElement ? list.parentElement : root).appendChild(quietLine());
    }
  }

  let queued = false;
  function queue() {
    if (queued) return;
    queued = true;
    setTimeout(() => {
      queued = false;
      try { sync(); } catch (err) { if (window.console) console.warn("[PeakCut] review-hooks:", err); }
    }, 0);
  }

  /* The review view has no hook name of its own in plugins.js (repaint watches
     #jobs, #ov, #cbody, #clipdlg, #sform and .topbar, never #rvroot), so this
     follows the keys.js precedent: the after hook fires when the shell
     repaints with the review title as the view opens and primes the one
     fetch, and an observer on #view re-runs sync after every review redraw. */
  function onShell() {
    if (document.getElementById("rvroot")) hooks().then(queue);
  }

  try {
    if (window.MutationObserver) {
      const view = document.getElementById("view");
      if (view) new MutationObserver(queue).observe(view, {childList: true, subtree: true});
    }
  } catch (err) { if (window.console) console.warn("[PeakCut] review-hooks observer:", err); }

  queue();
  P.add("review-hooks", { after: { drawShell: onShell } });
})();
