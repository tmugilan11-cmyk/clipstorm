/* One way of showing a failure.
 *
 * Until now every feature that hit a bad answer handled it its own way: a toast here,
 * a silent return there, and a bare "Something went wrong" when the server sent no
 * detail. This file gives all of them the same small line: one plain sentence that says
 * what failed and what to do next, plus a Retry button that runs the same call again.
 *
 * Another file uses it in one line, without any other change:
 *   P.fail.show(box, err, { what: "The clip list", retry: () => load() });
 *   P.fail.guard(load(), { what: "The clip list", host: "#jobs", retry: () => load() });
 */
(() => {
  const P = (window.PeakCut = window.PeakCut || {});

  /* ---- text helpers ----------------------------------------------------- */
  // The page already has esc(); the fallback only exists so this file cannot throw
  // on its own if it is ever loaded somewhere else.
  const escHtml = (s) => {
    if (typeof esc === "function") return esc(s);
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  };

  function text(err) {
    try {
      const s = String((err && err.message) || err || "").trim();
      return s === "[object Object]" ? "" : s;
    } catch (err) { note("reading the error text", err); return ""; }
  }

  function status(err) {
    const n = Number(err && (err.status || err.statusCode));
    return Number.isFinite(n) ? n : 0;
  }

  /* ---- plain words ------------------------------------------------------ */
  // The page's own fetch wrapper falls back to "Something went wrong" when a server
  // sends a bare status. That sentence tells nobody anything, so it is replaced here.
  const VAGUE = /^(?:something went wrong\.?|error\.?|failed\.?|undefined|null)?$/i;

  /** One plain sentence. `what` names the thing that failed, in the caller's words. */
  function say(err, what) {
    const w = String(what || "").trim().replace(/[.\s]+$/, "");
    const said = text(err);
    const low = said.toLowerCase();
    const code = status(err);

    if (typeof navigator === "object" && navigator && navigator.onLine === false) {
      return "You are offline. Check the connection, then retry.";
    }
    if (code === 401 || /please sign in|unauthori[sz]ed/i.test(said)) {
      return "Your session ended. Sign in again, then retry.";
    }
    if (/abort|cancel/i.test(low) || (err && err.name === "AbortError")) {
      return (w || "That request") + " was stopped before it answered. Retry when you are ready.";
    }
    if (/timed? ?out/i.test(low)) {
      return (w || "The server") + " took too long to answer. Retry in a moment.";
    }
    if (/failed to fetch|networkerror|load failed|network request failed/i.test(low)) {
      return "The app could not reach the server. Check the connection, then retry.";
    }
    if (code === 404) {
      return (w || "That item") + " is no longer on the server. Refresh the page to see what is left.";
    }
    if (code >= 500) {
      return (w || "The server") + " had a problem on its side. Retry in a moment.";
    }
    // Some servers answer with the bare status text and nothing else. Those are not
    // sentences, so they are turned into one before they reach a person.
    const plain = {
      "not found": (w || "That item") + " is no longer on the server. Refresh the page to see what is left.",
      "bad request": "The server could not accept that. Check the values, then retry.",
      "forbidden": "This account is not allowed to do that. Sign in with another one.",
      "internal server error": (w || "The server") + " had a problem on its side. Retry in a moment.",
      "service unavailable": (w || "The server") + " is busy right now. Retry in a moment.",
      "bad gateway": (w || "The server") + " did not answer properly. Retry in a moment.",
    };
    if (said && plain[low]) return plain[low];

    if (said && !VAGUE.test(said)) {
      // The server's own sentence is already the clearest reason, so it leads.
      const reason = said.replace(/\s+/g, " ").replace(/[.\s]+$/, "");
      return (w ? w + ": " : "") + reason + ".";
    }
    return w
      ? "There was a problem with " + w.toLowerCase() + ". Retry, and if it fails again reload the page."
      : "That step did not finish. Retry, and if it fails again reload the page.";
  }

  /* ---- a short memory of what failed ------------------------------------ */
  // Even where the right thing is to carry on, the failure is written down instead of
  // dropped. The list stays at twenty, and the page never shows it: it is there so a
  // later reader can see what has been failing rather than guess.
  const seen = [];
  function note(where, err) {
    try {
      seen.push({ at: new Date().toISOString(), where: String(where || ""), why: say(err, "") });
      if (seen.length > 20) seen.shift();
    } catch { seen.push({ where: String(where || ""), why: "note failed" }); }
    return seen[seen.length - 1];
  }

  /* ---- the retry slots -------------------------------------------------- */
  // A data-act button cannot carry a function, so each retry waits in a small map
  // and the button carries its key. Only the newest forty are kept.
  const slots = new Map();
  let seq = 0;

  function remember(fn) {
    if (typeof fn !== "function") return "";
    const id = "r" + (++seq);
    slots.set(id, fn);
    if (slots.size > 40) {
      const oldest = slots.keys().next();
      if (!oldest.done) slots.delete(oldest.value);
    }
    return id;
  }

  /* ---- the line --------------------------------------------------------- */
  // A string selector, an element, or {host}. Anything else falls back to a toast
  // rather than a throw, because showing a failure must never be a failure.
  function hostOf(h) {
    if (!h) return null;
    if (h.nodeType === 1) return h;
    if (h.host) return hostOf(h.host);
    if (typeof h === "string") { try { return document.querySelector(h); } catch (err) { note("finding the box " + h, err); return null; } }
    return null;
  }

  /** Draws the line at the top of a container. Returns the element, or null. */
  function show(host, err, opt) {
    const o = opt || {};
    const box = hostOf(host) || hostOf(o.host);
    const why = say(err, o.what);
    if (!box) {
      try { if (typeof P.toast === "function") P.toast(why, "bad"); } catch (err) { note("the toast for " + why, err); }
      return null;
    }

    const id = typeof o.retry === "function" ? remember(o.retry) : "";
    let line = null;
    try { line = box.querySelector(":scope > .pcerr"); } catch (err) { note("scoping the error line", err); line = box.querySelector(".pcerr"); }
    if (!line) {
      line = document.createElement("p");
      line.className = "pcerr";
      box.insertBefore(line, box.firstChild);
    }
    line.setAttribute("role", "alert");

    const btn = id
      ? `<button type="button" class="pcerr-btn" data-act="pcretry" data-r="${escHtml(id)}">Retry</button>`
      : "";
    line.innerHTML = `<span class="pcerr-why">${escHtml(why)}</span>${btn}`;
    return line;
  }

  function clear(host) {
    const box = hostOf(host);
    if (!box) return;
    const line = box.querySelector(".pcerr");
    if (line) line.remove();
  }

  /** Promise form: shows the line and never rethrows. Resolves to null on failure. */
  function guard(promise, opt) {
    const o = opt || {};
    return Promise.resolve(promise).catch((err) => {
      try { show(o.container || o.host, err, o); } catch (drawErr) { note("drawing the line for " + say(err, o.what), drawErr); }
      return null;
    });
  }

  /* ---- an error that already knows its own words ------------------------ */
  // Features that call PeakCut.api or PeakCut.send get this for free: the thrown error
  // carries the plain sentence and the exact call that produced it, so any existing
  // `catch (err) { ... err.message ... }` now reads properly, and P.fail.show can retry.
  function mark(err, rerun, what) {
    const e = err && typeof err === "object" ? err : new Error(String(err || ""));
    if (e.__pcfail) return e;
    try {
      e.__pcfail = true;
      if (what) e.pcwhat = what;
      if (typeof rerun === "function") e.pcretry = rerun;
      e.pcsay = say(e, what);
      if (!text(e)) e.message = e.pcsay;
    } catch (markErr) { note("marking a read-only error", markErr); }
    return e;
  }

  function wrap(name) {
    const orig = P[name];
    if (typeof orig !== "function" || orig.__pcfail) return;
    const wrapped = function (...args) {
      const rerun = () => P[name](...args);
      let out;
      try { out = orig.apply(P, args); }
      catch (err) { throw mark(err, rerun); }
      return Promise.resolve(out).catch((err) => { throw mark(err, rerun); });
    };
    wrapped.__pcfail = true;
    P[name] = wrapped;
  }

  /* ---- a failure nobody caught ----------------------------------------- */
  // Some features hand a promise to nobody, and a throw inside a paint hook is
  // swallowed by the loader. Those used to vanish into a blank area. One fixed line at
  // the foot of the window speaks them, so a silent feature becomes a visible one.
  let spot = null;
  function dock() {
    if (spot && spot.isConnected) return spot;
    spot = document.getElementById("pcerr-dock");
    if (!spot) {
      spot = document.createElement("div");
      spot.id = "pcerr-dock";
      spot.setAttribute("aria-live", "polite");
      spot.style.cssText = "position:fixed;left:16px;right:16px;bottom:16px;z-index:60;" +
        "display:flex;justify-content:center;pointer-events:none;max-width:640px;margin:0 auto";
      document.body.append(spot);
    }
    return spot;
  }

  function announce(err) {
    try {
      const box = dock();
      if (!box || box.querySelector(".pcerr")) return;      // one line at a time
      const line = document.createElement("p");
      line.className = "pcerr";
      line.setAttribute("role", "alert");
      line.style.pointerEvents = "auto";
      line.style.margin = "0";
      line.style.width = "100%";
      line.innerHTML = `<span class="pcerr-why">${escHtml(say(err, ""))}</span>`;
      const close = document.createElement("button");
      close.type = "button";
      close.className = "pcerr-btn";
      close.textContent = "Dismiss";
      close.addEventListener("click", () => line.remove());
      line.append(close);
      box.append(line);
    } catch (drawErr) { note("drawing the dock line", drawErr); }
  }

  let watching = false;
  function watch() {
    if (watching) return;
    watching = true;
    try {
      window.addEventListener("unhandledrejection", (e) => {
        const r = e && e.reason;
        if (r && r.__pcfail) return;      // already handled by whoever caught it
        announce(r);
      });
      window.addEventListener("error", (e) => {
        if (e && e.message) announce(e.error || new Error(e.message));
      });
    } catch (listenErr) { note("listening for page errors", listenErr); }
  }

  function install() {
    wrap("api");
    wrap("send");
    watch();
  }

  // Measured, not guessed: the old hover put white on the light red --bad (#F87171), which is 2.77:1 and
  // fails the 4.5 minimum for 12px text. Hovering now darkens the ground to the app's own deep red #C53030
  // (also used by the account menu), where white reads at 5.47:1. The base state, --bad on --bad-soft,
  // is 6.25:1 and does not move.
  P.css("polish-errors", `
    .pcerr{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:10px 0;padding:8px 10px;
      border:1px solid var(--bad);border-left-width:3px;border-radius:8px;background:var(--bad-soft);
      color:var(--text);font-size:13px;line-height:1.45;text-align:left}
    .pcerr .pcerr-why{flex:1 1 220px;min-width:0;text-wrap:pretty}
    .pcerr .pcerr-btn{flex:none;border:1px solid var(--bad);background:transparent;color:var(--bad);
      font:inherit;font-size:12px;font-weight:600;padding:5px 12px;border-radius:6px;cursor:pointer;
      transition:background-color .15s ease,color .15s ease}
    .pcerr .pcerr-btn:hover{background:#C53030;color:#fff}
    .pcerr .pcerr-btn:disabled{opacity:.55;cursor:default}
    @media (max-width:640px){.pcerr .pcerr-btn{min-height:44px;min-width:44px;padding:8px 14px}}
    @media (prefers-reduced-motion:reduce){.pcerr .pcerr-btn{transition:none}}
  `);

  P.fail = { say, show, clear, guard, mark, install, announce, note, seen, words: say };

  // plugins.js builds PeakCut.api/send inside boot(), which runs after every feature
  // file has loaded. Wrapping boot lets those two be caught the moment they exist.
  const boot0 = P.boot;
  if (typeof boot0 === "function") {
    P.boot = function () {
      let out;
      try { out = boot0.apply(P, arguments); }
      finally { try { install(); } catch (bootErr) { note("wrapping PeakCut api", bootErr); } }
      return out;
    };
  } else if (P._booted) {
    install();
  }

  window.PeakCut.add("polish-errors", {
    act: {
      /** data-act="pcretry" data-r="<slot>": runs the failed call again, in place. */
      async pcretry(el) {
        const id = el && el.dataset ? el.dataset.r : "";
        const run = slots.get(id);
        const line = el.closest(".pcerr");
        if (!run) { if (line) line.remove(); return; }
        const label = el.textContent;
        el.disabled = true;
        el.textContent = "Retrying";
        try {
          await run();
          slots.delete(id);
          if (line) line.remove();
        } catch (err) {
          const why = say(err, "");
          if (line) {
            const whyEl = line.querySelector(".pcerr-why");
            if (whyEl) whyEl.textContent = why;
          } else {
            try { if (typeof P.toast === "function") P.toast(why, "bad"); } catch (tErr) { note("the retry toast", tErr); }
          }
        } finally {
          if (el && el.isConnected) {
            el.disabled = false;
            if (el.textContent === "Retrying") el.textContent = label;
          }
        }
      },
    },
  });
})();
