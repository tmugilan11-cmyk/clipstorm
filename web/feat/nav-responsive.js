/* The menu is longer than the window now. Only the rows scroll: the search box, the
 * logo and the account feet stay put, and the last row has room under it so it never
 * sits under the bottom edge. On a narrow window the sidebar is a drawer, so the
 * sidebar's own collapse button opens and closes it instead of shrinking it. The page
 * already keeps that choice in one class on #app: "mini" for a narrow sidebar, "open"
 * for a drawer. This reads both and only adds the small-screen meaning of the button. */
(() => {
  const P = (window.PeakCut = window.PeakCut || {});
  const NARROW = "(max-width: 900px)";
  const narrow = () => window.matchMedia(NARROW).matches;

  P.css("nav-responsive", `
    /* Rows scroll; nothing else in the sidebar moves. */
    .side{overflow:hidden}
    .side-head,.side-foot{flex:none}
    #nav{overflow-y:auto;overscroll-behavior:contain;-webkit-overflow-scrolling:touch;
      scroll-padding-bottom:14px;padding-bottom:calc(18px + env(safe-area-inset-bottom))}
    @media ${NARROW}{
      /* The page hides this button on a small screen. It is the way back out now. */
      .side-head .collapse{display:grid;color:var(--frame-text)}
      /* A closed drawer is off the side of the window. Hidden, so the keyboard cannot
         walk into a menu nobody can see, and it slides away before it goes. */
      .side{width:min(280px,86vw);visibility:hidden;
        transition:transform .2s ease,visibility 0s linear .2s}
      .app.open .side{visibility:visible;transition:transform .2s ease,visibility 0s}
      #nav{padding-bottom:calc(30px + env(safe-area-inset-bottom))}
    }
    @media (prefers-reduced-motion:reduce){.side{transition:none}}
  `);

  let wired = false;

  // The page owns the classes. Report them on the button so the state is announced.
  function sync() {
    const app = document.getElementById("app");
    const btn = document.getElementById("collapseBtn");
    if (!app || !btn) return;
    const open = app.classList.contains("open");
    const mini = app.classList.contains("mini");
    const words = narrow()
      ? (open ? "Close the menu" : "Open the menu")
      : (mini ? "Widen the sidebar" : "Narrow the sidebar");
    btn.title = words;
    btn.setAttribute("aria-label", words);
    if (narrow()) btn.setAttribute("aria-expanded", String(open));
    else btn.removeAttribute("aria-expanded");
    // The drawer that is off-screen is hidden, but the page put no inert flag on it.
    const side = app.querySelector(".side");
    if (side) side.inert = narrow() && !open;
  }

  function closeDrawer() {
    const app = document.getElementById("app");
    if (!app || !app.classList.contains("open")) return false;
    app.classList.remove("open");
    sync();
    const menuBtn = document.getElementById("menuBtn");
    if (menuBtn && narrow()) menuBtn.focus({ preventScroll: true });
    return true;
  }

  function toggleDrawer() {
    const app = document.getElementById("app");
    if (!app) return;
    const open = !app.classList.contains("open");
    app.classList.toggle("open", open);
    sync();
    if (open) {
      const first = document.querySelector("#nav .nav-item");
      if (first) first.focus({ preventScroll: true });
    } else {
      const menuBtn = document.getElementById("menuBtn");
      if (menuBtn) menuBtn.focus({ preventScroll: true });
    }
  }

  // Runs before the page's own click handler, so on a narrow window "mini" never fires.
  function onClick(e) {
    const btn = e.target && e.target.closest ? e.target.closest('[data-act="collapse"]') : null;
    if (!btn || !narrow()) return;
    e.preventDefault();
    e.stopPropagation();
    toggleDrawer();
  }

  function onKey(e) {
    if (e.key === "Escape") closeDrawer();
  }

  function start() {
    if (!wired) {
      wired = true;
      document.addEventListener("click", onClick, true);
      document.addEventListener("keydown", onKey);
      window.addEventListener("resize", sync);
      // The page opens the drawer from its own topbar button too, so follow the class
      // rather than only the clicks this file answers.
      const app = document.getElementById("app");
      if (app) new MutationObserver(sync).observe(app, { attributes: true, attributeFilter: ["class"] });
    }
    sync();
  }

  start();

  P.add("nav-responsive", {
    after: {
      /** Runs after the shell was drawn: the sidebar may have been rebuilt. */
      drawShell() { start(); },
    },
  });
})();
