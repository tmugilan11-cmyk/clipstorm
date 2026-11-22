/* ============================================================ UI plug-ins
 *
 * One small loader so separate features live in their own files instead of all
 * being edited inside one 7,000-line script. A feature file exports a plain
 * object on `window.PeakCut`, one key per feature, and everything here hooks it
 * into the page that already exists:
 *
 *   PeakCut.filters = {
 *     label: "Filters",                    // shown in the debug list
 *     tools: () => ({ ... }),              // markup for Settings > Tools, optional
 *     load:  async () => {},               // called when that Tools tab opens
 *     act:   { name: (el) => ... },        // extra [data-act] handlers
 *     after: { drawJobs: (html) => ... },  // rewrite markup other drawers produced
 *   };
 *
 * Why this exists: eighteen agents each editing `index.html` overwrite each
 * other. Each one now owns a file, and this file is the only thing that has to
 * know about all of them. Adding a feature never means touching index.html.
 */
(() => {
  const P = (window.PeakCut = window.PeakCut || {});
  P._order = P._order || [];

  /* ---- adding a feature ------------------------------------------------- */
  P.add = (name, def) => {
    if (!name || !def) return;
    if (P[name]) Object.assign(P[name], def); else { P[name] = def; P._order.push(name); }
    if (P._booted) P._wire(name);        // late registration still works
  };

  /* ---- styles --------------------------------------------------------- */
  // A feature brings its own CSS as a string; this puts it in the page once.
  const styleCache = new Set();
  P.css = (id, text) => {
    if (!id || styleCache.has(id) || document.getElementById("pcss_" + id)) return;
    styleCache.add(id);
    const s = document.createElement("style");
    s.id = "pcss_" + id;
    s.textContent = text;
    document.head.append(s);
  };

  /* ---- pages and nav items --------------------------------------------- */
  // A feature can put a whole page in the main menu without touching index.html.
  //   PeakCut.page("analytics", {
  //     nav:    "Analytics",              // the words in the menu
  //     icon:   "chart",                  // a name from index.html's icon map
  //     tip:    "What your clips did",    // the hover text
  //     path:   "analytics",              // the address: /app/analytics
  //     group:  "",                       // "" for the top group, or a heading name
  //     badge:  () => 3,                  // optional number beside the words
  //     order:  10,                       // where in the group it sits
  //     view:   () => "<div>…</div>",     // the markup, drawn fresh on each visit
  //     load:   async () => {},           // called after the markup is in the page
  //     tab:    "",                       // optional sub-tab inside the page
  //   });
  P._pages = P._pages || [];
  P.page = (name, def) => {
    if (!name || !def) return;
    P._pages = P._pages.filter(p => p.name !== name);
    P._pages.push({ name, ...def });
    P._pages.sort((a, b) => (a.order || 50) - (b.order || 50));
    if (P._booted && typeof drawShell === "function") { try { drawShell(); } catch {} }
  };  P.hasPage = (v) => P._pages.some(p => p.name === v);
  P.pageFor = (path) => {
    const clean = String(path || "").replace(/\/$/, "");
    const p = P._pages.find(x => x.path && clean === "/app/" + x.path);
    return p ? p.name : null;
  };
  P.pagePath = (name) => { const p = P._pages.find(x => x.name === name); return p && p.path ? "/app/" + p.path : null; };

  // The menu is drawn by index.html's own drawShell; these two helpers give it the
  // extra rows a feature asked for, grouped the same way the built-in rows are.
  // Rows are gathered by group first, then ordered inside it: two files in the same group are often written
  // weeks apart and never share an order number, and sorting by order alone split one heading into two.
  P.navHtml = () => {
    const icons = typeof I === "object" && I ? I : {};
    const draw = (n) => (typeof ic === "function" && icons[n] ? ic(n) : "");
    const rows = [];
    const groups = [];
    // Settings keeps some tabs for an owner account only (Storage, AI). A page can say `admin: true` to
    // match, and the drawer then skips that row for everyone else: the page would only land on the
    // "Owner only" card, which is a dead end. Same key path Settings itself checks.
    const amOwner = typeof S === "object" && S && S.status && S.status.user && S.status.user.is_admin;
    for (const p of P._pages) {
      // A page can ask to stay out of the menu. It is still a page: `hidden: true` keeps it reachable by
      // address and by a button, which is what the audio editor wants -- it is only ever opened from the
      // "Edit audio" button inside a clip, never as a menu row of its own.
      if (p.hidden) continue;
      if (p.admin && !amOwner) continue;
      const g = p.group || "";
      let seen = groups.find(x => x.name === g);
      if (!seen) { seen = { name: g, order: p.order || 50, list: [] }; groups.push(seen); }
      seen.order = Math.min(seen.order, p.order || 50);
      seen.list.push(p);
    }
    groups.sort((a, b) => a.order - b.order);
    for (const g of groups) {
      if (g.name) rows.push(`<h4><span>${typeof esc === "function" ? esc(g.name) : g.name}</span></h4>`);
      for (const p of g.list) {
        let badge = "";
        try {
          const n = typeof p.badge === "function" ? p.badge() : p.badge;
          if (n) badge = `<span class="count">${Number(n) > 99 ? "99+" : Number(n)}</span>`;
        } catch {}
        const view = typeof S === "object" && S ? S.view : "";
        rows.push(`<button class="nav-item ${view === p.name ? "on" : ""}" data-act="pcpage" data-v="${esc(p.name)}" title="${esc(p.tip || p.nav || p.name)}">${draw(p.icon || "grid")}<span class="label">${esc(p.nav || p.name)}</span>${badge}</button>`);
      }
    }
    return rows.join("");
  };
  P.openPage = (name) => {
    const p = P._pages.find(x => x.name === name);
    if (!p) return false;
    if (typeof go === "function") { go(name); return true; }
    return false;
  };
  // A page in the menu draws its own markup, so the paint hooks that normally watch a Settings panel never fire
  // for it. Run the same hooks against the page, once its own load has finished and again after any redraw, so a
  // card that decorates Settings also decorates the page that hosts the same form.
  function runAfter(node) {
    if (!node) return;
    for (const n of P._order) {
      const fn = P[n] && P[n].after && P[n].after.drawSettings;
      if (fn) { try { fn(node); } catch {} }
    }
  }
  // index.html calls this after it has emptied the view for a page it does not know.
  P.drawPage = (name) => {
    const p = P._pages.find(x => x.name === name);
    if (!p) return false;
    const view = document.getElementById("view");
    if (!view) return false;
    view.innerHTML = typeof p.view === "function" ? p.view() : String(p.view || "");
    const settle = () => runAfter(view);
    if (typeof p.load === "function") {
      Promise.resolve().then(() => p.load()).then(settle, (err) => {
        if (P.toast) P.toast("That page could not finish loading.", "bad");
        try { console.warn("[PeakCut] page " + name + ":", err); } catch {}
        settle();
      });
    } else {
      settle();
    }
    return true;
  };

  /* ---- the tools list -------------------------------------------------- */
  P.toolSections = () => P._order.map(n => ({ name: n, def: P[n] }))
    .filter(x => typeof x.def.tools === "function");

  /* ---- click routing --------------------------------------------------- */
  // index.html handles its own [data-act] values in one big listener and ignores
  // anything it does not know, so a plug-in only has to register here.
  function wireActs() {
    document.addEventListener("click", async (e) => {
      const b = e.target.closest("[data-act]");
      if (!b) return;
      const act = b.dataset.act;
      // A page a feature put in the main menu opens itself; nothing else has to know it exists.
      if (act === "pcpage") {
        const v = b.dataset.v;
        if (v) { e.preventDefault(); P.openPage(v); }
        return;
      }
      for (const n of P._order) {
        const fn = P[n] && P[n].act && P[n].act[act];
        if (!fn) continue;
        e.preventDefault();
        try { await fn(b, e); } catch (err) { if (P.toast) P.toast(String(err.message || err), "bad"); }
        return;
      }
    });
  }

  /* ---- paint hooks ---------------------------------------------------- */
  // Some features only need to adjust markup that another function just drew.
  // `P.after("jobs", node)` is called whenever `#jobs` changes, and so on.
  const painted = new WeakMap();
  function watch(selector, hookName) {
    const els = Array.from(document.querySelectorAll(selector));
    for (const el of els) {
      const key = hookName + ":" + (el.innerHTML.length);
      if (painted.get(el) === key) continue;
      painted.set(el, key);
      for (const n of P._order) {
        const fn = P[n] && P[n].after && P[n].after[hookName];
        if (fn) { try { fn(el); } catch {} }
      }
    }
  }
  function repaint() {
    watch("#jobs", "drawJobs");
    watch("#ov", "drawOverview");
    watch("#cbody", "drawCreator");
    watch("#clipdlg", "drawClipDlg");
    watch("#sform", "drawSettings");
    watch(".topbar", "drawShell");
  }

  /* ---- keyboard ------------------------------------------------------- */
  function wireKeys() {
    document.addEventListener("keydown", async (e) => {
      const t = e.target;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable)) return;
      for (const n of P._order) {
        const fn = P[n] && P[n].keys;
        if (!fn) continue;
        try { if (await fn(e) === true) { e.preventDefault(); return; } } catch {}
      }
    });
  }

  /* ---- the Tools tab -------------------------------------------------- */
  // index.html renders `<div id="toolsec">` inside Settings > Tools and calls
  // P.loadTools() when that tab opens. Nothing else is required.
  P.toolsHtml = () => P.toolSections().map(({ name, def }) => {
    let inner = "";
    try { inner = def.tools(); }
    catch (err) {
      // The message goes into markup, so it is escaped like any other untrusted text.
      const why = String((err && err.message) || err || "");
      inner = `<p class="help">This part did not load: ${String(why).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]))}</p>`;
    }
    return `<div class="toolsbox" id="tool_${name}" data-tool="${name}">${inner}</div>`;
  }).join("");

  P.loadTools = async () => {
    for (const n of P._order) {
      const def = P[n];
      if (!def || typeof def.load !== "function") continue;
      // One part failing must not stop the rest, but it must not vanish either: the contract asks for
      // one quiet line rather than silence, so the person can see that a card did not come up.
      try { await def.load(); }
      catch (err) {
        try { if (P.toast) P.toast("One tool could not start. The others still work.", "bad"); } catch {}
        try { if (window.console) console.warn("[PeakCut] " + n + " did not load:", err); } catch {}
      }
    }
    repaint();
  };

  /* ---- boot ----------------------------------------------------------- */
  P._wire = (name) => { repaint(); };

  // Every file in web/feat/ is loaded here, so dropping a file in is all a feature needs. `_example.js` and
  // anything else starting with an underscore is ignored by the server's listing.
  P.loadFiles = async () => {
    let files = [];
    try { files = (await (await fetch("/assets/feat")).json()).files || []; } catch { return; }
    await Promise.all(files.map(f => new Promise(done => {
      const s = document.createElement("script");
      s.src = "/assets/feat/" + f;
      s.onload = done; s.onerror = done;
      document.head.append(s);
    })));
  };

  P.boot = () => {
    if (P._booted) { repaint(); return; }
    P._booted = true;
    P.toast = (m, k) => { try { if (typeof toast === "function") toast(m, k); } catch {} };
    P.send = (p, b, m) => send(p, b, m);
    P.api = (p, o) => api(p, o);
    P.state = () => S;
    P.money = {};
    wireActs(); wireKeys();
    // Redraw on a timer as well as a frame: a page opened in a background tab runs no animation
    // frames at all, so anything that only ever drew from a frame stayed blank until somebody
    // looked at it. `repaint` is cheap when nothing changed, so the timer costs almost nothing.
    const loop = () => { repaint(); };
    try { (function again() { loop(); setTimeout(again, 250); })(); } catch { loop(); }
    try { (function frame() { requestAnimationFrame(frame); repaint(); })(); } catch { /* the timer above redraws */ }
    document.addEventListener("peakcut:render", repaint);
    // A link straight to a page a feature file owns only becomes knowable once that file is in the page,
    // which is after index.html has already read the address. So read it again now, and go there.
    try {
      if (typeof fromPath === "function" && typeof go === "function") {
        const want = fromPath(location.pathname);
        if (want && want[0] && P.hasPage(want[0]) && (!S || S.view !== want[0])) go(want[0], want[1], true);
      }
    } catch {}
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => setTimeout(async () => { await P.loadFiles(); P.boot(); }, 1400));
  else setTimeout(async () => { await P.loadFiles(); P.boot(); }, 1400);
})();
