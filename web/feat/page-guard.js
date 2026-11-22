// Two quiet guards. Both fail soft, and neither runs while the page sits still.
//
// 1. An /app address that no built-in view and no page owns used to settle on the home
//    page without a word, so the address bar and the screen disagreed. Now it says one
//    line, where the person is already looking, and offers the way home.
// 2. Two files that register the same page name lost the first one in silence. Now that
//    costs a single console warning per name, never one per frame.
(() => {
  const P = window.PeakCut;
  if (!P || !P.add) return;

  // The views the frame draws itself. A creator view is "c:<id>". A page a feature file
  // registered answers through hasPage.
  const BUILT_IN = ["overview", "library", "settings", "usage", "review"];
  const owns = (v) => !v || v.indexOf("c:") === 0 || BUILT_IN.indexOf(v) >= 0 || !!(P.hasPage && P.hasPage(v));

  P.css("page-guard", ".pg-note{padding:22px 2px 0;font-size:14px;color:var(--dim)}.pg-note a{color:var(--brand-deep);font-weight:600;text-decoration:none}.pg-note a:hover{color:var(--text)}");

  // The address the bar is showing, when it points at nothing. Trailing slashes and the
  // clean /app and /app/videos forms are not news. If the frame has not loaded its files
  // yet, every page address looks unknown, so stay quiet until it has.
  function stray() {
    if (!P._booted || typeof pathKnown !== "function") return "";
    const path = location.pathname.replace(/\/$/, "");
    if (path !== "/app" && path.indexOf("/app/") !== 0) return "";
    if (pathKnown(path)) return "";
    return path;
  }

  // One line into #view. The sentence is ours, so it goes in as text, not as markup. The
  // way home is a plain address with no data-act: the frame cancels the default for every
  // anchor that carries one, and this link has to work when routing is the broken part.
  // A moving picture is never talked over.
  function say(view, text, key) {
    if (view.querySelector("iframe, video")) return;
    const had = view.querySelector(".pg-note");
    if (had && had.dataset.pgKey === key) return;   // already on screen, do not touch it
    if (had) had.remove();
    const note = document.createElement("div");
    note.className = "pg-note";
    note.dataset.pgKey = key;
    const home = document.createElement("a");
    home.href = "/app";
    home.textContent = "Go home";
    note.append(text + " ", home);
    view.prepend(note);
  }

  function guard() {
    const view = document.getElementById("view");
    if (!view) return;
    const addr = stray();
    if (addr) return say(view, "There is no page at that address.", "addr:" + addr);
    // The view can also name something nothing owns, for example a page file that failed
    // to load. Say so, and take the line back the moment something claims the view.
    const v = P.state ? P.state().view : "";
    if (!owns(v)) return say(view, "That page is not here.", "view:" + v);
    const old = view.querySelector(".pg-note");
    if (old) old.remove();
  }

  // The shell hook alone is not enough: it runs when the frame redraws, and changing view
  // leaves the frame exactly as it was. So also watch the view itself, which every view
  // change rewrites. That is event driven: nothing runs while the page sits still.
  const view = document.getElementById("view");
  if (view && window.MutationObserver) new MutationObserver(guard).observe(view, { childList: true });
  addEventListener("popstate", guard);

  // ---- the page name two files want --------------------------------------
  // The loader keeps the last registration and drops the others. Warn once, then shut up.
  const told = new Set();
  function taken(name) {
    if (!name || told.has(name)) return;
    if (!(P._pages || []).some((p) => p && p.name === name)) return;
    told.add(name);
    console.warn('Two files registered the page "' + name + '". The last one is kept and the other one is lost.');
  }
  // A page file may call this with the name it is about to take. If that name is already
  // registered, it says so at once, which is the only way to catch a duplicate after the
  // fact. Either way it answers with the names already taken.
  P.pageGuard = (name) => { taken(name); return (P._pages || []).map((p) => p.name); };
  const register = P.page;
  if (typeof register === "function") P.page = (name, def) => { taken(name); return register(name, def); };

  P.add("page-guard", { after: { drawShell() { guard(); } } });
})();
